import asyncio, os, re, subprocess

from dataclasses import dataclass, field

import imageio_ffmpeg

from config import VOICES, SPEAKER_LABELS



try:

    import edge_tts

    _EDGE_OK = True

except ImportError:

    _EDGE_OK = False

    print("[tts] edge-tts not installed: pip install edge-tts")





@dataclass

class ScriptSegment:

    speaker: str

    text: str

    voice: str

    audio_path: str = ""

    start: float = 0.0

    duration: float = 0.0

    words: list = field(default_factory=list)





_FIXED_VOICES = {

    "NARRATOR": VOICES["NARRATOR"],

    "OP":       VOICES["OP"],

    "OP_MALE":  VOICES["OP_MALE"],

}

_FEMALE_V = "fil-PH-BlessicaNeural"

_MALE_V  = "fil-PH-AngeloNeural"

_MALE_H  = {"_M", "_MALE", "HIM", "AMA", "TATAY", "KUYA", "LOLO"}



# ── Per-speaker prosody: rate shifts delivery speed; pitch separates voices ──
# NARRATOR: slow, deep — builds dread, immersive horror narration
# OP (female): slightly slow, natural — personal first-person storytelling
# OP_MALE: slow, lower — male horror storyteller
# CHARACTER_F: faster, higher — reactive, scared female dialogue
# CHARACTER_M: normal, deep — authoritative, menacing male character
# CHARACTER_F2/M2: slight variants so no two characters sound identical
_PROSODY = {
    "NARRATOR":     {"rate": "-22%", "pitch": "-10Hz"},  # slow, deep, dread — horror narrator
    "OP":           {"rate": "-6%",  "pitch": "+0Hz"},
    "OP_MALE":      {"rate": "-10%", "pitch": "-3Hz"},
    "CHARACTER_F":  {"rate": "+4%",  "pitch": "+4Hz"},
    "CHARACTER_M":  {"rate": "-3%",  "pitch": "-9Hz"},
    "CHARACTER_F2": {"rate": "+6%",  "pitch": "+6Hz"},
    "CHARACTER_M2": {"rate": "-1%",  "pitch": "-6Hz"},
    "_DEFAULT_F":   {"rate": "+2%",  "pitch": "+2Hz"},
    "_DEFAULT_M":   {"rate": "-4%",  "pitch": "-7Hz"},
}



def _get_prosody(speaker: str, voice: str) -> dict:
    """Return rate/pitch for this speaker. Falls back to gender-based default."""
    if speaker in _PROSODY:
        return _PROSODY[speaker]
    return _PROSODY["_DEFAULT_M"] if voice == _MALE_V else _PROSODY["_DEFAULT_F"]





def _is_male(tag: str) -> bool:

    t = tag.upper()

    return any(h in t for h in _MALE_H) or bool(re.search(r"_M\d*$", t))





def parse_script(script: str) -> list:

    pat = re.compile(r"\[([A-Z_0-9]+)\]\s*(.*?)(?=\n\s*\[[A-Z_0-9]+\]|$)", re.DOTALL)

    assigned: dict = {}

    segs = []

    for m in pat.finditer(script):

        speaker = m.group(1).strip()

        text    = m.group(2).strip()

        if not text:

            continue

        if speaker in _FIXED_VOICES:

            voice = _FIXED_VOICES.get(speaker)

        elif speaker in assigned:

            voice = assigned[speaker]

        else:

            voice = _MALE_V if _is_male(speaker) else _FEMALE_V

            assigned[speaker] = voice

        segs.append(ScriptSegment(speaker=speaker, text=text, voice=voice))

    return segs





def _get_duration(path: str) -> float:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    r = subprocess.run([ffmpeg, "-i", path], capture_output=True, text=True, timeout=15)

    for line in (r.stdout + r.stderr).splitlines():

        if "Duration:" in line:

            t = line.split("Duration:")[1].split(",")[0].strip()

            h, m, s = t.split(":")

            return int(h)*3600 + int(m)*60 + float(s)

    return 0.0





def _concat(paths: list, output: str) -> None:

    ffmpeg   = imageio_ffmpeg.get_ffmpeg_exe()

    listfile = output + ".list.txt"

    with open(listfile, "w", encoding="utf-8") as f:

        for p in paths:

            f.write(f"file '{os.path.abspath(p).replace(chr(92), chr(47))}'\n")

    subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",listfile,"-c","copy",output],

                   check=True, capture_output=True, timeout=180)

    os.remove(listfile)





async def _synth_async(text: str, voice: str, path: str,

                       rate: str = "+0%", pitch: str = "+0Hz") -> list:

    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)

    words = []

    with open(path, "wb") as f:

        async for chunk in comm.stream():

            if chunk["type"] == "audio":

                f.write(chunk["data"])

            elif chunk["type"] == "WordBoundary":

                words.append({

                    "word":  chunk["text"],

                    "start": chunk["offset"] / 1e7,

                    "end":   (chunk["offset"] + chunk["duration"]) / 1e7,

                })

    return words





def _synthesize_segment(seg: ScriptSegment, path: str) -> tuple:

    if not _EDGE_OK:

        raise RuntimeError("edge-tts not installed: pip install edge-tts")

    text = re.sub(r"\([^)]*\)", "", seg.text).strip() or seg.text.strip()

    p = _get_prosody(seg.speaker, seg.voice)

    words = asyncio.run(_synth_async(text, seg.voice, path, rate=p["rate"], pitch=p["pitch"]))

    return _get_duration(path), words





def _group_captions(words: list, group_size: int = 4) -> list:

    caps = []

    for i in range(0, len(words), group_size):

        g = words[i:i+group_size]

        caps.append({"start": g[0]["start"], "end": g[-1]["end"],

                      "text": " ".join(w["word"] for w in g).upper(),

                      "speaker": g[0].get("speaker", "NARRATOR")})

    return caps





def generate_drama_audio(script: str, output_dir: str) -> dict:

    os.makedirs(output_dir, exist_ok=True)

    segments = parse_script(script)

    if not segments:

        raise ValueError("Script has no valid [SPEAKER] segments")

    print(f"[tts] {len(segments)} segments...")

    paths, all_words, t = [], [], 0.0

    for i, seg in enumerate(segments):

        path  = os.path.join(output_dir, f"seg_{i:03d}.mp3")

        label = SPEAKER_LABELS.get(seg.speaker, seg.speaker)

        try:

            dur, words = _synthesize_segment(seg, path)

        except Exception as e:

            print(f"[tts] Segment {i} failed: {e}")

            continue

        for w in words:

            w["speaker"] = seg.speaker

        seg.audio_path = path

        seg.start      = t

        seg.duration   = dur

        t              += dur

        paths.append(path)

        all_words.extend(words)

        print(f"[tts]   [{label}] {dur:.1f}s -- {seg.text[:50]}...")

    if not paths:

        raise RuntimeError("All TTS segments failed")

    combined = os.path.join(output_dir, "combined_audio.mp3")

    _concat(paths, combined)

    return {

        "audio_path":     combined,

        "segments":       [{"speaker": s.speaker, "label": SPEAKER_LABELS.get(s.speaker, s.speaker),

                            "text": s.text, "start": s.start, "duration": s.duration}

                           for s in segments if s.audio_path],

        "captions":       _group_captions(all_words),

        "total_duration": t,

    }