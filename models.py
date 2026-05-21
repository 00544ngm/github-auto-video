from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, HttpUrl


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


class TrendingRepo(BaseModel):
    name: str
    author: str
    stars: str
    stars_count: int = 0
    description: str = ""
    url: HttpUrl


class ScriptSections(BaseModel):
    opening: str
    middle: str
    ending: str

    def as_list(self) -> List[Tuple[str, str]]:
        return [
            ("opening", self.opening),
            ("middle", self.middle),
            ("ending", self.ending),
        ]


class VideoPlan(BaseModel):
    video_title: str
    hook: str
    core_points: List[str] = Field(default_factory=list)
    script: ScriptSections
    image_prompts: List[str] = Field(default_factory=list)
    thumbnail_prompt: str = ""
    bgm_style: str = ""
    editing_style: str = ""


class ImagePrompt(BaseModel):
    scene_index: int
    title: str
    prompt: str
    output_path: Optional[str] = None


class AudioSegment(BaseModel):
    segment_id: str
    text: str
    path: str
    duration: float


class SubtitleCue(BaseModel):
    index: int
    start: float
    end: float
    text: str


class GenerationRequest(BaseModel):
    language_filter: Optional[str] = None
    since: str = "daily"
    limit: int = 3
    narration_language: str = "zh-CN"
    dry_run: bool = False
    output_name: Optional[str] = None
    repos: Optional[List[TrendingRepo]] = None


class BatchGenerationRequest(BaseModel):
    jobs: List[GenerationRequest] = Field(default_factory=list)


class RunResult(BaseModel):
    run_id: str
    status: str
    created_at: datetime
    output_dir: str
    trending_path: Optional[str] = None
    plan_path: Optional[str] = None
    prompt_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir)
