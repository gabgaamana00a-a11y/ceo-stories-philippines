"""
thumbnail.py — MAX CTR Filipino success/inspiration thumbnail for CEO Stories.

Viral CTR Formula (analyzed from top Filipino success channels):
  • DARK LEFT / BRIGHT RIGHT split — symbolizes poor-to-rich journey
  • Emotional FACE close-up (right side) — bright, confident, aspirational
  • HUGE bold text (left side) — yellow + white, thick black outline
  • RED urgency accent — arrow, circle, badge elements
  • Wealth symbols — money, graph, gold sparkles
  • Social proof badge — "TRENDING" — creates FOMO
  • Large "CEO STORIES" brand badge top-left
  • Bottom subscribe bar with notification bell icon
"""

import os
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

    # Stable RNG seeded from story seed
    seed_str  = story_seed or title or "default"
    seed_int  = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng       = random.Random(seed_int)

    # ── 1. Dramatic split background: dark left (poverty) → bright gold (success) ──
    bg = _ctr_background(W, H)

    # ── 2. Emotional face photo (right side, large, bright) ─────────────────────
    face = None
    if pexels_key and story_seed:
        face = _fetch_emotional_photo(story_seed, pexels_key, W, H)
    if face is None and background_video_path and os.path.exists(background_video_path):
        try:
            face = _extract_frame(background_video_path, W, H)
        except Exception:
            pass

    if face is not None:
        face = ImageEnhance.Brightness(face).enhance(1.05)
        face = ImageEnhance.Contrast(face).enhance(1.25)
        face = ImageEnhance.Color(face).enhance(1.15)
        gold_wash = Image.new("RGBA", (W, H), (220, 180, 60, 25))
        face_rgba = Image.alpha_composite(face.convert("RGBA"), gold_wash)

        # Face fade: starts at 35% (leaves room for text), fully visible by 78%
        fade = Image.new("L", (W, H), 0)
        fd   = ImageDraw.Draw(fade)
        for x in range(W):
            t = max(0, min(1, (x - W * 0.35) / (W * 0.43)))
            a = int(230 * (t ** 0.6))
            fd.line([(x, 0), (x, H)], fill=a)
        bg = bg.convert("RGBA")
        bg.paste(face_rgba, mask=fade)
        bg = bg.convert("RGB")
    else:
        bg = _draw_money_backup(bg, W, H, rng)

    # ── 3. Glowing upward trend arrow (wealth symbol) ──────────────────────────
    bg = _draw_wealth_arrow(bg, W, H, rng)

    # ── 4. Dark vignette + gold glow burst ────────────────────────────────────
    bg = _ctr_vignette(bg, W, H)

    # ── 5. Money/coin sparkles ────────────────────────────────────────────────
    bg = _draw_coin_sparkles(bg, W, H, rng)

    draw = ImageDraw.Draw(bg)

    # ── 6. RED urgency accent elements ────────────────────────────────────────
    _draw_urgency_elements(draw, W, H, rng)

    # ── 7. CEO STORIES brand badge (LARGER, more prominent) ───────────────────
    _draw_brand_badge(draw)

    # ── 8. Social proof badge (perception of popularity) ───────────────────────
    bg = _draw_social_proof_badge(bg)

    # ── 9. HUGE hook text — 2 lines, max impact ───────────────────────────────
    hook = _make_viral_hook(story_seed or title, rng)
    bg   = _draw_viral_text(bg, W, H, hook)

    # ── 10. Bottom bar with subscribe CTA ──────────────────────────────────────
    draw = ImageDraw.Draw(bg)
    _draw_subscribe_bar(draw, W, H)

    bg.save(output_path, "PNG", quality=95)
    print(f"[thumbnail] HIGH-CTR saved: {output_path}")
    return output_path


# ── 1. Dramatic split background ──────────────────────────────────────────────

