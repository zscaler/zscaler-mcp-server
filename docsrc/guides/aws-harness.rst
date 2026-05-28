.. _guide-aws-harness:

AWS Harness — AgentCore Harness deployment
==========================================

.. warning::

   **Status: Preview.** AgentCore Harness is a managed agent layer announced at AWS re:Invent 2025 — currently in **preview** with limited regional coverage. This integration tracks the preview API surface; expect breaking changes before GA.

This guide covers the deployment of the Zscaler MCP Server as an AgentCore **Harness** tool. For the existing **AgentCore Runtime** deployment (Direct Runtime + experimental Gateway), see :doc:`amazon-bedrock-agentcore`.

Pick a topology
---------------

The script supports two end-to-end deployment shapes. Pass ``--topology`` (or set ``TOPOLOGY`` in ``.env``); omit both and the script prompts interactively.

.. list-table::
   :header-rows: 1
   :widths: 16 16 28 12 28

   * - Topology
     - Tool type
     - MCP server runs on
     - IdP
     - When to pick
   * - ``ecs`` (default)
     - ``remote_mcp``
     - ECS Express Mode service (Fargate + auto-ALB)
     - n/a (Basic auth from Token Vault)
     - Simplest path; fewest moving parts; no Cognito to manage.
   * - ``gateway``
     - ``agentcore_gateway``
     - AgentCore Runtime (managed)
     - Amazon Cognito
     - No ALB / ECS / Fargate. Same Gateway can later front other MCP clients (Cursor/Claude/Strands) with a real OIDC login.

.. code-block:: text

   ecs topology                          gateway topology
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

What is AgentCore Harness?
--------------------------

