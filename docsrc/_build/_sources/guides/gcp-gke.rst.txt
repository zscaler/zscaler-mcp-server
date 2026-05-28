.. _gcp-gke:

GCP GKE Deployment
==================

This guide walks you through deploying the Zscaler Integrations MCP Server to **Google Kubernetes Engine** (GKE). The unified ``gcp_mcp_operations.py`` script provisions an Autopilot cluster on demand (or reuses an existing one), generates the manifests, applies them, and wires up GCP Secret Manager for credential delivery.

Prerequisites
-------------

- `gcloud CLI <https://cloud.google.com/sdk/docs/install>`__ installed and authenticated (``gcloud auth login``)
- A GCP project with billing enabled
- ``kubectl`` installed (``brew install kubernetes-cli`` on macOS, ``gcloud components install kubectl`` otherwise)
- Zscaler OneAPI credentials (``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_VANITY_DOMAIN``, ``ZSCALER_CUSTOMER_ID``)

Required GCP APIs
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   gcloud services enable \
     container.googleapis.com \
     secretmanager.googleapis.com \
     compute.googleapis.com \
     --project YOUR_PROJECT_ID

Required IAM Roles
~~~~~~~~~~~~~~~~~~

The default Compute Engine service account (``PROJECT_NUMBER-compute@developer.gserviceaccount.com``) needs:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Role
     - Purpose
   * - ``roles/secretmanager.secretAccessor``
     - Read Zscaler credentials from GCP Secret Manager at runtime
   * - ``roles/iam.workloadIdentityUser``
     - Bind the Kubernetes ``ServiceAccount`` to the GCP service account

.. code-block:: bash

   PROJECT_ID="your-project"
   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
   SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SA" --role="roles/iam.workloadIdentityUser"

Quick Start
-----------

.. code-block:: bash

   cd integrations/google/gcp
   python gcp_mcp_operations.py deploy

When prompted for the deployment target, select **GKE**. The script then asks for:

- **GCP project ID** and **region / zone** (defaults pulled from ``.env`` if present)
- **Cluster mode** — create a new GKE Autopilot cluster (PoC / testing) or use an existing cluster (production)
- **Cluster name** — defaults to ``zscaler-mcp-cluster`` for new clusters
- **Kubernetes namespace** — defaults to ``default``
- **Container image** — defaults to ``zscaler/zscaler-mcp-server:latest`` from Docker Hub
- **GCP Secret Manager** — recommended (``y``). When enabled, the script provisions secrets and grants the runtime service account ``roles/secretmanager.secretAccessor``; when disabled, credentials are baked into the manifest as plain env values.
- **MCP auth mode** — JWT, API Key, Zscaler, or None

What the Script Does
~~~~~~~~~~~~~~~~~~~~

1. Verifies ``kubectl`` and ``gcloud`` are installed and the user is logged in
2. Enables the GKE API on the target project
3. Creates the GKE Autopilot cluster (if requested) — this typically takes 5–10 minutes
4. Runs ``gcloud container clusters get-credentials`` to set the kubectl context
5. (Secret Manager path) creates Zscaler secrets in Secret Manager and grants IAM access
6. Generates a Kubernetes manifest (``Deployment`` + ``Service`` of type ``LoadBalancer``)
7. Applies the manifest with ``kubectl apply``
8. Polls for the LoadBalancer external IP
9. Updates Claude Desktop and Cursor configs with ``http://<EXTERNAL_IP>/mcp``

Operations
----------

.. code-block:: bash

   python gcp_mcp_operations.py status      # cluster state, pod, and service
   python gcp_mcp_operations.py logs        # kubectl logs deployment/zscaler-mcp-server -f
   python gcp_mcp_operations.py destroy     # tear down (full or partial — see below)
   python gcp_mcp_operations.py destroy -y  # non-interactive teardown

**Destroy behavior:**

- If the script created the cluster (``new`` mode), ``destroy`` deletes the cluster and any per-deployment GCP resources.
- If you supplied an existing cluster, ``destroy`` removes only the K8s ``Deployment`` and ``Service`` we created — your cluster and any other workloads remain intact.

Direct ``kubectl`` access works after deployment — the script sets your kubectl context to the cluster automatically:

.. code-block:: bash

   kubectl get pods -n default -l app=zscaler-mcp-server
   kubectl get svc zscaler-mcp-server -n default
   kubectl describe deployment zscaler-mcp-server -n default

GCP Secret Manager Integration
------------------------------

When you answer **Yes** to "Use GCP Secret Manager for credentials?", the script:

1. Stores each Zscaler credential as a separate secret in Secret Manager (with the canonical naming convention ``zscaler-client-id``, ``zscaler-client-secret``, ``zscaler-vanity-domain``, ``zscaler-customer-id``, ``zscaler-cloud``)
2. Grants ``roles/secretmanager.secretAccessor`` to the project's default Compute Engine service account
3. Configures the Pod with ``ZSCALER_MCP_GCP_SECRET_MANAGER=true`` and ``GCP_PROJECT_ID=<project>``

