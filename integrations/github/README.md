# GitHub MCP Registry Integration

The Zscaler MCP Server is listed on the [GitHub MCP Registry](https://github.com/modelcontextprotocol/registry), enabling one-click installation from GitHub Copilot and any MCP-compatible client that supports the registry.

## What It Provides

When users discover the Zscaler MCP Server in the GitHub MCP Registry, they can install it with a single click. The registry handles:

- **Automatic configuration** — the MCP client (VS Code, GitHub Copilot, etc.) prompts for the required credentials and sets up the server
- **Two installation methods** — PyPI (`uvx zscaler-mcp`) or Docker (`docker.io/zscaler/zscaler-mcp-server`)
- **Secret management** — credentials marked as `isSecret` are stored securely by the client
- **Version tracking** — the registry reflects the latest published version

## How It Works

The integration is powered by three files:

| File | Purpose |
|------|---------|
| [`server.json`](../../server.json) | MCP Registry manifest — server metadata, packages, and required environment variables |
| [`README.md`](../../README.md) | Contains `<!-- mcp-name: ... -->` HTML comment for PyPI ownership proof |
| [`Dockerfile`](../../Dockerfile) | Contains `LABEL io.modelcontextprotocol.server.name=...` for Docker image ownership proof |

### server.json Structure

The manifest declares two package types:

**PyPI Package** (`uvx`):

```json
{
  "registryType": "pypi",
  "identifier": "zscaler-mcp",
  "transport": { "type": "stdio" },
  "runtimeHint": "uvx",
  "environmentVariables": [
    { "name": "ZSCALER_CLIENT_ID", "isRequired": true, "isSecret": true },
    { "name": "ZSCALER_CLIENT_SECRET", "isRequired": true, "isSecret": true },
    { "name": "ZSCALER_CUSTOMER_ID", "isRequired": true, "isSecret": false },
    { "name": "ZSCALER_VANITY_DOMAIN", "isRequired": true, "isSecret": false }
  ]
}
```

**Docker Package** (`oci`):

```json
{
  "registryType": "oci",
  "identifier": "docker.io/zscaler/zscaler-mcp-server:latest",
  "transport": { "type": "stdio" },
  "runtimeHint": "docker",
  "runtimeArguments": [
    { "type": "named", "name": "-e", "value": "ZSCALER_CLIENT_ID={client_id}" },
    { "type": "named", "name": "-e", "value": "ZSCALER_CLIENT_SECRET={client_secret}" },
    { "type": "named", "name": "-e", "value": "ZSCALER_CUSTOMER_ID={customer_id}" },
    { "type": "named", "name": "-e", "value": "ZSCALER_VANITY_DOMAIN={vanity_domain}" }
  ]
}
```

## Required Credentials

Only 4 environment variables are needed — these are the Zscaler OneAPI credentials:

| Variable | Secret | Description |
|----------|--------|-------------|
| `ZSCALER_CLIENT_ID` | Yes | OneAPI Client ID from ZIdentity console |
| `ZSCALER_CLIENT_SECRET` | Yes | OneAPI Client Secret from ZIdentity console |
| `ZSCALER_CUSTOMER_ID` | No | Customer ID from ZIdentity console |
| `ZSCALER_VANITY_DOMAIN` | No | Vanity domain (e.g. `mycompany.zscloud.net`) |

### Why Only 4 Variables?

The registry serves **stdio transport** (local subprocess). In stdio mode:

- MCP client authentication is not applicable (local process, inherently trusted)
- HTTPS/TLS is not applicable (no HTTP involved — stdin/stdout between processes)
- Host header validation is not applicable (HTTP transports only)

The full set of security env vars (TLS, auth, host validation) is for HTTP/SSE deployments and is documented in the main [README](../../README.md).

## Version Automation

The `server.json` version is updated automatically during releases:

1. **`set-version.sh`** updates the `version` field in `server.json` alongside `pyproject.toml`, `__init__.py`, and plugin manifests
2. **`.releaserc.json`** includes `server.json` in the git assets, so the version bump is committed with the release

After each release, re-publish to the registry:

```bash
mcp-publisher publish
```

## Publishing

### Prerequisites

```bash
brew install mcp-publisher
```

### Steps

```bash
# 1. Authenticate with GitHub
mcp-publisher login github

# 2. Publish (from repo root)
cd /path/to/zscaler-mcp-server
mcp-publisher publish
```

### Validation

Validate the `server.json` locally before publishing:

```bash
python3 -c "
import json, urllib.request
from jsonschema import validate

with open('server.json') as f:
    data = json.load(f)

with urllib.request.urlopen(data['\$schema']) as resp:
    schema = json.loads(resp.read())

validate(instance=data, schema=schema)
print('Valid')
"
```

## Schema Reference

The `server.json` follows:

```text
https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json
```

For detailed publication steps, ownership proof requirements, and troubleshooting, see [`local_dev/GitHub/mcp-registry-publication.md`](../../local_dev/GitHub/mcp-registry-publication.md).
