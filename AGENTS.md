# Repository Guide

A lightweight static personal website built with HTML, CSS, JavaScript, and a Python-generated blog.

**Core principle: Every line of code should justify its existence.**

Treat the site as one coherent system. Prefer sound architecture, consistent design, performance, accessibility, and long-term maintainability over isolated fixes or artificially small diffs.

## Architecture

- `index.html`: Homepage and source of shared header/footer markup for generated pages.
- `assets/css/style.css`: Shared presentation, themes, and responsive styles.
- `assets/js/site.js`: Navigation, themes, search, and page interactions.
- `assets/js/atmosphere.js`: WebGL atmosphere and reduced-motion behavior.
- `posts/<slug>/index.md`: Article source; keep accompanying media in each post's `assets/`.
- `.github/scripts/`: Generation, synchronization, verification, and tests.
- `.github/workflows/`: Current CI, publication, and README synchronization adapters.
- `preview.py`: Shared local preview and verified static-build entry point.

See [PREVIEW.md](PREVIEW.md) for commands, publishing, and browser checks. Do not commit generated `blog/`, `_site/`, `sitemap.xml`, or activity snapshots.

## Engineering Principles

- Read relevant code, dependencies, and established behavior before editing; assess effects across pages, themes, devices, and workflows.
- Fix root causes. Reorganize inadequate implementations when warranted instead of stacking patches, overrides, or special cases.
- Prefer clear ownership, necessary reuse, and the simplest effective design. Remove redundant or obsolete code when addressing related areas.
- Avoid speculative abstractions, defensive complexity without evidence, and unrelated refactoring.
- Preserve existing functionality, accessibility, visual consistency, and compatibility unless explicitly changing them.
- Keep site generation portable. Treat hosts, deployment credentials, and optional integrations as replaceable adapters, not core build dependencies.

## Change Management

- Group work by coherent objectives. Use PRs when review, validation, or a durable engineering record is useful; use direct commits for routine, low-risk updates where permitted.
- Keep history meaningful; avoid fragmented PRs and procedural overhead. Verify before publishing and clean up merged temporary branches when appropriate.
- Follow explicit task instructions. Never rewrite shared history or discard existing work without authorization.

## Verification

- Match checks to the change's scope and risk; inspect affected code paths and report what was actually tested.
- For Python script changes: `python -m unittest discover -s .github/scripts -p 'test_*.py' -v`.
- For site, asset, generation, or deployment changes: `python3 preview.py --build-only` (Windows: `py -3 preview.py --build-only`).
- For relevant UI changes, review responsive layouts, light/dark modes, keyboard accessibility, browser navigation, and reduced-motion behavior.
- Confirm no obsolete implementation remains. Never claim a check passed unless it ran successfully.

## Documentation

- Treat code and workflows as the source of truth; update affected guidance when behavior, commands, or architecture changes.
- Preserve homepage-to-README generation: edit source content rather than generated sections.
- Keep published claims factual and protect private information and credentials.
- Keep repository-wide rules here and operational detail in [PREVIEW.md](PREVIEW.md); avoid duplicated or speculative documentation.

## Blog Content

- For tasks that create, edit, review, reorganize, or classify articles under `posts/`, read [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md) and [BLOG_INDEX.json](BLOG_INDEX.json) before making editorial decisions.
- `BLOG_GUIDELINES.md` is the authoritative source for editorial policy, research, writing, metadata, and content review. Keep editorial rules there; do not duplicate them in this file.
- `BLOG_INDEX.json` is generated from Markdown sources. Never edit it manually; regenerate with `python .github/scripts/blog_index.py --write` and verify with `python .github/scripts/blog_index.py --check`.
- Use the index for quick topic and tag discovery, then read relevant Markdown sources before relying on their details. The archive is context, not a limit on future subjects, formats, or depth.
- Website engineering tasks that do not touch blog content do not need to load the editorial guide. Mixed tasks must follow both this file and the editorial guide.
- Repository engineering and verification rules remain governed by this file; editorial decisions remain governed by `BLOG_GUIDELINES.md`. Follow explicit user instructions where applicable, without overriding factual accuracy, privacy, licensing, or publication safeguards.