The MCP server's built-in credential loader fetches each secret at startup before the server initializes — no wrapper scripts or container changes required. See :doc:`gcp-cloud-run` for the full naming convention table.

To rotate a credential:

.. code-block:: bash

   echo -n "new-client-secret" | \
     gcloud secrets versions add zscaler-client-secret --data-file=-

   kubectl rollout restart deployment/zscaler-mcp-server -n default

Authentication Modes
--------------------

GKE supports four MCP client authentication modes (the same set as Cloud Run):

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Mode
     - Description
     - Client Auth Header
   * - **JWT**
     - Validate JWTs against a JWKS endpoint
     - ``Authorization: Bearer <JWT>``
   * - **API Key**
     - Shared secret (auto-generated if not provided)
     - ``Authorization: Bearer <api-key>``
   * - **Zscaler**
     - Validate via OneAPI client credentials
     - ``Authorization: Basic base64(id:secret)``
   * - **None**
     - No authentication — development only
     - No header

When authentication is enabled, the script generates the appropriate ``Authorization`` header and writes it into your Claude Desktop and Cursor configs alongside the LoadBalancer URL.

Manual Deployment
-----------------

If you prefer a hand-rolled manifest, here is a minimal reference that mirrors what the script generates (Secret Manager path):

.. code-block:: yaml

   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: zscaler-mcp-server
     namespace: default
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
           - name: ZSCALER_MCP_ALLOW_HTTP
             value: "true"
           - name: ZSCALER_MCP_DISABLE_HOST_VALIDATION
             value: "true"
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: zscaler-mcp-server
     namespace: default
   spec:
     type: LoadBalancer
     selector:
       app: zscaler-mcp-server
     ports:
     - port: 80
       targetPort: 8000

You will also need a Kubernetes ``ServiceAccount`` (``zscaler-mcp-sa``) bound to a GCP service account that holds ``roles/secretmanager.secretAccessor`` via Workload Identity. The script handles all of this end-to-end.

Connecting Clients
------------------

The script updates Claude Desktop and Cursor automatically. If you need to configure a client manually:

**Claude Desktop:**

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "http://<EXTERNAL_IP>/mcp",
           "--allow-http",
           "--header",
           "Authorization: Basic <base64(client_id:client_secret)>"
         ]
       }
     }
   }

**Cursor (``mcp.json``):**

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "url": "http://<EXTERNAL_IP>/mcp",
         "headers": {
           "Authorization": "Basic <base64(client_id:client_secret)>"
         }
       }
     }
   }

For HTTPS endpoints (e.g. when you place an Ingress with TLS in front of the LoadBalancer), drop the ``--allow-http`` flag.

Production Hardening
--------------------

The default deployment exposes plain HTTP via a ``LoadBalancer`` Service for simplicity. For production:

- **TLS** — front the Service with an `Ingress + Google-managed certificate <https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs>`__ or NGINX Ingress + ``cert-manager`` (Let's Encrypt).
- **Internal-only ingress** — switch the Service to ``ClusterIP`` and expose via an internal LB or a private Ingress if clients are inside the VPC.
- **Replicas / HPA** — scale beyond the default single replica (``kubectl scale deployment zscaler-mcp-server --replicas=3``) and add an ``HorizontalPodAutoscaler``.
- **Network policies** — restrict pod ingress to the Ingress controller / known clients only.

Troubleshooting
---------------

**Pod stuck in ``Pending``** — usually an Autopilot resource constraint. Run ``kubectl describe pod <pod>`` to see the scheduler events.

**``CrashLoopBackOff`` with ``permission denied`` on Secret Manager** — confirm the project's default Compute Engine service account has ``roles/secretmanager.secretAccessor`` (the script grants this; rerun if you skipped Secret Manager originally).

**LoadBalancer external IP stays ``<pending>``** — the script polls for up to 5 minutes. Beyond that, GKE/GCP is still provisioning the Standard Load Balancer; ``kubectl get svc zscaler-mcp-server -w`` will show it eventually. Verify the project has the Compute Engine API enabled and a default network.

**``Connection refused`` from clients** — check the firewall (``gcloud compute firewall-rules list``) and confirm the Service shows ``EXTERNAL-IP`` with port 80 open.

References
----------

- `integrations/google/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/google>`__ — full integration source, env templates, and per-client configuration examples
- :doc:`gcp-cloud-run` — Cloud Run deployment guide (sister target)
- :doc:`gcp-compute-engine-vm` — Compute Engine VM deployment guide
- `GKE Autopilot <https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview>`__
- `Workload Identity on GKE <https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity>`__
- `GCP Secret Manager <https://cloud.google.com/secret-manager/docs>`__
