from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFilter

from models import AudioSegment, SubtitleCue
from utils.files import ensure_dir, write_json
from utils.fonts import load_font


def format_srt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    millis = int(round((seconds - math.floor(seconds)) * 1000))
    whole = int(seconds)
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def wrap_chinese_text(text: str, max_chars: int = 18) -> str:
    text = " ".join(text.strip().split())
    if len(text) <= max_chars:
        return text
    lines: List[str] = []
    current = ""
    for char in text:
        current += char
        if len(current) >= max_chars and char in "，。；：、,.!?！？ ":
            lines.append(current.strip())
            current = ""
        elif len(current) >= max_chars + 4:
            lines.append(current.strip())
            current = ""
    if current.strip():
        lines.append(current.strip())
    return "\n".join(lines[:3])


def split_text_for_duration(text: str, duration: float, max_chars: int = 22) -> List[Tuple[str, float]]:
    text = " ".join(text.strip().split())
    if not text:
        return []
    chunks = textwrap.wrap(text, width=max_chars) or [text]
    total_chars = sum(max(len(chunk), 1) for chunk in chunks)
    weighted: List[Tuple[str, float]] = []
    for chunk in chunks:
        ratio = max(len(chunk), 1) / total_chars
        weighted.append((chunk, max(0.8, duration * ratio)))
    return weighted


def build_subtitle_cues(
    segments: List[AudioSegment],
    max_chars: int = 22,
) -> List[SubtitleCue]:
    cues: List[SubtitleCue] = []
    cursor = 0.0
    index = 1
    for segment in segments:
        pieces = split_text_for_duration(segment.text, segment.duration, max_chars=max_chars)
        for text, piece_duration in pieces:
            start = cursor
            end = cursor + piece_duration
            cues.append(
                SubtitleCue(
                    index=index,
                    start=round(start, 3),
                    end=round(end, 3),
                    text=wrap_chinese_text(text, max_chars=18),
                )
            )
            cursor = end
            index += 1
    return cues


def write_srt(path: Path, cues: List[SubtitleCue]) -> Path:
    ensure_dir(path.parent)
    parts: List[str] = []
    for cue in cues:
        parts.append(str(cue.index))
        parts.append(f"{format_srt_time(cue.start)} --> {format_srt_time(cue.end)}")
        parts.append(cue.text)
        parts.append("")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def write_subtitle_manifest(path: Path, cues: List[SubtitleCue]) -> Path:
    return write_json(path, {"cues": cues})


def render_subtitle_image(
    text: str,
    output_path: Path,
    size: Tuple[int, int] = (1920, 260),
    font_size: int = 58,
    font_path: Optional[Union[str, Path]] = None,
    fonts_dir: Optional[Path] = None,
) -> Path:
    ensure_dir(output_path.parent)
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    font = load_font(font_size, preferred=font_path, fonts_dir=fonts_dir)
    draw = ImageDraw.Draw(image)
    lines = text.splitlines() or [text]
    line_height = int(font_size * 1.25)
    total_height = line_height * len(lines)
    y = max(8, (height - total_height) // 2)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        shadow = Image.new("RGBA", size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.text((x + 4, y + 5), line, font=font, fill=(0, 0, 0, 220))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
        image.alpha_composite(shadow)
        draw = ImageDraw.Draw(image)
        draw.text((x, y), line, font=font, fill=(245, 248, 255, 255), stroke_width=2, stroke_fill=(20, 48, 90, 210))
        y += line_height

    image.save(output_path)
    return output_path
