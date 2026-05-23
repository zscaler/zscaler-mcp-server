---
id: cli
title: CLI Reference
sidebar_label: CLI
sidebar_position: 1
---

# CLI Reference

The full CLI is available via `zscaler-mcp --help`. This page summarizes the most common flags.

## Server invocation

```bash
# stdio transport (default - for editor/agent use)
zscaler-mcp

# SSE transport
zscaler-mcp --transport sse

# Streamable HTTP transport
zscaler-mcp --transport streamable-http

# Custom host/port
zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8080
```

## Service selection

```bash
# Enable specific services
zscaler-mcp --services zia,zpa,zdx

# Exclude services
zscaler-mcp --disabled-services zcc,zdx

# Exclude specific tools (wildcards via fnmatch)
zscaler-mcp --disabled-tools "zcc_*,zia_list_device*"
```

## Toolsets

```bash
# Load a curated default set
zscaler-mcp --toolsets default

# Load specific toolsets
zscaler-mcp --toolsets zia_url_filtering,zpa_app_segments

# Load everything (then OneAPI entitlement filter trims)
zscaler-mcp --toolsets all

# Bypass the entitlement filter
zscaler-mcp --no-entitlement-filter
```

See the [Toolsets guide](../guides/toolsets) for the full catalog.

## Write operations

```bash
# Enable a specific write surface (allowlist MANDATORY)
zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zpa_delete_*"
```

`--enable-write-tools` without `--write-tools` registers **zero** write tools. See [Write operations](../security/write-operations).

## Auth & tokens

```bash
# Generate an API key for MCP client authentication (api-key mode)
zscaler-mcp --generate-auth-token
```

## Discovery & docs

```bash
# Print every registered tool and exit
zscaler-mcp --list-tools

# Regenerate auto-generated documentation regions
zscaler-mcp --generate-docs

# CI check — exit 1 if docs are stale
zscaler-mcp --check-docs

# Print version
zscaler-mcp --version
```

## Logging

```bash
# Enable tool-call audit logging
zscaler-mcp --log-tool-calls
```

## Lifecycle subcommands

Manage a running server (sends signals, no respawn unless requested):

```bash
zscaler-mcp status                  # PID, uptime, transport, port, .env path
zscaler-mcp reload                  # SIGHUP - soft reload .env (sessions survive)
zscaler-mcp restart                 # SIGUSR2 - hard restart (sessions die)
zscaler-mcp stop                    # SIGTERM - clean shutdown
```

Per-instance PID file overrides:

```bash
zscaler-mcp --pid-file /tmp/zscaler-mcp-8001.pid --port 8001
```

See [Configuration](../getting-started/configuration) for the complete environment variable / flag reference.
