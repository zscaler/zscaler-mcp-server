---
id: tls-and-hardening
title: TLS & Network Hardening
sidebar_label: TLS & Hardening
sidebar_position: 3
---

# TLS & Network Hardening

These controls apply to the HTTP transports (`sse` and `streamable-http`) and govern **who can reach the server over the network**.

## TLS

**HTTPS is required by default** for non-localhost deployments. The server refuses to start on a non-localhost interface without TLS certificates unless `ZSCALER_MCP_ALLOW_HTTP=true` is set.

```env
ZSCALER_MCP_TLS_CERTFILE=/path/to/cert.pem
ZSCALER_MCP_TLS_KEYFILE=/path/to/key.pem

# Optional
ZSCALER_MCP_TLS_KEYFILE_PASSWORD=your-key-password
ZSCALER_MCP_TLS_CA_CERTS=/path/to/ca-bundle.pem
```

Generate a self-signed cert for local testing:

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost"
```

For managed hosts (Cloud Run, Azure Container Apps, ALB-fronted ECS) where TLS terminates at the platform edge, set `ZSCALER_MCP_ALLOW_HTTP=true` — the platform's TLS protects the wire.

## Host header validation

```env
ZSCALER_MCP_ALLOWED_HOSTS=mcp.example.com,*.example.com
```

Requests whose `Host` header doesn't match the allowlist receive `421 Misdirected Request`. Supports wildcards. Disabled by default for stdio; enabled by default for HTTP.

To disable (for debugging only):

```env
ZSCALER_MCP_DISABLE_HOST_VALIDATION=true
```

## Source IP ACL

Restrict which client IPs can connect:

```env
ZSCALER_MCP_ALLOWED_SOURCE_IPS=10.0.0.0/8,172.16.0.5,2001:db8::/32
```

When unset, source IP filtering is **disabled** and deferred to upstream controls (security groups, firewall rules).

Health-check endpoints (`/health`, `/healthz`, `/ready`) are always exempt so load-balancer probes work. Disallowed IPs receive `403 Forbidden`.

## `.env` plaintext-secret scanner

When starting with HTTP transports, the server automatically scans any `.env` file in the working directory for plaintext secrets (values containing `SECRET`, `PASSWORD`, `KEY`, or `TOKEN`). If detected, a security warning is logged recommending a secrets manager or environment variables.

## Output sanitization

Every string in every tool result passes through a three-stage sanitizer before reaching the agent:

1. **Invisible / control characters stripped** — zero-width characters, BiDi controls (LRO, RLO, etc.), Arabic letter mark, soft hyphen, BOM. NBSP normalized to space. Tab/LF/CR preserved.
2. **HTML / Markdown sanitized** — `bleach` removes every HTML tag and comment; Markdown image syntax collapses to alt text; Markdown links keep text + (visible) URL but lose the directive.
3. **Code-fence info-strings filtered** — fences with role-impersonation tokens (`system`, `assistant`, `tool`, `ignore`, …) get neutralized to `text`. Code bodies preserved.

This defends against prompt-injection payloads embedded in admin-editable Zscaler resources (rule descriptions, location names, label descriptions, etc.).

On by default. Opt out (diagnostics only) with:

```env
ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION=true
```

## Security posture banner

On startup, the server logs a consolidated **Security Posture Banner** summarizing the active configuration — transport, host validation, auth mode, TLS status, write mode, allowlist, entitlement filter result. This makes it easy to verify the state at a glance.

## Audit logging

```env
ZSCALER_MCP_LOG_TOOL_CALLS=true
```

Every tool invocation logs:

```text
[TOOL CALL] zia_list_locations | args: {page: 1, page_size: 50, name: "HQ"}
[TOOL OK] zia_list_locations | 342ms | 15 items
```

Sensitive parameters (any name containing `password`, `secret`, `token`, `key`, `credential`) are auto-redacted. Full response data is never logged — only a summary.

## Defense-in-depth summary

| Layer | Scope | On by default? |
|---|---|---|
| Read-only mode | every transport | ✅ |
| Write allowlist | every transport | ✅ (allowlist mandatory) |
| HMAC delete confirmations | every transport | ✅ |
| OneAPI entitlement filter | every transport | ✅ |
| Toolset selection | every transport | optional |
| Output sanitization | every transport | ✅ |
| TLS | HTTP only | ✅ (non-localhost) |
| Host validation | HTTP only | ✅ |
| Source IP ACL | HTTP only | optional |
| MCP client auth | HTTP only | auto when configured |
| `.env` secret scanner | HTTP only | ✅ |
| Audit logging | every transport | optional |
