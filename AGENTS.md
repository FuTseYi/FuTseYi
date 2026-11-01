# Repository Guide

A lightweight personal website built with HTML, CSS, JavaScript, and a Python-generated blog, deployed through GitHub Pages.

**Core principle: Every line of code should justify its existence.**

Treat the repository as one coherent, evolving system. Prioritize architectural integrity, consistent design, simplicity, performance, and long-term maintainability over isolated optimizations or minimal diffs.

## Project Structure

- `index.html`: Homepage content and shared header/footer for generated blog pages.
- `assets/css/style.css`: Shared styles, responsive layouts, and themes.
- `assets/js/site.js`: Navigation, theme switching, search, and page interactions.
- `assets/js/atmosphere.js`: WebGL background animation and reduced-motion support.
- `posts/<slug>/index.md`: Blog sources, with article assets stored alongside each post.
- `.github/scripts/`: Site generation, README and activity synchronization, verification, and tests.
- `.github/workflows/`: Deployment, pull request validation, and Profile README synchronization.
- `preview.py`: Local build and preview entry point.
- `PREVIEW.md`: Local development and article publishing instructions.

Generated outputs, including `blog/`, `_site/`, `sitemap.xml`, and activity snapshots, must not be committed.

## Engineering Principles

- Understand the relevant architecture, dependencies, design patterns, and existing behavior before making changes.
- Approach each task from a system-wide perspective. Maintain consistency across related components, pages, interactions, and workflows.
- Address root causes rather than accumulating patches, overrides, special cases, or compensating logic.
- Reconsider and restructure existing implementations when necessary. Do not preserve an inadequate design merely to minimize the diff.
- Favor cohesive solutions, clear responsibilities, appropriate reuse, and the simplest effective implementation.
- Consolidate duplicated logic and remove obsolete code, unused dependencies, and superseded implementations when making related changes.
- Avoid unnecessary abstractions, speculative safeguards, premature optimization, and complexity without demonstrated value.
- Keep changes focused on the intended objective without sacrificing architectural integrity or introducing unrelated refactoring.
- Preserve established functionality, visual consistency, accessibility, compatibility, and user experience unless the task explicitly requires otherwise.
- Ensure each change leaves the affected system at least as coherent, efficient, and maintainable as before.

## Change Management

- Use pull requests for significant engineering changes that benefit from independent review, validation, or a lasting record of technical decisions.
- Use direct commits for routine, low-risk maintenance and content updates when repository permissions and protection rules allow.
- Organize changes by coherent engineering objectives rather than arbitrary implementation steps.
- Keep commits meaningful and reviewable. Avoid redundant pull requests, fragmented history, and unnecessary procedural overhead.
- Prefer testing coherent changes before pushing; clean up temporary branches after merged PRs while retaining PR history.
- Follow explicit task instructions and repository rules when choosing, merging, or publishing changes.
- Do not rewrite shared history or remove existing work without explicit authorization.

## Verification

- Keep core site generation portable across repository names, visibility settings, domains, and static hosts. Treat deployment credentials and platform-specific settings as adapters, not build inputs.
- Reuse the same verified build entry point for local development, PR previews, and production.
- Match verification to the scope and risk of each change.
- Review affected code paths and run relevant existing tests before considering a change complete.
- For Python script changes, run `python -m unittest discover -s .github/scripts -p 'test_*.py' -v`.
- For site, asset, generation, or deployment changes, run `python3 preview.py --build-only` (Windows: `py -3 preview.py --build-only`).
- Verify responsive layouts, light/dark themes, accessibility, browser behavior, and reduced-motion support when relevant.
- Confirm that obsolete code and redundant implementations have not been left behind.
- Do not claim successful verification without running the corresponding checks. Clearly report any limitations or unverified behavior.

## Documentation and Content

- Treat the implementation and workflows as the source of truth.
- Update relevant documentation when architecture, dependencies, commands, or publishing behavior changes.
- Maintain the existing homepage-to-README synchronization model. Modify source content rather than generated README sections.
- Keep public content factual. Do not introduce private information, inferred credentials, or unsupported claims.
- Keep `AGENTS.md` concise and limited to durable repository-wide guidance. Refer to existing documentation instead of duplicating it.
- Avoid unrelated documentation rewrites or cosmetic changes that provide no practical improvement.