**Harness is a managed agent.** You declare ``model``, ``systemPrompt``, ``tools``, ``memory``, and ``limits`` once via ``bedrock-agentcore-control:CreateHarness``; AWS runs the agent loop. Under the hood it is Strands Agents on AgentCore Runtime — both still exist; Harness is just the higher-level surface AWS now markets as the go-to-production path.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Property
     - Detail
   * - **Service**
     - Amazon Bedrock AgentCore — ``bedrock-agentcore-control`` (control plane) + ``bedrock-agentcore`` (data plane)
   * - **API**
     - ``CreateHarness``, ``GetHarness``, ``UpdateHarness``, ``DeleteHarness``, ``ListHarnesses``, ``InvokeHarness``
   * - **boto3**
     - ≥ 1.43.0 (earlier versions don't expose the API)
   * - **Tools**
     - ``remote_mcp``, ``agentcore_gateway``, ``agentcore_browser``, ``agentcore_code_interpreter``, ``inline_function``
   * - **Auth**
     - Static ``Authorization`` header (plain or resolved from AgentCore Identity Token Vault)
   * - **Memory**
     - Optional (AgentCore Memory). Opt-in per harness.
   * - **Observability**
     - Auto-emitted to CloudWatch under ``/aws/bedrock-agentcore/harness/<id>``

The Zscaler MCP Server fits exclusively as a **``remote_mcp``** tool — a URL Harness will call over HTTPS with whatever headers we configure.

Critical constraint — ``remote_mcp`` headers are static
--------------------------------------------------------

Harness's ``remote_mcp`` tool can **only send static ``Authorization`` headers**. It has no SigV4 signer. That means:

- **A SigV4-protected AgentCore Runtime URL will not work** as a ``remote_mcp`` target. Pointing Harness at ``https://bedrock-agentcore.<region>.amazonaws.com/runtimes/...`` produces HTTP 403 on every invocation.
- **Recommended:** let this script deploy the MCP server to ECS Express Mode (default path — auto-managed ALB + HTTPS). Or stand it up yourself behind any other non-SigV4 endpoint and pass the URL via ``MCP_URL=…``.
- **Alternative (now shipped):** AgentCore Gateway between Harness and a SigV4 Runtime URL — the Gateway does the OAuth → SigV4 protocol switch for you. Set ``--topology gateway`` (or ``TOPOLOGY=gateway``).

Prerequisites
-------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Requirement
     - Notes
   * - AWS account with **AgentCore Harness preview** access
     - Currently limited to a subset of regions. Confirm via ``aws bedrock-agentcore-control list-harnesses --region <r>``.
   * - AWS CLI / boto3 credentials
     - The script uses the default credential chain. ``aws sts get-caller-identity`` should succeed.
   * - Python 3.10+
     - One runtime dependency (``boto3``).
   * - Bedrock model access
     - At minimum the Claude Sonnet 4.6 inference profile (or whichever model you pick). Anthropic models additionally require a one-time **use-case form** in the Bedrock console.
   * - Permission to call ``ecs:CreateExpressGatewayService`` and ``iam:PassRole``
     - Granted by ``AdministratorAccess``.
   * - Default VPC in the target region
     - ECS Express auto-selects subnets + security groups from the default VPC.
   * - AWS Marketplace subscription to Zscaler MCP Server
     - Free (BYOL). Required if you let the script use the default Marketplace image.
   * - ``linux/amd64`` image
     - The Marketplace image is multi-arch; **dev builds must include ``linux/amd64``**.
   * - Zscaler OneAPI credentials
     - ``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_CUSTOMER_ID``, ``ZSCALER_VANITY_DOMAIN``.

Install
-------

.. code-block:: bash

   cd integrations/aws/harness
   uv venv .harness-venv --python 3.11
   source .harness-venv/bin/activate
   uv pip install -r requirements.txt

Configure
---------

Copy the template and fill in your Zscaler credentials:

.. code-block:: bash

   cp env.properties .env
   ${EDITOR:-vim} .env

You can also pass values as CLI flags or let the script prompt you interactively — ``env.properties`` is for convenience.

Deploy
------

.. code-block:: bash

   python harness_mcp_operations.py deploy --region us-east-1

The script walks the full stack in one run (≈4-5 minutes — most of it is the ECS Express ALB + target group health-check warm-up). The deploy creates:

1. **ECS task execution + infrastructure roles** — for cross-account ECR pull, CloudWatch Logs, and the auto-ALB provisioning.
2. **ECS cluster** (``zscaler-mcp``) — created if missing; preserved on destroy if it pre-existed.
3. **CloudWatch log group** (``/ecs/zscaler-mcp``).
4. **ECS Express service** (``zscaler-mcp-server``) — single ``CreateExpressGatewayService`` call provisions ALB + target group + security groups + auto-scaling. Returns a stable public HTTPS endpoint of the form ``xxxxx.ecs.<region>.on.aws``.
5. **AgentCore Identity Token Vault credential provider** (``zscaler-mcp-creds``) — stores ``Basic base64(client_id:client_secret)``.
6. **AWS IAM Harness execution role** (``zscaler-mcp-harness-execution-role``) — mirrors the AWS-published harness execution role policy.
7. **AgentCore Harness** (``zscaler-mcp-harness``) — wired to a model + system prompt + the ``remote_mcp`` tool block pointing at the ECS Express URL with the Token Vault credential provider as the ``Authorization`` substitution target.

State persisted to ``.aws-harness-state.json`` (gitignored).

What success looks like
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ── Deployment summary ─────────────────────────────────────────────────────────
     HarnessId              = zscaler-mcp-harness-AbCdEfGhIj
     HarnessArn             = arn:aws:bedrock-agentcore:us-east-1:111122223333:harness/zscaler-mcp-harness-AbCdEfGhIj
     Model                  = us.anthropic.claude-sonnet-4-5-20250929-v1:0
     MCP URL                = https://abc123.ecs.us-east-1.on.aws/mcp
     MCP Host               = ECS Express — zscaler-mcp-server (cluster: zscaler-mcp)
     Execution Role         = arn:aws:iam::111122223333:role/zscaler-mcp-harness-execution-role
     Credential Provider    = arn:aws:bedrock-agentcore:us-east-1:111122223333:token-vault/default/apikeycredentialprovider/zscaler-mcp-creds

Lifecycle commands
------------------

.. code-block:: bash

   python harness_mcp_operations.py status   --region us-east-1
   python harness_mcp_operations.py logs     --region us-east-1
   python harness_mcp_operations.py invoke "list my zpa segment groups" --region us-east-1
   python harness_mcp_operations.py destroy  --region us-east-1 [--yes] [--keep-role] [--keep-ecs]

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Command
     - Description
   * - ``deploy``
     - End-to-end walk-through. Idempotent on re-deploy — reuses existing ECS cluster, ECS Express service, IAM roles, log group, and credential provider when they already exist by name.
   * - ``status``
     - ``GetHarness`` + pretty-print of status, model, tool list, timestamps. When the ECS Express host is in state, also prints the service status, cluster, image, and public endpoint.
   * - ``logs``
     - Tails the auto-managed AgentCore runtime log group under ``/aws/bedrock-agentcore/runtimes/<runtime-id>``.
   * - ``invoke``
     - One-shot smoke test: opens an ``InvokeHarness`` event stream, prints text deltas, surfaces the stop reason and token usage.
   * - ``destroy``
     - Reverse-order tear-down. Use ``--keep-role`` to preserve IAM roles and ``--keep-ecs`` to preserve the MCP host across redeploys.

Authentication design
---------------------

The Zscaler MCP Server has five auth modes (``OIDCProxy``, ``JWT``, ``API Key``, ``Zscaler``, ``None``). Harness's ``remote_mcp`` tool pairs with them as follows:

.. list-table::
   :header-rows: 1
   :widths: 20 55 25

   * - MCP auth mode
     - Harness header config
     - Recommended?
   * - **Zscaler**
     - ``Authorization: ${arn:…/zscaler-mcp-creds}`` — Token Vault resolves to ``Basic base64(client_id:client_secret)``
     - **Yes — this script's default.** Rotation handled by Token Vault.
   * - **API Key**
     - ``Authorization: ${arn:…/zscaler-api-key}`` — plain bearer
     - Yes, if you'd rather use a static bearer instead of OneAPI.
   * - **JWT**
     - ``Authorization: Bearer <long-lived JWT>`` plaintext, or Token-Vault resolved if rotation is needed
     - Less common. JWT is usually short-lived.
   * - **OIDCProxy**
     - Use ``agentcore_gateway`` tool type instead, with ``outboundAuth.oauth`` configured on the Gateway
     - Topology C. The OIDC flow can't run from inside ``remote_mcp``.
   * - **None**
     - No ``Authorization`` header
     - Dev / testing only. Do not deploy without auth.

Secrets Manager — where Zscaler credentials live
------------------------------------------------

By default this script does **not** put ``ZSCALER_CLIENT_SECRET`` in the ECS task definition as plaintext env vars. The five-key credential bundle goes to AWS Secrets Manager and the container fetches it at boot.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Mode
     - How to activate
     - Lifecycle
   * - **Default — script-managed secret**
     - Leave ``ZSCALER_SECRET_NAME`` unset in ``.env``. The script creates ``zscaler-mcp-harness/credentials`` and seeds it from your ``ZSCALER_*`` ``.env`` values.
     - ``destroy`` schedules deletion with a 7-day recovery window. Use ``--force-secret-delete`` to skip the window.
   * - **Bring-your-own secret**
     - Set ``ZSCALER_SECRET_NAME=<arn-or-name>`` in ``.env``, pointing at a pre-existing secret managed by Terraform / CloudFormation / another team.
     - The script verifies the secret exists, scopes the IAM policy to its ARN, but **never overwrites the value or deletes the secret** — even on ``destroy``.
   * - **Plaintext opt-out** (dev/debug only)
     - Pass ``--no-secrets-manager`` to ``deploy``.
     - Restores the legacy behaviour where the 5 credential keys go straight into the ECS task definition. **Production deploys should never use this.**

Troubleshooting (highlights)
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Symptom
     - Cause / Fix
   * - **Harness playground** returns ``Failed to start MCP client: ... unhandled errors in a TaskGroup``
     - Harness execution role is missing one of the AWS-mandated grants — most commonly ``ecr-public:GetAuthorizationToken`` + ``sts:GetServiceBearerToken``. ``destroy --keep-ecs`` and ``deploy`` again — the script now mirrors the full AWS-published harness execution role policy.
   * - ``runtimeClientError: Failed to load tool 'zscaler' (type=remote_mcp): … not authorized to perform: bedrock-agentcore:GetResourceApiKey``
     - AgentCore Identity does multiple distinct IAM authz checks per ``GetResourceApiKey`` / ``GetResourceOauth2Token`` call — and every one of them must independently pass. **IAM-matching gotcha**: IAM ARN matching is exact (no prefix matching). ``destroy --keep-ecs && deploy`` rewrites the policy with all five required resource ARNs.
   * - ``botocore.exceptions.NoCredentialsError``
     - No AWS creds resolved. ``aws configure``, set ``AWS_PROFILE``, or export ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``.
   * - ``EndpointConnectionError: bedrock-agentcore-control.<region>.amazonaws.com``
     - Harness preview not available in that region. Pick a region from the AWS preview list. As of writing, ``us-east-1`` is the safest bet.
   * - ``ValidationException: harnessName … must satisfy regular expression pattern: [a-zA-Z][a-zA-Z0-9_]{0,39}``
     - Invalid characters in ``--harness-name`` — most commonly hyphens. Use letters, digits, and **underscores only**.
   * - First ``POST /mcp`` in CloudWatch returns ``421 Misdirected Request`` with ``Invalid Host header``
     - FastMCP's DNS-rebinding guard rejects every request whose ``Host`` header isn't in ``ZSCALER_MCP_ALLOWED_HOSTS``. The script **merges** the discovered FQDN into the container's allowlist on every deploy.
   * - ``exec /usr/local/bin/python: exec format error`` in ECS task logs
     - The image at ``ZSCALER_MCP_IMAGE_URI`` is single-arch ARM64 (what ``docker build`` defaults to on Apple Silicon), while ECS Fargate Express runs AMD64. Rebuild with ``make docker-build-multiarch IMAGE=<your-ecr-uri>:<tag> PLATFORMS=linux/amd64``.

The full Harness troubleshooting matrix lives in `integrations/aws/harness/README.md <https://github.com/zscaler/zscaler-mcp-server/blob/master/integrations/aws/harness/README.md>`__.

Where to go next
----------------

- :doc:`amazon-bedrock-agentcore` — the AgentCore Runtime deployment path (the URL we co-deploy from here, or the alternative if you don't need Harness at all).
- :doc:`strands-agentcore` — local terminal client for the AgentCore Runtime path; the equivalent for the Harness path is the ``invoke`` subcommand of the Harness script.
