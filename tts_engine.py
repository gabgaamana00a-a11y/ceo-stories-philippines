"""
tts_engine.py — Multi-voice TTS for Drama Desk.

Parses [SPEAKER] tagged scripts and generates separate audio per segment
using Kokoro-82M (open-weight, highly expressive emotional voices).
Works on GitHub Actions (CPU/ONNX) and locally (GPU if available).
All segments are concatenated into a single MP3.
"""

import os
import re
import subprocess
import urllib.request
from dataclasses import dataclass, field

import imageio_ffmpeg
import numpy as np
import soundfile as sf

from config import VOICES, SPEAKER_LABELS


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ScriptSegment:
    speaker: str
    text: str
    voice: str
    audio_path: str = ""
    start: float = 0.0
    duration: float = 0.0
    words: list = field(default_factory=list)


# ── Script parser ─────────────────────────────────────────────────────────────

# Fixed anchors — these three always get a specific voice
_FIXED_VOICES = {
    "NARRATOR": VOICES["NARRATOR"],   # af_heart
    "OP":       VOICES["OP"],         # af_bella
    "OP_MALE":  VOICES["OP_MALE"],    # am_michael
}

# Pools for dynamic character assignment — ordered by expressiveness
_FEMALE_POOL = ["af_nicole", "af_aoede", "af_kore", "af_sky",   "af_sarah"]
_MALE_POOL   = ["am_fenrir", "am_puck",  "am_eric", "am_adam",  "am_echo"]

_MALE_HINTS = {"_M_", "_MALE", "HIM", "DAD", "BRO", "BOY", "MAN",
               "HUSBAND", "FATHER", "SON", "UNCLE", "BROTHER", "BOYFRIEND"}


def _is_male_speaker(tag: str) -> bool:
    tag_up = tag.upper()
    # Match whole-word hints: CHARACTER_M but NOT CHARACTER_F2 or HER_FRIEND
    if re.search(r"(?<![A-Z])M(?![A-Z0-9])", tag_up):  # lone M at end after _
        pass  # handled by _M_ check below
    return any(
        tag_up == h or tag_up.endswith(h) or tag_up.startswith(h + "_") or ("_" + h) in tag_up
        for h in _MALE_HINTS
    ) or bool(re.search(r"_M\d*$", tag_up))  # CHARACTER_M, CHARACTER_M2, etc.


def parse_script(script: str) -> list[ScriptSegment]:
    """Split [SPEAKER] tagged script into segments.

    Voice assignment:
    - NARRATOR / OP / OP_MALE → fixed voices from config
    - Every other unique speaker tag → assigned dynamically from a voice pool,
      so no two characters ever share the same voice.
    """
    pattern = re.compile(
        r"\[([A-Z_0-9]+)\]\s*(.*?)(?=\n\s*\[[A-Z_0-9]+\]|$)",
        re.DOTALL,
    )

    # Dynamic assignment state (local to this parse call)
    assigned: dict[str, str] = {}
    f_used: list[str] = []
    m_used: list[str] = []

    def _assign_voice(speaker: str) -> str:
        if speaker in _FIXED_VOICES:
            return _FIXED_VOICES[speaker]
        if speaker in assigned:
            return assigned[speaker]
        if _is_male_speaker(speaker):
            pool, used = _MALE_POOL, m_used
        else:
            pool, used = _FEMALE_POOL, f_used
        # Pick next voice not yet used in this script
        voice = next((v for v in pool if v not in used), pool[len(used) % len(pool)])
        used.append(voice)
        assigned[speaker] = voice
        return voice

    segments = []
    for m in pattern.finditer(script):
        speaker = m.group(1).strip()
        text = m.group(2).strip()
        if not text:
            continue
        segments.append(ScriptSegment(speaker=speaker, text=text, voice=_assign_voice(speaker)))
    return segments


# ── Kokoro model (lazy singleton) ────────────────────────────────────────────

_kokoro = None

_MODEL_DIR   = os.path.join(os.path.dirname(__file__), "models")
_MODEL_URL   = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx"
_VOICES_URL  = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
_MODEL_FILE  = os.path.join(_MODEL_DIR, "kokoro-v1.0.int8.onnx")
_VOICES_FILE = os.path.join(_MODEL_DIR, "voices-v1.0.bin")


