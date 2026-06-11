# Helm Chart Integration

Deploy the Zscaler MCP Server to **any** Kubernetes cluster via Helm — EKS, GKE, AKS, OpenShift, Rancher, k3s, Talos, kind / minikube for local dev. The chart is cluster-vendor-agnostic and never calls `aws`, `az`, or `gcloud`. You bring the cluster; the chart brings the workload.

> **Need a hyperscaler-managed deploy instead?** This isn't for you. Use:
>
> - **AWS Bedrock AgentCore** → [`integrations/aws/bedrock-agentcore/`](../aws/bedrock-agentcore/)
> - **Azure Container Apps / VM / AKS-Preview script** → [`integrations/azure/`](../azure/)
> - **GCP Cloud Run / GKE-script / Compute Engine** → [`integrations/google/gcp/`](../google/gcp/)
>
> Those scripts provision and manage the underlying cloud infrastructure (clusters, networks, IAM, Key Vaults, etc.) end-to-end. **This chart assumes you already have a Kubernetes cluster** and want to install one more workload into it.

## When to Use This vs. Other Deploy Options

| You want to… | Use |
|---|---|
| Install into an existing K8s cluster (any cloud, any distro, on-prem) | **This chart** |
| Wire into ArgoCD / Flux / a corporate GitOps pipeline | **This chart** (Helm-source `Application` or `HelmRelease`) |
| Run locally on Claude Code / Cursor / Gemini CLI without containers | `uvx zscaler-mcp` (see top-level `README.md`) |
| Run a single container without Kubernetes | `docker run zscaler/zscaler-mcp-server` (see [`docsrc/guides/docker.rst`](../../docsrc/guides/docker.rst)) |
| Have AWS host the runtime for you on Bedrock | [`integrations/aws/bedrock-agentcore/`](../aws/bedrock-agentcore/) |
| Stand up brand-new Azure infra and deploy on top | [`integrations/azure/`](../azure/) |
| Stand up brand-new GCP infra and deploy on top | [`integrations/google/gcp/`](../google/gcp/) |

This chart is the right answer when **the cluster is already a fact** and your operating model treats every workload as a Helm release.

## Why a Helm chart at all?

The MCP server is an HTTP service that needs credentials, an ingress, a few `kubectl`-flavoured knobs (replicas, resources, probes), and the option to bring its own pre-existing Kubernetes `Secret`. Helm encodes that contract once and lets it run identically on:

