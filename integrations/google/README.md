# Google Cloud Integration

This directory contains all Google Cloud deployment options for the Zscaler MCP Server.

## Video Walkthrough

A complete video walkthrough covering all five Google Cloud deployment options (Cloud Run, GKE, Compute Engine VM, ADK Agent Local, ADK Agent Cloud Run) is available here:

**[Zscaler Integration MCP Server in GCP — Video Demo](https://zscaler.wistia.com/medias/13jxjizk3r)**

The demo walks through prerequisites, IAM setup, and live deployments for each target.

## What's Included

```text
integrations/google/
├── README.md                       # This file
├── gcp/                            # Standalone MCP server deployment
│   ├── gcp_mcp_operations.py       # Unified deployment script (Cloud Run, GKE, Compute Engine VM)
│   └── env.properties              # Template .env file
└── adk/                            # Google ADK agent integration (separate product)
    ├── adk_agent_operations.py     # ADK agent operations (local, Cloud Run, Agent Engine, Agentspace)
    ├── README.md
    └── zscaler_agent/              # ADK agent source code
```

## Deployment Options

### Option 1: Standalone MCP Server (`gcp/gcp_mcp_operations.py`)

Interactive deployment of the Zscaler MCP Server as an independent service. Supports three targets:

| Target | What It Deploys | Runtime |
|--------|----------------|---------|
| **Cloud Run** | Docker container (managed, serverless) | `zscaler/zscaler-mcp-server:latest` (Docker Hub) |
| **GKE** | Docker container on self-managed or Autopilot cluster | Same image; optionally creates a new Autopilot cluster |
| **Compute Engine VM** | Python library from PyPI via systemd | `pip install zscaler-mcp[gcp]` on Debian 12 |

MCP clients (Claude Desktop, Cursor, etc.) connect directly to the server over HTTPS using streamable-http transport.

**Quick start:**

```bash
cd integrations/google/gcp
python gcp_mcp_operations.py deploy      # guided deployment (prompts for target)
python gcp_mcp_operations.py status      # check health
python gcp_mcp_operations.py logs        # stream logs
python gcp_mcp_operations.py ssh         # SSH into VM (VM only)
python gcp_mcp_operations.py destroy     # tear down
python gcp_mcp_operations.py destroy -y  # tear down (no prompt)
```

**Features:**
- Interactive CLI with numbered menus (same UX as the Azure deployment script)
- GCP Secret Manager integration (optional, recommended)
- Four auth modes: JWT, API Key, Zscaler, None
- Auto-configures Claude Desktop and Cursor client configs
- State file (`.gcp-deploy-state.json`) for status/logs/destroy operations

### Option 2: ADK Agent (`adk/adk_agent_operations.py`)

Deploys a Gemini-powered AI agent that wraps the MCP server as an internal subprocess. Users interact with the agent through natural language — not directly with the MCP server.

| Target | Description |
|--------|-------------|
| **Local** | Run locally with `adk web` using `GOOGLE_API_KEY` |
| **Cloud Run** | Deploy agent container to Cloud Run (built from source via Cloud Build) |
| **Agent Engine** | Deploy to Vertex AI Agent Engine (fully managed) |
| **Agentspace** | Register an Agent Engine deployment with Google Agentspace |

All targets are managed through a single interactive script:

```bash
cd integrations/google/adk
python adk_agent_operations.py deploy      # guided deployment (prompts for target)
python adk_agent_operations.py status      # check status
python adk_agent_operations.py logs        # stream logs
python adk_agent_operations.py destroy     # tear down
```

See [adk/README.md](./adk/README.md) for full documentation.

### Option 3: Gemini CLI Extension

The Zscaler MCP Server is also available as a Gemini CLI extension for local developer use. The extension manifest (`gemini-extension.json`) lives at the repository root (required by Gemini CLI) and is documented in [integrations/gemini-extension/README.md](../gemini-extension/README.md).

## Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- A GCP project with billing enabled
- Zscaler OneAPI credentials
- For GKE: `kubectl` installed (cluster can be created by the script or pre-existing)
- For ADK: [Google ADK](https://google.github.io/adk-docs/) installed

### Required GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  compute.googleapis.com \
  container.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  --project YOUR_PROJECT_ID
```

### Required IAM Roles

The default Compute Engine service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`) needs specific roles depending on the deployment type.

#### Standalone MCP Server

| Role | Cloud Run | GKE | VM | Purpose |
|------|:---------:|:---:|:--:|---------|
| `roles/secretmanager.secretAccessor` | Yes | Yes | Yes | Read credentials from Secret Manager |
| `roles/iam.workloadIdentityUser` | — | Yes | — | Bind K8s service account to GCP service account |
| `roles/run.invoker` | Per-user | — | — | Invoke Cloud Run in enterprise orgs (see below) |

#### ADK Agent (Cloud Run)

| Role | Required | Purpose |
|------|:--------:|---------|
| `roles/storage.admin` | Yes | Cloud Build uploads source to Cloud Storage |
| `roles/artifactregistry.writer` | Yes | Cloud Build pushes container to Artifact Registry |
| `roles/aiplatform.user` | Yes | Cloud Run service calls Gemini via Vertex AI |
| `roles/run.invoker` | Per-user | Invoke Cloud Run in enterprise orgs |

#### Quick Setup

```bash
PROJECT_ID="your-project"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/storage.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/aiplatform.user"
```

## Configuration

### Step 1: Create `.env` file

```bash
cd gcp
cp env.properties .env
```

### Step 2: Edit `.env`

Update the values for your environment. At minimum:

```dotenv
GCP_PROJECT_ID=your-gcp-project
ZSCALER_CLIENT_ID=your-client-id
ZSCALER_CLIENT_SECRET=your-client-secret
ZSCALER_VANITY_DOMAIN=your-vanity-domain
ZSCALER_CUSTOMER_ID=your-customer-id
```

### Step 3: Deploy

```bash
python gcp_mcp_operations.py deploy
```

The script will prompt for deployment target, auth mode, and all required options.

## Enterprise Considerations

### Cloud Run: GCP Organization IAM Policies

Many enterprise GCP organizations enforce the `constraints/iam.allowedPolicyMemberDomains` organization policy, which prevents granting `allUsers` or `allAuthenticatedUsers` access to Cloud Run services. When this policy is active, the `--allow-unauthenticated` flag on `gcloud run deploy` will silently fail, and Cloud Run's IAM layer will return **401** for all external requests — *before* the MCP server's own auth layer is reached.

**Impact:** MCP clients like Claude Desktop and Cursor use `mcp-remote` to connect. When `mcp-remote` receives a 401 from Cloud Run's IAM layer, it interprets this as an MCP OAuth challenge and enters an OAuth discovery flow, which hangs indefinitely.

**Recommended patterns for enterprise environments:**

| Pattern | Description |
|---------|-------------|
| **Compute Engine VM** | No Cloud Run IAM layer — the MCP server's own auth (JWT, API Key, Zscaler) is the sole gatekeeper. Works out of the box. |
| **GKE** | No Cloud Run IAM layer — K8s LoadBalancer exposes the service directly. MCP server auth handles access control. |
| **Cloud Run + VPC-only ingress** | Restrict Cloud Run to internal traffic only (no public endpoint). Users connect through corporate VPN/network, and the MCP server's auth layer handles application-level access. |
| **Cloud Run + Identity-Aware Proxy (IAP)** | IAP handles org-level authentication via browser login. The MCP server handles tool-level auth via its own header. |
| **Cloud Run + `gcloud run services proxy`** | The proxy runs locally, handles GCP IAM auth transparently, and forwards requests to Cloud Run. The MCP server's auth travels through the proxy. Suitable for developer/testing scenarios. |

**For PoC and testing:** The Compute Engine VM option avoids this issue entirely and was validated end-to-end with `zscaler` auth mode.

## Resources

- [GCP Secret Manager Integration](../../docs/deployment/gcp_secrets_manager_integration.md)
- [Cloud Run Deployment Guide](../../docsrc/guides/gcp-cloud-run.rst)
- [Main README](../../README.md)
- [Supported Tools Reference](../../docs/guides/supported-tools.md)
- [Troubleshooting](../../docs/guides/TROUBLESHOOTING.md)
