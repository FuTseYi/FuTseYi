# Repository guide

A personal website built with HTML, CSS, JavaScript, and a Python-generated Blog.

**Principle:** Every line of code should justify its existence. Prefer the simplest maintainable solution that preserves behavior.

## Getting oriented

- Start with the relevant source files, existing tests, and [PREVIEW.md](PREVIEW.md) when build or preview behavior matters. Check the implementation rather than assuming this guide is exhaustive.
- Trace a feature through its source, generated output, and workflow before changing it. Follow existing patterns instead of introducing a parallel implementation.

## Project map

- `index.html`: homepage content and the shared header/footer used by generated Blog pages. Relative local assets allow direct-file viewing.
- `assets/css/style.css`: shared layout, responsive styles, and theme colors.
- `assets/js/site.js`: navigation, theme switching, search, and page interactions.
- `assets/js/atmosphere.js`: shared WebGL background, with light/dark rendering and reduced-motion support.
- `posts/<slug>/index.md`: Blog sources. `title` and `date` are required; `tags` is optional. Assets live alongside each post.
- `.github/scripts/build.py`: generates `blog/` and `sitemap.xml` from posts and the homepage template.
- `.github/scripts/sync_readme.py`: derives the website/Profile READMEs and injects recent posts into the deployed homepage. Edit `index.html` or post sources, not generated README content.
- `.github/scripts/sync_activity.py`: renders public GitHub activity into the deployed homepage; uses the previous snapshot when refresh fails.
- `preview.py` and `PREVIEW.md`: local development; `.github/scripts/verify.py` and `test_*.py`: build checks and tests; `.github/workflows/`: PR validation, deployment, and Profile sync.

## Working on changes

- Fix the cause of a demonstrated problem. Prefer removing, consolidating, or reusing code over adding dependencies, abstractions, speculative fallbacks, or patch-on-patch fixes.
- Keep changes focused and reviewable. Preserve existing content, design, interactions, accessibility, and cross-platform behavior unless the task requires changing them.
- Retain necessary error handling and accessibility behavior; do not remove safeguards merely to shorten the code.
- Keep public content factual. Do not add private contact details or inferred credentials; the public email is `hello@futseyi.com`.
- Do not commit generated `blog/`, `_site/`, `sitemap.xml`, or activity snapshots. When creating Git trees via API, use the current commit's base tree.

## Verification

- For a homepage-only visual check, open `index.html` directly. For the complete site, use `python3 preview.py` (Windows: `py -3 preview.py`).
- Run `python -m unittest discover -s .github/scripts -p 'test_*.py' -v` for script changes. Run `python3 preview.py --build-only` (Windows: `py -3 preview.py --build-only`) when changing pages, assets, generation, or deployment behavior.
- Check affected responsive, light/dark, keyboard, and no-JavaScript behavior when relevant. A successful build does not prove browser rendering is correct.
- Report what changed, which checks ran, and what remains unverified. Do not claim a test or browser check passed unless it was performed.

## Documentation upkeep

- Treat code and workflows as the source of truth. When architecture, ownership, dependencies, commands, or publishing behavior change, update the relevant documentation in the same change.
- Keep this file as a concise entry point. Put detailed preview and publishing instructions in `PREVIEW.md`; avoid copying existing code or documentation into agent instructions.
- Correct outdated guidance when encountered, but do not rewrite unrelated documents for routine fixes, content edits, or stylistic preferences.
