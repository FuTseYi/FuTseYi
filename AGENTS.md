# Website maintenance

A static personal website built with HTML, CSS, JavaScript, and a Python-generated Blog. Keep the implementation small and maintainable; introduce dependencies only when they solve a concrete problem.

## Working in this repository

- Read the relevant source files and existing tests before editing. Use the current implementation as the source of truth rather than assuming this document is exhaustive.
- Make focused changes and run the affected tests. For changes to templates, assets, or build logic, run `python3 preview.py --build-only` (Windows: `py -3 preview.py --build-only`).
- Update this file in the same change when file ownership, architecture, build commands, or long-term maintenance rules change. Keep it factual and concise; do not rewrite it for routine fixes or content updates.

## Sources of truth

- `index.html`: homepage content, navigation, and shared header/footer markup. Keep local asset paths relative so the homepage can open directly as a file.
- `assets/css/style.css`: shared styles for the homepage and Blog.
- `assets/js/site.js`: navigation, theme, search, and other page interactions.
- `assets/js/atmosphere.js`: WebGL background. Preserve its light/dark palettes and reduced-motion behavior.
- `posts/<slug>/index.md`: articles, with required `title` and `date` frontmatter and optional comma-separated `tags`. All posts are published; dates determine display order. Put article images in the post's `assets/` directory and use relative links.
- `.github/scripts/build.py`: builds `blog/` and `sitemap.xml`, deriving Blog headers and footers from `index.html`. Both outputs are ignored by Git.
- `.github/scripts/sync_readme.py`: derives the website and GitHub Profile READMEs from homepage content and the newest three posts. Do not manually edit generated README text; maintain its content and ordering in `index.html`.
- `.github/scripts/sync_activity.py`: renders recent public contributions into the deployed homepage. It excludes the website and Profile repositories, limits results to 12, and uses a previously published snapshot when the GitHub API fails.

## Development and publishing

- Homepage-only check: open `index.html` directly.
- Full local preview: `python3 preview.py` (Windows: `py -3 preview.py`). See [PREVIEW.md](PREVIEW.md).
- One-off build and verification: `python3 preview.py --build-only`.
- Unit tests: `python -m unittest discover -s .github/scripts -p 'test_*.py' -v`.
- Pull requests run both unit tests and a complete build. Pushes to `main` deploy GitHub Pages and synchronize the READMEs. Deployment also refreshes public activity twice monthly.
- Profile README sync needs `PROFILE_README_TOKEN` with Contents write permission to `FuTseYi/FuTseYi`; website deployment uses the built-in `GITHUB_TOKEN`.

## Changes

- Preserve the existing visual design, mobile navigation, accessibility labels, keyboard controls, and no-JavaScript behavior. Check light/dark themes and mobile layout when changing shared assets.
- Keep sections such as Active In limited to confirmed public affiliations. Public contact email: `hello@futseyi.com`. Do not introduce private contact information or inferred credentials.
- Do not migrate content from `My-Website` without checking privacy, asset paths, and URL changes.
- Do not commit `blog/`, `_site/`, generated snapshots, or test content.
- When writing Git trees through the GitHub API, set `base_tree_sha` to the current commit's tree; otherwise unrelated files can be lost.
