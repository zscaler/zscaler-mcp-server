.. _guide-helm-chart:

Kubernetes (Helm Chart)
=======================

Deploy the Zscaler MCP Server to **any** Kubernetes cluster via Helm — EKS, GKE, AKS, OpenShift, Rancher, k3s, Talos, kind / minikube for local dev. The chart is cluster-vendor-agnostic and never calls ``aws``, ``az``, or ``gcloud``. You bring the cluster; the chart brings the workload.

.. note::

   **Need a hyperscaler-managed deploy instead?** This isn't for you. Use:

   - **AWS Bedrock AgentCore** — :doc:`amazon-bedrock-agentcore`
   - **Azure Container Apps / VM / AKS-Preview script** — :doc:`azure-deployment`
   - **GCP Cloud Run / GKE-script / Compute Engine** — :doc:`gcp-cloud-run`

   Those scripts provision and manage the underlying cloud infrastructure (clusters, networks, IAM, Key Vaults, etc.) end-to-end. **This chart assumes you already have a Kubernetes cluster** and want to install one more workload into it.

When to Use This vs. Other Deploy Options
-----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - You want to…
     - Use
   * - Install into an existing K8s cluster (any cloud, any distro, on-prem)
     - **This chart**
   * - Wire into ArgoCD / Flux / a corporate GitOps pipeline
     - **This chart** (Helm-source ``Application`` or ``HelmRelease``)
   * - Run locally on Claude Code / Cursor / Gemini CLI without containers
     - ``uvx zscaler-mcp``
   * - Run a single container without Kubernetes
     - :doc:`docker`
   * - Have AWS host the runtime for you on Bedrock
     - :doc:`amazon-bedrock-agentcore`
   * - Stand up brand-new Azure infra and deploy on top
     - :doc:`azure-deployment`
   * - Stand up brand-new GCP infra and deploy on top
     - :doc:`gcp-cloud-run`

This chart is the right answer when **the cluster is already a fact** and your operating model treats every workload as a Helm release.

Why a Helm chart at all?
------------------------

The MCP server is an HTTP service that needs credentials, an ingress, a few ``kubectl``-flavoured knobs (replicas, resources, probes), and the option to bring its own pre-existing Kubernetes ``Secret``. Helm encodes that contract once and lets it run identically on:

- **EKS** with IRSA-fed Secrets via `External Secrets Operator (ESO) <https://external-secrets.io/>`__ → AWS Secrets Manager
- **GKE** with Workload Identity + Secret Manager via ESO
- **AKS** with Workload Identity Federation + Azure Key Vault via ESO **or** the Key Vault CSI driver
- **OpenShift** with ``Secret`` provisioned by the OpenShift secret-injection operator
- **Vanilla / on-prem K8s** with `HashiCorp Vault Agent Injector <https://developer.hashicorp.com/vault/docs/platform/k8s/injector>`__, `SealedSecrets <https://github.com/bitnami-labs/sealed-secrets>`__, or sops-encrypted GitOps
- **Local dev** (kind / minikube / colima) with an inline ``Secret`` rendered by the chart

In each of those cases, the cluster-side Helm command is **identical**; only the source-of-credentials story differs.

Prerequisites
-------------

- Kubernetes **1.24+**
- `Helm 3.0+ <https://helm.sh/docs/intro/install/>`__
- A Zscaler OneAPI client — ``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET`` (or ``ZSCALER_PRIVATE_KEY``), ``ZSCALER_VANITY_DOMAIN``, and ``ZSCALER_CUSTOMER_ID`` (for ZPA tools)
- (Optional) `cert-manager <https://cert-manager.io/>`__ for auto-issued TLS certs
- (Optional) `External Secrets Operator <https://external-secrets.io/>`__ or another secret-injection mechanism for production credential storage
- (Optional) An Ingress controller (NGINX, Traefik, ALB, etc.) **or** Gateway API v1 if you want to expose the MCP endpoint outside the cluster

Credential Setup — Choose Your Path
-----------------------------------

The chart never asks you to translate your ``.env`` into ``values.yaml`` syntax. Pick the path that matches how your team already manages secrets:

.. list-table::
   :header-rows: 1
   :widths: 5 35 60

   * - #
     - Path
     - When to use
   * - 1
     - **Interactive script** (``helm_mcp_operations.py deploy``)
     - Local dev, kind / minikube, day-1 walkthroughs. **Recommended starting point.**
   * - 2
     - **Manual ``kubectl + helm``** with ``.env``
     - CI pipelines, GitOps reconcilers (Argo, Flux).
   * - 3
     - **Inline ``--set`` credentials**
     - Quick local smoke tests, templating pipelines. Never use for production.
   * - 4
     - **Pre-existing ``Secret``** (GitOps)
     - ArgoCD / Flux + SealedSecrets / sops-encrypted manifests.
   * - 5
     - **External Secrets Operator**
     - Production with AWS Secrets Manager / Azure Key Vault / GCP Secret Manager / Vault / 1Password.

All five paths converge on the same chart contract: the Deployment uses ``envFrom: secretRef:`` to bulk-import every key in the Secret as an environment variable. Whatever ``ZSCALER_MCP_*`` / ``ZSCALER_*`` variable you put in your ``.env`` (or remote-secret backend) flows into the container without translation.

Quick Start
-----------

1. Interactive guided install via ``helm_mcp_operations.py`` (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The chart ships an interactive deployment script that mirrors the GCP / Azure ones. It reads your existing ``.env``, materialises it into a Kubernetes ``Secret``, runs ``helm upgrade --install``, waits for the rollout, starts ``kubectl port-forward``, and writes Cursor / Claude Desktop entries automatically.

.. code-block:: bash

   python integrations/helm-chart/helm_mcp_operations.py deploy

You'll be asked, in order: which kubectl context to target, the path to your ``.env`` file (defaults to the project root), namespace name, Helm release name, image tag, and how to expose the endpoint (port-forward / Ingress / none).

Follow-up commands:

.. code-block:: bash

   python integrations/helm-chart/helm_mcp_operations.py status    # release + pods + svc + port-forward
   python integrations/helm-chart/helm_mcp_operations.py logs      # tail Deployment logs
   python integrations/helm-chart/helm_mcp_operations.py configure # re-write Cursor / Claude configs
   python integrations/helm-chart/helm_mcp_operations.py test      # run `helm test` smoke probe
   python integrations/helm-chart/helm_mcp_operations.py destroy   # uninstall + optional ns deletion

2. Manual install with raw ``helm`` + an existing ``.env``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   kubectl create namespace zscaler-mcp
   kubectl -n zscaler-mcp create secret generic zscaler-mcp-creds \
     --from-env-file=/path/to/.env

   helm install zscaler-mcp \
     ./integrations/helm-chart/charts/zscaler-mcp-server \
     --namespace zscaler-mcp \
     --set secret.create=false \
     --set secret.existingName=zscaler-mcp-creds

   kubectl -n zscaler-mcp rollout status deployment/zscaler-mcp-zscaler-mcp-server
   kubectl -n zscaler-mcp port-forward svc/zscaler-mcp-zscaler-mcp-server 8000:80 &
   curl http://localhost:8000/health

3. Local dev with inline ``--set`` credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Not for production.**

.. code-block:: bash

   helm install zscaler-mcp \
     ./integrations/helm-chart/charts/zscaler-mcp-server \
     --namespace zscaler-mcp --create-namespace \
     --set secret.values.clientId=$ZSCALER_CLIENT_ID \
     --set secret.values.clientSecret=$ZSCALER_CLIENT_SECRET \
     --set secret.values.vanityDomain=$ZSCALER_VANITY_DOMAIN \
     --set secret.values.customerId=$ZSCALER_CUSTOMER_ID

4. Production with pre-existing Secret (GitOps-friendly)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the Secret out-of-band (External Secrets Operator, Vault Agent Injector, SealedSecrets — your choice). The chart will reference it by name:

.. code-block:: bash

   kubectl create namespace zscaler-mcp
   kubectl -n zscaler-mcp create secret generic zscaler-mcp-creds \
     --from-literal=ZSCALER_CLIENT_ID="$ZSCALER_CLIENT_ID" \
     --from-literal=ZSCALER_CLIENT_SECRET="$ZSCALER_CLIENT_SECRET" \
     --from-literal=ZSCALER_VANITY_DOMAIN="$ZSCALER_VANITY_DOMAIN" \
     --from-literal=ZSCALER_CUSTOMER_ID="$ZSCALER_CUSTOMER_ID"

   helm install zscaler-mcp \
     ./integrations/helm-chart/charts/zscaler-mcp-server \
     --namespace zscaler-mcp \
     --values - <<'EOF'
   secret:
     create: false
     existingName: zscaler-mcp-creds
   ingress:
     enabled: true
     className: nginx
     hosts:
       - host: zscaler-mcp.example.com
         paths:
           - path: /
             pathType: Prefix
     tls:
       - secretName: zscaler-mcp-tls
         hosts:
           - zscaler-mcp.example.com
   certificate:
     enabled: true
     secretName: zscaler-mcp-tls
     commonName: zscaler-mcp.example.com
     dnsNames:
       - zscaler-mcp.example.com
     issuerRef:
       name: letsencrypt-production
       kind: ClusterIssuer
   EOF

5. Production with External Secrets Operator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assumes ESO is installed and a ``ClusterSecretStore`` is wired to your secret backend (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, HashiCorp Vault, 1Password, etc.).

.. code-block:: yaml

   # external-secret.yaml — apply this BEFORE helm install
   apiVersion: external-secrets.io/v1
   kind: ExternalSecret
   metadata:
     name: zscaler-mcp-creds
     namespace: zscaler-mcp
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: my-cluster-secret-store
       kind: ClusterSecretStore
     target:
       name: zscaler-mcp-creds
     data:
       - secretKey: ZSCALER_CLIENT_ID
         remoteRef: { key: zscaler/mcp/client_id }
       - secretKey: ZSCALER_CLIENT_SECRET
         remoteRef: { key: zscaler/mcp/client_secret }
       - secretKey: ZSCALER_VANITY_DOMAIN
         remoteRef: { key: zscaler/mcp/vanity_domain }
       - secretKey: ZSCALER_CUSTOMER_ID
         remoteRef: { key: zscaler/mcp/customer_id }

.. code-block:: bash

   kubectl apply -f external-secret.yaml
   helm install zscaler-mcp \
     ./integrations/helm-chart/charts/zscaler-mcp-server \
     --namespace zscaler-mcp \
     --set secret.create=false \
     --set secret.existingName=zscaler-mcp-creds

Configuration Reference
-----------------------

Every key below is also documented inline in `charts/zscaler-mcp-server/values.yaml <https://github.com/zscaler/zscaler-mcp-server/blob/master/integrations/helm-chart/charts/zscaler-mcp-server/values.yaml>`__.

Image
~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Key
     - Default
     - Description
   * - ``image.repository``
     - ``zscaler/zscaler-mcp-server``
     - Docker Hub repo. Override to point at a private mirror / Marketplace ECR.
   * - ``image.tag``
     - ``latest``
     - Docker Hub currently publishes only the ``latest`` floating tag. Pin in production via ``image.digest``.
   * - ``image.digest``
     - ``""``
     - Pin by digest (``sha256:...``). When set, wins over ``image.tag``. Recommended for production.
   * - ``image.pullPolicy``
     - ``IfNotPresent``
     -
   * - ``imagePullSecrets``
     - ``[]``
     - Image pull Secrets for private registries.

Service / Ingress / HTTPRoute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ingress.enabled`` and ``httproute.enabled`` are **mutually exclusive** — picking both fails the install with a clear error.

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Key
     - Default
     - Description
   * - ``service.type``
     - ``ClusterIP``
     - ``ClusterIP`` / ``NodePort`` / ``LoadBalancer``.
   * - ``service.port``
     - ``80``
     - Service port.
   * - ``service.targetPort``
     - ``8000``
     - Container port — matches the MCP server default.
   * - ``ingress.enabled``
     - ``false``
     - Generate a ``networking.k8s.io/v1`` Ingress.
   * - ``ingress.className``
     - ``""``
     - e.g. ``nginx``, ``traefik``, ``alb``.
   * - ``httproute.enabled``
     - ``false``
     - Generate a Gateway API v1 HTTPRoute instead.
   * - ``certificate.enabled``
     - ``false``
     - Generate a cert-manager ``Certificate``.

MCP runtime (``mcp.*``)
~~~~~~~~~~~~~~~~~~~~~~~

These map 1:1 to the ``ZSCALER_MCP_*`` env vars the server already reads.

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Key
     - Default
     - Maps to
   * - ``mcp.transport``
     - ``streamable-http``
     - ``--transport``
   * - ``mcp.host``
     - ``0.0.0.0``
     - ``--host``
   * - ``mcp.port``
     - ``8000``
     - ``--port``
   * - ``mcp.auth.enabled``
     - ``true``
     - ``ZSCALER_MCP_AUTH_ENABLED``
   * - ``mcp.auth.mode``
     - ``zscaler``
     - ``ZSCALER_MCP_AUTH_MODE``
   * - ``mcp.toolsets.enabled``
     - ``""``
     - ``ZSCALER_MCP_TOOLSETS``
   * - ``mcp.writeTools.enabled``
     - ``false``
     - ``ZSCALER_MCP_WRITE_ENABLED``
   * - ``mcp.tls.allowHttp``
     - ``true``
     - ``ZSCALER_MCP_ALLOW_HTTP``. Required when TLS terminates at the Ingress / Gateway.

MCP Client Configuration
------------------------

Once the chart is installed, point your MCP client at the Service / Ingress hostname. The endpoint is ``/mcp``.

Recommended — ``helm_mcp_operations.py configure``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you installed the chart via Quick Start path 1, the script already wrote the right entry into Cursor + Claude Desktop. To rebuild those configs at any time:

.. code-block:: bash

   python integrations/helm-chart/helm_mcp_operations.py configure

Manually — derive the auth header from the cluster Secret
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   kubectl --namespace zscaler-mcp get secret zscaler-mcp-creds \
       -o jsonpath='{.data.ZSCALER_CLIENT_ID}:{.data.ZSCALER_CLIENT_SECRET}' \
     | base64 -d | tr -d '\n' | base64

Prefix the resulting string with the literal ``Basic`` (followed by a space) to form the ``Authorization`` header value.

Port-forwarded local dev (no Ingress)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   kubectl -n zscaler-mcp port-forward svc/zscaler-mcp-zscaler-mcp-server 8000:80
   # Then point your MCP client at http://localhost:8000/mcp

Operations
----------

Smoke-test the install:

.. code-block:: bash

   helm test zscaler-mcp -n zscaler-mcp

Inspect the rendered manifests without installing:

.. code-block:: bash

   helm template zscaler-mcp \
     ./integrations/helm-chart/charts/zscaler-mcp-server \
     --set secret.create=false \
     --set secret.existingName=zscaler-mcp-creds \
     --set ingress.enabled=true \
     --set ingress.className=nginx

Upgrade in place:

.. code-block:: bash

   helm upgrade zscaler-mcp \
     ./integrations/helm-chart/charts/zscaler-mcp-server \
     -n zscaler-mcp \
     -f my-values.yaml

Uninstall:

.. code-block:: bash

   helm uninstall zscaler-mcp -n zscaler-mcp

Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Symptom
     - Likely cause / Fix
   * - ``helm install`` fails with *"ingress.enabled and httproute.enabled are mutually exclusive"*
     - Pick one and set the other to ``false``.
   * - ``helm install`` fails with *"secret.create is false but secret.existingName is empty"*
     - Set ``secret.existingName`` or flip ``secret.create: true``.
   * - Pod CrashLoopBackOff with ``ZSCALER_VANITY_DOMAIN missing``
     - Confirm ``secret.envKeys.vanityDomain`` matches the actual key name in your pre-existing Secret.
   * - ``/health`` returns 200 but ``/mcp`` returns 401
     - Auth header missing or wrong format. ``zscaler`` expects ``Authorization: Basic``; ``jwt`` / ``api-key`` expect ``Authorization: Bearer``.
   * - MCP client sees zero tools
     - Entitlement filter trimmed everything. Your OneAPI client isn't entitled to the loaded toolsets. Either request entitlements, or set ``mcp.disableEntitlementFilter: true`` (emergency override only).

For deeper debugging:

.. code-block:: bash

   kubectl -n zscaler-mcp logs deploy/zscaler-mcp-zscaler-mcp-server --tail=200 -f
   kubectl -n zscaler-mcp describe pod -l app.kubernetes.io/name=zscaler-mcp-server
   kubectl -n zscaler-mcp get events --sort-by='.lastTimestamp' | tail -30

For the full chart contract — every value key, every template, the deployer script reference, GitOps integration recipes, and the complete troubleshooting matrix — see `integrations/helm-chart/README.md <https://github.com/zscaler/zscaler-mcp-server/blob/master/integrations/helm-chart/README.md>`__.
