"""
thumbnail.py — High-CTR Filipino horror thumbnail for Kwentong Multo.

Design formula (what drives clicks on Filipino horror YouTube):
  • Near-black background with deep red atmospheric glow
  • Terrified face photo on right side (Pexels), darkened + red-tinted
  • Glowing red eyes emerging from darkness (iconic horror motif)
  • Faint ghost silhouette (misty humanoid)
  • Blood drips from top edge
  • Large Tagalog hook text left-side, Impact font (white + blood-red)
  • "NAKAKATAKOT!" badge top-left
  • Bottom channel bar
"""

import os
import math
import random
import hashlib
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
    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
        exist_ok=True,
    )
    W, H = 1280, 720

    # Stable RNG seeded from story seed (reproducible, same seed = same thumbnail)
    seed_str  = story_seed or title or "default"
    seed_int  = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng       = random.Random(seed_int)

    # ── 1. Near-black background with red atmospheric glow ────────────────────
    bg = _dark_horror_bg(W, H)

    # ── 2. Scared face photo on right side (optional) ─────────────────────────
    face = None
    if pexels_key and story_seed:
        face = _fetch_dramatic_photo(story_seed, pexels_key, W, H)
    if face is None and background_video_path and os.path.exists(background_video_path):
        try:
            face = _extract_frame(background_video_path, W, H)
        except Exception:
            pass

    if face is not None:
        # Darken heavily + red tint — face is atmosphere, not subject
        face = ImageEnhance.Brightness(face).enhance(0.38)
        face = ImageEnhance.Contrast(face).enhance(1.45)
        red_wash  = Image.new("RGBA", (W, H), (85, 0, 0, 65))
        face_rgba = Image.alpha_composite(face.convert("RGBA"), red_wash)
        # Horizontal fade mask: transparent left → opaque right
        fade       = Image.new("L", (W, H), 0)
        fade_start = int(W * 0.40)
        fade_end   = int(W * 0.72)
        fd = ImageDraw.Draw(fade)
        for x in range(fade_start, W):
            a = int(240 * min(1.0, (x - fade_start) / (fade_end - fade_start)) ** 0.55)
            fd.line([(x, 0), (x, H)], fill=a)
        bg = bg.convert("RGBA")
        bg.paste(face_rgba, mask=fade)
        bg = bg.convert("RGB")

    # ── 3. Ghost silhouette ────────────────────────────────────────────────────
    bg = _draw_ghost_silhouette(bg, W, H, rng)

    # ── 4. Edge vignette + bottom red glow reinforcement ──────────────────────
    bg = _apply_horror_atmosphere(bg, W, H)

    # ── 5. Glowing red eyes ────────────────────────────────────────────────────
    bg = _draw_glowing_eyes(bg, W, H, rng)

    draw = ImageDraw.Draw(bg)

    # ── 6. Blood drips from top edge ──────────────────────────────────────────
    _draw_blood_drips(draw, W, rng)

    # ── 7. Horror badge top-left ───────────────────────────────────────────────
    _draw_horror_badge(draw)

    # ── 8. Large Tagalog hook text (returns new bg because of glow pass) ───────
    hook = _make_tagalog_horror_text(story_seed or title, rng)
    bg   = _draw_main_horror_text(bg, W, H, hook)

    # ── 9. Bottom channel bar ─────────────────────────────────────────────────
    draw = ImageDraw.Draw(bg)
    _draw_bottom_bar(draw, W, H)

    bg.save(output_path, "PNG", quality=95)
    print(f"Thumbnail saved: {output_path}")
    return output_path


# ── Background ────────────────────────────────────────────────────────────────

