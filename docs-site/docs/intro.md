---
id: intro
title: Zscaler MCP Server
sidebar_label: Overview
sidebar_position: 1
slug: /intro
---

# Zscaler MCP Server

**zscaler-mcp-server** is a Model Context Protocol (MCP) server that connects AI agents with the **Zscaler Zero Trust Exchange** platform.

By default, the server operates in **read-only mode** for security, requiring explicit opt-in to enable write operations.

:::warning Public Preview
This project is in public preview and under active development. Features and functionality may change before the stable `1.0` release. Avoid production deployments and please share feedback through [GitHub Issues](https://github.com/zscaler/zscaler-mcp-server/issues).
:::

## What it does

The Zscaler MCP Server brings context to your AI agents. Try prompts like:

- *"List my ZPA application segments"*
- *"List my ZPA segment groups"*
- *"List my ZIA rule labels"*
- *"Show the ZDX experience score for my San Francisco office in the last 24 hours"*

It exposes **300+ tools** across every major Zscaler product, behind a single MCP interface that any MCP-compatible client (Claude Desktop, Claude Code, Cursor, Gemini CLI, Kiro IDE, VS Code + Copilot) can speak.

## Supported services

| Service | Code | Description |
|---|---|---|
| **ZPA** | Zscaler Private Access | Application segments, server groups, access policies, app connector groups, PRA |
| **ZIA** | Zscaler Internet Access | URL filtering, cloud firewall, DLP, SSL inspection, sandbox, ATP, cloud app control |
| **ZDX** | Zscaler Digital Experience | Application/device experience scores, deep traces, alerts, software inventory |
| **ZCC** | Zscaler Client Connector | Device enrollment, forwarding profiles, trusted networks |
| **ZTW** | Zscaler Cloud & Branch Connector | IP groups, network services, admin roles |
| **ZIdentity** | Identity service | Users, groups |
| **EASM** | External Attack Surface Management | Findings, lookalike domains, asset evidence |
| **Z-Insights** | Analytics | Web traffic, threat trends, CASB, shadow IT, IoT |
| **ZMS** | Microsegmentation | Agents, resources, policy rules, tags |

See [Services overview](./services/overview) for the full per-service tool catalog.

## Security-first by design

The server ships with safe defaults and **multiple defense-in-depth layers**:

- **Read-only by default** — only `list_*` and `get_*` operations are exposed
- **Mandatory write allowlist** — enabling writes requires *both* `--enable-write-tools` AND an explicit `--write-tools` pattern
- **HMAC-confirmed deletes** — destructive actions require a cryptographic confirmation token that prompt-injection cannot forge
- **OneAPI entitlement filter** — toolsets for unentitled products are silently dropped at startup
- **Output sanitization** — every tool response is scrubbed of invisible Unicode, HTML, and prompt-injection payloads
- **TLS + Host-header validation + Source-IP ACL** — for HTTP transports

See [Security](./security/write-operations) for the full security model.

## Quick links

- [Installation](./getting-started/installation) — get the server running locally
- [Configuration](./getting-started/configuration) — environment variables and CLI flags
- [Authentication](./getting-started/authentication) — set up your OneAPI credentials
- [Quickstart](./getting-started/quickstart) — first prompts in 5 minutes
- [Editor integration](./usage/editor-integration) — wire it into your AI assistant
- [Toolsets](./guides/toolsets) — load only the tools you need
- [Deployment](./deployment/docker) — Docker, Azure, GCP, AWS Bedrock
- [Supported tools](./guides/supported-tools) — complete tool catalog
