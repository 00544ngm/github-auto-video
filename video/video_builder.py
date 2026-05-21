from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image

from config import Settings, load_settings
from models import AudioSegment, SubtitleCue
from utils.files import ensure_dir
from utils.moviepy_compat import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_audioclips,
    concatenate_videoclips,
    resized,
    with_audio,
    with_duration,
    with_opacity,
    with_position,
    with_start,
)
from video.effects import apply_default_motion
from video.subtitle import render_subtitle_image


class VideoBuildError(RuntimeError):
    pass


def fit_image_to_canvas(path: Path, output_path: Path, size: Tuple[int, int]) -> Path:
    ensure_dir(output_path.parent)
    width, height = size
    image = Image.open(path).convert("RGB")
    image_ratio = image.width / image.height
    target_ratio = width / height

    if image_ratio > target_ratio:
        new_height = height
        new_width = int(height * image_ratio)
    else:
        new_width = width
        new_height = int(width / image_ratio)

    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = max(0, (new_width - width) // 2)
    top = max(0, (new_height - height) // 2)
    image = image.crop((left, top, left + width, top + height))
    image.save(output_path, quality=95)
    return output_path


def _scene_durations(total_duration: float, scene_count: int) -> List[float]:
    if scene_count <= 0:
        return []
    base = max(total_duration / scene_count, 1.5)
    return [base for _ in range(scene_count)]


def _build_audio_track(segments: Sequence[AudioSegment]):
    clips = [AudioFileClip(segment.path) for segment in segments]
    if not clips:
        raise VideoBuildError("No audio segments were provided")
    if len(clips) == 1:
        return clips[0]
    return concatenate_audioclips(clips)


def _build_subtitle_clips(
    cues: Sequence[SubtitleCue],
    temp_dir: Path,
    settings: Settings,
) -> list:
    subtitle_clips = []
    for cue in cues:
        image_path = temp_dir / f"subtitle_{cue.index:03}.png"
        render_subtitle_image(
            cue.text,
            image_path,
            size=(settings.video_width, 260),
            font_size=58,
            font_path=settings.default_font_path,
            fonts_dir=settings.fonts_dir,
        )
        clip = ImageClip(str(image_path))
        clip = with_duration(clip, max(0.2, cue.end - cue.start))
        clip = with_start(clip, cue.start)
        clip = with_position(clip, ("center", settings.video_height - 300))
        subtitle_clips.append(clip)
    return subtitle_clips


def _bgm_clip(settings: Settings, duration: float):
    bgm_path = settings.default_bgm_path
    if not bgm_path:
        return None
    try:
        clip = AudioFileClip(str(bgm_path))
        if clip.duration < duration:
            loops = int(duration // clip.duration) + 1
            clip = concatenate_audioclips([clip] * loops)
        clip = clip.subclip(0, duration) if hasattr(clip, "subclip") else clip.subclipped(0, duration)
        if hasattr(clip, "volumex"):
            return clip.volumex(0.12)
        return clip.with_volume_scaled(0.12)
    except Exception:
        return None


def build_video(
    image_paths: Sequence[Path],
    audio_segments: Sequence[AudioSegment],
    subtitle_cues: Sequence[SubtitleCue],
    output_path: Path,
    settings: Optional[Settings] = None,
) -> Path:
    settings = settings or load_settings()
    ensure_dir(output_path.parent)
    temp_dir = ensure_dir(output_path.parent / "_render_cache")
    size = (settings.video_width, settings.video_height)

    if not image_paths:
        raise VideoBuildError("No images were provided for video rendering")

    audio = _build_audio_track(audio_segments)
    total_duration = float(audio.duration or sum(segment.duration for segment in audio_segments))
    durations = _scene_durations(total_duration, len(image_paths))

    scene_clips = []
    for index, (image_path, duration) in enumerate(zip(image_paths, durations), start=1):
        fitted = fit_image_to_canvas(image_path, temp_dir / f"scene_{index:03}.jpg", size)
        clip = ImageClip(str(fitted))
        clip = with_duration(clip, duration)
        clip = resized(clip, size)
        if settings.video_motion_mode == "full":
            clip = apply_default_motion(clip, index)
        scene_clips.append(clip)

    video = concatenate_videoclips(scene_clips, method="compose")
    if video.duration > total_duration:
        video = video.subclip(0, total_duration) if hasattr(video, "subclip") else video.subclipped(0, total_duration)

    subtitle_clips = _build_subtitle_clips(subtitle_cues, temp_dir, settings)
    composite_layers = [video, *subtitle_clips]
    composite = CompositeVideoClip(composite_layers, size=size)

    bgm = _bgm_clip(settings, total_duration)
    if bgm is not None:
        audio = CompositeAudioClip([audio, bgm])
    composite = with_audio(composite, audio)

    try:
        composite.write_videofile(
            str(output_path),
            fps=settings.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            ffmpeg_params=["-pix_fmt", "yuv420p"],
        )
    finally:
        for clip in scene_clips:
            try:
                clip.close()
            except Exception:
                pass
        for clip in subtitle_clips:
            try:
                clip.close()
            except Exception:
                pass
        try:
            video.close()
        except Exception:
            pass
        try:
            composite.close()
        except Exception:
            pass
        try:
            audio.close()
        except Exception:
            pass

    return output_path
