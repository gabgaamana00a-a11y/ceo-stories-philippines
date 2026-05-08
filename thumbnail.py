import os
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
