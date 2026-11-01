"""Check that README content follows the homepage rather than a second template."""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import sync_readme as sync


class ReadmeTests(unittest.TestCase):
    def test_both_readme_commits_use_the_same_identity_and_message(self):
        current={"content":sync.base64.b64encode(b"old README").decode("ascii"),"sha":"previous"}
        with patch.object(sync,"request",side_effect=[current,{}]) as request:
            sync.sync_profile("new README","test-token")
        body=request.call_args.args[3]
        workflow=(sync.ROOT/".github/workflows/sync-readme.yml").read_text(encoding="utf-8")
        self.assertIn('git commit -m "'+body["message"]+'"',workflow)
        self.assertIn('git config user.name "'+body["author"]["name"]+'"',workflow)
        self.assertIn('git config user.email "'+body["author"]["email"]+'"',workflow)
        self.assertEqual(body["author"],body["committer"])
        self.assertEqual(sync.base64.b64decode(body["content"]),b"new README")

    def test_sections_and_profile_content_match_homepage(self):
        home = sync.read_home()
        result = sync.render()
        self.assertEqual([line for line in result.splitlines() if line.startswith("#")],
                         ["## About", "## Active In", "## Recent Blog"])
        for text in [home["note"], *home["paragraphs"], home["languages"],
                     *home["quotes"], *home["links"]]:
            self.assertIn(text, result)
        for title, image in home["communities"]:
            self.assertIn(sync.community_row(title, image, sync.site_url()), result)
            self.assertIn(sync.community_row(title, image, sync.site_url()), result)
        for label in ("**Focus:**", "**Lang:**", "**Motto:**"):
            self.assertIn(label, result)
        for dt, _, _ in sync.read_post_entries():
            self.assertNotIn(dt.strftime("%Y.%m.%d"), result)
        self.assertNotIn("assets/images/profile/me.jpg", result)
        self.assertNotIn("## *Website*", result)
        self.assertNotIn("Powered by", result)
        ordered=["**Homepage**:",home["note"],*home["paragraphs"],
                 home["languages"],home["motto_label"],
                 *home["quotes"],*home["links"],home["badge"],"## Active In","## Recent Blog"]
        positions=[result.index(text) for text in ordered]
        self.assertEqual(positions,sorted(positions))

    def test_homepage_changes_propagate_without_generator_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html = (sync.ROOT / "index.html").read_text(encoding="utf-8")
            html = html.replace("Currently exploring new things, occasionally pretending I know what I’m doing.",
                                "A new profile note.")
            html = html.replace("Interested in AI, engineering, and whatever keeps me curious.", "A new focus.")
            html = html.replace(">LinkedIn</a>", ">Professional profile</a>")
            html = html.replace("Datawhale is an AI-focused open source organization founded in 2018.",
                                "A revised community description.")
            (root / "index.html").write_text(html, encoding="utf-8")
            shutil.copytree(sync.ROOT / "posts", root / "posts")
            with patch.object(sync, "ROOT", root):
                result = sync.render()
            for text in ("A new profile note.", "**Focus:** A new focus.",
                         "[Professional profile]"):
                self.assertIn(text, result)
            self.assertNotIn("A revised community description.", result)

    def test_website_urls_follow_repository_owner(self):
        with patch.dict(sync.os.environ, {"GITHUB_REPOSITORY": "NewOwner/NewOwner.github.io"}):
            result = sync.render()
        self.assertIn("**Homepage**: [newowner.github.io](https://newowner.github.io/)", result)
        self.assertIn("https://newowner.github.io/blog/", result)

    def test_local_website_url_follows_canonical(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(sync.os.environ, {}, clear=True):
            root = Path(directory)
            (root / "index.html").write_text('<link rel="canonical" href="https://another.github.io/">')
            with patch.object(sync, "ROOT", root):
                self.assertEqual(sync.site_url(), "https://another.github.io")

    def test_recent_posts_sort_by_date_without_publication_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "posts").mkdir()
            for i in range(1, 6):
                (root / "posts" / f"post-{i}").mkdir()
                (root / "posts" / f"post-{i}" / "index.md").write_text(
                    f"---\ntitle: Post {i}\ndate: 2099-01-0{i}\ndraft: {'true' if i == 5 else 'false'}\n---\nText", encoding="utf-8")
            with patch.object(sync, "ROOT", root):
                self.assertEqual([entry[1] for entry in sync.read_post_entries()],
                                 ["post-5", "post-4", "post-3"])


if __name__ == "__main__":
    unittest.main()
