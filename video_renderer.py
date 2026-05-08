"""
video_renderer.py — Long-form 16:9 drama video renderer for Drama Desk.

Pipeline:
  1. Download landscape B-roll clips from Pexels (scene-matched)
  2. Loop/extend clips to cover full audio duration
  3. Burn in karaoke-style subtitles + speaker lower-thirds
  4. Mix TTS audio + optional background music bed
  5. Output final 1920x1080 MP4

Free B-roll sources used:
  • Pexels (primary)  — free, API key required (PEXELS_API_KEY env var)
  • Pixabay (fallback) — free, API key required (PIXABAY_API_KEY env var, optional)
"""

import os
import random
import subprocess
import shutil
import requests
import imageio_ffmpeg

from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, SCENE_KEYWORDS

# ── GPU detection ─────────────────────────────────────────────────────────────

def _detect_nvenc() -> bool:
    """Returns True if ffmpeg has h264_nvenc support (NVIDIA GPU available)."""
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10,
        )
        return "h264_nvenc" in result.stdout
    except Exception:
        return False

_USE_NVENC = _detect_nvenc()
if _USE_NVENC:
    print("[render] GPU detected — using h264_nvenc (NVIDIA accelerated)")
else:
    print("[render] CPU encoding — using libx264")

def _encode_args(crf: int = 22, cq: int = 23) -> list:
    if _USE_NVENC:
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(cq), "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", str(crf)]

# ── Pexels helpers ────────────────────────────────────────────────────────────

