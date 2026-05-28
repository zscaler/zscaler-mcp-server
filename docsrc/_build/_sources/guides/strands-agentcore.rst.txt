.. _guide-strands-agentcore:

Strands Agent client for AgentCore Runtime
==========================================

An interactive CLI chat client that connects a **local Strands agent** (reasoning on Amazon Bedrock) to a Zscaler MCP Server **deployed on Amazon Bedrock AgentCore Runtime**. Every ``InvokeAgentRuntime`` call is signed locally with SigV4 from the host's AWS credentials.

The client is the companion to ``aws_mcp_operations.py``: that script provisions the runtime, this script talks to it.

.. code-block:: text

   1. python aws_mcp_operations.py deploy        -- provision the runtime
   2. python strands_agent_chat.py               -- chat against it

When to use this
----------------

Use the Strands chat client when you want to:

- Drive the deployed AgentCore Runtime from a local terminal without depending on the Bedrock Sandbox playground (no UI session limits, full control over headers).
- Validate end-to-end behaviour of a freshly deployed runtime — tool discovery, tool execution, and a real Bedrock model reasoning over the responses.
- Iterate on prompts and tool selection against the deployed runtime without leaving the shell.

Skip it if you already have a working integration (Claude Desktop with ``mcp-remote``, Cursor, a Foundry/Strands deployment on AWS itself, a Lambda caller, etc.) — those will keep working unchanged. This client is purely a local driver.

Architecture
------------

.. code-block:: text

     Local Strands agent (this script)
               │
               │ 1. boto3.Session().get_credentials()
               │
               │ 2. JSON-RPC body  +  SigV4 sign
               │
               ▼
     bedrock-agentcore:InvokeAgentRuntime  (HTTPS, region-scoped)
               │
               │   Headers:
               │     Authorization: AWS4-HMAC-SHA256 ...
               │     X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: <bedrock-id>
               │     Mcp-Session-Id: <mcp-id>  (after handshake)
               │
               ▼
     AgentCore Runtime container
               │
               │   Standard MCP streamable-http
               │
               ▼
     zscaler_mcp.server.main  --transport streamable-http
               │
               ▼
     Zscaler OneAPI  (creds from Secrets Manager)

Two distinct session identifiers travel on every call and they are **not** interchangeable:

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Header
     - Issued by
     - Purpose
   * - ``X-Amzn-Bedrock-AgentCore-Runtime-Session-Id``
     - the client (you)
     - Bedrock-level container affinity. Pins all requests in a chat to the same runtime instance so MCP server state survives across calls.
   * - ``Mcp-Session-Id``
     - the MCP server
     - MCP transport-level session id. Returned by the server in the ``initialize`` response, must be echoed on every subsequent JSON-RPC call.

Prerequisites
-------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Requirement
     - Notes
   * - **A deployed AgentCore Runtime**
     - Provisioned via ``aws_mcp_operations.py deploy`` or the CloudFormation root template. The script auto-discovers it from ``.aws-deploy-state.json`` if you run from ``integrations/aws/bedrock-agentcore/``.
   * - **AWS credentials**
     - Via ``aws configure``, ``AWS_PROFILE``, or env vars. The role/user needs ``bedrock-agentcore:InvokeAgentRuntime`` on the runtime ARN and ``bedrock:InvokeModelWithResponseStream`` / ``bedrock:Converse`` / ``bedrock:ConverseStream`` on the reasoning model.
   * - **Bedrock model access**
     - Enable the model you intend to use in the Bedrock console (Model access → Manage). Anthropic models additionally require a one-time **use-case form** to be submitted in the same console.
   * - **Python 3.10+**
     - The script is pure-Python with three runtime deps.

Install
-------

A co-located requirements file ships with the integration:

.. code-block:: bash

   cd integrations/aws/bedrock-agentcore
   uv venv .strands-venv --python 3.11
   source .strands-venv/bin/activate
   uv pip install -r requirements.txt

``requirements.txt`` pins exactly what the client needs:

.. code-block:: text

   boto3>=1.40.0
   strands-agents>=1.40.0
   httpx>=0.27.0

