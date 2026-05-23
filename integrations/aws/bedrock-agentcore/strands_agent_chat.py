#!/usr/bin/env python3
"""Zscaler MCP Server on AgentCore Runtime — interactive Strands chat client.

Connects a local Strands agent (running on Amazon Bedrock for reasoning) to a
Zscaler MCP server deployed on Amazon Bedrock AgentCore Runtime, signing every
``InvokeAgentRuntime`` call with SigV4 from the host's AWS credentials.

Companion to ``aws_mcp_operations.py``:

    1. ``python aws_mcp_operations.py deploy``     — deploy the runtime
    2. ``python strands_agent_chat.py``            — chat against it

The script walks you through:

    * picking the deployment (auto-discovered from ``.aws-deploy-state.json``
      if present, otherwise prompted)
    * picking a Bedrock reasoning model from a curated list (or supplying
      your own model id)
    * picking the slice of Zscaler tools the agent should know about
      (the full catalog is 200+ tools, way past Bedrock's per-request
      tool limit — so a filter is required, with a small curated default
      tailored to common admin tasks)

then drops you into an interactive REPL with per-message stats, an animated
spinner, and an end-of-session summary.

Quick start::

    cd integrations/aws/bedrock-agentcore
    uv venv .strands-venv --python 3.11 && source .strands-venv/bin/activate
    uv pip install strands-agents boto3 httpx
    python strands_agent_chat.py

Authentication path::

    ~/.aws (or env) ── SigV4 ──> bedrock-agentcore:InvokeAgentRuntime
                                  │
                                  ▼
                          AgentCore Runtime container
                                  │   (vanilla MCP / streamable-http)
                                  ▼
                          zscaler_mcp.server.main
                                  │
                                  ▼
                          Zscaler OneAPI (Secrets Manager creds)

Pattern adapted from the AWS reference at
https://github.com/aws-samples/sample-mcp-proxy-agentcore-runtime — full
MCP streamable-http transport with SigV4 is overkill here; each Strands
tool wraps a single signed ``tools/call`` request, which is enough for
every tool the Zscaler MCP server exposes.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import re
import sys
import threading
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import boto3
    import httpx
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError as exc:
    sys.stderr.write(
        f"ERROR: missing dependency ({exc.name}).\n"
        "Install with: uv pip install strands-agents boto3 httpx\n"
    )
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────
# Branding — chunky Zscaler logo with truecolor gradient.
# Lifted verbatim from aws_mcp_operations.py so both scripts feel like
# parts of the same tool.
# ──────────────────────────────────────────────────────────────────────────

_ZSCALER_ART = [
    "███████╗███████╗ ██████╗ █████╗ ██╗     ███████╗██████╗ ",
    "╚══███╔╝██╔════╝██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗",
    "  ███╔╝ ███████╗██║     ███████║██║     █████╗  ██████╔╝",
    " ███╔╝  ╚════██║██║     ██╔══██║██║     ██╔══╝  ██╔══██╗",
    "███████╗███████║╚██████╗██║  ██║███████╗███████╗██║  ██║",
    "╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
]
_TAGLINE = "Strands Agent  →  Bedrock AgentCore Runtime  →  Zscaler"


def _supports_truecolor() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return True
    term = os.environ.get("TERM", "").lower()
    return "256color" in term or "kitty" in term or "iterm" in term


def _rgb(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m"


_RESET = "\x1b[0m"


def print_zscaler_logo() -> None:
    width = max(len(line) for line in _ZSCALER_ART)
    pad = 2
    inner = width + pad * 2

    if not _supports_truecolor():
        print()
        print(f"  +{'-' * inner}+")
        for line in _ZSCALER_ART:
            print(f"  |{' ' * pad}{line.ljust(width)}{' ' * pad}|")
        print(f"  +{'-' * inner}+")
        print(f"  {_TAGLINE}")
        print()
        return

    start = (0x55, 0xCC, 0xFF)
    end = (0x00, 0x3D, 0x99)
    border = _rgb(0x33, 0x55, 0x99)
    shadow_color = _rgb(0x00, 0x3D, 0x99)

    def gradient_line(text: str) -> str:
        out: list[str] = []
        last = None
        padded = text.ljust(width)
        for i, ch in enumerate(padded):
            if ch == " ":
                out.append(" ")
                continue
            t = i / max(width - 1, 1)
            r = int(start[0] + (end[0] - start[0]) * t)
            g = int(start[1] + (end[1] - start[1]) * t)
            b = int(start[2] + (end[2] - start[2]) * t)
            color = (r, g, b)
            if color != last:
                out.append(_rgb(*color))
                last = color
            out.append(ch)
        out.append(_RESET)
        return "".join(out)

    blank = " " * width
    print()
    print(f"  {border}╭{'─' * inner}╮{_RESET}")
    print(f"  {border}│{_RESET}{' ' * pad}{blank}{' ' * pad}{border}│{_RESET}")
    for line in _ZSCALER_ART:
        print(f"  {border}│{_RESET}{' ' * pad}{gradient_line(line)}{' ' * pad}{border}│{_RESET}")
    shadow = "░" * width
    print(f"  {border}│{_RESET}{' ' * pad}{shadow_color}{shadow}{_RESET}{' ' * pad}{border}│{_RESET}")
    print(f"  {border}│{_RESET}{' ' * pad}{blank}{' ' * pad}{border}│{_RESET}")
    print(f"  {border}╰{'─' * inner}╯{_RESET}")
    print(f"  {_TAGLINE}")
    print()


# ──────────────────────────────────────────────────────────────────────────
# ANSI colours
# ──────────────────────────────────────────────────────────────────────────

COLOURS = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
if COLOURS and platform.system() == "Windows":
    try:
        import ctypes  # noqa: WPS433

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        COLOURS = False

RED = "\033[0;31m" if COLOURS else ""
GREEN = "\033[0;32m" if COLOURS else ""
YELLOW = "\033[1;33m" if COLOURS else ""
BLUE = "\033[0;34m" if COLOURS else ""
CYAN = "\033[0;36m" if COLOURS else ""
SKY_BLUE = "\033[34;01m" if COLOURS else ""
BOLD = "\033[1m" if COLOURS else ""
DIM = "\033[2m" if COLOURS else ""
NC = "\033[0m" if COLOURS else ""


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{NC}  {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{NC}    {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def err(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}", file=sys.stderr)


def step(title: str) -> None:
    bar = "─" * max(0, 80 - len(title) - 5)
    print(f"\n{SKY_BLUE}── {BOLD}{title}{NC}{SKY_BLUE} {bar}{NC}")


# ──────────────────────────────────────────────────────────────────────────
# Spinner — animated braille frames + live elapsed timer
# ──────────────────────────────────────────────────────────────────────────


class Spinner:
    """Animated spinner for long-running operations.

    Mirrors integrations/azure/foundry_agent.py so the chat UX feels
    consistent across cloud-specific Zscaler MCP integrations.
    """

    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Thinking") -> None:
        self._message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time = 0.0

    def start(self) -> "Spinner":
        self._start_time = time.time()
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def _spin(self) -> None:
        idx = 0
        while not self._stop.is_set():
            elapsed = time.time() - self._start_time
            frame = self._FRAMES[idx % len(self._FRAMES)]
            sys.stdout.write(f"\r{CYAN}{frame}{NC} {self._message} {DIM}({elapsed:.0f}s){NC}   ")
            sys.stdout.flush()
            idx += 1
            self._stop.wait(0.08)

    def stop(self) -> float:
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()
        return time.time() - self._start_time


# ──────────────────────────────────────────────────────────────────────────
# AgentCore Runtime invocation
# ──────────────────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT_S = 120.0
DEFAULT_QUALIFIER = "DEFAULT"

# Latest MCP protocol version known to the bundled `mcp` SDK as of this
# writing. FastMCP servers downgrade automatically if the client speaks a
# newer version than they understand, so always advertising the latest is
# safe. Bump this when the SDK pins a newer version.
MCP_PROTOCOL_VERSION = "2025-11-25"


def build_endpoint(runtime_arn: str, region: str, qualifier: str = DEFAULT_QUALIFIER) -> str:
    """Return the data-plane invocation URL for an AgentCore Runtime ARN."""
    encoded = urllib.parse.quote(runtime_arn, safe="")
    return (
        f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/"
        f"{encoded}/invocations?qualifier={qualifier}"
    )


def send_mcp_request(
    endpoint: str,
    region: str,
    method: str,
    params: Optional[dict] = None,
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    session_id: Optional[str] = None,
    mcp_session_id: Optional[str] = None,
    notification: bool = False,
) -> dict:
    """Send a SigV4-signed JSON-RPC request to AgentCore Runtime.

    Two distinct session identifiers are in play and they are NOT
    interchangeable:

      * ``session_id`` (``X-Amzn-Bedrock-AgentCore-Runtime-Session-Id``)
        — Bedrock-level affinity header. Pins requests to the same
        container instance so MCP state survives across calls.
      * ``mcp_session_id`` (``Mcp-Session-Id``) — MCP transport-level
        session id. Issued by the server in the response to
        ``initialize`` and must be echoed on every subsequent request.

    The handler accepts three response framings in priority order so a
    single script works against both the current MCP streamable-http
    runtime and the older ``v0.10.x`` ``web_server.py``-wrapped image:

      1. NDJSON ``{"type":"data","data":{"result":{"result": <mcp result>}}}``
         (legacy Genesis envelope — only emitted by older images)
      2. SSE ``data: {…}``
      3. Plain JSON ``{…}``

    Pass ``notification=True`` for fire-and-forget JSON-RPC notifications
    (no ``id``, server returns HTTP 202 with no body).
    """
    creds = boto3.Session().get_credentials()
    if creds is None:
        raise RuntimeError(
            "No AWS credentials found. Configure via `aws configure`, "
            "AWS_PROFILE, or AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
        )

    rpc: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
    }
    if not notification:
        rpc["id"] = str(uuid.uuid4())
    body = json.dumps(rpc)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = session_id
    if mcp_session_id:
        headers["Mcp-Session-Id"] = mcp_session_id

    aws_req = AWSRequest(method="POST", url=endpoint, data=body, headers=headers)
    SigV4Auth(creds, "bedrock-agentcore", region).add_auth(aws_req)

    resp = httpx.post(endpoint, content=body, headers=dict(aws_req.headers), timeout=timeout)

    # Notifications have no response body; the spec says 202 No Content.
    # Some intermediaries normalise to 200 with empty body — accept either.
    if notification:
        if resp.status_code >= 400:
            resp.raise_for_status()
        return {}

    resp.raise_for_status()

    text = resp.text
    if os.getenv("DEBUG_MCP_WIRE"):
        info(f"--- raw response ({len(text)} bytes) ---")
        info(text[:2000])
        info("--- end raw response ---")

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            frame = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(frame, dict) and frame.get("type") == "data":
            inner = frame.get("data") or {}
            inner_result = inner.get("result") or {}
            if "error" in inner_result:
                raise RuntimeError(f"MCP error from {method}: {inner_result['error']}")
            if "result" in inner_result:
                return inner_result["result"]
            if isinstance(inner_result, dict):
                return inner_result

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("data:"):
            data_body = stripped[len("data:") :].strip()
            if not data_body:
                continue
            try:
                payload = json.loads(data_body)
            except json.JSONDecodeError:
                continue
            if "error" in payload:
                raise RuntimeError(f"MCP error from {method}: {payload['error']}")
            if "result" in payload:
                return payload["result"]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse runtime response. First 500 chars:\n{text[:500]}\n"
            f"(re-run with DEBUG_MCP_WIRE=1 for the full body.) {exc}"
        ) from None
    if "error" in payload:
        raise RuntimeError(f"MCP error from {method}: {payload['error']}")
    return payload.get("result", {})


def mcp_initialize(
    endpoint: str,
    region: str,
    *,
    runtime_session_id: str,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> Optional[str]:
    """Perform the MCP streamable-http handshake; return the MCP session id.

    Mandatory on the current MCP-native AgentCore image (``v0.12+``).
    The flow is:

      1. POST ``initialize`` — server returns an ``Mcp-Session-Id``
         response header that must be echoed on every subsequent call.
      2. POST ``notifications/initialized`` — fire-and-forget notification
         (server returns HTTP 202).

    Returns the session id, or ``None`` if the runtime is the legacy
    ``v0.10.x`` Genesis-wrapped image that doesn't speak the handshake
    (it returns the bare tool result for ``initialize`` and no session
    header). Callers then run "session-less" — which is what that image
    expected anyway.
    """
    creds = boto3.Session().get_credentials()
    if creds is None:
        raise RuntimeError("No AWS credentials found.")

    init_body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "zscaler-strands-chat",
                    "version": "0.1.0",
                },
            },
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": runtime_session_id,
    }
    req = AWSRequest(method="POST", url=endpoint, data=init_body, headers=headers)
    SigV4Auth(creds, "bedrock-agentcore", region).add_auth(req)
    resp = httpx.post(
        endpoint, content=init_body, headers=dict(req.headers), timeout=timeout
    )
    resp.raise_for_status()

    # Header casing varies across proxies; check both.
    mcp_session_id = resp.headers.get("mcp-session-id") or resp.headers.get(
        "Mcp-Session-Id"
    )
    if not mcp_session_id:
        # Legacy Genesis-wrapped image — no handshake required.
        return None

    notif_headers = dict(headers)
    notif_headers["Mcp-Session-Id"] = mcp_session_id
    notif_body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
    )
    nreq = AWSRequest(
        method="POST", url=endpoint, data=notif_body, headers=notif_headers
    )
    SigV4Auth(creds, "bedrock-agentcore", region).add_auth(nreq)
    nresp = httpx.post(
        endpoint, content=notif_body, headers=dict(nreq.headers), timeout=timeout
    )
    if nresp.status_code >= 400:
        raise RuntimeError(
            f"notifications/initialized returned HTTP {nresp.status_code}: "
            f"{nresp.text[:300]}"
        )
    return mcp_session_id


# ──────────────────────────────────────────────────────────────────────────
# Strands tool factory
# ──────────────────────────────────────────────────────────────────────────


def make_strands_tool(
    *,
    name: str,
    description: str,
    endpoint: str,
    region: str,
    session_id: str,
    mcp_session_id: Optional[str] = None,
) -> Callable[..., str]:
    """Wrap one remote MCP tool as a Strands ``@tool`` function.

    The Strands signature is intentionally ``**kwargs`` — the LLM relies on
    the tool description (which carries the MCP server's full docstring) to
    decide what arguments to pass. The kwargs are forwarded verbatim as
    ``tools/call`` arguments; the runtime's MCP server is responsible for
    validating them against the tool's advertised JSON schema.
    """
    from strands import tool

    safe_name = re.sub(r"[^A-Za-z0-9_]", "_", name)

    @tool(name=safe_name, description=description)
    def tool_fn(**kwargs: Any) -> str:
        try:
            result = send_mcp_request(
                endpoint,
                region,
                "tools/call",
                {"name": name, "arguments": kwargs},
                session_id=session_id,
                mcp_session_id=mcp_session_id,
            )
        except Exception as exc:
            return f"[tool call failed] {exc}"

        # MCP `tools/call` response shapes seen on this runtime:
        #   * spec:   {"content": [{"type":"text", "text":"..."}], "isError": false}
        #   * legacy Genesis double-wrap: a bare list of text strings
        # Normalize both to a plain joined string so the LLM sees consistent
        # tool output regardless of which framing the runtime emits.
        if isinstance(result, list):
            return "\n".join(
                item if isinstance(item, str) else json.dumps(item)
                for item in result
            )
        if isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list) and content:
                texts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        texts.append(item["text"])
                    else:
                        texts.append(json.dumps(item))
                return "\n".join(texts)
        return json.dumps(result)

    return tool_fn


# ──────────────────────────────────────────────────────────────────────────
# Deployment discovery — read .aws-deploy-state.json + CFN outputs
# ──────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / ".aws-deploy-state.json"


def load_deploy_state() -> dict[str, Any]:
    """Read the state file written by aws_mcp_operations.py (if it exists)."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def lookup_runtime_arn(session: boto3.Session, stack_name: str) -> Optional[str]:
    """Query CloudFormation for the ``RuntimeArn`` output of a stack.

    Returns ``None`` if the stack or output isn't present.
    """
    cfn = session.client("cloudformation")
    try:
        resp = cfn.describe_stacks(StackName=stack_name)
    except ClientError:
        return None
    stacks = resp.get("Stacks", [])
    if not stacks:
        return None
    for output in stacks[0].get("Outputs", []) or []:
        if output.get("OutputKey") == "RuntimeArn":
            return output.get("OutputValue")
    return None


# ──────────────────────────────────────────────────────────────────────────
# Model catalogue — curated Bedrock models that support tool use
# ──────────────────────────────────────────────────────────────────────────
# `us.`-prefixed model ids use the cross-region inference profile, which
# routes requests across US regions. This is the recommended way to call
# newer Anthropic models on Bedrock — without it you'll typically hit
# "model not available in <region>" errors.
#
# Models marked *requires Anthropic use-case form* need a one-time
# attestation in the Bedrock console (Model access → Anthropic) before
# they'll respond. The error you'll see otherwise:
#   "Model use case details have not been submitted for this account."

MODEL_CATALOGUE = [
    {
        "id": "us.anthropic.claude-sonnet-4-6",
        "name": "Claude Sonnet 4.6",
        "vendor": "Anthropic",
        "notes": "Mid-tier flagship. 1M context, strong tool use. Requires Anthropic use-case form.",
        "tags": ["recommended", "tool-use"],
    },
    {
        "id": "us.anthropic.claude-opus-4-7",
        "name": "Claude Opus 4.7",
        "vendor": "Anthropic",
        "notes": "Top-tier flagship. 1M context, best for agentic / multi-tool reasoning. Requires Anthropic use-case form.",
        "tags": ["recommended", "tool-use"],
    },
    {
        "id": "us.anthropic.claude-opus-4-6-v1",
        "name": "Claude Opus 4.6",
        "vendor": "Anthropic",
        "notes": "Previous Opus flagship. 1M context. Slightly cheaper than 4.7. Requires Anthropic use-case form.",
        "tags": ["tool-use"],
    },
    {
        "id": "us.amazon.nova-pro-v1:0",
        "name": "Amazon Nova Pro",
        "vendor": "Amazon",
        "notes": "Amazon-hosted — no third-party access form needed. Good for verifying wiring end-to-end.",
        "tags": ["tool-use", "no-form"],
    },
    {
        "id": "us.meta.llama3-3-70b-instruct-v1:0",
        "name": "Llama 3.3 70B Instruct",
        "vendor": "Meta",
        "notes": "Open-weights option. Tool-use support varies by Strands version.",
        "tags": ["tool-use"],
    },
]


# ──────────────────────────────────────────────────────────────────────────
# Curated tool filters — the full catalogue is too big for Bedrock
# ──────────────────────────────────────────────────────────────────────────
# Bedrock Converse caps the toolConfig.tools array (typical ceiling is
# ~100 entries) and even at 30+ tools the LLM context bloats badly.
# These pre-baked filters keep things tractable for common admin tasks.

TOOL_PRESETS = [
    {
        "id": "discovery",
        "label": "Discovery (4 tools)",
        "description": "Service catalog + tool search — great starting point.",
        "pattern": r"^(zscaler_check_connectivity|zscaler_get_available_services|zscaler_search_tools|zscaler_list_toolsets)$",
    },
    {
        "id": "zpa-readonly",
        "label": "ZPA read-only (~25 tools)",
        "description": "Segment/app/connector/policy listing for ZPA.",
        "pattern": r"^zpa_(list|get)_.*$",
    },
    {
        "id": "zia-readonly",
        "label": "ZIA read-only (~65 tools)",
        "description": "Rules/locations/users/admins read-only for ZIA.",
        "pattern": r"^zia_(list|get)_.*$",
    },
    {
        "id": "zdx-readonly",
        "label": "ZDX read-only (~27 tools)",
        "description": "User experience analytics + deep-trace readout.",
        "pattern": r"^zdx_(list|get).*$",
    },
    {
        "id": "policy-investigation",
        "label": "Policy investigation (mixed, ~30 tools)",
        "description": "Hand-picked tools for cross-product policy audits.",
        "pattern": (
            r"^(zscaler_get_available_services|"
            r"zpa_list_(segment_groups|application_segments|server_groups|access_policy_rules|app_connectors)|"
            r"zia_list_(locations|users|admins|cloud_firewall_rules|url_filtering_rules|ssl_inspection_rules)|"
            r"zdx_list_(devices|active_geo|applications))$"
        ),
    },
    {
        "id": "custom",
        "label": "Custom regex",
        "description": "Supply your own filter pattern.",
        "pattern": None,
    },
    {
        "id": "all",
        "label": "All tools (will hit Bedrock tool-count limit)",
        "description": "Loads every tool the runtime exposes. Expect failures.",
        "pattern": r".*",
    },
]


# ──────────────────────────────────────────────────────────────────────────
# Interactive prompts
# ──────────────────────────────────────────────────────────────────────────


def _input(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" {DIM}[{default}]{NC}" if default else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    return raw or (default or "")


def _input_choice(prompt: str, choices: list[str], default_idx: int = 0) -> int:
    """Render a numbered menu and return the chosen index."""
    for i, choice in enumerate(choices, start=1):
        marker = f"{GREEN}*{NC}" if i - 1 == default_idx else " "
        print(f"  {marker} {BOLD}{i:>2}{NC}. {choice}")
    while True:
        raw = input(f"\n{prompt} {DIM}[{default_idx + 1}]{NC}: ").strip()
        if not raw:
            return default_idx
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return idx
        warn(f"Pick a number between 1 and {len(choices)}.")


def _input_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        raw = input(f"{prompt}{suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        warn("Please answer 'y' or 'n'.")


def prompt_for_deployment() -> tuple[str, str]:
    """Discover or prompt for AgentCore runtime ARN + region."""
    step("Step 1 of 3 — Pick the AgentCore deployment")

    state = load_deploy_state()
    discovered_arn: Optional[str] = None
    discovered_region: Optional[str] = state.get("region")
    discovered_stack: Optional[str] = state.get("stack_name")

    if discovered_region and discovered_stack:
        info(f"Found local state file: {STATE_FILE.name}")
        info(f"  Region:     {discovered_region}")
        info(f"  Stack:      {discovered_stack}")
        try:
            sess = boto3.Session(region_name=discovered_region)
            discovered_arn = lookup_runtime_arn(sess, discovered_stack)
            if discovered_arn:
                info(f"  RuntimeArn: {discovered_arn}")
        except NoCredentialsError:
            warn("No AWS credentials available — can't query CFN. Provide ARN manually.")
        except Exception as exc:
            warn(f"Couldn't resolve RuntimeArn from CFN: {exc}")

    if discovered_arn and _input_yes_no(
        "\nUse the deployment from the state file?", default=True
    ):
        return discovered_arn, discovered_region  # type: ignore[return-value]

    info("Manual entry — paste the AgentCore Runtime ARN.")
    info("  (You can find it in the deploy summary, the CFN console, or:")
    info("   aws bedrock-agentcore-control list-agent-runtimes)")
    print()
    while True:
        arn = _input("Runtime ARN", default=discovered_arn).strip()
        if arn.startswith("arn:aws:bedrock-agentcore:") and ":runtime/" in arn:
            break
        warn("That doesn't look like a runtime ARN. Expected:\n"
             "  arn:aws:bedrock-agentcore:<region>:<account>:runtime/<name>-<hash>")

    inferred_region = arn.split(":")[3]
    region = _input("AWS region", default=inferred_region or discovered_region or "us-east-1")
    return arn, region


def prompt_for_model() -> str:
    step("Step 2 of 3 — Pick the reasoning model")

    labels = [
        f"{BOLD}{m['name']}{NC} {DIM}({m['vendor']}){NC}  — {m['notes']}\n"
        f"      {DIM}{m['id']}{NC}"
        for m in MODEL_CATALOGUE
    ]
    labels.append(f"{BOLD}Custom{NC}  — paste your own Bedrock model id")

    default_idx = next(
        (i for i, m in enumerate(MODEL_CATALOGUE) if "recommended" in m["tags"]),
        0,
    )
    idx = _input_choice("Model", labels, default_idx=default_idx)

    if idx == len(MODEL_CATALOGUE):
        return _input("Bedrock model id").strip()

    chosen = MODEL_CATALOGUE[idx]
    if "no-form" not in chosen["tags"] and chosen["vendor"] == "Anthropic":
        warn(
            "Anthropic models on Bedrock require a one-time use-case form "
            "(Bedrock console → Model access → Manage). If you see "
            "'Model use case details have not been submitted', fill the "
            "form and retry."
        )
    return chosen["id"]


def prompt_for_tool_filter(total_tools: int) -> tuple[str, str]:
    """Returns (regex_pattern, label_for_display)."""
    step("Step 3 of 3 — Pick which tools to load")

    info(
        f"The runtime exposes {total_tools} tools. Bedrock's Converse API "
        "caps tool count per request (~100), and even 30+ tools degrade "
        "agent quality. A focused preset is recommended."
    )
    print()

    labels = [f"{p['label']:36s} — {DIM}{p['description']}{NC}" for p in TOOL_PRESETS]
    idx = _input_choice("Toolset", labels, default_idx=0)
    chosen = TOOL_PRESETS[idx]

    if chosen["id"] == "custom":
        pattern = _input(
            "Regex pattern (Python re syntax)",
            default=r"^zpa_list_.*$",
        ).strip()
        return pattern, "Custom regex"

    return chosen["pattern"], chosen["label"]


# ──────────────────────────────────────────────────────────────────────────
# Strands agent build + chat loop
# ──────────────────────────────────────────────────────────────────────────


def _extract_usage(result: Any) -> tuple[int, int, int]:
    """Return (input_tokens, output_tokens, total_tokens) from an AgentResult.

    Strands populates ``result.metrics.accumulated_usage`` as a
    ``TypedDict({inputTokens, outputTokens, totalTokens})``. Fall back
    to per-attribute access for older versions or partial responses.
    """
    metrics = getattr(result, "metrics", None)
    usage: Any = None
    if metrics is not None:
        usage = getattr(metrics, "accumulated_usage", None)
    if usage is None:
        return 0, 0, 0

    def _get(obj: Any, *keys: str) -> int:
        for k in keys:
            if isinstance(obj, dict) and k in obj:
                return int(obj[k] or 0)
            attr = getattr(obj, k, None)
            if attr is not None:
                return int(attr or 0)
        return 0

    in_t = _get(usage, "inputTokens", "input_tokens")
    out_t = _get(usage, "outputTokens", "output_tokens")
    total = _get(usage, "totalTokens", "total_tokens") or (in_t + out_t)
    return in_t, out_t, total


def _format_stats(elapsed: float, in_t: int, out_t: int, total: int) -> str:
    parts = [f"{elapsed:.1f}s"]
    if total:
        parts.append(f"{total:,} tokens")
        if in_t or out_t:
            parts.append(f"in:{in_t:,} out:{out_t:,}")
    return f"{DIM}[{' | '.join(parts)}]{NC}"


def build_agent(
    *,
    runtime_arn: str,
    region: str,
    model_id: str,
    tool_filter: str,
    initial_tools_meta: list[dict],
    endpoint: str,
    session_id: str,
    mcp_session_id: Optional[str] = None,
) -> tuple[Any, list[dict]]:
    """Build a Strands ``Agent`` with the filtered Zscaler tools.

    Setting ``AWS_REGION`` is the safest way to push the region down to
    Strands' BedrockModel — its public constructor signature changes
    across releases (``region`` and ``boto_session`` are unstable), but
    boto3's session resolver is.
    """
    from strands import Agent
    from strands.models.bedrock import BedrockModel

    os.environ.setdefault("AWS_DEFAULT_REGION", region)
    os.environ["AWS_REGION"] = region

    pat = re.compile(tool_filter)
    kept = [t for t in initial_tools_meta if pat.search(t["name"])]
    if not kept:
        raise RuntimeError(
            f"Tool filter '{tool_filter}' matched 0 of {len(initial_tools_meta)} tools."
        )

    tools = [
        make_strands_tool(
            name=t["name"],
            description=t.get("description", ""),
            endpoint=endpoint,
            region=region,
            session_id=session_id,
            mcp_session_id=mcp_session_id,
        )
        for t in kept
    ]

    agent = Agent(
        model=BedrockModel(model_id=model_id),
        tools=tools,
        system_prompt=(
            "You are a Zscaler administrator's assistant. Use the available "
            "tools to answer questions about ZIA, ZPA, ZDX, ZCC, ZIdentity, "
            "ZTW, ZMS, EASM, and Z-Insights. Be precise — quote IDs and "
            "names verbatim from tool responses. Don't speculate or invent "
            "data the tools didn't return."
        ),
    )
    return agent, kept


def _show_help() -> None:
    print()
    print(f"  {BOLD}Available commands{NC}")
    print(f"  {'─' * 40}")
    print(f"  {CYAN}help{NC}           Show this help message")
    print(f"  {CYAN}status{NC}         Show agent + session info")
    print(f"  {CYAN}tools{NC}          List loaded tool names")
    print(f"  {CYAN}clear{NC}          Clear the screen")
    print(f"  {CYAN}reset{NC}          Reset conversation history")
    print(f"  {CYAN}quit{NC} / {CYAN}exit{NC} / {CYAN}q{NC}  End the chat session")
    print()
    print(f"  {BOLD}Examples{NC}")
    print(f"  {'─' * 40}")
    print(f"  {DIM}List my ZPA segment groups and how many there are.{NC}")
    print(f"  {DIM}Are there any ZIA URL filtering rules that look overly permissive?{NC}")
    print(f"  {DIM}What is the experience score trend for users in San Jose?{NC}")
    print()


def chat_loop(
    *,
    agent: Any,
    runtime_arn: str,
    region: str,
    model_id: str,
    loaded_tools: list[dict],
    tool_filter_label: str,
) -> None:
    print()
    print("=" * 60)
    print(f"  {BOLD}Zscaler MCP Agent — Bedrock + AgentCore{NC}")
    print(f"  Runtime:    {DIM}{runtime_arn}{NC}")
    print(f"  Region:     {region}")
    print(f"  Model:      {model_id}")
    print(f"  Tools:      {len(loaded_tools)} loaded  {DIM}({tool_filter_label}){NC}")
    print(f"  Type {DIM}'help'{NC} for commands.")
    print("=" * 60)
    print()

    session_start = time.time()
    total_in = 0
    total_out = 0
    total_tokens = 0
    message_count = 0

    def show_status() -> None:
        elapsed = time.time() - session_start
        print()
        print(f"  {BOLD}Session info{NC}")
        print(f"  {'─' * 40}")
        print(f"  Runtime:        {runtime_arn}")
        print(f"  Region:         {region}")
        print(f"  Model:          {model_id}")
        print(f"  Tools loaded:   {len(loaded_tools)}")
        print(f"  Duration:       {elapsed:.0f}s")
        print(f"  Messages sent:  {message_count}")
        print(f"  Tokens (total): {total_tokens:,}")
        print(f"  Tokens (input): {total_in:,}")
        print(f"  Tokens (out):   {total_out:,}")
        print()

    def show_tools() -> None:
        print()
        print(f"  {BOLD}Loaded tools ({len(loaded_tools)}){NC}")
        print(f"  {'─' * 40}")
        for t in loaded_tools:
            desc = (t.get("description") or "").strip().split("\n", 1)[0][:70]
            print(f"  {CYAN}{t['name']:42s}{NC} {DIM}{desc}{NC}")
        print()

    try:
        while True:
            try:
                user_input = input(f"{BOLD}You:{NC} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue
            cmd = user_input.lower()
            if cmd in ("quit", "exit", "q"):
                break
            if cmd == "help":
                _show_help()
                continue
            if cmd == "status":
                show_status()
                continue
            if cmd == "tools":
                show_tools()
                continue
            if cmd == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue
            if cmd == "reset":
                agent.messages.clear()
                total_in = 0
                total_out = 0
                total_tokens = 0
                message_count = 0
                session_start = time.time()
                ok("Conversation reset.")
                print()
                continue

            message_count += 1
            sp = Spinner("Thinking").start()
            t0 = time.time()
            try:
                result = agent(user_input)
            except Exception as exc:
                sp.stop()
                err(f"Agent invocation failed: {exc}")
                continue
            elapsed = sp.stop()
            sp_elapsed = time.time() - t0

            in_t, out_t, total = _extract_usage(result)
            total_in += in_t
            total_out += out_t
            total_tokens += total

            text = str(result) if result is not None else ""
            print()
            print(f"{GREEN}Agent:{NC} {text}")
            print(f"       {_format_stats(max(elapsed, sp_elapsed), in_t, out_t, total)}")
            print()

    except KeyboardInterrupt:
        print()

    session_elapsed = time.time() - session_start
    print()
    print(f"{DIM}{'─' * 50}{NC}")
    print(
        f"{DIM}Session: {session_elapsed:.0f}s"
        f" | Messages: {message_count}"
        f" | Tokens: {total_tokens:,}"
        f" (in:{total_in:,} out:{total_out:,}){NC}"
    )
    print(f"{DIM}{'─' * 50}{NC}")
    info("Chat session ended.")


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--runtime-arn",
        default=os.getenv("AGENTCORE_RUNTIME_ARN"),
        help="Skip the deployment prompt — use this ARN directly.",
    )
    p.add_argument(
        "--region",
        default=os.getenv("AWS_REGION"),
        help="Skip the region prompt — use this region directly.",
    )
    p.add_argument(
        "--model",
        default=os.getenv("BEDROCK_MODEL_ID"),
        help="Skip the model picker — use this Bedrock model id directly.",
    )
    p.add_argument(
        "--tool-filter",
        default=None,
        help="Skip the tool-preset picker — use this regex directly.",
    )
    p.add_argument(
        "--list-tools",
        action="store_true",
        help="List the runtime's tools and exit. Pure smoke test, no LLM.",
    )
    p.add_argument(
        "--no-banner",
        action="store_true",
        help="Skip the ASCII logo (useful in CI / logs).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.WARNING)

    if not args.no_banner:
        print_zscaler_logo()

    if args.runtime_arn and args.region:
        runtime_arn = args.runtime_arn
        region = args.region
    else:
        runtime_arn, region = prompt_for_deployment()

    endpoint = build_endpoint(runtime_arn, region)
    session_id = f"strands-chat-{uuid.uuid4()}"
    info(f"Endpoint:   {endpoint}")
    info(f"Session ID: {session_id}")

    print()
    sp = Spinner("Initializing MCP session").start()
    try:
        mcp_session_id = mcp_initialize(
            endpoint, region, runtime_session_id=session_id
        )
    except httpx.HTTPStatusError as exc:
        sp.stop()
        err(
            f"HTTP {exc.response.status_code} from AgentCore Runtime on initialize: "
            f"{exc.response.text[:300]}"
        )
        return 2
    except Exception as exc:
        sp.stop()
        err(f"MCP initialize failed: {exc}")
        return 2
    sp.stop()
    if mcp_session_id:
        ok(f"MCP session established (id={mcp_session_id[:12]}…)")
    else:
        info("Runtime is the legacy Genesis-wrapped image — running session-less.")

    sp = Spinner("Discovering tools").start()
    try:
        tools_result = send_mcp_request(
            endpoint,
            region,
            "tools/list",
            session_id=session_id,
            mcp_session_id=mcp_session_id,
        )
    except httpx.HTTPStatusError as exc:
        sp.stop()
        err(
            f"HTTP {exc.response.status_code} from AgentCore Runtime: "
            f"{exc.response.text[:300]}"
        )
        return 2
    except Exception as exc:
        sp.stop()
        err(f"tools/list failed: {exc}")
        return 2
    sp.stop()

    tools_meta = tools_result.get("tools", [])
    if not tools_meta:
        err("Runtime returned zero tools. Check the deployment.")
        return 3
    ok(f"Discovered {len(tools_meta)} tools.")

    if args.list_tools:
        for t in tools_meta[:60]:
            desc = (t.get("description") or "").strip().split("\n", 1)[0][:90]
            print(f"  - {t['name']:50s} {desc}")
        if len(tools_meta) > 60:
            print(f"  ... and {len(tools_meta) - 60} more.")
        return 0

    model_id = args.model or prompt_for_model()
    tool_filter, tool_filter_label = (
        (args.tool_filter, "Custom (CLI)") if args.tool_filter
        else prompt_for_tool_filter(len(tools_meta))
    )

    try:
        agent, loaded = build_agent(
            runtime_arn=runtime_arn,
            region=region,
            model_id=model_id,
            tool_filter=tool_filter,
            initial_tools_meta=tools_meta,
            endpoint=endpoint,
            session_id=session_id,
            mcp_session_id=mcp_session_id,
        )
    except ImportError:
        err("Strands is not installed. Run: uv pip install strands-agents")
        return 4
    except Exception as exc:
        err(str(exc))
        return 4

    ok(f"Strands agent ready with {len(loaded)} tools (model={model_id}).")

    chat_loop(
        agent=agent,
        runtime_arn=runtime_arn,
        region=region,
        model_id=model_id,
        loaded_tools=loaded,
        tool_filter_label=tool_filter_label,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
