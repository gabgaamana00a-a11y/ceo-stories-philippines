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
import textwrap
import requests
import imageio_ffmpeg
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
        "Style: Caption,LiberationSans-Bold,68,&H00FFFFFF,&H000000FF,"
        "&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,4,2,2,60,60,100,1\n"
        # Label style — smaller, top-left, opaque dark box
        "Style: Label,LiberationSans,42,&H00FFFFFF,&H000000FF,"
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


# ── Horror-style PIL renderer ────────────────────────────────────────────────
#
# Filipino horror story layout:
#   • NARRATOR/OP segments → Dark story card with blood-red accents
#   • Dialogue segments    → Horror chat bubbles with speaker color + history
# No B-roll downloads needed — renders instantly.

_MONOLOGUE_SPEAKERS = {"NARRATOR", "OP", "OP_MALE"}

_SPEAKER_COLORS = {
    "NARRATOR":     (155, 155, 155),
    "OP":           (30,  130, 220),
    "OP_MALE":      (30,  110, 200),
    "HER":          (200,  75, 200),
    "HIM":          (75,  185,  75),
    "HER FRIEND":   (255, 155,  35),
    "HIS FRIEND":   (75,  200, 155),
    "CHARACTER_F":  (200,  75, 200),
    "CHARACTER_M":  (75,  185,  75),
    "CHARACTER_F2": (255, 120, 155),
    "CHARACTER_M2": (75,  175, 220),
}

_LABEL_MAP = {
    "NARRATOR":     "Tagapagsalaysay",
    "OP":           "Kwentista",
    "OP_MALE":      "Kwentista",
    "HER":          "Siya",
    "HIM":          "Siya",
    "HER FRIEND":   "Kaibigan",
    "HIS FRIEND":   "Kaibigan",
    "CHARACTER_F":  "Siya",
    "CHARACTER_M":  "Siya",
    "CHARACTER_F2": "Kaibigan",
    "CHARACTER_M2": "Kaibigan",
}


# Maps Windows font filenames → Linux Liberation/DejaVu equivalents
_LINUX_FONT_MAP = {
    "arialbd.ttf":  ["LiberationSans-Bold.ttf",    "DejaVuSans-Bold.ttf",   "NotoSans-Bold.ttf"],
    "arial.ttf":    ["LiberationSans-Regular.ttf", "DejaVuSans.ttf",        "NotoSans-Regular.ttf"],
    "impact.ttf":   ["LiberationSans-Bold.ttf",    "DejaVuSans-Bold.ttf",   "NotoSans-Bold.ttf"],
}
_LINUX_FONT_DIRS = [
    "/usr/share/fonts/truetype/liberation/",
    "/usr/share/fonts/truetype/dejavu/",
    "/usr/share/fonts/truetype/noto/",
    "/usr/share/fonts/truetype/",
    "/usr/share/fonts/",
]


def _vchat_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        name,
        f"C:\\Windows\\Fonts\\{name}",
        f"/usr/share/fonts/truetype/msttcorefonts/{name}",
    ]
    for lname in _LINUX_FONT_MAP.get(name.lower(), []):
        for d in _LINUX_FONT_DIRS:
            candidates.append(f"{d}{lname}")
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _speaker_color(speaker: str) -> tuple:
    if speaker in _SPEAKER_COLORS:
        return _SPEAKER_COLORS[speaker]
    for key, col in _SPEAKER_COLORS.items():
        if key in speaker or speaker in key:
            return col
    return (150, 150, 150)


# ── Horror visual effects ─────────────────────────────────────────────────────

