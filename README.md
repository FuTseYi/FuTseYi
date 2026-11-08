# FuTseYi Site

Source and build pipeline for [futseyi.com](https://www.futseyi.com/). The site uses native HTML, shared CSS and JavaScript, and a Python build. This repository is the only place where website content and build logic are edited.

## Architecture

| Area | Source | Output |
| --- | --- | --- |
| Home and shared layout | `index.html`, `assets/` | `/index.html`, `/assets/` |
| Articles | `posts/*/index.md` and adjacent media | `/blog/`, `/blog/posts.json` |
| Search | Article pages | `/pagefind/` |
| Public GitHub activity | `scripts/sync_activity.py` | `/contributions.json` and homepage HTML |
| Publication | `preview.py`, `.github/workflows/deploy.yml` | [futseyi.github.io](https://github.com/FuTseYi/futseyi.github.io) |

`preview.py` assembles and verifies one `_site/` directory. The publishing workflow copies that directory to the public repository. GitHub Pages and Vercel serve the public repository without running another website build. Each release includes `build-info.json` with its source commit and workflow run; the public repository history provides previous releases for rollback.

## Local development

Requires Python 3.10 or newer.

```sh
python preview.py
python preview.py --build-only
python -m unittest discover -s tests -t . -p 'test_*.py'
```

On Windows, `py -3` can replace `python`. The preview installs the dependencies in `requirements.txt` into a local environment when needed. See [PREVIEW.md](PREVIEW.md) for build and publishing details and [AGENTS.md](AGENTS.md) for repository guidance.

## Publication

Changes merged into `main` are tested, built once, and published with a short-lived GitHub App token. Pull requests validate without publishing. Scheduled runs refresh public contribution data. The separate profile README workflow uses the same App with a token scoped to the profile repository; it does not rewrite this repository's README.

The public repository contains only the generated site and its publication metadata. Its [README](https://github.com/FuTseYi/futseyi.github.io#readme) describes the hosted output.
