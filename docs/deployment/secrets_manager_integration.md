# AWS Secrets Manager Integration with Bedrock AgentCore

This guide provides the **exact steps** to integrate AWS Secrets Manager with the Zscaler MCP Server on Amazon Bedrock AgentCore.

## Important Discovery

After reviewing the AWS CLI API documentation for `bedrock-agentcore-control create-agent-runtime`, the following parameters are available:

```json
{
  "agentRuntimeName": "",
  "description": "",
  "agentRuntimeArtifact": { "containerConfiguration": {...} },
  "roleArn": "",
  "networkConfiguration": {...},
  "protocolConfiguration": {...},
  "environmentVariables": {...},
  "authorizerConfiguration": {...}
}
```

**Key Finding**: There is **NO** `identity-configuration` or `secretsManagerConfiguration` parameter in the current AgentCore API.

This means:

- ❌ AgentCore does NOT have built-in Secrets Manager integration at the container configuration level
- ❌ No native "token vault" parameter for automatic secret injection
- ✅ You must use one of the practical approaches below

---

## Available Approaches

| Approach | Container Changes | Complexity | Security | Recommended For |
|----------|------------------|------------|----------|-----------------|
| **1. Pre-Deployment Retrieval** | ❌ None | Low | Good | Most users |
| **2. Container Runtime Retrieval** | ✅ Required | Medium | Better | Enterprise |
| **3. Lambda Proxy** | ❌ None | Medium | Good | Automated pipelines |

---

## Approach 1: Pre-Deployment Secret Retrieval (Recommended)

Retrieve secrets from Secrets Manager **before** creating the agent runtime and pass them as environment variables.

### ✅ Advantages

- No container modifications
- Simple to implement
- Works with existing image
- Easy to automate

### ⚠️ Considerations

- Credentials visible in AWS console (in agent runtime configuration)
- Requires re-deployment for rotation

### Complete Implementation

#### Step 1: Create Secret in Secrets Manager

```bash
aws secretsmanager create-secret \
  --region us-east-1 \
  --name zscaler/mcp/credentials \
  --description "Zscaler MCP Server API Credentials" \
  --secret-string '{
    "ZSCALER_CLIENT_ID": "your_client_id",
    "ZSCALER_CLIENT_SECRET": "your_client_secret",
    "ZSCALER_VANITY_DOMAIN": "your_domain",
    "ZSCALER_CUSTOMER_ID": "your_customer_id",
    "ZSCALER_CLOUD": "production",
    "ZSCALER_MCP_WRITE_ENABLED": "true",
    "ZSCALER_MCP_WRITE_TOOLS": "zpa_*,zia_*"
  }'
```

**Verify the secret:**

```bash
aws secretsmanager get-secret-value \
  --region us-east-1 \
  --secret-id zscaler/mcp/credentials \
  --query SecretString \
  --output text | jq
```

#### Step 2: Grant Deployment User/Role Secrets Manager Access

Your **deployment user or role** (not the AgentCore execution role) needs permission to read secrets:

```bash
cat > deployment-secrets-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadZscalerSecrets",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:zscaler/mcp/*"
      ]
    }
  ]
}
EOF

# Attach to your deployment user
aws iam put-user-policy \
  --user-name your-deployment-user \
  --policy-name ZscalerSecretsDeploymentAccess \
  --policy-document file://deployment-secrets-policy.json

# OR attach to your deployment role
aws iam put-role-policy \
  --role-name your-deployment-role \
  --policy-name ZscalerSecretsDeploymentAccess \
  --policy-document file://deployment-secrets-policy.json
```

> [!IMPORTANT]
> The **Bedrock AgentCore execution role does NOT need Secrets Manager permissions** with this approach. Only your deployment user/role needs access.

#### Step 3: Create Deployment Script

