from __future__ import annotations

import hashlib
import math
import random
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFilter

from utils.files import ensure_dir
from utils.fonts import load_font


Color = Tuple[int, int, int]


def _palette(seed: str) -> Tuple[Color, Color, Color]:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    cyan = (30 + digest[0] % 35, 170 + digest[1] % 60, 220 + digest[2] % 35)
    violet = (130 + digest[3] % 70, 80 + digest[4] % 80, 220 + digest[5] % 30)
    green = (40 + digest[6] % 35, 210 + digest[7] % 35, 150 + digest[8] % 45)
    return cyan, violet, green


def _fit(value: int, design: int, actual: int) -> int:
    return max(1, int(value * actual / design))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> List[str]:
    rough_width = max(16, max_width // max(getattr(font, "size", 30), 1))
    words = textwrap.wrap(text, width=rough_width) or [text]
    lines: List[str] = []
    for word_line in words:
        current = ""
        for char in word_line:
            candidate = current + char
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = char
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) >= max_lines:
            break
    return lines[:max_lines]


def _draw_background(draw: ImageDraw.ImageDraw, size: Tuple[int, int], cyan: Color, violet: Color) -> None:
    width, height = size
    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(4 + 8 * ratio)
        g = int(7 + 13 * ratio)
        b = int(13 + 18 * ratio)
        draw.line((0, y, width, y), fill=(r, g, b))

    grid_gap = max(34, width // 24)
    for x in range(-width, width * 2, grid_gap):
        draw.line((x, height, x + width // 2, height // 2), fill=(*cyan, 26), width=1)
    for y in range(height // 2, height, grid_gap):
        draw.line((0, y, width, y), fill=(*violet, 18), width=1)


def _draw_signal_noise(
    overlay: Image.Image,
    seed: str,
    cyan: Color,
    violet: Color,
    green: Color,
) -> None:
    rng = random.Random(hashlib.sha256(seed.encode("utf-8")).hexdigest())
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size

    for _ in range(105):
        x = rng.randint(0, width)
        y = rng.randint(0, height)
        length = rng.randint(width // 45, width // 16)
        color = [cyan, violet, green][rng.randint(0, 2)]
        alpha = rng.randint(24, 88)
        draw.line((x, y, min(width, x + length), y), fill=(*color, alpha), width=1)

    for _ in range(32):
        x = rng.randint(0, width)
        y = rng.randint(0, height)
        radius = rng.randint(1, 3)
        color = [cyan, violet, green][rng.randint(0, 2)]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, 135))


def _panel(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], color: Color, alpha: int = 130) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=14, fill=(6, 12, 23, 178), outline=(*color, alpha), width=2)
    draw.rectangle((x1 + 20, y1 + 18, x1 + 130, y1 + 21), fill=(*color, 210))
    draw.rectangle((x2 - 112, y2 - 22, x2 - 22, y2 - 19), fill=(*color, 150))


def _draw_radar(
    draw: ImageDraw.ImageDraw,
    center: Tuple[int, int],
    radius: int,
    cyan: Color,
    violet: Color,
    green: Color,
    seed: str,
) -> None:
    cx, cy = center
    rng = random.Random(seed)
    for step in range(1, 5):
        r = radius * step // 4
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*cyan, 54), width=1)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x = cx + int(math.cos(rad) * radius)
        y = cy + int(math.sin(rad) * radius)
        draw.line((cx, cy, x, y), fill=(*violet, 40), width=1)

    for _ in range(9):
        angle = rng.random() * math.pi * 2
        dist = rng.uniform(radius * 0.18, radius * 0.92)
        x = cx + int(math.cos(angle) * dist)
        y = cy + int(math.sin(angle) * dist)
        color = green if rng.random() > 0.45 else cyan
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(*color, 210))
        draw.line((cx, cy, x, y), fill=(*color, 32), width=1)

    sweep_angle = math.radians(310)
    x = cx + int(math.cos(sweep_angle) * radius)
    y = cy + int(math.sin(sweep_angle) * radius)
    draw.line((cx, cy, x, y), fill=(*green, 180), width=3)


