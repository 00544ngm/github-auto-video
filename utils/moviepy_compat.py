from __future__ import annotations

from typing import Any


try:  # MoviePy 1.x
    from moviepy.editor import (  # type: ignore
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        concatenate_audioclips,
        concatenate_videoclips,
    )
except Exception:  # MoviePy 2.x
    from moviepy import (  # type: ignore
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        concatenate_audioclips,
        concatenate_videoclips,
    )


def with_duration(clip: Any, duration: float) -> Any:
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def with_position(clip: Any, position: Any) -> Any:
    if hasattr(clip, "with_position"):
        return clip.with_position(position)
    return clip.set_position(position)


def with_start(clip: Any, start: float) -> Any:
    if hasattr(clip, "with_start"):
        return clip.with_start(start)
    return clip.set_start(start)


def with_audio(clip: Any, audio: Any) -> Any:
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)


def resized(clip: Any, value: Any) -> Any:
    if hasattr(clip, "resized"):
        return clip.resized(value)
    return clip.resize(value)


def with_opacity(clip: Any, opacity: float) -> Any:
    if hasattr(clip, "with_opacity"):
        return clip.with_opacity(opacity)
    return clip.set_opacity(opacity)