Create or update `run_bedrock.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "Zscaler MCP - Bedrock AgentCore Deployment"
echo "with AWS Secrets Manager Integration"
echo "=========================================="
echo ""

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
SECRET_NAME="${SECRET_NAME:-zscaler/mcp/credentials}"
AGENT_NAME="zscalermcp"
AGENT_DESCRIPTION="Zscaler MCP Server Agent"
ROLE_ARN="arn:aws:iam::202719523534:role/bedrock-core-zscaler-role"
ECR_IMAGE="202719523534.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest"

echo "Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  Secret Name: $SECRET_NAME"
echo "  Agent Name: $AGENT_NAME"
echo "  Role ARN: $ROLE_ARN"
echo "  ECR Image: $ECR_IMAGE"
echo ""

# Step 1: Retrieve secrets from Secrets Manager
echo "📦 Step 1: Retrieving credentials from AWS Secrets Manager..."
SECRET_JSON=$(aws secretsmanager get-secret-value \
  --region "$AWS_REGION" \
  --secret-id "$SECRET_NAME" \
  --query SecretString \
  --output text 2>&1)

if [ $? -ne 0 ]; then
  echo "❌ ERROR: Failed to retrieve secret from Secrets Manager"
  echo ""
  echo "Error details:"
  echo "$SECRET_JSON"
  echo ""
  echo "Troubleshooting:"
  echo "  1. Verify the secret exists: aws secretsmanager describe-secret --secret-id $SECRET_NAME"
  echo "  2. Check IAM permissions for your user/role"
  echo "  3. Verify the region is correct"
  exit 1
fi

echo "   ✓ Secret retrieved successfully"
echo ""

# Step 2: Parse and validate credentials
echo "🔍 Step 2: Parsing credentials..."

ZSCALER_CLIENT_ID=$(echo "$SECRET_JSON" | jq -r '.ZSCALER_CLIENT_ID // empty')
ZSCALER_CLIENT_SECRET=$(echo "$SECRET_JSON" | jq -r '.ZSCALER_CLIENT_SECRET // empty')
ZSCALER_VANITY_DOMAIN=$(echo "$SECRET_JSON" | jq -r '.ZSCALER_VANITY_DOMAIN // empty')
ZSCALER_CUSTOMER_ID=$(echo "$SECRET_JSON" | jq -r '.ZSCALER_CUSTOMER_ID // empty')
ZSCALER_CLOUD=$(echo "$SECRET_JSON" | jq -r '.ZSCALER_CLOUD // "production"')
ZSCALER_MCP_WRITE_ENABLED=$(echo "$SECRET_JSON" | jq -r '.ZSCALER_MCP_WRITE_ENABLED // "false"')
ZSCALER_MCP_WRITE_TOOLS=$(echo "$SECRET_JSON" | jq -r '.ZSCALER_MCP_WRITE_TOOLS // ""')

# Validate required credentials
if [ -z "$ZSCALER_CLIENT_ID" ] || [ -z "$ZSCALER_CLIENT_SECRET" ]; then
  echo "❌ ERROR: Required credentials missing from secret"
  echo ""
  echo "The secret must contain:"
  echo "  - ZSCALER_CLIENT_ID"
  echo "  - ZSCALER_CLIENT_SECRET"
  echo ""
  echo "Current secret structure:"
  echo "$SECRET_JSON" | jq
  exit 1
fi

echo "   ✓ Credentials parsed and validated"
echo ""
echo "   Loaded credentials:"
echo "     - Client ID: ${ZSCALER_CLIENT_ID:0:10}..."
echo "     - Vanity Domain: $ZSCALER_VANITY_DOMAIN"
echo "     - Customer ID: ${ZSCALER_CUSTOMER_ID:0:10}..."
echo "     - Cloud: $ZSCALER_CLOUD"
echo "     - Write Mode: $ZSCALER_MCP_WRITE_ENABLED"
if [ "$ZSCALER_MCP_WRITE_ENABLED" = "true" ]; then
  echo "     - Write Tools: $ZSCALER_MCP_WRITE_TOOLS"
fi
echo ""

# Step 3: Deploy to Bedrock AgentCore
echo "🚀 Step 3: Deploying to Amazon Bedrock AgentCore..."
echo ""

aws bedrock-agentcore-control create-agent-runtime \
  --region "$AWS_REGION" \
  --agent-runtime-name "$AGENT_NAME" \
  --description "$AGENT_DESCRIPTION" \
  --agent-runtime-artifact "{
    \"containerConfiguration\": {
      \"containerUri\": \"$ECR_IMAGE\"
    }
  }" \
  --role-arn "$ROLE_ARN" \
  --network-configuration '{
    "networkMode": "PUBLIC"
  }' \
  --protocol-configuration '{
    "serverProtocol": "MCP"
  }' \
  --environment-variables "{
    \"ZSCALER_CLIENT_ID\": \"$ZSCALER_CLIENT_ID\",
    \"ZSCALER_CLIENT_SECRET\": \"$ZSCALER_CLIENT_SECRET\",
    \"ZSCALER_VANITY_DOMAIN\": \"$ZSCALER_VANITY_DOMAIN\",
    \"ZSCALER_CUSTOMER_ID\": \"$ZSCALER_CUSTOMER_ID\",
    \"ZSCALER_CLOUD\": \"$ZSCALER_CLOUD\",
    \"ZSCALER_MCP_WRITE_ENABLED\": \"$ZSCALER_MCP_WRITE_ENABLED\",
    \"ZSCALER_MCP_WRITE_TOOLS\": \"$ZSCALER_MCP_WRITE_TOOLS\"
  }"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Verify status: aws bedrock-agentcore-control get-agent-runtime --region $AWS_REGION --agent-runtime-id <ID>"
echo "  2. View logs: aws logs tail /aws/bedrock-agentcore/runtimes/<ID> --region $AWS_REGION --follow"
echo "  3. Test: Send a tools/list or tools/call request"
echo ""
```

