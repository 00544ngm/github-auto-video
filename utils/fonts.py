from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from PIL import ImageFont


SYSTEM_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
]


def resolve_font_path(
    preferred: Optional[Union[str, Path]] = None,
    fonts_dir: Optional[Path] = None,
) -> Optional[Path]:
    candidates: List[Path] = []
    if preferred:
        candidates.append(Path(preferred))
    if fonts_dir and fonts_dir.exists():
        for pattern in ("*.ttf", "*.otf", "*.ttc"):
            candidates.extend(sorted(fonts_dir.glob(pattern)))
    candidates.extend(SYSTEM_FONT_CANDIDATES)

    for path in candidates:
        if path.exists():
            return path
    return None


def load_font(
    size: int,
    preferred: Optional[Union[str, Path]] = None,
    fonts_dir: Optional[Path] = None,
) -> ImageFont.ImageFont:
    font_path = resolve_font_path(preferred=preferred, fonts_dir=fonts_dir)
    if font_path:
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()