def _apply_vignette(img: Image.Image, intensity: float = 0.75) -> Image.Image:
    """Add dark edge vignette with blood-red corner bleed."""
    W, H  = img.size
    half  = min(W, H) // 2
    vign  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d     = ImageDraw.Draw(vign)
    steps = 80
    for i in range(steps):
        t      = i / steps
        margin = int(t * half * 0.90)
        if W - 2 * margin < 2 or H - 2 * margin < 2:
            break
        alpha    = int(intensity * 255 * (t ** 1.6))
        red_tint = int(30 * (1 - t))
        d.rectangle([margin, margin, W - margin - 1, H - margin - 1],
                    outline=(red_tint, 0, 0, max(0, min(alpha, 255))), width=2)
    return Image.alpha_composite(img.convert("RGBA"), vign).convert("RGB")


def _apply_scanlines(img: Image.Image, alpha: int = 18) -> Image.Image:
    """Subtle horizontal scanlines for CRT/found-footage feel."""
    W, H = img.size
    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d    = ImageDraw.Draw(scan)
    for y in range(0, H, 4):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), scan).convert("RGB")


def _apply_film_grain(img: Image.Image, frame_idx: int, strength: int = 14) -> Image.Image:
    """Per-frame random noise grain for horror atmosphere."""
    rng = random.Random(frame_idx * 7919)
    W, H  = img.size
    grain = Image.new("L", (W, H))
    px    = grain.load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            v = rng.randint(-strength, strength)
            for dy in range(2):
                for dx in range(2):
                    if x + dx < W and y + dy < H:
                        px[x + dx, y + dy] = max(0, min(255, 128 + v))
    grain_rgb = Image.merge("RGB", (grain, grain, grain))
    return Image.blend(img, grain_rgb, alpha=0.07)


def _apply_red_flicker(img: Image.Image, frame_idx: int) -> Image.Image:
    """Occasional red tint flash on NARRATOR frames for dread effect."""
    rng = random.Random(frame_idx * 1337)
    if rng.random() > 0.18:
        return img
    W, H    = img.size
    flicker = Image.new("RGBA", (W, H), (120, 0, 0, rng.randint(12, 35)))
    return Image.alpha_composite(img.convert("RGBA"), flicker).convert("RGB")


def _apply_horror_effects(img: Image.Image, frame_idx: int, is_narrator: bool = False) -> Image.Image:
    """Apply all horror visual effects to a frame."""
    img = _apply_vignette(img, intensity=0.70 if is_narrator else 0.55)
    img = _apply_scanlines(img, alpha=20)
    img = _apply_film_grain(img, frame_idx, strength=12)
    if is_narrator:
        img = _apply_red_flicker(img, frame_idx)
    return img


def _draw_horror_header(draw, W: int, font) -> None:
    draw.rectangle([0, 0, W, 82], fill=(10, 2, 2))
    draw.rectangle([0, 82, W, 87], fill=(140, 10, 10))  # blood-red accent line
    left_text  = "KWENTONG MULTO  \u2022  Mga Tunay na Karanasan ng mga Pilipino"
    right_text = "I-comment sa ibaba  \u2193"
    draw.text((28, 18), left_text, fill=(190, 140, 140), font=font)
    try:
        rtw = int(font.getlength(right_text))
    except Exception:
        rtw = len(right_text) * 18
    draw.text((W - rtw - 28, 18), right_text, fill=(150, 90, 90), font=font)


