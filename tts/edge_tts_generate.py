from __future__ import annotations

import asyncio
import json
import wave
from pathlib import Path
from typing import List, Optional, Tuple

from config import Settings, load_settings
from models import AudioSegment, ScriptSections
from utils.files import ensure_dir, write_json


class TTSError(RuntimeError):
    pass


def estimate_duration(text: str, chars_per_second: float = 4.6) -> float:
    clean = "".join(ch for ch in text if not ch.isspace())
    return max(1.8, len(clean) / chars_per_second)


def _write_silent_wav(path: Path, duration: float, sample_rate: int = 44100) -> None:
    ensure_dir(path.parent)
    frames = int(duration * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        chunk = b"\x00\x00" * min(frames, sample_rate)
        remaining = frames
        while remaining > 0:
            count = min(remaining, sample_rate)
            handle.writeframes(chunk[: count * 2])
            remaining -= count


async def _edge_tts_save(
    text: str,
    path: Path,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
) -> None:
    try:
        import edge_tts
    except Exception as exc:
        raise TTSError("edge-tts is not installed") from exc

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )
    await communicate.save(str(path))


def _audio_duration(path: Path) -> float:
    try:
        from moviepy.editor import AudioFileClip
    except Exception:
        try:
            from moviepy import AudioFileClip
        except Exception:
            return 0.0

    clip = AudioFileClip(str(path))
    try:
        return float(clip.duration or 0)
    finally:
        clip.close()


def script_segments(script: ScriptSections) -> List[Tuple[str, str]]:
    return [(key, text.strip()) for key, text in script.as_list() if text.strip()]


def generate_tts_for_script(
    script: ScriptSections,
    output_dir: Path,
    settings: Optional[Settings] = None,
    dry_run: bool = False,
    duration_scale: float = 1.0,
) -> List[AudioSegment]:
    settings = settings or load_settings()
    audio_dir = ensure_dir(output_dir / "audio")
    segments: List[AudioSegment] = []

    for segment_id, text in script_segments(script):
        duration = max(0.4, estimate_duration(text) * duration_scale)
        if dry_run or settings.dry_run:
            path = audio_dir / f"{segment_id}.wav"
            _write_silent_wav(path, duration)
        else:
            path = audio_dir / f"{segment_id}.mp3"
            try:
                asyncio.run(
                    _edge_tts_save(
                        text=text,
                        path=path,
                        voice=settings.edge_tts_voice,
                        rate=settings.edge_tts_rate,
                        pitch=settings.edge_tts_pitch,
                        volume=settings.edge_tts_volume,
                    )
                )
                actual_duration = _audio_duration(path)
                if actual_duration > 0:
                    duration = actual_duration
            except Exception as exc:
                raise TTSError(f"Failed to generate TTS for segment {segment_id}: {exc}") from exc

        segments.append(
            AudioSegment(
                segment_id=segment_id,
                text=text,
                path=str(path),
                duration=duration,
            )
        )

    write_json(
        audio_dir / "audio_manifest.json",
        {
            "voice": settings.edge_tts_voice,
            "rate": settings.edge_tts_rate,
            "pitch": settings.edge_tts_pitch,
            "volume": settings.edge_tts_volume,
            "segments": segments,
        },
    )
    return segments


def load_audio_manifest(path: Path) -> List[AudioSegment]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [AudioSegment(**item) for item in payload.get("segments", [])]