def _ctr_background(W: int, H: int) -> Image.Image:
    """Dark left (poverty) → explosive gold right (success), dramatic blend."""
    bg = Image.new("RGB", (W, H), (5, 5, 25))
    draw = ImageDraw.Draw(bg)

    # Left side: cold dark blue wash — expanded to 45% for more text room
    for x in range(int(W * 0.45)):
        for y in range(H):
            dist = abs(y - H/2) / (H/2)
            dark = int(15 * (1 - dist * 0.6))
            r, g, b = 5, 5, 25 + dark
            draw.point((x, y), fill=(r, g, b))

    # Right side: explosive gold glow from center-right
    cx, cy = int(W * 0.78), H // 2
    for r in range(500, 0, -4):
        t = 1.0 - r / 500
        red = int(80 + 180 * (t ** 1.6))
        green = int(30 + 160 * (t ** 1.8))
        blue = int(0 + 40 * (t ** 2.5))
        draw.ellipse(
            [cx - r * 1.2, cy - r, cx + r * 1.2, cy + r],
            fill=(red, green, blue),
        )

    # Blend zone: gradient from dark left to gold right — wider for smooth transition
    blend_start = int(W * 0.25)
    blend_end = int(W * 0.55)
    for x in range(blend_start, blend_end):
        t = (x - blend_start) / (blend_end - blend_start)
        for y in range(0, H, 2):
            try:
                px = bg.getpixel((x, y))
            except Exception:
                continue
            gold_r = int(50 + 200 * t)
            gold_g = int(20 + 180 * t * t)
            gold_b = int(5 + 30 * t * t)
            mix_r = int(px[0] * (1 - t * 0.7) + gold_r * t * 0.7)
            mix_g = int(px[1] * (1 - t * 0.7) + gold_g * t * 0.7)
            mix_b = int(px[2] * (1 - t * 0.7) + gold_b * t * 0.7)
            draw.point((x, y), fill=(min(255, mix_r), min(255, mix_g), min(255, mix_b)))

    # Dark top edge for depth
    dark_top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dt = ImageDraw.Draw(dark_top)
    for y in range(int(H * 0.18)):
        a = int(100 * (1 - y / (H * 0.18)))
        dt.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    bg = Image.alpha_composite(bg.convert("RGBA"), dark_top).convert("RGB")

    return bg


# ── 2. Emotional face fetch ──────────────────────────────────────────────────

def _fetch_emotional_photo(seed: str, pexels_key: str, W: int, H: int):
    """Fetch high-impact emotional/aspirational face from Pexels."""
    try:
        import requests
    except ImportError:
        return None

    s = seed.lower()
    if any(k in s for k in ["negosyo", "business", "entrepreneur", "startup"]):
        queries = ["businessman smiling confident office", "happy business woman success"]
    elif any(k in s for k in ["ceo", "corporate", "executive"]):
        queries = ["confident ceo portrait smiling", "executive business man success"]
    elif any(k in s for k in ["ofw", "abroad", "overseas"]):
        queries = ["happy asian man success", "filipino professional smiling portrait"]
    elif any(k in s for k in ["small business", "tindahan", "store"]):
        queries = ["small business owner smiling proud", "happy shop owner portrait"]
    elif any(k in s for k in ["pamilya", "family", "nanay", "tatay"]):
        queries = ["happy filipino family portrait", "asian mother children happy"]
    elif any(k in s for k in ["mahirap", "probinsya", "baryo", "hirap"]):
        queries = ["asian businessman smiling office", "smiling man success portrait"]
    elif any(k in s for k in ["tech", "startup", "app", "digital"]):
        queries = ["tech entrepreneur smiling laptop", "startup founder laughing"]
    elif any(k in s for k in ["revenge", "higanti", "iniwan", "niloko", "itinakwil"]):
        queries = ["confident businessman serious portrait", "successful man looking up"]
    elif any(k in s for k in ["construction", "worker", "engineer"]):
        queries = ["construction worker smiling success", "engineer smiling hard hat"]
    else:
        queries = ["happy successful businessman portrait", "confident smiling asian professional"]

    headers = {"Authorization": pexels_key}
    for q in queries:
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": q, "per_page": 15, "orientation": "landscape", "size": "large"},
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            photos = resp.json().get("photos", [])
            if not photos:
                continue
            photo = random.choice(photos[:10])
            img_url = photo["src"].get("large2x") or photo["src"].get("original") or photo["src"].get("large")
            ir = requests.get(img_url, timeout=30)
            if ir.status_code == 200:
                img = Image.open(BytesIO(ir.content)).convert("RGB")
                img = _crop_to_ratio(img, W, H)
                print(f"[thumbnail] Face: '{q}' by {photo.get('photographer','Pexels')}")
                return img
        except Exception:
            continue
    return None


