"""Verify portable site generation under an unrelated repository name and domain."""
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from asset_urls import site_url

ROOT = Path(__file__).resolve().parents[2]


class SitePortabilityTests(unittest.TestCase):
    def test_canonical_origin_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "index.html"
            for canonical, expected in (
                ("https://example.org/", "https://example.org"),
                ("https://www.example.org/", "https://www.example.org"),
            ):
                source.write_text(f'<link rel="canonical" href="{canonical}">', encoding="utf-8")
                self.assertEqual(site_url(root), expected)
            for canonical in ("http://example.org/", "https://example.org/path/",
                              "https://example.org/?test=1"):
                source.write_text(f'<link rel="canonical" href="{canonical}">', encoding="utf-8")
                with self.assertRaises(ValueError):
                    site_url(root)

    def test_full_build_uses_alternate_origin(self):
        # A new checkout name and unrelated HTTPS origin must not change the build.
        import preview
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "renamed-private-website"
            root.mkdir()
            for name in ("index.html", "robots.txt"):
                shutil.copy2(ROOT / name, root / name)
            for name in ("posts", "assets", ".github/scripts"):
                shutil.copytree(ROOT / name, root / name)
            home = root / "index.html"
            home.write_text(home.read_text(encoding="utf-8").replace(
                'href="https://futseyi.github.io/"',
                'href="https://portable.example.org/"', 1), encoding="utf-8")
            snapshot = root / "_site/contributions.json"
            snapshot.parent.mkdir()
            snapshot.write_text(json.dumps({
                "updated_at": datetime.now(timezone.utc).isoformat(), "entries": []
            }), encoding="utf-8")
            preview.assemble(root)
            site = root / "_site"
            self.assertIn('https://portable.example.org/', (site / "index.html").read_text(encoding="utf-8"))
            self.assertIn('https://portable.example.org/blog/', (site / "blog/index.html").read_text(encoding="utf-8"))
            self.assertIn('https://portable.example.org/blog/', (site / "sitemap.xml").read_text(encoding="utf-8"))
            self.assertIn('Sitemap: https://portable.example.org/sitemap.xml',
                          (site / "robots.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