Both ``.strands-venv/`` and the local state file are listed in ``integrations/aws/bedrock-agentcore/.gitignore``.

Quick start
-----------

.. code-block:: bash

   cd integrations/aws/bedrock-agentcore
   source .strands-venv/bin/activate
   python strands_agent_chat.py

The script walks you through three steps:

1. **Pick the AgentCore deployment.** If ``.aws-deploy-state.json`` is present it auto-discovers the runtime ARN + region and asks for confirmation; otherwise it prompts.
2. **Pick a Bedrock reasoning model.** A curated list is shown.
3. **Pick which tools to load.** The runtime exposes 200+ tools; Bedrock Converse caps the ``toolConfig.tools`` array around 100 and even 30+ degrades agent quality. A small set of curated regex presets is shown.

After the picks, the agent prints a session banner and drops you into the chat loop.

Authentication
--------------

The client uses **only your local AWS credentials**. There is no static token, no MCP-side auth header, no OAuth flow.

- ``boto3.Session().get_credentials()`` resolves credentials from the default chain (env vars → shared config → IMDS/SSO).
- Every JSON-RPC POST to ``bedrock-agentcore.<region>.amazonaws.com/runtimes/<arn>/invocations`` is signed with SigV4 using those credentials.
- The runtime itself, when deployed with ``McpAuthMode=none``, trusts the AgentCore wrapper for AuthN.

MCP transport: the handshake
----------------------------

Starting with image ``v0.12.x-bedrock``, the AgentCore Runtime speaks **vanilla MCP streamable-http**. A session handshake is mandatory before any ``tools/list`` or ``tools/call``:

.. list-table::
   :header-rows: 1
   :widths: 10 30 60

   * - Step
     - Method
     - Notes
   * - 1
     - ``POST initialize``
     - Body carries ``protocolVersion`` (the client advertises ``2025-11-25``), empty ``capabilities``, and ``clientInfo``. The server replies with an ``Mcp-Session-Id`` response header — keep it.
   * - 2
     - ``POST notifications/initialized``
     - A JSON-RPC notification (no ``id``, no expected result). Server returns HTTP 202.
   * - 3
     - All subsequent calls
     - ``tools/list``, ``tools/call``, ``tools/get``, etc. — every one carries the ``Mcp-Session-Id`` header captured in step 1.

The client falls back gracefully: if ``initialize`` doesn't return an ``Mcp-Session-Id`` header, it concludes the runtime is the legacy Genesis-wrapped image and runs session-less.

Bedrock model catalogue
-----------------------

The client ships a small curated catalogue. Pick by number on first run; pin via ``--model`` after that.

.. list-table::
   :header-rows: 1
   :widths: 5 30 15 50

   * - #
     - Model
     - Region prefix
     - Notes
   * - 1
     - **Claude Sonnet 4.6** *(recommended)*
     - ``us.``
     - Mid-tier flagship. 1M context, strong tool use. **Requires Anthropic use-case form.**
   * - 2
     - **Claude Opus 4.7** *(recommended)*
     - ``us.``
     - Top-tier flagship. 1M context, best for agentic / multi-tool reasoning. **Requires Anthropic use-case form.**
   * - 3
     - Claude Opus 4.6
     - ``us.``
     - Previous Opus flagship. Cheaper than 4.7.
   * - 4
     - Amazon Nova Pro
     - ``us.``
     - Amazon-hosted — **no third-party access form needed**. Best for verifying wiring end-to-end.
   * - 5
     - Llama 3.3 70B Instruct
     - ``us.``
     - Meta open-weights. Tool-use support varies by Strands version.

Tool filter presets
-------------------

Bedrock Converse caps ``toolConfig.tools`` at roughly 100 entries; even at 30+ tools the LLM's reasoning degrades visibly. The client requires you to pick a filter so the loaded set fits.

