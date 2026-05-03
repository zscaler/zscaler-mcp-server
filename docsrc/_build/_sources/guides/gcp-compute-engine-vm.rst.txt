.. _gcp-compute-engine-vm:

GCP Compute Engine VM Deployment
================================

This guide walks you through deploying the Zscaler Integrations MCP Server to a **Google Compute Engine VM** running Debian 12, with the server installed from PyPI (``pip install zscaler-mcp[gcp]``) and managed by ``systemd``.

The unified ``gcp_mcp_operations.py`` script provisions the VM, opens a firewall rule for the MCP port, runs a startup script that installs the package and registers the service, and (optionally) wires up GCP Secret Manager for credential delivery.

When to Pick the VM Target
--------------------------

The VM target is useful when:

- Your organization enforces ``constraints/iam.allowedPolicyMemberDomains`` and Cloud Run's ``allUsers`` ingress is blocked. The VM avoids Cloud Run's IAM layer entirely — the MCP server's own auth (JWT, API Key, Zscaler) is the sole gatekeeper.
- You need direct OS-level control (custom networking, sidecar processes, package management).
- You want a long-lived deployment without containers or Kubernetes.
- You're running a PoC and want the simplest possible "single VM" footprint.

For managed / serverless alternatives see :doc:`gcp-cloud-run` and :doc:`gcp-gke`.

Prerequisites
-------------

- `gcloud CLI <https://cloud.google.com/sdk/docs/install>`__ installed and authenticated (``gcloud auth login``)
- A GCP project with billing enabled
- Zscaler OneAPI credentials (``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_VANITY_DOMAIN``, ``ZSCALER_CUSTOMER_ID``)

Required GCP APIs
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   gcloud services enable \
     compute.googleapis.com \
     secretmanager.googleapis.com \
     --project YOUR_PROJECT_ID

Required IAM Roles
~~~~~~~~~~~~~~~~~~

If you enable Secret Manager, the VM's runtime service account (default Compute Engine service account ``PROJECT_NUMBER-compute@developer.gserviceaccount.com``) needs:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Role
     - Purpose
   * - ``roles/secretmanager.secretAccessor``
     - Read Zscaler credentials from GCP Secret Manager at startup

.. code-block:: bash

   PROJECT_ID="your-project"
   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
   SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"

Quick Start
-----------

.. code-block:: bash

   cd integrations/google/gcp
   python gcp_mcp_operations.py deploy

When prompted for the deployment target, select **Compute Engine VM**. The script then asks for:

- **GCP project ID** and **zone** (defaults pulled from ``.env`` if present; default zone ``us-central1-a``)
- **VM name** — defaults to ``zscaler-mcp-server``
- **Machine type** — defaults to ``e2-medium``
- **MCP port** — defaults to ``8000``
- **MCP auth mode** — JWT, API Key, Zscaler, or None
- **GCP Secret Manager** — recommended (``y``)

What the Script Does
~~~~~~~~~~~~~~~~~~~~

1. Verifies ``gcloud`` is installed and the user is logged in
2. Enables the Compute Engine API on the target project
3. Creates a VPC firewall rule (``allow-mcp-<port>``) opening the MCP port for ``mcp-server``-tagged instances
4. (Secret Manager path) creates Zscaler secrets in Secret Manager and grants IAM access
5. Generates a startup script that:

   - Installs Python and ``pip``
   - Runs ``pip install zscaler-mcp[gcp]`` (the ``gcp`` extra includes the Secret Manager client)
   - Writes ``/opt/zscaler-mcp/env`` with the resolved configuration
   - Installs and starts a ``zscaler-mcp.service`` ``systemd`` unit

6. Provisions the VM with the ``mcp-server`` network tag and the embedded startup script
7. Polls the instance for its external IP
8. Updates Claude Desktop and Cursor configs with ``http://<EXTERNAL_IP>:<port>/mcp``

Operations
----------

.. code-block:: bash

   python gcp_mcp_operations.py status      # check VM and service health
   python gcp_mcp_operations.py logs        # stream systemd journal
   python gcp_mcp_operations.py ssh         # SSH into the VM
   python gcp_mcp_operations.py destroy     # delete VM + firewall rule
   python gcp_mcp_operations.py destroy -y  # non-interactive teardown

VM Service Management
~~~~~~~~~~~~~~~~~~~~~

Once deployed, you can manage the MCP server directly from the VM:

.. code-block:: bash

   python gcp_mcp_operations.py ssh

   # On the VM:
   sudo systemctl status zscaler-mcp     # service status
   sudo journalctl -u zscaler-mcp -f     # stream logs
   sudo systemctl restart zscaler-mcp    # restart service

   # Configuration / credentials:
   cat /opt/zscaler-mcp/env

   # Re-install / upgrade the package:
   sudo /opt/zscaler-mcp/venv/bin/pip install --upgrade 'zscaler-mcp[gcp]'

