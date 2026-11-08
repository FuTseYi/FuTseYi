# Development & Preview

This is the operating guide for **Source** (`FuTseYi-Site-Source`). The overview and canonical workflow diagram are in [README.md](README.md).

## Local preview and build

Requires Python 3.10 or newer. From the Source root:

```sh
python preview.py
python preview.py --build-only
python preview.py --port 8766
```

On Windows, use `py -3` in place of `python`. Open `http://127.0.0.1:8765/` or `http://127.0.0.1:8765/blog/` with the default port. Saving source files rebuilds the preview; refresh the browser to see changes. Stop with Ctrl+C and avoid running two preview processes in the same checkout.

`preview.py` installs missing dependencies from `requirements.txt` into the local `.venv` (or active virtual environment) if required. The initial installation needs Internet access. A failed rebuild preserves the last good preview. `--build-only` builds and validates the portable `_site/` without starting a server.

## Verification

```sh
python -m unittest discover -s tests -t . -p "test_*.py" -v
python preview.py --build-only
python scripts/blog_index.py --check
```

For UI changes, run the browser regression suite as CI does, and inspect navigation, both themes, keyboard access, reduced motion, mobile layouts, and relevant article types. The PR workflow [validate.yml](.github/workflows/validate.yml) runs unit tests, a full offline build, and Chromium/WebKit smoke tests (development dependencies in `requirements-dev.txt`). It does not publish the site.

## Articles and indexes

Article source lives at `posts/<slug>/index.md`, with media alongside it in `posts/<slug>/assets/`. Article titles, dates, tags, research quality, and editorial decisions are governed by [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md), not this operations guide.

After changing article metadata or adding/removing articles, run:

```sh
python scripts/blog_index.py --write
python scripts/blog_index.py --check
```

`BLOG_INDEX.json` is a tracked editorial discovery index. `contributions.json` is a **different** tracked snapshot updated by the contribution Action. Neither is the generated Pagefind search index; Pagefind is produced during the site build.

## Publishing and credentials

- Every ordinary Push to Source `main` first triggers [refresh-contributions.yml](.github/workflows/refresh-contributions.yml), except a push changing only `contributions.json`; that exception prevents recursive refresh. The refresh also runs on the 1st and 15th of each month (UTC 01:17) and by manual dispatch.
- After a successful refresh workflow, [deploy.yml](.github/workflows/deploy.yml) runs by `workflow_run`. It may also be manually dispatched. It checks out the latest Source `main`, tests, and performs one offline build. If the GitHub GraphQL request fails, the refresh workflow retains the last verified snapshot and emits a warning.
- GitHub App `FuTseYi Site Automation` must be installed on Source, Published, and Profile. Only Source stores `PUBLISH_APP_ID` (Actions Variable) and `PUBLISH_APP_PRIVATE_KEY` (Actions Secret). Each workflow requests a short-lived installation token scoped to its target repository. `GITHUB_TOKEN` reads the GraphQL API; the App Bot signs automated writes.
- The built `_site/` is copied to **Published** (`FuTseYi/FuTseYi.github.io`) only when actual static files differ. `build-info.json` records the checked-out Source SHA and Actions run; timestamp-only differences do not force a release. `vercel.json` is created by the publishing workflow and enables Vercel deployments from Published `main` only.
- GitHub Pages and Vercel host the **same** Published output without running Source's Python build. Never edit Published directly; `PUBLISHED_README.md` supplies its README.
- [sync-readme.yml](.github/workflows/sync-readme.yml) independently updates `FuTseYi/FuTseYi` Profile README when the homepage, articles, or related generators change, or by manual dispatch. It does not rewrite Source's `README.md`.

If an automatic publication produces no content changes, a successful run with no new Published commit is expected. Review its workflow logs and `build-info.json` when tracing releases. Keep hosting settings and private keys out of the portable static build.
