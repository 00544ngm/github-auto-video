from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException

from config import load_settings
from crawler.github_trending import fetch_trending
from models import BatchGenerationRequest, GenerationRequest, model_to_dict
from services.pipeline import read_run, run_batch, run_generation


app = FastAPI(
    title="GitHub Trending AI Tech Video Automation",
    version="0.1.0",
    description="Generate Chinese AI tech short videos from GitHub Trending projects.",
)


@app.get("/health")
def health() -> Dict[str, Any]:
    settings = load_settings()
    return {
        "status": "ok",
        "output_dir": str(settings.output_dir),
        "dry_run": settings.dry_run,
        "video": {
            "width": settings.video_width,
            "height": settings.video_height,
            "fps": settings.fps,
        },
    }


@app.get("/trending")
def trending(language: Optional[str] = None, since: str = "daily", limit: int = 3) -> List[Dict[str, Any]]:
    try:
        return [model_to_dict(repo) for repo in fetch_trending(language=language, since=since, limit=limit)]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/generate")
def generate(request: GenerationRequest) -> Dict[str, Any]:
    try:
        return model_to_dict(run_generation(request))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate/batch")
def generate_batch(request: BatchGenerationRequest) -> List[Dict[str, Any]]:
    jobs = request.jobs or [GenerationRequest(dry_run=True, output_name="batch-default")]
    return [model_to_dict(result) for result in run_batch(jobs)]


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    try:
        return read_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def run_system(dry_run: bool = False, output_name: Optional[str] = None) -> Dict[str, Any]:
    request = GenerationRequest(dry_run=dry_run, output_name=output_name)
    return model_to_dict(run_generation(request))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate GitHub Trending AI tech short videos.")
    parser.add_argument("--dry-run", action="store_true", help="Use built-in sample data and silent audio.")
    parser.add_argument("--output-name", default=None, help="Optional output video/run name.")
    parser.add_argument("--language", default=None, help="Optional GitHub Trending language filter.")
    parser.add_argument("--since", default="daily", choices=["daily", "weekly", "monthly"])
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    request = GenerationRequest(
        language_filter=args.language,
        since=args.since,
        limit=args.limit,
        dry_run=args.dry_run,
        output_name=args.output_name,
    )
    result = run_generation(request)
    print(json.dumps(model_to_dict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
