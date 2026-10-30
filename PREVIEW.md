# Local preview

Requires Python 3.10 or later.

```powershell
# Windows
py -3 preview.py
```

```sh
# macOS / Linux
python3 preview.py
```

Open <http://127.0.0.1:8765/> for the homepage or <http://127.0.0.1:8765/blog/> for the Blog. The preview builds the site, indexes search, checks links, and watches for changes. Refresh the browser after each successful rebuild; stop with Ctrl+C.

On first use, the script installs `Markdown>=3.7,<4`, `pagefind[extended]==1.5.2`, and `Pygments>=2.17,<3` in a project-local `.venv` (or an already active virtual environment). Internet access and Python's `venv`/`pip` support are required. It does not install packages into the system Python.

The preview serves generated files from `_site/`. A failed rebuild leaves the last working preview available. Local links are adjusted only in the temporary build; repository source files are unchanged. Public contributions come from a recent snapshot when available, otherwise from GitHub.

Useful options:

- `--build-only` builds and validates the full site without serving it. The preview port must still be available.
- `--port 8766` uses a different port if the default is occupied.

Run only one preview process per checkout. The build and generated files are excluded from Git.

## Publishing an article

Create `posts/my-note/index.md`:

```markdown
---
title: My note
date: 2026-10-28
tags: Notes, Website
---

Article text goes here.
```

`title` and `date` are required; `tags` and `lang` (`zh-CN` or `en`) are optional. The frontmatter title is the sole page H1; body headings render one level lower without changing their source anchors. Every post is published when its changes reach `main`; dates control display order, not publication scheduling.

Put images and other files in `posts/my-note/assets/`, referencing them as `assets/example.webp`. The folder name is the public URL slug (`/blog/my-note/`); keep it stable after publication.

The same push deploys the Blog and updates the website/Profile READMEs.
