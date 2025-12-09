# Deploying Zscaler MCP Server with Google ADK

This directory contains a prebuilt [Google ADK](https://google.github.io/adk-docs/) based agent integrated with the Zscaler MCP Server.

The goal is to provide customers an opinionated and validated set of instructions for running the Zscaler MCP Server and deploying it for their teams on Google Cloud.

## Table of Contents

1. [Setting up and running locally (5 minutes)](#setting-up-and-running-locally-5-minutes)
2. [Deployment - Why Deploy?](#deployment---why-deploy)
3. [Deploying the agent to Cloud Run](#deploying-the-agent-to-cloud-run)
4. [Deploying to Vertex AI Agent Engine and registering on Agentspace](#deploying-to-vertex-ai-agent-engine-and-registering-on-agentspace)
5. [Securing access, Evaluating, Optimizing performance and costs](#securing-access-evaluating-optimizing-performance-and-costs)

## Setting up and running locally (5 minutes)

You can run the following commands locally on Linux / Mac or in Google Cloud Shell.
If you plan to deploy the agent, it is recommended to run in Google Cloud Shell.

```bash
git clone https://github.com/zscaler/zscaler-mcp-server.git

cd zscaler-mcp-server/examples/adk

# Create and activate Python environment
python3 -m venv .venv
. .venv/bin/activate

# Install dependencies
pip install -r zscaler_agent/requirements.txt

# Make the script executable
chmod +x adk_agent_operations.sh

# Run the setup script
./adk_agent_operations.sh
```

The script will create a `.env` file in `zscaler_agent/` directory and prompt you to update it.

<details>

<summary><b>Sample Output - First Run</b></summary>

```bash
./adk_agent_operations.sh
INFO: No .env file found. Creating from template...
SUCCESS: 'zscaler_agent/env.properties' copied to 'zscaler_agent/.env'.
WARNING: ACTION REQUIRED: Please update the variables in 'zscaler_agent/.env' before running this script with an operation mode.
```

</details>

### Required Configuration

Update the `.env` file with your credentials:

```bash
# Zscaler API Credentials (from Zidentity console)
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_VANITY_DOMAIN=your_vanity_domain

# Google AI API Key (for local development)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_MODEL=gemini-2.0-flash
```

> [!NOTE]
> Get your GOOGLE_API_KEY using these [instructions](https://ai.google.dev/gemini-api/docs/api-key).
> Get your Zscaler credentials from the [Zidentity console](https://help.zscaler.com/zidentity/about-api-clients).

Now run the script with `local_run` parameter:

```bash
./adk_agent_operations.sh local_run
```

<details>

<summary><b>Sample Output - Local Run</b></summary>

```bash
./adk_agent_operations.sh local_run
INFO: Operation mode selected: 'local_run'.
--- Loading environment variables from './zscaler_agent/.env' ---
--- Environment variables loaded. ---
--- Validating required environment variables for 'local_run' mode ---
INFO: Variable 'GOOGLE_GENAI_USE_VERTEXAI' is set and valid.
INFO: Variable 'GOOGLE_API_KEY' is set and valid.
INFO: Variable 'GOOGLE_MODEL' is set and valid.
INFO: Variable 'ZSCALER_CLIENT_ID' is set and valid.
INFO: Variable 'ZSCALER_CLIENT_SECRET' is set and valid.
INFO: Variable 'ZSCALER_VANITY_DOMAIN' is set and valid.
INFO: Variable 'ZSCALER_AGENT_PROMPT' is set and valid.
--- All required environment variables are VALID. ---
INFO: Running ADK Agent for local development...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.

+-----------------------------------------------------------------------------+
| ADK Web Server started                                                      |
|                                                                             |
| For local testing, access at http://localhost:8000.                         |
+-----------------------------------------------------------------------------+

INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

</details>

You can access the agent at <http://localhost:8000> 🚀

> If running in Google Cloud Shell, use the web preview with port 8000.

You can stop the agent with `Ctrl+C`.

## Deployment - Why Deploy?

You may want to deploy the agent (with the Zscaler MCP Server) for the following reasons:

1. You do not want to hand out credentials to everyone to run the MCP server locally
2. You want to share a ready-to-use agent with your team
3. Use it for demos without any setup

You have two distinct paths to deployment:

1. Deploy on Cloud Run
2. Deploy on Vertex AI Agent Engine (and access through Agentspace after registration)

> [!NOTE]
> For all the following sections - If you are not running in Google Cloud Shell, make sure you have `gcloud` CLI [installed](https://cloud.google.com/sdk/docs/install) and you have authenticated with your username (preferably as owner of the project) on your local computer.

## Deploying the agent to Cloud Run

This section covers deployment to Cloud Run. Make sure you have all the required [APIs enabled](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service#before-you-begin) on the GCP project.

Update your `.env` file with Cloud Run configuration:

```bash
PROJECT_ID=your-gcp-project-id
REGION=us-central1
```

Then deploy:

```bash
cd examples/adk/
./adk_agent_operations.sh cloudrun_deploy
```

<details>

<summary><b>Sample Output - Cloud Run Deployment</b></summary>

```bash
INFO: Operation mode selected: 'cloudrun_deploy'.
--- Loading environment variables from './zscaler_agent/.env' ---
--- Environment variables loaded. ---
--- Validating required environment variables for 'cloudrun_deploy' mode ---
INFO: Variable 'GOOGLE_GENAI_USE_VERTEXAI' is set and valid.
INFO: Variable 'GOOGLE_MODEL' is set and valid.
INFO: Variable 'ZSCALER_CLIENT_ID' is set and valid.
INFO: Variable 'ZSCALER_CLIENT_SECRET' is set and valid.
INFO: Variable 'ZSCALER_VANITY_DOMAIN' is set and valid.
INFO: Variable 'ZSCALER_AGENT_PROMPT' is set and valid.
INFO: Variable 'PROJECT_ID' is set and valid.
INFO: Variable 'REGION' is set and valid.
--- All required environment variables are VALID. ---
INFO: Preparing for Cloud Run deployment...
INFO: Backing up './zscaler_agent/.env' to './zscaler_agent/.env.bak'.
INFO: Deploying ADK Agent to Cloud Run...

➡️ Allow unauthenticated invocations to [zscaler-mcp-agent] (y/N)?  N

Building and deploying new service...
✓ Building Container...
✓ Creating Revision...
✓ Routing traffic...
✓ Setting IAM Policy...
Done.
Service [zscaler-mcp-agent] revision has been deployed.
➡️ Service URL: https://zscaler-mcp-agent-xxxxx.us-central1.run.app
SUCCESS: Cloud Run deployment completed successfully.
```

</details>

> [!NOTE]
> By default the service has IAM authentication enabled. Follow steps below to enable access to yourself and your team.

### Granting Access to Cloud Run Service

1. Go to Cloud Run > Services > select `zscaler-mcp-agent` (checkbox)
2. Click `Permissions` at the top
3. Click `Add principal`
4. Add the users you want to provide access to with `Cloud Run Invoker` role
5. Wait for propagation

### Accessing the Service

Users can access the service using a local proxy:

```bash
gcloud run services proxy zscaler-mcp-agent --project PROJECT-ID --region YOUR-REGION
```

Then access the agent locally at `http://localhost:8080`.

## Deploying to Vertex AI Agent Engine and registering on Agentspace

This section covers deployment to Vertex AI Agent Engine.

### Prerequisites

1. Create a GCS bucket for staging artifacts in the same project:

```bash
gsutil mb -l us-central1 gs://your-agent-engine-staging-bucket
```

1. Update your `.env` file:

```bash
AGENT_ENGINE_STAGING_BUCKET=gs://your-agent-engine-staging-bucket
```

### Deploy to Agent Engine

```bash
cd examples/adk/
./adk_agent_operations.sh agent_engine_deploy
```

<details>

<summary><b>Sample Output - Agent Engine Deployment</b></summary>

```bash
INFO: Operation mode selected: 'agent_engine_deploy'.
--- Validating required environment variables for 'agent_engine_deploy' mode ---
--- All required environment variables are VALID. ---
INFO: Preparing for Agent Engine deployment...
INFO: Deploying ADK Agent to Agent Engine...
Copying agent source code...
Initializing Vertex AI...
Deploying to agent engine...

➡️ AgentEngine created. Resource name: projects/123456789/locations/us-central1/reasoningEngines/3670952665795123456

SUCCESS: Agent Engine deployment completed successfully.
```

</details>

**Copy the Agent Engine Number** from the output (e.g., `3670952665795123456`).

### Register with Agentspace

1. Go to [Agentspace](https://console.cloud.google.com/gen-app-builder/engines) in Google Cloud Console
2. Create an App (Type - Agentspace)
3. Note down the app name (e.g., `zscaler-security-agent-app_1750057151234`)
4. Enable Discovery Engine API for your project
5. Provide the following roles to the Discovery Engine Service Account:
   - Vertex AI Viewer
   - Vertex AI User

Update your `.env` file:

```bash
PROJECT_NUMBER=your-project-number
AGENT_LOCATION=global
REASONING_ENGINE_NUMBER=your-reasoning-engine-number
AGENT_SPACE_APP_NAME=your-agentspace-app-name
```

Then register:

```bash
./adk_agent_operations.sh agentspace_register
```

<details>

<summary><b>Sample Output - Agentspace Registration</b></summary>

```bash
INFO: Operation mode selected: 'agentspace_register'.
--- All required environment variables are VALID. ---
INFO: Registering ADK Agent with AgentSpace...
{
  "name": "projects/123456/locations/global/collections/default_collection/engines/zscaler-security-agent-app/assistants/default_assistant/agents/2662627860861234567",
  "displayName": "Zscaler MCP Agent",
  "description": "Allows users to interact with Zscaler Zero Trust Exchange platform",
  "state": "ENABLED"
}

SUCCESS: AgentSpace registration completed successfully.
```

</details>

Now you can access the agent in your Agentspace application!

### Deregistering an Agent

To remove an agent from Agentspace:

```bash
# List agents
curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_ID/locations/global/collections/default_collection/engines/$AGENT_SPACE_APP_NAME/assistants/default_assistant/agents"

# Delete agent (replace AGENT_NUMBER)
curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_ID/locations/global/collections/default_collection/engines/$AGENT_SPACE_APP_NAME/assistants/default_assistant/agents/AGENT_NUMBER"
```

## Securing access, Evaluating, Optimizing performance and costs

### Securing Access

1. **Local runs**: Make sure you are not using a shared machine
2. **Cloud Run deployment**: Use [IAM authentication](https://cloud.google.com/run/docs/securing/managing-access#control-service-or-job-access) (default behavior)
3. **Agentspace**: Provide access selectively by navigating to Agentspace > Apps > Your App > Integration > Grant Permissions with the `Discovery Engine User` role

### Evaluating

It is advised to evaluate the agent for the trajectory it takes and the output it produces. You can use [ADK documentation](https://google.github.io/adk-docs/evaluate/) to evaluate this agent. You can also test with different models.

### Optimizing Performance and Costs

Various native performance improvements are already part of the codebase. You can further optimize:

1. **Control conversation history**: Set `MAX_PREV_USER_INTERACTIONS` in your `.env` file. Default `-1` sends all conversations; recommended value is `5` for cost optimization.

2. **Choose the right model**: Use the appropriate [Gemini Model](https://ai.google.dev/gemini-api/docs/models#model-variations) for your use case:
   - `gemini-2.0-flash` - Fast, cost-effective (recommended for most use cases)
   - `gemini-2.0-pro` - More capable, higher cost
   - `gemini-1.5-flash` - Legacy, still supported

### Limiting Zscaler Services

You can limit which Zscaler services are available to the agent by setting:

```bash
# Only enable ZIA and ZPA
ZSCALER_MCP_SERVICES=zia,zpa
```

Available services: `zcc`, `zdx`, `zeasm`, `zia`, `zidentity`, `zpa`, `ztw`
