"""Verify final local links, including absolute canonical-host links and srcset."""
import tempfile
import unittest
from pathlib import Path

from scripts.site_verify import verify


class FinalArtifactTests(unittest.TestCase):
    def test_local_and_absolute_site_links_share_one_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "blog").mkdir()
            (root / "assets").mkdir()
            (root / "assets/photo.png").write_bytes(b"photo")
            (root / "index.html").write_text(
                '<link rel="canonical" href="https://example.org/">'
                '<a href="https://example.org/blog/#section">Blog</a>'
                '<meta property="og:image" content="https://example.org/assets/photo.png">',
                encoding="utf-8")
            blog = root / "blog/index.html"
            blog.write_text('<div id="section"></div><img srcset="/assets/photo.png 1x">', encoding="utf-8")
            self.assertEqual(verify(root), 2)
            blog.write_text('<div id="section"></div><img srcset="/assets/missing.png 1x">', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing local resource"):
                verify(root)
            blog.write_text('<div id="section"></div><img src="http://example.org/assets/photo.png">', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-HTTPS"):
                verify(root)


if __name__ == "__main__":
    unittest.main()
