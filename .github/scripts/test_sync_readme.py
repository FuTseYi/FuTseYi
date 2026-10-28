"""Check that README content follows the homepage rather than a second template."""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import sync_readme as sync


class ReadmeTests(unittest.TestCase):
    def test_sections_and_profile_content_match_homepage(self):
        home = sync.read_home()
        result = sync.render()
        self.assertEqual([line for line in result.splitlines() if line.startswith("#")],
                         ["## About", "## Active In", "## Recent Blog"])
        for text in [home["note"], *home["paragraphs"], home["languages"],
                     *home["quotes"], *home["links"]]:
            self.assertIn(text, result)
        for title, description in home["communities"]:
            self.assertIn(title, result)
            self.assertIn(description, result)
        self.assertNotIn("assets/me.jpg", result)
        self.assertNotIn("## *Website*", result)
        self.assertNotIn("Powered by", result)

    def test_homepage_changes_propagate_without_generator_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html = (sync.ROOT / "index.html").read_text(encoding="utf-8")
            html = html.replace("Currently exploring new things, occasionally pretending I know what I’m doing.",
                                "A new profile note.")
            html = html.replace("Interested in AI, engineering, and whatever keeps me curious.", "A new focus.")
            html = html.replace(">LinkedIn</a>", ">Professional profile</a>")
            html = html.replace("Open-source learning and knowledge sharing in AI and data science.",
                                "A revised community description.")
            (root / "index.html").write_text(html, encoding="utf-8")
            shutil.copytree(sync.ROOT / "posts", root / "posts")
            with patch.object(sync, "ROOT", root):
                result = sync.render()
            for text in ("A new profile note.", "Focus: A new focus.",
                         "[Professional profile]", "A revised community description."):
                self.assertIn(text, result)

    def test_recent_posts_limit_and_drafts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "posts").mkdir()
            for i in range(1, 6):
                (root / "posts" / f"post-{i}.md").write_text(
                    f"---\ntitle: Post {i}\ndate: 2020-01-0{i}\ndraft: {'true' if i == 5 else 'false'}\n---\nText", encoding="utf-8")
            with patch.object(sync, "ROOT", root):
                self.assertEqual([entry[1] for entry in sync.read_post_entries()],
                                 ["post-4", "post-3", "post-2"])


if __name__ == "__main__":
    unittest.main()
