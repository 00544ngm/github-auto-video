from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

import requests

from config import Settings, load_settings
from models import ScriptSections, TrendingRepo, VideoPlan, model_to_dict


class DeepSeekGenerationError(RuntimeError):
    pass


def _validate_video_plan(payload: Dict[str, Any]) -> VideoPlan:
    if hasattr(VideoPlan, "model_validate"):
        return VideoPlan.model_validate(payload)
    return VideoPlan.parse_obj(payload)


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def load_prompt_template(path: Optional[Path] = None) -> str:
    settings = load_settings()
    template_path = path or settings.prompt_template_path
    return template_path.read_text(encoding="utf-8")


def render_prompt(repos: List[TrendingRepo], template_path: Optional[Path] = None) -> str:
    repos_json = json.dumps(
        [model_to_dict(repo) for repo in repos],
        ensure_ascii=False,
        indent=2,
        default=str,
    )
    template = Template(load_prompt_template(template_path))
    return template.safe_substitute(repos_json=repos_json)


@dataclass
class DeepSeekClient:
    api_key: str
    base_url: str
    model: str
    timeout: float = 20.0
    retries: int = 3
    session: requests.Session = field(default_factory=requests.Session)

    @classmethod
    def from_settings(cls, settings: Optional[Settings] = None) -> "DeepSeekClient":
        settings = settings or load_settings()
        return cls(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            timeout=settings.request_timeout,
            retries=settings.request_retries,
        )

    def chat(self, prompt: str, temperature: float = 0.7) -> str:
        if not self.api_key:
            raise DeepSeekGenerationError("DEEPSEEK_API_KEY is not configured")

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {
                    "role": "system",
                    "content": "You output strict JSON only. No markdown, no comments.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        last_error: Optional[Exception] = None
        for _ in range(max(self.retries, 1)):
            try:
                response = self.session.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:
                last_error = exc

        raise DeepSeekGenerationError(f"DeepSeek request failed: {last_error}") from last_error


def fallback_video_plan(repos: List[TrendingRepo]) -> VideoPlan:
    if not repos:
        raise DeepSeekGenerationError("Cannot build fallback plan without repositories")

    repo_names = "、".join(f"{repo.author}/{repo.name}" for repo in repos)
    points = [
        f"{repo.author}/{repo.name}: {repo.description or 'GitHub Trending high-interest project'}"
        for repo in repos
    ]
    opening = (
        f"今天 GitHub Trending 冲上来三个值得盯住的项目：{repo_names}。"
        "它们不是简单的工具更新，而是开发者正在押注的新方向。"
    )
    middle_parts = [
        f"{repo.name} 目前有 {repo.stars} stars，核心看点是："
        f"{repo.description or '它正在获得开发者快速关注'}。"
        for repo in repos
    ]
    middle = " ".join(middle_parts)
    ending = (
        "如果你在寻找下一个自动化、AI 工程或开发效率方向，"
        "这三个项目值得今天就打开看一眼。"
    )
    image_prompts = [
        (
            f"Cinematic product-launch visualization for GitHub repository "
            f"{repo.author}/{repo.name}, theme: {repo.description or repo.name}"
        )
        for repo in repos
    ]

    return VideoPlan(
        video_title="GitHub 今日最值得关注的 3 个科技项目",
        hook="GitHub Trending 又出现三个高能项目，开发者的注意力正在转向这里。",
        core_points=points,
        script=ScriptSections(opening=opening, middle=middle, ending=ending),
        image_prompts=image_prompts,
        thumbnail_prompt=f"Premium tech thumbnail showing {repo_names}",
        bgm_style="low, cinematic, electronic pulse, premium launch-film energy",
        editing_style="fast hook, slow push-in, HUD overlays, restrained glitch transitions",
    )


def generate_video_plan(
    repos: List[TrendingRepo],
    settings: Optional[Settings] = None,
    dry_run: bool = False,
) -> VideoPlan:
    settings = settings or load_settings()
    if dry_run or settings.dry_run or not settings.deepseek_api_key:
        return fallback_video_plan(repos)

    client = DeepSeekClient.from_settings(settings)
    prompt = render_prompt(repos, settings.prompt_template_path)
    first_response = client.chat(prompt, temperature=0.7)
    try:
        return _validate_video_plan(_extract_json_object(first_response))
    except Exception:
        repair_prompt = (
            "Repair the following model output into valid JSON matching the required schema. "
            "Return JSON only:\n\n"
            f"{first_response}"
        )
        repaired = client.chat(repair_prompt, temperature=0.1)
        try:
            return _validate_video_plan(_extract_json_object(repaired))
        except Exception as exc:
            raise DeepSeekGenerationError("DeepSeek returned invalid VideoPlan JSON") from exc