def _dark_horror_bg(W: int, H: int) -> Image.Image:
    """Near-black base (#030008) with deep red radial glow from bottom-center."""
    bg   = Image.new("RGB", (W, H), (3, 0, 8))
    draw = ImageDraw.Draw(bg)

    cx, cy = W // 2, H + 60
    for r in range(350, 0, -5):
        t   = 1.0 - r / 350
        red = int(80 * (t ** 2.2))
        draw.ellipse(
            [cx - r * 2, cy - r, cx + r * 2, cy + r],
            fill=(red, 0, 0),
        )

    # Top-half extra darkening
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd   = ImageDraw.Draw(dark)
    for y in range(H // 2):
        a = int(130 * (1 - y / (H / 2)) ** 1.3)
        dd.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    bg = Image.alpha_composite(bg.convert("RGBA"), dark).convert("RGB")
    return bg


# ── Pexels photo helper ───────────────────────────────────────────────────────

def _fetch_dramatic_photo(seed: str, pexels_key: str, W: int, H: int):
    try:
        import requests
    except ImportError:
        return None

    s = seed.lower()
    if any(k in s for k in ["aswang", "manananggal", "mantiw"]):
        queries = ["terrified woman dark", "scared face dark night"]
    elif any(k in s for k in ["multo", "kaluluwa", "sulok", "telepono", "bangungot"]):
        queries = ["horrified woman face dark", "scared woman dark room"]
    elif any(k in s for k in ["ospital", "hospital", "nurse"]):
        queries = ["dark hospital corridor night", "scared woman hospital"]
    elif any(k in s for k in ["paaralan", "school", "eskwela"]):
        queries = ["scared student face dark", "dark school hallway"]
    elif any(k in s for k in ["gubat", "kagubatan", "probinsya", "baryo"]):
        queries = ["dark forest fog horror", "scared woman forest night"]
    elif any(k in s for k in ["ofw", "abroad", "japan", "dubai", "hongkong"]):
        queries = ["terrified asian woman dark", "scared woman dark room"]
    elif any(k in s for k in ["engkanto", "kapre", "tikbalang", "duwende"]):
        queries = ["eerie foggy forest night", "mysterious dark forest"]
    elif any(k in s for k in ["panaginip", "bangungot", "tulog"]):
        queries = ["terrified woman nightmare dark", "scared woman bed dark"]
    else:
        queries = ["terrified woman dark portrait", "horrified face darkness"]

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
            photo   = random.choice(photos[:8])
            img_url = photo["src"].get("large2x") or photo["src"].get("large")
            ir = requests.get(img_url, timeout=30)
            if ir.status_code == 200:
                img = Image.open(BytesIO(ir.content)).convert("RGB")
                img = _crop_to_ratio(img, W, H)
                print(f"[thumbnail] Photo: '{q}' by {photo.get('photographer','Pexels')}")
                return img
        except Exception:
            continue
    return None


def _crop_to_ratio(img: Image.Image, W: int, H: int) -> Image.Image:
    iw, ih = img.size
    tr, ir = W / H, iw / ih
    if ir > tr:
        nw   = int(ih * tr)
        left = (iw - nw) // 2
        img  = img.crop((left, 0, left + nw, ih))
    else:
        nh  = int(iw / tr)
        top = (ih - nh) // 3
        img = img.crop((0, top, iw, top + nh))
    return img.resize((W, H), Image.LANCZOS)


def _extract_frame(video_path: str, W: int, H: int) -> Image.Image:
    from moviepy import VideoFileClip
    clip  = VideoFileClip(video_path)
    frame = clip.get_frame(clip.duration * 0.25)
    clip.close()
    return _crop_to_ratio(Image.fromarray(frame), W, H)


# ── Horror graphic elements ───────────────────────────────────────────────────

def _draw_ghost_silhouette(
    bg: Image.Image, W: int, H: int, rng: random.Random
) -> Image.Image:
    """Faint misty humanoid ghost silhouette, heavily blurred."""
    ghost = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd    = ImageDraw.Draw(ghost)

    gx = int(W * rng.uniform(0.30, 0.44))
    gy = int(H * 0.22)
    c  = (195, 210, 230, 22)

    head_r   = 36
    body_w   = 52
    body_h   = 130
    neck_top = gy + head_r - 4
    body_top = neck_top + 22

    gd.ellipse([gx - head_r, gy - head_r, gx + head_r, gy + head_r], fill=c)
    gd.rectangle([gx - 11, neck_top, gx + 11, body_top], fill=c)
    gd.ellipse([gx - body_w, body_top, gx + body_w, body_top + body_h], fill=c)
    gd.ellipse([gx - body_w - 38, body_top + 18, gx - body_w + 18, body_top + 88], fill=c)
    gd.ellipse([gx + body_w - 18, body_top + 18, gx + body_w + 38, body_top + 88], fill=c)
    for i in range(6):
        yw = body_top + body_h + i * 26
        w  = body_w - i * 9
        if w < 4:
            break
        gd.ellipse([gx - w, yw, gx + w, yw + 28],
                   fill=(195, 210, 230, max(4, 18 - i * 4)))

    ghost = ghost.filter(ImageFilter.GaussianBlur(radius=20))
    return Image.alpha_composite(bg.convert("RGBA"), ghost).convert("RGB")


def _apply_horror_atmosphere(bg: Image.Image, W: int, H: int) -> Image.Image:
    """Dark edge vignette + stronger bottom red glow."""
    atm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d   = ImageDraw.Draw(atm)

    for i in range(55):
        t = i / 55
        a = int(195 * (1 - t) ** 1.9)
        m = i * 6
        if W - 2 * m < 2 or H - 2 * m < 2:
            break
        d.rectangle([m, m, W - m - 1, H - m - 1], outline=(0, 0, 0, a), width=3)

    for y in range(H - 1, H - 200, -1):
        t = (H - y) / 200
        a = int(50 * (1 - t) ** 1.4)
        d.line([(0, y), (W, y)], fill=(110, 0, 0, a))

    return Image.alpha_composite(bg.convert("RGBA"), atm).convert("RGB")


def _draw_glowing_eyes(
    bg: Image.Image, W: int, H: int, rng: random.Random
) -> Image.Image:
    """Iconic glowing red eyes in the darkness — center-frame."""
    ex  = int(W * rng.uniform(0.42, 0.52))
    ey  = int(H * rng.uniform(0.50, 0.62))
    gap = 52

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)

    for eye_cx in [ex - gap // 2, ex + gap // 2]:
        for r, a, col in [
            (36, 10, (160,  0,  0)),
            (26, 18, (200,  0,  0)),
            (18, 35, (240, 15,  0)),
            (11, 70, (255, 60,  0)),
            ( 5,170, (255,200, 80)),
        ]:
            gd.ellipse(
                [eye_cx - r, ey - r // 2, eye_cx + r, ey + r // 2],
                fill=(*col, a),
            )

    glow = glow.filter(ImageFilter.GaussianBlur(radius=7))
    return Image.alpha_composite(bg.convert("RGBA"), glow).convert("RGB")


def _draw_blood_drips(draw: ImageDraw.Draw, W: int, rng: random.Random) -> None:
    """Blood drips falling from the top edge of the frame."""
    for _ in range(rng.randint(9, 15)):
        x   = rng.randint(20, W - 20)
        h   = rng.randint(22, 90)
        w   = rng.randint(4, 9)
        col = (rng.randint(125, 165), 0, 0)
        draw.rectangle([x - w // 2, 0, x + w // 2, h], fill=col)
        r = rng.randint(5, 12)
        draw.ellipse([x - r, h - r // 2, x + r, h + r], fill=col)


# ── Badge & text ──────────────────────────────────────────────────────────────

def _draw_horror_badge(draw: ImageDraw.Draw) -> None:
    """Top-left badge: 'NAKAKATAKOT!' in blood red."""
    font = _font("impact.ttf", 54)
    text = "NAKAKATAKOT!"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad    = 14
    x1, y1 = 18, 18
    x2, y2 = x1 + tw + pad * 2, y1 + th + pad
    draw.rectangle([x1, y1, x2, y2], fill=(145, 0, 0))
    draw.rectangle([x1, y1, x2, y2], outline=(230, 45, 45), width=3)
    draw.text((x1 + pad, y1 + pad // 2), text, fill=(255, 255, 255), font=font)


def _make_tagalog_horror_text(seed: str, rng: random.Random) -> str:
    """Map story seed keywords → 2-line Tagalog hook text for high CTR."""
    s = seed.lower()

    if any(k in s for k in ["aswang", "manananggal", "mantiw", "sigbin"]):
        hooks = [
            ("NATUKLASAN KO", "ANG ASWANG!"),
            ("ASWANG SA", "AMING LUGAR!"),
            ("NAKITA KO ANG", "TUNAY NA ASWANG!"),
        ]
    elif any(k in s for k in ["multo", "kaluluwa", "sulok", "telepono", "bangungot", "nagsalita"]):
        hooks = [
            ("NAKITA KO ANG", "MULTO SA AMIN!"),
            ("MULTO SA", "AMING BAHAY!"),
            ("HINDI KO", "MALILIMUTAN ITO!"),
            ("ANG MULTO AY", "KASAMA NAMIN!"),
            ("NANINIWALA", "KA BA NITO?"),
        ]
    elif any(k in s for k in ["ospital", "hospital", "nurse", "doktor", "pasyente"]):
        hooks = [
            ("MULTO SA", "OSPITAL!"),
            ("HORROR SA", "OSPITAL!"),
            ("ANG DILIM SA", "OSPITAL!"),
        ]
    elif any(k in s for k in ["paaralan", "school", "eskwela", "estudyante", "guro"]):
        hooks = [
            ("MULTO SA", "AMING ESKWELA!"),
            ("HORROR SA", "PAARALAN!"),
            ("NAKATAGPO NG", "MULTO SA ESKWELA!"),
        ]
    elif any(k in s for k in ["probinsya", "baryo", "bukid", "palayan", "bundok", "gubat"]):
        hooks = [
            ("HORROR SA", "PROBINSYA!"),
            ("KABABALAGHAN SA", "AMING BARYO!"),
            ("SINDAK SA", "PROBINSYA!"),
        ]
    elif any(k in s for k in ["ofw", "abroad", "japan", "hongkong", "dubai", "taiwan", "singapore"]):
        hooks = [
            ("MULTO SA", "ABROAD!"),
            ("HORROR SA", "IBANG BANSA!"),
            ("NAKATAGPO NG", "MULTO SA ABROAD!"),
        ]
    elif any(k in s for k in ["engkanto", "kapre", "tikbalang", "duwende", "nuno", "sirena"]):
        hooks = [
            ("ENGKANTO ANG", "LUMABAS SA GABI!"),
            ("NAKITA KO ANG", "ENGKANTO!"),
            ("ANG KAPRE AY", "TOTOO!"),
        ]
    elif any(k in s for k in ["anak", "tatay", "nanay", "lolo", "lola", "asawa", "pamilya", "magulang"]):
        hooks = [
            ("MULTO SA", "AMING PAMILYA!"),
            ("ANG SIKRETO NG", "AMING PAMILYA!"),
            ("HINDI KO", "MALILIMUTAN ITO!"),
        ]
    elif any(k in s for k in ["panaginip", "bangungot", "tulog", "gising"]):
        hooks = [
            ("PANAGINIP NA", "TOTOO!"),
            ("HUWAG MANAGINIP", "NITO!"),
            ("BANGUNGOT NA", "NAGTOTOO!"),
        ]
    elif any(k in s for k in ["lungsod", "maynila", "metro", "highway", "urban", "kalsada"]):
        hooks = [
            ("URBAN LEGEND NA", "TOTOO!"),
            ("NATUKLASAN KO", "ANG KATOTOHANAN!"),
            ("HORROR SA", "LUNGSOD!"),
        ]
    else:
        hooks = [
            ("HINDI KO", "MALILIMUTAN!"),
            ("NANINIWALA", "KA BA?"),
            ("TOTOO ITO!", "NANGYARI SA AKIN!"),
            ("SINDAK NA", "SINDAK AKO!"),
            ("NAKATAGPO NG", "MULTO!"),
        ]

    line1, line2 = rng.choice(hooks)
    return f"{line1}\n{line2}"


def _draw_main_horror_text(bg: Image.Image, W: int, H: int, hook: str) -> Image.Image:
    """Large 2-line Impact hook text with red/white glow and thick outline."""
    lines     = hook.split("\n")[:2]
    max_chars = max(len(l) for l in lines)

    if max_chars <= 9:
        size = 118
    elif max_chars <= 13:
        size = 98
    else:
        size = 82

    font    = _font("impact.ttf", size)
    line_h  = int(size * 1.18)
    total_h = len(lines) * line_h
    start_y = H // 2 - total_h // 2 + 22
    cx      = int(W * 0.24)

    for i, line in enumerate(lines):
        y = start_y + i * line_h

        # Glow layer
        glow_col   = (190, 0, 0, 50) if i == 0 else (255, 255, 255, 38)
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd         = ImageDraw.Draw(glow_layer)
        for dx in (-10, -5, 0, 5, 10):
            for dy in (-10, -5, 0, 5, 10):
                gd.text((cx + dx, y + dy), line, font=font,
                        fill=glow_col, anchor="mm")
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=11))
        bg = Image.alpha_composite(bg.convert("RGBA"), glow_layer).convert("RGB")

        # Outline + main text
        draw = ImageDraw.Draw(bg)
        ow   = 7
        for dx in range(-ow, ow + 1):
            for dy in range(-ow, ow + 1):
                if dx != 0 or dy != 0:
                    draw.text((cx + dx, y + dy), line, font=font,
                              fill=(0, 0, 0), anchor="mm")
        main_col = (255, 255, 255) if i == 0 else (255, 18, 18)
        draw.text((cx, y), line, font=font, fill=main_col, anchor="mm")

    return bg


def _draw_bottom_bar(draw: ImageDraw.Draw, W: int, H: int) -> None:
    y = H - 64
    draw.rectangle([0, y, W, H], fill=(12, 0, 2))
    draw.rectangle([0, y, W, y + 3], fill=(175, 0, 0))
    font = _font("arialbd.ttf", 31)
    text = "KWENTONG MULTO   •   Mag-Subscribe para sa Bagong Kwento"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, y + 15), text,
              fill=(195, 175, 175), font=font)


# ── Font helpers ──────────────────────────────────────────────────────────────

_LINUX_FONT_MAP = {
    "impact.ttf":  ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf",   "NotoSans-Bold.ttf"],
    "arialbd.ttf": ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf",   "NotoSans-Bold.ttf"],
    "arial.ttf":   ["LiberationSans-Regular.ttf", "DejaVuSans.ttf",     "NotoSans-Regular.ttf"],
}
_LINUX_DIRS = [
    "/usr/share/fonts/truetype/liberation/",
    "/usr/share/fonts/truetype/dejavu/",
    "/usr/share/fonts/truetype/noto/",
    "/usr/share/fonts/truetype/",
    "/usr/share/fonts/",
]


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        name,
        f"C:\\Windows\\Fonts\\{name}",
        f"/System/Library/Fonts/{name}",
        f"/usr/share/fonts/truetype/msttcorefonts/{name}",
    ]
    for lname in _LINUX_FONT_MAP.get(name.lower(), []):
        for d in _LINUX_DIRS:
            candidates.append(f"{d}{lname}")
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()
