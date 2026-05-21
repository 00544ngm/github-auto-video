from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional convenience dependency
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None or value == "" else value


def _env_int(name: str, default: int) -> int:
    value = _env(name, "")
    if value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = _env(name, "")
    if value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name, "")
    if value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    project_root: Path
    output_dir: Path
    assets_dir: Path
    prompts_dir: Path
    bgm_dir: Path
    fonts_dir: Path
    overlays_dir: Path
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    edge_tts_voice: str
    edge_tts_rate: str
    edge_tts_pitch: str
    edge_tts_volume: str
    ffmpeg_binary: str
    request_timeout: float
    request_retries: int
    user_agent: str
    video_width: int
    video_height: int
    fps: int
    video_motion_mode: str
    dry_run: bool

    @property
    def prompt_template_path(self) -> Path:
        return self.prompts_dir / "prompt_template.txt"

    @property
    def default_bgm_path(self) -> Optional[Path]:
        configured = _env("BGM_PATH", "")
        if configured:
            path = Path(configured)
            return path if path.exists() else None
        candidates = sorted(self.bgm_dir.glob("*"))
        return candidates[0] if candidates else None

    @property
    def default_font_path(self) -> Optional[Path]:
        configured = _env("FONT_PATH", "")
        if configured:
            path = Path(configured)
            return path if path.exists() else None
        candidates: List[Path] = []
        for pattern in ("*.ttf", "*.otf", "*.ttc"):
            candidates.extend(sorted(self.fonts_dir.glob(pattern)))
        return candidates[0] if candidates else None

    def ensure_directories(self) -> None:
        for path in (
            self.output_dir,
            self.assets_dir,
            self.bgm_dir,
            self.fonts_dir,
            self.overlays_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")

    assets_dir = PROJECT_ROOT / "assets"
    settings = Settings(
        project_root=PROJECT_ROOT,
        output_dir=Path(_env("OUTPUT_DIR", str(PROJECT_ROOT / "output"))),
        assets_dir=assets_dir,
        prompts_dir=PROJECT_ROOT / "prompts",
        bgm_dir=assets_dir / "bgm",
        fonts_dir=assets_dir / "fonts",
        overlays_dir=assets_dir / "overlays",
        deepseek_api_key=_env("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        deepseek_model=_env("DEEPSEEK_MODEL", "deepseek-chat"),
        edge_tts_voice=_env("EDGE_TTS_VOICE", "zh-CN-YunxiNeural"),
        edge_tts_rate=_env("EDGE_TTS_RATE", "+0%"),
        edge_tts_pitch=_env("EDGE_TTS_PITCH", "+0Hz"),
        edge_tts_volume=_env("EDGE_TTS_VOLUME", "+0%"),
        ffmpeg_binary=_env("FFMPEG_BINARY", "ffmpeg"),
        request_timeout=_env_float("REQUEST_TIMEOUT", 20.0),
        request_retries=_env_int("REQUEST_RETRIES", 3),
        user_agent=_env(
            "HTTP_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36",
        ),
        video_width=_env_int("VIDEO_WIDTH", 1920),
        video_height=_env_int("VIDEO_HEIGHT", 1080),
        fps=_env_int("VIDEO_FPS", 30),
        video_motion_mode=_env("VIDEO_MOTION_MODE", "fast").lower(),
        dry_run=_env_bool("DRY_RUN", False),
    )
    settings.ensure_directories()
    return settings
