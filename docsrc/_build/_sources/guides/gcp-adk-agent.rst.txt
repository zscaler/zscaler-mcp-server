.. _gcp-adk-agent:

GCP ADK Agent Deployment
========================

This guide walks you through deploying the **Zscaler ADK Agent** — a Gemini-powered AI agent built with the `Google Agent Development Kit <https://google.github.io/adk-docs/>`__ that uses the Zscaler MCP Server as its tool backend. Unlike the standalone MCP server deployments (Cloud Run, GKE, Compute Engine VM), the ADK agent **embeds** the MCP server as a co-located subprocess inside the agent container.

End users interact with the agent through natural language ("List all ZPA application segments", "Show me ZIA firewall rules for the Finance department"). The Gemini model interprets the request, decides which Zscaler tools to call, executes them via the embedded MCP server, and returns a natural-language response.

The unified ``adk_agent_operations.py`` script supports four deployment targets:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Target
     - Description
   * - **Local development**
     - Run on your workstation with ``adk web`` and a ``GOOGLE_API_KEY``
   * - **Google Cloud Run**
     - Deploy as a managed container with built-in web UI (Cloud Build → Artifact Registry → Cloud Run)
   * - **Vertex AI Agent Engine**
     - Fully managed agent hosting on Vertex AI
   * - **Google Agentspace**
     - Register an existing Agent Engine deployment in your enterprise agent catalog

Architecture
------------

The MCP server is **not** a separate service — it runs as a child process inside the agent container, communicating over stdio.

.. code-block:: text

   ┌─── Container / Host ───────────────────────────────────────────┐
   │                                                                 │
   │  ┌─── Process 1: ADK Agent (Python) ──────────────────────┐    │
   │  │  Gemini model + function calling                         │    │
   │  │  Listens on HTTP :8080 (Cloud Run) or :8000 (local)      │    │
   │  └────────────────┬───────────────────────────────────────┘    │
   │                   │ stdin/stdout (stdio transport)               │
   │  ┌────────────────▼───────────────────────────────────────┐    │
   │  │  Process 2: zscaler-mcp (subprocess)                    │    │
   │  │  280+ tools, Zscaler SDK → Zscaler APIs                 │    │
   │  └─────────────────────────────────────────────────────────┘    │
   └─────────────────────────────────────────────────────────────────┘

This is different from the standalone MCP server deployments (:doc:`gcp-cloud-run`, :doc:`gcp-gke`, :doc:`gcp-compute-engine-vm`), where the MCP server runs as its own networked service and external clients (Claude Desktop, Cursor) connect remotely over HTTPS.

When the ADK agent process starts, it spawns ``zscaler-mcp`` via ``uvx``, the ``CachedMCPToolset`` discovers and caches all available tools, and the agent begins answering user requests.

Prerequisites
-------------

- Python 3.11 or higher
- `Google ADK <https://google.github.io/adk-docs/>`__ installed (``pip install google-adk``)
- `uv <https://docs.astral.sh/uv/>`__ installed (used internally to run ``uvx zscaler-mcp``)
- Zscaler OneAPI credentials (``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_VANITY_DOMAIN``, ``ZSCALER_CUSTOMER_ID``)
- For **local** development: a Google API key from `Google AI Studio <https://aistudio.google.com/app/apikey>`__
- For **Cloud Run / Agent Engine / Agentspace**: a GCP project with billing enabled and the ``gcloud`` CLI authenticated

Required GCP APIs (Cloud Run / Agent Engine / Agentspace)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   gcloud services enable \
     run.googleapis.com \
     artifactregistry.googleapis.com \
     aiplatform.googleapis.com \
     cloudbuild.googleapis.com \
     --project YOUR_PROJECT_ID

Required IAM Roles (Cloud Run / Agent Engine)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default Compute Engine service account (``PROJECT_NUMBER-compute@developer.gserviceaccount.com``) needs:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Role
     - Purpose
   * - ``roles/storage.admin``
     - Cloud Build uploads source to Cloud Storage
   * - ``roles/artifactregistry.writer``
     - Cloud Build pushes the container image to Artifact Registry
   * - ``roles/aiplatform.user``
     - Cloud Run service calls Gemini via Vertex AI

