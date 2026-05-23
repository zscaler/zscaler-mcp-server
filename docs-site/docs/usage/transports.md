---
id: transports
title: Transports
sidebar_label: Transports
sidebar_position: 2
---

# Transports

The Zscaler MCP Server supports three MCP transports. Pick the one that matches how clients will reach the server.

## `stdio` (default)

Standard input / standard output. The server is launched as a child process by the MCP client (Claude Desktop, Cursor, VS Code, etc.) and they communicate via stdin/stdout.

```bash
zscaler-mcp
# or
zscaler-mcp --transport stdio
```

**Use when:** Running locally for a single user. This is the default and the simplest setup. Authentication is not applicable — the operating system's process isolation provides security.

## `sse` (Server-Sent Events)

HTTP transport using Server-Sent Events for streaming responses.

```bash
zscaler-mcp --transport sse --host 0.0.0.0 --port 8000
```

**Use when:** Hosting a remote MCP server that clients connect to over HTTPS. Compatible with the MCP spec's SSE binding.

## `streamable-http`

HTTP transport with bi-directional streaming. The modern default for hosted MCP deployments.

```bash
zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

**Use when:** Deploying to Cloud Run, Azure Container Apps, AKS, AWS Bedrock AgentCore, or any other remote-MCP host. Used by every deployment integration in this project.

## TLS, host validation, and auth

Both HTTP transports support — and by default **require** for non-localhost — TLS, host-header allowlists, source-IP ACLs, and MCP client authentication. See:

- [TLS & hardening](../security/tls-and-hardening)
- [MCP client authentication](../security/mcp-client-auth)

## stdio vs HTTP — which to use?

| Scenario | Transport |
|---|---|
| Single-user local dev | `stdio` |
| Editor plugin (Claude, Cursor, VS Code) on your machine | `stdio` |
| Hosted MCP server (Cloud Run / AKS / VM / Bedrock) | `streamable-http` |
| Multi-user team server | `streamable-http` + `zscaler` or `jwt` auth |
| Legacy MCP client requiring SSE | `sse` |
