.. _gcp-cloud-run:

GCP Cloud Run Deployment
========================

This guide walks you through deploying the Zscaler Integrations MCP Server to Google Cloud Run with optional GCP Secret Manager integration for secure credential storage.

Prerequisites
-------------

- `gcloud CLI <https://cloud.google.com/sdk/docs/install>`_ installed and authenticated
- A GCP project with billing enabled
- Zscaler OneAPI credentials (``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_VANITY_DOMAIN``, ``ZSCALER_CUSTOMER_ID``)

Automated Deployment (Recommended)
-----------------------------------

The ``integrations/google/gcp/gcp_mcp_operations.py`` script provides an interactive deployment experience with support for Cloud Run, GKE, and Compute Engine VM targets:

.. code-block:: bash

   cd integrations/google/gcp
   python gcp_mcp_operations.py deploy

The script:

- Reads credentials from your ``.env`` file (or prompts interactively)
- Optionally stores credentials in GCP Secret Manager
- Deploys the container to Cloud Run with ``zscaler`` authentication mode
- Generates ``Authorization: Basic`` headers from your Zscaler OneAPI credentials
- Auto-configures Claude Desktop and Cursor client configs
- Supports ``--teardown`` for easy service deletion

**Options:**

.. code-block:: bash

   cd integrations/google/gcp
   python gcp_mcp_operations.py deploy       # Interactive guided deployment
   python gcp_mcp_operations.py status       # Check deployment
   python gcp_mcp_operations.py logs         # Stream logs
   python gcp_mcp_operations.py destroy      # Tear down

Authentication
~~~~~~~~~~~~~~

The script defaults to **Zscaler auth mode** — clients authenticate with the same Zscaler OneAPI credentials (``client_id:client_secret``) via HTTP Basic auth. No external Identity Provider, JWT setup, or API keys are required.

The script automatically:

1. Sets ``ZSCALER_MCP_AUTH_ENABLED=true`` and ``ZSCALER_MCP_AUTH_MODE=zscaler`` on the container
2. Generates ``base64(client_id:client_secret)`` for the ``Authorization: Basic`` header
3. Configures Claude Desktop (via ``mcp-remote --header``) and Cursor (via native ``headers``) with the auth credentials

Manual Deployment
-----------------

Deploy directly with ``gcloud``:

.. code-block:: bash

   gcloud run deploy zscaler-mcp-server \
     --image=zscaler/zscaler-mcp-server:latest \
     --region=us-central1 \
     --platform=managed \
     --port=8000 \
     --args="--transport,streamable-http,--host,0.0.0.0,--port,8000" \
     --set-env-vars="\
   ZSCALER_CLIENT_ID=your-client-id,\
   ZSCALER_CLIENT_SECRET=your-client-secret,\
   ZSCALER_VANITY_DOMAIN=your-domain,\
   ZSCALER_CUSTOMER_ID=your-customer-id,\
   ZSCALER_CLOUD=production,\
   ZSCALER_MCP_ALLOW_HTTP=true,\
   ZSCALER_MCP_DISABLE_HOST_VALIDATION=true,\
   ZSCALER_MCP_AUTH_ENABLED=true,\
   ZSCALER_MCP_AUTH_MODE=zscaler" \
     --memory=512Mi \
     --allow-unauthenticated

.. warning::

   Credentials passed as ``--set-env-vars`` are visible in the Cloud Console. Use GCP Secret Manager for production deployments.

GCP Secret Manager Integration
-------------------------------

The Docker image includes a built-in credential loader for GCP Secret Manager. When enabled, the server fetches Zscaler API credentials at startup — no wrapper scripts or container modifications required.

**How It Works:**

1. Container starts and checks ``ZSCALER_MCP_GCP_SECRET_MANAGER``
2. If ``true``, fetches each credential from Secret Manager using Application Default Credentials
3. Sets values as environment variables before the MCP server initializes

**Naming Convention:**

Environment variable names are converted to Secret Manager IDs by lowercasing and replacing underscores with hyphens:

.. list-table::
   :header-rows: 1
   :widths: 40 40

   * - Environment Variable
     - Secret Manager ID
   * - ``ZSCALER_CLIENT_ID``
     - ``zscaler-client-id``
   * - ``ZSCALER_CLIENT_SECRET``
     - ``zscaler-client-secret``
   * - ``ZSCALER_VANITY_DOMAIN``
     - ``zscaler-vanity-domain``
   * - ``ZSCALER_CUSTOMER_ID``
     - ``zscaler-customer-id``
   * - ``ZSCALER_CLOUD``
     - ``zscaler-cloud``

Step 1: Create Secrets
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   PROJECT_ID="your-gcp-project"

   echo -n "your-client-id" | \
     gcloud secrets create zscaler-client-id \
       --data-file=- --replication-policy=automatic --project=$PROJECT_ID

   echo -n "your-client-secret" | \
     gcloud secrets create zscaler-client-secret \
       --data-file=- --replication-policy=automatic --project=$PROJECT_ID

   # Repeat for zscaler-vanity-domain, zscaler-customer-id, zscaler-cloud

Step 2: Grant IAM Access
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
   SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

   for SECRET in zscaler-client-id zscaler-client-secret zscaler-vanity-domain \
                 zscaler-customer-id zscaler-cloud; do
     gcloud secrets add-iam-policy-binding $SECRET \
       --member="serviceAccount:$SA_EMAIL" \
       --role="roles/secretmanager.secretAccessor" \
       --project=$PROJECT_ID --quiet
   done

Step 3: Deploy with Secret Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   gcloud run deploy zscaler-mcp-server \
     --image=zscaler/zscaler-mcp-server:latest \
     --region=us-central1 \
     --set-env-vars="\
   ZSCALER_MCP_GCP_SECRET_MANAGER=true,\
   GCP_PROJECT_ID=$PROJECT_ID,\
   ZSCALER_MCP_ALLOW_HTTP=true,\
   ZSCALER_MCP_DISABLE_HOST_VALIDATION=true,\
   ZSCALER_MCP_AUTH_ENABLED=true,\
   ZSCALER_MCP_AUTH_MODE=zscaler" \
     --args="--transport,streamable-http,--host,0.0.0.0,--port,8000" \
     --port=8000 --memory=512Mi --allow-unauthenticated

GKE Deployment
~~~~~~~~~~~~~~

.. code-block:: yaml

   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: zscaler-mcp-server
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: zscaler-mcp-server
     template:
       metadata:
         labels:
           app: zscaler-mcp-server
       spec:
         serviceAccountName: zscaler-mcp-sa
         containers:
         - name: zscaler-mcp
           image: zscaler/zscaler-mcp-server:latest
           args: ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
           ports:
           - containerPort: 8000
           env:
           - name: ZSCALER_MCP_GCP_SECRET_MANAGER
             value: "true"
           - name: GCP_PROJECT_ID
             value: "your-gcp-project"

Connecting Clients
-------------------

Claude Desktop
~~~~~~~~~~~~~~

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "https://your-service.run.app/mcp",
           "--header",
           "Authorization: Basic <base64(client_id:client_secret)>"
         ]
       }
     }
   }

Generate the Base64 value:

.. code-block:: bash

   echo -n "your-client-id:your-client-secret" | base64

Cursor
~~~~~~

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "url": "https://your-service.run.app/mcp",
         "headers": {
           "Authorization": "Basic <base64(client_id:client_secret)>"
         }
       }
     }
   }

Credential Rotation
--------------------

.. code-block:: bash

   # Update the secret value
   echo -n "new-client-secret" | \
     gcloud secrets versions add zscaler-client-secret --data-file=-

   # Restart the service to pick up the new version
   gcloud run services update zscaler-mcp-server --region=us-central1

Troubleshooting
----------------

**401 Unauthorized:**

- Verify the ``Authorization: Basic`` header contains valid ``base64(client_id:client_secret)``
- Confirm ``ZSCALER_MCP_AUTH_ENABLED=true`` and ``ZSCALER_MCP_AUTH_MODE=zscaler`` are set on the container

**Permission denied accessing secret:**

.. code-block:: bash

   gcloud secrets add-iam-policy-binding zscaler-client-secret \
     --member="serviceAccount:YOUR_SA_EMAIL" \
     --role="roles/secretmanager.secretAccessor"

**Viewing logs:**

.. code-block:: bash

   gcloud run services logs read zscaler-mcp-server --region=us-central1 --limit=50