#### Step 4: Make Executable and Deploy

```bash
chmod +x run_bedrock.sh
./run_bedrock.sh
```

#### Step 5: Verify Deployment

```bash
# Get the runtime ID from the deployment output, then:
aws bedrock-agentcore-control get-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id <AGENT_RUNTIME_ID>
```

**Expected output:**

```json
{
  "agentRuntimeName": "zscalermcp",
  "status": "READY",
  "environmentVariables": {
    "ZSCALER_CLIENT_ID": "ipm2ol7odg7hp",
    "ZSCALER_VANITY_DOMAIN": "securitygeekio",
    ...
  }
}
```

---

## Approach 2: Container Runtime Secret Retrieval

This approach modifies the container to retrieve secrets at runtime (when the container starts).

### ✅ Advantages

- Secrets not visible in AWS console
- Credentials retrieved fresh on each container start
- Better security posture

### ⚠️ Considerations

- Requires container modifications
- Need to rebuild and push Docker image
- AgentCore execution role needs Secrets Manager permissions

### Complete Implementation

#### Step 1: Create Secret (Same as Approach 1)

```bash
aws secretsmanager create-secret \
  --region us-east-1 \
  --name zscaler/mcp/credentials \
  --description "Zscaler MCP Server API Credentials" \
  --secret-string '{
    "ZSCALER_CLIENT_ID": "your_client_id",
    "ZSCALER_CLIENT_SECRET": "your_client_secret",
    "ZSCALER_VANITY_DOMAIN": "your_domain",
    "ZSCALER_CUSTOMER_ID": "your_customer_id",
    "ZSCALER_CLOUD": "production"
  }'
```

#### Step 2: Grant AgentCore Execution Role Secrets Manager Access

**This is different from Approach 1** - the container needs to access Secrets Manager at runtime:

```bash
cat > agentcore-secrets-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecretsManagerRuntimeAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:zscaler/mcp/*"
      ]
    }
  ]
}
EOF

# Attach to the AgentCore execution role
aws iam put-role-policy \
  --role-name bedrock-core-zscaler-role \
  --policy-name SecretsManagerRuntimeAccess \
  --policy-document file://agentcore-secrets-policy.json
```

#### Step 3: Modify web_server.py

Add secret retrieval logic at the top of `web_server.py` (before initializing the MCP server):

