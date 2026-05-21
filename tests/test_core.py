from __future__ import annotations

import unittest

from crawler.github_trending import normalize_stars, parse_trending_html
from images.generate_prompt import STYLE_SUFFIX, enforce_style
from models import AudioSegment
from video.subtitle import build_subtitle_cues, format_srt_time


class CoreModuleTests(unittest.TestCase):
    def test_normalize_stars(self) -> None:
        self.assertEqual(normalize_stars("1,234"), 1234)
        self.assertEqual(normalize_stars("12.3k"), 12300)
        self.assertEqual(normalize_stars("1.2M"), 1200000)

    def test_parse_trending_html(self) -> None:
        html = """
        <article class="Box-row">
          <h2><a href="/octo/demo">octo / demo</a></h2>
          <p>Demo repository</p>
          <a href="/octo/demo/stargazers">1,234</a>
        </article>
        """
        repos = parse_trending_html(html)
        self.assertEqual(repos[0].author, "octo")
        self.assertEqual(repos[0].name, "demo")
        self.assertEqual(repos[0].stars_count, 1234)

    def test_enforce_style(self) -> None:
        prompt = enforce_style("AI coding launch film")
        self.assertIn("AI coding launch film", prompt)
        self.assertIn(STYLE_SUFFIX, prompt)

    def test_subtitle_cues(self) -> None:
        cues = build_subtitle_cues(
            [
                AudioSegment(
                    segment_id="opening",
                    text="今天 GitHub Trending 出现了三个值得关注的科技项目。",
                    path="opening.wav",
                    duration=4.0,
                )
            ]
        )
        self.assertTrue(cues)
        self.assertEqual(cues[0].start, 0)
        self.assertGreater(cues[-1].end, 0)
        self.assertEqual(format_srt_time(1.25), "00:00:01,250")


if __name__ == "__main__":
    unittest.main()