def _pexels_search(keyword: str, per_page: int = 10) -> list:
    key = os.getenv("PEXELS_API_KEY", "")
    if not key:
        return []
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": key},
            params={"query": keyword, "per_page": per_page, "orientation": "landscape", "size": "medium"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("videos", [])
    except Exception as e:
        print(f"[pexels] Search error '{keyword}': {e}")
    return []


def _pixabay_search(keyword: str, per_page: int = 5) -> list:
    """Pixabay fallback (returns Pexels-compatible dicts)."""
    key = os.getenv("PIXABAY_API_KEY", "")
    if not key:
        return []
    try:
        resp = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": key, "q": keyword, "per_page": per_page, "video_type": "film"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        hits = resp.json().get("hits", [])
        # Normalize to Pexels-style structure
        normalized = []
        for h in hits:
            vids = h.get("videos", {})
            large = vids.get("large", vids.get("medium", {}))
            url = large.get("url", "")
            if url:
                normalized.append({
                    "video_files": [{"link": url, "width": 1920, "height": 1080}]
                })
        return normalized
    except Exception as e:
        print(f"[pixabay] Search error '{keyword}': {e}")
    return []


def _best_landscape_file(video: dict) -> dict | None:
    files = video.get("video_files", [])
    landscape = [f for f in files if f.get("width", 0) >= f.get("height", 0)]
    ranked = sorted(landscape or files, key=lambda x: x.get("width", 0), reverse=True)
    # Prefer HD 1280-1920 range (avoid 4K — too slow to download)
    for f in ranked:
        if 1280 <= f.get("width", 0) <= 1920:
            return f
    return ranked[0] if ranked else None


# ── Video duration helper ─────────────────────────────────────────────────────

def _video_duration(path: str, ffmpeg: str) -> float:
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


# ── Clip downloader + processor ───────────────────────────────────────────────

def _download_and_process_clip(
    video: dict, raw: str, proc: str, ffmpeg: str, clip_len: int = 45
) -> float:
    """Download one video, trim to clip_len, scale to 1920x1080. Returns duration or 0."""
    vf = _best_landscape_file(video)
    if not vf:
        return 0.0
    try:
        r = requests.get(vf["link"], stream=True, timeout=120)
        with open(raw, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
    except Exception as e:
        print(f"[video] Download failed: {e}")
        return 0.0

    cmd = [
        ffmpeg, "-y", "-i", raw,
        "-t", str(clip_len),
        "-vf", (
            f"scale={int(VIDEO_WIDTH*1.04)}:{int(VIDEO_HEIGHT*1.04)}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={VIDEO_FPS}"
        ),
        *_encode_args(), "-an", "-pix_fmt", "yuv420p",
        proc,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if os.path.exists(raw):
        os.remove(raw)
    if result.returncode != 0:
        print(f"[video] ffmpeg processing failed for clip")
        return 0.0
    return _video_duration(proc, ffmpeg)


# ── Background video builder ──────────────────────────────────────────────────

def build_background_video(output_path: str, target_duration: float, scene_tags: list[str]) -> str:
    """
    Download Pexels (+ optional Pixabay) landscape clips and concatenate them
    until `target_duration` seconds are covered. Returns path to raw background
    video (no audio, no subtitles).
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Build keyword list: scene-specific first, then drama defaults
    keywords = list(scene_tags)
    for kw in SCENE_KEYWORDS["default"]:
        if kw not in keywords:
            keywords.append(kw)
    # Add extra drama fallbacks
    keywords += ["people lifestyle", "city night", "indoor aesthetic", "dramatic sunset"]

    clip_paths = []
    accumulated = 0.0
    target = target_duration + 10   # overshoot slightly for trim headroom
    kw_pool = (keywords * 5)        # cycle keywords if needed
    kw_idx = 0

    while accumulated < target and kw_idx < len(kw_pool):
        kw = kw_pool[kw_idx]
        kw_idx += 1

        videos = _pexels_search(kw, per_page=12)
        if not videos:
            videos = _pixabay_search(kw, per_page=5)
        if not videos:
            continue

        random.shuffle(videos)
        # Try first 3 candidates from this keyword
        for vid in videos[:3]:
            n = len(clip_paths)
            raw  = output_path.replace(".mp4", f"_raw{n}.mp4")
            proc = output_path.replace(".mp4", f"_clip{n}.mp4")
            dur = _download_and_process_clip(vid, raw, proc, ffmpeg)
            if dur > 0:
                clip_paths.append(proc)
                accumulated += dur
                print(f"[video] Clip {n+1}: '{kw}' → {dur:.1f}s (total {accumulated:.1f}/{target:.1f}s)")
                break   # move to next keyword after one good clip

        if not clip_paths and kw_idx > 8:
            raise RuntimeError(
                "Could not download any background clips — check PEXELS_API_KEY"
            )

    if not clip_paths:
        raise RuntimeError("No background video clips downloaded")

    # Concatenate clips
    if len(clip_paths) == 1:
        shutil.move(clip_paths[0], output_path)
    else:
        list_file = output_path + ".list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for p in clip_paths:
                f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")
        subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path],
            check=True, capture_output=True, timeout=300,
        )
        os.remove(list_file)
        for p in clip_paths:
            if os.path.exists(p):
                os.remove(p)

    print(f"[video] Background: {output_path} ({accumulated:.1f}s)")
    return output_path


# ── ASS subtitle writer ───────────────────────────────────────────────────────

def _ass_time(sec: float) -> str:
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = int(sec % 60)
    cs = int((sec % 1) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def write_ass_subtitles(captions: list, segments: list, ass_path: str) -> str:
    """
    Generate an ASS subtitle file with:
      • Fade-in/out karaoke-style captions, speaker-color-coded
      • Speaker lower-third labels (top left, semi-transparent box)
    """
    # ASS color format: &HAABBGGRR (alpha, blue, green, red)
    SPEAKER_COLORS = {
        "NARRATOR":     "&H00FFFFFF",   # white
        "OP":           "&H0000DCFF",   # gold/yellow
        "OP_MALE":      "&H0000DCFF",   # gold/yellow
        "CHARACTER_F":  "&H00C896FF",   # pink
        "CHARACTER_M":  "&H0064C8FF",   # light orange
        "CHARACTER_F2": "&H00FFAACC",   # lavender
        "CHARACTER_M2": "&H00FFD080",   # sky blue
    }

    # Build caption→speaker lookup: each caption maps to its segment by time overlap
    def _find_speaker(cap_start: float) -> str:
        for seg in segments:
            if seg["start"] <= cap_start < seg["start"] + seg["duration"] + 0.1:
                return seg.get("speaker", "NARRATOR")
        return "NARRATOR"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {VIDEO_WIDTH}\n"
        f"PlayResY: {VIDEO_HEIGHT}\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # Caption style — large bold, black outline, bottom-center
        "Style: Caption,Arial Black,68,&H00FFFFFF,&H000000FF,"
        "&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,4,2,2,60,60,100,1\n"
        # Label style — smaller, top-left, opaque dark box
        "Style: Label,Arial,42,&H00FFFFFF,&H000000FF,"
        "&H00111111,&HCC000000,-1,0,0,0,100,100,1,0,3,2,1,1,40,40,40,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header)

        # Speaker label lines (layer 0)
        for seg in segments:
            label = seg.get("label", seg.get("speaker", ""))
            start = _ass_time(seg["start"])
            end   = _ass_time(seg["start"] + seg["duration"])
            f.write(f"Dialogue: 0,{start},{end},Label,,0,0,0,,{label}\n")

        # Caption lines (layer 1) — colored + fade animated
        for cap in captions:
            text    = cap["text"].replace("{", "").replace("}", "").replace("\n", " ")
            start   = _ass_time(cap["start"])
            end     = _ass_time(cap["end"])
            speaker = _find_speaker(cap["start"])
            color   = SPEAKER_COLORS.get(speaker, "&H00FFFFFF")
            # {\fad(in_ms,out_ms)} fade + {\c&Hcolor&} speaker color
            styled  = f"{{\\fad(180,120)\\c{color}}}{text}"
            f.write(f"Dialogue: 1,{start},{end},Caption,,0,0,0,,{styled}\n")

    return ass_path


# ── Final render ──────────────────────────────────────────────────────────────

def render_drama_video(
    audio_path: str,
    captions: list,
    segments: list,
    output_path: str,
    scene_tags: list[str] | None = None,
    music_path: str | None = None,
) -> str:
    """
    Full render:
      1. Build Pexels background video
      2. Loop/trim background to exact audio duration
      3. Burn in ASS subtitles
      4. Mix TTS + optional music bed (music at ~8% volume)
      5. Output final MP4
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    base   = os.path.dirname(output_path)

    # ── Measure audio duration ────────────────────────────────────────────────
    dur_result = subprocess.run(
        [ffmpeg, "-i", audio_path, "-f", "null", "-"],
        capture_output=True, text=True, timeout=30,
    )
    audio_duration = 0.0
    for line in dur_result.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            audio_duration = int(h) * 3600 + int(m) * 60 + float(s)
    print(f"[render] Audio duration: {audio_duration:.1f}s ({audio_duration/60:.1f} min)")

    # ── 1. Background video ───────────────────────────────────────────────────
    bg_raw  = os.path.join(base, "_bg_raw.mp4")
    bg_trim = os.path.join(base, "_bg_trim.mp4")
    ass_path = os.path.join(base, "_subs.ass")

    print("[render] Fetching background video from Pexels...")
    build_background_video(bg_raw, audio_duration, scene_tags or [])

    # Loop & trim background to exact audio length
    subprocess.run(
        [ffmpeg, "-y", "-stream_loop", "-1", "-i", bg_raw,
         "-t", str(audio_duration), "-c", "copy", bg_trim],
        check=True, capture_output=True, timeout=300,
    )

    # ── 2. Subtitles ──────────────────────────────────────────────────────────
    print("[render] Writing subtitles...")
    write_ass_subtitles(captions, segments, ass_path)
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    # ── 3. Final assembly ─────────────────────────────────────────────────────
    print("[render] Assembling final video...")

    has_music = music_path and os.path.exists(music_path)
    fade_out_start = max(0, audio_duration - 4)

    if has_music:
        audio_filter = (
            "[1:a]volume=1.0[speech];"
            f"[2:a]volume=0.08,afade=t=in:st=0:d=3,"
            f"afade=t=out:st={fade_out_start:.1f}:d=4[music];"
            "[speech][music]amix=inputs=2:dropout_transition=3[aout]"
        )
        cmd = [
            ffmpeg, "-y",
            "-i", bg_trim,
            "-i", audio_path,
            "-i", music_path,
            "-filter_complex",
            f"[0:v]ass={ass_escaped}[v];{audio_filter}",
            "-map", "[v]", "-map", "[aout]",
            *_encode_args(), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-t", str(audio_duration),
            output_path,
        ]
    else:
        cmd = [
            ffmpeg, "-y",
            "-i", bg_trim,
            "-i", audio_path,
            "-filter_complex", f"[0:v]ass={ass_escaped}[v]",
            "-map", "[v]", "-map", "1:a",
            *_encode_args(), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-t", str(audio_duration),
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"Final render failed:\n{result.stderr[-1200:]}")

    # ── Cleanup temp files ────────────────────────────────────────────────────
    for p in [bg_raw, bg_trim, ass_path]:
        if os.path.exists(p):
            os.remove(p)

    size_mb = os.path.getsize(output_path) / 1_000_000
    print(f"[render] Done: {output_path} ({size_mb:.1f} MB)")
    return output_path
