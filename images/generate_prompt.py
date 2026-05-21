from __future__ import annotations

from pathlib import Path
from typing import List

from models import ImagePrompt, TrendingRepo, VideoPlan, model_to_dict
from utils.files import write_json


STYLE_SUFFIX = (
    "black background, blue and purple neon, futuristic technology UI, HUD, "
    "cinematic composition, ultra realistic, future technology, volumetric lighting, "
    "8k, 16:9"
)


def enforce_style(prompt: str) -> str:
    prompt = " ".join(prompt.strip().split())
    if not prompt:
        prompt = "futuristic software launch scene"
    lower = prompt.lower()
    required = ["black background", "blue", "purple", "hud", "cinematic", "16:9"]
    if all(token in lower for token in required):
        return prompt
    return f"{prompt}, {STYLE_SUFFIX}"


def fallback_prompt_for_repo(repo: TrendingRepo) -> str:
    description = repo.description or "developer tool gaining strong momentum"
    return (
        f"Frontier report visualization of GitHub project {repo.author}/{repo.name}, "
        f"concept: {description}, trend signal card, code telemetry panel, repository radar, "
        f"developer workflow dashboard, {STYLE_SUFFIX}"
    )


def build_image_prompts(
    plan: VideoPlan,
    repos: List[TrendingRepo],
    min_count: int = 3,
) -> List[ImagePrompt]:
    raw_prompts = list(plan.image_prompts)
    repo_prompts = [fallback_prompt_for_repo(repo) for repo in repos]
    while len(raw_prompts) < min_count and repo_prompts:
        raw_prompts.append(repo_prompts[len(raw_prompts) % len(repo_prompts)])

    prompts: List[ImagePrompt] = []
    for index, raw_prompt in enumerate(raw_prompts[: max(min_count, len(raw_prompts))], start=1):
        title = repos[index - 1].name if index - 1 < len(repos) else f"Scene {index}"
        prompts.append(
            ImagePrompt(
                scene_index=index,
                title=title,
                prompt=enforce_style(raw_prompt),
            )
        )
    return prompts


def build_thumbnail_prompt(plan: VideoPlan, repos: List[TrendingRepo]) -> str:
    names = ", ".join(f"{repo.author}/{repo.name}" for repo in repos)
    base = plan.thumbnail_prompt or f"GitHub trend briefing thumbnail for projects: {names}"
    return enforce_style(base)


def write_prompt_manifest(
    path: Path,
    prompts: List[ImagePrompt],
    thumbnail_prompt: str,
) -> Path:
    return write_json(
        path,
        {
            "image_prompts": [model_to_dict(prompt) for prompt in prompts],
            "thumbnail_prompt": thumbnail_prompt,
        },
    )
