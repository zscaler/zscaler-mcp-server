.. _guide-secrets-manager:

AWS Secrets Manager Integration with Bedrock AgentCore
======================================================

This guide provides the steps to integrate AWS Secrets Manager with the Zscaler MCP Server on Amazon Bedrock AgentCore.

Important Discovery
-------------------

After reviewing the AWS CLI API documentation for ``bedrock-agentcore-control create-agent-runtime``, the following parameters are available:

.. code-block:: json

   {
     "agentRuntimeName": "",
     "description": "",
     "agentRuntimeArtifact": { "containerConfiguration": {} },
     "roleArn": "",
     "networkConfiguration": {},
     "protocolConfiguration": {},
     "environmentVariables": {},
     "authorizerConfiguration": {}
   }

**Key Finding**: There is **NO** ``identity-configuration`` or ``secretsManagerConfiguration`` parameter in the current AgentCore API.

This means:

- AgentCore does NOT have built-in Secrets Manager integration at the container configuration level
- No native "token vault" parameter for automatic secret injection
- You must use one of the practical approaches below

Available Approaches
--------------------

.. list-table::
   :header-rows: 1
   :widths: 30 18 15 15 22

   * - Approach
     - Container Changes
     - Complexity
     - Security
     - Recommended For
   * - **1. Pre-Deployment Retrieval**
     - None
     - Low
     - Good
     - Most users
   * - **2. Container Runtime Retrieval**
     - Required
     - Medium
     - Better
     - Enterprise
   * - **3. Lambda Proxy**
     - None
     - Medium
     - Good
     - Automated pipelines

Approach 1: Pre-Deployment Secret Retrieval (Recommended)
---------------------------------------------------------

Retrieve secrets from Secrets Manager **before** creating the agent runtime and pass them as environment variables.

Advantages
~~~~~~~~~~

- No container modifications
- Simple to implement
- Works with existing image
- Easy to automate

Considerations
~~~~~~~~~~~~~~

- Credentials visible in AWS console (in agent runtime configuration)
- Requires re-deployment for rotation

Step 1: Create Secret in Secrets Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

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

**Verify the secret:**

.. code-block:: bash

   aws secretsmanager get-secret-value \
     --region us-east-1 \
     --secret-id zscaler/mcp/credentials \
     --query SecretString \
     --output text | jq

Step 2: Grant Deployment User/Role Secrets Manager Access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your **deployment user or role** (not the AgentCore execution role) needs permission to read secrets:

.. code-block:: bash

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

Step 3: Retrieve Secrets and Build Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Retrieve the secret
   SECRET_JSON=$(aws secretsmanager get-secret-value \
     --region us-east-1 \
     --secret-id zscaler/mcp/credentials \
     --query SecretString \
     --output text)

   # Parse the JSON values into shell variables
   ZSCALER_CLIENT_ID=$(echo $SECRET_JSON | jq -r '.ZSCALER_CLIENT_ID')
   ZSCALER_CLIENT_SECRET=$(echo $SECRET_JSON | jq -r '.ZSCALER_CLIENT_SECRET')
   ZSCALER_VANITY_DOMAIN=$(echo $SECRET_JSON | jq -r '.ZSCALER_VANITY_DOMAIN')
   ZSCALER_CUSTOMER_ID=$(echo $SECRET_JSON | jq -r '.ZSCALER_CUSTOMER_ID')

Step 4: Create AgentCore Runtime with Retrieved Secrets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   aws bedrock-agentcore-control create-agent-runtime \
     --agent-runtime-name zscaler-mcp-server \
     --description "Zscaler MCP Server with Secrets Manager" \
     --role-arn arn:aws:iam::ACCOUNT_ID:role/zscaler-mcp-execution-role \
     --network-configuration '{"networkMode":"PUBLIC"}' \
     --protocol-configuration '{"serverProtocol":"MCP"}' \
     --environment-variables "{
       \"ZSCALER_CLIENT_ID\":\"$ZSCALER_CLIENT_ID\",
       \"ZSCALER_CLIENT_SECRET\":\"$ZSCALER_CLIENT_SECRET\",
       \"ZSCALER_VANITY_DOMAIN\":\"$ZSCALER_VANITY_DOMAIN\",
       \"ZSCALER_CUSTOMER_ID\":\"$ZSCALER_CUSTOMER_ID\"
     }" \
     --agent-runtime-artifact "containerConfiguration={
       containerUri=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest
     }" \
     --region us-east-1

Approach 2: Container Runtime Retrieval
---------------------------------------

The container retrieves secrets from Secrets Manager at startup using boto3, so secrets are never visible in the AgentCore configuration.

Advantages
~~~~~~~~~~

- Secrets NEVER appear in AgentCore configuration
- Secrets NEVER appear in CloudFormation/CDK templates
- Automatic rotation support (re-fetch on restart)
- Strongest security posture

Considerations
~~~~~~~~~~~~~~

- Requires container code changes (already implemented in ``zscaler_mcp/config.py``)
- AgentCore execution role needs Secrets Manager access
- Slight startup delay (~100ms for secret retrieval)

How It Works
~~~~~~~~~~~~