.. code-block:: bash

   PROJECT_ID="your-project"
   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
   SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SA" --role="roles/storage.admin"
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SA" --role="roles/artifactregistry.writer"
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SA" --role="roles/aiplatform.user"

Configuration
-------------

Step 1 — Create the agent ``.env`` file:

.. code-block:: bash

   cd integrations/google/adk
   cp zscaler_agent/env.properties zscaler_agent/.env

Or run the operations script with no arguments to auto-create it:

.. code-block:: bash

   python adk_agent_operations.py

Step 2 — Edit ``zscaler_agent/.env``:

.. code-block:: bash

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

   # Optional: scope which MCP services / tools the agent can use
   ZSCALER_MCP_SERVICES=             # e.g. zia,zpa,zdx (empty = all)
   ZSCALER_MCP_WRITE_ENABLED=        # true/false (default: false)
   ZSCALER_MCP_WRITE_TOOLS=          # e.g. zpa_*,zia_*

   # Deployment (Cloud Run / Agent Engine / Agentspace)
   PROJECT_ID=your-gcp-project
   REGION=us-central1
   AGENT_ENGINE_STAGING_BUCKET=      # gs://your-bucket (Agent Engine only)

   # Agentspace (optional)
   PROJECT_NUMBER=
   AGENT_LOCATION=
   REASONING_ENGINE_NUMBER=
   AGENT_SPACE_APP_NAME=

Quick Start
-----------

.. code-block:: bash

   cd integrations/google/adk
   python adk_agent_operations.py deploy

The script presents a numbered menu — select the deployment target. It then validates required env vars, collects target-specific configuration, shows a deployment summary, and asks for confirmation before executing.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``deploy``
     - Interactive guided deployment (Local, Cloud Run, Agent Engine, or Agentspace)
   * - ``status``
     - Show current deployment status (URL, revision, etc.)
   * - ``logs``
     - Stream agent logs (Cloud Run / Agent Engine)
   * - ``destroy``
     - Tear down deployed resources
   * - ``destroy -y``
     - Non-interactive teardown

Local Development
~~~~~~~~~~~~~~~~~

Runs ``adk web`` locally using your ``GOOGLE_API_KEY``. The agent UI is available at ``http://localhost:8000``. No GCP project or IAM setup required.

Cloud Run
~~~~~~~~~

Builds the agent container from source via Cloud Build, pushes to Artifact Registry, and deploys to Cloud Run with the service name ``zscaler-agent-service``. The script:

1. Backs up your ``.env`` file
2. Removes ``GOOGLE_API_KEY`` and sets ``GOOGLE_GENAI_USE_VERTEXAI=True`` (Cloud Run uses Vertex AI for Gemini, not the public API)
3. Runs ``adk deploy cloud_run``
4. Saves deployment state for ``status`` / ``logs`` / ``destroy`` operations
5. Restores your ``.env`` file on exit (success or failure)

Vertex AI Agent Engine
~~~~~~~~~~~~~~~~~~~~~~

Deploys to Vertex AI Agent Engine with display name ``zscaler_agent``. Requires ``AGENT_ENGINE_STAGING_BUCKET`` set to a ``gs://`` bucket the deploy can stage artifacts into.

Google Agentspace
~~~~~~~~~~~~~~~~~

Registers an existing Agent Engine deployment with Google Agentspace via the Discovery Engine API. Requires the deployment to already exist, plus ``PROJECT_NUMBER``, ``REASONING_ENGINE_NUMBER``, and ``AGENT_SPACE_APP_NAME`` populated in ``.env``.

Authentication & MCP Server Security
------------------------------------

Because the MCP server runs as an in-process subprocess (stdio transport), the standard MCP HTTP auth modes (JWT, API key, OIDCProxy) **do not apply** in local mode — there is no HTTP surface to authenticate against. Cloud Run and Agent Engine deployments expose the agent (not the MCP server) over HTTPS through GCP's infrastructure.

Recommended security configuration for **Cloud Run / Agent Engine**:

.. code-block:: bash

   ZSCALER_MCP_ALLOW_HTTP=true
   ZSCALER_MCP_AUTH_ENABLED=false
   ZSCALER_MCP_DISABLE_HOST_VALIDATION=true

These are needed because:

