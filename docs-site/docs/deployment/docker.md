---
id: docker
title: Docker
sidebar_label: Docker
sidebar_position: 1
---

# Docker

The Zscaler MCP Server is published as a multi-arch (amd64 + arm64) Docker image on Docker Hub: [`zscaler/zscaler-mcp-server`](https://hub.docker.com/r/zscaler/zscaler-mcp-server).

## Pull and run (stdio)

```bash
docker pull zscaler/zscaler-mcp-server:latest

docker run --rm \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest
```

## SSE transport

```bash
docker run --rm -p 8000:8000 \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest \
  --transport sse --host 0.0.0.0
```

## Streamable-HTTP transport

```bash
docker run --rm -p 8000:8000 \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0
```

## Custom port

```bash
docker run --rm -p 8080:8080 \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8080
```

## With service selection

```bash
docker run --rm \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest \
  --services zia,zpa,zdx
```

## Pin a specific version

```bash
docker run --rm \
  --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:1.2.3
```

## Individual environment variables (no `.env`)

```bash
docker run --rm \
  -e ZSCALER_CLIENT_ID=your_client_id \
  -e ZSCALER_CLIENT_SECRET=your_secret \
  -e ZSCALER_CUSTOMER_ID=your_customer_id \
  -e ZSCALER_VANITY_DOMAIN=your_vanity_domain \
  zscaler/zscaler-mcp-server:latest
```

## Build locally (development)

```bash
git clone https://github.com/zscaler/zscaler-mcp-server.git
cd zscaler-mcp-server

docker build -t zscaler-mcp-server .

docker run --rm -e ZSCALER_CLIENT_ID=... -e ZSCALER_CLIENT_SECRET=... \
  zscaler-mcp-server
```

## Live `.env` reloading

For production, **bind-mount** the `.env` file so the container can re-read it on `zscaler-mcp restart`:

```bash
docker run -d --name zscaler-mcp-server \
  --env-file /path/to/.env \
  -v /path/to/.env:/app/.env:ro \
  -e ZSCALER_MCP_DOTENV_PATH=/app/.env \
  -p 8000:8000 \
  zscaler/zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0
```

Then to apply a config change without recreating the container:

```bash
$EDITOR /path/to/.env                              # edit on the host
docker exec zscaler-mcp-server zscaler-mcp restart # re-read + execvp inside the container
```

The `restart` subcommand uses `execvp` so the PID stays the same — Docker doesn't notice the swap. Sessions die; clients reconnect.

Alternative one-off (no bind mount):

```bash
docker cp /path/to/.env zscaler-mcp-server:/app/.env
docker exec zscaler-mcp-server zscaler-mcp restart
```

## When HTTP transport, set `--host 0.0.0.0`

Always set `--host 0.0.0.0` for HTTP transports in Docker, otherwise the server binds to the container loopback and is unreachable from outside.

## TLS in containers

For platforms that terminate TLS at the edge (Cloud Run, Azure Container Apps, ALB), set:

```env
ZSCALER_MCP_ALLOW_HTTP=true
```

For self-hosted containers, mount certificates and configure:

```env
ZSCALER_MCP_TLS_CERTFILE=/certs/cert.pem
ZSCALER_MCP_TLS_KEYFILE=/certs/key.pem
```

## Cloud deployment guides

- [Azure (Container Apps / VM / AKS Preview)](./azure)
- [GCP (Cloud Run / GKE / VM)](./gcp)
- [Amazon Bedrock AgentCore](./amazon-bedrock)