GCP Secret Manager Integration
------------------------------

When you answer **Yes** to "Use GCP Secret Manager for credentials?", the script:

1. Stores each Zscaler credential as a separate secret (canonical names: ``zscaler-client-id``, ``zscaler-client-secret``, ``zscaler-vanity-domain``, ``zscaler-customer-id``, ``zscaler-cloud``)
2. Grants ``roles/secretmanager.secretAccessor`` to the VM's runtime service account
3. Configures the VM with ``ZSCALER_MCP_GCP_SECRET_MANAGER=true`` and ``GCP_PROJECT_ID=<project>``

The MCP server's built-in credential loader fetches each secret at startup before the server initializes — no wrapper scripts required. Without Secret Manager, credentials are written into ``/opt/zscaler-mcp/env`` as plain values.

To rotate a credential:

.. code-block:: bash

   echo -n "new-client-secret" | \
     gcloud secrets versions add zscaler-client-secret --data-file=-

   # Restart the service so it picks up the new version:
   gcloud compute ssh <VM_NAME> --zone <ZONE> \
     --command "sudo systemctl restart zscaler-mcp"

Authentication Modes
--------------------

The VM supports four MCP client authentication modes (same set as Cloud Run / GKE):

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
     - Validate via OneAPI client credentials (recommended for VM)
     - ``Authorization: Basic base64(id:secret)``
   * - **None**
     - No authentication — development only
     - No header

The script generates the appropriate ``Authorization`` header for the selected mode and writes it into your Claude Desktop and Cursor configs alongside the VM's external IP.

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
           "http://<EXTERNAL_IP>:8000/mcp",
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
         "url": "http://<EXTERNAL_IP>:8000/mcp",
         "headers": {
           "Authorization": "Basic <base64(client_id:client_secret)>"
         }
       }
     }
   }

The ``--allow-http`` flag is required by ``mcp-remote`` for non-localhost HTTP URLs. Drop it if you front the VM with a load balancer + TLS.

Production Hardening
--------------------

The default deployment exposes plain HTTP on the MCP port via a single firewall rule. For production:

- **TLS** — front the VM with an `external HTTPS Load Balancer + Google-managed certificate <https://cloud.google.com/load-balancing/docs/https/setting-up-https-serverless>`__, or terminate TLS on the VM with NGINX / Caddy + Let's Encrypt.
- **Restrict ingress** — replace the firewall rule's default ``0.0.0.0/0`` source range with your corporate CIDRs or VPC ranges (``--source-ranges``), or move the VM into a private subnet behind an internal LB.
- **Identity-Aware Proxy** — for browser-mediated access from ``@yourcompany.com`` users, place the VM behind an external HTTPS LB with `IAP <https://cloud.google.com/iap/docs/enabling-compute-howto>`__ enabled and grant ``roles/iap.httpsResourceAccessor`` to the appropriate principals.
- **OS hardening** — restrict SSH ingress to IAP / your bastion, and patch the VM regularly (``unattended-upgrades`` is installed by default on Debian 12).

Troubleshooting
---------------

**``Connection refused`` from clients** — confirm the firewall rule exists (``gcloud compute firewall-rules describe allow-mcp-8000``) and that the VM has the ``mcp-server`` network tag (``gcloud compute instances describe <VM_NAME> --zone <ZONE>``).

**Service fails to start with ``permission denied`` on Secret Manager** — verify the project's default Compute Engine service account has ``roles/secretmanager.secretAccessor``. If you ran the destroy/redeploy cycle, the binding may not have been re-applied — ``gcloud projects add-iam-policy-binding`` it again.

**``systemctl status zscaler-mcp`` shows ``activating (auto-restart)``** — check ``sudo journalctl -u zscaler-mcp -n 100`` for the underlying error. The most common causes are missing env vars in ``/opt/zscaler-mcp/env`` or transient network errors reaching ZIdentity at startup.

**``mcp-remote`` hangs in Claude Desktop** — verify the URL is reachable (``curl http://<EXTERNAL_IP>:8000/mcp``). If you're behind a corporate proxy, also try ``--allow-http`` on the ``mcp-remote`` command.

References
----------

- `integrations/google/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/google>`__ — full integration source, env templates, and per-client configuration examples
- :doc:`gcp-cloud-run` — Cloud Run deployment guide
- :doc:`gcp-gke` — GKE deployment guide
- `Compute Engine documentation <https://cloud.google.com/compute/docs>`__
- `GCP Secret Manager <https://cloud.google.com/secret-manager/docs>`__
- `Identity-Aware Proxy for HTTPS resources <https://cloud.google.com/iap/docs/enabling-compute-howto>`__
