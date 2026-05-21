from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFilter

from utils.files import ensure_dir
from utils.fonts import load_font


def _palette(seed: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    blue = (20 + digest[0] % 45, 120 + digest[1] % 90, 220 + digest[2] % 35)
    purple = (120 + digest[3] % 75, 60 + digest[4] % 85, 220 + digest[5] % 35)
    return blue, purple


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> List[str]:
    words = textwrap.wrap(text, width=42) or [text]
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
    blue, purple = _palette(prompt)

    image = Image.new("RGB", size, (3, 5, 10))
    draw = ImageDraw.Draw(image)

    for y in range(0, height, 72):
        color = (8, 17, 28) if (y // 72) % 2 == 0 else (6, 12, 22)
        draw.rectangle((0, y, width, y + 72), fill=color)

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for x in range(80, width, 160):
        odraw.line((x, 0, x + 180, height), fill=(*blue, 28), width=1)
    for y in range(120, height, 140):
        odraw.line((0, y, width, y), fill=(*purple, 22), width=1)

    odraw.rounded_rectangle((120, 110, width - 120, height - 110), radius=22, outline=(*blue, 130), width=3)
    odraw.rectangle((156, 146, 520, 152), fill=(*purple, 180))
    odraw.rectangle((width - 520, height - 154, width - 156, height - 148), fill=(*blue, 180))

    glow = overlay.filter(ImageFilter.GaussianBlur(radius=12))
    image = Image.alpha_composite(image.convert("RGBA"), glow)
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    title_font = load_font(82, preferred=font_path, fonts_dir=fonts_dir)
    subtitle_font = load_font(42, preferred=font_path, fonts_dir=fonts_dir)
    prompt_font = load_font(28, preferred=font_path, fonts_dir=fonts_dir)
    label_font = load_font(22, preferred=font_path, fonts_dir=fonts_dir)

    draw.text((150, 152), "GITHUB TRENDING", font=label_font, fill=(125, 188, 255, 220))
    draw.text((150, 206), title, font=title_font, fill=(245, 248, 255, 255))

    subtitle_lines = _wrap(draw, subtitle, subtitle_font, width - 320, 3)
    y = 330
    for line in subtitle_lines:
        draw.text((150, y), line, font=subtitle_font, fill=(216, 226, 242, 245))
        y += 62

    draw.rectangle((150, height - 314, width - 150, height - 308), fill=(*purple, 190))
    prompt_lines = _wrap(draw, prompt, prompt_font, width - 320, 4)
    y = height - 282
    for line in prompt_lines:
        draw.text((150, y), line, font=prompt_font, fill=(160, 178, 205, 235))
        y += 42

    draw.text((width - 455, 152), "AI VIDEO SYSTEM", font=label_font, fill=(180, 135, 255, 210))
    draw.text((width - 330, height - 220), "1080P  /  30FPS", font=label_font, fill=(125, 188, 255, 210))

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
        subtitle="今日最值得关注的开源科技信号",
        prompt=prompt,
        output_path=output_path,
        size=size,
        font_path=font_path,
        fonts_dir=fonts_dir,
    )