- Cloud Run terminates TLS at the load balancer; the agent → MCP subprocess communication happens over local stdio (no HTTP), but if you ever switch transports, plain HTTP must be allowed.
- The MCP server's HTTP auth would conflict with Cloud Run's IAM-mediated access; let Cloud Run's identity layer handle inbound auth.
- Host validation is unnecessary when the agent is the only client.

The ``adk_agent_operations.py`` script warns about unconfigured security vars during deployment to help catch misconfigurations.

Cloud Run + Enterprise GCP IAM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enterprise GCP organizations enforcing ``constraints/iam.allowedPolicyMemberDomains`` will block ``allUsers`` access to Cloud Run. When deploying, answer ``N`` to "Allow unauthenticated invocations" and access the agent via:

.. code-block:: bash

   # Grant yourself invoker access
   gcloud run services add-iam-policy-binding zscaler-agent-service \
     --region REGION --member="user:YOUR_EMAIL" --role="roles/run.invoker"

   # Access via local proxy (handles IAM auth transparently)
   gcloud run services proxy zscaler-agent-service \
     --region REGION --project YOUR_PROJECT_ID
   # Then open http://localhost:8080

For multi-user access in enterprise orgs, place the Cloud Run service behind an external HTTPS Load Balancer with `Identity-Aware Proxy <https://cloud.google.com/iap/docs/enabling-cloud-run>`__ enabled and grant ``roles/iap.httpsResourceAccessor`` to the appropriate principals (a domain like ``domain:yourcompany.com``, an IdP group, or individual users).

Delete-Operation Confirmation (HMAC)
-------------------------------------

Delete tools are protected by the MCP server's cryptographic HMAC-SHA256 confirmation flow. When the agent calls a delete tool, the MCP server returns a ``CONFIRMATION REQUIRED`` message with a time-limited HMAC token. The agent presents the details to the user; on approval, the agent re-calls the tool with ``kwargs='{"confirmation_token": "<token>"}'``. The server verifies the token is bound to the exact tool name, parameters, and hasn't expired before executing.

This is transport-agnostic — it works the same in stdio (ADK), SSE, and streamable-http modes.

To disable confirmations for automation / CI:

.. code-block:: bash

   ZSCALER_MCP_SKIP_CONFIRMATIONS=true

Keep confirmations enabled for production deployments.

Example Prompts
---------------

Once the agent is running:

- "List all ZPA application segments"
- "Show me ZIA firewall rules for the Finance department"
- "What ZDX alerts are currently active?"
- "List EASM findings for my organization"
- "Show me shadow IT applications with high risk scores"
- "Check ZCC device enrollment status for my organization"
- "List all microsegmentation policy rules"

Troubleshooting
---------------

**``mcp-remote`` / ``adk web`` complains about missing ``uvx``** — install ``uv`` (``brew install uv`` on macOS or ``pip install uv``).

**Cloud Run deployment fails with ``permission denied`` on Cloud Build** — confirm the project's default Compute Engine service account has ``roles/storage.admin`` and ``roles/artifactregistry.writer``. The Cloud Build UI usually surfaces the exact resource being denied.

**Cloud Run service returns 401 to all requests** — your org likely enforces ``constraints/iam.allowedPolicyMemberDomains``. Either deploy to an unauthenticated-friendly project, or follow the enterprise pattern above (deploy with ``--no-allow-unauthenticated`` + per-user invoker bindings, accessed via ``gcloud run services proxy``).

**Agent stalls indefinitely on a delete operation** — this happens when ADK's built-in ``require_confirmation`` is enabled but the client (e.g. ``adk web``) doesn't implement the ``adk_request_confirmation`` protocol. The integration uses the MCP server's HMAC confirmation flow instead (``CachedMCPToolset(require_confirmation=False)``); if you customized this back to ``True``, switch back.

References
----------

- `integrations/google/adk/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/google/adk>`__ — full ADK integration source, agent definition, and env templates
- :doc:`gcp-cloud-run`, :doc:`gcp-gke`, :doc:`gcp-compute-engine-vm` — standalone MCP server deployment guides (different architecture — see "Architecture" above)
- `Google ADK Documentation <https://google.github.io/adk-docs/>`__
- `Vertex AI Agent Engine <https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview>`__
- `Google Agentspace <https://cloud.google.com/agentspace>`__
