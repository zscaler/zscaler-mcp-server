# Zscaler MCP Server on AWS

Five interactive, CloudFormation-driven paths for running the [Zscaler MCP Server](https://github.com/zscaler/zscaler-mcp-server) on AWS. Pick the path that matches the AWS surface you already operate.

| Path | When to use | Reachable from | Topology | Status |
|------|-------------|----------------|----------|--------|
| **[bedrock-agentcore/](./bedrock-agentcore/)** | The MCP server is consumed by a Bedrock agent (Amazon Quick Suite, AgentCore Browser, custom Strands/LangGraph agent on AgentCore Runtime). | AWS-side agents only (SigV4 / AgentCore Gateway).<br>**Cannot** be used by Claude Desktop, Cursor, or any non-AWS MCP client. | Bedrock AgentCore Runtime (managed) + optional Gateway with OAuth 2.0 3LO | GA |
| **[harness/](./harness/)** | Custom Bedrock AgentCore agent built with the AWS Strands SDK. Demonstrates wiring an external IdP (Okta) end-to-end. | Same as bedrock-agentcore | Strands SDK + AgentCore | Preview |
| **[ecs-fargate/](./ecs-fargate/)** | Serverless container deployment that any MCP client can reach directly over public HTTPS. **Recommended default** for "give me a remote MCP server with no servers to manage." | Claude Desktop, Cursor, Gemini CLI, VS Code, Windsurf, GitHub Copilot CLI, and any future MCP client. | ALB + ACM + ECS-Fargate (Docker Hub image) | GA |
| **[ec2/](./ec2/)** | You want a VM running the `zscaler-mcp-server` PyPI package under systemd. No container runtime. Mirror of the Azure VM deployment. | Same as ECS-Fargate | ALB + ACM + AL2023 + systemd + pip-installed package | GA |
| **[eks/](./eks/)** | You already operate an EKS cluster or want a Kubernetes-first deployment. | Same as ECS-Fargate | NLB + EKS Deployment + IRSA + K8s Secret (synced from SM) | Preview (no TLS out of the box) |

---

## Picking between the public-HTTPS paths

When you've established that you want a public-internet MCP endpoint (anything other than bedrock-agentcore / harness), the choice between **ecs-fargate**, **ec2**, and **eks** comes down to:

| Question | ECS-Fargate | EC2 | EKS |
|----------|:-:|:-:|:-:|
| Do you want zero infrastructure to patch? | ✅ Fully managed | ❌ OS-level patching is yours | ✅ Managed control plane, ❌ node patching is yours |
| Idle monthly cost (`us-east-1`, one workload, brand-new VPC) | ~$70 | ~$70 | ~$155 (control plane alone is $73) |
| Time-to-first-deploy | 8–15 min | 8–15 min + 60–180 s instance bootstrap | 12–18 min (control plane provisioning ~10 min) |
| Existing infrastructure you can attach to | Existing VPC | Existing VPC | Existing VPC + existing EKS cluster |
| Native horizontal scaling | `desired_count` flag | Manual instance resize | `kubectl scale` / HPA |
| Easiest debugging surface | CloudWatch Logs | SSM Session Manager + `journalctl` | `kubectl logs` + `kubectl describe` |
| Strongest fit when you already use… | ECS for other services | Plain EC2 / VMs | Kubernetes / GitOps |

**Rule of thumb:** start with `ecs-fargate` unless you have a specific reason to pick one of the other two.

---

## What's identical across all five paths

These behaviors are shared so the user experience is consistent regardless of compute target:

- **CloudFormation-first.** Every path is built on nested CloudFormation stacks uploaded to a per-deployment S3 asset bucket. Raw `aws cloudformation deploy` works for IaC pipelines too.
- **Interactive Python orchestrator.** Each path has its own `*_mcp_operations.py` script with `deploy / status / logs / destroy / configure` subcommands. EC2 adds `ssh`; EKS adds `kubectl` and `rotate-secrets`.
- **Five MCP-client auth modes.** `zscaler` (HTTP Basic with OneAPI creds — recommended default), `jwt`, `api-key`, `oidcproxy`, and `none`. Same env var names across all paths.
- **Secrets Manager.** Credentials always live in AWS Secrets Manager — the script either creates one from your `.env` or attaches to an existing ARN.
- **7-client auto-config.** After a successful deploy the script offers to wire up Claude Desktop, Claude Code, Cursor, Gemini CLI, VS Code, Windsurf, and GitHub Copilot CLI with the right URL + auth header.
- **Bring-your-own VPC.** Every path supports `NetworkMode=UseExisting` so the deployment can land in an existing VPC.
- **State file.** Each path writes a per-developer `.aws-deploy-state.json` so `status` / `logs` / `destroy` / `configure` know what to act on without re-prompting.

---

## File layout

```text
integrations/aws/
├── README.md                   # this file
├── bedrock-agentcore/          # MCP server on AgentCore Runtime + optional Gateway
├── harness/                    # Strands SDK harness (Okta IdP demo)
├── ecs-fargate/                # Serverless container behind an ALB
├── ec2/                        # AL2023 + systemd + pip-installed package
└── eks/                        # K8s Deployment behind an NLB
```

Each subdirectory is self-contained:

```text
<deployment>/
├── README.md                   # path-specific docs
├── env.properties              # config template
├── requirements.txt            # Python deps (boto3 et al.)
├── <deployment>_mcp_operations.py
└── cloudformation/             # nested CFN templates
    ├── zscaler-mcp-root.yaml
    └── *.yaml
```

(EKS additionally ships `k8s-manifests/` for the Pod-side resources.)

---

## Common prerequisites

- An **AWS account** with credentials configured (`aws configure` / `AWS_PROFILE` env var).
- **Python 3.9+** and the matching `requirements.txt` for the path you chose. All `logs` subcommands use boto3 directly — no AWS CLI required for log streaming.
- **AWS CLI** (any version) only if you use the EC2 `ssh` path (SSM Session Manager) or want to run `eks update-kubeconfig` manually.
- (EKS only) **kubectl** matching your cluster's K8s version.
- (Optional) An **MCP client** installed locally — the script will auto-detect and offer to configure it.

---

## Tear-down notes

Every path provides `destroy` that runs `aws cloudformation delete-stack` (and, for EKS, `kubectl delete namespace` first). What's removed depends on which CreateNew/UseExisting paths you took during deploy — each subdirectory README has the per-path matrix. Resources that are explicitly **not** removed by `destroy`:

- The S3 asset bucket (reused across deploys).
- Existing Secrets Manager secrets (UseExisting paths).
- Existing VPCs (UseExisting paths).
- Existing EKS clusters (UseExisting cluster mode).
- Local MCP client config entries — re-run `configure` or edit manually.

---

## See also

- [`docs/deployment/`](../../docs/deployment/) — high-level deployment guides for each cloud
- [`docs/guides/`](../../docs/guides/) — tool catalog, toolsets, supported services
- [`integrations/azure/`](../azure/) — equivalent for Azure (Container Apps / VM / AKS Preview)
- [`integrations/google/gcp/`](../google/gcp/) — equivalent for Google Cloud (Cloud Run / GKE / Compute Engine VM)