def _draw_metric_bars(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    colors: Tuple[Color, Color, Color],
    seed: str,
) -> None:
    x1, y1, x2, y2 = box
    rng = random.Random(seed)
    bar_count = 16
    gap = max(4, (x2 - x1) // 90)
    bar_width = max(6, ((x2 - x1) - gap * (bar_count - 1)) // bar_count)
    baseline = y2 - 20
    for index in range(bar_count):
        height = rng.randint(max(14, (y2 - y1) // 5), max(16, y2 - y1 - 30))
        x = x1 + index * (bar_width + gap)
        color = colors[index % len(colors)]
        draw.rounded_rectangle((x, baseline - height, x + bar_width, baseline), radius=4, fill=(*color, 156))


def _draw_code_stream(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    font,
    color: Color,
    seed: str,
) -> None:
    rng = random.Random(seed)
    x1, y1, x2, y2 = box
    tokens = ["git", "stars", "fork", "agent", "llm", "vector", "cuda", "api", "rank", "trend"]
    y = y1
    while y < y2:
        token_line = "  ".join(rng.choice(tokens) for _ in range(8))
        draw.text((x1, y), token_line[:64], font=font, fill=(*color, rng.randint(45, 100)))
        y += max(18, getattr(font, "size", 20) + 8)


def render_scene_image(
    title: str,
    subtitle: str,
    prompt: str,
    output_path: Path,
    size: Tuple[int, int] = (1920, 1080),
    font_path: Optional[Union[str, Path]] = None,
    fonts_dir: Optional[Path] = None,
) -> Path:
    ensure_dir(output_path.parent)
    width, height = size
    cyan, violet, green = _palette(prompt)

    image = Image.new("RGBA", size, (3, 6, 12, 255))
    draw = ImageDraw.Draw(image)
    _draw_background(draw, size, cyan, violet)

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((-width // 4, -height // 3, width // 2, height // 2), fill=(*cyan, 40))
    gdraw.ellipse((width // 2, height // 6, width + width // 5, height + height // 5), fill=(*violet, 42))
    gdraw.ellipse((width // 3, height // 2, width, height + height // 3), fill=(*green, 20))
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(radius=max(32, width // 30))))

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    _draw_signal_noise(overlay, prompt, cyan, violet, green)
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    title_font = load_font(_fit(76, 1920, width), preferred=font_path, fonts_dir=fonts_dir)
    subtitle_font = load_font(_fit(36, 1920, width), preferred=font_path, fonts_dir=fonts_dir)
    body_font = load_font(_fit(25, 1920, width), preferred=font_path, fonts_dir=fonts_dir)
    label_font = load_font(_fit(22, 1920, width), preferred=font_path, fonts_dir=fonts_dir)
    small_font = load_font(_fit(18, 1920, width), preferred=font_path, fonts_dir=fonts_dir)

    margin_x = _fit(110, 1920, width)
    top = _fit(82, 1080, height)
    header_h = _fit(74, 1080, height)

    draw.text((margin_x, top), "FRONTIER WATCH", font=label_font, fill=(*green, 235))
    draw.text((margin_x + _fit(245, 1920, width), top), "GITHUB TRENDING REPORT", font=label_font, fill=(170, 198, 230, 210))
    draw.line((margin_x, top + header_h, width - margin_x, top + header_h), fill=(*cyan, 118), width=2)

    title_y = top + _fit(104, 1080, height)
    title_lines = _wrap(draw, title, title_font, width - margin_x * 2, 2)
    for line in title_lines:
        draw.text((margin_x, title_y), line, font=title_font, fill=(245, 250, 255, 255))
        title_y += _fit(88, 1080, height)

    subtitle_box = (
        margin_x,
        title_y + _fit(18, 1080, height),
        width - margin_x,
        title_y + _fit(146, 1080, height),
    )
    _panel(draw, subtitle_box, cyan, alpha=120)
    subtitle_lines = _wrap(draw, subtitle, subtitle_font, subtitle_box[2] - subtitle_box[0] - _fit(52, 1920, width), 2)
    y = subtitle_box[1] + _fit(34, 1080, height)
    for line in subtitle_lines:
        draw.text((subtitle_box[0] + _fit(26, 1920, width), y), line, font=subtitle_font, fill=(218, 232, 248, 242))
        y += _fit(48, 1080, height)

    left_panel = (
        margin_x,
        subtitle_box[3] + _fit(42, 1080, height),
        margin_x + _fit(660, 1920, width),
        height - _fit(100, 1080, height),
    )
    right_panel = (
        left_panel[2] + _fit(34, 1920, width),
        left_panel[1],
        width - margin_x,
        left_panel[3],
    )
    _panel(draw, left_panel, violet, alpha=122)
    _panel(draw, right_panel, cyan, alpha=128)

    draw.text((left_panel[0] + _fit(28, 1920, width), left_panel[1] + _fit(36, 1080, height)), "TREND RADAR", font=label_font, fill=(*violet, 235))
    radar_radius = min(left_panel[2] - left_panel[0], left_panel[3] - left_panel[1]) // 3
    _draw_radar(
        draw,
        center=((left_panel[0] + left_panel[2]) // 2, left_panel[1] + _fit(245, 1080, height)),
        radius=radar_radius,
        cyan=cyan,
        violet=violet,
        green=green,
        seed=prompt,
    )

    metric_box = (
        left_panel[0] + _fit(48, 1920, width),
        left_panel[3] - _fit(210, 1080, height),
        left_panel[2] - _fit(48, 1920, width),
        left_panel[3] - _fit(44, 1080, height),
    )
    draw.text((metric_box[0], metric_box[1] - _fit(40, 1080, height)), "SIGNAL VELOCITY", font=small_font, fill=(168, 190, 220, 210))
    _draw_metric_bars(draw, metric_box, (cyan, violet, green), prompt)

    draw.text((right_panel[0] + _fit(28, 1920, width), right_panel[1] + _fit(36, 1080, height)), "WHY IT MATTERS NOW", font=label_font, fill=(*cyan, 235))
    prompt_lines = _wrap(draw, prompt, body_font, right_panel[2] - right_panel[0] - _fit(70, 1920, width), 7)
    y = right_panel[1] + _fit(92, 1080, height)
    for index, line in enumerate(prompt_lines, start=1):
        bullet_x = right_panel[0] + _fit(32, 1920, width)
        draw.rounded_rectangle((bullet_x, y + _fit(8, 1080, height), bullet_x + _fit(26, 1920, width), y + _fit(34, 1080, height)), radius=5, fill=(*green, 170))
        draw.text((bullet_x + _fit(45, 1920, width), y), line, font=body_font, fill=(220, 232, 246, 238))
        y += _fit(48, 1080, height)

    code_box = (
        right_panel[0] + _fit(32, 1920, width),
        right_panel[3] - _fit(220, 1080, height),
        right_panel[2] - _fit(34, 1920, width),
        right_panel[3] - _fit(48, 1080, height),
    )
    draw.rounded_rectangle(code_box, radius=12, fill=(2, 8, 16, 145), outline=(*green, 80), width=1)
    _draw_code_stream(
        draw,
        (
            code_box[0] + _fit(22, 1920, width),
            code_box[1] + _fit(18, 1080, height),
            code_box[2] - _fit(22, 1920, width),
            code_box[3] - _fit(12, 1080, height),
        ),
        small_font,
        green,
        prompt + title,
    )

    footer_y = height - _fit(58, 1080, height)
    draw.text((margin_x, footer_y), "UPDATED FROM GITHUB TRENDING", font=small_font, fill=(152, 178, 210, 190))
    draw.text((width - margin_x - _fit(265, 1920, width), footer_y), "REPORT / EXPLAINER / BUILD SIGNAL", font=small_font, fill=(152, 178, 210, 190))

    image.convert("RGB").save(output_path, quality=95)
    return output_path


def render_thumbnail(
    title: str,
    prompt: str,
    output_path: Path,
    size: Tuple[int, int] = (1920, 1080),
    font_path: Optional[Union[str, Path]] = None,
    fonts_dir: Optional[Path] = None,
) -> Path:
    return render_scene_image(
        title=title,
        subtitle="GitHub 热榜前沿报告：今天开发者正在关注什么",
        prompt=prompt,
        output_path=output_path,
        size=size,
        font_path=font_path,
        fonts_dir=fonts_dir,
    )
