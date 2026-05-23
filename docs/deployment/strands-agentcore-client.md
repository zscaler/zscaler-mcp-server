# Strands Agent client for AgentCore Runtime

An interactive CLI chat client that connects a **local Strands agent** (reasoning on Amazon Bedrock) to a Zscaler MCP Server **deployed on Amazon Bedrock AgentCore Runtime**. Every `InvokeAgentRuntime` call is signed locally with SigV4 from the host's AWS credentials.

The client is the companion to `aws_mcp_operations.py`: that script provisions the runtime, this script talks to it.

```text
  1. python aws_mcp_operations.py deploy        -- provision the runtime
  2. python strands_agent_chat.py               -- chat against it
```

## Table of contents

- [When to use this](#when-to-use-this)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Install](#install)
- [Quick start](#quick-start)
- [Authentication](#authentication)
- [MCP transport: the handshake](#mcp-transport-the-handshake)
- [Bedrock model catalogue](#bedrock-model-catalogue)
- [Tool filter presets](#tool-filter-presets)
- [Interactive flow](#interactive-flow)
- [Chat commands](#chat-commands)
- [Non-interactive (CLI flags)](#non-interactive-cli-flags)
- [Smoke test](#smoke-test)
- [Troubleshooting](#troubleshooting)
- [Where to go next](#where-to-go-next)

---

## When to use this

Use the Strands chat client when you want to:

- Drive the deployed AgentCore Runtime from a local terminal without depending on the Bedrock Sandbox playground (no UI session limits, full control over headers).
- Validate end-to-end behaviour of a freshly deployed runtime — tool discovery, tool execution, and a real Bedrock model reasoning over the responses.
- Iterate on prompts and tool selection against the deployed runtime without leaving the shell.

Skip it if you already have a working integration (Claude Desktop with `mcp-remote`, Cursor, a Foundry/Strands deployment on AWS itself, a Lambda caller, etc.) — those will keep working unchanged. This client is purely a local driver.

---

## Architecture

```text
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
            │   (no Genesis envelope on v0.12+)
            │
            ▼
  zscaler_mcp.server.main  --transport streamable-http
            │
            ▼
  Zscaler OneAPI  (creds from Secrets Manager)
```

Two distinct session identifiers travel on every call and they are **not** interchangeable:

| Header | Issued by | Purpose |
|---|---|---|
| `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` | the client (you) | Bedrock-level container affinity. Pins all requests in a chat to the same runtime instance so MCP server state survives across calls. |
| `Mcp-Session-Id` | the MCP server | MCP transport-level session id. Returned by the server in the `initialize` response, must be echoed on every subsequent JSON-RPC call. |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **A deployed AgentCore Runtime** | Provisioned via `aws_mcp_operations.py deploy` or the CloudFormation root template. The script auto-discovers it from `.aws-deploy-state.json` if you run from `integrations/aws/bedrock-agentcore/`. |
| **AWS credentials** | Via `aws configure`, `AWS_PROFILE`, or `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. The role/user needs `bedrock-agentcore:InvokeAgentRuntime` on the runtime ARN and `bedrock:InvokeModelWithResponseStream` / `bedrock:Converse` / `bedrock:ConverseStream` on the reasoning model. |
| **Bedrock model access** | Enable the model you intend to use in the Bedrock console (Model access → Manage). Anthropic models additionally require a one-time **use-case form** to be submitted in the same console. Without it you'll see `ResourceNotFoundException: Model use case details have not been submitted`. |
| **Python 3.10+** | The script is pure-Python with three runtime deps (see [Install](#install)). |

---

## Install

A co-located requirements file ships with the integration:

```bash
cd integrations/aws/bedrock-agentcore
uv venv .strands-venv --python 3.11
source .strands-venv/bin/activate
uv pip install -r requirements.txt
```

`requirements.txt` pins exactly what the client needs:

```text
boto3>=1.40.0
strands-agents>=1.40.0
httpx>=0.27.0
```

Both `.strands-venv/` and the local state file are listed in `integrations/aws/bedrock-agentcore/.gitignore`.

---

## Quick start

```bash
cd integrations/aws/bedrock-agentcore
source .strands-venv/bin/activate
python strands_agent_chat.py
```

The script walks you through three steps:

1. **Pick the AgentCore deployment.** If `.aws-deploy-state.json` is present it auto-discovers the runtime ARN + region and asks for confirmation; otherwise it prompts.
2. **Pick a Bedrock reasoning model.** A curated list is shown — see [Bedrock model catalogue](#bedrock-model-catalogue).
3. **Pick which tools to load.** The runtime exposes 200+ tools; Bedrock Converse caps the `toolConfig.tools` array around 100 and even 30+ degrades agent quality. A small set of curated regex presets is shown — see [Tool filter presets](#tool-filter-presets).

After the picks, the agent prints a session banner and drops you into the chat loop.

---

## Authentication

The client uses **only your local AWS credentials**. There is no static token, no MCP-side auth header, no OAuth flow.

- `boto3.Session().get_credentials()` resolves credentials from the default chain (env vars → shared config → IMDS/SSO).
- Every JSON-RPC POST to `bedrock-agentcore.<region>.amazonaws.com/runtimes/<arn>/invocations` is signed with SigV4 using those credentials.
- The runtime itself, when deployed with `McpAuthMode=none` (the default for the CloudFormation flow), trusts the AgentCore wrapper for AuthN. If `McpAuthMode=zscaler` was selected at deploy time, the runtime additionally validates `X-Zscaler-Client-ID` / `X-Zscaler-Client-Secret` headers — but in normal use those are injected by the deployment (Secrets Manager), not by the client.

In short: if your `aws sts get-caller-identity` works and the calling principal has `bedrock-agentcore:InvokeAgentRuntime` on the runtime ARN, the chat will connect.

---

## MCP transport: the handshake

Starting with image `v0.12.x-bedrock`, the AgentCore Runtime speaks **vanilla MCP streamable-http** — there is no `web_server.py` Genesis-style NDJSON wrapper any more. That means a session handshake is mandatory before any `tools/list` or `tools/call`:

| Step | Method | Notes |
|---|---|---|
| 1 | `POST initialize` | Body carries `protocolVersion` (the client advertises `2025-11-25`), empty `capabilities`, and `clientInfo`. The server replies with an `Mcp-Session-Id` response header — keep it. |
| 2 | `POST notifications/initialized` | A JSON-RPC notification (no `id`, no expected result). Server returns HTTP 202. |
| 3 | All subsequent calls | `tools/list`, `tools/call`, `tools/get`, etc. — every one carries the `Mcp-Session-Id` header captured in step 1. |

The client falls back gracefully: if `initialize` doesn't return an `Mcp-Session-Id` header, it concludes the runtime is the legacy Genesis-wrapped image and runs session-less. So the same script works against `v0.10.x` and `v0.12.x+` images without flags.

If you skip the handshake, the runtime returns a wrapped JSON-RPC error:

```text
[ERROR] tools/list failed: MCP error from tools/list:
        {'code': -32010, 'message': 'Received error (400) from runtime.
         Please check your CloudWatch logs for more information.'}
```

That `-32010` from `bedrock-agentcore` is the proxy mapping for "the underlying MCP server rejected the request" — typically the missing session.

---

## Bedrock model catalogue

The client ships a small curated catalogue. Pick by number on first run; pin via `--model` after that.

| # | Model | Region prefix | Notes |
|---|---|---|---|
| 1 | **Claude Sonnet 4.6** *(recommended)* | `us.` | Mid-tier flagship. 1M context, strong tool use. **Requires Anthropic use-case form.** |
| 2 | **Claude Opus 4.7** *(recommended)* | `us.` | Top-tier flagship. 1M context, best for agentic / multi-tool reasoning. **Requires Anthropic use-case form.** |
| 3 | Claude Opus 4.6 | `us.` | Previous Opus flagship. Cheaper than 4.7. **Requires Anthropic use-case form.** |
| 4 | Amazon Nova Pro | `us.` | Amazon-hosted — **no third-party access form needed**. Best for verifying wiring end-to-end. |
| 5 | Llama 3.3 70B Instruct | `us.` | Meta open-weights. Tool-use support varies by Strands version. |

If a model isn't enabled in your account, Bedrock returns `AccessDeniedException` or `ResourceNotFoundException` on first invoke. Open the Bedrock console → **Model access** → enable the model. Anthropic models additionally need the **Anthropic use-case** form filled in once per account (under the same Model access view).

---

## Tool filter presets

Bedrock Converse caps `toolConfig.tools` at roughly 100 entries; even at 30+ tools the LLM's reasoning degrades visibly. The client requires you to pick a filter so the loaded set fits.

| # | Preset | Regex | Roughly |
|---|---|---|---|
| 1 | **Discovery** | `^(zscaler_check_connectivity\|zscaler_get_available_services\|zscaler_search_tools\|zscaler_list_toolsets)$` | 4 tools — meta/catalog only. |
| 2 | **ZPA read-only** | `^zpa_(list\|get)_.*$` | ~25 tools — segment / app / connector / policy listing. |
| 3 | **ZIA read-only** | `^zia_(list\|get)_.*$` | ~65 tools — rules / locations / users / admins read paths. |
| 4 | **ZDX read-only** | `^zdx_(list\|get).*$` | ~27 tools — user experience analytics + deep-trace readout. |
| 5 | **Policy investigation** | hand-picked cross-product set | ~30 tools — segment groups, app segments, server groups, access rules, FW/URL/SSL rules, ZDX devices/geo/apps. |
| 6 | **Custom regex** | (you supply) | Anything matching the pattern is loaded. |
| 7 | **All tools** | `.*` | Loads everything — **expect Bedrock errors** beyond the tool-count limit. Useful only for sanity checks. |

Pin a preset non-interactively with `--tool-filter '<regex>'`.

---

## Interactive flow

A successful startup looks like this (truncated, colours stripped):

```text
  ╭─────────────────────────────────────────────╮
  │                                             │
  │   ZSCALER                                   │
  │                                             │
  ╰─────────────────────────────────────────────╯
  Strands Agent  →  Bedrock AgentCore Runtime  →  Zscaler

── Step 1 of 3 — Pick the AgentCore deployment ──
[INFO]  Found local state file: .aws-deploy-state.json
[INFO]  Region:     us-east-1
[INFO]  Stack:      zscaler-mcp-agentcore
[INFO]  RuntimeArn: arn:aws:bedrock-agentcore:us-east-1:...:runtime/zscalermcp-...
Use the deployment from the state file? [Y/n]: Y
[INFO]  Endpoint:   https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/...
[INFO]  Session ID: strands-chat-<uuid>

⠋ Initializing MCP session   (0s)
[OK]    MCP session established (id=01HXYZ...…)

⠋ Discovering tools   (1s)
[OK]    Discovered 205 tools.

── Step 2 of 3 — Pick a Bedrock reasoning model ──
  1. Claude Sonnet 4.6                 Mid-tier flagship. 1M context, strong tool use. ...
  2. Claude Opus 4.7                   Top-tier flagship. 1M context, best for agentic ...
  ...
Model [1]: 1

── Step 3 of 3 — Pick which tools to load ──
  1. Discovery (4 tools)               Service catalog + tool search — great starting point.
  2. ZPA read-only (~25 tools)         Segment/app/connector/policy listing for ZPA.
  ...
Toolset [1]: 2

[OK]    Strands agent ready with 25 tools (model=us.anthropic.claude-sonnet-4-6).
============================================================
  Zscaler MCP Agent — Bedrock + AgentCore
  Runtime:    arn:aws:bedrock-agentcore:...
  Region:     us-east-1
  Model:      us.anthropic.claude-sonnet-4-6
  Tools:      25 loaded  (ZPA read-only (~25 tools))
  Type 'help' for commands.
============================================================

You: list all zpa segment groups
```

Every reply is followed by an inline stats line:

```text
[15.9s | 97,487 tokens | in:95,656 out:1,831]
```

On clean exit (Ctrl+D or `quit`) the script prints a session summary: duration, message count, cumulative tokens.

---

## Chat commands

These work at any `You:` prompt:

| Command | Description |
|---|---|
| `help` | Show available commands + a few example prompts. |
| `status` | Print runtime ARN, region, model, tools loaded, session duration, message count, token totals. |
| `tools` | List the names + first-line descriptions of all currently-loaded tools. |
| `clear` | Clear the terminal screen. |
| `reset` | Reset the conversation context (clears chat history, token counters, message count). |
| `quit` / `exit` / `q` | End the chat session and print the summary. |

---

## Non-interactive (CLI flags)

Every interactive prompt has a flag or env var override so the script can be driven from scripts and CI.

| Flag | Env var | Effect |
|---|---|---|
| `--runtime-arn <arn>` | `AGENTCORE_RUNTIME_ARN` | Skip the deployment-picker, use this ARN. |
| `--region <name>` | `AWS_REGION` | Skip the region-picker, use this region. |
| `--model <id>` | `BEDROCK_MODEL_ID` | Skip the model-picker, use this Bedrock model id (e.g. `us.anthropic.claude-sonnet-4-6`). |
| `--tool-filter <regex>` | — | Skip the preset-picker, use this regex. |
| `--list-tools` | — | Print the runtime's tools and exit. Pure smoke test — no LLM is touched. |
| `--no-banner` | — | Skip the ASCII logo (useful in CI / logs). |

Example: fully non-interactive smoke test pinning everything.

```bash
python strands_agent_chat.py \
  --runtime-arn arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/zscalermcp-xxx \
  --region us-east-1 \
  --model us.amazon.nova-pro-v1:0 \
  --tool-filter '^zpa_list_segment_groups$' \
  --no-banner
```

---

## Smoke test

The fastest way to verify a fresh deployment is the `--list-tools` path. It exercises SigV4 signing, AgentCore reach, MCP handshake, and `tools/list` — **without** consuming a Bedrock model invocation.

```bash
python strands_agent_chat.py --list-tools --no-banner
```

A healthy output looks like:

```text
[INFO]  Endpoint:   https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/...
[INFO]  Session ID: strands-chat-<uuid>
[OK]    MCP session established (id=01HXYZ...…)
[OK]    Discovered 205 tools.
  - easm_get_active_subdomains              List active subdomains for a given domain
  - easm_get_assets                         List EASM-managed assets
  - ...
  ... and 145 more.
```

Once that passes, the LLM-driven chat is the next step.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `[ERROR] tools/list failed: MCP error from tools/list: {'code': -32010, 'message': 'Received error (400) from runtime.'}` | Skipping the MCP `initialize` handshake against a `v0.12.x+` runtime. | The client now handles this automatically. If you see it again, you're running an older copy of the script — pull the latest from `integrations/aws/bedrock-agentcore/strands_agent_chat.py` and verify `mcp_initialize` is present. |
| `No AWS credentials found.` | Local `boto3` couldn't resolve creds. | Run `aws configure`, set `AWS_PROFILE`, or export `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. Verify with `aws sts get-caller-identity`. |
| `botocore.exceptions.ClientError: An error occurred (AccessDeniedException) when calling the InvokeAgentRuntime operation` | IAM principal lacks `bedrock-agentcore:InvokeAgentRuntime` on the runtime ARN. | Attach a policy granting that action on `arn:aws:bedrock-agentcore:<region>:<acct>:runtime/<id>`. |
| `ResourceNotFoundException: Model use case details have not been submitted for this account.` | Anthropic models require a one-time per-account use-case attestation. | Bedrock console → **Model access** → **Manage** → Anthropic → fill the use-case form. Wait ~15 min and retry. |
| `AccessDeniedException` on the first model invoke (non-Anthropic) | The model isn't enabled in your account/region. | Bedrock console → **Model access** → enable the model in the target region. Region prefixes (`us.`, `eu.`) matter. |
| `Input should be a valid string` from a `zpa_list_*` tool | Older runtime image where `page` / `page_size` were typed as `Optional[str]`; current Bedrock models emit `int` for those args. | Already fixed at the source (see `zscaler_mcp/tools/zpa/*.py` — `Annotated[Optional[int], Field(ge=1, ...)]`). Rebuild the image and redeploy the runtime. |
| `Strands is not installed.` | `requirements.txt` not installed in the active venv. | `uv pip install -r integrations/aws/bedrock-agentcore/requirements.txt` (or `pip install -r ...`) and re-run. |
| `Tool filter '...' matched 0 of N tools.` | The regex didn't match any tool name in the runtime's `tools/list`. | Re-run with `--list-tools` to see the actual catalogue, then refine the regex. |
| Runtime ARN in state file doesn't match the live runtime | A redeploy ran without updating `.aws-deploy-state.json`. | The next `aws_mcp_operations.py deploy` will overwrite the state file. Until then, answer **n** to the "Use the deployment from the state file?" prompt and paste the live ARN. |
| Want to see exactly what's on the wire | — | Set `DEBUG_MCP_WIRE=1` before running. The first 2 kB of every response body is dumped to stdout. |

---

## Where to go next

- [`amazon_bedrock_agentcore.md`](amazon_bedrock_agentcore.md) — full deployment guide (CloudFormation + manual AWS CLI paths) for the AgentCore Runtime itself.
- [`../guides/TROUBLESHOOTING.md`](../guides/TROUBLESHOOTING.md) — broader troubleshooting across the AWS integration.
- [`../../integrations/aws/bedrock-agentcore/strands_agent_chat.py`](../../integrations/aws/bedrock-agentcore/strands_agent_chat.py) — the client source, ~1100 lines, single file, no external runtime config beyond the venv.
- [`../../integrations/aws/bedrock-agentcore/aws_mcp_operations.py`](../../integrations/aws/bedrock-agentcore/aws_mcp_operations.py) — companion deployment / lifecycle script.
