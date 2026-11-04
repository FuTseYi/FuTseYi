"""The site chrome is prepared once while metadata stays page-specific."""
import unittest
from unittest.mock import patch

import build


class LayoutTests(unittest.TestCase):
    def test_shared_layout_is_read_once_for_multiple_pages(self):
        with patch.object(build, "version_assets", wraps=build.version_assets) as version:
            shared = build.shared_layout()
            first = build.layout("First", "First page", build.SITE + "/blog/first/",
                                 "<p>First body</p>", shared=shared)
            second = build.layout("Second", "Second page", build.SITE + "/blog/second/",
                                  "<p>Second body</p>", shared=shared)
        version.assert_called_once()
        self.assertIn("<p>First body</p>", first)
        self.assertIn("<p>Second body</p>", second)
        self.assertIn('content="First page"', first)
        self.assertIn('content="Second page"', second)
        self.assertIn(shared["header"], first)
        self.assertIn(shared["header"], second)
        self.assertIn(shared["footer"], first)
        self.assertIn(shared["footer"], second)


if __name__ == "__main__":
    unittest.main()
