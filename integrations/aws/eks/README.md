# Zscaler MCP Server on AWS EKS (Preview)

Deploy the [Zscaler MCP Server](https://github.com/zscaler/zscaler-mcp-server) on **Amazon EKS** as a Kubernetes Deployment fronted by a Network Load Balancer. The cluster + IAM scaffolding is provisioned with CloudFormation; the K8s manifests are rendered and applied by the orchestrator script. Same UX as the sibling [`../ecs-fargate/`](../ecs-fargate/) and [`../ec2/`](../ec2/) deployments — `deploy`, `status`, `logs`, `destroy`, `configure` — plus EKS-specific `kubectl` and `rotate-secrets` subcommands.

> **Preview status**
> This is the first cut of the EKS path. The NLB serves **plain HTTP** out of the box — TLS termination requires layering an Ingress Controller (NGINX or AWS Load Balancer Controller) + cert-manager + ACM. The cluster itself is production-quality (managed node group, IRSA, OIDC, scoped IAM), but the data-plane TLS story is left to the operator. See "Production hardening" below.

---

## Topology

```text
   User / MCP client ───►  NLB (public, port 80)
                                │
                                ▼
                        K8s Service: LoadBalancer
                                │
                                ▼
                     Deployment: zscaler-mcp-server (×N)
                     ├─ envFrom: secretRef: zscaler-mcp-creds
                     ├─ serviceAccountName: zscaler-mcp-sa
                     └─ Image: zscaler/zscaler-mcp-server:latest
                                │ HTTPS
                                ▼
                          Zscaler OneAPI
```

What the stack creates:

- **VPC** (optional, CreateNew): 2 public + 2 private subnets across 2 AZs, IGW, single NAT gateway, all tagged for the AWS Load Balancer Controller.
- **EKS cluster** (optional, CreateNew): managed control plane with public + private endpoint access, audit/api/authenticator logging enabled, IAM access mode set to `API_AND_CONFIG_MAP`.
- **OIDC provider**: registered against IAM so the cluster's ServiceAccounts can assume AWS roles (IRSA).
- **Managed node group**: 1×`t3.medium` AL2023 worker by default (scales 1–3), in the private subnets, with `AmazonSSMManagedInstanceCore` for SSM access.
- **IRSA Pod role**: trust policy scoped to a specific `system:serviceaccount:<ns>:<sa>` claim, permission policy scoped to read the dedicated Secrets Manager secret only.
- **Secrets Manager secret** (optional, CreateNew): script creates one from your `.env`, or you point at an existing ARN.

What the script applies (post-CFN, via kubectl):

- **Namespace** (default `zscaler-mcp`)
- **ServiceAccount** annotated with the IRSA role ARN
- **K8s Secret** (`zscaler-mcp-creds`) — populated from the SM secret values at deploy time
- **Deployment** — single container, `envFrom: secretRef` on the Secret, no PVCs, requests 200m/256Mi
- **Service** (type LoadBalancer, NLB-backed) — port 80 → containerPort 8000

---

## File layout

```text
eks/
├── README.md                       # this file
├── env.properties                  # config template
├── requirements.txt                # Python deps (boto3)
├── eks_mcp_operations.py           # interactive orchestrator
├── cloudformation/
│   ├── zscaler-mcp-root.yaml       # root nested stack
│   ├── network.yaml                # VPC + subnets + NAT (CreateNew + CreateCluster)
│   ├── cluster.yaml                # EKS cluster + node group + OIDC provider
│   ├── iam.yaml                    # IRSA Pod role
│   └── secrets.yaml                # Secrets Manager (CreateNew)
└── k8s-manifests/
    ├── 00-namespace.yaml
    ├── 01-service-account.yaml     # IRSA annotation
    ├── 02-secret.yaml              # populated from SM at deploy/rotate time
    ├── 03-deployment.yaml          # Pod spec
    └── 04-service.yaml             # LoadBalancer (NLB)
```

The orchestrator renders every `k8s-manifests/*.yaml` file with `${VAR}` substitution into `.rendered-manifests/` before applying. Manual edits to the rendered copies are clobbered on the next deploy.

---

## Prerequisites

- **AWS credentials** with permission to create VPC, EKS, EC2, IAM, ELBv2, Secrets Manager, CloudFormation, and S3 resources.
- **Python 3.9+** with `boto3` (`pip install -r requirements.txt`).
- **AWS CLI v2** — used for `aws eks update-kubeconfig` and as a fallback by the script.
- **kubectl** — required; the script invokes it directly. Match the cluster's K8s version (`brew install kubectl`, or follow the official docs).
- (Optional) **eksctl** — only needed when attaching to an existing cluster that doesn't yet have an IAM OIDC provider associated. The script will print the exact `eksctl utils associate-iam-oidc-provider …` command to run.

---

## Quick start

```bash
cd integrations/aws/eks
pip install -r requirements.txt
cp env.properties .env       # then edit .env
python eks_mcp_operations.py deploy
```

The script walks you through:

1. **Region + stack name + resource prefix**
2. **Cluster** — create new (interactive prompts for name / K8s version / node type) OR attach to an existing cluster (interactive picker from `eks list-clusters`)
3. **Credentials** — reuse an existing SM secret OR create one
4. **VPC** (CreateNew cluster only) — create or attach existing
5. **MCP auth** — `zscaler` (default), `jwt`, `api-key`, `oidcproxy`, or `none`
6. **Namespace + replicas**
7. **Review** of every choice before launching
8. **Deploy** — CFN stack first, then `aws eks update-kubeconfig`, render manifests, `kubectl apply`, wait for the NLB hostname
9. **Configure MCP clients** — picks from any clients detected on your machine

Total runtime is typically **12–18 minutes** for a brand-new cluster (EKS control plane provisioning is ~10 minutes), and **3–5 minutes** for the UseExisting path.

---

## Commands

| Command | What it does |
|---------|--------------|
| `deploy [--fresh] [--non-interactive] [--skip-client-config] [--env-file PATH]` | CFN stack + `kubectl apply` + wait for LoadBalancer + configure clients. **Re-deploys are auto-detected**: when a state file from a prior deploy is found, all saved values (region, stack name, prefix, cluster mode + name, K8s namespace, network mode, credential ARN, TLS mode, auth mode) are reused so CFN runs an in-place update + `kubectl apply` rolls out the new manifest. Pass `--fresh` to ignore the state file (e.g. when the prior stack was destroyed via the AWS console). |
| `status` | Stack status, Pods, Deployment, Service. |
| `logs [-f] [--tail N]` | `kubectl logs deployment/zscaler-mcp-server` with the cluster's context pre-set. `-f` follows; `--tail N` limits to last N lines. |
| `kubectl -- <args>` | Run any kubectl command with the cluster's context pre-set. Example: `... kubectl -- get pods -n zscaler-mcp`. |
| `rotate-secrets` | Re-fetch creds from Secrets Manager, update the K8s Secret, roll the Deployment. Use after rotating credentials in AWS Secrets Manager. |
| `destroy [-y] [--stack-name X] [--region Y]` | Delete K8s namespace first (drains LB), then `cloudformation delete-stack`. Resilient to missing/partial state. |
| `configure [--env-file PATH]` | Re-write MCP client configs on this machine (no AWS calls). |

Flags:

- `--env-file PATH` — load a specific env file.
- `--non-interactive` — never prompt; rely entirely on env vars. Required for CI.
- `--fresh` (deploy only) — ignore any existing state file and treat the run as a first-time deploy. See "Re-deploying" below.
- `--skip-client-config` (deploy only) — don't touch any local MCP client configs.
- `-y` / `--yes` (destroy only) — skip the confirmation prompt.
- `--stack-name X` / `--region Y` (destroy only) — override the stack name / region when no state file is present.
- `-f` / `--follow` (logs only) — equivalent to `kubectl logs -f`.
- `--tail N` (logs only) — only show the last N log lines.

---

## Re-deploying / pushing updates to an existing stack

Re-running `python eks_mcp_operations.py deploy` against an already-deployed environment **is the intended way to push updates**. The script detects the state file from your prior deploy and:

1. Prints `Found existing deployment (stack=..., cluster=..., region=...). Re-using saved values — CFN runs an in-place update + kubectl apply rolls out the new manifest.`
2. Pins the locked dimensions to their saved values: region, stack name, prefix, cluster mode + name, K8s namespace, network mode (CFN cannot change these without a destroy).
3. Forces `CredentialSource=UseExisting` pointing at the saved Secrets Manager ARN. The K8s Secret is re-rendered from the SM contents on every deploy, so rotating the SM secret + re-running `deploy` (or running `rotate-secrets`) propagates new credentials to the Pod.
4. Allows soft overrides via `.env` for TLS mode, auth mode, image URI, and feature flags:
   - `ZSCALER_MCP_IMAGE_URI=...:0.6.0` to roll out a new image version (kubectl rolls the Deployment).
   - `ZSCALER_MCP_AUTH_MODE=jwt` to enable MCP-client auth.
   - `ZSCALER_MCP_WRITE_ENABLED=true` + `ZSCALER_MCP_WRITE_TOOLS=zia_*` for write tools.
5. Runs `update-stack` on CFN (typically a no-op when only the K8s manifest changed), then re-renders + applies the K8s manifest. The Deployment updates trigger a rolling pod restart.

If the prior stack was destroyed out-of-band, pass `--fresh` to start over.

```bash
# Typical update workflow
$EDITOR .env                          # bump ZSCALER_MCP_IMAGE_URI
python eks_mcp_operations.py deploy   # detects state file → in-place update
```

> **Pod CrashLoopBackoff on deploy?** The script now auto-runs `kubectl logs deployment/zscaler-mcp-server -n <ns> --tail=80` inline when the LoadBalancer never gets a hostname (most common cause: bad image arch or missing env var). The stack trace appears in the deploy script's stdout instead of requiring a manual `kubectl logs ...` invocation.

---

## Cluster lifecycle — new vs existing

| Choice | What the stack creates | When to use |
|--------|------------------------|-------------|
| **CreateNew** | Fresh VPC + EKS cluster + node group + OIDC provider + IRSA role + (optional) SM secret. Full lifecycle managed by this stack — `destroy` cleans everything up. | New workload. Self-contained. |
| **UseExisting** | Only the IRSA role + (optional) SM secret. K8s objects land in the existing cluster's `zscaler-mcp` namespace (configurable). The cluster, node group, VPC, etc. are left alone by `destroy`. | Shared cluster. Existing GitOps / ArgoCD / Flux setup. |

The **UseExisting** path requires the cluster to already have:

1. An IAM OIDC identity provider associated. Verify with `aws eks describe-cluster --name <name> --query cluster.identity.oidc.issuer` — if you see an issuer URL and a matching provider exists in `aws iam list-open-id-connect-providers`, you're good. If not:
   ```bash
   eksctl utils associate-iam-oidc-provider --cluster <name> --approve
   ```
2. A node group capable of running the Pod (1×`t3.medium` is plenty).
3. The K8s in-tree cloud-controller-manager (or AWS Load Balancer Controller) for `type: LoadBalancer` Services. EKS ships this by default.

---

## Credential rotation

Pods consume credentials via `envFrom: secretRef`, so a Secret update needs a rollout to take effect. The `rotate-secrets` command does both:

```bash
python eks_mcp_operations.py rotate-secrets
```

1. Reads the latest values out of Secrets Manager (using your local AWS credentials, not the IRSA role).
2. Re-applies `02-secret.yaml` with the new base64-encoded values.
3. `kubectl rollout restart deployment/zscaler-mcp-server` to cycle the Pods.
4. Waits for the rollout to complete (`rollout status`).

The IRSA role on the Pod isn't used for credential fetching in this version — credentials are baked into the K8s Secret by the orchestrator. The IRSA role is still provisioned (with `secretsmanager:GetSecretValue` scoped to the specific ARN) so you can extend the Deployment to do live AWS API calls later without re-architecting.

---

## Production hardening

The preview ships HTTP-only on the NLB. For production:

### TLS via ALB Ingress + cert-manager (recommended)

```bash
# 1. Install the AWS Load Balancer Controller via Helm.
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=<your-cluster-name> \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller

# 2. Install cert-manager (for ACM private CA issuance) or skip if you'll
#    use ACM public certs directly via the Ingress annotation.
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# 3. Replace the LoadBalancer Service with an Ingress backed by an
#    ALB + ACM cert. The ALB annotation makes the Service type=ClusterIP
#    and the Ingress points the ALB at it. See:
#    https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/
```

### Horizontal scaling

```bash
kubectl scale deployment/zscaler-mcp-server -n zscaler-mcp --replicas=3
```

The K8s in-tree cloud-controller load-balances across all healthy Pods automatically. For autoscaling, add an HPA:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: zscaler-mcp-server
  namespace: zscaler-mcp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: zscaler-mcp-server
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Cluster autoscaling

Bump the node group max via `eksctl scale nodegroup` or the Karpenter controller — the existing node group is `min:1 max:3` by default.

### Observability

For a production deployment add:

- **Container Insights**: `aws eks update-cluster-config --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'`
- **Fluent Bit**: Helm chart `aws-for-fluent-bit` ships Pod stdout/stderr to CloudWatch Logs.
- **Prometheus + Grafana**: standard EKS Blueprints / kube-prometheus-stack chart.

---

## MCP client auto-configuration

After deploy, the script offers to wire up any detected MCP client on the local machine. Same set as the other AWS deployments:

| Client | Config file written |
|--------|---------------------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code (CLI) | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| VS Code (MCP) | `~/Library/Application Support/Code/User/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| GitHub Copilot CLI | `~/Library/Application Support/github-copilot/mcp.json` |

Re-run `configure` on a fresh machine to point the existing deployment's URL at a freshly-installed client.

---

## State file

`.aws-deploy-state.json` lives in this directory after a successful deploy. It tracks:

- Stack name, region, account, asset bucket, resource prefix
- Cluster name + mode (CreateNew / UseExisting), kubectl context, namespace, service account
- MCP URL, LB hostname, Pod role ARN, secret name + ARN
- Auth mode, server name registered into MCP clients
- Configured-client paths

Not secret on its own. Per-developer — the `.gitignore` excludes it.

---

## Troubleshooting

**`No EKS clusters found in <region>`** during UseExisting — the script lists clusters via `eks list-clusters`. Your caller may not have `eks:ListClusters` permission, or you're in the wrong region.

**`No IAM OIDC provider registered for ...`** — the cluster doesn't have an OIDC provider associated. Run `eksctl utils associate-iam-oidc-provider --cluster <name> --approve`.

**`LoadBalancer didn't surface a hostname in time`** — the in-tree CCM is busy provisioning the NLB. Check the Service status: `python eks_mcp_operations.py kubectl -- describe svc zscaler-mcp-server -n zscaler-mcp`. Common causes: subnets not tagged with `kubernetes.io/role/elb=1`, or no public subnets in the cluster.

**Pod stuck in `CrashLoopBackOff`** — `python eks_mcp_operations.py logs --tail 50`. Most common is a missing required env var (the K8s Secret is incomplete).

**Pod logs show `exec /usr/local/bin/python: exec format error`** — the image at `ZSCALER_MCP_IMAGE_URI` is single-arch `arm64` (the default output of `docker build` on an M-series Mac) but the EKS managed node group is running `x86_64` nodes. Either unset `ZSCALER_MCP_IMAGE_URI` (the public Docker Hub default is multi-arch and works on any node arch) or rebuild your custom image as multi-arch: `docker buildx build --platform linux/amd64,linux/arm64 -t <your-image> --push .` The deploy script now runs an ECR pre-flight that catches this before submitting CFN.

**Pod stays in `ContainerCreating`** — secrets fetch failing. Check `kubectl describe pod ...`. The Pod uses `envFrom: secretRef` so it should NOT depend on AWS API access at startup — if the K8s Secret exists and contains all five keys, the Pod will come up.

---

## Cost ballpark (us-east-1)

| Component | Approx monthly |
|-----------|---------------:|
| EKS control plane | ~$73 (flat $0.10/hour) |
| Managed node group (1×t3.medium) | ~$30 |
| NLB (Network Load Balancer) | ~$16 + LCU |
| NAT gateway (CreateNew network) | ~$33 + per-GB |
| EBS volumes (node root) | ~$2 |
| Secrets Manager secret | $0.40 per secret |
| **Total (idle, no traffic)** | **~$155 / month** |

EKS is significantly more expensive than ECS-Fargate or EC2 at this single-Pod scale because of the $73/mo control plane charge. The break-even with ECS-Fargate is around 3–4 Pods worth of compute, or when you already have an EKS cluster to attach to (UseExisting mode — drops the $73 + $30 + $33 = ~$136/mo).

---

## Tear-down

```bash
python eks_mcp_operations.py destroy
```

What gets deleted depends on which path you took:

| Resource | CreateNew | UseExisting |
|----------|:--:|:--:|
| K8s namespace + all its objects | ✅ | ✅ |
| EKS cluster + node group | ✅ | ❌ (left alone) |
| OIDC provider | ✅ | ❌ |
| IRSA Pod role | ✅ | ✅ |
| Secrets Manager secret (CreateNew only) | ✅ | ✅ |
| VPC + subnets + NAT + IGW (CreateNew network only) | ✅ | ❌ |
| S3 asset bucket | ❌ (reused across deploys) | ❌ |

To also nuke the asset bucket: `aws s3 rb s3://<prefix>-cfn-<acct>-<rgn> --force`.
