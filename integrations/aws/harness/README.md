# Zscaler MCP Server — AWS Bedrock AgentCore **Harness** Integration

> **Status: Preview.** AgentCore Harness is a managed agent layer announced
> at AWS re:Invent 2025 — currently in **preview** with limited regional
> coverage. This integration tracks the preview API surface; expect
> breaking changes before GA.

This folder hosts the deployment of the Zscaler MCP Server as an AgentCore
**Harness** tool. For the existing **AgentCore Runtime** deployment
(Direct Runtime + experimental Gateway), see
[`../bedrock-agentcore/`](../bedrock-agentcore/).

## Pick a topology

The script supports two end-to-end deployment shapes. Pass `--topology` (or
set `TOPOLOGY` in `.env`); omit both and the script prompts interactively.

| Topology | Tool type | MCP server runs on | IdP | When to pick |
|---|---|---|---|---|
| `ecs` (default) | `remote_mcp` | ECS Express Mode service (Fargate + auto-ALB) | n/a (Basic auth from Token Vault) | Simplest path; fewest moving parts; no Cognito to manage. PR #47 behaviour. |
| `gateway` (PR #48) | `agentcore_gateway` | AgentCore Runtime (managed) | Amazon Cognito | No ALB / ECS / Fargate. Same Gateway can later front other MCP clients (Cursor/Claude/Strands) with a real OIDC login. |

```text
ecs topology (PR #47)                 gateway topology (PR #48)
─────────────────────                 ─────────────────────────
User ──SigV4──► Harness              User ──SigV4──► Harness
                  │                                    │
                  │ remote_mcp                         │ agentcore_gateway
                  │ (Token Vault Basic)                │ (Token Vault OAuth)
                  ▼                                    ▼
            ECS Express                          AgentCore Gateway
              (ALB+HTTPS)                       (CUSTOM_JWT Cognito)
                  │                                    │
                  ▼                                    │ OAuth2 outbound
            MCP container                              ▼
                                                AgentCore Runtime
                                                   (jwt Cognito)
                                                       │
                                                       ▼
                                                MCP container
```

---

## What is AgentCore Harness?

**Harness is a managed agent.** You declare `model`, `systemPrompt`, `tools`,
`memory`, and `limits` once via `bedrock-agentcore-control:CreateHarness`;
AWS runs the agent loop. Under the hood it is Strands Agents on AgentCore
Runtime — both still exist; Harness is just the higher-level surface AWS
now markets as the go-to-production path.

| Property | Detail |
|---|---|
| **Service** | Amazon Bedrock AgentCore — `bedrock-agentcore-control` (control plane) + `bedrock-agentcore` (data plane) |
| **API** | `CreateHarness`, `GetHarness`, `UpdateHarness`, `DeleteHarness`, `ListHarnesses`, `InvokeHarness` |
| **boto3** | ≥ 1.43.0 (earlier versions don't expose the API) |
| **Tools** | `remote_mcp`, `agentcore_gateway`, `agentcore_browser`, `agentcore_code_interpreter`, `inline_function` |
| **Auth** | Static `Authorization` header (plain or resolved from AgentCore Identity Token Vault) |
| **Memory** | Optional (AgentCore Memory). Opt-in per harness. |
| **Observability** | Auto-emitted to CloudWatch under `/aws/bedrock-agentcore/harness/<id>` |

The Zscaler MCP Server fits exclusively as a **`remote_mcp`** tool — a
URL Harness will call over HTTPS with whatever headers we configure.

---

## Architecture

```text
                 ┌──────────────────────────────────────────┐
                 │  User / Bedrock console / boto3 client   │
                 └────────────────┬─────────────────────────┘
                                  │ InvokeHarness  (data plane)
                                  ▼
                 ┌──────────────────────────────────────────┐
                 │     AgentCore Harness (managed)          │
                 │  model: claude-sonnet-4-6                │
                 │  systemPrompt: "Zscaler admin assistant" │
                 │  tools:                                  │
                 │    - type: remote_mcp                    │
                 │      name: zscaler                       │
                 │      url:  https://…ecs….on.aws/mcp      │
                 │      headers:                            │
                 │        Authorization: ${arn:…vault:…}    │
                 └────────────────┬─────────────────────────┘
                                  │ HTTPS, Basic header sourced from Token Vault
                                  ▼
                 ┌──────────────────────────────────────────┐
                 │  Zscaler MCP Server                      │
                 │  (deployed by THIS script to               │
                 │   Amazon ECS Express Mode — Fargate +    │
                 │   managed ALB + auto-scaling + auto-TLS) │
                 │  Image: zscaler/zscaler-mcp-server       │
                 │         (same image as AgentCore Runtime;│
                 │         override via ZSCALER_MCP_IMAGE_URI│
                 │         for dev builds)                  │
                 │  ZSCALER_MCP_AUTH_MODE=zscaler           │
                 └──────────────────────────────────────────┘
                                  │
                                  ▼
                          Zscaler OneAPI
```

### What this script creates (end-to-end)

The `deploy` command stands up the entire path in a single run:

1. **ECS task execution role** — `zscaler-mcp-ecs-task-execution-role`
   (configurable). Trusts `ecs-tasks.amazonaws.com`. Attached AWS-managed
   `AmazonECSTaskExecutionRolePolicy` for same-account ECR + CloudWatch
   Logs; layered inline policy scopes cross-account ECR pull to whichever
   registry account is in the image URI (defaults to the AWS Marketplace
   ECR account `709825985650`).
2. **ECS infrastructure role** — `zscaler-mcp-ecs-infrastructure-role`
   (configurable). Trusts `ecs.amazonaws.com`. Attached AWS-managed
   `AmazonECSInfrastructureRoleforExpressGatewayServices` — used by ECS
   only during create/update/delete to provision the ALB, target groups,
   security groups, and auto-scaling policies on your behalf.
3. **ECS cluster** — `zscaler-mcp` (configurable). Created if missing;
   preserved on destroy if it pre-existed (so we don't disturb shared
   workloads).
4. **CloudWatch log group** — `/ecs/zscaler-mcp` (configurable). Container
   stdout/stderr is streamed here with the `mcp` log-stream prefix.
5. **ECS Express service** — `zscaler-mcp-server` (configurable). A single
   `CreateExpressGatewayService` call provisions the entire stack — ALB,
   target group with `/mcp/` health check, security groups, auto-scaling
   target — and returns a stable public HTTPS endpoint of the form
   `xxxxx.ecs.<region>.on.aws`. The container runs on `streamable-http`
   at port 8000 with `ZSCALER_MCP_AUTH_MODE=zscaler` so it validates the
   inbound `Authorization: Basic …` header against Zscaler's
   `/oauth2/v1/token` endpoint.
6. **AgentCore Identity Token Vault credential provider** —
   `zscaler-mcp-creds` (configurable). Stores
   `Basic base64(client_id:client_secret)` so the Harness can substitute
   it into the outbound `Authorization` header at invocation time.
7. **AWS IAM Harness execution role** — `zscaler-mcp-harness-execution-role`
   (configurable). Trusts `bedrock-agentcore.amazonaws.com`. Inline
   policy mirrors the AWS-published
   [harness execution role policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness-security.html#harness-execution-role-policy)
   — **all of these are required**, the harness will silently fail
   `InvokeHarness` with `Failed to start MCP client: ... TaskGroup`
   if any are missing:
   - `bedrock:InvokeModel*`, `bedrock:Converse*` — call the reasoning model
   - `ecr-public:GetAuthorizationToken`, `sts:GetServiceBearerToken` —
     the under-the-hood AgentCore Runtime pulls its container image from
     ECR Public on every session
   - `xray:Put*`, `cloudwatch:PutMetricData` (scoped to namespace
     `bedrock-agentcore`) — AgentCore Observability
   - `logs:*` scoped to `/aws/bedrock-agentcore/runtimes/*` — the
     auto-managed runtime writes its own application logs
   - `bedrock-agentcore:GetWorkloadAccessToken*` scoped to
     `workload-identity-directory/default/workload-identity/harness_<name>-*`
   - `bedrock-agentcore:GetResourceApiKey`,
     `bedrock-agentcore:GetResourceOauth2Token` — Token Vault resolution
   - `secretsmanager:GetSecretValue` (scoped to
     `bedrock-agentcore-identity*`) plus a scoped `kms:Decrypt` —
     Token Vault backing secrets
8. **AgentCore Harness** — `zscaler-mcp-harness` (configurable). Wired
   to a model + system prompt + the `remote_mcp` tool block pointing at
   the ECS Express URL with the Token Vault credential provider as the
   `Authorization` substitution target.

State persisted to `.aws-harness-state.json` (gitignored).

> **Why ECS Express Mode and not App Runner?** AWS stopped onboarding
> new customers to App Runner on **Apr 30, 2026** and pointed everyone
> at ECS Express Mode as the replacement. Express Mode keeps the same
> single-API-call UX (one `CreateExpressGatewayService` provisions ALB
> + target groups + security groups + auto-scaling) and adds proper
> Fargate scaling. The image, env vars, and Harness wiring are
> identical regardless of host.

> **Want to host the MCP server elsewhere?** Set `MCP_URL=...` in `.env`
> (or pass `--mcp-url`). The ECS Express steps are skipped and Harness is
> wired to your existing endpoint. The endpoint must be HTTPS, non-SigV4,
> and accept the same `Authorization: Basic …` header — i.e. it must be
> running the Zscaler MCP Server with `ZSCALER_MCP_AUTH_MODE=zscaler`.

---

## Critical constraint — `remote_mcp` headers are static

Harness's `remote_mcp` tool can **only send static `Authorization` headers**.
It has no SigV4 signer. That means:

- **A SigV4-protected AgentCore Runtime URL will not work** as a
  `remote_mcp` target. Pointing Harness at
  `https://bedrock-agentcore.<region>.amazonaws.com/runtimes/...`
  produces HTTP 403 on every invocation.
- **Recommended:** let this script deploy the MCP server to ECS Express
  Mode (default path — auto-managed ALB + HTTPS). Or stand it up
  yourself behind any other non-SigV4 endpoint (Lambda + API Gateway
  without IAM auth, EC2 + systemd + HTTPS, Cloud Run, ACA, on-prem +
  ngrok) and pass the URL via `MCP_URL=…`. The server's existing
  `ZSCALER_MCP_AUTH_MODE=zscaler` mode handles the Basic header
  Harness delivers regardless of host.
- **Alternative (now shipped):** AgentCore Gateway between Harness and a
  SigV4 Runtime URL — the Gateway does the OAuth → SigV4 protocol switch
  for you. Set `--topology gateway` (or `TOPOLOGY=gateway`) and the script
  provisions AgentCore Runtime + Gateway + Amazon Cognito as the IdP in a
  single command. See [Gateway topology](#gateway-topology-pr-48) below.

The `deploy` script will **warn** if you point it at an obvious SigV4-only
URL and let you proceed anyway — useful for testing the Harness creation
flow before the MCP endpoint is finalised.

---

## Gateway topology (PR #48)

The Gateway topology eliminates the ECS Express / ALB / Fargate footprint
entirely. The MCP server runs on **AgentCore Runtime** (the same compute
the sibling `../bedrock-agentcore/` script uses) and Harness reaches it
through an **AgentCore Gateway**. Amazon Cognito is the inbound IdP —
fully AWS-native, no Auth0 / Okta / Entra ID required.

### How auth works (all three boundaries)

The whole flow uses Cognito-issued JWTs (client_credentials grant), brokered
by a **single OAuth2 credential provider** in AgentCore Identity Token
Vault. One Cognito App Client serves all three legs.

```text
[1] user / console           ──SigV4──────────────► Harness
[2] Harness                  ──HarnessGatewayOutboundAuth.oauth──►
                                  fetches Cognito client_credentials token
                                  from the OAuth2 credential provider
                              ──Bearer <Cognito JWT>──► Gateway
[3] Gateway                   ──customJWTAuthorizer (Cognito JWKS)──┘
                                  validates aud / client_id / signature
                              ──target outbound: OAuth2 (same provider)──►
                                  refetches Cognito token, presents to
                              ──Bearer <Cognito JWT>──► Runtime
[4] Runtime                   ──customJwtAuthorizer (Cognito JWKS)──┘
                                  same validation as Gateway
                              ──container env: jwt mode──► MCP server
[5] MCP server                ──Zscaler Secret Manager via TaskRole──►
                                  loads ZSCALER_* creds from Secrets Manager
                              ──Basic auth─────► Zscaler OneAPI
```

### What the script creates (gateway topology)

A single `deploy --topology gateway` run provisions:

1. **Amazon Cognito User Pool** — `zscaler-mcp-harness-up` (configurable).
   `AdminCreateUserOnly` set to true — we never mint users.
2. **Cognito Resource Server** — identifier `zscaler-mcp` (becomes the
   `aud` claim on tokens). Has one custom scope: `invoke`.
3. **Cognito App Client** — `zscaler-mcp-harness-client`, client_credentials
   grant only, with `zscaler-mcp/invoke` in `AllowedOAuthScopes`. Generates
   a client secret on create.
4. **Cognito hosted-UI domain** — auto-suffixed with the AWS account ID
   for global uniqueness. Hosts the `/oauth2/token` endpoint.
5. **AgentCore Identity OAuth2 credential provider** —
   `zscaler-mcp-cognito-oauth`. Stores the Cognito (`client_id`,
   `client_secret`, `discoveryUrl`) tuple. Backs both the Harness→Gateway
   and Gateway→Runtime auth legs.
6. **Runtime execution role** — `zscaler-mcp-harness-runtime-role`. Grants
   ECR pull, CloudWatch Logs PutLogEvents on
   `/aws/bedrock-agentcore/runtimes/*`, Secrets Manager
   `GetSecretValue` + scoped `kms:Decrypt` on the Zscaler secret.
7. **AgentCore Runtime** — `zscaler_mcp_runtime`. Configured with
   `auth: jwt` + `customJwtAuthorizer` pointing at Cognito, env vars
   include `ZSCALER_SECRET_NAME` so the container's `zscaler_mcp.config`
   module loads credentials via boto3 at boot.
8. **Gateway service role** — `zscaler-mcp-harness-gateway-role`.
   Trusts `bedrock-agentcore.amazonaws.com`. Inline policy grants
   `bedrock-agentcore:InvokeAgentRuntime` on the Runtime ARN.
9. **AgentCore Gateway** — `zscaler-mcp-gateway`. `protocolType=MCP`,
   `authorizerType=CUSTOM_JWT` against the Cognito User Pool.
10. **Gateway target** — `zscaler-mcp-runtime`. `mcpServer` target type
    pointing at the Runtime's invocation URL. Outbound credential
    provider = the OAuth2 provider from (5), `grantType=CLIENT_CREDENTIALS`.
11. **Harness execution role** — same as the ECS topology
    (`zscaler-mcp-harness-execution-role`).
12. **AgentCore Harness** — wired with an `agentcore_gateway` tool
    block whose `outboundAuth.oauth.providerArn` points back at (5).

State persisted to `.aws-harness-state.json` with a `topology: "gateway"`
marker plus all the IDs above.

### Why this topology is cleaner

| | ECS topology (PR #47) | Gateway topology (PR #48) |
|---|---|---|
| Compute | Fargate task in ECS Express service | AgentCore Runtime (managed) |
| Networking | ALB + target group + security groups + auto-scaling | None (Runtime is internal to AgentCore) |
| Health checks | ALB `/health` probe (FastMCP `HealthCheckMiddleware`) | None (Runtime polls READY status itself) |
| Inbound auth on MCP | Basic (Zscaler-mode middleware on the container) | JWT (validated by AgentCore Runtime *before* the container is hit) |
| IdP | None (Token Vault holds static Basic header) | Amazon Cognito (1 User Pool, 1 App Client, 1 Resource Server, 1 domain) |
| Reachable by non-Harness MCP clients | Yes — `https://…ecs….on.aws/mcp` is a plain URL | Yes — Gateway exposes a Cognito-fronted MCP URL too |
| Destroy blast radius | Cluster + service + task defs + ALB + roles | Runtime + Gateway + target + Cognito + roles |
| Cost when idle | ALB ~$16/mo + 1 Fargate task | Near-zero (Runtime + Gateway charged per invocation) |

### Limitations (preview API)

- **Gateway inbound auth is CUSTOM_JWT only** as of the 2023-06-05
  service spec. Cognito is the easiest IdP because the script provisions
  it for you; any OIDC-compliant IdP would also work but you'd have to
  bring your own and edit the deploy script's
  `_deploy_gateway_topology()` to use its discovery URL.
- **Domain prefix collisions:** Cognito hosted-UI domain prefixes are
  globally unique within a region. The script suffixes the prefix with
  the AWS account ID, but two separate AWS accounts in the same region
  trying to use the same prefix will see one fail. Override
  `--cognito-domain-prefix` if this hits you.
- **No interactive `--keep-runtime`** option on destroy yet. If you need
  to preserve the Runtime (e.g. it's also the backend for the
  `../bedrock-agentcore/` deploy), pass `--keep-role` to keep the
  Runtime exec role + Gateway service role, then manually run
  `aws bedrock-agentcore-control delete-gateway-target` /
  `delete-gateway` to remove just the Gateway pieces.
- **Cognito tokens cap at 1 hour** by default. Token Vault refreshes them
  automatically; you should never see token-expiry errors from Harness.

### Switching between topologies

The two topologies are **mutually exclusive** in a single state file —
the script tracks one Harness at a time. To switch:

```sh
# Tear down the current deployment (whichever topology)
python harness_mcp_operations.py destroy --yes

# Redeploy with the other topology
python harness_mcp_operations.py deploy --topology gateway
# or
python harness_mcp_operations.py deploy --topology ecs
```

If you want both topologies running side-by-side, pass different
`--harness-name` values (and clone the script directory so the state
files don't collide).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| AWS account with **AgentCore Harness preview** access | Currently limited to a subset of regions. Confirm via `aws bedrock-agentcore-control list-harnesses --region <r>`. |
| AWS CLI / boto3 credentials | The script uses the default credential chain. `aws sts get-caller-identity` should succeed. |
| Python 3.10+ | One runtime dependency (`boto3`). |
| Bedrock model access | At minimum the Claude Sonnet 4.6 inference profile (or whichever model you pick). Anthropic models additionally require a one-time **use-case form** in the Bedrock console. |
| Permission to call `ecs:CreateExpressGatewayService` and `iam:PassRole` on `ecsTaskExecutionRole` / `ecsInfrastructureRoleForExpressServices` | Granted by `AdministratorAccess`. Tighter least-privilege policies are documented in [the ECS Express Mode getting-started guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html). |
| Default VPC in the target region | ECS Express auto-selects subnets + security groups from the default VPC when `networkConfiguration` is omitted. Most accounts have one out of the box; otherwise create one with `aws ec2 create-default-vpc`. |
| AWS Marketplace subscription to Zscaler MCP Server | Free (BYOL). Required if you let the script use the default Marketplace image. Skip this if you set `ZSCALER_MCP_IMAGE_URI` to your own ECR. |
| `linux/amd64` image | The Marketplace image is multi-arch; **dev builds must include `linux/amd64`** (ECS Fargate is amd64 by default). Use `make docker-build-multiarch IMAGE=<your-ecr-uri>:<tag>` to build a manifest list, or `… PLATFORMS=linux/amd64` to push amd64 only. A plain `docker build` on Apple Silicon ships an arm64-only image and crashes Fargate with `exec format error`. |
| Zscaler OneAPI credentials | `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_VANITY_DOMAIN` from the ZIdentity console. All four are required when this script deploys the MCP server itself. |

---

## Install

```bash
cd integrations/aws/harness
uv venv .harness-venv --python 3.11
source .harness-venv/bin/activate
uv pip install -r requirements.txt
```

Both `.harness-venv/` and the deployment state file are listed in
`integrations/aws/harness/.gitignore`.

---

## Configure

Copy the template and fill in your Zscaler credentials:

```bash
cp env.properties .env
${EDITOR:-vim} .env
```

You can also pass values as CLI flags or let the script prompt you
interactively — `env.properties` is for convenience.

---

## Deploy

```bash
python harness_mcp_operations.py deploy --region us-east-1
```

The script walks the full stack in one run (≈4-5 minutes — most of it
is the ECS Express ALB + target group health-check warm-up):

| # | Step | What happens |
|---|------|--------------|
| 1 | Load configuration | Reads `.env`, merges with CLI flags. |
| 2 | Verify AWS credentials | `sts:GetCallerIdentity`. |
| 3 | Pick MCP source | ECS Express (default) or pre-existing `MCP_URL`. |
| 4 | Zscaler OneAPI credentials | Validates `CLIENT_ID` / `CLIENT_SECRET` (+ `CUSTOMER_ID` / `VANITY_DOMAIN` on the ECS Express path). |
| 5 | Container image source | Defaults to the Marketplace ECR image; override via `ZSCALER_MCP_IMAGE_URI`. |
| 6 | ECS IAM roles | Task execution role (`ecs-tasks.amazonaws.com` + `AmazonECSTaskExecutionRolePolicy` + cross-account ECR inline) and infrastructure role (`ecs.amazonaws.com` + `AmazonECSInfrastructureRoleforExpressGatewayServices`). |
| 7 | ECS cluster + log group | Cluster created if missing (tracked for symmetric destroy); CloudWatch log group created idempotently. |
| 8 | ECS Express service | `CreateExpressGatewayService`, polls until status is `ACTIVE` *and* the PUBLIC ingress endpoint is published. Returns the stable `*.ecs.<region>.on.aws` URL. |
| 9 | Stage credentials in Token Vault | `CreateApiKeyCredentialProvider` storing `Basic base64(client_id:client_secret)`. |
| 10 | Harness execution role | IAM role for the Harness itself. Sleeps ~10s for propagation. |
| 11 | Pick Bedrock reasoning model | Claude Sonnet 4.6 (default), Claude Opus 4.7, Nova Pro, or Llama 3.3 70B. Skipped if `MODEL_ID` is set. |
| 12 | `CreateHarness` | Submits the harness with model + system prompt + `remote_mcp` tool, polls until `READY`. |

Steps 5–8 are skipped when `MCP_URL` is set; the script wires Harness
to your existing endpoint instead.

On success, prints the harness ARN, the ECS Express public endpoint
(when applicable), the Bedrock console URL for the playground, and the
next commands to run (`logs` / `invoke` / `destroy`).

### What success looks like

```
── Deployment summary ─────────────────────────────────────────────────────────
  HarnessId              = zscaler-mcp-harness-AbCdEfGhIj
  HarnessArn             = arn:aws:bedrock-agentcore:us-east-1:123456789012:harness/zscaler-mcp-harness-AbCdEfGhIj
  Model                  = us.anthropic.claude-sonnet-4-5-20250929-v1:0
  MCP URL                = https://abc123.ecs.us-east-1.on.aws/mcp
  MCP Host               = ECS Express — zscaler-mcp-server (cluster: zscaler-mcp)
  Execution Role         = arn:aws:iam::123456789012:role/zscaler-mcp-harness-execution-role
  Credential Provider    = arn:aws:bedrock-agentcore:us-east-1:123456789012:token-vault/default/apikeycredentialprovider/zscaler-mcp-creds
  Console                = https://us-east-1.console.aws.amazon.com/bedrock-agentcore/home?region=us-east-1#/harnesses/zscaler-mcp-harness-AbCdEfGhIj
```

---

## Lifecycle commands

```bash
python harness_mcp_operations.py status   --region us-east-1
python harness_mcp_operations.py logs     --region us-east-1
python harness_mcp_operations.py invoke "list my zpa segment groups" --region us-east-1
python harness_mcp_operations.py destroy  --region us-east-1 [--yes] [--keep-role] [--keep-ecs]
```

| Command | Description |
|---|---|
| `deploy`  | End-to-end walk-through (above). Idempotent on re-deploy — reuses existing ECS cluster, ECS Express service, IAM roles, log group, and credential provider when they already exist by name. |
| `status`  | `GetHarness` + pretty-print of status, model, tool list, timestamps. When the ECS Express host is in state, also prints the service status, cluster, image, and public endpoint. |
| `logs`    | Tails the auto-managed AgentCore runtime log group under `/aws/bedrock-agentcore/runtimes/<runtime-id>`. The runtime ID is discovered by scanning that prefix for groups tied to your harness; the group only materialises on the first `InvokeHarness`. (For container-side / ECS logs use `aws logs tail /ecs/zscaler-mcp --follow`.) |
| `invoke`  | One-shot smoke test: opens an `InvokeHarness` event stream, prints text deltas, surfaces the stop reason and token usage. |
| `destroy` | Reverse-order tear-down: `DeleteHarness` → wait → `DeleteApiKeyCredentialProvider` → delete Harness exec role → `DeleteExpressGatewayService` → delete ECS CloudWatch log group → delete cluster (only if we created it) → delete ECS task execution + infrastructure roles → delete `.aws-harness-state.json`. The auto-managed Harness runtime log group under `/aws/bedrock-agentcore/runtimes/*` is owned by AWS and drained automatically when the harness is deleted — we do not touch it. Use `--keep-role` to preserve IAM roles and `--keep-ecs` to preserve the MCP host across redeploys. |

---

## Authentication design

The Zscaler MCP Server has five auth modes (`OIDCProxy`, `JWT`,
`API Key`, `Zscaler`, `None`). Harness's `remote_mcp` tool pairs with
them as follows:

| MCP auth mode | Harness header config | Recommended? |
|---|---|---|
| **Zscaler** | `Authorization: ${arn:…/zscaler-mcp-creds}` — Token Vault resolves to `Basic base64(client_id:client_secret)` | **Yes — this script's default.** Rotation handled by Token Vault. |
| **API Key** | `Authorization: ${arn:…/zscaler-api-key}` — plain bearer | Yes, if you'd rather use a static bearer instead of OneAPI. |
| **JWT** | `Authorization: Bearer <long-lived JWT>` plaintext, or Token-Vault resolved if rotation is needed | Less common. JWT is usually short-lived. |
| **OIDCProxy** | Use `agentcore_gateway` tool type instead, with `outboundAuth.oauth` configured on the Gateway | Topology C. The OIDC flow can't run from inside `remote_mcp`. |
| **None** | No `Authorization` header | Dev / testing only. Do not deploy without auth. |

---

## Secrets Manager — where Zscaler credentials live

By default this script does **not** put `ZSCALER_CLIENT_SECRET` (or
`ZSCALER_CLIENT_ID` / `ZSCALER_VANITY_DOMAIN` / `ZSCALER_CUSTOMER_ID` /
`ZSCALER_CLOUD`) in the ECS task definition as plaintext env vars. The
five-key credential bundle goes to AWS Secrets Manager and the container
fetches it at boot.

### Why

Plaintext env vars in an ECS task definition are visible to anyone with
`ecs:DescribeTaskDefinition` and the value is logged in CloudTrail on
every `RegisterTaskDefinition` / `CreateExpressGatewayService` /
`UpdateExpressGatewayService` call. Secrets Manager scopes the read to
a single secret ARN, audits each fetch separately, and enables
credential rotation without touching the task definition.

### How it works (zero container-code changes)

The container image already ships with `zscaler_mcp/config.py`, a
side-effect module that runs at process boot via `aws_entrypoint.py`:

1. The deploy script writes the credential JSON to
   `zscaler-mcp-harness/credentials` in Secrets Manager.
2. The ECS task definition gets only `ZSCALER_SECRET_NAME=<that-name>`
   — never the actual credential values.
3. The task execution role gets a scoped two-statement inline policy
   (`secretsmanager:GetSecretValue` on the secret ARN +
   `kms:Decrypt` filtered by `kms:ViaService=secretsmanager.<region>`).
4. At container boot, `config.py` calls `GetSecretValue` via boto3,
   parses the JSON, and `os.environ`-injects each key. The SDK then
   initialises exactly as if the keys had been passed as env vars.

Result: the same SDK code, the same env-var shape — but no Zscaler
credential ever appears in `aws ecs describe-task-definition`,
CloudTrail, or the ECS console.

### Three modes

| Mode | How to activate | Lifecycle |
|---|---|---|
| **Default — script-managed secret** | Leave `ZSCALER_SECRET_NAME` unset in `.env`. The script creates `zscaler-mcp-harness/credentials` (override via `--secret-name`) and seeds it from your `ZSCALER_*` `.env` values. | `destroy` schedules deletion with a 7-day recovery window. Use `--force-secret-delete` to skip the window. Re-deploys after a `.env` rotation update the secret in place via `PutSecretValue`. |
| **Bring-your-own secret** | Set `ZSCALER_SECRET_NAME=<arn-or-name>` in `.env`, pointing at a pre-existing secret managed by Terraform / CloudFormation / another team. Secret JSON must use the same key names (`ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, etc.). | The script verifies the secret exists, scopes the IAM policy to its ARN, but **never overwrites the value or deletes the secret** — even on `destroy`. |
| **Plaintext opt-out** (dev/debug only) | Pass `--no-secrets-manager` to `deploy`. | Restores the legacy behaviour where the 5 credential keys go straight into the ECS task definition. No Secrets Manager resource is created, no IAM policy is attached. **Production deploys should never use this.** |

### IAM additions

The existing `zscaler-mcp-ecs-task-execution-role` (idempotent on
re-deploy) gets one extra inline policy when Secrets Manager is on:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadZscalerCredentialsSecret",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": [
        "arn:aws:secretsmanager:<region>:<account>:secret:zscaler-mcp-harness/credentials-<random>",
        "arn:aws:secretsmanager:<region>:<account>:secret:zscaler-mcp-harness/credentials-<random>-*"
      ]
    },
    {
      "Sid": "DecryptZscalerCredentialsSecret",
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "secretsmanager.<region>.amazonaws.com"
        }
      }
    }
  ]
}
```

The `-*` ARN wildcard handles the random 6-char suffix Secrets Manager
appends to secret ARNs and is constrained to the same logical secret
(IAM ARN matching is exact otherwise — bare `secret:foo` does NOT
match `secret:foo-aBc123`).

---

## File layout

```text
integrations/aws/harness/
├── harness_mcp_operations.py     # interactive deployment / lifecycle script
├── env.properties                # .env template (copy to .env, fill in)
├── requirements.txt              # boto3>=1.43.0
├── .gitignore                    # local state + venv
├── README.md                     # this file
└── .aws-harness-state.json       # generated by `deploy` (gitignored)
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| **Harness playground** returns `Failed to start MCP client: ... unhandled errors in a TaskGroup (1 sub-exception)` on every invocation | Harness execution role is missing one of the AWS-mandated grants — most commonly `ecr-public:GetAuthorizationToken` + `sts:GetServiceBearerToken` (without these, the auto-managed AgentCore Runtime can't pull its own container from ECR Public and the MCP tool loader never starts). | `destroy --keep-ecs` and `deploy` again — the script now mirrors the full [AWS-published harness execution role policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness-security.html#harness-execution-role-policy). To verify by hand: `aws iam get-role-policy --role-name zscaler-mcp-harness-execution-role --policy-name HarnessInline`. |
| **Harness playground** returns `AccessDeniedException ... not authorized to perform: secretsmanager:GetSecretValue` | Harness exec role can't read the Token Vault's backing secret in Secrets Manager. | Same fix as above — `destroy --keep-ecs && deploy`. The policy includes a scoped `secretsmanager:GetSecretValue` on `bedrock-agentcore-identity*` plus a `kms:Decrypt` (scoped via `kms:ViaService`). |
| **Harness playground** returns `runtimeClientError: Failed to load tool 'zscaler' (type=remote_mcp): … not authorized to perform: bedrock-agentcore:GetResourceApiKey on resource: <arn>` — where `<arn>` rotates between five distinct shapes across retries (`workload-identity-directory/default`, `…/workload-identity/harness_<name>-…`, `token-vault/default`, `token-vault/default/apikeycredentialprovider/<provider>`, or the OAuth2 equivalent) | AgentCore Identity does **multiple** distinct IAM authz checks per `GetResourceApiKey` / `GetResourceOauth2Token` call — and every one of them must independently pass. The canonical [service-authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonbedrockagentcore.html) declares `GetResourceApiKey` requires permission on **three** distinct resource types (`apikeycredentialprovider`, `token-vault`, `workload-identity`), plus AgentCore additionally checks the `workload-identity-directory` root. The simpler [scope-credential-provider-access](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/scope-credential-provider-access.html) page is **incomplete** — it omits the `apikeycredentialprovider` sub-ARN. **Critical IAM-matching gotcha**: IAM ARN matching is exact (no prefix matching), so listing `token-vault/default` does NOT cover `token-vault/default/apikeycredentialprovider/<name>`. Both ARN forms have to be in the Resource list. | `destroy --keep-ecs && deploy`. The current `ResolveTokenVaultCredentials` statement enumerates all five resource ARNs (workload-identity-directory root, workload-identity, token-vault, apikeycredentialprovider/*, oauth2credentialprovider/*), so every authz check the runtime makes lands on a statement that allows it. |
| Add-tool dialog in Bedrock console shows the MCP URL **without** a trailing slash (e.g. `…/mcp`) but a previous deploy stored `…/mcp/` | Older script revisions ended the URL with `/mcp/`. The harness's built-in MCP client issues POSTs and won't follow the 307 redirect FastMCP emits on `/mcp` → `/mcp/`, so the tool fails to initialise with the TaskGroup error. | `destroy && deploy` to regenerate the harness with the trimmed URL the AWS console expects. |
| `botocore.exceptions.NoCredentialsError` | No AWS creds resolved. | `aws configure`, set `AWS_PROFILE`, or export `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. |
| `EndpointConnectionError: bedrock-agentcore-control.<region>.amazonaws.com` | Harness preview not available in that region. | Pick a region from the AWS preview list. As of writing, `us-east-1` is the safest bet. |
| `AccessDeniedException: User … is not authorized to perform: bedrock-agentcore-control:CreateHarness` | IAM user / role missing preview permissions. | Add `bedrock-agentcore-control:*` and `bedrock-agentcore:*` to the calling principal. |
| `ValidationException: harnessName … must satisfy regular expression pattern: [a-zA-Z][a-zA-Z0-9_]{0,39}` | Invalid characters in `--harness-name` — most commonly hyphens (`-`), which the AgentCore API rejects. | Use letters, digits, and **underscores only** (no hyphens), max 40 chars. Default is `zscaler_mcp_harness`. |
| `MalformedPolicyDocument` on IAM role creation | Account hasn't been onboarded to AgentCore yet (the service principal `bedrock-agentcore.amazonaws.com` isn't recognised). | Enable AgentCore in the Bedrock console first — usually a one-click opt-in on the AgentCore landing page. |
| Harness creates but every invocation returns 403 from the MCP URL | The MCP URL is SigV4-only (AgentCore Runtime invocation endpoint). | Re-run `deploy` without `MCP_URL` (uses ECS Express) or point `MCP_URL` at a non-SigV4 endpoint (Cloud Run, API Gateway w/o IAM, EC2+HTTPS). |
| `invoke` prints reasoning but no text from the model | `stopReason: max_iterations_exceeded` — agent loop hit the iteration cap. | Bump `maxIterations` in `harness_mcp_operations.py::create_harness` (default 25). |
| `ResourceNotFoundException` on `delete_api_key_credential_provider` | The provider was already removed. | Safe to ignore — `destroy` already prints `[INFO] Credential provider … already absent`. |
| `exec /usr/local/bin/python: exec format error` in ECS task logs | The image at `ZSCALER_MCP_IMAGE_URI` is single-arch ARM64 (what `docker build` defaults to on Apple Silicon), while ECS Fargate Express runs AMD64. The image isn't actually wrong; the build command is. | Rebuild with the repo's Makefile target. For a dev-only ECS push: `make docker-build-multiarch IMAGE=<your-ecr-uri>:<tag> PLATFORMS=linux/amd64` (single-arch, 1 ECR row). For Graviton + Mac too: drop `PLATFORMS=` and you get the default manifest list (linux/amd64 + linux/arm64, 3 ECR rows). Alternatively, unset `ZSCALER_MCP_IMAGE_URI` to fall back to the multi-arch Marketplace image. |
| ECR shows several "untagged" rows after `docker-build-multiarch` | Buildx normally produces 5 rows: 1 image-index (the `latest` tag), 2 per-platform images (the actual amd64 / arm64 binaries the index points to), and 2 "unknown/unknown" rows with 0-byte size (in-toto provenance + SBOM attestations). The two attestation rows are useful for SLSA / AWS Marketplace but pure noise for dev. | The `docker-build-multiarch` Makefile target passes `--provenance=false --sbom=false`, so dev pushes show 3 rows total: the `latest` tag plus one untagged row per architecture. Drop to 1 row by adding `PLATFORMS=linux/amd64` (single-arch, no manifest list). CI keeps attestations enabled for the official Marketplace image. |
| `ECSExpressGatewayService` stays `CREATING` for >5 minutes | Default VPC subnets are misconfigured / no Internet egress; or the container is restart-looping. | `aws logs tail /ecs/zscaler-mcp --follow` to inspect container output. `aws ecs describe-express-gateway-service --service-arn <arn>` shows `status.statusReason`. |
| `iam:PassRole` denied on `ecsTaskExecutionRole` / `ecsInfrastructureRoleForExpressServices` | Deploying principal doesn't have `iam:PassRole` for those role ARNs. | Grant `iam:PassRole` on the two role ARNs with the condition `iam:PassedToService = ecs.amazonaws.com`. The exact policy is in the [ECS Express getting-started guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html). |
| Re-deploy detects drift (`Updating ECS Express service … image: … → …`) and does a rolling deployment | The script now diffs the live service's image + `healthCheckPath` against the current `ZSCALER_MCP_IMAGE_URI` / desired health path and calls `UpdateExpressGatewayService` when they differ — zero-downtime rolling replace, no `destroy` needed. | Expected. Wait for the second "ECS Express status = ACTIVE" line, then test. If you actually want a from-scratch rebuild (different cluster, different IAM topology, fresh ALB), run `destroy` first. |
| First `POST /mcp` in CloudWatch returns `421 Misdirected Request` with `WARNING:mcp.server.transport_security:Invalid Host header: zs-<hash>.ecs.us-east-1.on.aws` | FastMCP's DNS-rebinding guard rejects every request whose `Host` header isn't in `ZSCALER_MCP_ALLOWED_HOSTS`. The ECS Express FQDN is AWS-generated and can't be known at `.env` time. | The script **merges** the discovered FQDN into the container's `ZSCALER_MCP_ALLOWED_HOSTS` on every deploy (deduplicating, preserving every other entry already in your `.env`). If you're upgrading from a build that pre-dates this fix, re-run `deploy` and an `UpdateExpressGatewayService` rolls in the FQDN. Full opt-out: `ZSCALER_MCP_DISABLE_HOST_VALIDATION=true` in `.env` — the script then touches nothing. |
| Same 421 but Host header is some other domain (CloudFront, custom DNS, API Gateway in front of ECS Express) | You're fronting the MCP server with infrastructure that rewrites or adds a Host the script doesn't know about. | Add the externally-visible hostname to your `.env`: `ZSCALER_MCP_ALLOWED_HOSTS=mcp.acme.com`. The script merges the ECS Express FQDN AND `127.0.0.1:*,localhost:*` into whatever you provide, so all three hostnames end up in the container's allowlist. |
| After `destroy`, the ECS console still lists ACTIVE task definitions like `zscaler-mcp-zscaler-mcp-server:17` / `…:18` | `delete_express_gateway_service` only tears down the service + ALB + target groups; it deliberately leaves task-definition revisions intact as immutable history. They're account-scoped (not cluster-scoped), so they don't block cluster deletion — but they accumulate across deploy cycles and pollute the console. | `destroy` now runs a two-step cleanup per family (`{cluster}-{service}`): `deregister_task_definition` on every ACTIVE revision, then `delete_task_definitions` (batched 10 at a time per AWS API limit). To clean up leftovers from older script revisions manually: `aws ecs list-task-definitions --family-prefix zscaler-mcp-zscaler-mcp-server --status ACTIVE` then `aws ecs deregister-task-definition --task-definition <arn>` and finally `aws ecs delete-task-definitions --task-definitions <arn1> <arn2> …`. |
| `destroy` finishes but `delete_cluster` raises `ClusterContainsServicesException` even though the express service is gone | ECS Express's `delete_express_gateway_service` returns the instant the service flips to `INACTIVE`, but the underlying ALB + target groups + occasional draining task instances keep tearing down asynchronously. A cluster delete that races into that tail still sees the residue and refuses. | `delete_ecs_cluster` now polls every 15s for up to 3 min, treating `ClusterContains{Services,Tasks,ContainerInstances}Exception` + `ResourceInUseException` as "wait a bit longer" instead of hard failures. If you still hit the timeout, the script prints the exact `aws ecs list-services` command to inspect and you can finish the cluster delete manually. |
| `destroy` reports `Keeping ECS cluster …` even though the script originally created it. The cluster persists across destroy cycles. | Cluster ownership used to be tracked via a per-deploy state-file boolean (`cluster_created_by_us`). After `destroy --keep-ecs` → `deploy`, the second deploy correctly *reused* the existing cluster — and recorded `cluster_created_by_us=False`. Every subsequent `destroy` then refused to delete it. Bug. | Fixed: ownership is now read from the cluster's `managed-by=zscaler-mcp-harness` tag (attached on every CreateCluster call). The tag survives any number of deploy/destroy cycles, so a cluster the script ever created stays "owned" forever. To verify: `aws ecs describe-clusters --clusters zscaler-mcp --include TAGS`. If you ran a deploy before this fix and the destroy summary still says "will be kept", just re-run `deploy` once — the new code rechecks tags and gets it right next destroy. |
| `deploy` fails immediately with `ECS cluster zscaler-mcp is currently DEPROVISIONING — another deploy or destroy is in flight` | A previous `destroy` is still tearing down the cluster (Express Mode's ALB/target-group teardown can take 1-3 min after the service is INACTIVE). Re-deploying instantly would race into a `ClusterAlreadyExistsException` from the AWS API. | Wait 1-3 minutes for the cluster status to clear, then re-run `deploy`. Or use `--ecs-cluster-name <other-name>` to create a fresh cluster alongside. Inspect with `aws ecs describe-clusters --clusters zscaler-mcp`. |
| `deploy` fails with `InvalidParameterException ... Unable to Start a service that is still Draining` | The cluster's ECS *service* (not the cluster itself) is in DRAINING state from a recent destroy. ECS Express's `delete_express_gateway_service` returns when the service flips to INACTIVE, but the underlying classic ECS service keeps draining ALB targets + tasks for another 1-3 min — and `list_services` hides DRAINING services from results, so `discover_ecs_express_service` can't detect it before attempting `CreateExpressGatewayService`. | When you re-run `deploy`, the new interactive cluster picker (Step 7) detects the cluster, surfaces the draining service in the count, and offers three escape hatches: (a) wait 1-3 min and pick option 1 to reuse, (b) pick option 2 to auto-generate a fresh `zscaler-mcp-<random>` cluster name and deploy alongside, or (c) pick option 3 to specify a custom cluster name. Option 2 is the fastest unblock when an old destroy is still in flight. |
| `deploy` prompts "How would you like to handle the existing cluster?" every time, even on a clean re-deploy | This is intentional. The script no longer silently reuses an existing default-named cluster — it presents the choice so you don't accidentally deploy into someone else's cluster. | Three ways to skip the prompt: (a) the default option (`1`) reuses the cluster — just press Enter; (b) pass `--ecs-cluster-name <any-name>` on the CLI to bypass the prompt entirely (the resolver only prompts when the name is the default and a cluster with that name already exists); (c) for non-default workflows, set `ECS_CLUSTER_NAME=<my-cluster>` in `.env`. |
| Container logs show `RuntimeError: Could not load Zscaler configuration from Secrets Manager: AccessDenied` shortly after startup | The ECS task execution role's scoped `secretsmanager:GetSecretValue` policy isn't there (rare — usually means a prior deploy was run with an older script revision and the role wasn't refreshed, or an out-of-band IAM change removed it). | Just re-run `deploy`. `ensure_ecs_task_execution_role` is idempotent and re-puts the `ReadZscalerSecrets` inline policy on every deploy. To verify by hand: `aws iam get-role-policy --role-name zscaler-mcp-ecs-task-execution-role --policy-name ReadZscalerSecrets`. |
| Container logs show `RuntimeError: ... ResourceNotFoundException` on the Secrets Manager fetch | The ECS task is still running the OLD task-definition revision that points at a secret name that no longer exists (e.g. you ran `destroy` then `deploy` again with a different `--secret-name`, but the express service caught up on the second update). | `aws ecs update-express-gateway-service --service-arn <arn>` with no other changes forces a fresh rollout against the latest task definition. Or just re-run `deploy` once — the script will detect drift and roll out a fresh revision. |
| Deploy fails with `InvalidRequestException: ... scheduled for deletion` on `create_secret` | A previous `destroy` soft-deleted the secret with the default 7-day recovery window and the same name is being reused. | The script handles this automatically (calls `restore_secret` + `put_secret_value`). If you need to skip the recovery window on future destroys, run `destroy --force-secret-delete`. To clean up manually: `aws secretsmanager delete-secret --secret-id zscaler-mcp-harness/credentials --force-delete-without-recovery`. |
| Operator wants to manage the secret out-of-band (Terraform) but the script keeps refreshing it | The script only treats the secret as "managed externally" when `ZSCALER_SECRET_NAME` is set in `.env` BEFORE the first deploy. If you let the script create the secret and now want to take it over, set `ZSCALER_SECRET_NAME=<arn>` in `.env` and re-run `deploy` — subsequent runs (and `destroy`) will leave it alone. | Decision is recorded in `.aws-harness-state.json` under `zscaler_secret_managed_externally`. Set the env var BEFORE the first deploy for the cleanest experience. |
| **Gateway topology only:** `deploy --topology gateway` aborts at Step 5 with `Ecr uri region 'us-east-1' does not match the application region '<other>'. Container images must be in the same region as the application.` | **AgentCore Runtime requires the container image in the same region as the Runtime.** Unlike ECS Fargate (which happily pulls cross-region), the AgentCore control plane validates this hard at `CreateAgentRuntime` time. The default Marketplace image lives in `us-east-1`, so deploying the Gateway topology anywhere else needs either a region change or a same-region copy of the image. | Two paths. **(A) Easiest:** redeploy in `us-east-1` — set `AWS_REGION=us-east-1` in `.env` or pass `--region us-east-1`. **(B) Stay in your current region:** replicate the image to ECR in your own account. The script now fails fast (before any IAM role is created) and prints the exact `docker pull` / `docker tag` / `docker push` commands plus the `ZSCALER_MCP_IMAGE_URI=…` line to add to `.env`. If you ran an older script revision and a Runtime exec role was created before the validation hit, clean it up with `aws iam delete-role --role-name zscaler-mcp-harness-runtime-role` (and any inline policies it carries). |

---

## Where to go next

- [`../../../local_dev/aws_harness_agent/integration-analysis.md`](../../../local_dev/aws_harness_agent/integration-analysis.md)
  — full architecture write-up, three integration topologies, deliverables, open questions.
- [`../bedrock-agentcore/README.md`](../bedrock-agentcore/README.md)
  — the AgentCore Runtime deployment path (the URL we co-deploy from
  here, or the alternative if you don't need Harness at all).
- [`../bedrock-agentcore/strands_agent_chat.py`](../bedrock-agentcore/strands_agent_chat.py)
  — local terminal client for the AgentCore Runtime path; the equivalent
  for the Harness path is the `invoke` subcommand of this script (a
  full multi-turn Harness chat client is on the roadmap).