def _make_card_frame(seg: dict, W: int = 1920, H: int = 1080) -> Image.Image:
    """Filipino horror story card for NARRATOR / OP / OP_MALE segments."""
    img  = Image.new("RGB", (W, H), (5, 0, 5))
    draw = ImageDraw.Draw(img)

    f_hdr  = _vchat_font("arialbd.ttf", 35)
    f_sub  = _vchat_font("arialbd.ttf", 28)
    f_meta = _vchat_font("arial.ttf",   24)
    f_body = _vchat_font("arial.ttf",   34)
    f_foot = _vchat_font("arial.ttf",   24)

    _draw_horror_header(draw, W, f_hdr)

    # Subtle corner vignette — dark red bleed at corners
    for i in range(40):
        alpha = int(60 * (1 - i / 40))
        draw.rectangle([0, 87 + i, W, 87 + i + 1], fill=(20 - i // 4, 0, 0))

    # Card
    CX, CY = 130, 105
    CW, CH = W - 260, H - 125
    draw.rectangle([CX, CY, CX + CW, CY + CH], fill=(18, 5, 5))
    draw.rectangle([CX, CY, CX + CW, CY + CH], outline=(100, 20, 20), width=2)
    draw.rectangle([CX, CY, CX + 5, CY + CH], fill=(160, 10, 10))  # blood-red left bar

    tx = CX + 26
    y  = CY + 18

    # Speaker label + metadata
    spk   = seg.get("speaker", "NARRATOR")
    label = _LABEL_MAP.get(spk, spk.title())
    color = _speaker_color(spk)
    draw.text((tx, y), label.upper(), fill=color, font=f_sub)
    y += 36
    if spk in ("OP", "OP_MALE"):
        meta = "Sariling Karanasan  \u2022  Kwentong Multo Philippines"
    else:
        meta = "Tagapagsalaysay  \u2022  Kwentong Multo"
    draw.text((tx, y), meta, fill=(100, 60, 60), font=f_meta)
    y += 32
    draw.rectangle([CX + 18, y, CX + CW - 18, y + 1], fill=(55, 20, 20))
    y += 14

    # Body text
    WRAP      = 74
    LINE_H    = 44
    max_lines = (CH - (y - CY) - 58) // LINE_H
    lines     = textwrap.wrap(seg.get("text", ""), width=WRAP)
    for line in lines[:max_lines]:
        draw.text((tx, y), line, fill=(210, 195, 195), font=f_body)
        y += LINE_H
    if len(lines) > max_lines:
        draw.text((tx, y), "\u2026", fill=(100, 70, 70), font=f_body)

    # Footer
    fy = CY + CH - 42
    draw.rectangle([CX + 18, fy - 6, CX + CW - 18, fy - 5], fill=(50, 15, 15))
    draw.text((tx, fy), "[SINDAK]  24.7k    [MULTO]  3.2k Naniniwala    Mag-Subscribe",
              fill=(110, 70, 70), font=f_foot)
    return img


def _make_bubble_frame(history: list, W: int = 1920, H: int = 1080) -> Image.Image:
    """Horror chat-bubble frame for dialogue speakers."""
    img  = Image.new("RGB", (W, H), (5, 0, 5))
    draw = ImageDraw.Draw(img)

    f_hdr  = _vchat_font("arialbd.ttf", 35)
    f_lbl  = _vchat_font("arialbd.ttf", 27)
    f_text = _vchat_font("arial.ttf",   40)
    _draw_horror_header(draw, W, f_hdr)

    BX, BW  = 75, W - 150
    PAD     = 20
    LINE_H  = 50
    LABEL_H = 34
    GAP     = 10
    WRAP    = 68

    def bh(txt: str) -> int:
        return LABEL_H + PAD + max(1, len(textwrap.wrap(txt, width=WRAP)[:6])) * LINE_H + PAD

    # Fit bubbles bottom-up (cap at last 8 to avoid overrun)
    avail   = H - 97 - 12
    visible = []
    used    = 0
    for item in reversed(history[-8:]):
        h = bh(item[2]) + GAP
        used += h
        if used > avail:
            break
        visible.insert(0, item)

    y = 97
    for spk, lbl, txt, is_cur in visible:
        color  = _speaker_color(spk)
        op     = 1.0 if is_cur else 0.48
        c_dim  = tuple(int(v * op) for v in color)
        lines  = textwrap.wrap(txt, width=WRAP)[:6]
        height = bh(txt)

        draw.text((BX, y + 4), lbl.upper(), fill=c_dim, font=f_lbl)

        b_y0 = y + LABEL_H
        b_y1 = b_y0 + PAD + len(lines) * LINE_H + PAD

        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rounded_rectangle(
            [BX, b_y0, BX + BW, b_y1], radius=16,
            fill=(*color, int(55 * op)),
            outline=(*color, int(180 * op)),
            width=3,
        )
        img  = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        draw = ImageDraw.Draw(img)

        tc = (255, 255, 255) if is_cur else (165, 158, 165)
        for j, line in enumerate(lines):
            draw.text((BX + PAD, b_y0 + PAD + j * LINE_H), line, fill=tc, font=f_text)

        y += height + GAP

    return img


# ── Horror ambient audio generator ───────────────────────────────────────────

def _generate_horror_ambient(output_path: str, duration: float, ffmpeg: str) -> str | None:
    """
    Synthesize a low-frequency horror ambient drone using ffmpeg:
    - 38 Hz + 57 Hz + 76 Hz sine tones (ominous rumble)
    - Heavy echo/reverb for cavern-like dread
    - Low-pass filtered to keep only bass atmosphere
    """
    try:
        d = f"{duration + 2:.2f}"
        cmd = [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", f"sine=frequency=38:duration={d}",
            "-f", "lavfi", "-i", f"sine=frequency=57:duration={d}",
            "-f", "lavfi", "-i", f"sine=frequency=76:duration={d}",
            "-f", "lavfi", "-i", f"sine=frequency=19:duration={d}",
            "-filter_complex", (
                "[0:a]volume=0.35[a0];"
                "[1:a]volume=0.22[a1];"
                "[2:a]volume=0.14[a2];"
                "[3:a]volume=0.10[a3];"
                "[a0][a1][a2][a3]amix=inputs=4,"
                "aecho=0.88:0.60:900:0.40,"
                "aecho=0.70:0.45:1800:0.25,"
                "lowpass=f=220,"
                "volume=3.0"
            ),
            "-c:a", "aac", "-b:a", "128k",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(output_path):
            print("[render] Horror ambient drone generated")
            return output_path
        print(f"[render] Horror ambient failed (non-fatal): {result.stderr[-200:]}")
    except Exception as e:
        print(f"[render] Horror ambient exception (non-fatal): {e}")
    return None


def render_chat_video(
    audio_path: str,
    segments: list,
    output_path: str,
    music_path: str | None = None,
) -> str:
    """
    Render Filipino horror video: dark story cards for narration, horror chat bubbles for dialogue.
    Includes synthesized horror ambient audio underneath TTS speech.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    base   = os.path.dirname(output_path) or "."
    fd     = os.path.join(base, "_frames")
    os.makedirs(fd, exist_ok=True)

    audio_duration = sum(s["duration"] for s in segments)
    print(f"[render] Generating {len(segments)} Reddit-style frames...")

    frame_entries = []
    history       = []   # (speaker, label, text, is_current)

    for i, seg in enumerate(segments):
        spk = seg["speaker"]
        lbl = _LABEL_MAP.get(spk, seg.get("label", spk))
        txt = seg["text"]
        dur = seg["duration"]

        history = [(s, l, t, False) for s, l, t, _ in history]
        history.append((spk, lbl, txt, True))

        frame = (_make_card_frame(seg)
                 if spk in _MONOLOGUE_SPEAKERS
                 else _make_bubble_frame(history))

        # Apply horror visual effects
        frame = _apply_horror_effects(frame, i, is_narrator=(spk in _MONOLOGUE_SPEAKERS))

        fpath = os.path.join(fd, f"frame_{i:04d}.png")
        frame.save(fpath, "PNG")
        frame_entries.append((fpath, dur))
        print(f"[render]   [{spk}] frame {i+1}/{len(segments)} ({dur:.1f}s)")

    # Write ffmpeg image concat list
    list_file = os.path.join(base, "_frames.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for fp, dur in frame_entries:
            abs_fp = os.path.abspath(fp).replace("\\", "/")
            f.write(f"file '{abs_fp}'\nduration {dur:.4f}\n")
        # Repeat last frame to prevent ffmpeg concat truncation
        if frame_entries:
            abs_fp = os.path.abspath(frame_entries[-1][0]).replace("\\", "/")
            f.write(f"file '{abs_fp}'\nduration 0.1\n")

    # Encode frames → silent video
    silent = os.path.join(base, "_chat_silent.mp4")
    print("[render] Encoding frames to video...")
    result = subprocess.run([
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-vf", f"fps={VIDEO_FPS},scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
        *_encode_args(), "-pix_fmt", "yuv420p",
        "-t", str(audio_duration + 0.5),
        silent,
    ], capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError(f"Frame encode failed:\n{result.stderr[-800:]}")

    # Use local horror music (always — it IS the ambient track)
    if not music_path:
        local_music = os.path.join(os.path.dirname(__file__), "music", "horror_ambient_loop.mp3")
        if os.path.exists(local_music):
            music_path = local_music

    # Mux audio + horror ambient music
    has_music   = music_path and os.path.exists(music_path)
    has_ambient = False   # sine drone removed; horror_ambient_loop.mp3 is the ambient
    fade_out    = max(0, audio_duration - 4)
    print("[render] Assembling final video...")

    inputs = [ffmpeg, "-y", "-i", silent, "-i", audio_path]
    if has_music:
        inputs += ["-i", music_path]

    # Build audio filter graph
    n_audio = 1 + (1 if has_ambient else 0) + (1 if has_music else 0)
    if n_audio == 1:
        afilt = None
        amap  = "1:a"
    else:
        parts  = ["[1:a]volume=1.0[speech]"]
        mixins = ["[speech]"]
        idx    = 2
        if has_music:
            parts.append(
                f"[{idx}:a]volume=0.72,"
                f"afade=t=in:st=0:d=3,afade=t=out:st={fade_out:.1f}:d=4[music]"
            )
            mixins.append("[music]")
        n_mix = len(mixins)
        parts.append(
            f"{''.join(mixins)}amix=inputs={n_mix}:normalize=0:dropout_transition=3[aout]"
        )
        afilt = ";".join(parts)
        amap  = "[aout]"

    if afilt:
        cmd = [
            *inputs,
            "-filter_complex", afilt,
            "-map", "0:v", "-map", amap,
            *_encode_args(), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            "-t", str(audio_duration), output_path,
        ]
    else:
        cmd = [
            *inputs,
            "-map", "0:v", "-map", amap,
            *_encode_args(), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            "-t", str(audio_duration), output_path,
        ]

    result2 = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result2.returncode != 0:
        raise RuntimeError(f"Final mux failed:\n{result2.stderr[-800:]}")

    # Cleanup
    os.remove(list_file)
    if os.path.exists(silent):
        os.remove(silent)
    if has_ambient and os.path.exists(ambient_path):
        os.remove(ambient_path)
    shutil.rmtree(fd, ignore_errors=True)

    sz = os.path.getsize(output_path) / 1_000_000
    print(f"[render] Done: {output_path} ({sz:.1f} MB)")
    return output_path


# ── Final render (public entry point) ─────────────────────────────────────────

def render_drama_video(
    audio_path: str,
    captions: list,
    segments: list,
    output_path: str,
    scene_tags: list[str] | None = None,
    music_path: str | None = None,
) -> str:
    """
    Render final video using Reddit-style chat/post-card frames.
    scene_tags and captions kept for API compatibility but not used.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    dur_res = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-i", audio_path, "-f", "null", "-"],
        capture_output=True, text=True, timeout=30,
    )
    audio_duration = 0.0
    for line in dur_res.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            audio_duration = int(h) * 3600 + int(m) * 60 + float(s)
    print(f"[render] Audio duration: {audio_duration:.1f}s ({audio_duration/60:.1f} min)")
    return render_chat_video(audio_path, segments, output_path, music_path)