```python
import boto3
import json
import os
from botocore.exceptions import ClientError

def load_secrets_from_aws_secrets_manager():
    """
    Load Zscaler credentials from AWS Secrets Manager at container startup.
    
    This function is called before initializing the MCP server to retrieve
    credentials from Secrets Manager and set them as environment variables.
    """
    # Check if Secrets Manager should be used
    use_secrets_manager = os.getenv('USE_SECRETS_MANAGER', 'false').lower() == 'true'
    
    if not use_secrets_manager:
        logger.info("USE_SECRETS_MANAGER not enabled, using direct environment variables")
        return
    
    logger.info("=" * 80)
    logger.info("🔐 Loading credentials from AWS Secrets Manager")
    logger.info("=" * 80)
    
    # Configuration
    secret_name = os.getenv('SECRET_NAME', 'zscaler/mcp/credentials')
    region_name = os.getenv('AWS_REGION', 'us-east-1')
    
    logger.info(f"Secret Name: {secret_name}")
    logger.info(f"Region: {region_name}")
    
    # Create Secrets Manager client
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
    except Exception as e:
        logger.error(f"Failed to create Secrets Manager client: {e}")
        raise
    
    # Retrieve secret
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret_string = get_secret_value_response['SecretString']
        secrets = json.loads(secret_string)
        
        logger.info("✓ Secret retrieved successfully from Secrets Manager")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Secret '{secret_name}' not found in region '{region_name}'")
        elif error_code == 'InvalidRequestException':
            logger.error(f"Invalid request to Secrets Manager: {e}")
        elif error_code == 'InvalidParameterException':
            logger.error(f"Invalid parameter: {e}")
        elif error_code == 'AccessDeniedException':
            logger.error(f"Access denied to secret '{secret_name}'")
            logger.error("Verify the IAM role has secretsmanager:GetSecretValue permission")
        else:
            logger.error(f"Error retrieving secret: {e}")
        
        raise e
    
    except json.JSONDecodeError as e:
        logger.error(f"Secret value is not valid JSON: {e}")
        raise
    
    # Validate and set environment variables
    required_fields = ['ZSCALER_CLIENT_ID', 'ZSCALER_CLIENT_SECRET']
    missing_fields = [field for field in required_fields if not secrets.get(field)]
    
    if missing_fields:
        logger.error(f"Required credentials missing from secret: {', '.join(missing_fields)}")
        raise ValueError(f"Missing required fields in secret: {', '.join(missing_fields)}")
    
    # Set environment variables from secrets
    os.environ['ZSCALER_CLIENT_ID'] = secrets.get('ZSCALER_CLIENT_ID', '')
    os.environ['ZSCALER_CLIENT_SECRET'] = secrets.get('ZSCALER_CLIENT_SECRET', '')
    os.environ['ZSCALER_VANITY_DOMAIN'] = secrets.get('ZSCALER_VANITY_DOMAIN', '')
    os.environ['ZSCALER_CUSTOMER_ID'] = secrets.get('ZSCALER_CUSTOMER_ID', '')
    os.environ['ZSCALER_CLOUD'] = secrets.get('ZSCALER_CLOUD', 'production')
    
    # Optional: Load write mode configuration from secret
    if 'ZSCALER_MCP_WRITE_ENABLED' in secrets:
        os.environ['ZSCALER_MCP_WRITE_ENABLED'] = str(secrets['ZSCALER_MCP_WRITE_ENABLED'])
    if 'ZSCALER_MCP_WRITE_TOOLS' in secrets:
        os.environ['ZSCALER_MCP_WRITE_TOOLS'] = str(secrets['ZSCALER_MCP_WRITE_TOOLS'])
    
    logger.info("✓ Credentials loaded and set as environment variables")
    logger.info(f"  - Client ID: {os.environ['ZSCALER_CLIENT_ID'][:10]}...")
    logger.info(f"  - Vanity Domain: {os.environ['ZSCALER_VANITY_DOMAIN']}")
    logger.info(f"  - Cloud: {os.environ['ZSCALER_CLOUD']}")
    logger.info("=" * 80)


# Load secrets BEFORE initializing the MCP server
try:
    load_secrets_from_aws_secrets_manager()
except Exception as e:
    logger.error(f"Failed to load secrets: {e}")
    logger.error("Server will not start without valid credentials")
    sys.exit(1)

# Create instance of Zscaler MCP server (now has credentials in env vars)
logger.info("Initializing Zscaler MCP Server instance")
mcp_server = ZscalerMCPServer()
```

Add the import at the top of the file:

```python
import sys  # Add if not already present
```

#### Step 4: Update requirements.txt

Ensure boto3 is included (should already be there):

```txt
boto3>=1.34.0
botocore>=1.34.0
```

#### Step 5: Rebuild and Push Docker Image

```bash
# Build
docker build -t zscaler/zscaler-mcp-server .

# Tag
docker tag zscaler/zscaler-mcp-server:latest \
  202719523534.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest

# Push
docker push 202719523534.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest
```

#### Step 6: Deploy Agent Runtime