.. list-table::
   :header-rows: 1
   :widths: 5 25 35 35

   * - #
     - Preset
     - Regex
     - Roughly
   * - 1
     - **Discovery**
     - ``^(zscaler_check_connectivity|zscaler_get_available_services|zscaler_search_tools|zscaler_list_toolsets)$``
     - 4 tools — meta/catalog only.
   * - 2
     - **ZPA read-only**
     - ``^zpa_(list|get)_.*$``
     - ~25 tools — segment / app / connector / policy listing.
   * - 3
     - **ZIA read-only**
     - ``^zia_(list|get)_.*$``
     - ~65 tools — rules / locations / users / admins read paths.
   * - 4
     - **ZDX read-only**
     - ``^zdx_(list|get).*$``
     - ~27 tools — user experience analytics + deep-trace readout.
   * - 5
     - **Policy investigation**
     - hand-picked cross-product set
     - ~30 tools — segment groups, app segments, server groups, access rules, FW/URL/SSL rules, ZDX devices/geo/apps.
   * - 6
     - **Custom regex**
     - (you supply)
     - Anything matching the pattern is loaded.
   * - 7
     - **All tools**
     - ``.*``
     - Loads everything — **expect Bedrock errors** beyond the tool-count limit. Useful only for sanity checks.

Pin a preset non-interactively with ``--tool-filter '<regex>'``.

Chat commands
-------------

These work at any ``You:`` prompt:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - Description
   * - ``help``
     - Show available commands + a few example prompts.
   * - ``status``
     - Print runtime ARN, region, model, tools loaded, session duration, message count, token totals.
   * - ``tools``
     - List the names + first-line descriptions of all currently-loaded tools.
   * - ``clear``
     - Clear the terminal screen.
   * - ``reset``
     - Reset the conversation context (clears chat history, token counters, message count).
   * - ``quit`` / ``exit`` / ``q``
     - End the chat session and print the summary.

Non-interactive (CLI flags)
---------------------------

Every interactive prompt has a flag or env var override so the script can be driven from scripts and CI.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Flag
     - Env var
     - Effect
   * - ``--runtime-arn <arn>``
     - ``AGENTCORE_RUNTIME_ARN``
     - Skip the deployment-picker, use this ARN.
   * - ``--region <name>``
     - ``AWS_REGION``
     - Skip the region-picker, use this region.
   * - ``--model <id>``
     - ``BEDROCK_MODEL_ID``
     - Skip the model-picker, use this Bedrock model id (e.g. ``us.anthropic.claude-sonnet-4-6``).
   * - ``--tool-filter <regex>``
     - —
     - Skip the preset-picker, use this regex.
   * - ``--list-tools``
     - —
     - Print the runtime's tools and exit. Pure smoke test — no LLM is touched.
   * - ``--no-banner``
     - —
     - Skip the ASCII logo (useful in CI / logs).

Example: fully non-interactive smoke test pinning everything.

.. code-block:: bash

   python strands_agent_chat.py \
     --runtime-arn arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/zscalermcp-xxx \
     --region us-east-1 \
     --model us.amazon.nova-pro-v1:0 \
     --tool-filter '^zpa_list_segment_groups$' \
     --no-banner

Smoke test
----------

The fastest way to verify a fresh deployment is the ``--list-tools`` path. It exercises SigV4 signing, AgentCore reach, MCP handshake, and ``tools/list`` — **without** consuming a Bedrock model invocation.

.. code-block:: bash

   python strands_agent_chat.py --list-tools --no-banner

A healthy output looks like:

.. code-block:: text

   [INFO]  Endpoint:   https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/...
   [INFO]  Session ID: strands-chat-<uuid>
   [OK]    MCP session established (id=01HXYZ...…)
   [OK]    Discovered 205 tools.

Where to go next
----------------

- :doc:`amazon-bedrock-agentcore` — full deployment guide for the AgentCore Runtime itself.
- :doc:`troubleshooting` — broader troubleshooting across the AWS integration.
- `strands_agent_chat.py <https://github.com/zscaler/zscaler-mcp-server/blob/master/integrations/aws/bedrock-agentcore/strands_agent_chat.py>`__ — the client source, single file, no external runtime config beyond the venv.
