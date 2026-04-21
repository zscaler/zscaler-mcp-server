.. _azure-deployment-guide:

Azure Deployment
================

This guide walks you through deploying the Zscaler Integrations MCP Server to Microsoft Azure with the interactive ``azure_mcp_operations.py`` script. Three deployment targets are supported:

.. list-table::
   :header-rows: 1
   :widths: 25 35 25 15

   * - Target
     - Description
     - Image / Package
     - Status
   * - **Azure Container Apps**
     - Managed, serverless containers (recommended)
     - Docker Hub: ``zscaler/zscaler-mcp-server:latest``
     - GA
   * - **Azure Virtual Machine**
     - Ubuntu 22.04, self-managed
     - PyPI: ``zscaler-mcp-server``
     - GA
   * - **Azure Kubernetes Service (AKS)**
     - Kubernetes Deployment + LoadBalancer Service
     - Docker Hub: ``zscaler/zscaler-mcp-server:latest``
     - **Preview**

All three targets use **Azure Key Vault** for secret storage by default (Container Apps + AKS via Workload Identity Federation, VM via direct injection at deploy time). The same script also creates and manages **Azure AI Foundry** agents that call the deployed MCP server as a tool.

Prerequisites
-------------

- `Azure CLI <https://aka.ms/installazurecli>`__ (``az``) — logged in via ``az login``
- `Node.js <https://nodejs.org/>`__ — required by ``npx mcp-remote`` (Claude Desktop bridge)
- Zscaler OneAPI credentials (``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_VANITY_DOMAIN``, ``ZSCALER_CUSTOMER_ID``)
- For AKS: ``kubectl`` installed (``brew install kubernetes-cli`` on macOS)
- For OIDCProxy auth: an OIDC provider app registration (Entra ID, Okta, Auth0, etc.)
- For VM: SSH key pair (the script can generate one on demand)

Authentication Modes
--------------------

The script supports five MCP client authentication modes. Container Apps and VM support all five; AKS Preview supports four (OIDCProxy is on the roadmap).

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Mode
     - Description
     - Client Auth Header
   * - **OIDCProxy**
     - OAuth 2.1 + Dynamic Client Registration via your OIDC provider (browser login)
     - Handled automatically by ``mcp-remote``
   * - **JWT**
     - Validate JWTs against a JWKS endpoint
     - ``Authorization: Bearer <JWT>``
   * - **API Key**
     - Shared secret, auto-generated if not provided
     - ``Authorization: Bearer <api-key>``
   * - **Zscaler**
     - Validate via OneAPI client credentials
     - ``Authorization: Basic base64(id:secret)``
   * - **None**
     - No authentication — development only
     - No header

Quick Start
-----------

.. code-block:: bash

   cd integrations/azure
   python azure_mcp_operations.py deploy

The script prompts for:

1. **Deployment target** — Container Apps, VM, or AKS Preview
2. **Credential source** — load from a ``.env`` file or enter manually
3. **Auth mode** — OIDCProxy, JWT, API Key, Zscaler, or None
4. **Azure options** — resource group, region, Key Vault, deployment-specific options

When the deployment finishes, the script automatically updates your Claude Desktop and Cursor configurations with the new MCP server URL and the appropriate auth header.

MCP Server Operations
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Description
   * - ``deploy``
     - Interactive guided deployment (Container Apps, VM, or AKS Preview)
   * - ``status``
     - Show deployment status and health
   * - ``logs``
     - Stream container / VM / pod logs
   * - ``ssh``
     - SSH into the VM (VM deployments only)
   * - ``destroy``
     - Tear down all Azure resources. For AKS with an existing cluster, removes only the K8s ``Deployment`` + ``Service``.

.. code-block:: bash

   python azure_mcp_operations.py status      # check health
   python azure_mcp_operations.py logs        # stream logs
   python azure_mcp_operations.py destroy -y  # non-interactive teardown

Container Apps Deployment
-------------------------

Container Apps is the recommended path for most deployments — Azure handles scaling, ingress, and TLS termination automatically.

- **Image** — Docker Hub: ``zscaler/zscaler-mcp-server:latest`` (no build required)
- **TLS** — Automatic HTTPS via Azure Container Apps ingress
- **Scaling** — Azure manages 1–3 replicas by default
- **Secrets** — Stored in Azure Key Vault and injected at startup via system-assigned managed identity

VM Deployment
-------------

Ubuntu 22.04 VM with the MCP server installed from PyPI (``zscaler-mcp-server``) and managed by ``systemd``.

