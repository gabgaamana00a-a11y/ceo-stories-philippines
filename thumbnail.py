"""
thumbnail.py — Viral-optimized thumbnail generator for Drama Desk.

Layout: Real face photo from Pexels (shocked/emotional) + short punchy text.
Formula used by top AITA/Reddit drama channels with 1M+ subs:
  - Human face showing emotion = #1 CTR driver
  - 4-6 word text max (Impact font, massive, with black outline)
  - "AITA?" badge top-left
  - Clean, not cluttered
"""

import os
import math
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


# ── Public entry point ────────────────────────────────────────────────────────

def generate_thumbnail(
    title: str,
    output_path: str,
    background_video_path: str = None,
    style: str = "drama",
    story_seed: str = None,
    pexels_key: str = None,
) -> str:
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    W, H = 1280, 720

    # 1. Background: real face photo > video frame > gradient (in priority order)
    bg = None
    if pexels_key and story_seed:
        bg = _fetch_dramatic_photo(story_seed, pexels_key, W, H)
    if bg is None and background_video_path and os.path.exists(background_video_path):
        try:
            bg = _extract_frame(background_video_path, W, H)
        except Exception:
            pass
    if bg is None:
        bg = _dark_gradient(W, H)

    # 2. Mood: slightly darker + contrast boost for drama feel
    bg = ImageEnhance.Brightness(bg).enhance(0.65)
    bg = ImageEnhance.Contrast(bg).enhance(1.25)

    # 3. Vignette — smooth gradient: opaque left (text area) → transparent right (face)
    bg = bg.convert("RGBA")
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    # Draw column-by-column for a smooth fade: 155 alpha at x=0, 0 alpha at x=W*0.68
    fade_end = int(W * 0.68)
    for x in range(fade_end):
        alpha = int(158 * (1.0 - x / fade_end) ** 0.7)   # power curve: fast drop-off
        vd.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
    # Uniform light tint on right side so face stays readable
    vd.rectangle([fade_end, 0, W, H], fill=(0, 0, 0, 28))
    # Top strip (brand bar area)
    vd.rectangle([0, 0, W, 85], fill=(0, 0, 0, 90))
    bg = Image.alpha_composite(bg, vignette).convert("RGB")

    draw = ImageDraw.Draw(bg)

    # 4. Short punchy thumbnail text (4-6 words, NOT the full title)
    thumb_text = _make_thumbnail_text(story_seed or title)

    # 5. Compose elements
    _draw_aita_badge(draw, W)
    _draw_main_text(draw, thumb_text, W, H)
    _draw_starburst(draw, W)
    _draw_bottom_bar(draw, W, H)
    _draw_border(draw, W, H)

    bg.save(output_path, "PNG", quality=95)
    print(f"Thumbnail saved: {output_path}")
    return output_path


# ── Background helpers ────────────────────────────────────────────────────────

def _fetch_dramatic_photo(seed: str, pexels_key: str, W: int, H: int) -> "Image.Image | None":
    """Download a shocked/emotional face photo from Pexels matching the story theme."""
    try:
        import requests
    except ImportError:
        return None

    s = seed.lower()
    # Theme → emotional face queries (faces = highest CTR on AITA content)
    if any(k in s for k in ["wedding", "bride", "ceremony", "groom", "venue"]):
        queries = ["shocked woman face", "upset woman portrait", "surprised woman dramatic"]
    elif any(k in s for k in ["cheating", "affair", "cheated"]):
        queries = ["sad woman crying", "shocked woman portrait", "upset woman face close up"]
    elif any(k in s for k in ["divorce", "separated"]):
        queries = ["crying woman portrait", "upset woman dramatic", "sad woman face"]
    elif any(k in s for k in ["boss", "fired", "quit", "job", "work"]):
        queries = ["angry woman face", "shocked professional woman", "upset woman office portrait"]
    elif any(k in s for k in ["mom", "mother", "stepmom", "parent"]):
        queries = ["shocked woman face", "angry woman portrait", "upset woman close up"]
    elif any(k in s for k in ["sister", "brother", "sibling"]):
        queries = ["upset woman dramatic face", "shocked woman", "emotional woman portrait"]
    elif any(k in s for k in ["money", "cash", "debt", "stole", "loan"]):
        queries = ["shocked woman stressed", "upset woman face", "worried woman portrait"]
    else:
        queries = ["shocked woman face portrait", "surprised dramatic woman", "emotional woman upset"]

    headers = {"Authorization": pexels_key}
    for q in queries:
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": q, "per_page": 15, "orientation": "landscape"},
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            photos = resp.json().get("photos", [])
            if not photos:
                continue
            photo = random.choice(photos[:8])
            img_url = photo["src"].get("large2x") or photo["src"].get("large")
            img_resp = requests.get(img_url, timeout=30)
            if img_resp.status_code == 200:
                img = Image.open(BytesIO(img_resp.content)).convert("RGB")
                img = _crop_to_ratio(img, W, H)
                print(f"[thumbnail] Photo: '{q}' by {photo.get('photographer', 'Pexels')}")
                return img
        except Exception:
            continue
    return None