Deploy with minimal environment variables (secrets retrieved at runtime):

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --region us-east-1 \
  --agent-runtime-name "zscalermcp" \
  --description "Zscaler MCP Server with Runtime Secret Retrieval" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "202719523534.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest"
    }
  }' \
  --role-arn "arn:aws:iam::202719523534:role/bedrock-core-zscaler-role" \
  --network-configuration '{
    "networkMode": "PUBLIC"
  }' \
  --protocol-configuration '{
    "serverProtocol": "MCP"
  }' \
  --environment-variables '{
    "USE_SECRETS_MANAGER": "true",
    "SECRET_NAME": "zscaler/mcp/credentials",
    "AWS_REGION": "us-east-1",
    "ZSCALER_MCP_WRITE_ENABLED": "false"
  }'
```

> [!NOTE]
> Notice that `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, etc. are **NOT** in environment variables. They're retrieved from Secrets Manager when the container starts.

#### Step 7: Verify Deployment

```bash
# Check status
aws bedrock-agentcore-control get-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id <AGENT_RUNTIME_ID>

# Check CloudWatch logs
aws logs tail /aws/bedrock-agentcore/runtimes/<AGENT_RUNTIME_ID> \
  --region us-east-1 \
  --follow
```

**Expected log output:**

```text
================================================================================
🔐 Loading credentials from AWS Secrets Manager
================================================================================
Secret Name: zscaler/mcp/credentials
Region: us-east-1
✓ Secret retrieved successfully from Secrets Manager
✓ Credentials loaded and set as environment variables
  - Client ID: ipm2ol7odg...
  - Vanity Domain: securitygeekio
  - Cloud: production
================================================================================
Initializing Zscaler MCP Server instance
```

---

## Approach 3: Lambda Proxy for Deployment

Use a Lambda function to retrieve secrets and deploy the agent runtime.

### Implementation

#### Step 1: Create Lambda Function

```python
import boto3
import json
import os

def lambda_handler(event, context):
    """
    Lambda function to deploy Bedrock AgentCore runtime with secrets from Secrets Manager.
    
    Trigger: Manually, or via EventBridge schedule for redeployment
    """
    secrets_client = boto3.client('secretsmanager')
    agentcore_client = boto3.client('bedrock-agentcore-control')
    
    # Configuration
    secret_name = os.environ.get('SECRET_NAME', 'zscaler/mcp/credentials')
    region = os.environ.get('AWS_REGION', 'us-east-1')
    role_arn = os.environ['ROLE_ARN']
    ecr_image = os.environ['ECR_IMAGE']
    agent_name = os.environ.get('AGENT_NAME', 'zscalermcp')
    
    # Retrieve secrets
    try:
        secret_response = secrets_client.get_secret_value(SecretId=secret_name)
        credentials = json.loads(secret_response['SecretString'])
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Failed to retrieve secrets: {str(e)}')
        }
    
    # Deploy agent runtime
    try:
        response = agentcore_client.create_agent_runtime(
            region=region,
            agentRuntimeName=agent_name,
            description='Zscaler MCP Server Agent',
            agentRuntimeArtifact={
                'containerConfiguration': {
                    'containerUri': ecr_image
                }
            },
            roleArn=role_arn,
            networkConfiguration={
                'networkMode': 'PUBLIC'
            },
            protocolConfiguration={
                'serverProtocol': 'MCP'
            },
            environmentVariables={
                'ZSCALER_CLIENT_ID': credentials['ZSCALER_CLIENT_ID'],
                'ZSCALER_CLIENT_SECRET': credentials['ZSCALER_CLIENT_SECRET'],
                'ZSCALER_VANITY_DOMAIN': credentials.get('ZSCALER_VANITY_DOMAIN', ''),
                'ZSCALER_CUSTOMER_ID': credentials.get('ZSCALER_CUSTOMER_ID', ''),
                'ZSCALER_CLOUD': credentials.get('ZSCALER_CLOUD', 'production'),
                'ZSCALER_MCP_WRITE_ENABLED': str(credentials.get('ZSCALER_MCP_WRITE_ENABLED', 'false')),
                'ZSCALER_MCP_WRITE_TOOLS': credentials.get('ZSCALER_MCP_WRITE_TOOLS', '')
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Agent runtime created successfully',
                'agentRuntimeId': response['agentRuntimeId'],
                'agentRuntimeArn': response['agentRuntimeArn']
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Failed to create agent runtime: {str(e)}')
        }
```

#### Step 2: Create Lambda IAM Role

