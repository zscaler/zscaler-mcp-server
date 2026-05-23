---
id: building-from-source
title: Building from Source
sidebar_label: Building from Source
sidebar_position: 2
---

# Building from Source

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or pip
- `make` (optional convenience)

## Clone

```bash
git clone https://github.com/zscaler/zscaler-mcp-server.git
cd zscaler-mcp-server
```

## With `uv` (recommended)

```bash
# Creates .venv and installs all extras
uv sync --all-extras
source .venv/bin/activate

zscaler-mcp --version
```

## With pip (editable install)

```bash
pip install -e .

zscaler-mcp --version
```

## With make

```bash
make install-dev      # install in dev mode with all extras
make sync-dev-deps    # re-sync dev dependencies
make clean            # clean build artifacts
```

## Running locally

```bash
# Use uvx for quick runs from working dir
uvx zscaler-mcp

# Or the activated venv
zscaler-mcp
```

## Building the Docker image

```bash
make docker-build
make docker-run            # stdio mode
make docker-run-http       # HTTP + auth mode
```

## Auto-generated docs

Three Markdown files have auto-generated regions sourced from the live tool inventory:

- `docs/guides/supported-tools.md`
- `README.md` (service summary table)
- `docs/guides/toolsets.md`

Refresh after adding / renaming / removing a tool:

```bash
make generate-docs            # regenerate in place
make check-docs               # exit 1 if stale (CI gate)
```

## Lint and format

```bash
ruff check .
ruff format .
```

## Tests

```bash
pytest tests/ --ignore=tests/e2e -v       # unit + integration
pytest --run-e2e -v -s tests/e2e/         # E2E (requires creds)
```

## Releasing

Releases are fully automated:

1. Push commits using [Conventional Commits](https://www.conventionalcommits.org/)
2. semantic-release computes the next version from the commit messages
3. A new tag, GitHub release, and PyPI publish happen via the release workflow

Manual version bumps are not needed. See `.releaserc.json` for the configuration.
