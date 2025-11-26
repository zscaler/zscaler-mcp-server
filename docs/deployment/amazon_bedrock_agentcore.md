# Deploying Zscaler MCP Server to Amazon Bedrock AgentCore

This guide provides complete instructions for deploying the Zscaler MCP Server to Amazon Bedrock AgentCore with **two deployment methods** and **two credential management approaches**.

## 📋 Table of Contents

- [Deployment Methods Overview](#deployment-methods-overview)
- [Credential Management Approaches](#credential-management-approaches)
- [Prerequisites](#prerequisites)
- [Method 1: CloudFormation Deployment (Recommended)](#method-1-cloudformation-deployment-recommended)
- [Method 2: Manual AWS CLI Deployment](#method-2-manual-aws-cli-deployment)
- [Testing Your Deployment](#testing-your-deployment)
- [Troubleshooting](#troubleshooting)

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
