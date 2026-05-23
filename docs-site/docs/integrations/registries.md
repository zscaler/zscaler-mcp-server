---
title: Published Registries
sidebar_label: Overview
---

The Zscaler MCP Server is published to every major MCP / AI-tooling registry so admins can discover and install it from whichever surface their team already uses. Each listing below points at the same upstream artifact (PyPI package, Docker image, or `.mcpb` bundle) — pick whichever marketplace your client supports.

The left-hand sidebar lists each destination individually so you can jump straight to the one you need.

## Cursor Marketplace {#cursor-marketplace}

One-click install for the [Cursor](https://cursor.com) IDE.

- **Where to find it:** [Cursor Marketplace — Zscaler](https://cursor.com/marketplace/zscaler)
- **What you get:** The Cursor Plugin, which wires the MCP server into Cursor's chat and Composer and ships the same toolset and skill surface as every other client.
- **Install:** Click **Install** on the marketplace page. Cursor handles the rest, including prompting for your Zscaler OneAPI credentials.

Need the manual install instructions or a deep-dive on the Cursor extension? See the dedicated [Cursor](/docs/integrations/cursor) page.

## Claude Marketplace {#claude-marketplace}

Official listing for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and the Claude family.

- **Where to find it:** [Claude Marketplace — Zscaler](https://claude.com/plugins/zscaler)
- **What you get:** The Claude Code Plugin (CLI). The Plugin also bundles every guided [Skill](/docs/guides/skills) for auto-activation in Claude Code conversations.
- **Install:** From a terminal with the Claude Code CLI installed:

  ```bash
  claude plugin install zscaler
  ```

The separate **Claude Desktop Extension** (`.mcpb` bundle for the Claude Desktop app) is published to Anthropic's in-app Directory of Connectors — open **Claude Desktop → Directory → Connectors** and search for `zscaler`. Full walkthrough on the [Claude](/docs/integrations/claude#claude-desktop-extension) page.

## Official MCP Registry {#official-mcp-registry}

The canonical [Model Context Protocol registry](https://registry.modelcontextprotocol.io/) maintained by the MCP working group.

- **Where to find it:** [Official MCP Registry — Zscaler](https://registry.modelcontextprotocol.io/?q=zscaler)
- **What you get:** The PyPI and Docker package descriptors (manifest-only — no extra runtime). Consumed by any MCP client that supports the Model Context Protocol registry spec (GitHub Copilot, VS Code, and a growing list of others).
- **Install:** Discover from any registry-aware client, or invoke directly with [`uvx`](https://docs.astral.sh/uv/):

  ```bash
  uvx zscaler-mcp
  ```

## Docker MCP Hub {#docker-mcp-hub}

Docker's curated catalog of containerised MCP servers.

- **Where to find it:** [Docker MCP Hub — Zscaler](https://hub.docker.com/mcp/server/zscaler-mcp-server/overview)
- **What you get:** The published `zscaler/zscaler-mcp-server` image, ready to run as a long-lived container or as an on-demand stdio process.
- **Install:** Pull the image and run with your `.env` file mounted:

  ```bash
  docker pull zscaler/zscaler-mcp-server:latest
  docker run -i --rm --env-file .env zscaler/zscaler-mcp-server:latest
  ```

For the full Docker walkthrough (stdio vs. HTTP transport, auth modes, host validation), see the [Docker deployment](/docs/deployment/docker) page.

## GitHub MCP Registry {#github-mcp-registry}

GitHub's MCP registry, surfaced inside GitHub Copilot and any MCP-compatible client that supports the registry spec.

- **Where to find it:** [GitHub MCP Registry — Zscaler](https://github.com/mcp?search=zscaler)
- **What you get:** A registry entry pointing at both the PyPI package (`uvx zscaler-mcp`) and the Docker image, with `isSecret`-marked credential fields that the client prompts for at install time.
- **Install:** Use the **Install** button on the registry page, or wire it manually in any client that supports the [Anthropic registry manifest format](/docs/integrations/github-registry).

For the technical breakdown of how the listing is published (`server.json`, PyPI ownership proof, Docker label), see the [GitHub MCP Registry](/docs/integrations/github-registry) page.

## At a glance

| Registry | Surface | Artifact |
|----------|---------|----------|
| [Cursor Marketplace](https://cursor.com/marketplace/zscaler) | Cursor IDE | Cursor Plugin |
| [Claude Marketplace](https://claude.com/plugins/zscaler) | Claude Code (CLI) | `claude plugin install zscaler` |
| [Claude Desktop Directory](/docs/integrations/claude#claude-desktop-extension) | Claude Desktop app | `.mcpb` bundle |
| [Official MCP Registry](https://registry.modelcontextprotocol.io/?q=zscaler) | Any MCP-spec client | PyPI + Docker descriptors |
| [Docker MCP Hub](https://hub.docker.com/mcp/server/zscaler-mcp-server/overview) | Docker / OCI runtimes | `zscaler/zscaler-mcp-server` image |
| [GitHub MCP Registry](https://github.com/mcp?search=zscaler) | GitHub Copilot + MCP clients | PyPI + Docker descriptors |
