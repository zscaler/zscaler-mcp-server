---
id: installation
title: Installation
sidebar_label: Installation
sidebar_position: 1
---

# Installation

## Prerequisites

- **Python 3.11 or higher**
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- Zscaler OneAPI credentials — see [Authentication](./authentication)

## Install from PyPI (recommended)

```bash
uv tool install zscaler-mcp-server
```

Or with `pipx`:

```bash
pipx install zscaler-mcp-server
```

Or with plain `pip`:

```bash
pip install zscaler-mcp-server
```

Verify the installation:

```bash
zscaler-mcp --version
```

## Install from source

```bash
git clone https://github.com/zscaler/zscaler-mcp-server.git
cd zscaler-mcp-server

# With uv (creates .venv automatically)
uv sync --all-extras
source .venv/bin/activate

# Or with pip
pip install -e .
```

## Run with Docker

A pre-built image is published on Docker Hub:

```bash
docker pull zscaler/zscaler-mcp-server:latest

docker run --rm \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest
```

For HTTP transports, expose the port:

```bash
docker run --rm -p 8000:8000 \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0
```

See [Docker deployment](../deployment/docker) for the full reference.

## Run with `uvx` (no install)

```bash
uvx zscaler-mcp-server
```

`uvx` resolves and runs the server in an ephemeral environment. This is the simplest path for ad-hoc use and is the configuration most editor integrations recommend.

## Next steps

1. [Configure your credentials](./authentication) — set `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_VANITY_DOMAIN`, and `ZSCALER_CUSTOMER_ID`
2. [Review the configuration options](./configuration) — services, toolsets, transport, write mode
3. [Run your first prompt](./quickstart) — verify the server end-to-end
4. [Wire it into your editor](../usage/editor-integration) — Claude, Cursor, Gemini CLI, VS Code, Kiro