```bash
cat > lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name ZscalerMCPDeploymentLambdaRole \
  --assume-role-policy-document file://lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name ZscalerMCPDeploymentLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Add Secrets Manager permissions
cat > lambda-secrets-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:zscaler/mcp/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateAgentRuntime",
        "bedrock-agentcore:DeleteAgentRuntime",
        "bedrock-agentcore:GetAgentRuntime",
        "bedrock-agentcore:ListAgentRuntimes"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::*:role/bedrock-core-zscaler-role"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ZscalerMCPDeploymentLambdaRole \
  --policy-name ZscalerMCPDeploymentPolicy \
  --policy-document file://lambda-secrets-policy.json
```

#### Step 3: Deploy Lambda Function

```bash
# Package the function
zip lambda-deployment.zip lambda_function.py

# Create Lambda function
aws lambda create-function \
  --region us-east-1 \
  --function-name ZscalerMCPDeployment \
  --runtime python3.12 \
  --role arn:aws:iam::<ACCOUNT_ID>:role/ZscalerMCPDeploymentLambdaRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 60 \
  --environment Variables="{
    SECRET_NAME=zscaler/mcp/credentials,
    ROLE_ARN=arn:aws:iam::202719523534:role/bedrock-core-zscaler-role,
    ECR_IMAGE=202719523534.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest,
    AGENT_NAME=zscalermcp
  }"
```

#### Step 4: Invoke Lambda to Deploy

```bash
aws lambda invoke \
  --region us-east-1 \
  --function-name ZscalerMCPDeployment \
  response.json

cat response.json
```

---

## Credential Rotation

### For Approach 1 (Pre-Deployment)

```bash
#!/bin/bash
# rotate_and_redeploy.sh

# Step 1: Update secret
aws secretsmanager update-secret \
  --region us-east-1 \
  --secret-id zscaler/mcp/credentials \
  --secret-string '{
    "ZSCALER_CLIENT_ID": "new_client_id",
    "ZSCALER_CLIENT_SECRET": "new_client_secret",
    "ZSCALER_VANITY_DOMAIN": "your_domain",
    "ZSCALER_CUSTOMER_ID": "your_customer_id",
    "ZSCALER_CLOUD": "production"
  }'

# Step 2: Get current runtime ID
RUNTIME_ID=$(aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='zscalermcp'].agentRuntimeId" \
  --output text)

# Step 3: Delete runtime
aws bedrock-agentcore-control delete-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id $RUNTIME_ID

# Step 4: Wait for deletion
echo "Waiting for deletion..."
sleep 15

# Step 5: Redeploy with new credentials
./run_bedrock.sh
```

### For Approach 2 (Runtime Retrieval)

```bash
#!/bin/bash
# rotate_and_restart.sh

# Step 1: Update secret
aws secretsmanager update-secret \
  --region us-east-1 \
  --secret-id zscaler/mcp/credentials \
  --secret-string '{...}'

# Step 2: Restart agent runtime (delete and recreate)
RUNTIME_ID=$(aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='zscalermcp'].agentRuntimeId" \
  --output text)

aws bedrock-agentcore-control delete-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id $RUNTIME_ID

sleep 15

# Redeploy (credentials will be retrieved from updated secret)
aws bedrock-agentcore-control create-agent-runtime \
  --region us-east-1 \
  --agent-runtime-name "zscalermcp" \
  --environment-variables '{
    "USE_SECRETS_MANAGER": "true",
    "SECRET_NAME": "zscaler/mcp/credentials",
    "AWS_REGION": "us-east-1"
  }' \
  # ... rest of config
```

---

## Comparison Matrix

| Aspect | Approach 1: Pre-Deployment | Approach 2: Runtime Retrieval | Approach 3: Lambda Proxy |
|--------|---------------------------|------------------------------|--------------------------|
| **Container Changes** | ❌ None | ✅ Required | ❌ None |
| **Secrets Visible in Console** | ✅ Yes (env vars) | ❌ No | ✅ Yes (env vars) |
| **AgentCore Role Needs SM Access** | ❌ No | ✅ Yes | ❌ No |
| **Deployment Complexity** | Low | Medium | Medium |
| **Rotation Process** | Update secret → Redeploy | Update secret → Restart | Update secret → Invoke Lambda |
| **Best For** | Most users | High security requirements | Automated pipelines |

---

## Recommendation

### For Most Users: **Approach 1** (Pre-Deployment Retrieval)

**Why:**

