# GitHub Trending AI Tech Video Automation

Python 3.10 project for generating Chinese AI tech short videos from GitHub Trending repositories.

## What It Does

```text
GitHub Trending
-> top repositories
-> DeepSeek/OpenAI-compatible video plan
-> AI image prompts + local tech-style fallback images
-> Edge-TTS narration
-> subtitles
-> MoviePy/FFmpeg video render
-> MP4 + thumbnail + JSON run records
```

## Setup

```powershell
& 'D:\Miniconda3\envs\ai_dev\python.exe' -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DEEPSEEK_API_KEY` in `.env` for live LLM generation. Without it, `--dry-run` uses built-in sample repositories and local generated visuals.

## Run Locally

Quick smoke test:

```powershell
$env:VIDEO_WIDTH='640'
$env:VIDEO_HEIGHT='360'
$env:VIDEO_FPS='15'
& 'D:\Miniconda3\envs\ai_dev\python.exe' main.py --dry-run --output-name smoke
```

Production-style local run:

```powershell
& 'D:\Miniconda3\envs\ai_dev\python.exe' main.py --output-name github-trending-video
```

FastAPI server:

```powershell
& 'D:\Miniconda3\envs\ai_dev\python.exe' -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Useful endpoints:

```text
GET  /health
GET  /trending
POST /generate
POST /generate/batch
GET  /runs/{run_id}
```

## Output

Each run writes an isolated folder under `output/`:

```text
output/<run_id>/
  trending.json
  video_plan.json
  image_prompts.json
  audio/
  subtitles/
  images/
  thumbnail.png
  <output_name>.mp4
  run_metadata.json
```

## Notes

- Default output is 1920x1080 at 30 fps.
- `VIDEO_MOTION_MODE=fast` is optimized for batch throughput.
- Set `VIDEO_MOTION_MODE=full` to enable heavier per-frame cinematic motion effects.
- Image generation providers are intentionally abstracted; current MVP exports prompts and uses local tech-style fallback images so the video pipeline remains runnable.
