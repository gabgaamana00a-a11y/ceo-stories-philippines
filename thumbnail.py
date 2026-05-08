import os
import math
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


def generate_thumbnail(title: str, output_path: str,
                        background_video_path: str = None,
                        style: str = "drama") -> str:
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    # Long-form YouTube: 1280x720 landscape; Shorts/TikTok: 1080x1920 portrait
    width, height = (1280, 720) if style == "drama" else (1080, 1920)
    if background_video_path and os.path.exists(background_video_path):
        try:
            bg = _extract_frame(background_video_path, width, height)
        except Exception:
            bg = _gradient(width, height, style)
    else:
        bg = _gradient(width, height, style)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 140))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    _draw_top_badge(draw, width)
    _draw_main_title(draw, title, width, height)
    _draw_red_highlight_circle(draw, width, height)
    _draw_attention_arrows(draw, width, height)
    _draw_shock_starburst(draw, width, height)
    _draw_bottom_bar(draw, width, height)
    _draw_border(draw, width, height)
    bg.save(output_path, "PNG", quality=95)
    print(f"Thumbnail saved: {output_path}")
    return output_path


def _extract_frame(video_path, width, height):
    from moviepy import VideoFileClip
    clip = VideoFileClip(video_path)
    frame = clip.get_frame(clip.duration * 0.3)
    clip.close()
    img = Image.fromarray(frame).resize((width, height), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(2))
    return ImageEnhance.Brightness(img).enhance(0.6)


def _gradient(width, height, style):
    gradients = {
        "drama":    [(20, 0, 0),     (80, 10, 10)],    # deep crimson — drama style
        "dark":     [(15, 15, 35),   (45, 25, 80)],
        "gradient": [(255, 65, 108), (255, 75, 43)],
        "bright":   [(67, 198, 172), (25, 22, 84)],
        "gold":     [(255, 165, 0),  (139, 69, 19)],
    }
    c = gradients.get(style, gradients["dark"])
    img = Image.new("RGB", (width, height))
    for y in range(height):
        r = y / height
        img.paste(
            (int(c[0][0]*(1-r)+c[1][0]*r),
             int(c[0][1]*(1-r)+c[1][1]*r),
             int(c[0][2]*(1-r)+c[1][2]*r)),
            (0, y, width, y+1)
        )
    return img


def _font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except:
        return ImageFont.load_default()


def _draw_top_badge(draw, width):
    # Drama branding badge — "DRAMA DESK" instead of #SHORTS
    draw.rectangle([width//2-220, 18, width//2+220, 75], fill=(180, 10, 10))
    font = _font("arial.ttf", 38)
    text = "🎭 DRAMA DESK"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((width-(bbox[2]-bbox[0]))//2, 28), text, fill="white", font=font)


def _draw_main_title(draw, title, width, height):
    font_l = _font("arialbd.ttf", 80)
    font_m = _font("arialbd.ttf", 62)
    wrapped = textwrap.wrap(title.upper(), width=22)
    font = font_l if len(wrapped) <= 2 else font_m
    line_h = 95
    start_y = (height - len(wrapped)*line_h) // 2 - 30
    for i, line in enumerate(wrapped):
        y = start_y + i*line_h
        # Shadow
        draw.text((width//2+3, y+3), line, fill=(0,0,0,200), font=font, anchor="mm")
        # Gold first line, white rest — drama look
        color = (255, 200, 50) if i == 0 else (255, 255, 255)
        draw.text((width//2, y), line, fill=color, font=font, anchor="mm")


def _draw_bottom_bar(draw, width, height):
    y = height - 90
    draw.rectangle([0, y, width, y+90], fill=(180, 10, 10))
    font = _font("arialbd.ttf", 38)
    text = "NEW STORY EVERY DAY  •  DROP A COMMENT BELOW"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((width-(bbox[2]-bbox[0]))//2, y+22), text, fill="white", font=font)


def _draw_border(draw, width, height):
    b = 12
    draw.rectangle([0, 0, width, b], fill=(255,0,0))
    draw.rectangle([0, height-b, width, height], fill=(255,0,0))
    draw.rectangle([0, 0, b, height], fill=(255,0,0))
    draw.rectangle([width-b, 0, width, height], fill=(255,0,0))


def _draw_red_highlight_circle(draw, width, height):
    """Jagged red circle around the title area — draws attention like a real highlight."""
    cx, cy = width // 2, height // 2 - 15
    rx, ry = width // 3 + 20, 145
    # Draw a rough ellipse with thick red stroke
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=(255, 15, 15), width=9)
    # Second slightly offset for hand-drawn feel
    draw.ellipse((cx - rx + 4, cy - ry - 4, cx + rx - 4, cy + ry + 4), outline=(220, 0, 0), width=4)


def _draw_attention_arrows(draw, width, height):
    """Two bold red arrows pointing inward to the title from left and right."""
    # Left arrow (pointing right →)
    lx, ly = 55, height // 2 - 15
    shaft = [(lx, ly - 10), (lx + 60, ly - 10), (lx + 60, ly + 10), (lx, ly + 10)]
    head  = [(lx + 55, ly - 28), (lx + 95, ly), (lx + 55, ly + 28)]
    draw.polygon(shaft, fill=(255, 20, 20))
    draw.polygon(head,  fill=(255, 20, 20))

    # Right arrow (pointing left ←)
    rx2, ry2 = width - 55, height // 2 - 15
    shaft2 = [(rx2, ry2 - 10), (rx2 - 60, ry2 - 10), (rx2 - 60, ry2 + 10), (rx2, ry2 + 10)]
    head2  = [(rx2 - 55, ry2 - 28), (rx2 - 95, ry2), (rx2 - 55, ry2 + 28)]
    draw.polygon(shaft2, fill=(255, 20, 20))
    draw.polygon(head2,  fill=(255, 20, 20))


def _draw_shock_starburst(draw, width, height):
    """Starburst badge in top-right with shock text."""
    cx, cy = width - 120, 155
    r_outer, r_inner = 88, 55
    spikes = 12
    points = []
    for i in range(spikes * 2):
        angle = math.pi * i / spikes - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=(220, 0, 0))
    # Inner circle for text
    draw.ellipse((cx - 50, cy - 50, cx + 50, cy + 50), fill=(180, 0, 0))
    font_big = _font("arialbd.ttf", 28)
    font_sm  = _font("arialbd.ttf", 20)
    draw.text((cx, cy - 14), "NO", fill="white", font=font_big, anchor="mm")
    draw.text((cx, cy + 14), "WAY!", fill="white", font=font_sm, anchor="mm")
