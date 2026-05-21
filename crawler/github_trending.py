from __future__ import annotations

import re
import time
from typing import List, Optional, Tuple
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from config import load_settings
from models import TrendingRepo


VALID_SINCE = {"daily", "weekly", "monthly"}
STAR_RE = re.compile(r"([\d,.]+)\s*([kKmM]?)")


class GitHubTrendingError(RuntimeError):
    pass


def normalize_stars(value: str) -> int:
    text = value.strip().replace(",", "")
    match = STAR_RE.search(text)
    if not match:
        return 0
    number = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    return int(number)


def build_trending_url(language: Optional[str] = None) -> str:
    if language:
        return f"https://github.com/trending/{quote(language.strip('/'))}"
    return "https://github.com/trending"


def _repo_parts(anchor_text: str, href: str) -> Tuple[str, str]:
    parts = [part.strip() for part in anchor_text.replace("\n", " ").split("/") if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1].replace(" ", "")

    path_parts = [part for part in href.strip("/").split("/") if part]
    if len(path_parts) >= 2:
        return path_parts[0], path_parts[1]
    raise GitHubTrendingError(f"Could not parse repository identity from href={href!r}")


def parse_trending_html(html: str, limit: int = 3) -> List[TrendingRepo]:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.Box-row")
    if not articles:
        articles = soup.select("article")
    if not articles:
        raise GitHubTrendingError("GitHub Trending page did not contain repository cards")

    repos: List[TrendingRepo] = []
    for article in articles:
        anchor = article.select_one("h2 a") or article.select_one("h3 a")
        if anchor is None:
            continue

        href = anchor.get("href", "").strip()
        if not href:
            continue

        author, name = _repo_parts(anchor.get_text(" ", strip=True), href)
        description_node = article.select_one("p")
        description = description_node.get_text(" ", strip=True) if description_node else ""

        stars_node = None
        for candidate in article.select("a"):
            candidate_href = candidate.get("href", "")
            if candidate_href.endswith("/stargazers") or "/stargazers" in candidate_href:
                stars_node = candidate
                break

        stars = stars_node.get_text(" ", strip=True) if stars_node else "0"
        stars_count = normalize_stars(stars)
        url = urljoin("https://github.com", href)

        repos.append(
            TrendingRepo(
                name=name,
                author=author,
                stars=stars,
                stars_count=stars_count,
                description=description,
                url=url,
            )
        )

    repos.sort(key=lambda repo: repo.stars_count, reverse=True)
    return repos[:limit]


def fetch_trending(
    language: Optional[str] = None,
    since: str = "daily",
    limit: int = 3,
    session: Optional[requests.Session] = None,
    timeout: Optional[float] = None,
    retries: Optional[int] = None,
    user_agent: Optional[str] = None,
) -> List[TrendingRepo]:
    if since not in VALID_SINCE:
        raise ValueError(f"since must be one of {sorted(VALID_SINCE)}")

    settings = load_settings()
    timeout = settings.request_timeout if timeout is None else timeout
    retries = settings.request_retries if retries is None else retries
    user_agent = settings.user_agent if user_agent is None else user_agent

    client = session or requests.Session()
    url = build_trending_url(language)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    }

    last_error: Optional[Exception] = None
    for attempt in range(1, max(retries, 1) + 1):
        try:
            response = client.get(url, params={"since": since}, headers=headers, timeout=timeout)
            response.raise_for_status()
            return parse_trending_html(response.text, limit=limit)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 6))

    raise GitHubTrendingError(f"Failed to fetch GitHub Trending: {last_error}") from last_error