def _crop_to_ratio(img: "Image.Image", W: int, H: int) -> "Image.Image":
    """Center-crop to 16:9, bias toward top third (faces are usually there)."""
    iw, ih = img.size
    target_ratio = W / H
    img_ratio = iw / ih
    if img_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        top = (ih - new_h) // 3   # bias toward top (face location)
        img = img.crop((0, top, iw, top + new_h))
    return img.resize((W, H), Image.LANCZOS)


def _extract_frame(video_path: str, W: int, H: int) -> "Image.Image":
    from moviepy import VideoFileClip
    clip = VideoFileClip(video_path)
    frame = clip.get_frame(clip.duration * 0.25)
    clip.close()
    img = Image.fromarray(frame)
    return _crop_to_ratio(img, W, H)


def _dark_gradient(W: int, H: int) -> "Image.Image":
    """Deep red-to-dark fallback gradient (only used when no photo available)."""
    img = Image.new("RGB", (W, H))
    for y in range(H):
        r = y / H
        img.paste((int(45 * (1 - r) + 8 * r), int(5 * (1 - r)), int(5 * (1 - r))), (0, y, W, y + 1))
    return img


# ── Font helpers ──────────────────────────────────────────────────────────────

_THUMB_LINUX_FONT_MAP = {
    "impact.ttf":   ["LiberationSans-Bold.ttf",    "DejaVuSans-Bold.ttf"],
    "arialbd.ttf":  ["LiberationSans-Bold.ttf",    "DejaVuSans-Bold.ttf"],
    "arial.ttf":    ["LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
}
_THUMB_LINUX_FONT_DIRS = [
    "/usr/share/fonts/truetype/liberation/",
    "/usr/share/fonts/truetype/dejavu/",
    "/usr/share/fonts/truetype/",
]


def _font(name: str, size: int) -> "ImageFont.FreeTypeFont":
    candidates = [
        name,
        f"C:\\Windows\\Fonts\\{name}",
        f"/System/Library/Fonts/{name}",
        f"/usr/share/fonts/truetype/msttcorefonts/{name}",
    ]
    for lname in _THUMB_LINUX_FONT_MAP.get(name.lower(), []):
        for d in _THUMB_LINUX_FONT_DIRS:
            candidates.append(f"{d}{lname}")
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _outlined_text(draw, xy, text, font, fill, outline=(0, 0, 0), ow=5, anchor="mm"):
    """Draw text with thick black outline — visible over any background."""
    x, y = xy
    for dx in range(-ow, ow + 1):
        for dy in range(-ow, ow + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


# ── Text content ──────────────────────────────────────────────────────────────

def _make_thumbnail_text(seed: str) -> str:
    """Convert long story seed into 4-6 word punchy thumbnail text (2 short lines)."""
    s = seed.lower().replace("aita for ", "").replace("aita ", "").strip()

    patterns = [
        # specific first (more precise keyword matches)
        (["tacky", "embarrass"],                    "SHE CALLED IT\nTACKY"),
        (["wedding", "venue"],                      "I RUINED\nHER WEDDING?!"),
        (["wedding", "bride", "ceremony"],          "SHE RUINED\nMY WEDDING"),
        (["cheating", "affair", "cheated"],         "SHE CAUGHT HIM\nCHEATING"),
        (["divorce", "separated"],                  "THE DIVORCE\nSHOCKED EVERYONE"),
        (["fired", "quit", "walked out"],           "I QUIT IN FRONT\nOF EVERYONE"),
        (["boss", "job", "work", "office"],         "MY BOSS\nHUMILIATED ME"),
        (["mother-in-law", "mil"],                  "MY MIL\nCROSSED THE LINE"),
        (["mom", "mother", "stepmom"],              "MY MOM\nBETRAYED ME"),
        (["sister"],                                "MY SISTER\nDID THE UNTHINKABLE"),
        (["brother"],                               "MY BROTHER\nCROSSED THE LINE"),
        (["boyfriend", "girlfriend", "ex"],         "MY EX\nRUINED EVERYTHING"),
        (["husband"],                               "MY HUSBAND'S\nSECRET"),
        (["wife"],                                  "SHE HID THIS\nFROM ME"),
        (["money", "cash", "stole", "loan"],        "SHE TOOK\nEVERYTHING"),
        (["party", "invite", "birthday"],           "THEY DIDN'T\nINVITE ME"),
        (["secret", "lied", "truth", "hiding"],     "THE TRUTH\nCAME OUT"),
        (["kicked out", "homeless", "evict"],       "THEY KICKED\nME OUT"),
        (["baby", "pregnant", "child", "kid"],      "SHE HID\nTHE PREGNANCY"),
        (["inheritance", "will", "estate"],         "THEY STOLE\nMY INHERITANCE"),
        (["family"],                                "MY FAMILY\nIS DIVIDED"),
    ]
    for keywords, text in patterns:
        if any(k in s for k in keywords):
            return text

    # Fallback: extract first ~8 meaningful words, split into 2 lines
    words = s.rstrip("?!.").split()[:8]
    mid = max(2, len(words) // 2)
    return " ".join(words[:mid]).upper() + "\n" + " ".join(words[mid:]).upper()


# ── Drawing functions ─────────────────────────────────────────────────────────

def _draw_aita_badge(draw, W: int):
    """Large red AITA? badge — top left, unmissable."""
    font = _font("impact.ttf", 78)
    text = "AITA?"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 16
    x1, y1 = 16, 16
    x2, y2 = x1 + tw + pad * 2, y1 + th + pad
    draw.rectangle([x1, y1, x2, y2], fill=(210, 15, 15))
    draw.rectangle([x1, y1, x2, y2], outline=(255, 70, 70), width=3)
    draw.text((x1 + pad, y1 + pad // 2), text, fill="white", font=font)


def _draw_main_text(draw, thumb_text: str, W: int, H: int):
    """Massive 2-line punchy text — Impact font, black outline, left side of frame."""
    lines = thumb_text.split("\n")[:2]

    # Impact is the viral thumbnail font (used by every top AITA channel)
    font_xl = _font("impact.ttf", 118)
    font_l  = _font("impact.ttf", 95)
    font_m  = _font("impact.ttf", 82)

    max_chars = max(len(l) for l in lines)
    if max_chars <= 10:
        font = font_xl
    elif max_chars <= 14:
        font = font_l
    else:
        font = font_m

    line_h = int(font.size * 1.10) if hasattr(font, 'size') else 110

    # Position: center of left 55% of image, vertically centered
    cx = int(W * 0.28)
    total_h = len(lines) * line_h
    start_y = H // 2 - total_h // 2 + 20   # slight downward bias

    for i, line in enumerate(lines):
        y = start_y + i * line_h
        color = (255, 255, 255) if i == 0 else (255, 220, 30)   # white line 1, gold line 2
        _outlined_text(draw, (cx, y), line, font, fill=color, outline=(0, 0, 0), ow=6)


def _draw_starburst(draw, W: int):
    """Starburst badge top-right — 'OMG' shock reaction."""
    cx, cy = W - 108, 115
    r_outer, r_inner, spikes = 100, 62, 10
    points = []
    for i in range(spikes * 2):
        angle = math.pi * i / spikes - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=(215, 0, 0))
    draw.ellipse((cx - 55, cy - 55, cx + 55, cy + 55), fill=(175, 0, 0))

    font_big = _font("impact.ttf", 42)
    font_sm  = _font("impact.ttf", 26)
    draw.text((cx, cy - 16), "OMG", fill="white", font=font_big, anchor="mm")
    draw.text((cx, cy + 18), "NO WAY", fill=(255, 220, 30), font=font_sm, anchor="mm")


def _draw_bottom_bar(draw, W: int, H: int):
    y = H - 76
    draw.rectangle([0, y, W, H], fill=(185, 12, 12))
    font = _font("arialbd.ttf", 35)
    text = "DRAMA DESK   |   DROP YOUR VERDICT IN THE COMMENTS"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, y + 18), text, fill="white", font=font)


def _draw_border(draw, W: int, H: int):
    b = 10
    for rect in [(0, 0, W, b), (0, H - b, W, H), (0, 0, b, H), (W - b, 0, W, H)]:
        draw.rectangle(rect, fill=(255, 0, 0))