- **EKS** with IRSA-fed Secrets via [External Secrets Operator (ESO)](https://external-secrets.io/) → AWS Secrets Manager
- **GKE** with Workload Identity + Secret Manager via ESO
- **AKS** with Workload Identity Federation + Azure Key Vault via ESO **or** the Key Vault CSI driver
- **OpenShift** with `Secret` provisioned by the OpenShift secret-injection operator
- **Vanilla / on-prem K8s** with [HashiCorp Vault Agent Injector](https://developer.hashicorp.com/vault/docs/platform/k8s/injector), [SealedSecrets](https://github.com/bitnami-labs/sealed-secrets), or sops-encrypted GitOps
- **Local dev** (kind / minikube / colima) with an inline `Secret` rendered by the chart

In each of those cases, the cluster-side Helm command is **identical**; only the source-of-credentials story differs. That portability is what justifies the chart's existence.

## What the Chart Ships

```text
integrations/helm-chart/
├── README.md                                    ← this file
├── helm_mcp_operations.py                       ← interactive deployer (deploy/destroy/status/logs/configure/test)
└── charts/
    └── zscaler-mcp-server/
        ├── Chart.yaml
        ├── values.yaml
        ├── .helmignore
        └── templates/
            ├── _helpers.tpl
            ├── NOTES.txt                        ← printed by `helm install`
            ├── deployment.yaml
            ├── service.yaml
            ├── secret.yaml                      ← optional (when secret.create)
            ├── serviceaccount.yaml
            ├── ingress.yaml                     ← optional (ingress.enabled)
            ├── httproute.yaml                   ← optional (httproute.enabled)
            ├── certificate.yaml                 ← optional (cert-manager)
            ├── pdb.yaml                         ← optional (PodDisruptionBudget)
            ├── hpa.yaml                         ← optional (HorizontalPodAutoscaler)
            └── tests/
                └── test-connection.yaml         ← `helm test` smoke test
```

The Python deployer (`helm_mcp_operations.py`) is a thin orchestrator over `kubectl` + `helm` that follows the same pattern as `integrations/google/gcp/gcp_mcp_operations.py` and `integrations/azure/azure_mcp_operations.py`. It only depends on the stdlib + `kubectl` + `helm 3` — no cloud SDK, no `pip install`.

Every optional template is gated by an explicit boolean in `values.yaml` — no opt-out surprises.

## Prerequisites

- Kubernetes **1.24+**
- [Helm 3.0+](https://helm.sh/docs/intro/install/)
- A Zscaler OneAPI client — `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET` (or `ZSCALER_PRIVATE_KEY`), `ZSCALER_VANITY_DOMAIN`, and `ZSCALER_CUSTOMER_ID` (for ZPA tools). See the top-level [`README.md`](../../README.md) for credential setup.
- (Optional) [cert-manager](https://cert-manager.io/) for auto-issued TLS certs
- (Optional) [External Secrets Operator](https://external-secrets.io/) or another secret-injection mechanism for production credential storage
- (Optional) An Ingress controller (NGINX, Traefik, ALB, etc.) **or** Gateway API v1 if you want to expose the MCP endpoint outside the cluster

## Credential Setup — Choose Your Path

The chart never asks you to translate your `.env` into `values.yaml` syntax. Pick the path that matches how your team already manages secrets:

| # | Path | When to use |
|---|---|---|
| 1 | **Interactive script** (`helm_mcp_operations.py deploy`) | Local dev, kind / minikube, day-1 walkthroughs. **Recommended starting point.** |
| 2 | **Manual `kubectl + helm`** with `.env` | CI pipelines, GitOps reconcilers (Argo, Flux). |
| 3 | **Inline `--set` credentials** | Quick local smoke tests, templating pipelines. Never use for production. |
| 4 | **Pre-existing `Secret`** (GitOps) | ArgoCD / Flux + SealedSecrets / sops-encrypted manifests. |
| 5 | **External Secrets Operator** | Production with AWS Secrets Manager / Azure Key Vault / GCP Secret Manager / Vault / 1Password. |

Where credentials come from and where they end up, per path:

- **Path 1.** Your existing `.env` (defaults to the project root) → materialised into a chart-managed Kubernetes `Secret` via `kubectl create secret --from-env-file`.
- **Path 2.** Your `.env` → `kubectl create secret --from-env-file` → pre-existing `Secret` referenced by the chart via `secret.create=false`.
- **Path 3.** `--set secret.values.clientId=...` flags on the `helm install` command → chart-rendered `Secret` (`secret.create=true`). Values live in shell history — never use for production.
- **Path 4.** A Kubernetes `Secret` you create out-of-band before installing → chart references it via `secret.create=false` + `secret.existingName=<your-secret>`.
- **Path 5.** An `ExternalSecret` CR pulling from your secret backend → ESO materialises the K8s `Secret` → chart references it by name (same `secret.create=false` + `secret.existingName=…` flow as path 4).

All five paths converge on the same chart contract: the Deployment uses `envFrom: secretRef:` to bulk-import every key in the Secret as an environment variable. Whatever `ZSCALER_MCP_*` / `ZSCALER_*` variable you put in your `.env` (or remote-secret backend) flows into the container without translation.

> The five `Quick Start` examples below are numbered to match the table above.

## Quick Start

### 1. Interactive guided install via `helm_mcp_operations.py` (recommended)

The chart ships an interactive deployment script that mirrors the GCP / Azure ones — `integrations/helm-chart/helm_mcp_operations.py`. It reads your existing `.env`, materialises it into a Kubernetes `Secret`, runs `helm upgrade --install`, waits for the rollout, starts `kubectl port-forward`, and writes Cursor / Claude Desktop entries automatically.

```bash
python integrations/helm-chart/helm_mcp_operations.py deploy
```

You'll be asked, in order: which kubectl context to target, the path to your `.env` file (defaults to the project root), namespace name, Helm release name, image tag, and how to expose the endpoint (port-forward / Ingress / none). Then it does everything below in one shot:

1. Creates the namespace if missing.
2. Runs `kubectl create secret generic <release>-creds --from-env-file=.env` (idempotently, via `--dry-run=client | apply`). Every `ZSCALER_MCP_*` and `ZSCALER_*` variable in your `.env` becomes a key in the Secret — no translation into `values.yaml`.
3. `helm upgrade --install` with `secret.create=false` + `secret.existingName=<release>-creds`, plus the image / auth-mode / Ingress overrides you chose.
4. `kubectl rollout status` until the Deployment is healthy.
5. Background `kubectl port-forward` (when no Ingress was configured).
6. Writes the `zscaler-mcp-server` entry into `~/.cursor/mcp.json` and (on macOS) `~/Library/Application Support/Claude/claude_desktop_config.json` with the right `Authorization: Basic …` header.
7. Saves state to `.helm-deploy-state.json` so the follow-up commands (`status`, `logs`, `destroy`, `configure`, `test`) know what to target.

Follow-up commands:

```bash
python integrations/helm-chart/helm_mcp_operations.py status    # release + pods + svc + port-forward
python integrations/helm-chart/helm_mcp_operations.py logs      # tail Deployment logs
python integrations/helm-chart/helm_mcp_operations.py configure # re-write Cursor / Claude configs
python integrations/helm-chart/helm_mcp_operations.py test      # run `helm test` smoke probe
python integrations/helm-chart/helm_mcp_operations.py destroy   # uninstall + optional ns deletion
```

> Same pattern as `integrations/google/gcp/gcp_mcp_operations.py` and `integrations/azure/azure_mcp_operations.py` — if you've used either, this will feel familiar.

### 2. Manual install with raw `helm` + an existing `.env`

If you'd rather not run the Python helper (e.g. CI, GitOps reconciler), the three primitive commands the script runs for you are:

```bash
# 1) Materialise a Secret from your .env (same values, no translation).
kubectl create namespace zscaler-mcp
kubectl -n zscaler-mcp create secret generic zscaler-mcp-creds \
  --from-env-file=/path/to/.env

# 2) Install the chart pointing at that pre-existing Secret.
helm install zscaler-mcp \
  ./integrations/helm-chart/charts/zscaler-mcp-server \
  --namespace zscaler-mcp \
  --set secret.create=false \
  --set secret.existingName=zscaler-mcp-creds

# 3) Wait for the rollout and connect.
kubectl -n zscaler-mcp rollout status deployment/zscaler-mcp-zscaler-mcp-server
kubectl -n zscaler-mcp port-forward svc/zscaler-mcp-zscaler-mcp-server 8000:80 &
curl http://localhost:8000/health
```

> **Why this works:** `kubectl create secret --from-env-file` parses each `KEY=VALUE` line in your `.env` and turns it into a key inside the Secret. The chart's Deployment then does `envFrom: secretRef: <name>`, so every `ZSCALER_MCP_*` / `ZSCALER_*` variable in your `.env` flows into the container untouched.

### 3. Local dev with inline `--set` credentials

When you don't have a `.env` handy (or you're rendering values from a templating tool). Renders a `Secret` from the values you pass on the command line. **Not for production** — never commit a real `clientSecret` into a values file.

```bash
helm install zscaler-mcp \
  ./integrations/helm-chart/charts/zscaler-mcp-server \
  --namespace zscaler-mcp --create-namespace \
  --set secret.values.clientId=$ZSCALER_CLIENT_ID \
  --set secret.values.clientSecret=$ZSCALER_CLIENT_SECRET \
  --set secret.values.vanityDomain=$ZSCALER_VANITY_DOMAIN \
  --set secret.values.customerId=$ZSCALER_CUSTOMER_ID
```

Then port-forward to test:

```bash
kubectl -n zscaler-mcp port-forward svc/zscaler-mcp-zscaler-mcp-server 8000:80
curl http://localhost:8000/health
# expected: {"status":"healthy"}
```

### 4. Production with pre-existing Secret (GitOps-friendly)

Create the Secret out-of-band (External Secrets Operator, Vault Agent Injector, SealedSecrets — your choice). The chart will reference it by name:

```bash
# Example: bootstrap a Secret manually (replace this with your ESO/Vault flow)
kubectl create namespace zscaler-mcp
kubectl -n zscaler-mcp create secret generic zscaler-mcp-creds \
  --from-literal=ZSCALER_CLIENT_ID="$ZSCALER_CLIENT_ID" \
  --from-literal=ZSCALER_CLIENT_SECRET="$ZSCALER_CLIENT_SECRET" \
  --from-literal=ZSCALER_VANITY_DOMAIN="$ZSCALER_VANITY_DOMAIN" \
  --from-literal=ZSCALER_CUSTOMER_ID="$ZSCALER_CUSTOMER_ID"

# Install the chart pointing at the pre-existing Secret
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
podDisruptionBudget:
  enabled: true
  minAvailable: 1
EOF
```

### 5. Production with External Secrets Operator

Assumes ESO is installed and a `ClusterSecretStore` is wired to your secret backend (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, HashiCorp Vault, 1Password, etc.).

```yaml
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
    name: zscaler-mcp-creds            # the K8s Secret ESO will materialize
  data:
    - secretKey: ZSCALER_CLIENT_ID
      remoteRef: { key: zscaler/mcp/client_id }
    - secretKey: ZSCALER_CLIENT_SECRET
      remoteRef: { key: zscaler/mcp/client_secret }
    - secretKey: ZSCALER_VANITY_DOMAIN
      remoteRef: { key: zscaler/mcp/vanity_domain }
    - secretKey: ZSCALER_CUSTOMER_ID
      remoteRef: { key: zscaler/mcp/customer_id }
```

```bash
kubectl apply -f external-secret.yaml
helm install zscaler-mcp \
  ./integrations/helm-chart/charts/zscaler-mcp-server \
  --namespace zscaler-mcp \
  --set secret.create=false \
  --set secret.existingName=zscaler-mcp-creds
```

## Deployment Script Reference (`helm_mcp_operations.py`)

The script is a thin Python orchestrator over `kubectl` + `helm` — stdlib-only, no `pip install` required. Six subcommands cover the full lifecycle of a release.

### Subcommands

| Subcommand | Flags | Summary |
|---|---|---|
| `deploy` | _none_ | Interactive guided install — prompts for context / `.env` / namespace / release / image tag / expose mode / auth mode, then runs the full deploy. |
| `destroy` | `--yes` / `-y` | Uninstall the Helm release. `--yes` skips the confirmation prompt (CI / scripted teardown). |
| `status` | _none_ | Print release health, pod phases, Service + Ingress URLs, live port-forward PID, and the Secret name. Read-only. |
| `logs` | _none_ | Tail Deployment logs (`kubectl logs deploy/<release>-zscaler-mcp-server -f --tail=200`). |
| `configure` | _none_ | Re-write Cursor + Claude Desktop entries from the cluster Secret without redeploying. |
| `test` | _none_ | Run `helm test` against the bundled smoke pod (`/health` probe). |

What each subcommand does in detail:

- **`deploy`** — Creates the namespace if missing, materialises the Secret from `.env` via `kubectl create secret --from-env-file`, runs `helm upgrade --install`, then polls the rollout with live per-pod status. Detects `ImagePullBackOff` / `CreateContainerConfigError` / `CrashLoopBackOff` and exits early with a tailored recovery hint instead of waiting for the Helm timeout. When no Ingress is configured, starts a background `kubectl port-forward` and writes Cursor + Claude Desktop entries. Persists everything to `.helm-deploy-state.json`.
- **`destroy`** — Reads `.helm-deploy-state.json`, prints a summary of what will be removed (release / namespace ownership / Secret / port-forward), prompts for confirmation, runs `helm uninstall`, optionally deletes the namespace (only if `deploy` created it), removes the local port-forward, and clears the Cursor / Claude entries.
- **`status`** — Prints `helm status`, `kubectl get pods -l app.kubernetes.io/instance=<release>`, Service + Ingress URLs, the live port-forward PID (if any), and the Secret path. Never mutates the cluster.
- **`logs`** — Tails the Deployment logs. Ctrl-C exits cleanly.
- **`configure`** — Pulls `ZSCALER_CLIENT_ID` + `ZSCALER_CLIENT_SECRET` directly from the cluster Secret (works whether it's chart-managed or pre-existing), recomputes the `Authorization: Basic` header, ensures a background port-forward is running, and writes the entries into `~/.cursor/mcp.json` + (on macOS) `~/Library/Application Support/Claude/claude_desktop_config.json`. Useful after credential rotation or when restoring an MCP client config on a new machine.
- **`test`** — Runs `helm test <release> -n <namespace>` against the bundled smoke pod (`templates/tests/test-connection.yaml`), which curls the in-cluster `/health` endpoint and asserts HTTP 200. Useful in CI to gate a chart upgrade.

### Preflight checks (all subcommands)

Every subcommand starts by validating:

1. `kubectl` and `helm` are both on `PATH`.
2. The active kubectl context can reach the API server (`kubectl get --raw=/healthz --request-timeout=5s`). If the cluster is unreachable (stopped kind, expired kubeconfig, VPN down) the script exits with a focused diagnostic instead of letting `helm` block silently.

### State file (`.helm-deploy-state.json`)

`deploy` writes a tiny JSON file in the working directory recording: kubectl context, namespace, namespace-ownership flag, Helm release name, image repo/tag, chart path, Secret name (chart-managed vs pre-existing), MCP URL (port-forward host or Ingress hostname), and the port-forward PID. Subsequent subcommands read it so you don't have to retype any of those values.

> Treat `.helm-deploy-state.json` like a local pointer file — it's safe to commit if you want a shared baseline for a team-managed cluster, but `destroy` deletes it so a fresh `deploy` cycles cleanly.

### Pod-startup recovery (built-in)

The `deploy` rollout-wait loop classifies pod state per iteration and bails out with a tailored hint on terminal failures (after a 15-second grace window):

| Terminal state | What the script prints |
|---|---|
| `ImagePullBackOff` / `ErrImagePull` / `InvalidImageName` | Image / tag / registry guidance; on a `kind` context it adds the `kind load docker-image` recipe. |
| `CreateContainerConfigError` / `CreateContainerError` / `RunContainerError` | Dumps Kubernetes' `container.state.waiting.message` verbatim (usually pinpoints the missing Secret key or invalid env-var name) + the `kubectl describe pod` command. |
| `CrashLoopBackOff` / `OOMKilled` / `Error` | Same recovery surface — `kubectl describe pod` plus the last 20 pod events. |

When any terminal state is hit, the script also dumps the **last 20 pod events** automatically. You don't have to copy-paste `kubectl describe`.

> Tip: the chart sets `runAsNonRoot: true` with `runAsUser: 1000` / `runAsGroup: 1000` to match the `app` user baked into the Docker image. If you override `image.repository` to point at a custom build of the server, make sure it still runs under UID `1000` — otherwise the pod will hit `CreateContainerConfigError` on startup with the `runAsNonRoot and image has non-numeric user` message.

### Manual fallback (no script)

If you cannot run Python in your environment, every operation has a one-liner equivalent — they're listed in the Operations section below.

## Configuration Reference

Every key below is also documented inline in [`charts/zscaler-mcp-server/values.yaml`](./charts/zscaler-mcp-server/values.yaml).

### Image

| Key | Default | Description |
|---|---|---|
| `image.repository` | `zscaler/zscaler-mcp-server` | Docker Hub repo. Override to point at a private mirror / Marketplace ECR. |
| `image.tag` | `latest` | Each release publishes immutable + rolling semver tags (`X.Y.Z`, `X.Y`). Pin a version in production — or pin via `image.digest`, which wins over `image.tag`. Releases ≤ v0.12.6 have no versioned tags unless backfilled. |
| `image.digest` | `""` | Pin by digest (`sha256:...`). When set, wins over `image.tag`. Recommended for production. |
| `image.pullPolicy` | `IfNotPresent` | |
| `imagePullSecrets` | `[]` | Image pull Secrets for private registries. |

### Replicas, resources, scheduling

| Key | Default | Description |
|---|---|---|
| `replicaCount` | `1` | Ignored when `autoscaling.enabled=true`. |
| `resources.requests.cpu/memory` | `100m / 256Mi` | |
| `resources.limits.cpu/memory` | `1000m / 1Gi` | |
| `nodeSelector` / `tolerations` / `affinity` / `topologySpreadConstraints` | `{}` / `[]` | Standard pod-scheduling knobs. |
| `priorityClassName` | `""` | |
| `terminationGracePeriodSeconds` | `30` | Allows graceful drain of in-flight MCP sessions. |

### Pod / container security

| Key | Default | Description |
|---|---|---|
| `podSecurityContext.runAsNonRoot` | `true` | Enforces non-root at the K8s admission layer. |
| `podSecurityContext.runAsUser` | `1000` | Numeric UID of the `app` user baked into the Docker image. Must be numeric — Kubernetes cannot introspect a Dockerfile `USER <name>` directive, so unsetting this trips `runAsNonRoot` admission. |
| `podSecurityContext.runAsGroup` | `1000` | Matching numeric GID. |
| `podSecurityContext.fsGroup` | `1000` | Owns any volume mounted into the pod; lets the `app` user write to mounted volumes. |
| `podSecurityContext.seccompProfile.type` | `RuntimeDefault` | Satisfies Restricted PSS. |
| `securityContext.runAsNonRoot` / `runAsUser` / `runAsGroup` | `true` / `1000` / `1000` | Repeated at the container level so a downstream chart override of `podSecurityContext` cannot accidentally land us back at root. |
| `securityContext.allowPrivilegeEscalation` | `false` | |
| `securityContext.readOnlyRootFilesystem` | `false` | Flip to `true` only after adding an `emptyDir` mount for `/tmp` via `extraVolumes`. |
| `securityContext.capabilities.drop` | `["ALL"]` | |

### Service / Ingress / HTTPRoute

`ingress.enabled` and `httproute.enabled` are **mutually exclusive** — picking both fails the install with a clear error.

| Key | Default | Description |
|---|---|---|
| `service.type` | `ClusterIP` | `ClusterIP` / `NodePort` / `LoadBalancer`. |
| `service.port` | `80` | Service port. |
| `service.targetPort` | `8000` | Container port — matches the MCP server default. |
| `ingress.enabled` | `false` | Generate a `networking.k8s.io/v1` Ingress. |
| `ingress.className` | `""` | e.g. `nginx`, `traefik`, `alb`. |
| `ingress.hosts[]` / `ingress.tls[]` | see values.yaml | Standard Ingress fields. |
| `httproute.enabled` | `false` | Generate a Gateway API v1 HTTPRoute instead. |
| `httproute.parentRefs[]` / `httproute.hostnames[]` | see values.yaml | |
| `certificate.enabled` | `false` | Generate a cert-manager `Certificate`. |
| `certificate.issuerRef.{name,kind}` | `letsencrypt-production` / `ClusterIssuer` | |

### Availability

| Key | Default | Description |
|---|---|---|
| `podDisruptionBudget.enabled` | `false` | Recommended for any `replicaCount >= 2`. |
| `podDisruptionBudget.minAvailable` | `1` | Mutually exclusive with `maxUnavailable`. |
| `autoscaling.enabled` | `false` | Generates an HPA targeting CPU. |
| `autoscaling.minReplicas` / `maxReplicas` | `1 / 5` | |
| `autoscaling.targetCPUUtilizationPercentage` | `80` | |

### MCP runtime (`mcp.*`)

These map 1:1 to the `ZSCALER_MCP_*` env vars the server already reads. See the top-level [`CLAUDE.md`](../../CLAUDE.md) and `zscaler_mcp/server.py` for the full env-var contract.

| Key | Default | Maps to |
|---|---|---|
| `mcp.transport` | `streamable-http` | `--transport` |
| `mcp.host` | `0.0.0.0` | `--host` |
| `mcp.port` | `8000` | `--port` |
| `mcp.auth.enabled` | `true` | `ZSCALER_MCP_AUTH_ENABLED` |
| `mcp.auth.mode` | `zscaler` | `ZSCALER_MCP_AUTH_MODE` (`jwt` / `api-key` / `zscaler` / `none`) |
| `mcp.auth.jwt.{jwksUri,issuer,audience}` | `""` | `ZSCALER_MCP_AUTH_JWKS_URI`, `_JWT_ISSUER`, `_JWT_AUDIENCE` |
| `mcp.toolsets.enabled` | `""` | `ZSCALER_MCP_TOOLSETS`. Special values: `default`, `all`. |
| `mcp.toolsets.disabled` | `""` | `ZSCALER_MCP_DISABLED_TOOLSETS` |
| `mcp.services.enabled` | `""` | `ZSCALER_MCP_SERVICES` |
| `mcp.services.disabled` | `""` | `ZSCALER_MCP_DISABLED_SERVICES` |
| `mcp.tools.disabled` | `""` | `ZSCALER_MCP_DISABLED_TOOLS` (fnmatch patterns) |
| `mcp.writeTools.enabled` | `false` | `ZSCALER_MCP_WRITE_ENABLED` |
| `mcp.writeTools.allowlist` | `""` | `ZSCALER_MCP_WRITE_TOOLS` (fnmatch patterns) |
| `mcp.disableEntitlementFilter` | `false` | `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER` |
| `mcp.disableOutputSanitization` | `false` | `ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION` |
| `mcp.logToolCalls` | `false` | `ZSCALER_MCP_LOG_TOOL_CALLS` |
| `mcp.security.disableHostValidation` | `false` | `ZSCALER_MCP_DISABLE_HOST_VALIDATION` |
| `mcp.security.allowedHosts` | `""` | `ZSCALER_MCP_ALLOWED_HOSTS` |
| `mcp.security.allowedSourceIPs` | `""` | `ZSCALER_MCP_ALLOWED_SOURCE_IPS` |
| `mcp.tls.allowHttp` | `true` | `ZSCALER_MCP_ALLOW_HTTP`. Required when TLS terminates at the Ingress / Gateway. |
| `mcp.tls.certSecret.name` | `""` | TLS termination *inside* the container (rare — leave empty). |

### Credentials (`secret.*`)

| Key | Default | Description |
|---|---|---|
| `secret.create` | `true` | When `true`, the chart renders a `Secret` from `secret.values.*`. When `false`, references `secret.existingName`. |
| `secret.existingName` | `""` | Required when `secret.create=false`. The Secret must contain the keys named in `secret.envKeys.*`. |
| `secret.envKeys.clientId` | `ZSCALER_CLIENT_ID` | Key name *inside* the Secret. Override only if your pre-existing Secret uses different key names. |
| `secret.envKeys.clientSecret` | `ZSCALER_CLIENT_SECRET` | |
| `secret.envKeys.vanityDomain` | `ZSCALER_VANITY_DOMAIN` | |
| `secret.envKeys.customerId` | `ZSCALER_CUSTOMER_ID` | |
| `secret.envKeys.privateKey` | `ZSCALER_PRIVATE_KEY` | For JWT-based OneAPI auth (alternative to `clientSecret`). |
| `secret.envKeys.apiKey` | `ZSCALER_MCP_AUTH_API_KEY` | Used when `mcp.auth.mode=api-key`. |
| `secret.values.*` | all `""` | Only consulted when `secret.create=true`. Empty values are skipped. |

### Power-user passthrough

| Key | Default | Description |
|---|---|---|
| `extraEnv[]` | `[]` | Verbatim env vars; wins over `mcp.*` when names collide. |
| `extraEnvFrom[]` | `[]` | Additional `envFrom` references (extra Secrets / ConfigMaps). |
| `extraVolumes[]` / `extraVolumeMounts[]` | `[]` | |
| `extraInitContainers[]` / `extraContainers[]` | `[]` | |
| `lifecycle` | `{}` | Pod lifecycle hooks (e.g. `preStop`). |

### Tests

| Key | Default | Description |
|---|---|---|
| `tests.enabled` | `true` | Generates a `helm test` pod that probes `/health`. |
| `tests.image.{repository,tag}` | `curlimages/curl:8.10.1` | |

## MCP Client Configuration

Once the chart is installed, point your MCP client at the Service / Ingress hostname. The endpoint is `/mcp`.

### Recommended — `helm_mcp_operations.py configure`

If you installed the chart via Quick Start path 1 (`helm_mcp_operations.py deploy`), the script already wrote the right entry into Cursor + Claude Desktop. To rebuild those configs at any time — after rotating credentials, restoring a config file, switching machines — run:

```bash
python integrations/helm-chart/helm_mcp_operations.py configure
```

It reads `.helm-deploy-state.json` to find the release / namespace / Secret name / MCP URL, pulls the OneAPI credentials out of the cluster Secret, computes the `Authorization: Basic` header, (re)starts a background `kubectl port-forward` if needed, and writes the entry into:

- `~/.cursor/mcp.json` (Cursor's HTTP-native shape)
- `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS (or the OS-appropriate path on Linux / Windows) using the `mcp-remote` bridge

`configure` is also useful when you installed the chart manually (Quick Start path 2 / 3) — just run `deploy` first and pick the same release / namespace / `.env` values, then let `deploy` populate the state file. Subsequent `configure` calls then work without re-running install.

### Manually — derive the auth header from the cluster Secret

If you'd rather assemble the header yourself (CI, scripts, another OS):

```bash
kubectl --namespace zscaler-mcp get secret zscaler-mcp-creds \
    -o jsonpath='{.data.ZSCALER_CLIENT_ID}:{.data.ZSCALER_CLIENT_SECRET}' \
  | base64 -d | tr -d '\n' | base64
# → prints the base64 token; prefix with "Basic " to form the header.
```

That's the exact command the `helm install` NOTES section prints for you. It works whether the Secret was chart-managed (`secret.create=true`) or pre-existing (`secret.create=false`) — the chart uses the same key names (`ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`) in both modes.

### Claude Desktop / Cursor (manual JSON)

If you don't want to run the configurator, paste this into the relevant config file under `mcpServers.zscaler`:

```jsonc
// Cursor (~/.cursor/mcp.json) — HTTP-native shape
{
  "url": "http://localhost:8000/mcp",
  "headers": {
    "Authorization": "Basic <base64 of CLIENT_ID:CLIENT_SECRET>"
  }
}

// Claude Desktop — via mcp-remote bridge
{
  "command": "npx",
  "args": [
    "-y", "mcp-remote",
    "http://localhost:8000/mcp",
    "--header",
    "Authorization: Basic <base64 of CLIENT_ID:CLIENT_SECRET>"
  ]
}
```

### VS Code (GitHub Copilot)

```jsonc
{
  "github.copilot.chat.mcp.servers": {
    "zscaler-mcp": {
      "type": "http",
      "url": "https://zscaler-mcp.example.com/mcp"
    }
  }
}
```

### Port-forwarded local dev (no Ingress)

```bash
kubectl -n zscaler-mcp port-forward svc/zscaler-mcp-zscaler-mcp-server 8000:80
# Then point your MCP client at http://localhost:8000/mcp
```

## Operations

### Smoke test the install

```bash
helm test zscaler-mcp -n zscaler-mcp
```

The bundled test pod (`templates/tests/test-connection.yaml`) curls `/health` from inside the cluster and asserts HTTP 200. Useful in CI to gate a chart upgrade.

### Inspect the rendered manifests without installing

```bash
helm template zscaler-mcp \
  ./integrations/helm-chart/charts/zscaler-mcp-server \
  --set secret.create=false \
  --set secret.existingName=zscaler-mcp-creds \
  --set ingress.enabled=true \
  --set ingress.className=nginx
```

### Upgrade in place

```bash
helm upgrade zscaler-mcp \
  ./integrations/helm-chart/charts/zscaler-mcp-server \
  -n zscaler-mcp \
  -f my-values.yaml
```

The Deployment carries a `checksum/credentials` pod annotation, so any change to the chart-managed Secret triggers a rolling restart automatically. When you point at a pre-existing Secret (`secret.create: false`), the annotation is intentionally **not** rendered — Secret rotation is the operator's responsibility (External Secrets Operator handles this natively).

### Uninstall

```bash
helm uninstall zscaler-mcp -n zscaler-mcp
# The chart-managed Secret is removed with the release.
# Pre-existing Secrets (secret.create: false) are NOT touched.
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `helm install` fails with *"ingress.enabled and httproute.enabled are mutually exclusive"* | Both set to `true` | Pick one and set the other to `false`. |
| `helm install` fails with *"secret.create is false but secret.existingName is empty"* | Operator mode without naming a target | Set `secret.existingName` or flip `secret.create: true`. |
| `helm install` fails with *"secret.create is true but ... are all empty"* | Forgot to pass credentials | Use `--set secret.values.clientId=...` or `--values creds.yaml`. |
| Pod CrashLoopBackOff with `ZSCALER_VANITY_DOMAIN missing` | Vanity domain not in the Secret | Confirm `secret.envKeys.vanityDomain` matches the actual key name in your pre-existing Secret. |
| `/health` returns 200 but `/mcp` returns 401 | Auth header missing or wrong format | Re-check `mcp.auth.mode` against the header you're sending. `zscaler` expects `Authorization: Basic`; `jwt` / `api-key` expect `Authorization: Bearer`. |
| MCP client sees zero tools | Entitlement filter trimmed everything | Your OneAPI client isn't entitled to the loaded toolsets. Either request entitlements, or set `mcp.disableEntitlementFilter: true` (emergency override only). |
| Stale Secret values after rotation | Pre-existing Secret was updated but pods didn't restart | Either bounce the Deployment (`kubectl rollout restart`) or wire ESO's reloader / Stakater reloader to do it automatically. |

For deeper debugging:

```bash
kubectl -n zscaler-mcp logs deploy/zscaler-mcp-zscaler-mcp-server --tail=200 -f
kubectl -n zscaler-mcp describe pod -l app.kubernetes.io/name=zscaler-mcp-server
kubectl -n zscaler-mcp get events --sort-by='.lastTimestamp' | tail -30
```

### Recovering from a failed install (`ImagePullBackOff`, bad creds, etc.)

If `helm install` succeeded but the Pod can't start (`kubectl get pods` shows `ImagePullBackOff`, `CrashLoopBackOff`, `Error`):

```bash
# 1) Inspect what went wrong
kubectl -n zscaler-mcp describe pod -l app.kubernetes.io/name=zscaler-mcp-server | sed -n '/Events:/,$p'
kubectl -n zscaler-mcp logs deploy/zscaler-mcp-zscaler-mcp-server --tail=200

# 2a) If it's an image issue (your cluster can't reach Docker Hub),
#     upgrade the existing release pointing at a private mirror:
helm upgrade zscaler-mcp ./integrations/helm-chart/charts/zscaler-mcp-server \
  -n zscaler-mcp \
  --reuse-values \
  --set image.repository=registry.example.com/zscaler-mcp-server \
  --set image.tag=latest

# 2b) If it's a credentials issue, fix the Secret and bounce the Deployment:
kubectl -n zscaler-mcp create secret generic zscaler-mcp-creds \
  --from-env-file=/path/to/.env \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n zscaler-mcp rollout restart deployment/zscaler-mcp-zscaler-mcp-server

# 2c) When in doubt, blow it away and start over:
helm uninstall zscaler-mcp -n zscaler-mcp
kubectl delete namespace zscaler-mcp
# then re-run Quick Start path 1.
```

`helm uninstall` always wins over `helm upgrade` if you've gotten into a deeply broken state — the chart leaves no dangling resources, and recreating from scratch is fast.

## Versioning

The chart version (`Chart.yaml::version`) is **independent** of the MCP server version (`Chart.yaml::appVersion`). They follow [Semantic Versioning](https://semver.org/) independently:

- **Chart version** moves when chart templates or `values.yaml` schema change.
- **App version** moves when a new MCP server release is published, and the chart's default `image.tag` is updated to match.

The chart is **alpha** until it gets cut as `0.1.0`. Until then, breaking changes to `values.yaml` may happen between minor chart releases and will be called out in the changelog.

## Roadmap (post-v1)

- **GitHub Pages Helm repo** so `helm repo add zscaler-mcp https://zscaler.github.io/zscaler-mcp-server/` works without cloning. A GitHub Actions workflow will run `helm package` + `helm repo index` on every release tag and publish to the `gh-pages` branch.
- **Chart-testing CI** (`ct lint`, `kubeconform`, `kind`-based install smoke).
- **values.schema.json** for early validation of `--set` typos.
- **OIDCProxy** mode (OAuth 2.1 + DCR) once it's reachable via env vars rather than the programmatic `auth=` parameter.
- **Built-in ExternalSecret template** (gated by `externalSecrets.enabled: true`) so customers with ESO installed don't need to maintain a separate manifest. Deliberately deferred from v1 to avoid coupling the chart to a specific CRD version.

## Contributing

Chart changes live under `integrations/helm-chart/charts/zscaler-mcp-server/`. Before opening a PR:

```bash
cd integrations/helm-chart/charts/zscaler-mcp-server
helm lint .
helm template t . \
  --set secret.values.clientId=test \
  --set secret.values.clientSecret=test \
  --set secret.values.vanityDomain=test.zsapi.net \
  --set secret.values.customerId=12345 \
  > /tmp/rendered.yaml
# Inspect /tmp/rendered.yaml for sanity.
```

If your change touches the runtime contract (env vars, port, args), bump `appVersion` (or the underlying release) **first** and verify the chart renders against it. If your change is chart-only (templates, values.yaml), bump `version` (the chart version) only.