def _download_if_missing(url: str, dest: str):
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(f"[tts] Downloading {os.path.basename(dest)} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"[tts] Saved → {dest}")


def _get_kokoro():
    global _kokoro
    if _kokoro is not None:
        return _kokoro
    try:
        from kokoro_onnx import Kokoro as _KokoroOnnx
        _download_if_missing(_MODEL_URL,  _MODEL_FILE)
        _download_if_missing(_VOICES_URL, _VOICES_FILE)
        print("[tts] Loading Kokoro model...")
        _kokoro = _KokoroOnnx(_MODEL_FILE, _VOICES_FILE)
        print("[tts] Kokoro model ready.")
    except Exception as e:
        raise RuntimeError(
            f"[tts] Kokoro init failed: {e}\n"
            "Run: pip install kokoro-onnx soundfile\n"
            "Linux: sudo apt-get install -y espeak-ng"
        )
    return _kokoro


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _get_audio_duration(path: str) -> float:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, "-i", path, "-f", "null", "-"],
        capture_output=True, text=True, timeout=30,
    )
    for line in result.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def _wav_to_mp3(wav_path: str, mp3_path: str) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-q:a", "2", mp3_path],
        check=True, capture_output=True, timeout=60,
    )
    os.remove(wav_path)


def _concat_audio(paths: list[str], output: str) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    list_file = output + ".list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in paths:
            abs_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output],
        check=True, capture_output=True, timeout=180,
    )
    os.remove(list_file)


def _group_captions(words: list, group_size: int = 4) -> list:
    captions = []
    for i in range(0, len(words), group_size):
        group = words[i : i + group_size]
        captions.append({
            "start":   group[0]["start"],
            "end":     group[-1]["end"],
            "text":    " ".join(w["word"] for w in group).upper(),
            "speaker": group[0].get("speaker", "NARRATOR"),
        })
    return captions


# ── Per-segment synthesis ─────────────────────────────────────────────────────

def _synthesize_segment(seg: ScriptSegment, path: str) -> float:
    """Generate Kokoro audio for one segment. Returns duration (seconds)."""
    kokoro = _get_kokoro()
    # Clean up stage directions in parentheses, e.g. "(Gasps)" "(Crying)"
    text = re.sub(r"\([^)]*\)", "", seg.text).strip()
    if not text:
        text = seg.text.strip()

    samples, sample_rate = kokoro.create(
        text,
        voice=seg.voice,
        speed=1.0,
        lang="en-us",
    )
    wav_path = path.replace(".mp3", ".wav")
    sf.write(wav_path, samples, sample_rate)
    _wav_to_mp3(wav_path, path)
    return _get_audio_duration(path)


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_drama_audio(script: str, output_dir: str) -> dict:
    """
    Generate multi-voice audio for the full drama script.

    Returns:
        {
          "audio_path":      str,    # combined MP3
          "segments":        list,   # [{speaker, text, start, duration}]
          "captions":        list,   # [{text, start, end, speaker}]
          "total_duration":  float,  # seconds
        }
    """
    os.makedirs(output_dir, exist_ok=True)
    segments = parse_script(script)
    if not segments:
        raise ValueError("Script has no valid [SPEAKER] segments")

    print(f"[tts] {len(segments)} segments to synthesize...")

    segment_paths = []
    all_words: list[dict] = []
    current_time = 0.0

    for i, seg in enumerate(segments):
        path = os.path.join(output_dir, f"seg_{i:03d}.mp3")
        label = SPEAKER_LABELS.get(seg.speaker, seg.speaker)

        try:
            duration = _synthesize_segment(seg, path)
        except Exception as e:
            print(f"[tts] Segment {i} ({seg.speaker}) failed: {e} — retrying with NARRATOR voice")
            try:
                seg.voice = VOICES["NARRATOR"]
                duration = _synthesize_segment(seg, path)
            except Exception as e2:
                print(f"[tts] Segment {i} skipped after retry: {e2}")
                continue

        seg.audio_path = path
        seg.start = current_time
        seg.duration = duration

        current_time += duration
        segment_paths.append(path)
        preview = seg.text[:55].replace("\n", " ")
        print(f"[tts]   [{label}] {duration:.1f}s — {preview}...")

    if not segment_paths:
        raise RuntimeError("All TTS segments failed")

    combined = os.path.join(output_dir, "combined_audio.mp3")
    _concat_audio(segment_paths, combined)

    print(f"[tts] Total audio: {current_time:.1f}s ({current_time / 60:.1f} min)")

    return {
        "audio_path": combined,
        "segments": [
            {
                "speaker":  s.speaker,
                "label":    SPEAKER_LABELS.get(s.speaker, s.speaker),
                "text":     s.text,
                "start":    s.start,
                "duration": s.duration,
            }
            for s in segments if s.audio_path
        ],
        "captions": _group_captions(all_words, group_size=4),
        "total_duration": current_time,
    }