The Zscaler MCP Server's container image already includes ``zscaler_mcp/config.py``, a side-effect module that runs at process boot via ``aws_entrypoint.py``:

1. The deploy script writes the credential JSON to a Secrets Manager entry (e.g. ``zscaler-mcp/credentials``).
2. The AgentCore runtime task definition gets only ``ZSCALER_SECRET_NAME=<that-name>`` — never the actual credential values.
3. The execution role gets a scoped two-statement inline policy: ``secretsmanager:GetSecretValue`` on the secret ARN + ``kms:Decrypt`` filtered by ``kms:ViaService=secretsmanager.<region>``.
4. At container boot, ``config.py`` calls ``GetSecretValue`` via boto3, parses the JSON, and ``os.environ``-injects each key. The SDK then initialises exactly as if the keys had been passed as env vars.

Required IAM Policy for the Execution Role
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The AgentCore **execution role** (the role passed to ``create-agent-runtime --role-arn``) needs the following inline policy:

.. code-block:: json

   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "ReadZscalerCredentialsSecret",
         "Effect": "Allow",
         "Action": ["secretsmanager:GetSecretValue"],
         "Resource": [
           "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:zscaler/mcp/credentials-*"
         ]
       },
       {
         "Sid": "DecryptZscalerCredentialsSecret",
         "Effect": "Allow",
         "Action": ["kms:Decrypt"],
         "Resource": "*",
         "Condition": {
           "StringEquals": {
             "kms:ViaService": "secretsmanager.us-east-1.amazonaws.com"
           }
         }
       }
     ]
   }

The ``-*`` ARN wildcard handles the random 6-char suffix Secrets Manager appends to secret ARNs.

Deploying with Container Runtime Retrieval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After creating the secret (same as Approach 1, Step 1) and granting the execution role the policy above:

.. code-block:: bash

   aws bedrock-agentcore-control create-agent-runtime \
     --agent-runtime-name zscaler-mcp-server \
     --description "Zscaler MCP Server with container-side secret retrieval" \
     --role-arn arn:aws:iam::ACCOUNT_ID:role/zscaler-mcp-execution-role \
     --network-configuration '{"networkMode":"PUBLIC"}' \
     --protocol-configuration '{"serverProtocol":"MCP"}' \
     --environment-variables '{
       "ZSCALER_SECRET_NAME": "zscaler/mcp/credentials",
       "AWS_REGION": "us-east-1"
     }' \
     --agent-runtime-artifact "containerConfiguration={
       containerUri=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest
     }" \
     --region us-east-1

Notice the environment variables now contain **only** ``ZSCALER_SECRET_NAME`` and ``AWS_REGION`` — the actual Zscaler credentials never leave Secrets Manager.

Approach 3: Lambda Proxy
------------------------

A Lambda function acts as a proxy: it fetches the secret from Secrets Manager and creates the AgentCore runtime with the retrieved values, all within an automated pipeline.

Best for: CI/CD pipelines, GitOps deployments, multi-environment automation.

The flow is:

1. CI/CD triggers a Lambda function
2. Lambda retrieves the secret from Secrets Manager
3. Lambda calls ``bedrock-agentcore-control:CreateAgentRuntime`` with the retrieved values as env vars
4. Lambda destroys the temporary credential strings from memory

This pattern is essentially Approach 1 wrapped in a Lambda — same security model, but the secret-retrieval step never runs on a developer workstation.

Secret rotation
---------------

For Approach 1 (Pre-Deployment Retrieval), rotation requires re-deploying the AgentCore runtime with the new credentials.

For Approach 2 (Container Runtime Retrieval), rotation works automatically because the container re-fetches the secret on every cold start. To force a refresh:

.. code-block:: bash

   # Rotate the secret
   aws secretsmanager put-secret-value \
     --region us-east-1 \
     --secret-id zscaler/mcp/credentials \
     --secret-string '{"ZSCALER_CLIENT_SECRET":"new_secret",...}'

   # Force the AgentCore runtime to cycle (creates a new task with fresh env)
   aws bedrock-agentcore-control update-agent-runtime \
     --agent-runtime-name zscaler-mcp-server \
     --region us-east-1 \
     ...

Security comparison summary
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 23 23 24

   * - Property
     - Approach 1
     - Approach 2
     - Approach 3
   * - Container changes needed
     - No
     - Yes
     - No
   * - Secrets in AgentCore config
     - Yes
     - No
     - Yes
   * - Secrets in CloudTrail (CreateAgentRuntime call)
     - Yes
     - No
     - Yes (Lambda call only)
   * - Rotation requires redeploy
     - Yes
     - No
     - Yes
   * - Suitable for production
     - With caveats
     - Yes
     - Yes
   * - Suitable for compliance regimes (SOC2, ISO27001, PCI-DSS)
     - Limited
     - Yes
     - Yes

Use Approach 2 whenever you can — the Zscaler MCP Server container image already supports it.

See also
--------

- :doc:`amazon-bedrock-agentcore` — full AgentCore Runtime deployment walkthrough.
- :doc:`aws-harness` — AgentCore Harness preview, which uses Approach 2 by default.
- :doc:`strands-agentcore` — local Strands client for testing a deployed runtime.
