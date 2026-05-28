# Zscaler MCP Server on AWS ECS-Fargate

Deploy the [Zscaler MCP Server](https://github.com/zscaler/zscaler-mcp-server) as a publicly accessible HTTPS service on **AWS ECS-Fargate**, fronted by an Application Load Balancer with an ACM TLS certificate. The deployment is driven by **CloudFormation** (nested stacks) and orchestrated by an **interactive Python script** that mirrors the design of the existing AWS Bedrock AgentCore deployment in the sibling `bedrock-agentcore/` folder.

> **When to use this deployment**
> Any MCP client that speaks plain HTTPS — Claude Desktop, Cursor, Gemini CLI, VS Code, Windsurf, GitHub Copilot CLI, or any future client — can connect directly to the URL this deployment produces. Use this when you want a remote MCP server reachable from outside AWS, without the SigV4 restriction that Bedrock AgentCore Runtime imposes.

---

## Topology

```text
                            ┌─────────────────────────────────────────┐
   User / MCP client ───►   │ Application Load Balancer (TLS @ 443)   │
                            │   • ACM cert via Route53 (managed) OR   │
                            │     existing cert ARN OR HTTP-only      │
                            └────────────────┬────────────────────────┘
                                             │
                                             ▼
                            ┌─────────────────────────────────────────┐
                            │ ECS-Fargate Service (1+ tasks)          │
                            │   • zscaler/zscaler-mcp-server:latest   │
                            │   • Secrets injected from               │
                            │     AWS Secrets Manager                 │
                            └────────────────┬────────────────────────┘
                                             │ HTTPS
                                             ▼
                                       Zscaler OneAPI
```

Everything is provisioned by the stack:

- **VPC** (optional): 2 public + 2 private subnets across 2 AZs, IGW, single NAT gateway. Or attach to an existing VPC.
- **ALB**: HTTPS listener with TLS termination (when TLS enabled), HTTP→HTTPS redirect, target group with health checks.
- **ACM certificate** (optional): DNS-validated against a Route53 hosted zone — fully automatic.
- **Route53 alias** (optional): A-record pointing your FQDN at the ALB.
- **ECS cluster + service**: Fargate launch type, 1 task by default, configurable CPU/memory.
- **Task definition**: pulls the Docker Hub image, mounts secrets from Secrets Manager via the `secrets` block, sets all required env vars.
- **IAM roles**: task execution role (pull image, read secret, write logs) + task role (no AWS API access by default).
- **CloudWatch log group**: every container log line, with configurable retention.
- **Secrets Manager secret** (optional): script creates one from your `.env`, or you point at an existing ARN.

---

## File layout

```text
ecs-fargate/
├── README.md                            # this file
├── env.properties                       # config template (copy to .env)
├── requirements.txt                     # Python deps (boto3)
├── ecs_fargate_mcp_operations.py        # interactive orchestrator
└── cloudformation/
    ├── zscaler-mcp-root.yaml            # root nested stack
    ├── network.yaml                     # VPC + subnets + NAT (CreateNew mode)
    ├── iam.yaml                         # task execution + task roles
    ├── secrets.yaml                     # Secrets Manager (CreateNew mode)
    └── ecs.yaml                         # cluster, task def, service, ALB, listeners,
                                         #   ACM cert, Route53 alias, security groups
```

---

## Prerequisites

- **AWS credentials** with permission to create VPC, ECS, IAM, ELBv2, ACM (if AcmManaged), Route53 (if AcmManaged), Secrets Manager, CloudWatch Logs, and S3 resources.
- **Python 3.9+** with `boto3` (installed by `requirements.txt`). The `logs` subcommand uses boto3 directly — no AWS CLI required.
- (Optional) An **MCP client** installed on your laptop — the script auto-detects and configures Claude Desktop, Claude Code (CLI), Cursor, Gemini CLI, VS Code, Windsurf, and GitHub Copilot CLI.

---

## Quick start

```bash
cd integrations/aws/ecs-fargate
pip install -r requirements.txt
cp env.properties .env        # then edit .env
python ecs_fargate_mcp_operations.py deploy
```

The script walks you through:

1. **Region + stack name + resource prefix**
2. **Credentials** — reuse an existing Secrets Manager secret OR create a new one from your `.env`
3. **VPC** — create a new one OR pick existing VPC + subnets (interactive picker)
4. **TLS** — Route53-validated ACM cert OR existing cert ARN OR plaintext HTTP (demo)
5. **MCP auth mode** — `zscaler` (default, HTTP Basic with OneAPI creds), `jwt`, `api-key`, `oidcproxy`, or `none`
6. **Review** of every choice before launching the stack
7. **Deploy** — uploads CFN templates, runs `create-stack`, waits with live status
8. **Configure MCP clients** — picks from any clients detected on your machine

Total runtime is typically **8–15 minutes**, dominated by ALB + ACM provisioning. If you pick AcmManaged TLS, ACM DNS validation adds 2–5 minutes.

---

## Commands

| Command | What it does |
|---------|--------------|
| `deploy [--fresh] [--non-interactive] [--skip-client-config] [--env-file PATH]` | Build asset bucket, upload nested templates, launch the root stack, write client configs. **Re-deploys are auto-detected**: when a state file from a prior deploy is found, all saved values (region, stack name, prefix, network mode, credential ARN, TLS mode, auth mode) are reused so the operator just hits Enter past every prompt and CFN runs an in-place update with whatever changed in `.env` (new image tag, write-tool toggle, new feature flags, etc.). Pass `--fresh` to ignore the state file (e.g. when the prior stack was destroyed via the AWS console). |
| `status` | Show current stack status, MCP URL, ALB DNS, ECS service health (desired vs running tasks). |
| `logs [-f] [--since N]` | Stream the ECS task's CloudWatch log group. `-f` keeps polling; `--since` controls how many minutes of history to dump on first read (default 30). Uses boto3 directly — works with AWS CLI v1, v2, or no AWS CLI installed. |
| `destroy [-y] [--stack-name X] [--region Y]` | `cloudformation delete-stack` and wait for completion; deletes the state file. Resilient to missing/partial state: falls back to `zscaler-mcp-fargate` / `us-east-1` if no state exists; accepts `--stack-name` / `--region` overrides. |
| `configure [--env-file PATH]` | Re-write MCP client configs on this machine (no AWS calls). Useful after re-installing a client. |

Flags:

- `--env-file PATH` — load a specific env file (defaults to `.env`/`env.properties` in the script directory).
- `--non-interactive` — never prompt; rely entirely on env vars. Required for CI.
- `--fresh` (deploy only) — ignore any existing state file and treat the run as a first-time deploy. See the "Re-deploying" section below.
- `--skip-client-config` (deploy only) — don't touch any local MCP client configs (useful on CI / shared machines).
- `--yes` / `-y` (destroy only) — skip the destroy confirmation prompt.
- `--stack-name X` / `--region Y` (destroy only) — override the stack name / region when no state file is present (e.g. cleaning up after a partial deploy on a different machine).
- `-f` / `--follow` (logs only) — keep polling for new events.
- `--since MINUTES` (logs only) — how many minutes of history to dump on first read. Default `30`.

---

## Re-deploying / pushing updates to an existing stack

Re-running `python ecs_fargate_mcp_operations.py deploy` against an already-deployed environment **is the intended way to push updates**. The script detects the state file from your prior deploy and:

1. Prints `Found existing deployment (stack=..., region=...). Re-using saved values — CFN will run an in-place update.`
2. Pins the **locked** dimensions to their saved values: region, stack name, prefix, network mode. (CFN cannot change these between deploys without a destroy — overriding them in `.env` after the first deploy would either fail or trigger a destructive VPC swap.)
3. Forces `CredentialSource=UseExisting` pointing at the saved Secrets Manager ARN. The secret stays in place; the operator is not re-prompted for sensitive credentials. To rotate the secret's contents, update it directly in AWS Secrets Manager (out of band) and then force a task restart: `aws ecs update-service --cluster zscaler-mcp-cluster --service zscaler-mcp-service --force-new-deployment`.
4. Uses **soft defaults** (overridable via `.env`) for TLS mode, auth mode, image URI, and feature flags. These are valid things to change between deploys:
   - Update `ZSCALER_MCP_IMAGE_URI=...:0.6.0` in `.env` to roll out a new image version.
   - Flip `ZSCALER_MCP_AUTH_MODE=jwt` to enable MCP-client auth.
   - Toggle `ZSCALER_MCP_WRITE_ENABLED=true` and `ZSCALER_MCP_WRITE_TOOLS=zia_*` to enable write tools.
   - Adjust `ZSCALER_MCP_TOOLSETS=zia_url_filtering,zpa_app_segments` to narrow the loaded toolset list.
5. Runs `update-stack` on CloudFormation; CFN computes the diff and only updates resources that changed (typically just the task definition + ECS service for env-var changes).

If the prior stack was destroyed out-of-band (e.g. via the AWS console) and the state file is stale, pass `--fresh` to start over.

```bash
# Typical update workflow
$EDITOR .env                                # bump ZSCALER_MCP_IMAGE_URI
python ecs_fargate_mcp_operations.py deploy # detects state file → in-place update
```

---

## Credentials — three paths

The deploy script asks how you want to deliver the OneAPI credentials to the task:

| Path | When to use | Setup |
|------|-------------|-------|
| **Existing Secrets Manager secret** | Production. Secret lifecycle is managed outside the deploy (rotation, KMS key, replication). | Pre-create the secret as a JSON object with keys `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_VANITY_DOMAIN`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_CLOUD`. Set `ZSCALER_SECRET_NAME=zscaler/mcp/credentials` in `.env`. |
| **Script creates a new secret** | Dev / test / quick PoC. Values appear in the CloudFormation parameters during deploy. | Populate `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_VANITY_DOMAIN`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_CLOUD` in `.env`. Leave `ZSCALER_SECRET_NAME` unset. |
| **Interactive prompts** | First-time exploration. Same as above, but the script asks for each value. | Leave `.env` empty (or skip the file entirely). |

Either way, the **task definition only sees env vars** — never the secret. The container reads `ZSCALER_CLIENT_ID` etc. from its environment exactly as it would in any other deployment. The `secrets:` block in the task definition syncs each JSON key out of Secrets Manager and binds it as an env var at container startup. Rotating the secret requires a task restart (`aws ecs update-service --force-new-deployment ...`).

---

## VPC — existing vs new

| Choice | What gets provisioned | When to use |
|--------|----------------------|-------------|
| **CreateNew** | New `/16` VPC (`10.42.0.0/16` by default), 2 public subnets + 2 private subnets across 2 AZs, IGW, single NAT gateway, route tables. | Quickest path. Acceptable for prod when this is the only workload, but a single NAT in one AZ is a SPOF for the NAT path — bump to per-AZ NAT manually if HA matters. |
| **UseExisting** | None — you point at an existing VPC + subnet IDs. The deploy interactively picks them from `aws ec2 describe-vpcs` / `describe-subnets`. | Required when the workload must share networking with existing resources (RDS, internal APIs, private hosted zones, peering). |

When choosing **UseExisting**, the private subnets must already have a route to a NAT gateway (or transit gateway / VPC endpoints) — Fargate tasks need outbound HTTPS to reach Docker Hub for image pulls and Zscaler OneAPI at runtime. The deploy will succeed without internet but the tasks will crash-loop with `image pull failed`.

---

## TLS — three paths

| Choice | What gets provisioned | When to use |
|--------|----------------------|-------------|
| **AcmManaged** | ACM cert + DNS validation CNAME (automatic) + Route53 A-alias pointing your FQDN at the ALB. End-to-end HTTPS at `https://your-fqdn/mcp`. | You own a Route53 hosted zone and want a one-shot deploy. |
| **AcmExisting** | The 443 listener attached to the cert ARN you supply. No DNS record is created — you point your CNAME at the ALB DNS name yourself. | DNS lives outside Route53, or you've already issued a wildcard cert. |
| **None** | ALB listener on port 80, plaintext HTTP. URL is `http://<alb-dns>/mcp`. | Demos and quick PoCs only. The MCP server's `Authorization: Basic` header would be sent in clear text — never use this with `zscaler` auth mode for real credentials. |

In the AcmManaged path the cert + DNS validation + alias record all live inside the same CloudFormation stack, so a `destroy` cleans everything up.

---

## MCP-client authentication

The MCP server has its own auth layer (independent from AWS IAM). Pick one:

| Mode | Client sends | Server validates against | Setup |
|------|--------------|--------------------------|-------|
| `zscaler` (default) | `Authorization: Basic <base64(client_id:client_secret)>` | Zscaler's `/oauth2/v1/token` endpoint (cached for token lifetime) | Zero — uses the OneAPI creds you already have. |
| `jwt` | `Authorization: Bearer <jwt>` | JWKS at `ZSCALER_MCP_AUTH_JWKS_URI` + issuer + audience match | Configure JWKS URI / issuer / audience in `.env`. |
| `api-key` | `X-Api-Key: <key>` or `Authorization: Bearer <key>` | String comparison against `ZSCALER_MCP_AUTH_API_KEY` | Set the key in `.env` or let the script generate one. |
| `oidcproxy` | Full OAuth 2.1 flow with Dynamic Client Registration | An IdP you control (Auth0, Cognito, Entra ID, ...) | Configure `OIDCPROXY_*` env vars. |
| `none` | nothing | nothing | Only safe for cluster-internal use behind a network boundary. |

The `Authorization: Basic` header generated by the deploy script for `zscaler` mode is the simplest production path: same credentials in two places (the Secrets Manager secret consumed by the container, and the local MCP client config), no extra IdP setup.

---

## MCP client auto-configuration

After a successful deploy the script detects which of these MCP clients are installed on your machine and offers to wire each one up to the new URL with the right auth header:

| Client | Config file written |
|--------|---------------------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| Claude Code (CLI) | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| VS Code (MCP) | `~/Library/Application Support/Code/User/mcp.json` (macOS) |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| GitHub Copilot CLI | `~/Library/Application Support/github-copilot/mcp.json` (macOS) |

The same set as the local-Docker `scripts/setup-mcp-server.py` orchestrator in the main `zscaler-mcp-server` repo. Two patterns are written depending on the client's transport support:

- **Clients that speak HTTP/SSE natively** (Cursor, Gemini CLI, VS Code, GitHub Copilot CLI) get a `{ "url": "...", "headers": { ... } }` entry.
- **Clients that need an MCP-remote shim** (Claude Desktop, Claude Code, Windsurf) get an `npx -y mcp-remote <url> --header "..."` entry.

Re-run `configure` whenever you reinstall a client on a fresh machine — it loads the URL from the state file and re-writes configs without touching AWS.

---

## State file

`.aws-deploy-state.json` lives in this directory after a successful deploy. It tracks:

- Stack name, region, account
- MCP URL, ALB DNS, log group, secret name
- Auth mode, server name registered into MCP clients
- VPC ID, network mode (CreateNew vs UseExisting)
- Configured-client paths (used by `destroy` to optionally clean them up)

This file is **not** secret on its own (it stores resource identifiers, not credentials), but it is per-developer — the `.gitignore` excludes it.

---

## Recovering from a failed deploy

CloudFormation's `OnFailure: DELETE` rolls back automatically on failure, but the asset bucket and any pre-existing Secrets Manager secret (CreateNew path within Secrets Manager's 7-day soft-delete window) survive. Symptoms and remedies:

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Stack already exists in ROLLBACK_COMPLETE` | Previous failed deploy left a stub stack. | `python ecs_fargate_mcp_operations.py destroy -y` then redeploy. |
| `Secret already scheduled for deletion` | Earlier CreateNew destroy is still inside Secrets Manager's 7-day window. | `aws secretsmanager restore-secret --secret-id <name>` then redeploy, OR pick a different `AWS_RESOURCE_NAME_PREFIX`. |
| `Image pull failed` in task logs | Tasks have no NAT route (UseExisting VPC), or Docker Hub rate limit hit. | Confirm private subnets route `0.0.0.0/0` to a NAT gateway. For rate limits, pin to a private ECR mirror via `ZSCALER_MCP_IMAGE_URI`. |
| `exec /usr/local/bin/python: exec format error` (exit code 255) | The image at `ZSCALER_MCP_IMAGE_URI` is single-arch and the arch doesn't match Fargate (default `LINUX/X86_64`). Classic outcome of `docker build` on an M-series Mac without `--platform`. | Either unset `ZSCALER_MCP_IMAGE_URI` (the public Docker Hub default is multi-arch), or rebuild: `docker buildx build --platform linux/amd64,linux/arm64 -t <your-image> --push .` The deploy script now runs an ECR pre-flight that catches this before submitting CFN. |
| `Health checks failing` | Service can't bind to port 8000, or `/mcp` returns 5xx. | `python ecs_fargate_mcp_operations.py logs -f` and look at the container output. |
| ACM cert stuck in `PENDING_VALIDATION` | Route53 zone ID is wrong, or zone is not authoritative for the FQDN. | `aws acm describe-certificate ...` and confirm the validation CNAME is the same one published in the zone. |

---

## Cost ballpark (us-east-1)

| Component | Approx monthly |
|-----------|---------------:|
| ECS-Fargate (1 task, 0.5 vCPU + 1 GiB) | ~$15 |
| Application Load Balancer | ~$22 + LCU |
| NAT gateway (when CreateNew network) | ~$33 + per-GB |
| ACM certificate | $0 |
| Route53 hosted zone | $0.50 (zone) + per-query |
| Secrets Manager secret | $0.40 per secret |
| CloudWatch Logs | $0.50 per GiB ingested + storage |
| **Total (idle, no traffic)** | **~$70–80 / month** |

NAT is the biggest line item; bring-your-own-VPC + an existing NAT gateway reduces it to ~$40/month.

---

## Tear-down

```bash
python ecs_fargate_mcp_operations.py destroy
```

Deletes the root stack and (transitively, via nested-stack delete order):

- ECS service + task definition
- ALB + target group + listeners
- ACM cert (AcmManaged)
- Route53 A-record (AcmManaged)
- Security groups
- IAM roles
- CloudWatch log group
- Secrets Manager secret (CreateNew only; soft-delete with 7-day recovery window)
- VPC + subnets + NAT + IGW (CreateNew only)

Things `destroy` does **not** remove:

- The S3 asset bucket (reused across deploys, contains the nested templates).
- Existing Secrets Manager secrets (UseExisting path).
- Existing VPCs (UseExisting path).
- Local MCP client config entries — re-run `configure` or edit manually.

To also nuke the asset bucket: `aws s3 rb s3://<prefix>-cfn-<acct>-<rgn> --force`.
