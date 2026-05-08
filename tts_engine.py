"""
tts_engine.py — Multi-voice TTS for Drama Desk.

Parses [SPEAKER] tagged scripts and generates separate audio per segment
using Microsoft Edge TTS neural voices.  All segments are concatenated into
a single MP3 with word-level timing data for subtitle generation.
"""

import os
import asyncio
import re
import subprocess
from dataclasses import dataclass, field

import edge_tts
import imageio_ffmpeg

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
    words: list = field(default_factory=list)   # [{word, start, end}]


# ── Script parser ─────────────────────────────────────────────────────────────

def parse_script(script: str) -> list[ScriptSegment]:
    """Split [SPEAKER] tagged script into segments."""
    pattern = re.compile(
        r"\[([A-Z_0-9]+)\]\s*(.*?)(?=\n\s*\[[A-Z_0-9]+\]|$)",
        re.DOTALL,
    )
    segments = []
    for m in pattern.finditer(script):
        speaker = m.group(1).strip()
        text = m.group(2).strip()
        if not text:
            continue
        voice = VOICES.get(speaker, VOICES["NARRATOR"])
        segments.append(ScriptSegment(speaker=speaker, text=text, voice=voice))
    return segments


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


def _parse_srt_words(srt: str) -> list:
    """Parse Edge TTS SubMaker SRT into word-timing dicts."""
    words = []
    for block in srt.strip().split("\n\n"):
        lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
        if len(lines) < 3:
            continue
        try:
            start_s, end_s = lines[1].split(" --> ")
            words.append({
                "start": _t(start_s),
                "end":   _t(end_s),
                "word":  " ".join(lines[2:]),
            })
        except Exception:
            continue
    return words


def _t(s: str) -> float:
    s = s.strip().replace(",", ".")
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def _concat_audio(paths: list[str], output: str) -> None:
    """Concatenate MP3 files via ffmpeg concat demuxer."""
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
    """Group word-timing dicts into subtitle chunks."""
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


# ── Per-segment TTS ───────────────────────────────────────────────────────────

async def _synthesize_segment(seg: ScriptSegment, path: str) -> tuple[float, list]:
    """
    Generate TTS audio for one segment.
    Returns (duration_seconds, word_timings).
    """
    communicate = edge_tts.Communicate(seg.text, seg.voice)
    submaker = edge_tts.SubMaker()

    with open(path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    srt = submaker.get_srt()
    words = _parse_srt_words(srt)
    duration = _get_audio_duration(path)
    return duration, words


# ── Main entry point ──────────────────────────────────────────────────────────

async def generate_drama_audio(script: str, output_dir: str) -> dict:
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
            duration, words = await _synthesize_segment(seg, path)
        except Exception as e:
            print(f"[tts] Segment {i} ({seg.speaker}) failed: {e} — retrying with NARRATOR voice")
            try:
                seg.voice = VOICES["NARRATOR"]
                duration, words = await _synthesize_segment(seg, path)
            except Exception as e2:
                print(f"[tts] Segment {i} skipped after retry: {e2}")
                continue

        seg.audio_path = path
        seg.start = current_time
        seg.duration = duration
        seg.words = words

        # Offset word timings to absolute position in combined audio
        for w in words:
            all_words.append({
                "word":    w["word"],
                "start":   current_time + w["start"],
                "end":     current_time + w["end"],
                "speaker": seg.speaker,
            })

        current_time += duration
        segment_paths.append(path)
        preview = seg.text[:55].replace("\n", " ")
        print(f"[tts]   [{label}] {duration:.1f}s — {preview}...")

    if not segment_paths:
        raise RuntimeError("All TTS segments failed")

    # Combine all segments into one file
    combined = os.path.join(output_dir, "combined_audio.mp3")
    _concat_audio(segment_paths, combined)

    captions = _group_captions(all_words, group_size=4)

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
        "captions": captions,
        "total_duration": current_time,
    }
