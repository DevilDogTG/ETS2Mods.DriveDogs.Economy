#!/usr/bin/env python3
"""
Generates the mod's cover/thumbnail image for the ETS2 Mod Manager listing.
Convention shared with the BetterFlares* packages: 276x162 JPEG, referenced
via manifest.sii's `icon:` field.

Composited at 4x (1104x648) then downscaled for anti-aliasing. Unlike the
BetterFlares headlight mods, this one drops the oncoming-beam layer (not a
headlight mod) but keeps the road graphic and gold/amber palette matching
logo.png's own tones.
"""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "logo.png"
OUT_PATH = ROOT / "src" / "cover.jpg"

SCALE = 4
FINAL_SIZE = (276, 162)
CANVAS_SIZE = (FINAL_SIZE[0] * SCALE, FINAL_SIZE[1] * SCALE)

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REG = r"C:\Windows\Fonts\arial.ttf"

BG_TOP = (10, 12, 16)
BG_BOTTOM = (24, 20, 14)
TITLE_COLOR = (255, 255, 255)
SUBTITLE_COLOR = (255, 196, 84)
SKYLINE_COLOR = (5, 5, 9)
SKYLINE_RIM_COLOR = (255, 170, 70)
WINDOW_COLOR = (255, 196, 84)
COIN_COLOR = (255, 196, 84)
COIN_RIM_COLOR = (168, 122, 40)


def make_background(size):
    w, h = size
    img = Image.new("RGB", size, BG_BOTTOM)
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def add_skyline(img):
    """City silhouette confined to the thin gap between the text block and
    the road (roughly 0.685h-0.72h) so it never fights the title/subtitle,
    and is hidden behind the logo where the two would otherwise overlap,
    since this runs before paste_logo."""
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(7)  # fixed seed - stable output across regenerations

    baseline = int(h * 0.722)  # sits right at the road's top edge
    x = 0.0
    while x < w:
        bw = rng.uniform(w * 0.028, w * 0.06)
        top_frac = rng.uniform(0.685, 0.705)
        # one taller tower breaking the skyline for visual interest
        if 0.80 * w < x < 0.90 * w:
            top_frac = 0.635
        top = int(h * top_frac)
        draw.rectangle([x, top, x + bw, baseline], fill=(*SKYLINE_COLOR, 255))
        draw.line([(x, top), (x + bw, top)], fill=(*SKYLINE_RIM_COLOR, 90), width=max(1, int(h * 0.004)))

        # sparse lit windows
        rows = max(1, int((baseline - top) / (h * 0.02)))
        cols = max(1, int(bw / (w * 0.011)))
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.3:
                    wx = x + (c + 0.5) * (bw / cols)
                    wy = top + (r + 0.7) * ((baseline - top) / rows)
                    draw.rectangle(
                        [wx - w * 0.0025, wy - h * 0.004, wx + w * 0.0025, wy + h * 0.004],
                        fill=(*WINDOW_COLOR, 200),
                    )
        x += bw + rng.uniform(w * 0.004, w * 0.012)
    return img


def add_money_motif(img):
    """Subtle glowing coin stacks tucked into the bottom corners, clear of
    the road, logo, and text - a quiet nod to the mod's economy theme."""
    w, h = img.size

    def coin_stack(cx, cy, r, count):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for i in range(count):
            y = cy - i * r * 0.38
            draw.ellipse([cx - r, y - r * 0.34, cx + r, y + r * 0.34], fill=(*COIN_COLOR, 210))
            draw.ellipse(
                [cx - r, y - r * 0.34, cx + r, y + r * 0.34], outline=(*COIN_RIM_COLOR, 230), width=max(1, int(r * 0.08))
            )
        glow = layer.filter(ImageFilter.GaussianBlur(radius=r * 0.5))
        base = img.convert("RGBA")
        base = Image.alpha_composite(base, glow)
        base = Image.alpha_composite(base, layer)
        return base.convert("RGB")

    img = coin_stack(cx=w * 0.10, cy=h * 0.90, r=w * 0.024, count=4)
    img = coin_stack(cx=w * 0.925, cy=h * 0.91, r=w * 0.020, count=3)
    return img


def add_road(img):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    road_top_y = int(h * 0.72)
    draw.polygon(
        [
            (w * 0.30, h),
            (w * 0.70, h),
            (w * 0.56, road_top_y),
            (w * 0.44, road_top_y),
        ],
        fill=(28, 30, 36),
    )
    dash_w = w * 0.01
    for i in range(4):
        t0 = i / 4
        t1 = (i + 0.5) / 4
        y0 = int(h - (h - road_top_y) * t0)
        y1 = int(h - (h - road_top_y) * t1)
        x0 = w * 0.50 - dash_w * (1 - t0) * 0.5
        x1 = w * 0.50 + dash_w * (1 - t0) * 0.5
        draw.rectangle([x0, y1, x1, y0], fill=(120, 110, 90))
    return img


def paste_logo(img):
    logo = Image.open(LOGO_PATH).convert("RGBA")
    target_h = int(img.height * 0.62)
    ratio = target_h / logo.height
    target_w = int(logo.width * ratio)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    pad = int(img.height * 0.06)
    pos = (pad, pad)

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_logo = Image.new("RGBA", logo.size, (0, 0, 0, 160))
    shadow_logo.putalpha(logo.split()[3])
    shadow.paste(shadow_logo, (pos[0] + 6, pos[1] + 6), shadow_logo)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))

    base = img.convert("RGBA")
    base = Image.alpha_composite(base, shadow)
    base.paste(logo, pos, logo)
    return base.convert("RGB")


def fit_font(draw, text, font_path, max_width, start_size, min_size=10):
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(font_path, min_size)


def draw_with_outline(draw, pos, text, font, fill, outline=(0, 0, 0), width=2):
    x, y = pos
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def add_text(img):
    draw = ImageDraw.Draw(img)
    w, h = img.size

    x_start = w * 0.40
    max_width = w * 0.97 - x_start

    title_lines = ["DriveDogs:", "Economy"]
    subtitle = "Economy & Realism Overhaul"

    title_size = int(h * 0.135)
    title_font = None
    for line in title_lines:
        f = fit_font(draw, line, FONT_BOLD, max_width, title_size)
        title_size = min(title_size, f.size)
        title_font = f
    title_font = ImageFont.truetype(FONT_BOLD, title_size)

    subtitle_font = fit_font(draw, subtitle, FONT_REG, max_width, int(h * 0.06))

    line_bbox = draw.textbbox((0, 0), "Ag", font=title_font)
    line_h = (line_bbox[3] - line_bbox[1]) * 1.15

    total_h = line_h * len(title_lines) + line_h * 0.9
    y = h * 0.50 - total_h / 2

    for line in title_lines:
        draw_with_outline(draw, (x_start, y), line, title_font, TITLE_COLOR, width=3)
        y += line_h

    y += line_h * 0.15
    draw_with_outline(draw, (x_start, y), subtitle, subtitle_font, SUBTITLE_COLOR, width=2)
    return img


def main():
    img = make_background(CANVAS_SIZE)
    img = add_skyline(img)
    img = add_road(img)
    img = add_money_motif(img)
    img = paste_logo(img)
    img = add_text(img)
    img = img.resize(FINAL_SIZE, Image.LANCZOS)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PATH, "JPEG", quality=92)
    print(f"Wrote {OUT_PATH} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