- ✅ No container modifications needed
- ✅ Works with existing Docker image
- ✅ Simple bash script
- ✅ Easy to understand and maintain
- ✅ Secrets stored in Secrets Manager (not in git)
- ⚠️ Credentials visible in AgentCore console (acceptable for most use cases)

### For High Security Requirements: **Approach 2** (Runtime Retrieval)

**Why:**

- ✅ Credentials never visible in console
- ✅ Retrieved fresh on each container start
- ✅ Better audit trail
- ⚠️ Requires container rebuild
- ⚠️ More complex to implement

### For CI/CD Automation: **Approach 3** (Lambda Proxy)

**Why:**

- ✅ Fully automated
- ✅ No manual deployment steps
- ✅ Can trigger on schedule or events
- ⚠️ Additional Lambda function to maintain

---

## Quick Start

### Approach 1 (Recommended for Most Users)

```bash
# 1. Create secret
aws secretsmanager create-secret \
  --region us-east-1 \
  --name zscaler/mcp/credentials \
  --secret-string '{"ZSCALER_CLIENT_ID":"...","ZSCALER_CLIENT_SECRET":"...",...}'

# 2. Grant your deployment user Secrets Manager access
aws iam put-user-policy \
  --user-name your-user \
  --policy-name ZscalerSecretsAccess \
  --policy-document file://deployment-secrets-policy.json

# 3. Use the updated run_bedrock.sh script (from Step 3 above)
chmod +x run_bedrock.sh
./run_bedrock.sh

# Done! ✅ No container changes needed
```

### Approach 2 (For High Security)

```bash
# 1. Create secret (same as above)

# 2. Grant AgentCore execution role Secrets Manager access
aws iam put-role-policy \
  --role-name bedrock-core-zscaler-role \
  --policy-name SecretsManagerAccess \
  --policy-document file://agentcore-secrets-policy.json

# 3. Modify web_server.py (add code from Step 3 above)

# 4. Rebuild and push Docker image
docker build -t zscaler/zscaler-mcp-server .
docker tag zscaler/zscaler-mcp-server:latest <ECR_URI>
docker push <ECR_URI>

# 5. Deploy with USE_SECRETS_MANAGER=true
aws bedrock-agentcore-control create-agent-runtime \
  --environment-variables '{"USE_SECRETS_MANAGER":"true",...}' \
  # ... rest of config

# Done! ✅ Credentials retrieved at runtime
```

---

## Security Best Practices

### 1. Use Least Privilege IAM Policies

Only grant access to specific secrets:

```json
{
  "Resource": [
    "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:zscaler/mcp/credentials-*"
  ]
}
```

The `-*` suffix allows for versioning while restricting to your specific secret.

### 2. Enable CloudTrail Logging

Monitor all secret access:

```bash
aws cloudtrail lookup-events \
  --region us-east-1 \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=zscaler/mcp/credentials \
  --max-results 50
```

### 3. Use Separate Secrets Per Environment

```bash
# Development
aws secretsmanager create-secret \
  --name zscaler/mcp/credentials/dev \
  --secret-string '{...}'

# Production
aws secretsmanager create-secret \
  --name zscaler/mcp/credentials/prod \
  --secret-string '{...}'
```

Update your scripts to use environment-specific secrets:

```bash
ENVIRONMENT="${ENVIRONMENT:-prod}"
SECRET_NAME="zscaler/mcp/credentials/$ENVIRONMENT"
```

### 4. Enable Secret Versioning and Rotation

```bash
# Enable automatic rotation (requires Lambda function)
aws secretsmanager rotate-secret \
  --region us-east-1 \
  --secret-id zscaler/mcp/credentials \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:RotateZscalerCredentials \
  --rotation-rules AutomaticallyAfterDays=30
```

### 5. Use Resource-Based Policies

Add an additional layer of security:

```bash
cat > secret-resource-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::202719523534:role/bedrock-core-zscaler-role",
          "arn:aws:iam::202719523534:user/deployment-user"
        ]
      },
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "202719523534"
        }
      }
    }
  ]
}
EOF

aws secretsmanager put-resource-policy \
  --region us-east-1 \
  --secret-id zscaler/mcp/credentials \
  --resource-policy file://secret-resource-policy.json
```

---

## Troubleshooting

### Issue: "Access Denied to Secret"

**Symptom:**

```text
AccessDeniedException: User is not authorized to perform: secretsmanager:GetSecretValue
```

**Solution:**

