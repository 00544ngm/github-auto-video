from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import Settings, load_settings
from crawler.github_trending import fetch_trending
from images.generate_prompt import (
    build_image_prompts,
    build_thumbnail_prompt,
    write_prompt_manifest,
)
from images.local_render import render_scene_image, render_thumbnail
from llm.deepseek_generate import generate_video_plan
from models import GenerationRequest, RunResult, TrendingRepo, model_to_dict
from tts.edge_tts_generate import generate_tts_for_script
from utils.files import ensure_dir, timestamped_run_id, write_json
from video.subtitle import build_subtitle_cues, write_srt, write_subtitle_manifest
from video.video_builder import build_video


class PipelineError(RuntimeError):
    pass


def create_run_dir(settings: Settings, output_name: Optional[str] = None) -> Tuple[str, Path]:
    run_id = timestamped_run_id(output_name)
    run_dir = ensure_dir(settings.output_dir / run_id)
    ensure_dir(run_dir / "images")
    ensure_dir(run_dir / "subtitles")
    return run_id, run_dir


def _default_repos() -> List[TrendingRepo]:
    return [
        TrendingRepo(
            name="agentic-engine",
            author="open-source-labs",
            stars="12,400",
            stars_count=12400,
            description="A framework for building reliable AI agents with workflow orchestration.",
            url="https://github.com/open-source-labs/agentic-engine",
        ),
        TrendingRepo(
            name="fast-code-index",
            author="devtools-ai",
            stars="9,870",
            stars_count=9870,
            description="A high-performance code search and semantic indexing toolkit.",
            url="https://github.com/devtools-ai/fast-code-index",
        ),
        TrendingRepo(
            name="local-vision-stack",
            author="future-ui",
            stars="7,530",
            stars_count=7530,
            description="Local-first computer vision pipelines for desktop automation.",
            url="https://github.com/future-ui/local-vision-stack",
        ),
    ]


def _resolve_repos(request: GenerationRequest, settings: Settings) -> List[TrendingRepo]:
    if request.repos:
        return request.repos[: request.limit]
    if request.dry_run or settings.dry_run:
        return _default_repos()[: request.limit]
    return fetch_trending(
        language=request.language_filter,
        since=request.since,
        limit=request.limit,
    )


def _render_local_images(
    run_dir: Path,
    plan_title: str,
    prompts,
    thumbnail_prompt: str,
    settings: Settings,
) -> Tuple[List[Path], Path]:
    image_dir = ensure_dir(run_dir / "images")
    image_paths: List[Path] = []
    for prompt in prompts:
        output_path = image_dir / f"scene_{prompt.scene_index:03}.jpg"
        render_scene_image(
            title=prompt.title,
            subtitle=plan_title,
            prompt=prompt.prompt,
            output_path=output_path,
            size=(settings.video_width, settings.video_height),
            font_path=settings.default_font_path,
            fonts_dir=settings.fonts_dir,
        )
        prompt.output_path = str(output_path)
        image_paths.append(output_path)

    thumbnail_path = run_dir / "thumbnail.png"
    render_thumbnail(
        title=plan_title,
        prompt=thumbnail_prompt,
        output_path=thumbnail_path,
        size=(settings.video_width, settings.video_height),
        font_path=settings.default_font_path,
        fonts_dir=settings.fonts_dir,
    )
    return image_paths, thumbnail_path


def run_generation(
    request: Optional[GenerationRequest] = None,
    settings: Optional[Settings] = None,
) -> RunResult:
    settings = settings or load_settings()
    request = request or GenerationRequest(dry_run=settings.dry_run)
    run_id, run_dir = create_run_dir(settings, request.output_name)
    created_at = datetime.now()
    result = RunResult(
        run_id=run_id,
        status="running",
        created_at=created_at,
        output_dir=str(run_dir),
    )

    try:
        repos = _resolve_repos(request, settings)
        trending_path = write_json(run_dir / "trending.json", repos)
        result.trending_path = str(trending_path)

        plan = generate_video_plan(repos, settings=settings, dry_run=request.dry_run)
        plan_path = write_json(run_dir / "video_plan.json", plan)
        result.plan_path = str(plan_path)

        image_prompts = build_image_prompts(plan, repos, min_count=max(3, len(repos)))
        thumbnail_prompt = build_thumbnail_prompt(plan, repos)
        prompt_path = write_prompt_manifest(run_dir / "image_prompts.json", image_prompts, thumbnail_prompt)
        result.prompt_path = str(prompt_path)

        image_paths, thumbnail_path = _render_local_images(
            run_dir=run_dir,
            plan_title=plan.video_title,
            prompts=image_prompts,
            thumbnail_prompt=thumbnail_prompt,
            settings=settings,
        )
        result.thumbnail_path = str(thumbnail_path)

        audio_segments = generate_tts_for_script(
            plan.script,
            run_dir,
            settings=settings,
            dry_run=request.dry_run,
            duration_scale=0.01 if request.dry_run else 1.0,
        )

        cues = build_subtitle_cues(audio_segments)
        subtitle_dir = ensure_dir(run_dir / "subtitles")
        srt_path = write_srt(subtitle_dir / "subtitles.srt", cues)
        write_subtitle_manifest(subtitle_dir / "subtitle_manifest.json", cues)
        result.subtitle_path = str(srt_path)

        video_name = request.output_name or "final"
        video_path = run_dir / f"{video_name}.mp4"
        build_video(
            image_paths=image_paths,
            audio_segments=audio_segments,
            subtitle_cues=cues,
            output_path=video_path,
            settings=settings,
        )
        result.video_path = str(video_path)
        result.status = "completed"
        result.metadata = {
            "repos": [model_to_dict(repo) for repo in repos],
            "video_title": plan.video_title,
            "dry_run": request.dry_run or settings.dry_run,
            "image_count": len(image_paths),
            "audio_segments": len(audio_segments),
            "subtitle_cues": len(cues),
        }
    except Exception as exc:
        result.status = "failed"
        result.error = str(exc)
        write_json(run_dir / "run_metadata.json", result)
        raise

    write_json(run_dir / "run_metadata.json", result)
    return result


def run_batch(
    requests: List[GenerationRequest],
    settings: Optional[Settings] = None,
) -> List[RunResult]:
    settings = settings or load_settings()
    results: List[RunResult] = []
    for index, request in enumerate(requests, start=1):
        if not request.output_name:
            request.output_name = f"batch-{index:03}"
        try:
            results.append(run_generation(request=request, settings=settings))
        except Exception as exc:
            run_id, run_dir = create_run_dir(settings, f"failed-batch-{index:03}")
            failed = RunResult(
                run_id=run_id,
                status="failed",
                created_at=datetime.now(),
                output_dir=str(run_dir),
                error=str(exc),
            )
            write_json(run_dir / "run_metadata.json", failed)
            results.append(failed)
    return results


def read_run(run_id: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    settings = settings or load_settings()
    metadata_path = settings.output_dir / run_id / "run_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")
    import json

    return json.loads(metadata_path.read_text(encoding="utf-8"))