- **Self-managed** — full control over the VM (SSH, packages, updates)
- **systemd service** — automatic startup and restart on failure
- **NSG configured** — port 22 (SSH) and port 8000 (MCP) opened
- **Secrets** — Key Vault is mandatory; values are pulled at deploy time and rendered into the systemd unit file

VM service management:

.. code-block:: bash

   # SSH into the VM (or use the script wrapper)
   python azure_mcp_operations.py ssh

   # On the VM:
   sudo systemctl status zscaler-mcp     # check status
   sudo journalctl -u zscaler-mcp -f     # stream logs
   sudo systemctl restart zscaler-mcp    # restart service

   # Environment file:
   /opt/zscaler-mcp/env

AKS Deployment (Preview)
------------------------

.. note::

   **Status: Preview.** AKS support is fully functional for ``jwt``, ``api-key``, ``zscaler``, and ``none`` auth modes and has been validated end-to-end with cluster creation, ``LoadBalancer`` Service, and the Docker Hub image. Credentials are stored in Azure Key Vault by default and pulled at runtime via Workload Identity Federation + the Key Vault CSI driver. **OIDCProxy auth, TLS Ingress, and HPA are still planned for AKS GA.**

Deploys the MCP server to an Azure Kubernetes Service cluster as a ``Deployment`` exposed via a ``Service`` of type ``LoadBalancer``.

- **Cluster lifecycle** — create a brand-new AKS cluster (PoC / testing) or use an existing cluster (production)
- **Container image** — same Docker Hub image as Container Apps (``zscaler/zscaler-mcp-server:latest``)
- **External access** — Azure Standard Load Balancer with public IP
- **Resource defaults** — ``200m``–``1000m`` CPU and ``512Mi``–``1Gi`` memory per pod, single replica
- **Namespace** — defaults to ``default``, configurable
- **Credential storage:**

  - **Azure Key Vault (default, recommended).** Workload Identity Federation + Key Vault CSI driver. The script provisions the vault, the User-Assigned Managed Identity (UAMI), the federated credential bound to the pod's ``ServiceAccount``, and the ``SecretProviderClass``. Pods consume secrets via ``valueFrom.secretKeyRef`` against a synced Kubernetes ``Secret``.
  - **Plain env vars (PoC).** Credentials are baked into the Deployment manifest at deploy time — fine for short demos, not for production.

- **Cleanup** — if the script created the cluster, ``destroy`` deletes the entire resource group; if you supplied an existing cluster, ``destroy`` removes only the K8s resources we created plus the per-deployment UAMI and federated credential (the Key Vault is preserved).

Operations on AKS:

.. code-block:: bash

   python azure_mcp_operations.py status      # AKS provisioning state, pod, and service
   python azure_mcp_operations.py logs        # kubectl logs deployment/zscaler-mcp-server -f
   python azure_mcp_operations.py destroy     # full or partial teardown (see above)

Direct ``kubectl`` access works after deployment — the script sets your kubectl context to the cluster automatically:

.. code-block:: bash

   kubectl get pods -n default -l app=zscaler-mcp-server
   kubectl get svc zscaler-mcp-server -n default
   kubectl describe deployment zscaler-mcp-server -n default

Known limitations (Preview):

