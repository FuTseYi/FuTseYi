"""Regression tests for generated SEO identity and indexing contracts."""
import tempfile
import unittest
from pathlib import Path

import verify as seo_verify


class SeoContractTests(unittest.TestCase):
    @staticmethod
    def page(*, canonical=None, duplicate=False, robots=None):
        canonicals = ([canonical] if canonical is not None else [])
        if duplicate:
            canonicals.append(canonical)
        head = "".join(f'<link rel="canonical" href="{url}">' for url in canonicals)
        if robots is not None:
            head += f'<meta name="robots" content="{robots}">'
        result = seo_verify.Page()
        result.feed(f"<html><head>{head}</head><body></body></html>")
        return result

    def test_generated_page_identity_matches_exact_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = "https://example.org"
            path = root / "blog/example/index.html"
            valid = self.page(canonical="https://example.org/blog/example/")
            self.assertEqual(seo_verify.check_page_identity({path: valid}, root, origin), [])
            wrong = self.page(canonical="https://example.org/")
            self.assertIn("canonical", " ".join(seo_verify.check_page_identity({path: wrong}, root, origin)))
            for page in (self.page(), self.page(canonical="https://example.org/blog/example/", duplicate=True)):
                self.assertIn("exactly one", " ".join(seo_verify.check_page_identity({path: page}, root, origin)))
            hidden = self.page(canonical="https://example.org/blog/example/", robots="max-snippet:-1, NOINDEX")
            self.assertIn("noindex", " ".join(seo_verify.check_page_identity({path: hidden}, root, origin)))


if __name__ == "__main__":
    unittest.main()
