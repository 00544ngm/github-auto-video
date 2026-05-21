from __future__ import annotations

import math
from typing import Any, Tuple

from utils.moviepy_compat import resized


def slow_zoom(clip: Any, zoom: float = 0.06) -> Any:
    duration = float(getattr(clip, "duration", 1) or 1)

    def scale_at(t: float) -> float:
        return 1.0 + zoom * min(max(t / duration, 0.0), 1.0)

    return resized(clip, scale_at)


def push_in(clip: Any) -> Any:
    return slow_zoom(clip, zoom=0.08)


def cinematic_pan(clip: Any, distance: int = 42) -> Any:
    duration = float(getattr(clip, "duration", 1) or 1)

    def position(t: float) -> Tuple[float, float]:
        ratio = min(max(t / duration, 0.0), 1.0)
        x = -distance * ratio
        y = -distance * 0.35 * math.sin(ratio * math.pi)
        return x, y

    if hasattr(clip, "with_position"):
        return clip.with_position(position)
    return clip.set_position(position)


def parallax(clip: Any) -> Any:
    return cinematic_pan(slow_zoom(clip, zoom=0.05), distance=28)


def fade(clip: Any, duration: float = 0.35) -> Any:
    result = clip
    try:
        result = result.fadein(duration).fadeout(duration)
    except Exception:
        try:
            result = result.with_effects([])
        except Exception:
            pass
    return result


def digital_glitch(clip: Any, intensity: float = 0.015) -> Any:
    # Lightweight deterministic jitter that avoids heavy per-frame processing.
    duration = float(getattr(clip, "duration", 1) or 1)

    def position(t: float) -> Tuple[int, int]:
        burst = 1 if int(t * 12) % 17 == 0 else 0
        shift = int(18 * intensity * 100 * burst * math.sin(t * 120))
        return shift, 0

    if duration < 0.5:
        return clip
    if hasattr(clip, "with_position"):
        return clip.with_position(position)
    return clip.set_position(position)


def apply_default_motion(clip: Any, scene_index: int) -> Any:
    effects = [push_in, parallax, cinematic_pan]
    result = effects[(scene_index - 1) % len(effects)](clip)
    if scene_index % 3 == 0:
        result = digital_glitch(result)
    return fade(result)