- **OIDCProxy auth is not supported on AKS today** — use ``jwt``, ``api-key``, ``zscaler``, or ``none``.
- **No Ingress controller** — the script provisions a ``LoadBalancer`` Service that exposes plain HTTP on port 80. For production, place this behind Application Gateway or NGINX Ingress with ``cert-manager`` for TLS (requires a DNS A record pointing at the cluster's ingress LoadBalancer).
- **Single replica by default** — for HA, scale via ``kubectl scale deployment zscaler-mcp-server --replicas=3`` or edit the generated ``.aks-manifest.yaml``.

Azure AI Foundry Agent Integration
----------------------------------

For organizations using `Azure AI Foundry <https://ai.azure.com>`__, the same script can create a managed Foundry agent (powered by GPT-4o or GPT-4) that calls the deployed MCP server as a tool. End users interact with the agent in natural language and the agent decides which Zscaler tools to call.

**Prerequisites:**

- Azure AI Foundry project at `ai.azure.com <https://ai.azure.com>`__
- Azure OpenAI deployment of GPT-4o or GPT-4
- A deployed MCP server (Container Apps, VM, or AKS — from the steps above)
- Python packages: ``pip install azure-ai-projects azure-ai-agents azure-identity``
- Azure CLI authenticated: ``az login``

MCP Server Authentication from Foundry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Azure AI Foundry no longer accepts authentication headers passed inline through ``MCPTool.headers``. Any header containing words like ``secret``, ``key``, ``token``, or ``authorization`` is rejected with ``invalid_payload``::

   Headers that can include sensitive information are not allowed in the headers
   property for MCP tools. Use project_connection_id instead.

The supported pattern is to register a **Custom keys connection** in the Foundry project that holds the headers, and reference it via ``MCPTool.project_connection_id``. Foundry then injects the connection's keys as request headers when calling the MCP server.

**One-time portal setup** (required before ``agent_create`` will succeed when an MCP auth mode that needs headers is selected):

1. Open your project at `ai.azure.com <https://ai.azure.com>`__.
2. Left navigation: **Management center** → **Connected resources**.
3. Click **+ New connection** → **Custom keys**.
4. Connection name: ``zscaler-mcp-headers`` (the script's default; override via ``AZURE_FOUNDRY_CONNECTION_NAME``).
5. Mark each row as a **secret** and add the keys for your MCP auth mode:

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - MCP Auth Mode
     - Custom Keys to Add
     - Source
   * - ``zscaler``
     - ``X-Zscaler-Client-ID`` + ``X-Zscaler-Client-Secret``
     - OneAPI credentials
   * - ``api-key``
     - ``X-MCP-API-Key``
     - MCP API key
   * - ``none``
     - *(no connection needed)*
     - —

6. Click **Save**, then run ``agent_create``.

The connection name is read from ``AZURE_FOUNDRY_CONNECTION_NAME`` (env var or ``.env``), defaulting to ``zscaler-mcp-headers``. The data-plane SDK (``azure-ai-projects`` v2.0.x) cannot create connections — only read them — so the portal step is currently required. Connection CRUD via the management plane is on the follow-up roadmap.

The script's ``agent_create`` command probes the connection at runtime: if it exists, it proceeds silently; if it's missing, it prints copy-paste-ready portal instructions and exits before mutating anything in Foundry.

Foundry Agent Operations
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Command
     - Flags
     - Description
   * - ``agent_create``
     -
     - Create a Foundry agent with Zscaler MCP tools. Reads the project endpoint, model name, and connection name from ``.env`` (or prompts).
   * - ``agent_status``
     -
     - Show agent name, version, model, MCP server URL, and project endpoint.
   * - ``agent_chat``
     - ``-m "..."``
     - Start an interactive multi-turn chat. Optionally pass an initial message.
   * - ``agent_destroy``
     - ``-y``
     - Delete the Foundry agent. Pass ``-y`` to skip the confirmation prompt.

.. code-block:: bash

   # 1. Deploy the MCP server (if you haven't already)
   python azure_mcp_operations.py deploy

   # 2. One-time: create the Custom keys connection in the portal (see above)

   # 3. Create the Foundry agent
   python azure_mcp_operations.py agent_create

   # 4. Chat
   python azure_mcp_operations.py agent_chat
   python azure_mcp_operations.py agent_chat -m "list ZPA segment groups"

   # 5. Manage
   python azure_mcp_operations.py agent_status
   python azure_mcp_operations.py agent_destroy -y

After ``agent_create`` succeeds, the script prints a deep link straight into the new Foundry experience for the agent. The chat command exposes:

- **Animated spinner** with a live elapsed-time counter while the model thinks
- **Per-response token usage** (input, output, total)
- **Wall-clock latency** for each request/response
- **Tool approval flow** — ``require_approval="always"`` is set by default, so you confirm each Zscaler tool call before it runs
- **Multi-turn context** — proper response chaining preserves conversation history
- **Session summary** — total duration and cumulative token count on exit

Finding the Agent in the Foundry Portal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Agents created by ``agent_create`` are **Prompt Agents** in the new Foundry experience (versioned, type ``prompt``). To find them in the portal:

1. Open the project at `ai.azure.com <https://ai.azure.com>`__.
2. Make sure the **"New Foundry"** toggle (top-right) is **ON** — Prompt Agents only appear in the new experience.
3. Left nav: **Build** → **Agents** → **Agents** tab.
4. Select ``zscaler-mcp-agent`` (Type: ``prompt``, Version: ``1``).
5. Use the **Playground** to test interactively, or **Publish** to share with your tenant.

.. note::

   **Two agent surfaces in Foundry — heads-up.** The "Agents" tab in the *new* Foundry experience lists **Prompt Agents** (created by this script). The classic experience also has an "Agents" tab that lists **Assistant API** agents (type ``asst_xxxx``, no versioning). They are different platforms in the same project. If you previously opened the Playground or used another tool, you may see leftover ``Agent###`` rows in classic — they're unrelated to ``zscaler-mcp-agent`` and safe to leave alone.

Connecting Clients
------------------

After deployment, the script automatically updates your Claude Desktop (``claude_desktop_config.json``) and Cursor (``mcp.json``) configurations with the new MCP server URL and the auth header for the selected mode. If you need to configure a client manually, see the `integrations/azure README <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/azure>`__ for full per-client examples.

For HTTP endpoints (VM, AKS without Ingress), Claude Desktop requires the ``--allow-http`` flag to ``mcp-remote``. The script adds this automatically when the deployed URL is HTTP.

Credential Sources
------------------

**From a ``.env`` file.** Copy ``integrations/azure/env.properties`` to ``.env`` and fill in the values. During deployment, select "From a .env file" and provide the file path.

**Interactive prompts.** Select "Enter manually" and the script will prompt for each credential. Secrets are entered via ``getpass`` (hidden input).

Required environment variables for all auth modes:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Variable
     - Description
   * - ``ZSCALER_CLIENT_ID``
     - OneAPI client ID from ZIdentity
   * - ``ZSCALER_CLIENT_SECRET``
     - OneAPI client secret
   * - ``ZSCALER_VANITY_DOMAIN``
     - Zscaler vanity domain
   * - ``ZSCALER_CUSTOMER_ID``
     - Zscaler customer ID
   * - ``ZSCALER_CLOUD``
     - Zscaler cloud (e.g. ``production``, ``beta``)

Troubleshooting
---------------

**"Non-HTTPS URLs are only allowed for localhost"** in Claude Desktop:

   Add ``--allow-http`` to your ``mcp-remote`` args. The deployment script does this automatically for HTTP endpoints; only manual configurations need the flag.

**Claude Desktop shows "Server disconnected":**

   Run ``python azure_mcp_operations.py status`` to check the deployment health, ``... logs`` to inspect the server logs, and ``curl http://<PUBLIC_IP>:8000/mcp`` (or the HTTPS Container Apps URL) to verify reachability. For VM deployments, also confirm the NSG allows inbound on the MCP port.

**Foundry ``agent_create`` errors with "Headers that can include sensitive information are not allowed":**

   You're hitting the policy described in *MCP Server Authentication from Foundry* above. Create the Custom keys connection in the portal and re-run; the script will pick it up via ``project_connection_id``.

**Foundry ``agent_create`` errors with "Foundry connection 'zscaler-mcp-headers' was not found":**

   Same fix — the connection name in your ``.env`` (``AZURE_FOUNDRY_CONNECTION_NAME``) must match a Custom keys connection that exists in the project's **Connected resources**.

**OIDCProxy callback URL issues:**

   For OIDCProxy mode, register the callback URL in your identity provider:

   .. code-block:: text

      http://<PUBLIC_IP>:8000/auth/callback

   Some providers also require explicitly allowing HTTP callback URLs for non-HTTPS deployments.

Security
--------

- **Secrets in Key Vault.** All credentials are stored in Azure Key Vault by default for Container Apps, mandatory for VM, and the recommended path on AKS via Workload Identity Federation.
- **Five auth modes.** Choose the level appropriate for the environment — production deployments should use OIDCProxy, JWT, or Zscaler.
- **TLS.** Container Apps provides automatic HTTPS. VM deployments default to HTTP (front with a load balancer + TLS for production). AKS Preview exposes plain HTTP today; place behind Application Gateway / NGINX + ``cert-manager`` for production.
- **NSG.** VM deployments configure Network Security Group rules for SSH and the MCP port.
- **HMAC confirmations.** Destructive Zscaler operations require cryptographic confirmation tokens (controlled by ``ZSCALER_MCP_SKIP_CONFIRMATIONS`` and ``ZSCALER_MCP_CONFIRMATION_TTL``).
- **Read-only by default.** Write tools are disabled unless explicitly enabled via ``ZSCALER_MCP_WRITE_ENABLED=true`` and ``ZSCALER_MCP_WRITE_TOOLS``.

References
----------

- `integrations/azure/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/azure>`__ — full integration source, env templates, and per-client configuration examples
- `Azure AI Foundry <https://ai.azure.com>`__
- `Azure Container Apps <https://learn.microsoft.com/en-us/azure/container-apps/>`__
- `Azure Kubernetes Service <https://learn.microsoft.com/en-us/azure/aks/>`__
- `Azure Key Vault <https://learn.microsoft.com/en-us/azure/key-vault/>`__
