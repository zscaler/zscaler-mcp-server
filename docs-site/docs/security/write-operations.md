---
id: write-operations
title: Write Operations
sidebar_label: Write Operations
sidebar_position: 1
---

# Write Operations

The Zscaler MCP Server is **read-only by default**. Write tools (create / update / delete) require **two explicit opt-ins** before any write tool is registered with the server.

## The two-gate model

```bash
# ❌ WRONG — registers 0 write tools (allowlist missing)
zscaler-mcp --enable-write-tools

# ✅ CORRECT — explicit allowlist required
zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zpa_delete_*"
```

| Gate | Flag | Env var | Notes |
|---|---|---|---|
| 1 | `--enable-write-tools` | `ZSCALER_MCP_WRITE_ENABLED=true` | Global unlock |
| 2 | `--write-tools "pattern"` | `ZSCALER_MCP_WRITE_TOOLS="pattern"` | **Mandatory** allowlist (wildcards via `fnmatch`) |

Without **both** gates, **zero** write tools are registered — `list_*` and `get_*` remain available, the rest are inaccessible.

## Allowlist patterns

```bash
# All ZPA create + delete
--write-tools "zpa_create_*,zpa_delete_*"

# All ZPA writes
--write-tools "zpa_*"

# Cross-service: all create operations
--write-tools "*_create_*"

# Specific tools only
--write-tools "zpa_create_application_segment,zia_create_rule_label"
```

Startup log when an allowlist is active:

```text
⚠️  WRITE TOOLS MODE ENABLED
⚠️  Explicit allowlist provided - only listed write tools will be registered
⚠️  Allowed patterns: zpa_create_*, zpa_delete_*
🔒 Security: 85 write tools blocked by allowlist, 8 allowed
```

## HMAC-confirmed destructive actions

Delete operations use a **cryptographic confirmation token** instead of a `confirmed=true` boolean. The token is bound to the specific operation parameters and expires after 5 minutes.

This prevents **prompt injection attacks** where a malicious prompt could trick the agent into confirming a destructive action. Even if an attacker compromises the agent's prompt, they cannot forge a valid token.

Flow:

1. Agent calls a `*_delete_*` tool
2. Server returns `{"confirmation_required": true, "token": "<HMAC-SHA256>", "expires_at": "..."}`
3. Agent must echo the token back within 5 minutes to confirm execution
4. Tokens are single-use and tamper-proof

To bypass confirmations in CI / non-interactive contexts:

```bash
export ZSCALER_MCP_SKIP_CONFIRMATIONS=true
```

Use this **only in trusted automation pipelines** — never in interactive sessions.

## Tool naming convention

Every operation is a separate, single-purpose tool with explicit verb-based naming:

```text
zpa_list_application_segments    ← Read-only, safe to allow-list
zpa_get_application_segment      ← Read-only, safe to allow-list
zpa_create_application_segment   ← Write — requires gates 1 + 2
zpa_update_application_segment   ← Write — requires gates 1 + 2
zpa_delete_application_segment   ← Destructive — requires gates 1 + 2 + HMAC
```

This design lets AI assistants:

- Allow-list read-only tools for autonomous exploration
- Require explicit user confirmation for write operations (via `destructiveHint`)
- Clearly understand each tool's intent from its name

## Best practices

- **Production agents** → keep read-only (default). Don't set `WRITE_ENABLED`.
- **Automation pipelines** → use the **narrowest possible** allowlist (e.g. `zpa_create_application_segment` rather than `zpa_*`).
- **Audit regularly** → review which write tools are allowlisted; remove anything you don't actively use.
- **Never** set `ZSCALER_MCP_WRITE_ENABLED=true` in a default-shared `.env` template.
- **Never** ship a config with `ZSCALER_MCP_SKIP_CONFIRMATIONS=true` outside trusted CI.

## Related

- [MCP client authentication](./mcp-client-auth) — who can connect
- [TLS & hardening](./tls-and-hardening) — network controls
- [Output sanitization](#) — coming soon
