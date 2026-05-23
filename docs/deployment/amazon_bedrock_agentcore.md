# Deploying Zscaler MCP Server to Amazon Bedrock AgentCore

This guide provides complete instructions for deploying the Zscaler MCP Server to Amazon Bedrock AgentCore with **two deployment methods** and **two credential management approaches**.

> **Topology at a glance.** The shipped, production-tested topology is **AgentCore Runtime alone**, called via `bedrock-agentcore:InvokeAgentRuntime` (boto3, the `agentcore` CLI, the Sandbox playground, etc.). An optional **AgentCore Gateway** can be placed in front of the runtime for downstream agent platforms like Amazon Quick Suite — that path is currently **experimental**: end-to-end Runtime invocation through a Gateway works, but `tools/list` propagation through the Gateway target is inconsistent in current testing. See [Gateway integration (experimental)](#gateway-integration-experimental) for the full status.

## 📋 Table of Contents

- [Deployment Methods Overview](#deployment-methods-overview)
- [Credential Management Approaches](#credential-management-approaches)
- [Prerequisites](#prerequisites)
- [Method 1: CloudFormation Deployment (Recommended)](#method-1-cloudformation-deployment-recommended)
- [Method 2: Manual AWS CLI Deployment](#method-2-manual-aws-cli-deployment)
- [Gateway integration (experimental)](#gateway-integration-experimental)
- [Testing Your Deployment](#testing-your-deployment)
- [Configuring OAuth (Auth0) for AgentCore Identity](#configuring-oauth-auth0-for-agentcore-identity)
- [Troubleshooting](#troubleshooting)
- [Environment variable reference](#environment-variable-reference)

---

## Deployment Methods Overview

Choose the deployment method that best fits your needs:

| Method | Best For | Complexity | Security | Time |
|--------|----------|------------|----------|------|
| **CloudFormation** | Production, automation | ⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Excellent | ~5 min |
| **Manual AWS CLI** | Testing, learning | ⭐ Simple | ⭐⭐⭐⭐ Good | ~10 min |

---

## Credential Management Approaches

The Zscaler MCP Server supports **two approaches** for managing Zscaler API credentials:

### Approach A: Container-Based Secrets Manager Integration (Recommended) 🔒

**How it works:**

- Credentials stored in AWS Secrets Manager (encrypted with KMS)
- Container retrieves credentials at startup using boto3
- **Zero credentials in infrastructure configuration**

**Security Benefits:**

- ✅ Credentials encrypted at rest (KMS)
- ✅ Credentials encrypted in transit (TLS)
- ✅ Credentials never visible in AgentCore config
- ✅ Credentials never in deployment scripts
- ✅ CloudTrail audit logging
- ✅ Secret rotation support

**When to use:**

- ✅ Production deployments
- ✅ Compliance requirements (SOC2, ISO27001, PCI-DSS)
- ✅ Multiple team members
- ✅ Credential rotation needed

### Approach B: Direct Environment Variables

**How it works:**

- Credentials passed directly in `--environment-variables` parameter
- No Secrets Manager required

**Security Considerations:**

- ⚠️ Credentials visible in AgentCore configuration
- ⚠️ Credentials in deployment scripts
- ⚠️ Credentials in command history

**When to use:**

- ✅ Development/testing
- ✅ Quick proof-of-concept
- ✅ Internal environments only

---

## Prerequisites

### Required for All Deployments

1. **AWS CLI** configured with appropriate credentials
2. **Zscaler API Credentials**:
   - Client ID
   - Client Secret
   - Vanity Domain
   - Customer ID
   - Cloud (optional, only for Beta tenant: `beta`)

3. **Docker Image** pushed to Amazon ECR:

   ```bash
   # Build and push the image
   docker build --platform linux/arm64 -t zscaler/zscaler-mcp-server .
   docker tag zscaler/zscaler-mcp-server:latest \
     YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest
   docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest
   ```

### Additional for Secrets Manager Approach

1. **AWS Secrets Manager** access
2. **IAM permissions** to create/read secrets

---

## Method 1: CloudFormation Deployment (Recommended)

### 🚀 One-Click Deploy

Click the button below to launch the stack in the AWS Console:

<a href="https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=zscaler-mcp-server&templateURL=https%3A%2F%2Fzscaler-mcp-cloudformation-templates.s3.us-east-1.amazonaws.com%2Fbedrock-agentcore-deployment.yaml" target="_blank">
    <img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png" alt="Launch Stack" style="border: 0;"/>
</a>

### What Gets Deployed

- ✅ **IAM Execution Role** - With ECR, CloudWatch, Secrets Manager, and Bedrock permissions
- ✅ **Secrets Manager Secret** - (Optional) Encrypted with AWS KMS
- ✅ **Lambda Custom Resource** - Automates AgentCore deployment
- ✅ **Bedrock AgentCore Runtime** - Container-based secret retrieval

### Deployment Steps

#### Step 1: Click Launch Stack Button

The button will open the AWS CloudFormation console with the template pre-loaded.

#### Step 2: Specify Stack Details

**Stack Name:** `zscaler-mcp-server` (or your preferred name)

**Parameters:**

##### Agent Runtime Configuration

- **AgentRuntimeName**: `zscalermcp` (alphanumeric and underscores only, no hyphens)
- **AgentDescription**: `Zscaler MCP Server with Secrets Manager Integration`
- **ECRImageUri**: `YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest`
  - ⚠️ **Important:** Replace `YOUR_ACCOUNT_ID` with your actual AWS account ID

##### Credential Management

**Choose one of two options:**

#### Option A: Create New Secret (First-Time Deployment)

1. **CredentialSource**: Select `CreateNew`
2. Fill in your Zscaler credentials:
   - **ZscalerClientId**: Your OAuth Client ID
   - **ZscalerClientSecret**: Your OAuth Client Secret
   - **ZscalerVanityDomain**: Your vanity domain (e.g., `example`)
   - **ZscalerCustomerId**: Your Customer ID
   - **ZscalerCloud**: Leave empty for production, or select `beta` for Beta tenant

#### Option B: Use Existing Secret (Recommended if Secret Already Exists)

1. **CredentialSource**: Select `UseExisting`
2. **ExistingSecretName**: `zscaler/mcp/credentials` (or your secret name)
3. Leave credential fields empty (they're not used)

##### Security Configuration

- **EnableWriteTools**: `false` (recommended) or `true` to enable write operations
- **WriteToolsAllowlist**: Leave empty, or specify tools (e.g., `zpa_*,zia_*`)

#### Step 3: Configure Stack Options

- **Tags** (optional): Add tags for cost tracking
- **Permissions**: CloudFormation will create IAM roles automatically
- **Stack failure options**: Use default settings

#### Step 4: Review and Create

1. Review all parameters
2. ✅ Check the box: **"I acknowledge that AWS CloudFormation might create IAM resources with custom names"**
3. Click **"Submit"**

#### Step 5: Monitor Deployment

Wait 3-5 minutes for the stack to complete. The status will change from:

- `CREATE_IN_PROGRESS` → `CREATE_COMPLETE` ✅

#### Step 6: Get Outputs

Once complete, go to the **Outputs** tab to see:

- **AgentRuntimeId**: Your runtime ID
- **AgentRuntimeArn**: Your runtime ARN
- **SecretName**: The Secrets Manager secret name
- **SecurityNote**: Confirmation that credentials are not exposed
- **VerificationCommand**: Command to check runtime status
- **LogsCommand**: Command to view container logs

### Verify Deployment

```bash
# Get runtime ID from CloudFormation outputs
RUNTIME_ID="zscalermcp-AbCdEf1234"  # Replace with your runtime ID

# Check runtime status
aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeId=='$RUNTIME_ID']"

# View container logs
aws logs tail /aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT \
  --region us-east-1 \
  --follow
```

**Look for these log entries:**

```text
INFO:zscaler_mcp.config:Successfully retrieved and parsed secret from Secrets Manager
INFO:zscaler_mcp.config:Set environment variable: ZSCALER_CLIENT_ID
INFO:zscaler_mcp.config:Zscaler credentials injected into environment variables
INFO:zscaler_mcp.server:Initializing Zscaler MCP Server
```

✅ **Success!** The container retrieved credentials from Secrets Manager.

### Verify Security

```bash
# Verify credentials are NOT in AgentCore config
aws bedrock-agentcore-control get-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id $RUNTIME_ID \
  --query 'environmentVariables'
```

**Expected output:**

```json
{
  "ZSCALER_SECRET_NAME": "zscalermcp-credentials",
  "AWS_REGION": "us-east-1",
  "ZSCALER_MCP_WRITE_ENABLED": "false",
  "ZSCALER_MCP_WRITE_TOOLS": ""
}
```

✅ **Notice:** No `ZSCALER_CLIENT_ID` or `ZSCALER_CLIENT_SECRET`!

---

## Method 2: Manual AWS CLI Deployment

For users who prefer manual deployment or need more control over the process.

### Choose Your Credential Approach

#### Approach A: With Secrets Manager (Recommended for Production)

##### Step 1: Create Secrets Manager Secret

```bash
# Create encrypted secret with KMS
aws secretsmanager create-secret \
  --name zscaler/mcp/credentials \
  --description "Zscaler API credentials for MCP Server" \
  --kms-key-id alias/aws/secretsmanager \
  --secret-string '{
    "ZSCALER_CLIENT_ID": "your-client-id",
    "ZSCALER_CLIENT_SECRET": "your-client-secret",
    "ZSCALER_VANITY_DOMAIN": "your-vanity-domain",
    "ZSCALER_CUSTOMER_ID": "your-customer-id",
    "ZSCALER_CLOUD": "",
    "ZSCALER_MCP_WRITE_ENABLED": "false",
    "ZSCALER_MCP_WRITE_TOOLS": ""
  }' \
  --region us-east-1
```

**Verify secret creation:**

```bash
aws secretsmanager describe-secret \
  --secret-id zscaler/mcp/credentials \
  --region us-east-1 \
  --query '{Name:Name,ARN:ARN,KmsKeyId:KmsKeyId}'
```

**Expected output:**

```json
{
  "Name": "zscaler/mcp/credentials",
  "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:zscaler/mcp/credentials-AbCdEf",
  "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/..."
}
```

✅ **Encryption confirmed!** The secret is encrypted with AWS KMS.

##### Step 2: Create IAM Execution Role

Create a role with Secrets Manager permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRImageAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "arn:aws:ecr:us-east-1:YOUR_ACCOUNT_ID:repository/zscaler/zscaler-mcp-server"
    },
    {
      "Sid": "ECRTokenAccess",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:zscaler/mcp/credentials-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/bedrock-agentcore/runtimes/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

**Create the role:**

```bash
# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name BedrockAgentExecutionRole \
  --assume-role-policy-document file://trust-policy.json

# Attach permissions policy
aws iam put-role-policy \
  --role-name BedrockAgentExecutionRole \
  --policy-name BedrockAgentExecutionPolicy \
  --policy-document file://execution-policy.json
```

##### Step 3: Deploy AgentCore Runtime

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --region us-east-1 \
  --agent-runtime-name zscalermcp \
  --description "Zscaler MCP Server with Secrets Manager" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest"
    }
  }' \
  --role-arn "arn:aws:iam::YOUR_ACCOUNT_ID:role/BedrockAgentExecutionRole" \
  --network-configuration '{"networkMode": "PUBLIC"}' \
  --protocol-configuration '{"serverProtocol": "MCP"}' \
  --environment-variables '{
    "ZSCALER_SECRET_NAME": "zscaler/mcp/credentials",
    "AWS_REGION": "us-east-1",
    "ZSCALER_MCP_WRITE_ENABLED": "false",
    "ZSCALER_MCP_WRITE_TOOLS": ""
  }'
```

**Key Points:**

- ✅ Only `ZSCALER_SECRET_NAME` is passed (not actual credentials)
- ✅ Container retrieves credentials at startup
- ✅ Credentials never visible in AgentCore config

##### Step 4: Verify Secrets Manager Integration

```bash
# Check container logs
RUNTIME_ID="zscalermcp-AbCdEf1234"  # Get from create-agent-runtime output

aws logs tail /aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT \
  --region us-east-1 \
  --since 5m | grep -E "(config|secret|Secret)"
```

**Expected log entries:**

```text
INFO:zscaler_mcp.config:Attempting to fetch secret: zscaler/mcp/credentials from region: us-east-1
INFO:zscaler_mcp.config:Successfully retrieved and parsed secret from Secrets Manager
INFO:zscaler_mcp.config:Set environment variable: ZSCALER_CLIENT_ID
INFO:zscaler_mcp.config:Set environment variable: ZSCALER_CLIENT_SECRET
INFO:zscaler_mcp.config:Zscaler credentials injected into environment variables
```

✅ **Success!** Container-based Secrets Manager integration is working.

---

#### Approach B: With Direct Environment Variables

##### Step 1: Create IAM Execution Role

Create a role **without** Secrets Manager permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRImageAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "arn:aws:ecr:us-east-1:YOUR_ACCOUNT_ID:repository/zscaler/zscaler-mcp-server"
    },
    {
      "Sid": "ECRTokenAccess",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/bedrock-agentcore/runtimes/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

**Notice:** No `secretsmanager:GetSecretValue` permission needed.

##### Step 2: Deploy AgentCore Runtime

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --region us-east-1 \
  --agent-runtime-name zscalermcp \
  --description "Zscaler MCP Server" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest"
    }
  }' \
  --role-arn "arn:aws:iam::YOUR_ACCOUNT_ID:role/BedrockAgentExecutionRole" \
  --network-configuration '{"networkMode": "PUBLIC"}' \
  --protocol-configuration '{"serverProtocol": "MCP"}' \
  --environment-variables '{
    "ZSCALER_CLIENT_ID": "your-client-id",
    "ZSCALER_CLIENT_SECRET": "your-client-secret",
    "ZSCALER_VANITY_DOMAIN": "your-vanity-domain",
    "ZSCALER_CUSTOMER_ID": "your-customer-id",
    "ZSCALER_CLOUD": "",
    "ZSCALER_MCP_WRITE_ENABLED": "false",
    "ZSCALER_MCP_WRITE_TOOLS": ""
  }'
```

**Key Points:**

- ⚠️ Credentials passed directly in the command
- ⚠️ Credentials visible in AgentCore configuration
- ⚠️ Credentials in shell history

##### Step 3: Verify Direct Environment Variable Approach

```bash
# Check container logs
aws logs tail /aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT \
  --region us-east-1 \
  --since 5m | grep "ZSCALER_SECRET_NAME"
```

**Expected log entry:**

```text
INFO:zscaler_mcp.config:ZSCALER_SECRET_NAME not set - using credentials from environment variables directly
```

✅ **Success!** Container is using direct environment variables.

---

## Comparison: Secrets Manager vs Direct Environment Variables

### Security Comparison

| Aspect | Secrets Manager | Direct Env Vars |
|--------|----------------|-----------------|
| **Credentials in AgentCore config** | ✅ No - only secret name | ❌ Yes - plaintext |
| **Credentials in deployment scripts** | ✅ No - only secret name | ❌ Yes - plaintext |
| **Credentials in command history** | ✅ No - only secret name | ❌ Yes - plaintext |
| **Credentials in CloudFormation** | ✅ No - only secret name | ❌ Yes - plaintext |
| **Encryption at rest** | ✅ Yes - KMS encrypted | ⚠️ AWS encrypts config |
| **Encryption in transit** | ✅ Yes - TLS | ✅ Yes - TLS |
| **Audit logging** | ✅ Yes - CloudTrail | ⚠️ Limited |
| **Secret rotation** | ✅ Yes - automated | ❌ Manual |
| **Compliance** | ✅ SOC2, ISO27001, PCI-DSS | ⚠️ May not meet requirements |

### Operational Comparison

| Aspect | Secrets Manager | Direct Env Vars |
|--------|----------------|-----------------|
| **Setup complexity** | ⭐⭐⭐ Moderate | ⭐ Simple |
| **Deployment time** | ~5 minutes | ~3 minutes |
| **IAM permissions** | More (Secrets Manager) | Fewer |
| **Cost** | ~$0.40/month | Free |
| **Credential rotation** | Update secret + restart | Redeploy runtime |
| **Production ready** | ✅ Yes | ⚠️ Not recommended |

### Decision Matrix

**Use Secrets Manager if:**

- ✅ Production environment
- ✅ Security/compliance requirements
- ✅ Multiple team members
- ✅ Credential rotation needed
- ✅ Audit logging required

**Use Direct Environment Variables if:**

- ✅ Development/testing only
- ✅ Quick proof-of-concept
- ✅ Internal use only
- ✅ No compliance requirements
- ✅ Single user environment

---

## Authentication, custom headers, and AgentCore

`InvokeAgentRuntime` (the AgentCore data-plane API) does **not** forward arbitrary HTTP headers to the container by default. Only headers that have been added to the runtime's [`requestHeaderAllowlist`](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-header-allowlist.html) are propagated, with a hard limit of 20 entries and 4 KB per value. This affects every `McpAuthMode` the Zscaler MCP Server supports.

The deployment configures the runtime automatically based on `McpAuthMode`:

| `McpAuthMode` | Allowlist set by the deployment | `customJwtAuthorizer` configured? | Sandbox playground works without extra effort? |
|---|---|---|---|
| `none` | *(nothing)* | no | yes — no auth |
| `api-key` | `X-Api-Key` | no | yes — see container-side fallback below |
| `zscaler` | `X-Zscaler-Client-ID`, `X-Zscaler-Client-Secret` | no | yes — see container-side fallback below |
| `jwt` | `Authorization` | **yes** — provisioned with discovery URL + audience from `JwtIssuer` / `JwtAudience` (override with `JwtDiscoveryUrl` / `JwtAllowedClients`) | yes — via AgentCore Identity **Sign-In** button (see "Configuring OAuth" below) |

### Container-side credential fallback (api-key and zscaler modes)

The AWS Console Sandbox playground only accepts a JSON payload — there is no UI to attach custom headers. To keep the playground usable, the AWS variant of the MCP server **also accepts credentials from its own environment** in `api-key` and `zscaler` modes. The container reads:

- `ZSCALER_MCP_AUTH_API_KEY` (for `api-key` mode)
- `ZSCALER_CLIENT_ID` and `ZSCALER_CLIENT_SECRET` (for `zscaler` mode)

These are already populated from Secrets Manager at container startup. When an incoming request has neither the allowlisted header nor an `Authorization` value, the auth provider falls back to the env vars. The startup log notes when this fallback is active.

> **Note on the auth boundary.** When the fallback is in play, every request that reaches your container passes the MCP-layer auth check because the container is comparing its own credentials against itself. The real per-caller authorization boundary in this configuration is **AWS IAM** — the caller must have `bedrock-agentcore:InvokeAgentRuntime` on the runtime ARN. This is consistent with the standard IAM-controlled posture for any AgentCore Runtime, and is the recommended pattern when fronting the runtime with AgentCore Gateway or Amazon Quick Suite (both authenticate the user upstream and then call AgentCore with their own IAM identity).

### Invoking the runtime with allowlisted headers

When you need real per-caller authentication (Gateway, Quick Suite, custom boto3 clients, automation), attach the headers explicitly. boto3 exposes botocore events for this:

```python
import json, boto3

RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/zscalermcp-XXXXXX"

client = boto3.client("bedrock-agentcore", region_name="us-east-1")
events = client.meta.events
EVENT = "before-sign.bedrock-agentcore.InvokeAgentRuntime"

# Pick one (matches your McpAuthMode):

# --- api-key ---
def attach_api_key(request, **_):
    request.headers.add_header("X-Api-Key", "sk-...your-key...")
handler = events.register_first(EVENT, attach_api_key)

# --- zscaler ---
# def attach_zscaler(request, **_):
#     request.headers.add_header("X-Zscaler-Client-ID", "<client_id>")
#     request.headers.add_header("X-Zscaler-Client-Secret", "<client_secret>")
# handler = events.register_first(EVENT, attach_zscaler)

# --- jwt ---
# token = ... # obtained from your IdP / AgentCore Identity Sign-In
# def attach_bearer(request, **_):
#     request.headers.add_header("Authorization", f"Bearer {token}")
# handler = events.register_first(EVENT, attach_bearer)

payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode()
response = client.invoke_agent_runtime(agentRuntimeArn=RUNTIME_ARN, payload=payload)
for chunk in response.get("response", []):
    print(chunk.decode("utf-8"), end="")

events.unregister(EVENT, handler)
```

The `agentcore` CLI exposes the same capability via repeated `-H` flags:

```bash
agentcore invoke '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  -H "X-Api-Key: sk-..."
```

---

## Gateway integration (experimental)

> **Status: experimental.** End-to-end Runtime invocation through the Gateway has been verified, but **tool discovery (`tools/list` propagation through the Gateway target)** is inconsistent in current testing — downstream agent platforms see only a subset of the MCP server's tools, or none at all. The Gateway code paths are kept in this integration so you can evaluate the topology, but **production deployments should use the Direct Runtime path** until tool discovery is fully validated.
>
> What has been verified:
>
> - Gateway creation succeeds (both `create` and `attach` modes)
> - Inbound `CUSTOM_JWT` authorizer + `OAUTH` outbound credential provider wiring is correct
> - The runtime itself, called directly via `bedrock-agentcore:InvokeAgentRuntime`, returns the full tool list — so the issue is on the Gateway target / discovery side, not the MCP server
>
> The rest of this section walks through the options for evaluation.

The Zscaler MCP Server runs perfectly well on AgentCore Runtime on its own — downstream callers reach it via `bedrock-agentcore:InvokeAgentRuntime` (boto3, the `agentcore` CLI, or the Console Sandbox). The **AgentCore Gateway** is an opt-in fronting layer that gives you a single OAuth-authenticated MCP URL that downstream agent platforms (Amazon Quick Suite, Bedrock Agents, custom MCP clients) can call without going through `InvokeAgentRuntime`.

The deploy script supports both an **owned-Gateway** and a **bring-your-own-Gateway** pattern. Pick whichever matches your operating model.

### How the deploy script asks about the Gateway

When you run `python aws_mcp_operations.py deploy`, the script reaches **Step 7 — Architecture** and always asks which topology you want:

```text
[1] Direct runtime (no Gateway)                  [recommended]
[2] Provision a new AgentCore Gateway            [experimental]
[3] Attach to an existing AgentCore Gateway      [experimental]

Choice [1-3] (default 1):
```

- Pick **1** for Direct Runtime. The Gateway nested stack is skipped entirely and you don't need any of the `GATEWAY_*` variables below — even if they happen to be set in `.env`, the script writes `EnableAgentCoreGateway=false` into the CloudFormation parameters and ignores them.
- Pick **2** or **3** to enable the experimental Gateway. The script reads `GATEWAY_MODE` and the rest of the `GATEWAY_*` variables from `.env` for the CloudFormation parameters.

`ENABLE_AGENTCORE_GATEWAY` in `.env` is purely a **default for the prompt**: if it's `true`, the prompt defaults to option `[2]` (or `[3]` when `GATEWAY_MODE=attach`); if it's `false` or unset, the prompt defaults to `[1]`. You can always override interactively.

For **non-interactive deploys** (`--non-interactive` flag, CI/CD), the `.env` value is the only signal — the script silently picks based on `ENABLE_AGENTCORE_GATEWAY` and `GATEWAY_MODE`.

### When to enable the Gateway

| Use case | Need a Gateway? |
|---|---|
| Calling the runtime from your own boto3 / Lambda / EC2 / CodeBuild | No |
| Testing in the AgentCore Sandbox playground | No |
| Connecting the runtime to Amazon Quick Suite | Yes (Quick Suite expects an MCP URL, not `InvokeAgentRuntime`) |
| Connecting to Bedrock Agents via an MCP tool | Either path works; Gateway gives you centralized observability + OAuth brokerage |
| Demonstrating end-to-end OAuth 2.0 Authorization Code (3LO) flow | Yes (the Gateway is the OAuth surface) |

### Mode 1 — Create a new Gateway (we own the lifecycle)

Pick option `[2]` at the architecture prompt (or set `GATEWAY_MODE=create` for non-interactive deploys). The deploy script provisions:

- A new `AgentCore Gateway` named `<resource-prefix>-gateway` with `protocolType=MCP` and a `CUSTOM_JWT` inbound authorizer
- A dedicated `GatewayServiceRole` with the AWS-documented permission set for MCP-server targets
- An `mcpServer` target pointing at the runtime's MCP URL, with `JWT_PASSTHROUGH` outbound auth (default) or an OAuth credential provider you supply

`destroy` cascades: target → gateway → service role.

Required `.env` entries for Mode 1 (in addition to the baseline Zscaler credentials):

```env
# Optional — sets the default for the architecture prompt to [2]. For
# interactive deploys, you can omit this and just choose [2] at the prompt.
ENABLE_AGENTCORE_GATEWAY=true
GATEWAY_MODE=create

# Required once Mode 1 is selected.
GATEWAY_INBOUND_DISCOVERY_URL=https://my-tenant.us.auth0.com/.well-known/openid-configuration
GATEWAY_OAUTH_CLIENT_ID=<client-id-quick-suite-uses>
GATEWAY_TOOL_SCHEMA_FILE=tool-schema.json
```

### Mode 2 — Attach to an existing Gateway (you own the lifecycle)

Pick option `[3]` at the architecture prompt (or set `GATEWAY_MODE=attach` for non-interactive deploys) and supply `EXISTING_GATEWAY_ID`. The deploy script:

- Looks up the existing Gateway via `bedrock-agentcore-control:GetGateway`
- Registers our runtime as one of its `mcpServer` targets
- Wires JWT passthrough or your supplied OAuth credential provider on the target

`destroy` removes **only the target we created** — never the Gateway itself. This is the right mode if you already operate a shared Gateway for multiple MCP servers, want to keep its IAM ownership outside this stack, or are demonstrating Zscaler-on-AgentCore on a Gateway provisioned by another team.

Required `.env` entries for Mode 2 (in addition to the baseline Zscaler credentials):

```env
# Optional — sets the default for the architecture prompt to [3]. For
# interactive deploys, you can omit these and just choose [3] at the prompt.
ENABLE_AGENTCORE_GATEWAY=true
GATEWAY_MODE=attach

# Required once Mode 2 is selected.
EXISTING_GATEWAY_ID=<gateway-id-from-bedrock-agentcore-control:ListGateways>
GATEWAY_TOOL_SCHEMA_FILE=tool-schema.json
```

### Inbound JWT claim contract (must read for non-Cognito IdPs)

AgentCore Gateway's `customJWTAuthorizer.allowedClients` matcher is **not** RFC-7519 compliant: it reads the `client_id` claim specifically, which is a Cognito-native convention. Every other major OIDC IdP uses the RFC-standard `azp` claim ("authorized party"). When `allowedClients` can't find a `client_id` to compare against, the Gateway returns `403 insufficient_scope` — a misleading error name that sent the entire industry chasing scope-config rabbit holes when the actual problem was the client-ID claim.

The deploy script works around this transparently by detecting your IdP from the discovery URL and either:

- Emitting `allowedClients` when the IdP is Cognito (claim name = `client_id`), or
- Emitting a `customClaims` matcher on the right claim name for every other IdP (claim name = `azp` for Auth0/Entra/Keycloak/Google, `cid` for Okta).

| IdP | Claim name | Authorizer shape | Override env var if auto-detect picks wrong |
|---|---|---|---|
| Amazon Cognito | `client_id` | `allowedClients` | `GATEWAY_INBOUND_CLIENT_CLAIM_NAME=client_id` |
| Auth0 | `azp` | `customClaims` | `GATEWAY_INBOUND_CLIENT_CLAIM_NAME=azp` |
| Okta | `cid` | `customClaims` | `GATEWAY_INBOUND_CLIENT_CLAIM_NAME=cid` |
| Microsoft Entra ID (v2.0) | `azp` | `customClaims` | `GATEWAY_INBOUND_CLIENT_CLAIM_NAME=azp` |
| Microsoft Entra ID (v1.0) | `appid` | `customClaims` | `GATEWAY_INBOUND_CLIENT_CLAIM_NAME=appid` |
| Keycloak | `azp` | `customClaims` | `GATEWAY_INBOUND_CLIENT_CLAIM_NAME=azp` |
| Google Identity | `azp` | `customClaims` | `GATEWAY_INBOUND_CLIENT_CLAIM_NAME=azp` |

To verify the matcher is going to work before deploying, decode a token your IdP issues for the M2M flow you'll use, and confirm the claim above is present and equal to your OAuth client ID. Auth0 example:

```bash
TOKEN=$(curl -sS -X POST "https://<tenant>.auth0.com/oauth/token" \
  -H "content-type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<CLIENT_ID>" -d "client_secret=<CLIENT_SECRET>" \
  -d "audience=<API_IDENTIFIER>" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
python3 -c "import sys,base64,json; p='$TOKEN'.split('.')[1]; p+='='*((4-len(p)%4)%4); print(json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2))"
```

You should see `"azp": "<CLIENT_ID>"` in the output. If your IdP uses a non-standard claim name, set `GATEWAY_INBOUND_CLIENT_CLAIM_NAME` to that name.

### Setting up the Gateway IdP (Auth0 example)

The Gateway's `CUSTOM_JWT` authorizer needs an OIDC IdP to validate downstream agent tokens against. **AWS does not provide one for you** — you bring your own (Auth0, Cognito, Okta, Entra ID, Keycloak, anything OIDC-compliant). This subsection walks through the Auth0 setup as a concrete example; the same shape applies to any IdP.

You'll create two objects in Auth0: an **API** (the protected resource — the Gateway) and an **Application** (the client that calls the Gateway).

#### 1. Create an Auth0 API

In Auth0 dashboard → **Applications → APIs → Create API**:

| Auth0 field | Value | Used as |
|---|---|---|
| **Name** | `Zscaler MCP Gateway` (label, anything works) | — |
| **Identifier** | `urn:zscaler-mcp:gateway` or `https://zscaler-mcp.example.com/api` | Becomes `aud` claim in tokens. **This is what you paste into `GATEWAY_INBOUND_ALLOWED_AUDIENCE`.** A URI string — doesn't need to be reachable. |
| **Signing algorithm** | RS256 | Required (HS256 won't work — Gateway needs JWKS). |

#### 2. Create an Auth0 Application

In Auth0 dashboard → **Applications → Applications → Create Application**:

| Auth0 field | Value | Used as |
|---|---|---|
| **Application type** | **Machine-to-Machine** (simplest for testing / demos). For real Quick Suite integration, use **Single Page** or **Native** later. | — |
| **Authorize for the API above** | Yes — select the API you just created | Without this, tokens won't have your audience. |
| **Grant Types** | `client_credentials` (auto-set for M2M) | Lets you mint a token via `POST /oauth/token` for testing. |

After saving, grab the **Client ID** from the application's Settings tab. **This goes into `GATEWAY_OAUTH_CLIENT_ID`.** The Client Secret stays in Auth0 — you only need it locally to mint test tokens.

#### 3. Values to paste into `.env`

| Auth0 source | Goes into | What the Gateway does with it |
|---|---|---|
| Tenant domain → `https://<tenant>.auth0.com/` | `GATEWAY_INBOUND_ISSUER` (or paste the discovery URL into `GATEWAY_INBOUND_DISCOVERY_URL`) | Fetches JWKS to verify token signature |
| API **Identifier** from step 1 | `GATEWAY_INBOUND_ALLOWED_AUDIENCE` | Validates `aud` claim |
| Application **Client ID** from step 2 | `GATEWAY_OAUTH_CLIENT_ID` | Matched against the **`azp` claim** for Auth0 (the deploy script auto-detects this; see the table above) |
| Application **Client Secret** from step 2 | `GATEWAY_OAUTH_CLIENT_SECRET` | Used by the Gateway to mint runtime tokens via `client_credentials` |

You can leave `GATEWAY_INBOUND_CLIENT_CLAIM_NAME` unset — auto-detection from the Auth0 issuer URL sets it to `azp` for you.

**Auth0 tenant setting (mandatory, one-time):** Auth0 Dashboard → Settings → General → API Authorization Settings → **Default Audience** = the same value you used for `GATEWAY_INBOUND_ALLOWED_AUDIENCE` (e.g. `urn:zscaler-mcp:gateway`). Without this, Auth0 rejects client_credentials requests with `"No audience parameter was provided, and no default audience has been configured"` because AgentCore Identity cannot pass `audience` per request.

You only need *either* `GATEWAY_INBOUND_ISSUER` *or* `GATEWAY_INBOUND_DISCOVERY_URL` — the script derives one from the other.

#### 4. Smoke-test after the deploy

```bash
# Mint a token via Auth0 (M2M flow)
TOKEN=$(curl -s --request POST \
  --url "https://<your-tenant>.us.auth0.com/oauth/token" \
  --header "content-type: application/json" \
  --data '{
    "client_id":"<APP_CLIENT_ID>",
    "client_secret":"<APP_CLIENT_SECRET>",
    "audience":"<API_IDENTIFIER>",
    "grant_type":"client_credentials"
  }' | jq -r .access_token)

# Call the Gateway with that token
curl -s -X POST "$GATEWAY_MCP_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

If the response lists Zscaler tools, the chain works end-to-end (Auth0 → Gateway → Runtime → MCP).

### Outbound credential provider (Gateway → Runtime)

The Gateway has to authenticate *itself* to the runtime when forwarding a tool call. AWS rejects `JWT_PASSTHROUGH` for `mcpServer` targets, so the only supported path is **`OAUTH` via an AgentCore Identity OAuth2 credential provider**. The deploy script handles this in one of two ways:

- **Auto-provision (default).** Leave `GATEWAY_OAUTH_PROVIDER_ARN` empty. The deploy Lambda calls `bedrock-agentcore-control:create_oauth2_credential_provider` for you, using the same inbound IdP details (discovery URL + `GATEWAY_OAUTH_CLIENT_ID`) plus the secret you provide in `GATEWAY_OAUTH_CLIENT_SECRET`. The provider is created with grant type `CLIENT_CREDENTIALS` and torn down on stack delete.

- **Bring your own.** Set `GATEWAY_OAUTH_PROVIDER_ARN` to an existing provider ARN (e.g. one you created in the console for `MyOrgAuth0Provider`). The stack skips auto-provisioning entirely, ignores `GATEWAY_OAUTH_CLIENT_SECRET`, and binds the target to that provider. Use this to share one provider across deployments or to enforce curated scopes.

#### IdP must accept a vanilla client_credentials request

AgentCore Identity is intentionally minimal: it sends only the standard OAuth 2.0 client_credentials payload to your IdP's `/token` endpoint —

```http
POST /token HTTP/1.1
content-type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=...&client_secret=...&scope=...
```

It does **not** expose any way to add `audience`, `resource`, or other IdP-specific parameters. Any query string you put on the configured `tokenEndpoint` URL is dropped before the POST. This is a hard limit of the AgentCore Identity API surface, not something the deploy script controls.

| IdP | What works out of the box | What you need to configure on the IdP side |
|---|---|---|
| Okta (custom auth servers) | Yes | Nothing — audience is bound to the auth server URL. |
| Amazon Cognito | Yes | Nothing — resource server inferred from scopes. |
| Microsoft Entra ID (v2) | Yes | Use `scope=<api-app-uri>/.default` (set via `GATEWAY_OAUTH_PROVIDER_SCOPES`). |
| Google Identity | Yes | Nothing — scopes alone. |
| Keycloak | Yes | Nothing — audience usually bound to client config. |
| **Auth0** | **No** — Auth0 demands an explicit `audience` per request | **Enable tenant-level Default Audience.** See below. |

##### Auth0-specific one-time setup

Auth0 is the one common IdP that requires `audience` per request *unless* you enable a tenant-level default. The fix is a 30-second click:

1. Auth0 Dashboard → **Settings** → tab **General**
2. Scroll to **API Authorization Settings**
3. Set **Default Audience** = `urn:zscaler-mcp:gateway` (or whatever value you also set as `GATEWAY_INBOUND_ALLOWED_AUDIENCE`)
4. Click **Save**

After this, Auth0 mints client_credentials tokens with `aud: "urn:zscaler-mcp:gateway"` even when the request body has no `audience` param — which is exactly what AgentCore Identity sends.

The deploy script's `GATEWAY_OAUTH_TOKEN_ENDPOINT_QUERY` env var is preserved as an escape hatch for hypothetical future IdPs that accept extra params some other way, but it does **not** rescue Auth0 (AgentCore strips the query string before POSTing).

### Tool schema (SchemaUpfront vs ImplicitSync)

When `GATEWAY_TOOL_SCHEMA_FILE` is empty, the Gateway uses **ImplicitSync** — it crawls the runtime live during target creation, which requires interactive admin OAuth consent and **does not work in CI**. Generate a curated schema once with `python aws_mcp_operations.py export-tool-schema` and ship it via `GATEWAY_TOOL_SCHEMA_FILE` for any production deploy.

### Verifying the Gateway after deploy

```bash
python aws_mcp_operations.py status
```

Look for:

- `GatewayLifecycleMode = create` or `attach`
- `GatewayId` — the ID downstream platforms reference
- `GatewayMcpUrl` — the URL Quick Suite, Bedrock Agents, etc. register
- `GatewayTargetId` — the target we created on the Gateway

To inspect the live target shape:

```bash
aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier <GatewayId> --region us-east-1
```

### When the Gateway path is genuinely overkill

If your only consumer is a Lambda / Step Function / Bedrock Agent inside the same AWS account, calling `InvokeAgentRuntime` directly is simpler and cheaper. Skip the Gateway entirely (leave `ENABLE_AGENTCORE_GATEWAY=false`) and use the boto3 patterns from the "Authentication, custom headers, and AgentCore" section above.

---

## Testing Your Deployment

### Test via AWS Bedrock Sandbox

1. Navigate to **AWS Bedrock AgentCore Console**
2. Select your runtime
3. Open the **Test** or **Sandbox** tab
4. Send a test request:

#### Test 1: List Available Tools

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Expected response:**

```json
{
  "status": "success",
  "tool": "tools/list",
  "result": {
    "tools": [
      {"name": "zia_list_ssl_inspection_rules", "description": "..."},
      {"name": "zpa_list_app_segments", "description": "..."},
      ...
    ]
  }
}
```

#### Test 2: Call a Zscaler Tool

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "zia_list_ssl_inspection_rules",
    "arguments": {}
  }
}
```

**Expected response:**

```json
{
  "status": "success",
  "tool": "zia_list_ssl_inspection_rules",
  "result": [
    "{\n  \"id\": 184200,\n  \"name\": \"Zscaler Recommended Exemptions\",\n  ..."
  ]
}
```

✅ **Success!** Real data from Zscaler API.

---

## Configuring OAuth (Auth0) for AgentCore Identity

When the Zscaler MCP Server is deployed with **JWT authentication** (Layer 1), the Bedrock AgentCore Test Sandbox cannot send `Authorization: Bearer <token>` headers by default. Configuring Auth0 as an identity provider in AgentCore enables the sandbox and agent to obtain tokens and forward them to your MCP runtime.

### Prerequisites

- MCP runtime deployed with JWT auth (e.g. via `deploy_with_jwt.sh`)
- Auth0 tenant with a Machine-to-Machine (M2M) application
- Client ID and Client Secret from the Auth0 app
- API audience configured (e.g. `zscaler-mcp-server`)

### Step-by-Step: Add Auth0 OAuth Client

1. **Open the Identity menu**
   - In the AWS console, go to **Amazon Bedrock AgentCore**
   - In the left sidebar under **Build**, select **Identity**

2. **Add OAuth Client**
   - Click **Add OAuth Client**
   - You will see the "Add OAuth Client" form

3. **Name**
   - Enter a name (e.g. `auth0-zscaler-mcp` or accept the auto-generated one)
   - Valid characters: `a-z`, `A-Z`, `0-9`, `_` (underscore), `-` (hyphen)
   - Max 50 characters

4. **Provider**
   - Select **Included provider** (not Custom provider)
   - From the dropdown, choose **Auth0 by Okta**

5. **Provider configurations**
   Fill in the fields with values from your Auth0 tenant. Example for **acme.us.auth0.com**:

   | Field | Value |
   |-------|-------|
   | **Client ID** | `x7hEmN5MikTZXhZkOnTMRlQlbtiiPCce` |
   | **Client secret** | *(Use the value from Auth0 Dashboard → Applications, or from `AUTH0_CLIENT_SECRET` in your env)* |
   | **Issuer** | `https://acme.us.auth0.com/` |
   | **Authorization endpoint** | `https://acme.us.auth0.com/authorize` |
   | **Token endpoint** | `https://acme.us.auth0.com/oauth/token` |

   For a different Auth0 tenant, use these URL patterns (replace `YOUR_TENANT` with your domain):

   - **Issuer:** `https://YOUR_TENANT/` (trailing slash required)
   - **Authorization endpoint:** `https://YOUR_TENANT/authorize`
   - **Token endpoint:** `https://YOUR_TENANT/oauth/token`

6. **Save**
   - Click **Add** (or equivalent) to create the OAuth client

### Step 2: Add the Callback URL to Auth0 (Required)

After creating the OAuth client, Bedrock displays a **Callback URL** on the provider details page. You must add this URL to your Auth0 application.

1. In the provider details (e.g. for `MyOrgAuth0Provider`), locate the **Callback URL** (e.g. `https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback/76ae34e8-117e-4a20-989e-b8b0b27216fa`).
2. Copy the full URL.
3. In **Auth0 Dashboard** → **Applications** → your application → **Settings**.
4. In **Allowed Callback URLs**, add the Bedrock callback URL (comma-separated if you have others).
5. Click **Save Changes**.

Without this step, the OAuth flow will fail when the sandbox or agent tries to obtain tokens.

### Step 3: Associate the OAuth Client for Sandbox Testing

The success message says: *"Associate it within your local agent code or in a Gateway target."*

**For Agent Sandbox testing:**

1. **If using Agent Sandbox with a Runtime** – When you open the sandbox and select your Zscaler MCP runtime, look for:
   - A **Sign in** or **Connect** option that lets you authenticate with an identity provider.
   - A dropdown or settings to select **MyOrgAuth0Provider** (or your provider name).
   - After signing in, the sandbox should obtain tokens and include them in `Authorization: Bearer` headers when invoking the runtime.

2. **If using a Gateway** – When the Zscaler MCP runtime is exposed through a Gateway (as a target), add the OAuth credential provider when creating or editing the Gateway target:
   - In the Gateway target configuration, set the **credentials** / **credential provider** to the ARN of your Auth0 provider (e.g. `arn:aws:bedrock-agentcore:us-east-1:123456789012:token-vault/default/oauth2credentialprovider/MyOrgAuth0Provider`).

3. **If using local agent code** – Use the identity provider ARN in your agent’s configuration when it connects to the MCP runtime, so the agent can fetch tokens and attach them to MCP requests.

The provider ARN is shown on the provider details page (e.g. `arn:aws:bedrock-agentcore:us-east-1:123456789012:token-vault/default/oauth2credentialprovider/MyOrgAuth0Provider`).

### Step 4: Verify Auth0 API and Audience

- Ensure your Auth0 API has an identifier (e.g. `zscaler-mcp-server`) that matches the `AUDIENCE` in your MCP deployment.
- The `audience` parameter is required for Auth0 to return JWT (not opaque) tokens.

### Troubleshooting Identity Configuration

- **401 Unauthorized from MCP** – Ensure the OAuth client’s issuer and endpoints match the values used by your MCP server’s JWT validation (`ZSCALER_MCP_AUTH_ISSUER`, JWKS URI, etc.).
- **Token not sent** – Confirm the OAuth client is associated with the runtime/gateway used for testing.
- **Audience mismatch** – Ensure your Auth0 API has the same audience (e.g. `zscaler-mcp-server`) as configured in `AUDIENCE` in your deployment.
- **OAuth redirect/callback errors** – Add the Bedrock callback URL (from the provider details page) to Auth0 **Allowed Callback URLs**.

---

## Troubleshooting

### Issue: Stack Creation Fails with "AgentRuntimeDeployment CREATE_FAILED"

**Check Lambda logs:**

```bash
aws logs tail /aws/lambda/zscalermcp-deployment \
  --region us-east-1 \
  --since 10m
```

**Common causes:**

1. **ECR Image URI incorrect** - Verify your account ID is correct
2. **IAM permissions missing** - Check Lambda role has `bedrock-agentcore:*`
3. **Secret not found** - Verify secret name matches

### Issue: Container Fails to Start

**Check container logs:**

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/RUNTIME_ID-DEFAULT \
  --region us-east-1 \
  --since 10m
```

**Common causes:**

1. **"Failed to retrieve secret"** - Check IAM role has Secrets Manager permissions
2. **"Secret not found"** - Verify secret name is correct
3. **"AccessDenied"** - Check IAM role permissions

### Issue: Tools Return "Zscaler SDK failed to initialize"

**Check if credentials are loaded:**

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/RUNTIME_ID-DEFAULT \
  --region us-east-1 \
  --since 5m | grep "Set environment variable"
```

**Expected:** Should see all credential variables being set.

**If using Secrets Manager:**

- Verify secret contains all required fields
- Check IAM role has `secretsmanager:GetSecretValue`

**If using direct env vars:**

- Verify all credentials are in the `--environment-variables` parameter

### Issue: Credentials Visible in AgentCore Config

**This is expected if using Direct Environment Variables approach.**

**If using Secrets Manager and still seeing credentials:**

- Check that `ZSCALER_SECRET_NAME` is set in environment variables
- Check container logs for "using credentials from environment variables directly"

---

## Security Best Practices

### For Production Deployments

1. ✅ **Use Secrets Manager** - Container-based retrieval
2. ✅ **Enable KMS encryption** - Use AWS managed or customer managed keys
3. ✅ **Restrict IAM permissions** - Least privilege access
4. ✅ **Enable CloudTrail** - Audit all secret access
5. ✅ **Rotate credentials regularly** - Use Secrets Manager rotation
6. ✅ **Monitor CloudWatch logs** - Set up alarms for errors
7. ✅ **Use VPC endpoints** - For private network access (if needed)

### For Development/Testing

1. ✅ **Use separate credentials** - Don't use production credentials
2. ✅ **Consider Secrets Manager** - Even for dev (good practice)
3. ✅ **Clear shell history** - After using direct env vars: `history -c`
4. ✅ **Don't commit credentials** - Never commit `.env` files or scripts with credentials

---

## Encryption Details

### Secrets Manager Encryption

**Default Encryption:**

- ✅ AWS Secrets Manager **always encrypts** secrets at rest
- ✅ Uses AWS managed KMS key: `alias/aws/secretsmanager`
- ✅ Encryption is automatic and transparent

**Custom KMS Key (Optional):**

```bash
# Create custom KMS key
aws kms create-key \
  --description "Zscaler MCP Server credentials encryption key" \
  --region us-east-1

# Create secret with custom key
aws secretsmanager create-secret \
  --name zscaler/mcp/credentials \
  --kms-key-id <your-kms-key-id> \
  --secret-string '{...}' \
  --region us-east-1
```

**Verify encryption:**

```bash
aws secretsmanager describe-secret \
  --secret-id zscaler/mcp/credentials \
  --region us-east-1 \
  --query 'KmsKeyId'
```

### CloudFormation Template Encryption

The CloudFormation template explicitly specifies KMS encryption:

```yaml
ZscalerCredentialsSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    KmsKeyId: 'alias/aws/secretsmanager'  # ← AWS managed KMS key
    SecretString: !Sub |
      { ... }
```

✅ **All secrets created by the CloudFormation template are encrypted with KMS.**

---

## Migration Between Approaches

### From Direct Environment Variables → Secrets Manager

1. **Extract current credentials:**

   ```bash
   aws bedrock-agentcore-control get-agent-runtime \
     --region us-east-1 \
     --agent-runtime-id <runtime-id> \
     --query 'environmentVariables' > current-creds.json
   ```

2. **Create Secrets Manager secret:**

   ```bash
   aws secretsmanager create-secret \
     --name zscaler/mcp/credentials \
     --kms-key-id alias/aws/secretsmanager \
     --secret-string file://current-creds.json \
     --region us-east-1
   ```

3. **Update IAM role** - Add Secrets Manager permissions

4. **Delete old runtime:**

   ```bash
   aws bedrock-agentcore-control delete-agent-runtime \
     --region us-east-1 \
     --agent-runtime-id <old-runtime-id>
   ```

5. **Deploy new runtime** - Using Secrets Manager approach (see above)

### From Secrets Manager → Direct Environment Variables

1. **Get credentials from secret:**

   ```bash
   aws secretsmanager get-secret-value \
     --secret-id zscaler/mcp/credentials \
     --region us-east-1 \
     --query 'SecretString' --output text > credentials.json
   ```

2. **Delete old runtime**

3. **Deploy new runtime** - Using direct environment variables approach (see above)

---

## Summary

### Recommended Approach for Production

**CloudFormation + Secrets Manager:**

```text
Click Launch Stack Button
  ↓
Select "UseExisting" or "CreateNew"
  ↓
Fill in parameters
  ↓
Deploy (3-5 minutes)
  ↓
✅ Secure, encrypted, production-ready
```

### Quick Approach for Testing

**Manual CLI + Direct Environment Variables:**

```text
Create IAM role (basic permissions)
  ↓
Run aws bedrock-agentcore-control create-agent-runtime
  ↓
Pass credentials directly
  ↓
✅ Fast, simple, good for testing
```

---

## Environment variable reference

The integration deliberately keeps the user-facing surface small. The deploy script (via the runtime provisioner Lambda) and the container image set most plumbing values internally — you should rarely need to touch them. The tables below split what's intended for users versus what the system manages itself, and map to the same layout in `integrations/aws/bedrock-agentcore/env.properties`.

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
| `AWS_RESOURCE_NAME_PREFIX` | `zscaler-mcp` | Prefix for all named resources. |
| `AWS_ASSET_BUCKET` | auto-generated | S3 bucket for nested templates. Leave blank to auto-generate. |
| `ZSCALER_MCP_IMAGE_URI` | bundled Marketplace tag | Override to pin a specific image tag, mirror, or dev build. |
| `ZSCALER_MCP_WRITE_ENABLED` | `false` | Enable create/update/delete tools. |
| `ZSCALER_MCP_WRITE_TOOLS` | (unset) | Wildcard allowlist when writes are on, e.g. `zpa_create_*,zia_update_*`. |
| `ZSCALER_MCP_DISABLED_TOOLS` | (unset) | Wildcard blocklist for individual tools. |
| `ZSCALER_MCP_DISABLED_SERVICES` | (unset) | Comma-separated service blocklist (`zcc,zdx`). |
| `ZSCALER_MCP_LOG_TOOL_CALLS` | `true` | Audit every tool call to CloudWatch. |

### User-facing — authentication (mode-dependent)

Pick the block matching your `ZSCALER_MCP_AUTH_MODE`.

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

See [Gateway integration (experimental)](#gateway-integration-experimental) for the current state of testing before setting these.

| Variable | Mode | Purpose |
|---|---|---|
| `ENABLE_AGENTCORE_GATEWAY` | both | Default for the interactive architecture prompt: `true` defaults the prompt to option `[2]`/`[3]`, `false` (or unset) defaults to `[1]` Direct Runtime. For non-interactive deploys this is the only signal. |
| `GATEWAY_MODE` | both | `create` (stack provisions Gateway) or `attach` (use existing). Pairs with `ENABLE_AGENTCORE_GATEWAY` to pick the prompt default — `create` → `[2]`, `attach` → `[3]`. |
| `EXISTING_GATEWAY_ID` | `attach` | ID of a Gateway you already operate. |
| `GATEWAY_INBOUND_DISCOVERY_URL` | `create` | IdP OIDC discovery URL for the Gateway's `customJwtAuthorizer`. |
| `GATEWAY_INBOUND_ISSUER` | `create` | Alternative to discovery URL. |
| `GATEWAY_OAUTH_CLIENT_ID` | `create` | Comma-separated OAuth client_id allowlist. |
| `GATEWAY_INBOUND_ALLOWED_AUDIENCE` | `create` | Expected `aud` claim. |
| `GATEWAY_INBOUND_ALLOWED_SCOPES` | `create` | Required scope(s); also published in `scopes_supported` metadata. |
| `GATEWAY_INBOUND_CLIENT_CLAIM_NAME` | `create` (rare) | Override the client-id claim name when auto-detection picks wrong. |
| `GATEWAY_OAUTH_CLIENT_SECRET` | `create` | Secret for the auto-provisioned outbound credential provider. |
| `GATEWAY_OAUTH_PROVIDER_ARN` | `create` | Reuse an existing OAuth provider (alternative to auto-provisioning). |
| `GATEWAY_OAUTH_PROVIDER_SCOPES` | `create` (rare) | Optional scope override for the outbound provider. |
| `GATEWAY_OAUTH_PROVIDER_GRANT_TYPE` | `create` (rare) | `CLIENT_CREDENTIALS` (default) / `AUTHORIZATION_CODE` / `TOKEN_EXCHANGE`. |
| `GATEWAY_OAUTH_TOKEN_ENDPOINT_QUERY` | `create` (rare) | Escape hatch for IdP-specific quirks. Auth0 ignores it — use tenant-level Default Audience instead. |
| `GATEWAY_TOOL_SCHEMA_FILE` | both | Path to a JSON tool schema. Strongly recommended — puts the target in SchemaUpfront mode. |

### Internal — set by the runtime provisioner / Dockerfile (do not set manually)

These are documented for transparency only. The deploy script and the container image set them automatically; setting them yourself in `env.properties` either gets overwritten at deploy time or breaks the deployment. They map directly to behaviour the AgentCore Runtime topology requires.

| Variable | Set to | Why it's internal |
|---|---|---|
| `FASTMCP_STATELESS_HTTP` | `true` (Dockerfile) | AgentCore Runtime replicas are ephemeral and may be replaced between requests; stateful sessions would pin to dead replicas. |
| `ZSCALER_MCP_ALLOW_HTTP` | `true` (provisioner) | AgentCore terminates TLS upstream of the container, so the inner HTTP server runs plain HTTP. |
| `ZSCALER_MCP_DISABLE_HOST_VALIDATION` | `true` (provisioner) | AgentCore is the sole ingress and has already authenticated the request before forwarding. The internal Host header is not predictable for an inner allowlist. |
| `ZSCALER_MCP_AUTH_ENABLED` | `true`/`false` (provisioner) | Derived from `McpAuthMode`. |
| `ZSCALER_MCP_TRANSPORT` / `ZSCALER_MCP_HOST` / `ZSCALER_MCP_PORT` | `streamable-http` / `0.0.0.0` / `8000` (Dockerfile CMD) | Required for AgentCore Runtime to forward MCP traffic correctly. |
| `AWS_REGION` | injected by AgentCore | Used by the container's Secrets Manager loader. |

**Defense-in-depth toggles** (not surfaced in `env.properties` and not exposed by the deploy script): `ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION`, `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER`, `ZSCALER_MCP_SKIP_CONFIRMATIONS`, `ZSCALER_MCP_CONFIRMATION_TTL`. These remove security layers and should only be set for short-lived debugging.

---

## Additional Resources

- [CloudFormation README](../../AWS/zscaler-mcp-server/local_dev/cloudformation/README.md) - Detailed CloudFormation guide
- [Secrets Manager Integration](../../AWS/zscaler-mcp-server/docs/SECRETS_MANAGER_INTEGRATION.md) - Security implementation details
- [Development Process](../../AWS/zscaler-mcp-server/docs/DEVELOPMENT_PROCESS.md) - Design decisions and rationale
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/)

---

**Document Version:** 2.0.0
**Last Updated:** November 22, 2025
**Deployment Methods:** CloudFormation (recommended), Manual AWS CLI
**Credential Approaches:** Secrets Manager (recommended), Direct Environment Variables
