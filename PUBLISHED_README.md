# futseyi.github.io

This repository hosts the generated static files for [futseyi.com](https://www.futseyi.com/). GitHub Pages and Vercel serve the same published output.

## Source and publishing

The private source repository builds and verifies the complete `_site/` directory, then publishes it here through GitHub Actions. This repository is updated automatically; manual edits are replaced by the next publication. No build step runs here.

Each release includes [build-info.json](build-info.json) with the source commit and build run. Previous releases remain in this repository's Git history. See [LICENSING.md](LICENSING.md) for reuse terms.
