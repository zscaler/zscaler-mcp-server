---
id: service-configuration
title: Service Configuration
sidebar_label: Service Configuration
sidebar_position: 4
---

# Service Configuration

The MCP server can load all services, a specific subset, or a tightly-scoped slice via toolsets. There are three independent layers:

## 1. Service selection

Controlled by `--services` / `ZSCALER_MCP_SERVICES`:

```bash
# Enable only ZIA, ZPA, ZDX
zscaler-mcp --services zia,zpa,zdx

# Enable only ZIA
zscaler-mcp --services zia
```

When unset, every service is enabled. When the OneAPI entitlement filter runs (default), services the credentials cannot call are also dropped.

## 2. Service exclusion

```bash
# Run all services EXCEPT ZCC
zscaler-mcp --disabled-services zcc

# Combine with --services for fine-grained control
zscaler-mcp --services zia,zpa,zcc --disabled-services zcc
# (effectively: zia + zpa)
```

## 3. Tool exclusion (wildcards)

```bash
# Block every ZCC tool by pattern
zscaler-mcp --disabled-tools "zcc_*"

# Block multiple patterns
zscaler-mcp --disabled-tools "zcc_*,zia_list_device*"
```

Patterns use `fnmatch` syntax (shell glob).

## 4. Toolsets

The most surgical control — load only the bundles of tools an agent actually needs:

```bash
zscaler-mcp --toolsets zia_url_filtering,zpa_app_segments
zscaler-mcp --toolsets default
zscaler-mcp --toolsets all
```

See [Toolsets](../guides/toolsets) for the full catalog and the runtime-discovery meta-tools (`zscaler_list_toolsets`, `zscaler_enable_toolset`).

## Precedence

When multiple controls are set, precedence is:

1. **`disabled_tools`** — wins everything (blocks even an explicitly enabled tool)
2. **Toolset selection** — narrows what's available
3. **`enabled_tools`** allowlist — further narrows
4. **`write_tools`** allowlist — applies only to write tools

## Verifying the configuration

```bash
# List every tool that will be registered with current flags
zscaler-mcp --list-tools

# Check what's actually loaded at runtime (from an agent)
# Prompt: "List the Zscaler toolsets currently enabled"
# This calls zscaler_list_toolsets (always available)
```

## Recommended patterns

**Production read-only agent serving a single service team:**

```bash
zscaler-mcp \
  --services zia \
  --toolsets zia_url_filtering,zia_cloud_firewall,zia_dlp
```

**Production with narrow write surface for automation:**

```bash
zscaler-mcp \
  --services zpa \
  --toolsets zpa_app_segments,zpa_access_policies \
  --enable-write-tools \
  --write-tools "zpa_create_application_segment,zpa_update_application_segment"
```

**Development / exploration:**

```bash
zscaler-mcp --toolsets default
```
