# Zscaler MCP Server — AWS Bedrock AgentCore Integration

Deploy the Zscaler MCP Server on **AWS Bedrock AgentCore Runtime**, pulling the official container image from **AWS Marketplace**. An optional **AgentCore Gateway** fronting layer is available for evaluation but is currently experimental — see [Experimental: AgentCore Gateway](#experimental-agentcore-gateway) for caveats.

This integration ships two parallel paths against the same modular CloudFormation templates:

| Path | When to use it |
|---|---|
| **Interactive Python wrapper** (`aws_mcp_operations.py`) | One-off deployments, evaluations, demos, hand-holding for first-time deployers. Mirrors the UX of `integrations/azure/azure_mcp_operations.py` and `integrations/google/gcp/gcp_mcp_operations.py`. |
| **Raw CloudFormation** (`cloudformation/zscaler-mcp-root.yaml` + nested children) | IaC teams. Fits into any existing CI/CD that runs `aws cloudformation deploy`. |

Both produce identical AWS resources — pick whichever matches how your team operates.

---

## What gets deployed

```text
                         AssetBucket (S3)
                                │
                                │  nested templates
                                ▼
         ┌─────────────── zscaler-mcp-root.yaml ───────────────┐
         │                                                      │
         │   ┌──────────┐  ┌──────────┐  ┌──────────────┐      │
         │   │   IAM    │  │ Secrets  │  │   Runtime    │      │
         │   │  Stack   │  │  Stack*  │  │    Stack     │      │
         │   └────┬─────┘  └────┬─────┘  └──────┬───────┘      │
         │        │             │               │              │
         │        │             │               │              │
         │        │   ┌─────────────────────────────────┐      │
         │        └──▶│  Gateway Stack (experimental)** │      │
         │            └─────────────────────────────────┘      │
         └──────────────────────────────────────────────────────┘

         *  Secrets stack runs only when CredentialSource=CreateNew
         ** Gateway stack runs only when EnableAgentCoreGateway=true
```

| Component | Always created? | Purpose |
|---|---|---|
| **IAM stack** | yes | AgentCore Runtime execution role + deployment-Lambda role. Grants cross-account ECR pull from the AWS Marketplace registry (`709825985650`). |
| **Secrets stack** | only when `CredentialSource=CreateNew` | Provisions a Secrets Manager secret holding Zscaler OneAPI credentials. Production deployments should reuse an existing secret instead. |
| **Runtime stack** | yes | Custom-resource Lambda calls `bedrock-agentcore:CreateAgentRuntime` against the Marketplace image. Wires in env vars for auth mode, write-tools allowlist, audit logging, etc. |
| **Gateway stack** | only when `EnableAgentCoreGateway=true` | **Experimental.** Custom-resource Lambdas call `bedrock-agentcore-control:CreateGateway` + `CreateGatewayTarget`. See [Experimental: AgentCore Gateway](#experimental-agentcore-gateway) for the current state of testing. |

---

## Prerequisites

1. **AWS Marketplace subscription** to *Zscaler MCP Server*. Subscription is free (BYOL) but is what grants your account permission to pull from `709825985650.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server`.
   - <https://aws.amazon.com/marketplace> → search "Zscaler MCP Server"
2. **AWS CLI / boto3 credentials** with permissions to create CloudFormation stacks, IAM roles, Lambda functions, Secrets Manager secrets, S3 buckets, and Bedrock AgentCore runtimes.
3. **Python 3.10+** with `boto3` installed (only required for the interactive wrapper).
4. **Zscaler OneAPI credentials** from the ZIdentity console.

> Gateway-only prerequisite: a pre-existing OAuth client registered with your IdP of choice (Auth0, Okta, Entra, Cognito, Keycloak). The wrapper does not create the OAuth client for you — only needed if you enable the experimental Gateway path.

---

## Recommended path — Direct Runtime

The Direct Runtime topology is the proven, production-tested path. AgentCore Runtime exposes a standard MCP streamable-HTTP endpoint that downstream callers invoke via `bedrock-agentcore:InvokeAgentRuntime` (boto3, the `agentcore` CLI, the AgentCore Sandbox playground, Lambda, etc.).

### Quick start (interactive wrapper)

```bash
cd integrations/aws/bedrock-agentcore
pip install boto3
cp env.properties .env       # optional but recommended
$EDITOR .env                 # fill in Zscaler creds + auth choice
python aws_mcp_operations.py deploy
```

The script will:

1. Verify your AWS credentials and region.
2. Create (or reuse) the asset S3 bucket.
3. Upload the nested templates to S3.
4. Launch the root CloudFormation stack.
5. Wait for completion and print the runtime ARN.

At the architecture prompt, pick **option 1 — Direct runtime (no Gateway)** for the recommended path.

### Other lifecycle commands

```bash
python aws_mcp_operations.py status                  # show stack + runtime state
python aws_mcp_operations.py logs --target runtime   # tail runtime-provisioner Lambda logs
python aws_mcp_operations.py destroy                 # delete everything
```

### Quick start (raw CloudFormation)

```bash
# 1) Create asset bucket (one-time)
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
BUCKET=zscaler-mcp-cfn-${ACCOUNT}-${REGION}
aws s3 mb s3://${BUCKET} --region ${REGION}

# 2) Upload nested templates
aws s3 sync integrations/aws/bedrock-agentcore/cloudformation/ s3://${BUCKET}/zscaler-mcp/ \
  --exclude '*' --include 'iam.yaml' --include 'secrets.yaml' \
  --include 'runtime.yaml' --include 'gateway.yaml' --include 'zscaler-mcp-root.yaml'

# 3) Launch the root stack — minimal example, runtime only
aws cloudformation create-stack \
  --stack-name zscaler-mcp-agentcore \
  --template-url https://${BUCKET}.s3.amazonaws.com/zscaler-mcp/zscaler-mcp-root.yaml \
  --parameters \
    ParameterKey=AssetBucket,ParameterValue=${BUCKET} \
    ParameterKey=CredentialSource,ParameterValue=UseExisting \
    ParameterKey=ExistingSecretName,ParameterValue=zscaler/mcp/credentials \
    ParameterKey=McpAuthMode,ParameterValue=zscaler \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --region ${REGION}
```

`EnableAgentCoreGateway` defaults to `false`, so the Gateway nested stack is skipped and you get a clean Runtime-only deployment.

---

## Authentication

There are **two independent auth layers** the deployment composes:

| Layer | Controls | Where it's configured |
|---|---|---|
| **MCP-client auth** (`McpAuthMode`) | Who can call the MCP server's HTTP endpoint | Runtime stack — `jwt` / `zscaler` / `api-key` / `none` |
| **Gateway inbound / outbound** | Who can call the Gateway URL, and how the Gateway authenticates to the runtime | Gateway stack — experimental, see below |

For Direct Runtime deployments only the MCP-client auth layer is relevant.

### How each auth mode reaches the container

AgentCore's `InvokeAgentRuntime` API only forwards HTTP headers that have been added to the runtime's [`requestHeaderAllowlist`](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-header-allowlist.html) (max 20 per runtime). The deployment configures the allowlist automatically per `McpAuthMode`:

| Mode | Allowlist entries set by the provisioner | `customJwtAuthorizer` configured? | Container-side env-var fallback |
|---|---|---|---|
| `none` | *(none)* | no | n/a |
| `api-key` | `X-Api-Key` | no | `ZSCALER_MCP_AUTH_API_KEY` |
| `zscaler` | `X-Zscaler-Client-ID`, `X-Zscaler-Client-Secret` | no | `ZSCALER_CLIENT_ID` / `ZSCALER_CLIENT_SECRET` (from Secrets Manager) |
| `jwt` | `Authorization` | **yes** — derived from `JwtIssuer` / `JwtAudience` | n/a |

The env-var fallback exists for a UX reason: the AWS Console AgentCore **Sandbox playground has no UI to attach custom headers** — only a JSON payload field. For `api-key` and `zscaler` modes the container therefore also accepts the credential from its own env (loaded from Secrets Manager at startup). The actual per-caller auth boundary in AgentCore is **AWS IAM** (`bedrock-agentcore:InvokeAgentRuntime` on the runtime ARN).

### Invoking the runtime with per-caller credentials

`agentcore invoke` (the CLI) and boto3 both let you attach the allowlisted headers. The boto3 pattern uses botocore event handlers (see the [AWS doc](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-header-allowlist.html) for the full reference):

```python
import json, boto3

RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/zscalermcp-XXXXXX"

client = boto3.client("bedrock-agentcore", region_name="us-east-1")
events = client.meta.events
EVENT = "before-sign.bedrock-agentcore.InvokeAgentRuntime"

# --- mode: api-key ---
def add_api_key(request, **_):
    request.headers.add_header("X-Api-Key", "sk-...your-key...")
handler = events.register_first(EVENT, add_api_key)

# --- mode: zscaler ---
def add_zscaler(request, **_):
    request.headers.add_header("X-Zscaler-Client-ID", "<client_id>")
    request.headers.add_header("X-Zscaler-Client-Secret", "<client_secret>")
# handler = events.register_first(EVENT, add_zscaler)

# --- mode: jwt — token comes from your OAuth flow, e.g. AgentCore Identity Sign-In ---
def add_bearer(request, **_):
    request.headers.add_header("Authorization", f"Bearer {jwt_token}")
# handler = events.register_first(EVENT, add_bearer)

payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode()
response = client.invoke_agent_runtime(agentRuntimeArn=RUNTIME_ARN, payload=payload)

for chunk in response.get("response", []):
    print(chunk.decode("utf-8"), end="")
```

CLI equivalent — `agentcore invoke "..." -H "X-Api-Key: sk-..."` (one `-H` flag per header).

### JWT mode specifics

JWT mode requires AgentCore Identity to be configured with a `customJwtAuthorizer` so that the `Authorization` header is allowlist-eligible at all. The deployment does this for you:

- `JwtAudience` → `customJwtAuthorizer.allowedAudience`
- `JwtIssuer` → derives `customJwtAuthorizer.discoveryUrl` as `<issuer>/.well-known/openid-configuration` unless you explicitly set `JwtDiscoveryUrl`
- `JwtAllowedClients` (optional) → comma-separated OAuth client_id allowlist on the AgentCore authorizer

The container then *also* validates the JWT independently via its own JWKS (`ZSCALER_MCP_AUTH_JWKS_URI`) — defense in depth, single source of truth at the IdP.

For the Sandbox playground in JWT mode, AgentCore Identity itself provides a Sign-In flow that mints the token — see `docs/deployment/amazon_bedrock_agentcore.md` for the end-to-end Auth0 walkthrough.

---

## Experimental: AgentCore Gateway

> **Status: experimental.** End-to-end Runtime invocation through the Gateway has been verified, but **tool discovery (`tools/list` propagation through the Gateway target)** does not fully work in current testing — downstream agent platforms see only a subset of the MCP server's tools, or in some cases none at all. The Gateway code paths are kept in this integration so you can evaluate the topology, but **production deployments should use the Direct Runtime path** until tool discovery is fully validated.
>
> What we have verified:
>
> - Gateway creation succeeds (both `create` and `attach` modes)
> - Inbound `CUSTOM_JWT` authorizer + `OAUTH` outbound credential provider wiring is correct
> - The runtime itself, called directly via `bedrock-agentcore:InvokeAgentRuntime`, returns the full tool list — so the issue is on the Gateway target / discovery side, not the MCP server
>
> If you need to evaluate the Gateway anyway, the rest of this section walks through the options.

The Gateway is an opt-in fronting layer that gives downstream agent platforms (Amazon Quick Suite, Bedrock Agents, custom MCP clients) a single OAuth-authenticated MCP URL instead of calling the runtime directly via `InvokeAgentRuntime`. Two modes are supported:

**Mode 1 — Create a brand-new Gateway (full lifecycle owned by the stack):**

```bash
    ParameterKey=EnableAgentCoreGateway,ParameterValue=true \
    ParameterKey=GatewayMode,ParameterValue=create \
    ParameterKey=GatewayInboundDiscoveryUrl,ParameterValue=https://my-tenant.us.auth0.com/.well-known/openid-configuration \
    ParameterKey=GatewayOAuthClientId,ParameterValue=<your-client-id> \
    ParameterKey=GatewayToolSchemaJson,ParameterValue="$(cat tool-schema.json | jq -c)" \
```

Outbound credential provider: AWS rejects `JWT_PASSTHROUGH` for `mcpServer` targets, so the Gateway always uses **`OAUTH` via an AgentCore Identity credential provider**. The stack does this for you in one of two ways:

- **Auto-provision (default)** — leave `GatewayOAuthProviderArn` empty and supply `GatewayOAuthClientSecret`. The deploy Lambda creates an `OAUTH` provider with `CLIENT_CREDENTIALS` grant using your inbound IdP details. Provider is torn down on stack delete.
- **Reuse existing** — set `GatewayOAuthProviderArn` to an ARN you created (e.g. via the console). The stack skips auto-provisioning and ignores `GatewayOAuthClientSecret`.

```bash
    # Reuse an existing provider
    ParameterKey=GatewayOAuthProviderArn,ParameterValue=arn:aws:bedrock-agentcore:us-east-1:111122223333:oauth2-credential-provider/... \
```

IdP-side requirements: AgentCore Identity issues only the standard `grant_type/client_id/client_secret/scope` payload to your IdP and cannot send `audience`/`resource` parameters. Most IdPs (Okta, Cognito, Entra v2, Google, Keycloak) accept this out of the box. **Auth0 users must enable tenant-level Default Audience** in the dashboard — see the [deployment guide](../../docs/deployment/amazon_bedrock_agentcore.md#idp-must-accept-a-vanilla-client_credentials-request) for the click-path.

**Mode 2 — Attach the runtime as a target on a Gateway you already operate:**

```bash
    ParameterKey=EnableAgentCoreGateway,ParameterValue=true \
    ParameterKey=GatewayMode,ParameterValue=attach \
    ParameterKey=ExistingGatewayId,ParameterValue=<gateway-id-you-already-have> \
    ParameterKey=GatewayToolSchemaJson,ParameterValue="$(cat tool-schema.json | jq -c)" \
```

`attach` mode does **not** create or modify the Gateway itself — only registers the Zscaler MCP server as one of its `mcpServer` targets. `destroy` only removes the target, never the customer-owned Gateway.

### Tool schema (improves discovery — recommended if you use the Gateway at all)

The `tool-schema.json` referenced above puts the Gateway target in **SchemaUpfront** mode, where the target's tool list is declared at registration time instead of being crawled live from the runtime (**ImplicitSync** mode). SchemaUpfront avoids the OAuth-consent dance that ImplicitSync needs and is more reliable. Generate it after a successful runtime deployment:

```bash
python aws_mcp_operations.py export-tool-schema --bearer <JWT> > tool-schema.json
```

Even with SchemaUpfront, full propagation of all 280+ MCP tools through Gateway-fronted clients is currently inconsistent — hence the experimental status.

---

## AWS Marketplace ECR — what changes vs Docker Hub

The runtime container image lives at:

```text
709825985650.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:0.10.4-bedrock
```

Account `709825985650` is the AWS Marketplace seller-side ECR registry. The Marketplace listing publishes immutable `<semver>-bedrock` tags only — there is no moving `latest` tag, so the version is explicit. Bump the tag in `env.properties` (or the CloudFormation parameter) when a newer version is published. Pulls are cross-account, which means **the AgentCore Runtime execution role needs explicit ECR permissions** scoped to that registry. The IAM nested stack handles this for you:

```yaml
- Effect: Allow
  Action:
    - ecr:GetAuthorizationToken
  Resource: '*'
- Effect: Allow
  Action:
    - ecr:BatchCheckLayerAvailability
    - ecr:GetDownloadUrlForLayer
    - ecr:BatchGetImage
  Resource: arn:aws:ecr:${AWS::Region}:709825985650:repository/zscaler/*
```

You do **not** need to copy the image into your own ECR. You also do **not** need an ECR pull-through cache. AgentCore Runtime pulls directly from the Marketplace registry, gated by your Marketplace subscription.

---

## VPC connectivity

The deploy script's **Step 7.5** prompts for a network mode. There are two concerns that look related but are independently configured — read the table before picking.

| Concern | Where the ENIs live | What it enables | Configured via |
|---|---|---|---|
| **Runtime in VPC mode** (covered by this script) | AgentCore creates ENIs in **your** subnets / SGs | The container can reach private resources in your VPC: RDS, internal APIs, Zscaler private DNS, etc. | `AGENTCORE_NETWORK_MODE=VPC` + `AGENTCORE_VPC_SUBNETS` + `AGENTCORE_VPC_SECURITY_GROUPS` |
| **PrivateLink for caller traffic** (not provisioned by this script) | A VPC Interface Endpoint in **your caller's** VPC | EC2 / Lambda / ECS in a VPC call `bedrock-agentcore:InvokeAgentRuntime` over PrivateLink instead of the public internet | `aws ec2 create-vpc-endpoint --service-name com.amazonaws.<region>.bedrock-agentcore --vpc-endpoint-type Interface` |

You don't need the PrivateLink endpoint just to use VPC mode (or vice versa). A caller inside a VPC can already reach AgentCore's public service endpoint over SigV4 without any extra plumbing — the PrivateLink endpoint is only needed when you want that **caller → AgentCore API** hop to stay on the AWS backbone.

### When to pick PUBLIC

The default. AgentCore runs on the AWS-managed network, outbound internet works out of the box, Zscaler OneAPI is directly reachable, and you pay nothing extra for networking. Use this unless the container itself needs to reach private resources you own.

### When to pick VPC

When the MCP container needs to reach **private** resources — a private RDS, an internal API behind a corporate Transit Gateway, your Zscaler tenant's private DNS, anything not on the public internet.

Hard constraints AWS enforces:

1. **Supported Availability Zones only.** The subnets you pass must live in AgentCore-supported AZ IDs (e.g. `use1-az1`, not `us-east-1a` — note these are AZ **IDs**, not names; AWS randomises the name→ID mapping per account). The full per-region table is at <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html#supported-az>. The deploy script bundles this table and rejects unsupported subnets **before** launching the stack.
2. **Private subnet + NAT gateway for outbound internet.** Placing AgentCore in a public subnet does **not** give it internet. If the container needs to call Zscaler OneAPI (or any other public endpoint), put the ENIs in private subnets with a NAT gateway route. AgentCore behaves identically to Lambda-in-VPC in this regard — IGW is for inbound, NAT GW is for outbound from a private subnet.
3. **Service-linked role.** The first VPC-mode deploy in an account creates the `AWSServiceRoleForBedrockAgentCoreNetwork` SLR. The IAM nested stack grants the narrow `iam:CreateServiceLinkedRole` perm needed for that automatically when you set `NetworkMode=VPC` (and grants nothing when you stay on PUBLIC). This mirrors the relevant slice of the AWS managed policy `BedrockAgentCoreFullAccess`.
4. **Best practice: >=2 subnets in different AZs.** Not enforced by AWS, but the deploy script warns if you only pick one. ENIs are shared across agents using the same subnet+SG, and unused ENIs may linger for up to 8 hours after the agent is deleted.

### Interactive VPC deploy

Just run `python aws_mcp_operations.py deploy`. Step 7.5 will:

1. Prompt **PUBLIC vs VPC**.
2. If VPC: list every VPC in the region with the default VPC pinned to the top.
3. List every subnet in the chosen VPC, **filtered** to AgentCore-supported AZ IDs (subnets in unsupported AZs are hidden with a count).
4. List every security group in the chosen VPC.
5. Hard-validate the selection via `ec2:DescribeSubnets` before kicking off the stack.

### Non-interactive VPC deploy

```bash
cat > .env <<EOF
# ... your Zscaler creds and the other usual settings ...
AGENTCORE_NETWORK_MODE=VPC
AGENTCORE_VPC_SUBNETS=subnet-0123abcd,subnet-0456efgh
AGENTCORE_VPC_SECURITY_GROUPS=sg-0123abcd
EOF
python aws_mcp_operations.py deploy --non-interactive
```

The validator still runs in `--non-interactive` mode — bad AZ IDs hard-fail with the list of supported AZ IDs for the region.

### Verifying outbound connectivity from inside the VPC

Once VPC mode is up, the standard `InvokeAgentRuntime` API still works the same way. If the agent can't reach a private resource, check (in order):

1. The SG you passed has an **outbound** rule for the target resource's port + IP/SG.
2. The target's SG has an **inbound** rule for your AgentCore SG.
3. Private subnet route table has `0.0.0.0/0` → NAT gateway (only if outbound internet is needed).
4. Enable VPC Flow Logs and tail them while the agent runs — every connection attempt shows up there.

### Adding a PrivateLink endpoint for caller traffic (optional, not provisioned)

If your *callers* (EC2 / Lambda / ECS in a VPC) need to invoke AgentCore over PrivateLink instead of the public internet:

```bash
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-CALLER \
    --service-name com.amazonaws.<region>.bedrock-agentcore \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-CALLER_PRIVATE_1 subnet-CALLER_PRIVATE_2 \
    --security-group-ids sg-FOR-ENDPOINT
```

This is a separate, optional step. It does **not** change anything about the runtime itself.

---

## Tearing down

```bash
python aws_mcp_operations.py destroy
```

This deletes the runtime, gateway (if enabled), provisioner Lambdas, IAM roles, and (if the stack created it) the Secrets Manager secret.

If you used `CredentialSource=UseExisting`, your secret is preserved. Same for the asset S3 bucket — it stays so subsequent re-deployments can reuse it.

---

## Environment variable reference

The integration deliberately keeps the user-facing surface small. The deploy script and the runtime provisioner Lambda set most plumbing values internally — you should rarely need to touch them. The tables below split what's intended for users versus what the system manages itself.

### User-facing — required

These are the only variables strictly required for a baseline Direct Runtime deployment with `CredentialSource=CreateNew`. With `CredentialSource=UseExisting` you don't need to set them at all — only `ZSCALER_SECRET_NAME`.

| Variable | Purpose | Source |
|---|---|---|
| `ZSCALER_CLIENT_ID` | OneAPI client ID from ZIdentity. | ZIdentity console |
| `ZSCALER_CLIENT_SECRET` | OneAPI client secret. | ZIdentity console |
| `ZSCALER_VANITY_DOMAIN` | ZIdentity vanity domain (e.g. `acme`). | ZIdentity console |
| `ZSCALER_CUSTOMER_ID` | Zscaler customer/tenant ID. | ZIdentity console |
| `ZSCALER_CLOUD` | Cloud override — `production` by default; set to `beta` for the Beta tenant. | ZIdentity console |
| `ZSCALER_SECRET_NAME` | Pre-existing Secrets Manager secret name (alternative to inline creds). Recommended for production. | Secrets Manager |

### User-facing — optional (tunables)

Sensible defaults are baked in; override only when you need to.

| Variable | Default | Purpose |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Region for all created resources. |
| `AWS_STACK_NAME` | `zscaler-mcp-agentcore` | Root CloudFormation stack name. |
| `AWS_RESOURCE_NAME_PREFIX` | `zscaler-mcp` | Prefix for all named resources (runtime, gateway, roles, etc.). |
| `AWS_ASSET_BUCKET` | auto-generated | S3 bucket for nested templates. Leave blank to auto-generate `zscaler-mcp-cfn-<account>-<region>`. |
| `ZSCALER_MCP_IMAGE_URI` | bundled Marketplace tag | Override to pin a specific image tag, mirror, or dev build. |
| `ZSCALER_MCP_WRITE_ENABLED` | `false` | Enable create/update/delete tools. Read-only by default. |
| `ZSCALER_MCP_WRITE_TOOLS` | (unset) | Wildcard allowlist when writes are on, e.g. `zpa_create_*,zia_update_*`. |
| `ZSCALER_MCP_DISABLED_TOOLS` | (unset) | Wildcard blocklist for individual tools. |
| `ZSCALER_MCP_DISABLED_SERVICES` | (unset) | Comma-separated service blocklist (e.g. `zcc,zdx`). |
| `ZSCALER_MCP_LOG_TOOL_CALLS` | `true` | Audit every tool call to CloudWatch. |
| `AGENTCORE_NETWORK_MODE` | `PUBLIC` | `PUBLIC` (default — AWS-managed network) or `VPC` (place ENIs in your subnets). See [VPC connectivity](#vpc-connectivity). |
| `AGENTCORE_VPC_SUBNETS` | (unset) | Comma-separated subnet IDs. Required when `AGENTCORE_NETWORK_MODE=VPC`. Must be in [AgentCore-supported AZ IDs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html#supported-az). |
| `AGENTCORE_VPC_SECURITY_GROUPS` | (unset) | Comma-separated security group IDs. Required when `AGENTCORE_NETWORK_MODE=VPC`. |
| `AGENTCORE_VPC_ID` | (unset) | Optional — pre-select the VPC in the interactive picker. No effect in `--non-interactive` (subnets / SGs are taken verbatim). |

### User-facing — authentication (mode-dependent)

`ZSCALER_MCP_AUTH_MODE` selects which block applies. Only set the ones for your chosen mode.

| Variable | Used by mode | Purpose |
|---|---|---|
| `ZSCALER_MCP_AUTH_MODE` | always | `jwt` / `zscaler` / `api-key` / `none`. |
| `ZSCALER_MCP_AUTH_JWKS_URI` | `jwt` | JWKS endpoint of your IdP. |
| `ZSCALER_MCP_AUTH_ISSUER` | `jwt` | Token issuer URL (matched against `iss` claim). |
| `ZSCALER_MCP_AUTH_AUDIENCE` | `jwt` | Expected `aud` claim value. |
| `ZSCALER_MCP_AUTH_JWT_DISCOVERY_URL` | `jwt` (optional) | Override `customJwtAuthorizer.discoveryUrl`. Derived from issuer if blank. |
| `ZSCALER_MCP_AUTH_JWT_ALLOWED_CLIENTS` | `jwt` (optional) | Comma-separated `client_id` allowlist on the AgentCore authorizer. |
| `ZSCALER_MCP_AUTH_API_KEY` | `api-key` | API key. Auto-generated at deploy time if blank. |

### Experimental — AgentCore Gateway (only when `ENABLE_AGENTCORE_GATEWAY=true`)

Required only when you opt into the experimental Gateway path. See the [Experimental: AgentCore Gateway](#experimental-agentcore-gateway) section for the partial-tool-discovery caveat before setting these.

| Variable | Mode | Purpose |
|---|---|---|
| `ENABLE_AGENTCORE_GATEWAY` | both | `true` to enable. Default `false`. |
| `GATEWAY_MODE` | both | `create` (stack provisions Gateway) or `attach` (use existing). |
| `EXISTING_GATEWAY_ID` | `attach` | ID of a Gateway you already operate. |
| `GATEWAY_INBOUND_DISCOVERY_URL` | `create` | IdP OIDC discovery URL for the Gateway's `customJwtAuthorizer`. |
| `GATEWAY_INBOUND_ISSUER` | `create` | Alternative to discovery URL — issuer is appended with `/.well-known/openid-configuration`. |
| `GATEWAY_OAUTH_CLIENT_ID` | `create` | Comma-separated OAuth client_id allowlist. |
| `GATEWAY_INBOUND_ALLOWED_AUDIENCE` | `create` | Expected `aud` claim. |
| `GATEWAY_INBOUND_ALLOWED_SCOPES` | `create` | Required scope(s); also published in `scopes_supported` metadata. |
| `GATEWAY_INBOUND_CLIENT_CLAIM_NAME` | `create` (rare) | IdP-specific override — `azp` for Auth0/Entra/Keycloak/Google, `cid` for Okta, `client_id` for Cognito. Auto-detected. |
| `GATEWAY_OAUTH_CLIENT_SECRET` | `create` | Secret for the auto-provisioned outbound credential provider (one of the two outbound paths below). |
| `GATEWAY_OAUTH_PROVIDER_ARN` | `create` | Reuse an existing AgentCore Identity OAuth provider (alternative to auto-provisioning). |
| `GATEWAY_OAUTH_PROVIDER_SCOPES` | `create` (rare) | Optional scope override for the outbound provider. |
| `GATEWAY_OAUTH_PROVIDER_GRANT_TYPE` | `create` (rare) | `CLIENT_CREDENTIALS` (default) / `AUTHORIZATION_CODE` / `TOKEN_EXCHANGE`. |
| `GATEWAY_OAUTH_TOKEN_ENDPOINT_QUERY` | `create` (rare) | Escape hatch for IdPs needing extra params. Auth0 ignores it — fix is tenant-level Default Audience instead. |
| `GATEWAY_TOOL_SCHEMA_FILE` | both | Path to a JSON tool schema (generated by `export-tool-schema`). Strongly recommended — puts the target in SchemaUpfront mode. |

### Internal — set by the runtime provisioner / Dockerfile (do not set manually)

These are documented for transparency only. The deploy script and the container image set them automatically; setting them yourself in `.env` either gets overwritten or breaks the deployment. They map directly to behaviour the AgentCore Runtime topology requires.

| Variable | Set to | Why it's internal |
|---|---|---|
| `FASTMCP_STATELESS_HTTP` | `true` (Dockerfile) | AgentCore Runtime replicas are ephemeral and may be replaced between requests; stateful sessions would pin to dead replicas. |
| `ZSCALER_MCP_ALLOW_HTTP` | `true` (provisioner) | AgentCore terminates TLS upstream of the container, so the inner HTTP server runs plain HTTP. |
| `ZSCALER_MCP_DISABLE_HOST_VALIDATION` | `true` (provisioner) | AgentCore is the sole ingress — it has already authenticated/authorized the request before forwarding. Inner host-allowlist adds no security and would block all traffic (AgentCore forwards an internal Host header that isn't predictable). |
| `ZSCALER_MCP_AUTH_ENABLED` | `true`/`false` (provisioner) | Derived from `McpAuthMode`. The provisioner sets it to match the chosen auth mode. |
| `ZSCALER_MCP_TRANSPORT` / `ZSCALER_MCP_HOST` / `ZSCALER_MCP_PORT` | `streamable-http` / `0.0.0.0` / `8000` (Dockerfile CMD) | Required for AgentCore Runtime to forward MCP traffic correctly. |
| `AWS_REGION` | injected by AgentCore | Used by the container's Secrets Manager loader. |

> **Defense-in-depth toggles** (not in `env.properties` and not exposed by the deploy script): `ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION`, `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER`, `ZSCALER_MCP_SKIP_CONFIRMATIONS`, `ZSCALER_MCP_CONFIRMATION_TTL`. These remove security layers and should only be set for short-lived debugging. See the root `CLAUDE.md` "Environment" section for details.

---

## Files in this directory

| File | Purpose |
|---|---|
| `aws_mcp_operations.py` | Interactive wrapper — `deploy` / `status` / `logs` / `destroy` / `export-tool-schema` |
| `env.properties` | Template for `.env` configuration (copy + customize) |
| `cloudformation/zscaler-mcp-root.yaml` | Root nested-stack template |
| `cloudformation/iam.yaml` | IAM roles (runtime exec + deployment Lambda) |
| `cloudformation/secrets.yaml` | Secrets Manager (only used when `CredentialSource=CreateNew`) |
| `cloudformation/runtime.yaml` | AgentCore Runtime + provisioner Lambda |
| `cloudformation/gateway.yaml` | AgentCore Gateway + target + provisioner Lambda (experimental) |
| `.aws-deploy-state.json` | Generated by `deploy` — remembers stack name / region for subsequent commands |