1. **For Approach 1**: Check your deployment user/role permissions

   ```bash
   aws iam get-user-policy \
     --user-name your-user \
     --policy-name ZscalerSecretsAccess
   ```

2. **For Approach 2**: Check the AgentCore execution role permissions

   ```bash
   aws iam get-role-policy \
     --role-name bedrock-core-zscaler-role \
     --policy-name SecretsManagerRuntimeAccess
   ```

3. Test access manually:

   ```bash
   aws secretsmanager get-secret-value \
     --region us-east-1 \
     --secret-id zscaler/mcp/credentials
   ```

### Issue: "Secret Not Found"

**Symptom:**

```text
ResourceNotFoundException: Secrets Manager can't find the specified secret
```

**Solution:**

1. List secrets to verify it exists:

   ```bash
   aws secretsmanager list-secrets \
     --region us-east-1 \
     --filters Key=name,Values=zscaler/mcp
   ```

2. Check the region matches

3. Verify the secret name is exact (case-sensitive)

### Issue: "Container Fails to Start" (Approach 2)

**Symptom:**
Agent runtime status shows `FAILED`

**Solution:**

1. Check CloudWatch logs:

   ```bash
   aws logs tail /aws/bedrock-agentcore/runtimes/<AGENT_RUNTIME_ID> \
     --region us-east-1 \
     --follow
   ```

2. Look for errors like:
   - "Failed to create Secrets Manager client"
   - "Access denied to secret"
   - "Missing required fields in secret"

3. Test the container locally:

   ```bash
   docker run -it --rm \
     -e USE_SECRETS_MANAGER=true \
     -e SECRET_NAME=zscaler/mcp/credentials \
     -e AWS_REGION=us-east-1 \
     -e AWS_ACCESS_KEY_ID=<YOUR_KEY> \
     -e AWS_SECRET_ACCESS_KEY=<YOUR_SECRET> \
     -p 8000:8000 \
     zscaler/zscaler-mcp-server:latest
   ```

### Issue: "Invalid JSON in Secret"

**Symptom:**

```text
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solution:**

Validate your secret structure:

```bash
aws secretsmanager get-secret-value \
  --region us-east-1 \
  --secret-id zscaler/mcp/credentials \
  --query SecretString \
  --output text | jq .
```

Ensure it's valid JSON with required fields:

```json
{
  "ZSCALER_CLIENT_ID": "...",
  "ZSCALER_CLIENT_SECRET": "...",
  "ZSCALER_VANITY_DOMAIN": "...",
  "ZSCALER_CUSTOMER_ID": "...",
  "ZSCALER_CLOUD": "production"
}
```

---

## Cost Analysis

### AWS Secrets Manager Costs

| Component | Cost | Calculation |
|-----------|------|-------------|
| Secret storage | $0.40/month | Per secret |
| API calls | $0.05/10,000 calls | Per retrieval |

### Example Scenarios

#### Scenario 1: Approach 1 (Pre-Deployment)

- 1 secret
- 20 deployments/month
- **Cost: $0.40/month** (API calls negligible)

#### Scenario 2: Approach 2 (Runtime Retrieval)

- 1 secret
- Container restarts 100 times/month
- **Cost: $0.40/month** (API calls negligible)

#### Scenario 3: Multi-Environment

- 3 secrets (dev/staging/prod)
- 50 total deployments/month
- **Cost: $1.20/month**

> [!NOTE]
> Secrets Manager costs are minimal. Even with frequent rotations, the cost is typically under $5/month.

---

## Summary

### Key Findings

1. **AgentCore does NOT have native Secrets Manager integration** at the API level
2. **No `identity-configuration` parameter exists** in current AgentCore API
3. **You must choose one of the three practical approaches** outlined above

### Recommended Approach

For **most users**: **Approach 1 (Pre-Deployment Retrieval)**

- Simplest to implement
- No container changes
- Works immediately
- Secrets in Secrets Manager (not in git)
- Good enough security for most use cases

For **high security requirements**: **Approach 2 (Runtime Retrieval)**

- Credentials never visible in console
- Retrieved at container startup
- Requires container modification
- Best security posture

For **automated pipelines**: **Approach 3 (Lambda Proxy)**

- Fully automated
- Event-driven deployments
- Centralized deployment logic

---

## Additional Resources

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Zscaler MCP Server GitHub](https://github.com/zscaler/zscaler-mcp-server)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