def _crop_to_ratio(img: Image.Image, W: int, H: int) -> Image.Image:
    iw, ih = img.size
    tr, ir = W / H, iw / ih
    if ir > tr:
        nw = int(ih * tr)
        left = (iw - nw) // 2
        img = img.crop((left, 0, left + nw, ih))
    else:
        nh = int(iw / tr)
        top = (ih - nh) // 3
        img = img.crop((0, top, iw, top + nh))
    return img.resize((W, H), Image.LANCZOS)


def _extract_frame(video_path: str, W: int, H: int) -> Image.Image:
    from moviepy import VideoFileClip
    clip = VideoFileClip(video_path)
    frame = clip.get_frame(clip.duration * 0.25)
    clip.close()
    return _crop_to_ratio(Image.fromarray(frame), W, H)


# ── 2b. Money backup graphic (if no face) ────────────────────────────────────

def _draw_money_backup(bg: Image.Image, W: int, H: int, rng) -> Image.Image:
    """Bold money/finance symbols as fallback when no face photo."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = int(W * 0.72), int(H * 0.45)
    font = _font("impact.ttf", 200)
    d.text((cx, cy), "₱", fill=(255, 215, 0, 120), font=font, anchor="mm")
    for i in range(3):
        r = 60 - i * 10
        d.ellipse([cx - r, cy - r + 40, cx + r, cy + r + 40],
                  fill=(255, 215, 0, 30 - i * 8))
    img = img.filter(ImageFilter.GaussianBlur(radius=6))
    return Image.alpha_composite(bg.convert("RGBA"), img).convert("RGB")


# ── 3. Wealth arrow ──────────────────────────────────────────────────────────

def _draw_wealth_arrow(bg: Image.Image, W: int, H: int, rng) -> Image.Image:
    """Bold upward-trending arrow — wealth symbol."""
    arr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(arr)

    start_x, start_y = int(W * 0.08), int(H * 0.68)
    end_x, end_y = int(W * 0.52), int(H * 0.20)
    d.line([(start_x, start_y), (end_x, end_y)],
           fill=(255, 215, 0, 55), width=10)

    d.polygon([
        (end_x - 5, end_y + 18),
        (end_x + 22, end_y - 2),
        (end_x - 5, end_y - 22),
    ], fill=(255, 215, 0, 60))

    d.line([(start_x + 30, start_y + 5), (end_x + 5, end_y + 5)],
           fill=(255, 255, 200, 25), width=4)

    arr = arr.filter(ImageFilter.GaussianBlur(radius=3))
    return Image.alpha_composite(bg.convert("RGBA"), arr).convert("RGB")


# ── 4. CTR vignette ──────────────────────────────────────────────────────────

def _ctr_vignette(bg: Image.Image, W: int, H: int) -> Image.Image:
    """Strong edge vignette + bright gold burst from center-right."""
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(v)

    for i in range(60):
        t = i / 60
        a = int(220 * (1 - t) ** 2.2)
        m = i * 5
        if W - 2 * m < 2 or H - 2 * m < 2:
            break
        d.rectangle([m, m, W - m - 1, H - m - 1], outline=(0, 0, 0, a), width=3)

    for y in range(H - 1, H - 120, -1):
        t = (H - y) / 120
        a = int(40 * (1 - t) ** 1.4)
        d.line([(0, y), (W, y)], fill=(255, 200, 30, a))

    return Image.alpha_composite(bg.convert("RGBA"), v).convert("RGB")


# ── 5. Coin sparkles ─────────────────────────────────────────────────────────

def _draw_coin_sparkles(bg: Image.Image, W: int, H: int, rng) -> Image.Image:
    """Gold coin/dollar sparkles — wealth visual cue."""
    sp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)

    for _ in range(30):
        sx = rng.randint(int(W * 0.30), int(W * 0.95))
        sy = rng.randint(int(H * 0.05), int(H * 0.60))
        sz = rng.randint(2, 6)
        a = rng.randint(40, 120)
        d.ellipse([sx - sz, sy - sz, sx + sz, sy + sz],
                  fill=(255, 215, 0, a))

    for _ in range(8):
        sx = rng.randint(int(W * 0.35), int(W * 0.90))
        sy = rng.randint(int(H * 0.05), int(H * 0.50))
        sz = rng.randint(5, 12)
        a = rng.randint(60, 150)
        d.line([(sx - sz, sy), (sx + sz, sy)], fill=(255, 255, 200, a), width=2)
        d.line([(sx, sy - sz), (sx, sy + sz)], fill=(255, 255, 200, a), width=2)

    sp = sp.filter(ImageFilter.GaussianBlur(radius=2))
    return Image.alpha_composite(bg.convert("RGBA"), sp).convert("RGB")


# ── 6. RED urgency elements ──────────────────────────────────────────────────

def _draw_urgency_elements(draw: ImageDraw.Draw, W: int, H: int, rng) -> None:
    """Red attention-grabbing elements: arrow, circle, emoji."""
    # Red circle accent near text
    cx, cy = int(W * 0.38), int(H * 0.62)
    for r in range(45, 0, -3):
        a = int(80 * (1 - r / 45))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(255, 40, 40, a), width=3)

    # Red arrow pointing right (to subscribe/action area)
    ax, ay = int(W * 0.88), int(H * 0.85)
    for i in range(6):
        a = 120 - i * 18
        draw.polygon([
            (ax - 15 - i * 3, ay - 10 - i * 2),
            (ax + 5 + i * 2, ay),
            (ax - 15 - i * 3, ay + 10 + i * 2),
        ], fill=(255, 30, 30, max(0, a)))

    # Small gold star accent near badge (replaces emoji)
    for sx, sy in [(178, 26), (193, 32)]:
        sz = 5
        draw.line([(sx - sz, sy), (sx + sz, sy)], fill=(255, 215, 0, 180), width=2)
        draw.line([(sx, sy - sz), (sx, sy + sz)], fill=(255, 215, 0, 180), width=2)


# ── 7. Brand badge ───────────────────────────────────────────────────────────

def _draw_brand_badge(draw: ImageDraw.Draw) -> None:
    """Larger, bolder brand badge: 'CEO STORIES' with red accent."""
    font = _font("impact.ttf", 54)
    text = "CEO STORIES"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 16
    x1, y1 = 22, 14
    x2, y2 = x1 + tw + pad * 2, y1 + th + pad + 2

    draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 30, 200))
    draw.rectangle([x1, y1, x2, y2], outline=(255, 215, 0), width=4)
    draw.rectangle([x1, y2 - 2, x2, y2], fill=(255, 40, 40))
    draw.text((x1 + pad, y1 + pad // 2), text, fill=(255, 215, 0), font=font)


# ── 8. Social proof badge ────────────────────────────────────────────────────

def _draw_social_proof_badge(bg: Image.Image) -> Image.Image:
    """Social proof badge: 'TRENDING' with drawn flame graphic — creates FOMO."""
    W, H = bg.size
    draw = ImageDraw.Draw(bg)
    font = _font("arialbd.ttf", 32)
    text = "TRENDING"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 10
    gap = 8
    x1, y1 = 22, 82
    x2, y2 = x1 + tw + pad * 2 + gap + 18, y1 + th + pad

    # Red badge background
    draw.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=(200, 20, 20))
    draw.rounded_rectangle([x1, y1, x2, y2], radius=6, outline=(255, 255, 255), width=2)

    # Text
    draw.text((x1 + pad, y1 + pad // 2 - 1), text, fill=(255, 255, 255), font=font)

    # Drawn flame icon (replaces 🔥 emoji)
    fx = x1 + tw + pad + gap + 9
    fy = y1 + th // 2 + 2
    flame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(flame)
    # Outer flame (orange-red)
    fd.ellipse([fx - 7, fy - 10, fx + 3, fy + 4], fill=(255, 100, 0, 200))
    fd.ellipse([fx - 3, fy - 12, fx + 7, fy + 2], fill=(255, 150, 0, 200))
    fd.ellipse([fx - 1, fy - 8, fx + 5, fy + 4], fill=(255, 200, 50, 200))
    # Inner flame (yellow-white)
    fd.ellipse([fx + 1, fy - 6, fx + 3, fy + 1], fill=(255, 255, 200, 220))
    flame = flame.filter(ImageFilter.GaussianBlur(radius=1))
    bg = Image.alpha_composite(bg.convert("RGBA"), flame).convert("RGB")
    return bg


# ── 9. Viral hook text ───────────────────────────────────────────────────────

def _make_viral_hook(seed: str, rng: random.Random) -> str:
    """High-CTR 2-line Tagalog hook text — NO EMOJIS (PIL can't render them)."""
    s = seed.lower()

    if any(k in s for k in ["ceo", "corporation", "korporasyon", "presidente"]):
        hooks = [
            ("MULA SA WALA", "NAGING CEO!"),
            ("CEO NA", "DATING MAHIRAP!"),
            ("SIYA AY", "CEO NA CEO!"),
        ]
    elif any(k in s for k in ["negosyo", "business", "tindahan", "store", "shop"]):
        hooks = [
            ("PISO LANG", "PUHUNAN!"),
            ("MULA TINDAHAN", "IMPERYO NA!"),
            ("NEGOSYANTENG", "NAGSIMULA SA WALA!"),
        ]
    elif any(k in s for k in ["ofw", "abroad", "dubai", "japan", "hongkong", "canada"]):
        hooks = [
            ("OFW NA NAGING", "MAKAKA-IYAK!"),
            ("MULA OFW", "MILYONARYO!"),
            ("NAGSAPALARAN", "SA ABROAD!"),
        ]
    elif any(k in s for k in ["mahirap", "hirap", "walang pera", "bangketa", "estero"]):
        hooks = [
            ("KAHIRAPAN", "KAYAMANAN!"),
            ("MAHIRAP NOON", "MAYAMAN NGAYON!"),
            ("MULA ESTERO", "HANGGANG EMPIRE!"),
        ]
    elif any(k in s for k in ["pamilya", "nanay", "tatay", "ina", "ama", "anak"]):
        hooks = [
            ("ALAY SA", "PAMILYA!"),
            ("PAMILYA NIYA", "NAGTAGUMPAY!"),
            ("SAKRIPISYO PARA", "SA PAMILYA!"),
        ]
    elif any(k in s for k in ["bagsak", "fail", "scam", "naloko", "nawalan", "bangkarote"]):
        hooks = [
            ("BUMAGSAK", "BUMANGON!"),
            ("NATALO PERO", "HINDI SUMUKO!"),
            ("MULA PAGKABIGO", "TAGUMPAY!"),
        ]
    elif any(k in s for k in ["tech", "startup", "app", "software", "programmer"]):
        hooks = [
            ("STARTUP SA", "GARAHE!"),
            ("PROGRAMMER NA", "NAGING CEO!"),
            ("TECH CEO", "MULA SA WALA!"),
        ]
    elif any(k in s for k in ["probinsya", "baryo", "bukid", "lalawigan"]):
        hooks = [
            ("PROBINSYANO", "CEO NGAYON!"),
            ("TAGA-BARYO", "NAGPATUNAY!"),
            ("MULA PROBINSYA", "HANGGANG BOARDROOM!"),
        ]
    elif any(k in s for k in ["revenge", "higanti", "iniwan", "niloko", "pinahiya", "tinanggal", "itinakwil"]):
        hooks = [
            ("PINAHIYA PERO", "BUMANGON!"),
            ("INIWAN DAHIL", "SA KAHIRAPAN!"),
            ("TINANGGAL SA", "TRABAHO NAGING CEO!"),
            ("ITINAKWIL PERO", "MAS MAYAMAN!"),
            ("NILOKO NG KASAMA", "BILLIONAIRE NA!"),
        ]
    else:
        hooks = [
            ("WALA", "YAMAN!"),
            ("KWENTO NG", "TAGUMPAY!"),
            ("SIYA AY", "NAGTAGUMPAY!"),
            ("HINDI SUMUKO", "NGAYON CEO NA!"),
        ]

    line1, line2 = rng.choice(hooks)
    return f"{line1}\n{line2}"


def _draw_viral_text(bg: Image.Image, W: int, H: int, hook: str) -> Image.Image:
    """
    MAX CTR text rendering:
    • Line 1: HUGE bright yellow/gold with thick black outline + inner glow
    • Line 2: Large white with red underline accent
    """
    lines = hook.split("\n")[:2]
    max_chars = max(len(l) for l in lines)

    if max_chars <= 7:
        sizes = (135, 115)  # was 130, 110
    elif max_chars <= 10:
        sizes = (115, 95)   # was 110, 90
    elif max_chars <= 14:
        sizes = (100, 82)   # was 95, 78
    else:
        sizes = (88, 72)    # was 82, 68

    fonts = [_font("impact.ttf", sizes[0]), _font("impact.ttf", sizes[1])]

    line_heights = [int(sizes[i] * 1.15) for i in range(len(lines))]
    total_h = sum(line_heights)
    start_y = H // 2 - total_h // 2 - 15
    cx = int(W * 0.28)

    for i, line in enumerate(lines):
        y = start_y + sum(line_heights[:i]) + (line_heights[i] - sizes[i]) // 2
        font = fonts[i]
        is_gold = (i == 0)

        # GLOW layer
        glow_color = (255, 215, 0, 50) if is_gold else (255, 255, 255, 35)
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        for dx in (-10, -5, 0, 5, 10):
            for dy in (-10, -5, 0, 5, 10):
                gd.text((cx + dx, y + dy), line, font=font, fill=glow_color, anchor="mm")
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=12 if is_gold else 8))
        bg = Image.alpha_composite(bg.convert("RGBA"), glow_layer).convert("RGB")

        # THICK OUTLINE
        draw = ImageDraw.Draw(bg)
        ow = 8 if is_gold else 6
        for dx in range(-ow, ow + 1):
            for dy in range(-ow, ow + 1):
                if dx != 0 or dy != 0:
                    draw.text((cx + dx, y + dy), line, font=font, fill=(0, 0, 0), anchor="mm")

        # MAIN TEXT
        main_col = (255, 220, 30) if is_gold else (255, 255, 255)
        draw.text((cx, y), line, font=font, fill=main_col, anchor="mm")

        # Red underline for line 2 (urgency)
        if i == 1:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            uy = y + int(sizes[1] * 0.55)
            draw.rectangle([cx - tw // 2, uy, cx + tw // 2, uy + 5],
                           fill=(255, 40, 40))

    return bg


# ── 10. Subscribe bar ────────────────────────────────────────────────────────

def _draw_subscribe_bar(draw: ImageDraw.Draw, W: int, H: int) -> None:
    """Bottom subscribe CTA bar with gold accents and red SUBSCRIBE button."""
    y = H - 60
    draw.rectangle([0, y, W, H], fill=(5, 5, 30))

    # Gold top border
    draw.rectangle([0, y, W, y + 3], fill=(255, 215, 0))

    font = _font("arialbd.ttf", 32)
    text = "🔔 SUBSCRIBE  •  CEO STORIES PHILIPPINES  •  ARAW-ARAW"
    draw.text((W // 2, y + 14), text, fill=(255, 215, 0), font=font, anchor="ma")

    # Red SUBSCRIBE pill button
    btn_w, btn_h = 170, 38
    bx, by = W - btn_w - 14, y + 11
    draw.rounded_rectangle([bx, by, bx + btn_w, by + btn_h],
                           radius=19, fill=(255, 10, 10))
    draw.rounded_rectangle([bx, by, bx + btn_w, by + btn_h],
                           radius=19, outline=(255, 255, 255), width=2)
    bfont = _font("arialbd.ttf", 26)
    draw.text((bx + btn_w // 2, by + btn_h // 2), "SUBSCRIBE",
              fill=(255, 255, 255), font=bfont, anchor="mm")


# ── Font helpers ──────────────────────────────────────────────────────────────

_LINUX_FONT_MAP = {
    "impact.ttf":  ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf"],
    "arialbd.ttf": ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf"],
    "arial.ttf":   ["LiberationSans-Regular.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"],
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
