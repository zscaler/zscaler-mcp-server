# Google ADK (Agent Development Kit) Integration

The Zscaler MCP Server integrates with [Google ADK](https://google.github.io/adk-docs/) to build autonomous Zscaler security agents powered by Gemini models. This integration enables you to create AI agents that can query and manage your Zscaler environment through natural language, using the MCP server as the tool backend.

## What's Included

| Component | Location | Purpose |
|-----------|----------|---------|
| Root `.env` | `integrations/adk/.env` | Zscaler API credentials and write-tool configuration |
| Agent `.env` | `integrations/adk/zscaler_agent/.env` | Google ADK config (model, API key, agent prompt, Cloud Run settings) |

## How It Works

The Google ADK agent connects to the Zscaler MCP Server as an MCP tool provider. The agent:

1. Starts the Zscaler MCP Server as a subprocess (via `uvx` or Docker)
2. Discovers all available Zscaler tools (280+ across 8 services)
3. Uses a Gemini model (e.g., `gemini-2.0-flash`) to interpret user requests
4. Invokes the appropriate Zscaler tools and returns results in natural language

```
User → Google ADK Agent → Gemini Model → Zscaler MCP Server → Zscaler APIs
```

## Prerequisites

- Python 3.11 or higher
- [Google ADK](https://google.github.io/adk-docs/) installed (`pip install google-adk`)
- A Google API key or Vertex AI access
- [uv](https://docs.astral.sh/uv/) installed (for `uvx` method) or Docker
- Zscaler OneAPI credentials

## Configuration

### Step 1: Configure Zscaler credentials

Edit `integrations/adk/.env` with your Zscaler OneAPI credentials:

```dotenv
ZSCALER_CLIENT_ID="your-client-id"
ZSCALER_CLIENT_SECRET="your-client-secret"
ZSCALER_VANITY_DOMAIN="your-vanity-domain"
ZSCALER_CUSTOMER_ID="your-customer-id"
ZSCALER_CLOUD=""
ZSCALER_MCP_WRITE_ENABLED=""
ZSCALER_MCP_WRITE_TOOLS=zpa_*,zia_*
```

### Step 2: Configure the ADK agent

Edit `integrations/adk/zscaler_agent/.env` with your Google and agent settings:

```dotenv
# Google ADK Configuration
GOOGLE_GENAI_USE_VERTEXAI=False
GOOGLE_API_KEY="your-google-api-key"
GOOGLE_MODEL=gemini-2.0-flash

# Zscaler API Credentials (same as root .env)
ZSCALER_CLIENT_ID="your-client-id"
ZSCALER_CLIENT_SECRET="your-client-secret"
ZSCALER_VANITY_DOMAIN="your-vanity-domain"
ZSCALER_CUSTOMER_ID="your-customer-id"
ZSCALER_CLOUD=""

# Agent Configuration
ZSCALER_AGENT_PROMPT='You are a helpful Zscaler security assistant with access to ZIA, ZPA, ZDX, ZCC, EASM, and ZIdentity. Help users query and manage their Zscaler environment.'

# Optional MCP Configuration
ZSCALER_MCP_SERVICES=""
ZSCALER_MCP_TOOLS=""
ZSCALER_MCP_WRITE_ENABLED=""

# Cloud Run Deployment (optional)
PROJECT_ID=your-gcp-project-id
REGION=us-central1

# Performance
MAX_PREV_USER_INTERACTIONS=-1
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI instead of Google AI Studio | `False` |
| `GOOGLE_API_KEY` | Google AI Studio API key (required if not using Vertex AI) | — |
| `GOOGLE_MODEL` | Gemini model to use | `gemini-2.0-flash` |
| `ZSCALER_AGENT_PROMPT` | System prompt for the agent | (see `.env`) |
| `ZSCALER_MCP_SERVICES` | Comma-separated services to enable (empty = all) | — |
| `ZSCALER_MCP_WRITE_ENABLED` | Enable write operations | `false` |
| `ZSCALER_MCP_WRITE_TOOLS` | Allowlist of write tools (wildcards supported) | — |
| `PROJECT_ID` | GCP project ID for Cloud Run deployment | — |
| `REGION` | GCP region for Cloud Run deployment | `us-central1` |
| `MAX_PREV_USER_INTERACTIONS` | Max conversation history turns (`-1` = unlimited) | `-1` |

## Usage

### Local Development

```bash
cd integrations/adk
adk run zscaler_agent
```

### Vertex AI / Google Cloud

For deploying to Google Cloud Run with Vertex AI:

```bash
# Set your GCP project
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Deploy
adk deploy cloud_run --project $PROJECT_ID --region $REGION zscaler_agent
```

### Example Prompts

Once the agent is running:

- "List all ZPA application segments"
- "Show me ZIA firewall rules for the Finance department"
- "What ZDX alerts are currently active?"
- "List EASM findings for my organization"
- "Show me shadow IT applications with high risk scores"

## Security Considerations

- The `.env` files contain sensitive credentials — never commit them to source control
- Write operations are disabled by default; enable explicitly with `ZSCALER_MCP_WRITE_ENABLED=true`
- When enabling write operations, use `ZSCALER_MCP_WRITE_TOOLS` with specific patterns (e.g., `zpa_create_*`) rather than broad wildcards
- For production deployments, use GCP Secret Manager for credential storage

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Main README](../../README.md)
- [Supported Tools Reference](../../docs/guides/supported-tools.md)
- [Authentication & Deployment Guide](../../docs/deployment/authentication-and-deployment.md)
- [Troubleshooting](../../docs/guides/TROUBLESHOOTING.md)
