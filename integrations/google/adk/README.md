# Google ADK (Agent Development Kit) Integration

The Zscaler MCP Server integrates with [Google ADK](https://google.github.io/adk-docs/) to build autonomous Zscaler security agents powered by Gemini models. This integration enables you to create AI agents that can query and manage your Zscaler Zero Trust Exchange through natural language, using the MCP server as the tool backend.

## Video Walkthrough

A complete video walkthrough covering all Google Cloud deployment options — including the ADK Agent for local development and Cloud Run — is available here:

**[Zscaler Integration MCP Server in GCP — Video Demo](https://zscaler.wistia.com/medias/13jxjizk3r)**

## What's Included

```text
integrations/google/adk/
├── adk_agent_operations.py      # Python deployment/operations script
├── README.md
└── zscaler_agent/
    ├── __init__.py              # Package init (re-exports agent module)
    ├── agent.py                 # ADK agent definition (root_agent)
    ├── .env                     # Environment variables (edit this)
    ├── env.properties           # Template for .env
    └── requirements.txt         # Python dependencies
```

## How It Works

The Google ADK agent connects to the Zscaler MCP Server as an MCP tool provider via stdio:

```text
User → Google ADK Agent → Gemini Model → Zscaler MCP Server (uvx zscaler-mcp) → Zscaler APIs
```

1. ADK starts the Zscaler MCP Server as a subprocess via `uvx zscaler-mcp`
2. The `CachedMCPToolset` discovers and caches all available tools (300+ across 9 services)
3. Gemini interprets user requests and invokes the appropriate Zscaler tools
4. Results are returned in natural language with context and recommendations

## Architecture

### Runtime Model: Co-located Subprocess

The MCP server is **not** a separate VM or container. When the ADK agent runs, it spawns `zscaler-mcp` as a **child process** inside the same container (or host) and communicates over stdin/stdout pipes using the MCP stdio transport. Both processes share the same memory and CPU allocation.

```text
┌─── Container / Host ─────────────────────────────────────────┐
│                                                               │
│  ┌─── Process 1: ADK Agent (Python) ──────────────────────┐  │
│  │  Gemini model + function calling                        │  │
│  │  Listens on HTTP :8080 (Cloud Run) or :8000 (local)     │  │
│  └────────────────┬───────────────────────────────────────┘  │
│                   │ stdin/stdout (stdio transport)            │
│  ┌────────────────▼───────────────────────────────────────┐  │
│  │  Process 2: zscaler-mcp (subprocess)                    │  │
│  │  300+ tools, Zscaler SDK → Zscaler APIs                 │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

This is different from the **standalone MCP server deployment** (e.g., via `setup-gcp-cloudrun.py` or Docker), where the MCP server runs as its own service and clients connect remotely over HTTPS:

```text
┌─── Client (Claude, Cursor, etc.) ─┐         ┌─── Cloud Run / Docker ──────────┐
│  mcp-remote / native MCP client    │  HTTPS  │  zscaler-mcp                    │
│                                    │────────▶│  (standalone, streamable-http)   │
└────────────────────────────────────┘         └─────────────────────────────────┘
```

**Key difference**: The ADK integration bundles the MCP server *inside* the agent container as a subprocess. The standalone deployment exposes it as an independent networked service.

### Deployment Targets

The agent uses the same deployment architecture as other marketplace MCP agents (e.g., CrowdStrike Falcon MCP):

- **Local development:** `adk web` with `GOOGLE_API_KEY`
- **Cloud Run:** `adk deploy cloud_run` with Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=True`)
- **Vertex AI Agent Engine:** `adk deploy agent_engine` for managed agent hosting
- **Agentspace:** Registration via Discovery Engine API for Google Agentspace integration

In all cases, the MCP server runs as a co-located subprocess — not as a separate service. The ADK agent manages the MCP server lifecycle automatically (start on init, stop on shutdown).

## Prerequisites

- Python 3.11 or higher
- [Google ADK](https://google.github.io/adk-docs/) installed (`pip install google-adk`)
- A Google API key (local dev) or Vertex AI access (Cloud Run / Agent Engine)
- [uv](https://docs.astral.sh/uv/) installed (for `uvx zscaler-mcp`)
- Zscaler OneAPI credentials (`ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, etc.)

### Cloud Run / Agent Engine: Required IAM Roles

Cloud deployments use the Compute Engine default service account. Grant these roles before deploying:

```bash
PROJECT_ID="your-project"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Cloud Build uploads source to Cloud Storage
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/storage.admin"

# Cloud Build pushes built container to Artifact Registry
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/artifactregistry.writer"

# Cloud Run service calls Gemini via Vertex AI
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/aiplatform.user"
```

Also enable the required APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  --project $PROJECT_ID
```

### Cloud Run: Enterprise GCP Organization IAM

Enterprise GCP organizations enforcing `constraints/iam.allowedPolicyMemberDomains` will block `allUsers` access to Cloud Run. When deploying, answer `N` to "Allow unauthenticated invocations" and access the agent via:

```bash
# Grant yourself invoker access
gcloud run services add-iam-policy-binding zscaler-agent-service \
  --region REGION --member="user:YOUR_EMAIL" --role="roles/run.invoker"

# Access via local proxy (handles IAM auth transparently)
gcloud run services proxy zscaler-agent-service \
  --region REGION --project YOUR_PROJECT_ID
# Then open http://localhost:8080
```

## Configuration

### Step 1: Set up the environment file

If `zscaler_agent/.env` doesn't exist, copy from the template:

```bash
cp zscaler_agent/env.properties zscaler_agent/.env
```

Or run the operations script with no arguments to auto-create it:

```bash
python adk_agent_operations.py
```

### Step 2: Edit `zscaler_agent/.env`

```dotenv
# Google ADK Configuration
GOOGLE_GENAI_USE_VERTEXAI=False
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=gemini-2.5-flash

# Zscaler OneAPI Credentials
ZSCALER_CLIENT_ID=your-client-id
ZSCALER_CLIENT_SECRET=your-client-secret
ZSCALER_VANITY_DOMAIN=your-vanity-domain
ZSCALER_CUSTOMER_ID=your-customer-id
ZSCALER_CLOUD=

# Optional MCP Configuration
ZSCALER_MCP_SERVICES=             # e.g., zia,zpa,zdx (empty = all)
ZSCALER_MCP_WRITE_ENABLED=        # true/false
ZSCALER_MCP_WRITE_TOOLS=          # e.g., zpa_*,zia_*

# Deployment (Cloud Run / Agent Engine)
PROJECT_ID=your-gcp-project
REGION=us-central1
AGENT_ENGINE_STAGING_BUCKET=      # gs://your-bucket (Agent Engine only)

# Agentspace (optional)
PROJECT_NUMBER=
AGENT_LOCATION=
REASONING_ENGINE_NUMBER=
AGENT_SPACE_APP_NAME=

# Performance
MAX_PREV_USER_INTERACTIONS=-1     # -1 = unlimited, 5 = recommended
```

### Configuration Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI instead of Google AI Studio | `False` |
| `GOOGLE_API_KEY` | Google AI Studio API key (required if not using Vertex AI) | — |
| `GOOGLE_MODEL` | Gemini model to use | `gemini-2.5-flash` |
| `ZSCALER_MCP_SERVICES` | Comma-separated services to enable (empty = all) | — |
| `ZSCALER_MCP_WRITE_ENABLED` | Enable write operations | — |
| `ZSCALER_MCP_WRITE_TOOLS` | Allowlist of write tools (wildcards supported) | — |
| `PROJECT_ID` | GCP project ID for deployment | — |
| `REGION` | GCP region for deployment | `us-central1` |
| `AGENT_ENGINE_STAGING_BUCKET` | GCS bucket for Agent Engine artifacts | — |
| `ZSCALER_MCP_DISABLED_SERVICES` | Comma-separated services to disable | — |
| `ZSCALER_MCP_DISABLED_TOOLS` | Comma-separated tool patterns to disable (wildcards) | — |
| `ZSCALER_MCP_AUTH_ENABLED` | Enable MCP client authentication (HTTP only) | `true` |
| `ZSCALER_MCP_ALLOW_HTTP` | Allow plaintext HTTP on non-localhost | `false` |
| `ZSCALER_MCP_ALLOWED_HOSTS` | Comma-separated allowed Host header values | — |
| `ZSCALER_MCP_ALLOWED_SOURCE_IPS` | Comma-separated allowed client IPs/CIDRs | — |
| `ZSCALER_MCP_DISABLE_HOST_VALIDATION` | Disable Host header checks | `false` |
| `ZSCALER_MCP_TLS_CERTFILE` | TLS certificate path | — |
| `ZSCALER_MCP_TLS_KEYFILE` | TLS key path | — |
| `ZSCALER_MCP_SKIP_CONFIRMATIONS` | Skip HMAC confirmation for destructive ops | `false` |
| `ZSCALER_MCP_CONFIRMATION_TTL` | Confirmation token TTL in seconds | `300` |
| `MAX_PREV_USER_INTERACTIONS` | Max conversation history turns (`-1` = unlimited) | `-1` |

## Usage

All operations are managed through a single interactive script (`adk_agent_operations.py`) with a numbered menu — the same UX pattern used by the standalone GCP and Azure deployment scripts:

```bash
cd integrations/google/adk
python adk_agent_operations.py deploy      # interactive guided deployment
python adk_agent_operations.py status      # check deployment status
python adk_agent_operations.py logs        # stream logs
python adk_agent_operations.py destroy     # tear down deployed resources
python adk_agent_operations.py destroy -y  # tear down without confirmation
```

### `deploy` — Interactive Guided Deployment

Running `python adk_agent_operations.py deploy` presents a menu to choose the deployment target:

```text
  Select deployment target:

    [1] Local development  — run with 'adk web' on localhost
    [2] Google Cloud Run   — deploy as managed container with web UI
    [3] Vertex AI Agent Engine — fully managed agent hosting
    [4] Google Agentspace  — register in enterprise agent catalog
```

The script then prompts for credentials (load from `.env` file or custom path), validates required environment variables, collects target-specific configuration, shows a deployment summary, and asks for confirmation before executing.

#### Local Development

Runs `adk web` locally using your `GOOGLE_API_KEY`. The agent UI will be available at `http://localhost:8000`. No GCP project or IAM setup required.

#### Cloud Run

Builds the agent container from source using Cloud Build, pushes to Artifact Registry, and deploys to Cloud Run. The script automatically:

1. Backs up your `.env` file
2. Removes `GOOGLE_API_KEY` and sets `GOOGLE_GENAI_USE_VERTEXAI=True`
3. Runs `adk deploy cloud_run` with the service name `zscaler-agent-service`
4. Saves deployment state for `status` / `logs` / `destroy` operations
5. Restores your `.env` file on exit (success or failure)

#### Vertex AI Agent Engine

Deploys to Vertex AI Agent Engine with display name `zscaler_agent`. Requires `AGENT_ENGINE_STAGING_BUCKET` set to a `gs://` bucket.

#### Google Agentspace

Registers an existing Agent Engine deployment with Google Agentspace via the Discovery Engine API. Requires the deployment to already exist, plus `PROJECT_NUMBER`, `REASONING_ENGINE_NUMBER`, and `AGENT_SPACE_APP_NAME`.

### Example Prompts

Once the agent is running:

- "List all ZPA application segments"
- "Show me ZIA firewall rules for the Finance department"
- "What ZDX alerts are currently active?"
- "List EASM findings for my organization"
- "Show me shadow IT applications with high risk scores"
- "Check ZCC device enrollment status for my organization"
- "List all microsegmentation policy rules"

## MCP Server Security Enforcement

The Zscaler MCP server enforces several security features **by default**. These must be understood and configured for each deployment mode:

| Security Feature | Default | stdio (local) | Cloud Run / Agent Engine |
|-----------------|---------|---------------|------------------------|
| **Authentication** | Enabled for HTTP | Not applicable | Must configure or disable via `ZSCALER_MCP_AUTH_ENABLED=false` if Cloud Run IAP handles auth |
| **HTTPS** | Required | Not applicable | Set `ZSCALER_MCP_ALLOW_HTTP=true` (Cloud Run terminates TLS at the load balancer) |
| **Host validation** | Enabled | Not applicable | Set `ZSCALER_MCP_ALLOWED_HOSTS` to your service URL, or `ZSCALER_MCP_DISABLE_HOST_VALIDATION=true` |
| **Source IP ACL** | Disabled | Not applicable | Optionally set `ZSCALER_MCP_ALLOWED_SOURCE_IPS` |
| **Write operations** | Disabled | Must enable explicitly | Must enable explicitly |
| **HMAC confirmations** | Enabled for destructive ops | Active | Active unless `ZSCALER_MCP_SKIP_CONFIRMATIONS=true` |

### Local Development (stdio)

For `local_run` with stdio transport, auth/TLS/host-validation are **not applicable** — the MCP server communicates via stdin/stdout with no HTTP involved.

### Cloud Run / Agent Engine Deployments

When deploying to Cloud Run or Agent Engine, the MCP server runs over HTTP behind Google's infrastructure. Since Cloud Run terminates TLS at the load balancer, configure:

```dotenv
ZSCALER_MCP_ALLOW_HTTP=true
ZSCALER_MCP_AUTH_ENABLED=false
ZSCALER_MCP_DISABLE_HOST_VALIDATION=true
```

The operations script (`adk_agent_operations.py`) warns about unconfigured security vars during deployment to help catch misconfigurations.

## Delete-Operation Confirmation (HMAC)

Delete operations are irreversible and protected by the MCP server's cryptographic HMAC-SHA256 confirmation flow. Create and update operations execute directly — this matches the MCP server's zero-trust design.

### How It Works

When a delete tool is called, the MCP server does **not** execute immediately. Instead:

1. The server returns a `CONFIRMATION REQUIRED` message with a time-limited HMAC token
2. The agent instruction tells the model to present these details to the user
3. If the user approves, the agent re-calls the tool with `kwargs='{"confirmation_token": "<token>"}'`
4. The server verifies the token is bound to the exact tool name, parameters, and hasn't expired
5. Only then does the delete execute

This is transport-agnostic — it works the same in stdio, SSE, and streamable-http modes.

### Why Not ADK's `require_confirmation`?

ADK has a built-in `require_confirmation` mechanism, but the `adk web` developer UI does **not** implement the `adk_request_confirmation` protocol handler. Setting `require_confirmation=True` causes the agent to stall indefinitely in the developer UI. For production ADK deployments with a custom client that handles the confirmation protocol, this can be re-enabled by passing `require_confirmation=True` to the `CachedMCPToolset`.

### Disabling Confirmations

| Setting | Effect |
|---------|--------|
| `ZSCALER_MCP_SKIP_CONFIRMATIONS=true` | Disables HMAC confirmation for automation/CI/CD |

For production deployments, keep HMAC confirmations enabled (the default).

## Security Considerations

- The `.env` files contain sensitive credentials — never commit them to source control
- Write operations are disabled by default; enable explicitly with `ZSCALER_MCP_WRITE_ENABLED=true`
- When enabling writes, use `ZSCALER_MCP_WRITE_TOOLS` with specific patterns (e.g., `zpa_create_*`) rather than broad wildcards
- For production deployments, use GCP Secret Manager for credential storage
- The `CachedMCPToolset` caches tools in-memory to avoid repeated MCP server round-trips

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Google AI Agent Finder](https://cloud.withgoogle.com/agentfinder)
- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
- [Main README](../../README.md)
- [Supported Tools Reference](../../docs/guides/supported-tools.md)
- [Troubleshooting](../../docs/guides/TROUBLESHOOTING.md)
