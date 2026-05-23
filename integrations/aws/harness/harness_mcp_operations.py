#!/usr/bin/env python3
"""Zscaler MCP Server — AWS Bedrock AgentCore **Harness** deployment & lifecycle.

Sibling of ``integrations/aws/bedrock-agentcore/aws_mcp_operations.py``.
Where that script deploys the *Runtime* that hosts the MCP server,
**this** script consumes any reachable MCP URL (Runtime, ECS, Lambda+ALB,
on-prem, GCP/Azure, etc.) and wires it into an AgentCore **Harness** —
AWS's managed, declarative agent layer (preview).

Topology (see ``local_dev/aws_harness_agent/integration-analysis.md``):

    User / Bedrock console  ────►  Harness (managed Strands)
                                          │
                                          │ remote_mcp tool
                                          │ Authorization: Basic ${arn:…token-vault…}
                                          ▼
                                   Zscaler MCP Server  ──►  Zscaler OneAPI

Commands:
    deploy      Create execution role + credential provider + harness
    status      Show harness status, model, tools, last activity
    logs        Tail the harness CloudWatch log group
    invoke      One-shot smoke test (sends a single prompt, prints reply)
    destroy     Reverse-order tear-down (harness → cred provider → IAM role)

Critical constraint
-------------------
Harness's ``remote_mcp`` tool can only attach *static* headers — it has
no SigV4 signer. A SigV4-protected AgentCore Runtime URL therefore
**cannot** be consumed directly by ``remote_mcp``. Use one of:

  * A non-SigV4 MCP endpoint (ECS/Fargate + ALB, Lambda + API Gateway
    without IAM auth, EC2 + systemd, Cloud Run, ACA, on-prem).
  * Front the SigV4 Runtime with an AgentCore **Gateway** (Topology C,
    deferred) — the gateway does the SigV4 signing on Harness's behalf.

The script will warn you if you point it at an obvious SigV4-only URL
(``bedrock-agentcore.<region>.amazonaws.com/runtimes/...``) and let you
proceed anyway.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import re
import secrets
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import boto3
    from botocore.exceptions import (
        ClientError,
        EndpointConnectionError,
        NoCredentialsError,
        ProfileNotFound,
    )
except ImportError:
    print("ERROR: boto3 is required.  pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────
# Branding
# ──────────────────────────────────────────────────────────────────────────

_ZSCALER_ART = [
    "███████╗███████╗ ██████╗ █████╗ ██╗     ███████╗██████╗ ",
    "╚══███╔╝██╔════╝██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗",
    "  ███╔╝ ███████╗██║     ███████║██║     █████╗  ██████╔╝",
    " ███╔╝  ╚════██║██║     ██╔══██║██║     ██╔══╝  ██╔══██╗",
    "███████╗███████║╚██████╗██║  ██║███████╗███████╗██║  ██║",
    "╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
]
_TAGLINE = "AWS Bedrock AgentCore — Harness Deployment (Preview)"


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
# Colours / pretty-print
# ──────────────────────────────────────────────────────────────────────────

COLOURS = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
if COLOURS and platform.system() == "Windows":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        COLOURS = False

RED      = "\033[0;31m" if COLOURS else ""
GREEN    = "\033[0;32m" if COLOURS else ""
YELLOW   = "\033[1;33m" if COLOURS else ""
BLUE     = "\033[0;34m" if COLOURS else ""
CYAN     = "\033[0;36m" if COLOURS else ""
SKY_BLUE = "\033[34;01m" if COLOURS else ""
BOLD     = "\033[1m" if COLOURS else ""
DIM      = "\033[2m" if COLOURS else ""
NC       = "\033[0m" if COLOURS else ""


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
# Spinner (for long-running polls)
# ──────────────────────────────────────────────────────────────────────────

_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Spinner:
    """Minimal threaded spinner with elapsed-time counter."""

    def __init__(self, label: str) -> None:
        self.label = label
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_ts: float = 0.0

    def start(self) -> "Spinner":
        if not COLOURS:
            print(f"{BLUE}…{NC} {self.label}")
            return self
        self._start_ts = time.time()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        i = 0
        while not self._stop.is_set():
            elapsed = int(time.time() - self._start_ts)
            mm, ss = divmod(elapsed, 60)
            elapsed_s = f"{mm:d}m {ss:02d}s" if mm else f"{ss}s"
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            sys.stdout.write(f"\r{CYAN}{frame}{NC} {self.label}  {DIM}({elapsed_s}){NC}   ")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def stop(self, final: Optional[str] = None) -> None:
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=1.0)
        if COLOURS:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
        if final:
            print(final)


# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / ".aws-harness-state.json"
RUNTIME_STATE_FILE = SCRIPT_DIR.parent / "bedrock-agentcore" / ".aws-deploy-state.json"

# Container image. Matches the convention in
# integrations/aws/bedrock-agentcore/aws_mcp_operations.py:
#   * Default → the immutable "<semver>-bedrock" tag in AWS Marketplace ECR.
#   * Override → set ZSCALER_MCP_IMAGE_URI in .env (or as a CLI flag) to a
#     locally-built dev image you've pushed to your own ECR, a mirrored
#     private ECR, or a pinned older Marketplace tag.
# The image itself is identical regardless of host (AgentCore Runtime or
# App Runner) — only the surrounding deploy plumbing differs.
MARKETPLACE_IMAGE = (
    "709825985650.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:0.10.4-bedrock"
)

DEFAULT_REGION = "us-east-1"
# AgentCore Harness names match [a-zA-Z][a-zA-Z0-9_]{0,39} — letters,
# digits, underscores only (no hyphens), max 40 chars. The IAM /
# Token-Vault / CloudWatch resources alongside the harness accept the
# hyphenated style, so we only swap to underscores for the harness
# itself (and the remote_mcp tool name, which has the same constraint).
DEFAULT_HARNESS_NAME = "zscaler_mcp_harness"
DEFAULT_ROLE_NAME = "zscaler-mcp-harness-execution-role"
DEFAULT_CREDENTIAL_PROVIDER_NAME = "zscaler-mcp-creds"
DEFAULT_MCP_TOOL_NAME = "zscaler"
# AgentCore Harness auto-writes its APPLICATION_LOGS under this CloudWatch
# log-group prefix without any operator wiring (see "logs are auto-managed"
# note above). `cmd_logs` scans for `<prefix>/<runtime-id>` log groups
# tied to a given harness at tail time.
AGENTCORE_RUNTIME_LOG_PREFIX = "/aws/bedrock-agentcore/runtimes/"
HARNESS_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,39}$")

# Amazon ECS Express Mode is the default non-SigV4 hosting target for the
# MCP server so Harness's remote_mcp tool can authenticate with a static
# Basic header. We picked Express Mode over plain App Runner because:
#   * AWS stopped onboarding new App Runner customers on Apr 30, 2026
#     (existing customers grandfathered, no new features). Express Mode
#     is the AWS-recommended replacement.
#   * Express Mode auto-provisions the ALB, target groups, security
#     groups, and auto-scaling policies — same one-API-call UX as App
#     Runner had.
#   * It returns a stable public HTTPS URL of the form
#     "xxxxx.ecs.<region>.on.aws" with managed TLS, so Harness's
#     remote_mcp tool can speak to it with no extra plumbing.
# Image, port, and runtime env vars are kept identical to the AgentCore
# Runtime deploy in bedrock-agentcore/ — only the host wrapper differs.
DEFAULT_ECS_CLUSTER_NAME = "zscaler-mcp"
DEFAULT_ECS_SERVICE_NAME = "zscaler-mcp-server"
DEFAULT_ECS_EXECUTION_ROLE_NAME = "zscaler-mcp-ecs-task-execution-role"
DEFAULT_ECS_INFRASTRUCTURE_ROLE_NAME = "zscaler-mcp-ecs-infrastructure-role"
DEFAULT_ECS_LOG_GROUP = "/ecs/zscaler-mcp"
DEFAULT_ECS_LOG_STREAM_PREFIX = "mcp"
DEFAULT_CONTAINER_PORT = 8000
DEFAULT_ECS_CPU = "1024"    # 1 vCPU
DEFAULT_ECS_MEMORY = "2048"  # 2 GB
DEFAULT_HEALTH_CHECK_PATH = "/health"

# ──────────────────────────────────────────────────────────────────────────
# Gateway topology (PR #48) — preview
#
# Alternative to ECS Express: deploy the MCP server on AgentCore Runtime
# and front it with an AgentCore Gateway. Harness consumes the Gateway via
# the agentcore_gateway tool type (NOT remote_mcp). This eliminates the
# ALB / Fargate / Express-cluster footprint at the cost of standing up a
# Cognito User Pool (the inbound IdP).
#
# End-to-end auth (all three boundaries use the same Cognito User Pool +
# App Client, brokered by a single OAuth2 credential provider in AgentCore
# Identity Token Vault):
#
#   user/console ──SigV4───────────────────────────────► Harness
#       Harness ──HarnessGatewayOutboundAuth.oauth─────► Gateway
#       Gateway ──customJWTAuthorizer (Cognito JWKS)───┘
#       Gateway ──target outbound: oauth (Cognito M2M)─► Runtime
#       Runtime ──customJwtAuthorizer (Cognito JWKS)───┘
#       Runtime ──TaskRole boto3 fetch──► Secrets Manager (Zscaler creds)
#
# CUSTOM_JWT is the only inbound auth Gateway supports today (botocore
# 2023-06-05 service-2.json: AuthorizerConfiguration.customJWTAuthorizer
# is the sole variant). awsIam is listed on HarnessGatewayOutboundAuth but
# Gateway has no IAM inbound mode yet, so we don't use it.
# ──────────────────────────────────────────────────────────────────────────

# Names default to a stable per-tenant prefix so a re-deploy is idempotent
# and a destroy can find them. All overridable via CLI flags or env vars.
DEFAULT_TOPOLOGY = "ecs"  # backward-compatible default; preserves PR #47 behaviour
SUPPORTED_TOPOLOGIES = ("ecs", "gateway")

# AgentCore Runtime — sibling deploy still owns the equivalent runtime in
# the bedrock-agentcore CFN flow; this script's Gateway topology
# provisions its own so the two are independent.
DEFAULT_RUNTIME_NAME = "zscaler_mcp_runtime"  # same name pattern as Harness
DEFAULT_RUNTIME_EXECUTION_ROLE_NAME = "zscaler-mcp-harness-runtime-role"

# AgentCore Gateway
DEFAULT_GATEWAY_NAME = "zscaler-mcp-gateway"
DEFAULT_GATEWAY_TARGET_NAME = "zscaler-mcp-runtime"
DEFAULT_GATEWAY_ROLE_NAME = "zscaler-mcp-harness-gateway-role"

# AgentCore Identity OAuth2 credential provider — the Token Vault entry
# that holds (clientId, clientSecret, discoveryUrl). Used by BOTH the
# Harness→Gateway leg (HarnessGatewayOutboundAuth.oauth) AND the
# Gateway→Runtime leg (target outbound credentialProvider). The same
# Cognito App Client backs all three boundaries, so one provider is
# enough.
DEFAULT_OAUTH_PROVIDER_NAME = "zscaler-mcp-cognito-oauth"

# Amazon Cognito — the AWS-native OIDC IdP that fronts the Gateway.
# We default to a single User Pool with one App Client (client_credentials
# grant) and one Resource Server (whose identifier becomes the JWT
# audience). The custom scope on the Resource Server lets Cognito mint
# M2M tokens without needing a real user. Domain prefix is required for
# the /oauth2/token endpoint (Cognito requires a hosted UI domain even
# when only client_credentials is enabled).
DEFAULT_COGNITO_USER_POOL_NAME = "zscaler-mcp-harness-up"
DEFAULT_COGNITO_RESOURCE_SERVER_IDENTIFIER = "zscaler-mcp"
DEFAULT_COGNITO_SCOPE_NAME = "invoke"
DEFAULT_COGNITO_APP_CLIENT_NAME = "zscaler-mcp-harness-client"
# Domain prefix is suffixed with the AWS account ID at deploy time so two
# tenants in the same region don't collide. The full domain becomes:
#   <prefix>-<accountId>.auth.<region>.amazoncognito.com
# Cognito enforces global uniqueness of the prefix portion within a region.
DEFAULT_COGNITO_DOMAIN_PREFIX = "zscaler-mcp-harness"

# Bare-minimum env vars that the Runtime container MUST have to bind
# to the port AgentCore expects. Applied only when the operator didn't
# already set them in .env — same fill-the-gap pattern as the ECS
# topology's _build_container_env_vars.
_RUNTIME_TOPOLOGY_FALLBACKS: dict[str, str] = {
    "ZSCALER_MCP_TRANSPORT": "streamable-http",
    "ZSCALER_MCP_HOST": "0.0.0.0",
    "ZSCALER_MCP_PORT": str(DEFAULT_CONTAINER_PORT),
    "ZSCALER_MCP_ALLOW_HTTP": "true",
    "ZSCALER_MCP_DISABLE_HOST_VALIDATION": "true",
}

# Secrets Manager: where we stash the Zscaler OneAPI credentials so the
# container can fetch them at boot via `zscaler_mcp.config` instead of
# receiving them as plaintext env vars in the ECS task definition.
# Namespaced under `zscaler-mcp-harness/` so this doesn't collide with
# the agentcore deploy's `zscaler-mcp/credentials` secret if both paths
# are exercised against the same account.
DEFAULT_ECS_SECRET_NAME = "zscaler-mcp-harness/credentials"

# The exact keys that move OUT of the ECS task env and INTO the
# Secrets Manager JSON blob. `zscaler_mcp/config.py` reads the secret,
# parses the JSON, and re-injects each key into ``os.environ`` before
# the SDK initialises — so from the SDK's perspective these are still
# regular env vars, they just never appear in the task definition or
# CloudTrail. `ZSCALER_CLOUD` is included because it's part of the same
# logical credential bundle (cloud / vanity domain pair the SDK needs
# to route to the correct ZIdentity tenant).
_ZSCALER_CRED_ENV_KEYS: frozenset[str] = frozenset({
    "ZSCALER_CLIENT_ID",
    "ZSCALER_CLIENT_SECRET",
    "ZSCALER_VANITY_DOMAIN",
    "ZSCALER_CUSTOMER_ID",
    "ZSCALER_CLOUD",
})
# ECS Express provisions an internal ALB and probes the container at this
# path every ~30s. We point it at /health (served by the MCP server's
# HealthCheckMiddleware) instead of /mcp because:
#   - /mcp requires POST + Accept: application/json,text/event-stream;
#     the ALB cannot synthesise that handshake, so probes against /mcp
#     get a 405 from RejectNonSSEGetMiddleware (or a 406 from FastMCP on
#     older images), marking every target unhealthy and flapping tasks.
#   - /health is anonymous, unconditional 200, and bypasses auth /
#     source-IP ACL / FastMCP — exactly what an LB probe needs.
# Available since zscaler-mcp-server image with the HealthCheckMiddleware
# (added alongside RejectNonSSEGetMiddleware for Bedrock Harness compat).

# Canonical AWS-managed policies — required for ECS Express Mode.
# Sources:
#   https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html
#   https://aws.amazon.com/blogs/containers/automated-deployments-with-github-actions-for-amazon-ecs-express-mode/
AWS_MANAGED_POLICY_ECS_TASK_EXECUTION = (
    "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
)
AWS_MANAGED_POLICY_ECS_INFRASTRUCTURE_EXPRESS = (
    "arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"
)

# Sticking to inference-profile model IDs so callers don't have to think
# about on-demand vs cross-region availability. Mirrors the catalogue
# used by integrations/aws/bedrock-agentcore/strands_agent_chat.py.
MODEL_CATALOGUE: list[dict[str, str]] = [
    {
        "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "label": "Claude Sonnet 4.6 (default)",
        "note": "Anthropic. Requires one-time use-case form in Bedrock console.",
    },
    {
        "id": "us.anthropic.claude-opus-4-5-20250929-v1:0",
        "label": "Claude Opus 4.7",
        "note": "Anthropic. Best-quality, slower, higher cost.",
    },
    {
        "id": "us.amazon.nova-pro-v1:0",
        "label": "Amazon Nova Pro",
        "note": "Native Amazon model. No third-party form required.",
    },
    {
        "id": "us.meta.llama3-3-70b-instruct-v1:0",
        "label": "Llama 3.3 70B Instruct",
        "note": "Open-weights. Tool use supported.",
    },
]

DEFAULT_MODEL_ID = MODEL_CATALOGUE[0]["id"]

SYSTEM_PROMPT = """You are a senior Zscaler Zero Trust Exchange administrator assistant.
You have one tool — a Zscaler MCP server — exposing 200+ read and write
operations across ZIA, ZPA, ZDX, ZCC, ZTW, ZIdentity, EASM, Z-Insights, and ZMS.

Operating rules:
  • Always answer in plain language. Do not narrate tool plumbing
    (JMESPath, pagination, retries, schema validation).
  • Empty list responses are authoritative. If a *_list_* tool returns
    nothing for a name, the resource does not exist by that name — stop
    and ask the user to clarify, do not fan out retries.
  • Before creating or modifying anything, list/get first to understand
    current state. Treat every write as destructive — confirm with the
    user before executing.
  • After any ZIA create/update/delete you MUST call
    zia_activate_configuration(); changes are staged until activation.
  • IDs are strings even when numeric. Never invent IDs.
  • If a service appears to be missing, call
    zscaler_get_available_services first — it lists disabled services
    explicitly so you do not waste turns searching for tools that
    won't be there.
"""


# ──────────────────────────────────────────────────────────────────────────
# State file
# ──────────────────────────────────────────────────────────────────────────

def save_state(data: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(data, indent=2))


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def remove_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def persist_partial_state(
    partial: dict[str, Any], *, phase: str, topology: str
) -> None:
    """Incrementally append-and-overwrite the state file as each major
    resource is created during `deploy`.

    Why this exists: AgentCore Gateway / Runtime / Cognito provisioning
    is a multi-minute pipeline. If the operator hits Ctrl-C, a
    ValidationException fires partway through, or the network drops,
    every resource created up to that point would otherwise be orphaned
    — `cmd_destroy` only consults the state file and a missing file
    means "nothing to clean up", forcing manual AWS-console surgery.

    Behaviour:
      * Reads the existing state file (returns ``{}`` if absent or
        malformed) and shallow-merges ``partial`` on top.
      * Stamps ``topology``, ``phase``, and ``state_partial=True`` so
        ``cmd_destroy`` can branch correctly and so the operator can
        tell at a glance whether the last deploy finished. The final
        deploy step writes ``state_partial=False`` (see ``save_state``
        wrappers in cmd_deploy).
      * Best-effort — a failure to write the state file logs a warning
        and continues. The user always has the option to manually run
        ``aws bedrock-agentcore-control list-*`` to enumerate
        leftovers; not writing the file is strictly worse than writing
        a partial one.
    """
    try:
        current = load_state()
        current.update(partial)
        current["topology"] = topology
        current["phase"] = phase
        current["state_partial"] = True
        save_state(current)
    except OSError as e:
        warn(f"Could not persist partial state ({phase}): {e}")


def finalize_state(state: dict[str, Any]) -> None:
    """Mark a state file as the result of a complete deploy run.

    Call this exactly once, at the end of ``cmd_deploy``, after the
    Harness itself has been created. Sets ``state_partial=False`` and
    stamps ``deploy_completed_at`` so subsequent ``status`` runs can
    show the operator that the deploy crossed the finish line.
    """
    state["state_partial"] = False
    state["deploy_completed_at"] = _utc_now_iso()
    save_state(state)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ──────────────────────────────────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────────────────────────────────

def prompt(label: str, default: Optional[str] = None, *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    if secret:
        import getpass
        val = getpass.getpass(f"{label}{suffix}: ").strip()
    else:
        val = input(f"{label}{suffix}: ").strip()
    return val or (default or "")


def prompt_bool(label: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    val = input(f"{label} [{suffix}]: ").strip().lower()
    if not val:
        return default
    return val[:1] == "y"


def prompt_choice(label: str, choices: list[str], default_idx: int = 0) -> int:
    print(f"\n{BOLD}{label}{NC}")
    for i, ch in enumerate(choices, start=1):
        marker = f"{GREEN}*{NC}" if i - 1 == default_idx else " "
        print(f"  {marker} {i}. {ch}")
    while True:
        raw = input(f"Choice [{default_idx + 1}]: ").strip()
        if not raw:
            return default_idx
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return int(raw) - 1
        warn(f"Invalid choice — pick 1-{len(choices)}")


# ──────────────────────────────────────────────────────────────────────────
# AWS session helpers
# ──────────────────────────────────────────────────────────────────────────

def get_session(region: str, profile: Optional[str] = None) -> boto3.Session:
    try:
        if profile:
            return boto3.Session(profile_name=profile, region_name=region)
        return boto3.Session(region_name=region)
    except ProfileNotFound as e:
        err(f"AWS profile not found: {e}")
        sys.exit(1)


def get_account_id(sess: boto3.Session) -> str:
    sts = sess.client("sts")
    try:
        return sts.get_caller_identity()["Account"]
    except (NoCredentialsError, ClientError) as e:
        err(f"Could not resolve AWS account from STS — check credentials. ({e})")
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────
# Runtime URL discovery (auto-discover co-deployed AgentCore Runtime)
# ──────────────────────────────────────────────────────────────────────────

def discover_runtime_url(region: str) -> Optional[dict[str, str]]:
    """Look for a sibling AgentCore Runtime deployment and pull its MCP URL.

    Returns a dict with ``url``, ``stack_name``, ``runtime_arn`` if found,
    None otherwise. The URL surfaced by AgentCore Runtime is SigV4-only,
    so the caller must decide whether to use it (see module docstring).
    """
    if not RUNTIME_STATE_FILE.exists():
        return None
    try:
        state = json.loads(RUNTIME_STATE_FILE.read_text())
    except json.JSONDecodeError:
        return None
    stack = state.get("stack_name")
    region_in_state = state.get("region")
    if not stack or not region_in_state:
        return None
    if region_in_state != region:
        warn(
            f"Sibling Runtime deployment is in {region_in_state}, "
            f"but this Harness deploy is targeting {region} — won't auto-discover."
        )
        return None
    try:
        sess = get_session(region)
        cfn = sess.client("cloudformation")
        outs = cfn.describe_stacks(StackName=stack)["Stacks"][0].get("Outputs", []) or []
        out_map = {o["OutputKey"]: o["OutputValue"] for o in outs}
    except ClientError:
        return None
    url = out_map.get("RuntimeMcpUrl") or out_map.get("RuntimeUrl")
    arn = out_map.get("RuntimeArn") or ""
    if not url:
        return None
    return {"url": url, "stack_name": stack, "runtime_arn": arn}


def url_looks_sigv4_only(url: str) -> bool:
    return "bedrock-agentcore." in url and "/runtimes/" in url


# ──────────────────────────────────────────────────────────────────────────
# IAM execution role
# ──────────────────────────────────────────────────────────────────────────

def _harness_role_trust_policy() -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def _harness_role_inline_policy(
    account_id: str, region: str, harness_name: str
) -> dict[str, Any]:
    """Mirror of the AWS-published Harness execution role policy.

    Source:
      https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness-security.html#harness-execution-role-policy

    Key things this enables (and that the previous, narrower policy did
    NOT, which was the root cause of every InvokeHarness call returning
    "Failed to start MCP client: ... unhandled errors in a TaskGroup"):

    - **ECR Public auth** (`ecr-public:GetAuthorizationToken` +
      `sts:GetServiceBearerToken`). Harness is implemented as an
      auto-managed AgentCore Runtime, and that runtime pulls its own
      container from ECR Public at session start. Without these grants
      the underlying runtime never starts and every tool-loader call
      times out with a TaskGroup wrapper.
    - **CloudWatch Logs scoped to `/aws/bedrock-agentcore/runtimes/*`**
      so the auto-managed runtime can write its application logs
      (those are where Harness logs actually land — they do NOT go
      through the CloudWatch vendedLogs delivery pipeline, harness is
      not a valid resource type for `PutDeliverySource`).
    - **X-Ray + CloudWatch Metrics** for the AgentCore Observability
      dashboard.
    - **Workload identity scope** narrowed to
      `workload-identity-directory/default/workload-identity/harness_<name>-*`,
      same pattern the AgentCore CLI scaffolds.
    - **Token Vault `GetResourceApiKey` + secretsmanager + kms:Decrypt**
      so the `remote_mcp` tool can resolve `${arn:…}` headers without
      the documented `AccessDeniedException` on `GetSecretValue`.
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockModelInvocation",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Converse",
                    "bedrock:ConverseStream",
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account_id}:*",
                    f"arn:aws:bedrock:{region}:{account_id}:inference-profile/*",
                    f"arn:aws:bedrock:{region}:{account_id}:application-inference-profile/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                ],
            },
            {
                "Sid": "EcrPublicTokenAccess",
                "Effect": "Allow",
                "Action": ["ecr-public:GetAuthorizationToken"],
                "Resource": "*",
            },
            {
                "Sid": "StsForEcrPublicPull",
                "Effect": "Allow",
                "Action": ["sts:GetServiceBearerToken"],
                "Resource": "*",
            },
            {
                "Sid": "XRayTracingAccess",
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                "Resource": "*",
            },
            {
                "Sid": "CloudWatchLogsGroup",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:DescribeLogStreams",
                ],
                "Resource": (
                    f"arn:aws:logs:{region}:{account_id}"
                    ":log-group:/aws/bedrock-agentcore/runtimes/*"
                ),
            },
            {
                "Sid": "CloudWatchLogsDescribeGroups",
                "Effect": "Allow",
                "Action": ["logs:DescribeLogGroups"],
                "Resource": f"arn:aws:logs:{region}:{account_id}:log-group:*",
            },
            {
                "Sid": "CloudWatchLogsStream",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": (
                    f"arn:aws:logs:{region}:{account_id}"
                    ":log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ),
            },
            {
                "Sid": "CloudWatchMetricsPublish",
                "Effect": "Allow",
                "Action": "cloudwatch:PutMetricData",
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "cloudwatch:namespace": "bedrock-agentcore",
                    }
                },
            },
            {
                # Workload-identity access-token actions. Scoped to the
                # AgentCore-managed `default` workload-identity directory
                # and the per-harness identity AWS auto-creates under it
                # (`workload-identity/harness_<name>-<aws-suffix>`).
                "Sid": "AgentCoreWorkloadIdentity",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetWorkloadAccessToken",
                    "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/harness_{harness_name}-*",
                ],
            },
            {
                # Token-Vault credential resolution. The `remote_mcp` tool
                # uses these calls to materialise `${arn:…}` header
                # substitutions (API-key or OAuth2 providers).
                #
                # Per the canonical AWS service-authorization reference:
                #   https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonbedrockagentcore.html
                # the `GetResourceApiKey` action requires permission on
                # THREE resource types simultaneously: `apikeycredentialprovider`,
                # `token-vault`, AND `workload-identity`. (The
                # `scope-credential-provider-access` doc page omits the
                # apikeycredentialprovider line; trust the reference.)
                # AgentCore Identity performs FIVE distinct authz checks
                # for one logical call — the directory itself is also
                # checked, and IAM ARN matching is exact (NOT prefix-
                # matched), so `token-vault/default` does NOT cover
                # `token-vault/default/apikeycredentialprovider/<name>`.
                #
                # ARN shapes covered (every form we've observed in error
                # messages plus the canonical ones from the reference):
                #   1. workload-identity-directory/default
                #      (the directory root)
                #   2. workload-identity-directory/default/workload-identity/
                #      harness_<name>-<aws-suffix>
                #      (the per-harness workload-identity)
                #   3. token-vault/default
                #      (the parent token vault)
                #   4. token-vault/default/apikeycredentialprovider/*
                #      (the API-key credential provider sub-resource)
                #   5. token-vault/default/oauth2credentialprovider/*
                #      (the OAuth2 credential provider sub-resource)
                #
                # Listing all five resource ARNs is the simplest "no
                # whack-a-mole" form — every authz check the runtime
                # makes lands on a statement that allows it.
                "Sid": "ResolveTokenVaultCredentials",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetResourceApiKey",
                    "bedrock-agentcore:GetResourceOauth2Token",
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/harness_{harness_name}-*",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:token-vault/default",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:token-vault/default/apikeycredentialprovider/*",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:token-vault/default/oauth2credentialprovider/*",
                ],
            },
            {
                # GetResourceApiKey internally reads the Secrets Manager
                # secret that the Token Vault uses to persist API-key
                # credential providers. Without this, the remote_mcp
                # tool loader fails with
                #   AccessDeniedException ... not authorized to perform:
                #   secretsmanager:GetSecretValue
                # AgentCore Identity stores these as managed secrets
                # under the bedrock-agentcore-identity!* name prefix.
                "Sid": "ReadTokenVaultBackingSecrets",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": [
                    f"arn:aws:secretsmanager:{region}:{account_id}:secret:bedrock-agentcore-identity*",
                ],
            },
            {
                # Those Secrets Manager entries are KMS-encrypted with
                # the AWS-managed `aws/secretsmanager` key. Scope the
                # grant via ViaService so it can't be replayed against
                # other workloads.
                "Sid": "DecryptTokenVaultBackingSecrets",
                "Effect": "Allow",
                "Action": ["kms:Decrypt"],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "kms:ViaService": f"secretsmanager.{region}.amazonaws.com",
                    }
                },
            },
        ],
    }


def ensure_execution_role(
    sess: boto3.Session, role_name: str, region: str, harness_name: str
) -> str:
    iam = sess.client("iam")
    account_id = get_account_id(sess)
    inline_policy = _harness_role_inline_policy(account_id, region, harness_name)

    try:
        existing = iam.get_role(RoleName=role_name)
        role_arn = existing["Role"]["Arn"]
        info(f"Reusing existing execution role: {role_arn}")
        try:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName="HarnessInlinePolicy",
                PolicyDocument=json.dumps(inline_policy),
            )
            ok("Refreshed inline policy on existing role.")
        except ClientError as e:
            warn(f"Could not refresh inline policy (continuing): {e}")
        return role_arn
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise

    info(f"Creating execution role: {role_name}")
    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(_harness_role_trust_policy()),
        Description="Execution role for Zscaler MCP AgentCore Harness",
        Tags=[
            {"Key": "managed-by", "Value": "zscaler-mcp-harness"},
            {"Key": "integration", "Value": "harness"},
        ],
    )
    role_arn = resp["Role"]["Arn"]
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="HarnessInlinePolicy",
        PolicyDocument=json.dumps(inline_policy),
    )
    # IAM role propagation in STS can take 5-15s after creation. Sleep a
    # small fixed window so CreateHarness doesn't 400 on "role not yet
    # assumable" — empirically AgentCore validates the trust policy
    # synchronously when CreateHarness is dispatched.
    sp = Spinner("Waiting for IAM role propagation (≈10s)").start()
    time.sleep(10)
    sp.stop(f"{GREEN}[OK]{NC}    Role propagated.")
    ok(f"Created execution role: {role_arn}")
    return role_arn


def delete_execution_role(sess: boto3.Session, role_name: str) -> None:
    iam = sess.client("iam")
    try:
        iam.delete_role_policy(RoleName=role_name, PolicyName="HarnessInlinePolicy")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("NoSuchEntity",):
            warn(f"Could not delete inline policy: {e}")
    try:
        iam.delete_role(RoleName=role_name)
        ok(f"Deleted execution role: {role_name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "NoSuchEntity":
            info(f"Execution role {role_name} already absent.")
        else:
            warn(f"Could not delete execution role {role_name}: {e}")


# ──────────────────────────────────────────────────────────────────────────
# Amazon ECS Express Mode — non-SigV4 host for the MCP server
# ──────────────────────────────────────────────────────────────────────────
# Why ECS Express Mode? AgentCore Runtime endpoints require SigV4 signing,
# which Harness's remote_mcp tool cannot do. AWS deprecated new-customer
# onboarding for App Runner on Apr 30, 2026 and pointed everyone at ECS
# Express Mode as the replacement.
#
# Express Mode gives us:
#   * Auto-managed HTTPS endpoint (xxxxx.ecs.<region>.on.aws)
#   * Single API call (CreateExpressGatewayService) provisions the ALB,
#     target groups, security groups, and auto-scaling policies
#   * Cross-account ECR pull (same Marketplace image as AgentCore Runtime
#     when the user hasn't set ZSCALER_MCP_IMAGE_URI)
#   * One-shot tear-down via DeleteExpressGatewayService
#
# Two IAM roles are required (AWS conventions):
#   1. ecsTaskExecutionRole          — trusts ecs-tasks.amazonaws.com,
#                                       pulls image + writes container logs
#   2. ecsInfrastructureRoleForExpressServices
#                                    — trusts ecs.amazonaws.com,
#                                       manages the ALB / SGs / scaling
# Both are reused if they already exist by name (idempotent re-deploy).

def _extract_ecr_registry_account(image_uri: str) -> Optional[str]:
    """Extract the 12-digit AWS account ID from an ECR image URI.

    Returns None for non-ECR sources (public.ecr.aws, docker.io, etc.).
    Format: ``<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>``.
    """
    host = image_uri.split("/", 1)[0]
    parts = host.split(".")
    if len(parts) < 6 or parts[1] != "dkr" or parts[2] != "ecr":
        return None
    if not parts[0].isdigit() or len(parts[0]) != 12:
        return None
    return parts[0]


def _extract_ecr_region(image_uri: str) -> Optional[str]:
    """Extract the AWS region from an ECR image URI.

    Sibling of :func:`_extract_ecr_registry_account`. Returns None for
    non-ECR sources. Format:
    ``<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>``.
    """
    host = image_uri.split("/", 1)[0]
    parts = host.split(".")
    if len(parts) < 6 or parts[1] != "dkr" or parts[2] != "ecr":
        return None
    return parts[3] or None


def _assert_runtime_image_region_compatible(image_uri: str, deploy_region: str) -> None:
    """Fail fast with a clear remediation message when the container
    image lives in a different region than the AgentCore Runtime.

    AgentCore Runtime enforces same-region ECR. Unlike ECS Fargate
    (which is happy pulling cross-region), the control plane will
    reject ``CreateAgentRuntime`` with::

        ValidationException: Ecr uri region '<image-region>' does
        not match the application region '<deploy-region>'.
        Container images must be in the same region as the
        application.

    We pre-validate this BEFORE provisioning the Runtime IAM role so
    a region mismatch costs zero AWS resources.
    """
    image_region = _extract_ecr_region(image_uri)
    if image_region is None or image_region == deploy_region:
        return

    err(
        f"AgentCore Runtime requires the container image in the same region as the Runtime.\n"
        f"  image URI region : {image_region}  ({image_uri})\n"
        f"  deploy region    : {deploy_region}\n"
        "\n"
        "Two ways to fix this:\n"
        "\n"
        f"  A) Redeploy in {image_region} (where the image already is). Set\n"
        f"        AWS_REGION={image_region}    in your .env  (or pass --region {image_region})\n"
        "     and retry. This is the zero-replication path.\n"
        "\n"
        f"  B) Replicate the image into a {deploy_region} ECR repo in your own\n"
        "     account and override ZSCALER_MCP_IMAGE_URI to point at it.\n"
        "     Quick recipe (needs Docker + permission on both ECRs):\n"
        "\n"
        f"        aws ecr get-login-password --region {image_region} \\\n"
        f"          | docker login --username AWS --password-stdin {image_uri.split('/', 1)[0]}\n"
        f"        docker pull {image_uri}\n"
        f"        aws ecr create-repository --repository-name zscaler-mcp-server --region {deploy_region} || true\n"
        f"        aws ecr get-login-password --region {deploy_region} \\\n"
        f"          | docker login --username AWS --password-stdin <YOUR_ACCT>.dkr.ecr.{deploy_region}.amazonaws.com\n"
        f"        docker tag {image_uri} <YOUR_ACCT>.dkr.ecr.{deploy_region}.amazonaws.com/zscaler-mcp-server:bedrock\n"
        f"        docker push <YOUR_ACCT>.dkr.ecr.{deploy_region}.amazonaws.com/zscaler-mcp-server:bedrock\n"
        "\n"
        f"     Then in .env:\n"
        f"        ZSCALER_MCP_IMAGE_URI=<YOUR_ACCT>.dkr.ecr.{deploy_region}.amazonaws.com/zscaler-mcp-server:bedrock\n"
        "\n"
        "Note: the ECS topology does NOT have this restriction — ECS Fargate is happy\n"
        "pulling cross-region. This is an AgentCore Runtime constraint specifically."
    )
    sys.exit(1)


# ── IAM: ECS task execution role ───────────────────────────────────────
# Trusts ecs-tasks.amazonaws.com. AWS-managed
# AmazonECSTaskExecutionRolePolicy covers same-account ECR + CloudWatch
# Logs. We layer on an inline policy for cross-account ECR pull, scoped
# to whichever registry account is parsed out of the image URI (so the
# AWS Marketplace registry 709825985650 works for the default image,
# and a user's own ECR works when ZSCALER_MCP_IMAGE_URI overrides it).

def _ecs_task_execution_role_trust_policy() -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def _ecs_cross_account_ecr_policy(image_uri: str, region: str) -> Optional[dict[str, Any]]:
    """Inline policy granting cross-account ECR pull for the image's registry.

    Returns None when the image lives in the same account (the managed
    AmazonECSTaskExecutionRolePolicy already covers same-account pulls).
    """
    registry_account = _extract_ecr_registry_account(image_uri)
    if registry_account is None:
        # ECR Public or non-ECR registry — the AWS-managed policy already
        # handles the public flavour, and a non-ECR registry needs its
        # own credential mechanism (Secrets Manager + repositoryCredentials).
        return None
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ecr:GetAuthorizationToken"],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:DescribeImages",
                ],
                "Resource": f"arn:aws:ecr:{region}:{registry_account}:repository/*",
            },
        ],
    }


def _ecs_read_zscaler_secret_policy(
    secret_arn: str, region: str
) -> dict[str, Any]:
    """Inline policy granting the ECS execution role read access to the
    Zscaler credentials secret.

    Two statements, both tightly scoped:

    * ``secretsmanager:GetSecretValue`` on the **exact** secret ARN (we
      use the ARN with the random 6-char suffix Secrets Manager appends,
      not the bare name — otherwise IAM ARN matching can leak access to
      similarly-named secrets created later in the same account). To
      cover potential ARN format changes, we additionally allow the
      ``-*`` wildcard form so future revisions of the same logical
      secret still match.
    * ``kms:Decrypt`` constrained via ``kms:ViaService=secretsmanager.<region>``
      so the grant can only be used **through** Secrets Manager — never
      replayed directly against arbitrary KMS-encrypted resources.

    ECS Express has a single ``executionRoleArn`` slot (no separate
    ``taskRoleArn`` — that's a regular ECS-on-Fargate feature). So the
    container's boto3 client at runtime *also* uses this role; the same
    statement covers both image-pull-time and runtime usage.
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadZscalerCredentialsSecret",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": [
                    secret_arn,
                    f"{secret_arn}-*",
                ],
            },
            {
                "Sid": "DecryptZscalerCredentialsSecret",
                "Effect": "Allow",
                "Action": ["kms:Decrypt"],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "kms:ViaService": f"secretsmanager.{region}.amazonaws.com",
                    }
                },
            },
        ],
    }


def ensure_ecs_task_execution_role(
    sess: boto3.Session,
    role_name: str,
    image_uri: str,
    region: str,
    *,
    secret_arn: Optional[str] = None,
) -> str:
    iam = sess.client("iam")
    cross_account_policy = _ecs_cross_account_ecr_policy(image_uri, region)
    secret_policy = (
        _ecs_read_zscaler_secret_policy(secret_arn, region)
        if secret_arn else None
    )

    try:
        existing = iam.get_role(RoleName=role_name)
        role_arn = existing["Role"]["Arn"]
        info(f"Reusing existing ECS task execution role: {role_arn}")
        # Re-attach the managed policy (idempotent — IAM ignores duplicate
        # attachments) so a role manually altered out-of-band gets fixed.
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=AWS_MANAGED_POLICY_ECS_TASK_EXECUTION,
            )
        except ClientError as e:
            warn(f"Could not re-attach managed policy (continuing): {e}")
        if cross_account_policy is not None:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName="CrossAccountEcrPull",
                PolicyDocument=json.dumps(cross_account_policy),
            )
            ok("Refreshed cross-account ECR pull policy.")
        if secret_policy is not None:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName="ReadZscalerSecrets",
                PolicyDocument=json.dumps(secret_policy),
            )
            ok("Refreshed Zscaler-secret read policy.")
        else:
            # The operator turned off Secrets Manager wiring (e.g. set
            # ``--no-secrets-manager``). Tear down any stale inline
            # policy from a prior deploy so the role doesn't carry
            # privileges it no longer needs.
            try:
                iam.delete_role_policy(
                    RoleName=role_name, PolicyName="ReadZscalerSecrets"
                )
                info("Removed stale Zscaler-secret read policy.")
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
                    warn(f"Could not remove ReadZscalerSecrets: {e}")
        return role_arn
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise

    info(f"Creating ECS task execution role: {role_name}")
    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(_ecs_task_execution_role_trust_policy()),
        Description="Task execution role for Zscaler MCP ECS Express service",
        Tags=[
            {"Key": "managed-by", "Value": "zscaler-mcp-harness"},
            {"Key": "integration", "Value": "harness"},
        ],
    )
    role_arn = resp["Role"]["Arn"]
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn=AWS_MANAGED_POLICY_ECS_TASK_EXECUTION,
    )
    if cross_account_policy is not None:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="CrossAccountEcrPull",
            PolicyDocument=json.dumps(cross_account_policy),
        )
    if secret_policy is not None:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="ReadZscalerSecrets",
            PolicyDocument=json.dumps(secret_policy),
        )
    sp = Spinner("Waiting for IAM role propagation (≈10s)").start()
    time.sleep(10)
    sp.stop(f"{GREEN}[OK]{NC}    Role propagated.")
    ok(f"Created ECS task execution role: {role_arn}")
    return role_arn


def delete_ecs_task_execution_role(sess: boto3.Session, role_name: str) -> None:
    iam = sess.client("iam")
    try:
        iam.detach_role_policy(
            RoleName=role_name,
            PolicyArn=AWS_MANAGED_POLICY_ECS_TASK_EXECUTION,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("NoSuchEntity",):
            warn(f"Could not detach managed policy: {e}")
    for policy_name in ("CrossAccountEcrPull", "ReadZscalerSecrets"):
        try:
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code != "NoSuchEntity":
                warn(f"Could not delete inline policy {policy_name}: {e}")
    try:
        iam.delete_role(RoleName=role_name)
        ok(f"Deleted ECS task execution role: {role_name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "NoSuchEntity":
            info(f"ECS task execution role {role_name} already absent.")
        else:
            warn(f"Could not delete ECS task execution role {role_name}: {e}")


# ── IAM: ECS Express Mode infrastructure role ────────────────────────────
# Trusts ecs.amazonaws.com. AWS-managed
# AmazonECSInfrastructureRoleforExpressGatewayServices covers ALB +
# target group + security group + scaling-policy management. ECS only
# assumes this role during service create/update/delete operations —
# not during runtime.

def _ecs_infrastructure_role_trust_policy() -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def ensure_ecs_infrastructure_role(sess: boto3.Session, role_name: str) -> str:
    iam = sess.client("iam")
    try:
        existing = iam.get_role(RoleName=role_name)
        role_arn = existing["Role"]["Arn"]
        info(f"Reusing existing ECS infrastructure role: {role_arn}")
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=AWS_MANAGED_POLICY_ECS_INFRASTRUCTURE_EXPRESS,
            )
        except ClientError as e:
            warn(f"Could not re-attach managed policy (continuing): {e}")
        return role_arn
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise

    info(f"Creating ECS infrastructure role: {role_name}")
    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(_ecs_infrastructure_role_trust_policy()),
        Description=(
            "Infrastructure role for Zscaler MCP ECS Express service "
            "(manages ALB, target groups, security groups, auto-scaling)"
        ),
        Tags=[
            {"Key": "managed-by", "Value": "zscaler-mcp-harness"},
            {"Key": "integration", "Value": "harness"},
        ],
    )
    role_arn = resp["Role"]["Arn"]
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn=AWS_MANAGED_POLICY_ECS_INFRASTRUCTURE_EXPRESS,
    )
    sp = Spinner("Waiting for IAM role propagation (≈10s)").start()
    time.sleep(10)
    sp.stop(f"{GREEN}[OK]{NC}    Role propagated.")
    ok(f"Created ECS infrastructure role: {role_arn}")
    return role_arn


def delete_ecs_infrastructure_role(sess: boto3.Session, role_name: str) -> None:
    iam = sess.client("iam")
    try:
        iam.detach_role_policy(
            RoleName=role_name,
            PolicyArn=AWS_MANAGED_POLICY_ECS_INFRASTRUCTURE_EXPRESS,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code != "NoSuchEntity":
            warn(f"Could not detach managed policy: {e}")
    try:
        iam.delete_role(RoleName=role_name)
        ok(f"Deleted ECS infrastructure role: {role_name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "NoSuchEntity":
            info(f"ECS infrastructure role {role_name} already absent.")
        else:
            warn(f"Could not delete ECS infrastructure role {role_name}: {e}")


# ── ECS cluster (idempotent, tracked-ownership) ──────────────────────────

_HARNESS_CLUSTER_OWNER_TAG_KEY = "managed-by"
_HARNESS_CLUSTER_OWNER_TAG_VALUE = "zscaler-mcp-harness"


def _cluster_is_script_owned(cluster: dict[str, Any]) -> bool:
    """Return True iff the cluster carries our owner tag.

    The tag is the *durable* source of truth for "did THIS script
    create THIS cluster". We use it (not a per-deploy state-file
    boolean) because state booleans forget ownership across deploy
    cycles — concretely, ``destroy --keep-ecs`` followed by a fresh
    ``deploy`` would otherwise leave the cluster marked as
    pre-existing, and the next ``destroy`` would never delete it.
    """
    for tag in cluster.get("tags") or []:
        # ECS tag dict keys are lowercase ``key`` / ``value`` (vs IAM
        # tags which use ``Key`` / ``Value``). Both casings observed
        # in the wild depending on how the tag was attached, so check
        # both.
        k = tag.get("key") or tag.get("Key")
        v = tag.get("value") or tag.get("Value")
        if (
            k == _HARNESS_CLUSTER_OWNER_TAG_KEY
            and v == _HARNESS_CLUSTER_OWNER_TAG_VALUE
        ):
            return True
    return False


def _list_cluster_services_summary(
    sess: boto3.Session, cluster_name: str
) -> tuple[int, list[str]]:
    """Return ``(total_services, sample_names)`` for the cluster.

    Used as a pre-prompt hint when the operator is deciding whether to
    reuse an existing cluster — knowing there's a still-draining
    ``zscaler-mcp-server`` in there tells them "yes, that's the cluster
    where my last deploy lives" so they can pick a fresh name instead.
    Best-effort: a list_services failure returns ``(0, [])`` (the
    prompt then just shows the cluster status without a service
    breakdown).
    """
    ecs = sess.client("ecs")
    arns: list[str] = []
    try:
        paginator = ecs.get_paginator("list_services")
        for page in paginator.paginate(cluster=cluster_name):
            arns.extend(page.get("serviceArns") or [])
    except ClientError:
        return 0, []
    names = [arn.rsplit("/", 1)[-1] for arn in arns]
    return len(names), names[:5]


def resolve_ecs_cluster_name(
    sess: boto3.Session,
    requested: str,
    *,
    default_name: str,
) -> str:
    """Interactive cluster-name resolution with three escape hatches.

    The script's default cluster name is ``zscaler-mcp``. When an
    operator runs ``deploy`` without ``--ecs-cluster-name``, the bare
    default would collide with any prior deploy's leftover cluster —
    which is fine on a re-deploy but very wrong if they actually
    wanted a fresh cluster. This resolver makes the decision explicit:

    1. **Operator passed a non-default name** (``--ecs-cluster-name foo``)
       → no prompt. They're already telling us what to use.
    2. **Default name + no cluster exists** → use the default silently.
    3. **Default name + cluster exists** → prompt with three options:

       - Reuse the existing cluster (default — common re-deploy case)
       - Auto-generate a new name like ``zscaler-mcp-<6-hex>``
         (when the old cluster is still draining and we need
         somewhere fresh)
       - Operator provides a custom name interactively

    Returns the resolved cluster name to feed into
    ``ensure_ecs_cluster``.
    """
    # Case 1: explicit override → trust the operator, but print a hint
    # if the cluster exists so they have context.
    if requested != default_name:
        ecs = sess.client("ecs")
        try:
            desc = ecs.describe_clusters(
                clusters=[requested], include=["TAGS"]
            )
            for c in desc.get("clusters", []) or []:
                if c.get("status") == "ACTIVE":
                    owned = _cluster_is_script_owned(c)
                    info(
                        f"ECS cluster '{requested}' already exists "
                        f"({'script-owned' if owned else 'pre-existing'}) — "
                        "will be reused per your --ecs-cluster-name flag."
                    )
                    break
        except ClientError:
            pass
        return requested

    # Cases 2 + 3: default name, check existence
    ecs = sess.client("ecs")
    try:
        desc = ecs.describe_clusters(
            clusters=[requested], include=["TAGS"]
        )
    except ClientError:
        return requested  # describe failed → fall through, ensure_ecs_cluster will retry
    active = [
        c for c in (desc.get("clusters") or [])
        if c.get("status") == "ACTIVE"
    ]
    if not active:
        # Case 2: nothing in the way, use the default silently
        return requested

    # Case 3: existing cluster, surface context + prompt
    cluster = active[0]
    owned = _cluster_is_script_owned(cluster)
    info(f"ECS cluster '{requested}' already exists (status: ACTIVE)")
    if owned:
        info(
            "  Owner tag: managed-by=zscaler-mcp-harness "
            "(previous deploy of this script — safe to reuse)"
        )
    else:
        info(
            "  Owner tag: none (pre-existing or operator-managed — "
            "destroy will NOT delete it)"
        )

    svc_count, svc_sample = _list_cluster_services_summary(sess, requested)
    if svc_count:
        info(f"  Services currently in the cluster: {svc_count}")
        for name in svc_sample:
            info(f"    - {name}")
        if svc_count > len(svc_sample):
            info(f"    … and {svc_count - len(svc_sample)} more")
        info(
            "  Note: ECS hides DRAINING services from list_services. If "
            "your last destroy was recent, the count may be lower than "
            "what's actually still tearing down in the background."
        )
    else:
        info("  Services currently in the cluster: 0 (cluster is empty)")

    print()
    choices = [
        f"Reuse the existing cluster '{requested}' (recommended for re-deploys)",
        f"Create a new cluster with an auto-generated name ({requested}-<random>)",
        "Create a new cluster with a custom name I'll provide",
    ]
    idx = prompt_choice(
        "How would you like to handle the existing cluster?",
        choices,
        default_idx=0,
    )

    if idx == 0:
        return requested
    if idx == 1:
        # 6-char hex is short enough to read but wide enough (16M
        # combinations) that collisions in the same account are
        # effectively impossible.
        suffix = secrets.token_hex(3)
        new_name = f"{requested}-{suffix}"
        info(f"Will create new cluster: {new_name}")
        return new_name

    # Custom name — loop until a valid, non-conflicting name is entered.
    while True:
        candidate = prompt("New cluster name (letters, digits, _, -; max 255 chars)").strip()
        if not candidate:
            warn("Cluster name cannot be empty — try again.")
            continue
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,254}$", candidate):
            warn(
                "Invalid cluster name. Must start with a letter or digit "
                "and contain only letters, digits, hyphens, and underscores "
                "(max 255 chars total)."
            )
            continue
        if candidate == requested:
            warn(
                "That's the same name as the existing cluster. To reuse "
                "it, restart and pick option 1; otherwise enter a "
                "different name."
            )
            continue
        # Optional: warn if the chosen custom name ALSO already exists
        try:
            check = ecs.describe_clusters(clusters=[candidate])
            for c in check.get("clusters", []) or []:
                if c.get("status") == "ACTIVE":
                    warn(
                        f"Cluster '{candidate}' already exists too. "
                        "Pick a different name or hit Ctrl-C and re-run "
                        "with --ecs-cluster-name <name> to bypass this prompt."
                    )
                    break
            else:
                return candidate
            continue
        except ClientError:
            return candidate


def ensure_ecs_cluster(sess: boto3.Session, cluster_name: str) -> tuple[str, bool]:
    """Create or reuse an ECS cluster, with tag-based ownership detection.

    Returns ``(cluster_arn, owned_by_us)``. The boolean is sourced from
    the cluster's tags — specifically ``managed-by=zscaler-mcp-harness``,
    which ``create_cluster`` always attaches when the script creates a
    new cluster. This survives ``destroy --keep-ecs`` → ``deploy`` →
    ``destroy`` cycles where a per-process state boolean would lose
    ownership context.

    Three additional safety nets:

    1. ``DEPROVISIONING`` cluster (mid-destroy from a prior run): fail
       with a clear message instead of letting ``create_cluster`` throw
       ``ClusterAlreadyExistsException`` 30s later.
    2. ``PROVISIONING`` cluster (concurrent deploy in progress): same
       — fail fast.
    3. ``FAILED`` cluster: warn but treat as deletable + retry create.
       ECS leaves clusters in FAILED if the initial CreateCluster
       returned but the underlying provisioning bombed.
    """
    ecs = sess.client("ecs")
    desc = ecs.describe_clusters(
        clusters=[cluster_name],
        include=["TAGS"],
    )
    for cluster in desc.get("clusters", []) or []:
        status = cluster.get("status")
        if status == "ACTIVE":
            owned = _cluster_is_script_owned(cluster)
            tag_note = (
                "tagged managed-by=zscaler-mcp-harness — will be deleted on destroy"
                if owned
                else "no owner tag — pre-existing cluster, will be preserved on destroy"
            )
            info(f"Reusing existing ECS cluster: {cluster_name} ({tag_note})")
            return cluster["clusterArn"], owned
        if status in ("PROVISIONING", "DEPROVISIONING"):
            err(
                f"ECS cluster {cluster_name} is currently {status} — another "
                "deploy or destroy is in flight. Wait for it to settle "
                "(usually 1–3 min), or use --ecs-cluster-name to pick a "
                "different cluster for this deployment. Inspect with: "
                f"aws ecs describe-clusters --clusters {cluster_name}"
            )
            sys.exit(1)
        if status == "FAILED":
            warn(
                f"ECS cluster {cluster_name} is in FAILED state from a "
                "previous deploy. Deleting it and recreating."
            )
            try:
                ecs.delete_cluster(cluster=cluster_name)
            except ClientError as e:
                warn(f"Could not delete FAILED cluster (continuing): {e}")
        # status == "INACTIVE" (deleted) or unknown — fall through to create
    info(f"Creating ECS cluster: {cluster_name}")
    resp = ecs.create_cluster(
        clusterName=cluster_name,
        tags=[
            {
                "key": _HARNESS_CLUSTER_OWNER_TAG_KEY,
                "value": _HARNESS_CLUSTER_OWNER_TAG_VALUE,
            },
            {"key": "integration", "value": "harness"},
        ],
    )
    arn = resp["cluster"]["clusterArn"]
    ok(f"Created ECS cluster: {arn}")
    return arn, True


def delete_ecs_cluster(
    sess: boto3.Session, cluster_name: str, max_wait_s: int = 180
) -> None:
    """Delete an ECS cluster, tolerating slow ECS Express tear-down.

    ECS Express's ``delete_express_gateway_service`` returns once the
    *service* is marked INACTIVE, but the underlying ALB, target groups,
    and (occasionally) task-instances continue tearing down asynchronously
    in the background. A cluster delete that races into that tail returns
    ``ClusterContainsServicesException`` even though the service we
    deleted no longer shows up in ``list_services``. Retry every 15s for
    up to ``max_wait_s`` so a normal deploy/destroy/deploy loop doesn't
    leave the cluster orphaned in the console.
    """
    ecs = sess.client("ecs")
    deadline = time.time() + max_wait_s
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            ecs.delete_cluster(cluster=cluster_name)
            ok(f"Deleted ECS cluster: {cluster_name}")
            return
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            last_err = e
            if code == "ClusterNotFoundException":
                info(f"ECS cluster {cluster_name} already absent.")
                return
            if code in (
                "ClusterContainsServicesException",
                "ClusterContainsTasksException",
                "ClusterContainsContainerInstancesException",
                "ResourceInUseException",
            ):
                info(
                    f"Cluster {cluster_name} still draining ({code}); "
                    "retrying in 15s…"
                )
                time.sleep(15)
                continue
            warn(f"Could not delete ECS cluster {cluster_name}: {e}")
            return
    warn(
        f"Could not delete ECS cluster {cluster_name} within {max_wait_s}s. "
        f"Last error: {last_err}. Inspect with `aws ecs list-services "
        f"--cluster {cluster_name}` and delete the cluster manually once "
        "it shows zero services + tasks."
    )


def deregister_and_delete_task_definitions(
    sess: boto3.Session,
    family: str,
) -> None:
    """Tear down every revision of an ECS task-definition family.

    ECS Express auto-registers a new task-definition revision on every
    create / update. Plain ``delete_express_gateway_service`` does NOT
    deregister these — they survive as ACTIVE task definitions at the
    AWS account level, accumulating across deploy cycles and cluttering
    the ECS console (``zscaler-mcp-zscaler-mcp-server:17``,
    ``…:18``, …). They don't *block* cluster deletion, but they're stale
    state the operator has to clean up manually otherwise.

    Two-step lifecycle per AWS:

    * ``deregister_task_definition`` marks each revision INACTIVE
      (transition is reversible — INACTIVE definitions are still visible
      in the console + listable for historical audit).
    * ``delete_task_definitions`` permanently removes the INACTIVE rows
      so they stop showing up in default-filtered lists. Batched at 10
      per call (AWS hard limit).

    Best-effort: a per-revision failure logs a warning and moves on.
    """
    ecs = sess.client("ecs")

    try:
        paginator = ecs.get_paginator("list_task_definitions")
        arns: list[str] = []
        for page in paginator.paginate(
            familyPrefix=family,
            status="ACTIVE",
        ):
            arns.extend(page.get("taskDefinitionArns") or [])
    except ClientError as e:
        warn(f"Could not list task definitions for family {family}: {e}")
        return

    if not arns:
        info(f"No task definitions left for family {family}.")
        return

    info(
        f"Deregistering {len(arns)} task-definition revision(s) "
        f"for family {family}…"
    )
    deregistered: list[str] = []
    for arn in arns:
        try:
            ecs.deregister_task_definition(taskDefinition=arn)
            deregistered.append(arn)
        except ClientError as e:
            warn(f"Could not deregister {arn}: {e}")

    if not deregistered:
        return

    info(
        f"Permanently deleting {len(deregistered)} task-definition "
        "revision(s)…"
    )
    for i in range(0, len(deregistered), 10):
        chunk = deregistered[i : i + 10]
        try:
            ecs.delete_task_definitions(taskDefinitions=chunk)
        except ClientError as e:
            warn(f"Could not delete task definitions batch {chunk[0]}…: {e}")
    ok(f"Cleaned up task definitions for family {family}.")


# ── CloudWatch log group (created up front so the container can stream) ──

def ensure_cloudwatch_log_group(sess: boto3.Session, log_group_name: str) -> None:
    logs = sess.client("logs")
    try:
        logs.create_log_group(logGroupName=log_group_name)
        ok(f"Created log group: {log_group_name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ResourceAlreadyExistsException":
            info(f"Reusing existing log group: {log_group_name}")
            return
        warn(f"Could not create log group {log_group_name}: {e}")


def delete_cloudwatch_log_group(sess: boto3.Session, log_group_name: str) -> None:
    logs = sess.client("logs")
    try:
        logs.delete_log_group(logGroupName=log_group_name)
        ok(f"Deleted log group: {log_group_name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            info(f"Log group {log_group_name} already absent.")
        else:
            warn(f"Could not delete log group {log_group_name}: {e}")


# ── AgentCore Harness logs are auto-managed ──────────────────────────
# Harness runs on an auto-provisioned AgentCore Runtime that AWS owns
# and that writes its APPLICATION_LOGS to
#   /aws/bedrock-agentcore/runtimes/<runtime-id>
# directly — there's no vendedLogs `PutDeliverySource` wiring required
# (and in fact `harness` is not a valid resourceArn type for
# PutDeliverySource; only [code-interpreter, memory, payment-manager,
# workload-identity, code-interpreter-custom, runtime, gateway] are).
# cmd_logs locates the auto-managed group at tail time by scanning for
# the harness_id under that prefix.


# ── Container env-var assembly (identical values regardless of host) ─────

# Whitelist of env-var name PREFIXES we forward from the operator's
# .env into the container. Everything outside these prefixes (AWS_*,
# MCP_URL, MODEL_ID, etc.) is consumed by the deploy script itself and
# has no business reaching the MCP server.
_FORWARDED_ENV_PREFIXES: tuple[str, ...] = (
    "ZSCALER_",
    "FASTMCP_",
    "MCP_",  # excludes MCP_URL which is a script-only key (we strip it)
)
# Keys that match a forwarded prefix but should still be stripped
# because they're for the deploy script, not the MCP server.
_DEPLOY_ONLY_KEYS: frozenset[str] = frozenset({
    "ZSCALER_MCP_IMAGE_URI",   # tells the script which image to deploy
    "MCP_URL",                  # tells the script to skip ECS Express
})

# Minimum operational env vars the container needs to *bind correctly*
# behind the ECS Express ALB. We only inject these when the operator
# hasn't supplied their own. None of them are credentials or auth.
_ECS_EXPRESS_TOPOLOGY_DEFAULTS: tuple[tuple[str, str], ...] = (
    ("ZSCALER_MCP_TRANSPORT", "streamable-http"),
    ("ZSCALER_MCP_HOST", "0.0.0.0"),
    ("ZSCALER_MCP_PORT", str(DEFAULT_CONTAINER_PORT)),
)


def _build_container_secrets(
    secret_arn: str, secret_keys: list[str]
) -> list[dict[str, str]]:
    """Return the ``primaryContainer.secrets`` block for ECS Express.

    The ECS Agent (which has ``executionRoleArn`` credentials) fetches
    the Secrets Manager secret, parses the JSON, and injects the named
    key as a plain env var into the container BEFORE the container
    starts. The container's process then sees ``os.environ[key]`` as
    if it had been passed as a regular env var — no boto3, no runtime
    IAM credentials needed inside the container.

    ECS Express's ``valueFrom`` syntax for projecting individual JSON
    keys out of a Secrets Manager secret is::

        <secret-arn>:<json-key>:<version-stage>:<version-id>

    Trailing empty ``::`` means "latest version, no stage" — what we
    want for credential rotation to "just work" without redeploying
    the task definition. AWS docs:
    https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-secrets.html#secrets-app-mesh-json
    """
    return [
        {"name": k, "valueFrom": f"{secret_arn}:{k}::"}
        for k in secret_keys
    ]


def _build_container_env_vars(
    env: dict[str, str],
    *,
    discovered_host: Optional[str] = None,
    secret_keys: Optional[list[str]] = None,
) -> list[dict[str, str]]:
    """Forward the operator's ``.env`` to the container, verbatim.

    Behaviour (matches integrations/aws/bedrock-agentcore policy):

    * Every key starting with ``ZSCALER_``, ``FASTMCP_``, or ``MCP_``
      from the resolved ``.env`` is forwarded to the container exactly
      as the operator wrote it. The script does **not** invent auth,
      transport, host-validation, or write-tool defaults — if a value
      isn't in ``.env``, it isn't in the container.
    * Two deploy-time-only keys (``ZSCALER_MCP_IMAGE_URI``, ``MCP_URL``)
      are stripped because they configure the deploy script itself, not
      the MCP server.
    * The bare minimum ECS Express topology defaults
      (``ZSCALER_MCP_TRANSPORT=streamable-http``, ``ZSCALER_MCP_HOST=0.0.0.0``,
      ``ZSCALER_MCP_PORT=8000``) are added **only when the operator
      didn't set them themselves** — without these three the container
      can't even bind to the ALB target. The operator can still override
      any of them by setting that var in their ``.env``.

    The single argument ``env`` is the dict returned by
    ``_load_env_file`` (or a merged copy). The function is intentionally
    independent of ``argparse.Namespace`` so credentials passed only via
    ``--client-id`` / ``--client-secret`` flags don't leak into the
    container (we keep CLI overrides scoped to the deploy script's own
    AWS API calls — Token Vault credential provider, etc.).

    ``discovered_host`` is the AWS-generated ECS Express FQDN (e.g.
    ``zs-<hash>.ecs.us-east-1.on.aws``) — known *only* after the service
    is provisioned. When supplied, the FQDN is **merged into**
    ``ZSCALER_MCP_ALLOWED_HOSTS`` (deduplicating against whatever the
    operator already set, preserving every other entry). This is not
    optional: AWS mints the FQDN at provision time so the operator
    physically cannot put it in ``.env``, and without it FastMCP's
    DNS-rebinding guard rejects every Harness POST with ``421
    Misdirected Request``. Common operator entries like
    ``127.0.0.1:*,localhost:*`` (the boilerplate that ships in
    ``env.properties``) are kept verbatim and the FQDN is appended.

    The single way to opt out of host validation is
    ``ZSCALER_MCP_DISABLE_HOST_VALIDATION=true`` — that fully disables
    the guard and we touch nothing.

    ``secret_keys`` enables Secrets Manager wiring: the listed keys are
    **stripped** from the forwarded env (they'll come in via the ECS
    task definition's ``secrets:`` block instead — see
    ``_build_container_secrets``). The ECS agent injects them as
    regular env vars before the container starts, so the SDK still
    sees ``os.environ['ZSCALER_CLIENT_SECRET']`` etc. — but the values
    never appear in the task definition, CloudTrail
    ``RegisterTaskDefinition`` events, or ``aws ecs
    describe-task-definition`` output. ``ZSCALER_SECRET_NAME`` is NOT
    set in the container env (we don't want ``zscaler_mcp.config``'s
    runtime boto3 fetch to fire — ECS Express tasks have no IAM
    credentials inside the container by default; the secrets:[]
    pattern works because the ECS *agent* does the fetch using
    ``executionRoleArn``, which we already grant).

    When ``secret_keys`` is None or empty the legacy behaviour
    (plaintext env) is preserved for ``--no-secrets-manager`` opt-out.

    ECS Express primaryContainer.environment uses lowercase ``name`` /
    ``value`` keys (vs. App Runner's ``Name`` / ``Value``).
    """
    forwarded: dict[str, str] = {}
    for key, value in env.items():
        if key in _DEPLOY_ONLY_KEYS:
            continue
        if not key.startswith(_FORWARDED_ENV_PREFIXES):
            continue
        v = (value or "").strip()
        if not v or v == "NOT_SET":
            continue
        forwarded[key] = v

    if secret_keys:
        for key in secret_keys:
            forwarded.pop(key, None)
        # Defensive: also strip any leftover ZSCALER_SECRET_NAME that
        # might've been in .env (e.g. from a config that previously
        # used the runtime-boto3 pattern). Avoids triggering
        # zscaler_mcp.config's boto3 fetch which would fail with
        # NoCredentialsError inside ECS Express.
        forwarded.pop("ZSCALER_SECRET_NAME", None)

    for key, default_value in _ECS_EXPRESS_TOPOLOGY_DEFAULTS:
        forwarded.setdefault(key, default_value)

    if discovered_host:
        user_set_disable = (
            forwarded.get("ZSCALER_MCP_DISABLE_HOST_VALIDATION", "").lower()
            in ("true", "1", "yes")
        )
        if not user_set_disable:
            existing = forwarded.get("ZSCALER_MCP_ALLOWED_HOSTS", "").strip()
            entries = [h.strip() for h in existing.split(",") if h.strip()]
            if discovered_host not in entries:
                entries.insert(0, discovered_host)
            if not any(h == "127.0.0.1:*" for h in entries):
                entries.append("127.0.0.1:*")
            if not any(h == "localhost:*" for h in entries):
                entries.append("localhost:*")
            forwarded["ZSCALER_MCP_ALLOWED_HOSTS"] = ",".join(entries)

    return [{"name": k, "value": v} for k, v in forwarded.items()]


# ── ECS Express Mode service lifecycle ───────────────────────────────────

def _ecs_service_public_endpoint(service: dict[str, Any]) -> Optional[str]:
    """Pluck the PUBLIC ingress endpoint out of a DescribeExpressGatewayService
    response. ECS Express returns a list of ingress paths (PUBLIC vs PRIVATE);
    we want the public one for Harness to consume."""
    configs = service.get("activeConfigurations") or []
    if not configs:
        return None
    # The list is ordered most-recent-last; use the tail.
    paths = configs[-1].get("ingressPaths") or []
    for p in paths:
        if p.get("accessType") == "PUBLIC" and p.get("endpoint"):
            return p["endpoint"]
    return None


def discover_ecs_express_service(
    sess: boto3.Session, cluster_name: str, service_name: str
) -> Optional[dict[str, Any]]:
    """Look up an ECS Express service by name within a cluster.

    Returns the full DescribeExpressGatewayService payload, or None.
    ECS doesn't expose a list-by-name primitive on the Express API, so
    we use list_services on the cluster + describe each ARN whose name
    matches.
    """
    ecs = sess.client("ecs")
    paginator = ecs.get_paginator("list_services")
    for page in paginator.paginate(cluster=cluster_name):
        for arn in page.get("serviceArns") or []:
            # ECS service ARNs look like
            # arn:aws:ecs:<r>:<a>:service/<cluster>/<name>
            if arn.rsplit("/", 1)[-1] != service_name:
                continue
            try:
                return ecs.describe_express_gateway_service(serviceArn=arn).get("service")
            except ClientError as e:
                # If this happens, the ARN belongs to a classic ECS service
                # that lives alongside an Express deployment with the same
                # name — let the caller surface the conflict.
                code = e.response.get("Error", {}).get("Code", "")
                if code in ("InvalidParameterException", "ClientException"):
                    warn(
                        f"Service {service_name} exists but is not an "
                        f"Express Mode service: {e}"
                    )
                    return None
                raise
    return None


def _verify_image_supports_amd64(sess: boto3.Session, image_uri: str) -> None:
    """Warn if `image_uri` lacks an amd64 variant — fast-fails the
    classic Apple-Silicon footgun where a developer's local
    `docker build` produces an arm64-only image, pushes it to ECR, and
    every ECS task then crashes with
        exec /usr/local/bin/python: exec format error
    nine seconds after starting. Only ECR images are inspectable from
    here (we'd need the registry's pull token to introspect anything
    else); the check is opportunistic — for non-ECR registries it just
    logs an INFO line and continues. Always non-fatal: a false positive
    must never block a deploy.
    """
    if ".dkr.ecr." not in image_uri or "amazonaws.com" not in image_uri:
        info(
            f"Skipping image-arch check (not an ECR URI): {image_uri}. "
            "Make sure your image manifest includes linux/amd64."
        )
        return

    try:
        host_and_path, _, tag = image_uri.partition(":")
        tag = tag or "latest"
        registry, _, repo_path = host_and_path.partition("/")
        if not repo_path or not registry:
            return
        region = registry.split(".")[3] if registry.count(".") >= 5 else None
        ecr = sess.client("ecr", region_name=region) if region else sess.client("ecr")
        resp = ecr.batch_get_image(
            repositoryName=repo_path,
            imageIds=[{"imageTag": tag}],
            acceptedMediaTypes=[
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.oci.image.index.v1+json",
            ],
        )
        images = resp.get("images") or []
        if not images:
            return
        manifest_json = images[0].get("imageManifest", "")
        manifest = json.loads(manifest_json) if manifest_json else {}
        # Multi-arch (manifest list / image index) — look at each entry.
        archs: list[str] = []
        if "manifests" in manifest:
            for m in manifest["manifests"]:
                plat = m.get("platform") or {}
                arch = plat.get("architecture")
                if arch:
                    archs.append(arch)
        else:
            # Single-arch v2 manifest — architecture lives on the config
            # blob, not the manifest. The manifest's mediaType + digest
            # don't directly expose it, so we fall back to ECR's
            # `describe-images` for the `imageManifestMediaType` and
            # leave the arch field empty if we can't tell. The simplest
            # heuristic that works in practice: any single-arch image
            # pushed from Apple Silicon without --platform comes out
            # arm64, so an absent manifest-list is suspicious enough to
            # warn about — but not to fail.
            describe = ecr.describe_images(
                repositoryName=repo_path, imageIds=[{"imageTag": tag}]
            )
            details = (describe.get("imageDetails") or [{}])[0]
            archs = details.get("imageArchitectures") or []
        archs_lower = [a.lower() for a in archs]
        if "amd64" in archs_lower:
            info(f"Image arch check OK — {image_uri} includes amd64 (archs: {archs_lower}).")
            return
        if archs_lower:
            warn(
                f"Image {image_uri} manifest lists {archs_lower} but NO amd64. "
                "ECS Fargate runs amd64 by default and the task will exit 255 "
                "with `exec format error` ~9 seconds after start. Rebuild via:\n"
                f"  make docker-build-multiarch IMAGE={image_uri}\n"
                "(see integrations/aws/harness/README.md → Troubleshooting)."
            )
        else:
            info(
                f"Could not determine architectures for {image_uri}; "
                "if the task crash-loops with `exec format error`, rebuild "
                "with `make docker-build-multiarch IMAGE=<uri>`."
            )
    except ClientError as e:
        # Permission gaps on ECR Describe/BatchGet are common in
        # restricted dev accounts. Don't block on them.
        info(f"Skipping image-arch check (ECR call failed: {e}).")
    except Exception as e:  # noqa: BLE001 — never let a warning kill deploy
        info(f"Skipping image-arch check ({e}).")


def provision_ecs_express_service(
    sess: boto3.Session,
    *,
    cluster_name: str,
    service_name: str,
    image_uri: str,
    execution_role_arn: str,
    infrastructure_role_arn: str,
    log_group: str,
    env_vars: list[dict[str, str]],
    health_check_path: str,
    secrets: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    ecs = sess.client("ecs")
    _verify_image_supports_amd64(sess, image_uri)
    existing = discover_ecs_express_service(sess, cluster_name, service_name)
    if existing:
        status = (existing.get("status") or {}).get("statusCode")
        active = existing.get("activeConfigurations") or []
        cur_image = (
            active[-1].get("primaryContainer", {}).get("image", "") if active else ""
        )
        cur_health = (
            active[-1].get("healthCheckPath", "") if active else ""
        )
        # If anything material changed (image, healthCheckPath, env vars) the
        # service needs a rolling update — otherwise the ALB will keep probing
        # the old path or the container will keep running the old image. ECS
        # Express handles this as a zero-downtime rolling deployment. We
        # intentionally don't compare env vars line-by-line here: env-only
        # changes are rare and the update API is idempotent, so we only
        # update when image OR health-check path drifted (the two we KNOW
        # break the deployment in practice).
        cur_secrets = (
            active[-1].get("primaryContainer", {}).get("secrets", []) if active else []
        )
        # Normalise both sides to name→valueFrom dicts so list-order doesn't
        # cause spurious updates.
        cur_secrets_map = {
            s.get("name"): s.get("valueFrom") for s in (cur_secrets or [])
        }
        desired_secrets_map = {
            s["name"]: s["valueFrom"] for s in (secrets or [])
        }
        secrets_drift = cur_secrets_map != desired_secrets_map
        if cur_image != image_uri or cur_health != health_check_path or secrets_drift:
            reasons = []
            if cur_image and cur_image != image_uri:
                reasons.append(f"image: {cur_image} → {image_uri}")
            if cur_health and cur_health != health_check_path:
                reasons.append(
                    f"healthCheckPath: {cur_health} → {health_check_path}"
                )
            if secrets_drift:
                reasons.append(
                    f"secrets[]: {len(cur_secrets_map)} → {len(desired_secrets_map)} entries"
                )
            info(
                f"Updating ECS Express service {service_name} "
                f"(status={status}): " + "; ".join(reasons)
            )
            primary_container: dict[str, Any] = {
                "image": image_uri,
                "containerPort": DEFAULT_CONTAINER_PORT,
                "awsLogsConfiguration": {
                    "logGroup": log_group,
                    "logStreamPrefix": DEFAULT_ECS_LOG_STREAM_PREFIX,
                },
                "environment": env_vars,
            }
            if secrets:
                primary_container["secrets"] = secrets
            try:
                ecs.update_express_gateway_service(
                    serviceArn=existing["serviceArn"],
                    executionRoleArn=execution_role_arn,
                    healthCheckPath=health_check_path,
                    primaryContainer=primary_container,
                )
            except ClientError as e:
                err(f"UpdateExpressGatewayService failed: {e}")
                raise
            ok("UpdateExpressGatewayService submitted; rolling deployment in progress")
            return poll_ecs_express_active(sess, existing["serviceArn"])

        info(
            f"Reusing existing ECS Express service: {service_name} "
            f"(status={status}, image and healthCheckPath unchanged)"
        )
        return existing

    info(f"Creating ECS Express service: {service_name}")
    info(f"  cluster: {cluster_name}")
    info(f"  image:   {image_uri}")
    info(f"  cpu/mem: {DEFAULT_ECS_CPU} / {DEFAULT_ECS_MEMORY}")
    if secrets:
        info(f"  secrets[]: {len(secrets)} entries projected from Secrets Manager")
    primary_container: dict[str, Any] = {
        "image": image_uri,
        "containerPort": DEFAULT_CONTAINER_PORT,
        "awsLogsConfiguration": {
            "logGroup": log_group,
            "logStreamPrefix": DEFAULT_ECS_LOG_STREAM_PREFIX,
        },
        "environment": env_vars,
    }
    if secrets:
        primary_container["secrets"] = secrets
    try:
        resp = ecs.create_express_gateway_service(
            executionRoleArn=execution_role_arn,
            infrastructureRoleArn=infrastructure_role_arn,
            serviceName=service_name,
            cluster=cluster_name,
            healthCheckPath=health_check_path,
            primaryContainer=primary_container,
            cpu=DEFAULT_ECS_CPU,
            memory=DEFAULT_ECS_MEMORY,
            tags=[
                {"key": "managed-by", "value": "zscaler-mcp-harness"},
                {"key": "integration", "value": "harness"},
            ],
        )
    except ClientError as e:
        err(f"CreateExpressGatewayService failed: {e}")
        raise
    svc = resp["service"]
    ok(f"CreateExpressGatewayService submitted. ServiceArn = {svc['serviceArn']}")
    return poll_ecs_express_active(sess, svc["serviceArn"])


def poll_ecs_express_active(
    sess: boto3.Session, service_arn: str, timeout_s: int = 900
) -> dict[str, Any]:
    ecs = sess.client("ecs")
    sp = Spinner("Waiting for ECS Express service to reach ACTIVE").start()
    deadline = time.time() + timeout_s
    last: dict[str, Any] = {}
    while time.time() < deadline:
        try:
            last = ecs.describe_express_gateway_service(serviceArn=service_arn).get(
                "service", {}
            )
        except ClientError as e:
            sp.stop()
            err(f"DescribeExpressGatewayService failed: {e}")
            return last
        status = (last.get("status") or {}).get("statusCode", "UNKNOWN")
        # The service surfaces a stable PUBLIC ingress endpoint once the
        # ALB + target group come up, even if the underlying task is
        # still warming. Wait for ACTIVE *and* a non-empty endpoint so
        # the URL we hand to Harness is actually reachable.
        endpoint = _ecs_service_public_endpoint(last)
        if status == "ACTIVE" and endpoint:
            sp.stop(f"{GREEN}[OK]{NC}    ECS Express status = {status}")
            return last
        if status == "INACTIVE":
            sp.stop(f"{RED}[ERROR]{NC} ECS Express status = INACTIVE")
            return last
        time.sleep(10)
    sp.stop(
        f"{YELLOW}[WARN]{NC}  Timed out waiting for ACTIVE. "
        f"Last status = {(last.get('status') or {}).get('statusCode')}"
    )
    return last


# ──────────────────────────────────────────────────────────────────────────
# Secrets Manager — Zscaler OneAPI credentials
# ──────────────────────────────────────────────────────────────────────────
#
# Why this exists: prior to PR-pending, ``_build_container_env_vars`` wrote
# ``ZSCALER_CLIENT_SECRET`` (and ``ZSCALER_CLIENT_ID`` / ``ZSCALER_CUSTOMER_ID``
# / ``ZSCALER_VANITY_DOMAIN`` / ``ZSCALER_CLOUD``) straight into the ECS task
# definition's ``environment`` block as plaintext. Every operator with
# ``ecs:DescribeTaskDefinition`` could read the secret, and every CloudTrail
# event for ``RegisterTaskDefinition`` / ``CreateExpressGatewayService`` /
# ``UpdateExpressGatewayService`` recorded the cleartext value.
#
# The fix is to mirror what ``integrations/aws/bedrock-agentcore``'s
# CloudFormation already does: stash the 5-key JSON blob in Secrets Manager,
# put **only** the secret's name in the task env, and let the container's
# pre-existing ``zscaler_mcp.config`` module (already in the image) fetch +
# inject the values via boto3 at process boot. ECS Express's container picks
# up its IAM credentials from the *execution* role (no separate task-role
# slot on Express), so ``ensure_ecs_task_execution_role`` is also extended
# with a scoped ``secretsmanager:GetSecretValue`` + ``kms:Decrypt``.

def _zscaler_secret_payload(env: dict[str, str]) -> dict[str, str]:
    """Pluck the 5 Zscaler credential keys out of the resolved env.

    Returned dict has the **exact** ZSCALER_* env-var names — that's the
    contract ``zscaler_mcp/config.py`` expects: it iterates the parsed
    JSON and calls ``os.environ[key] = value`` for every entry. Keys
    missing from ``env`` are simply omitted; the operator may legitimately
    skip ``ZSCALER_CLOUD`` (defaults to production) or ``ZSCALER_CUSTOMER_ID``
    (only required for ZPA tools).
    """
    return {
        key: env[key]
        for key in _ZSCALER_CRED_ENV_KEYS
        if env.get(key)
    }


def _read_secret_json_keys(
    sess: boto3.Session, secret_id: str
) -> list[str]:
    """Read the secret's JSON, return its top-level key list.

    Used to figure out which ``ZSCALER_*`` env vars to project via the
    ECS task definition's ``secrets:`` block. We can't declare a
    ``secrets[]`` entry for a key the secret doesn't actually have —
    the ECS agent would fail at task start with a clear-but-unfriendly
    error. Filter to only the canonical Zscaler keys present in the
    JSON object.
    """
    sm = sess.client("secretsmanager")
    try:
        resp = sm.get_secret_value(SecretId=secret_id)
    except ClientError as e:
        warn(
            f"Could not GetSecretValue on {secret_id} to enumerate keys: {e}. "
            "Falling back to the canonical ZSCALER_CLIENT_ID + CLIENT_SECRET "
            "key set; if your secret JSON uses different key names the "
            "task will fail at startup with a clear ECS agent error."
        )
        return ["ZSCALER_CLIENT_ID", "ZSCALER_CLIENT_SECRET"]
    raw = resp.get("SecretString")
    if not raw:
        warn(f"Secret {secret_id} has no SecretString — binary secrets not supported.")
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        warn(
            f"Secret {secret_id} value is not valid JSON ({e}). "
            "Container injection requires a flat JSON object with "
            "ZSCALER_* keys."
        )
        return []
    if not isinstance(parsed, dict):
        warn(f"Secret {secret_id} JSON is not an object; cannot project keys.")
        return []
    return [k for k in parsed.keys() if k in _ZSCALER_CRED_ENV_KEYS]


def ensure_zscaler_secret(
    sess: boto3.Session,
    secret_name: str,
    env: dict[str, str],
    *,
    reuse_existing: bool,
) -> tuple[str, str, list[str]]:
    """Resolve a Zscaler credentials secret. Returns ``(name, arn, keys_in_secret)``.

    Mirrors the bedrock-agentcore CloudFormation pattern (see
    ``integrations/aws/bedrock-agentcore/cloudformation/secrets.yaml``):
    two modes, no value-rotation gymnastics, no soft-delete dance.

    * ``reuse_existing=True`` — operator already created the secret
      out-of-band (Terraform / CloudFormation / console). ``.env`` only
      tells us its name via ``ZSCALER_SECRET_NAME``. We ``DescribeSecret``
      to capture the ARN, ``GetSecretValue`` to enumerate which
      ``ZSCALER_*`` keys are present, and reference it. We **never**
      touch the value. We **never** delete it on ``destroy``.

    * ``reuse_existing=False`` — script-managed secret. Two sub-cases:
        - Doesn't exist → ``CreateSecret`` with the payload built from
          ``env``. Tagged ``managed-by=zscaler-mcp-harness`` so a future
          ``destroy`` knows it can remove it.
        - Already exists (because we created it on a prior deploy) →
          reference without overwriting. The credentials live in
          Secrets Manager from now on; ``.env`` is only consulted on
          first create. To rotate, either edit the secret directly
          (``aws secretsmanager put-secret-value``) or run
          ``destroy --force-secret-delete`` then ``deploy`` again.

    The third return element drives the ECS task definition's
    ``secrets:`` block — we can only project keys that ACTUALLY exist
    in the JSON (a missing-key projection would cause ECS to fail the
    task at startup with ``ResourceInitializationError``).
    """
    sm = sess.client("secretsmanager")

    if reuse_existing:
        try:
            desc = sm.describe_secret(SecretId=secret_name)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ResourceNotFoundException":
                err(
                    f"ZSCALER_SECRET_NAME={secret_name} was set in .env but "
                    f"the secret does not exist in Secrets Manager. Either "
                    f"create it first, or remove ZSCALER_SECRET_NAME from "
                    f".env so the script can manage the secret automatically."
                )
                sys.exit(1)
            raise
        if desc.get("DeletedDate") is not None:
            err(
                f"ZSCALER_SECRET_NAME={secret_name} exists but is scheduled "
                f"for deletion (DeletedDate={desc['DeletedDate']}). Restore "
                f"it manually (`aws secretsmanager restore-secret "
                f"--secret-id {secret_name}`) or unset ZSCALER_SECRET_NAME "
                f"so the script can create a fresh one."
            )
            sys.exit(1)
        info(f"Reusing existing Secrets Manager secret: {desc['Name']}")
        info("  (managed externally — value will NOT be overwritten or deleted)")
        keys = _read_secret_json_keys(sess, desc["Name"])
        if not keys:
            err(
                "Could not find any usable ZSCALER_* keys in the secret. "
                "The secret JSON must be a flat object with at least "
                "ZSCALER_CLIENT_ID and ZSCALER_CLIENT_SECRET."
            )
            sys.exit(1)
        info(f"  Keys to project as env vars: {', '.join(keys)}")
        return desc["Name"], desc["ARN"], keys

    # CreateNew mode — the script owns the lifecycle. Three sub-cases:
    #   - Doesn't exist           → CreateSecret from .env
    #   - Exists, soft-deleted    → RestoreSecret + PutSecretValue
    #                               (both instant + atomic — no
    #                               eventual-consistency race like
    #                               ForceDeleteWithoutRecovery has)
    #   - Exists, healthy         → reference without overwriting
    try:
        existing = sm.describe_secret(SecretId=secret_name)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            raise
        existing = None

    payload = _zscaler_secret_payload(env)
    if not payload.get("ZSCALER_CLIENT_ID") or not payload.get("ZSCALER_CLIENT_SECRET"):
        err(
            "Cannot build Zscaler secret: ZSCALER_CLIENT_ID and "
            "ZSCALER_CLIENT_SECRET must be present in the resolved env. "
            "Set them in .env, pass --client-id / --client-secret, or "
            "set ZSCALER_SECRET_NAME=<existing-secret> in .env to bring "
            "your own pre-populated secret."
        )
        sys.exit(1)
    secret_string = json.dumps(payload, separators=(",", ":"))
    keys = list(payload.keys())

    if existing is not None and existing.get("DeletedDate") is not None:
        # Soft-deleted shadow from a prior destroy. The operator just
        # asked for CreateNew, so .env is the source of truth: restore
        # the secret (instant; reclaims the name slot atomically) then
        # overwrite the value with the current .env payload. No
        # eventual-consistency race because RestoreSecret +
        # PutSecretValue are both strongly consistent on the same
        # resource.
        info(
            f"Secret {secret_name} was soft-deleted by a prior destroy "
            f"(DeletedDate={existing['DeletedDate']}); restoring and "
            "updating with current .env values."
        )
        try:
            sm.restore_secret(SecretId=secret_name)
            sm.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_string,
            )
        except ClientError as e:
            err(
                f"Could not restore + update soft-deleted secret "
                f"{secret_name}: {e}. If you want a fully fresh secret, "
                f"force-purge with `aws secretsmanager delete-secret "
                f"--secret-id {secret_name} --force-delete-without-recovery` "
                f"and re-run. The recovery window is up to 30 days."
            )
            sys.exit(1)
        ok(f"Restored + updated Secrets Manager secret: {existing['ARN']}")
        info(f"  Keys to project as env vars: {', '.join(keys)}")
        return existing["Name"], existing["ARN"], keys

    if existing is not None:
        # Healthy existing secret from a prior script-managed deploy.
        # Don't overwrite — the operator may have rotated credentials
        # directly via `aws secretsmanager put-secret-value` and we
        # don't want to clobber that. To rotate via the script, they
        # can `destroy` (soft-delete) + `deploy` (this branch becomes
        # the restore+put path above and pulls in the new .env values).
        info(f"Reusing script-managed Secrets Manager secret: {existing['Name']}")
        info("  (already created on a prior deploy — value preserved; to")
        info("   rotate, edit .env then `destroy && deploy`, or set the")
        info("   value directly via `aws secretsmanager put-secret-value`)")
        actual_keys = _read_secret_json_keys(sess, existing["Name"])
        if not actual_keys:
            err(
                "Could not find any usable ZSCALER_* keys in the existing "
                "secret. Run destroy + deploy to recreate from .env."
            )
            sys.exit(1)
        info(f"  Keys to project as env vars: {', '.join(actual_keys)}")
        return existing["Name"], existing["ARN"], actual_keys

    # Fresh CreateSecret path.
    info(f"Creating Secrets Manager secret: {secret_name}")
    try:
        resp = sm.create_secret(
            Name=secret_name,
            Description=(
                "Zscaler OneAPI credentials projected into the Harness MCP "
                "server container by the ECS agent via the task definition's "
                "secrets[] block. Managed by harness_mcp_operations.py."
            ),
            SecretString=secret_string,
            Tags=[
                {"Key": "managed-by", "Value": "zscaler-mcp-harness"},
                {"Key": "integration", "Value": "harness"},
            ],
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "InvalidRequestException" and "scheduled for deletion" in str(e):
            # describe_secret claimed "not found" but the name slot is
            # actually in the soft-delete window — race between our
            # describe and another deletion. Fall through to the same
            # restore + put policy as the proactive path above.
            info(
                f"Secret {secret_name} race: name slot is in soft-delete "
                "window; restoring + updating instead."
            )
            try:
                sm.restore_secret(SecretId=secret_name)
                sm.put_secret_value(
                    SecretId=secret_name,
                    SecretString=secret_string,
                )
                resp = sm.describe_secret(SecretId=secret_name)
            except ClientError as e2:
                err(
                    f"Could not restore secret after CreateSecret race: {e2}"
                )
                sys.exit(1)
        else:
            raise
    arn = resp["ARN"]
    ok(f"Created Secrets Manager secret: {arn}")
    info(f"  Keys to project as env vars: {', '.join(keys)}")
    return secret_name, arn, keys


def delete_zscaler_secret(
    sess: boto3.Session,
    secret_name: str,
    *,
    force: bool = False,
) -> None:
    """Delete the Zscaler credentials secret on destroy.

    Default: 7-day recovery window so an accidental ``destroy`` is
    reversible via ``aws secretsmanager restore-secret``. ``force=True``
    bypasses the recovery window for CI / repeated test deploys where
    soft-delete window collisions otherwise block redeploys.
    """
    sm = sess.client("secretsmanager")
    try:
        if force:
            sm.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True,
            )
            ok(f"Force-deleted Secrets Manager secret: {secret_name}")
        else:
            sm.delete_secret(
                SecretId=secret_name,
                RecoveryWindowInDays=7,
            )
            ok(
                f"Scheduled Secrets Manager secret for deletion in 7 days: "
                f"{secret_name} (restore with `aws secretsmanager "
                f"restore-secret --secret-id {secret_name}`)"
            )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            info(f"Secrets Manager secret {secret_name} already absent.")
            return
        warn(f"Could not delete Secrets Manager secret {secret_name}: {e}")


def delete_ecs_express_service(sess: boto3.Session, service_arn: str) -> None:
    ecs = sess.client("ecs")
    try:
        ecs.delete_express_gateway_service(serviceArn=service_arn)
        ok(f"DeleteExpressGatewayService submitted for {service_arn}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ServiceNotFoundException", "ServiceNotActiveException"):
            info(f"ECS Express service {service_arn} already absent or inactive.")
            return
        warn(f"Could not delete ECS Express service {service_arn}: {e}")
        return

    sp = Spinner("Waiting for ECS Express service to reach INACTIVE").start()
    deadline = time.time() + 900
    last_status = "UNKNOWN"
    while time.time() < deadline:
        try:
            svc = ecs.describe_express_gateway_service(serviceArn=service_arn).get(
                "service", {}
            )
            last_status = (svc.get("status") or {}).get("statusCode", last_status)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ServiceNotFoundException":
                sp.stop(f"{GREEN}[OK]{NC}    ECS Express service deleted.")
                return
            sp.stop()
            warn(f"DescribeExpressGatewayService failed during delete poll: {e}")
            return
        if last_status == "INACTIVE":
            sp.stop(f"{GREEN}[OK]{NC}    ECS Express service is INACTIVE.")
            return
        time.sleep(10)
    sp.stop(f"{YELLOW}[WARN]{NC}  Timed out waiting for delete. Last status = {last_status}")


# ══════════════════════════════════════════════════════════════════════════
# GATEWAY TOPOLOGY (PR #48) — Cognito / Runtime / Gateway / OAuth helpers
# ══════════════════════════════════════════════════════════════════════════
#
# Helpers for the alternative deployment topology where the MCP server
# runs on AgentCore Runtime and Harness consumes it through an AgentCore
# Gateway, fronted by Amazon Cognito as the OIDC IdP. See the constants
# block at the top of this file for the full data-flow diagram.
#
# Lift provenance:
#   * Runtime CRUD: adapted from
#     ../bedrock-agentcore/cloudformation/lambda/runtime_provisioner.py
#   * Gateway / Target / OAuth2 credential provider:
#     ../bedrock-agentcore/cloudformation/lambda/gateway_provisioner.py
# The lambda variants were CFN custom resources; here we use them as
# straight boto3 calls with this script's existing TTY/logging helpers.
# ══════════════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────────────────
# OAuth2 credential provider (Token Vault) — used by both Harness→Gateway
# and Gateway→Runtime legs in the Gateway topology
# ──────────────────────────────────────────────────────────────────────────

def find_oauth2_credential_provider_by_name(
    sess: boto3.Session, name: str
) -> Optional[dict[str, Any]]:
    """List + filter — Token Vault has no native get-by-name for OAuth2.

    Caps maxResults at 20 (AgentCore Identity hard-cap on this API; higher
    values raise ValidationException). Paginates if needed.
    """
    ctrl = sess.client("bedrock-agentcore-control")
    kwargs: dict[str, Any] = {"maxResults": 20}
    while True:
        try:
            resp = ctrl.list_oauth2_credential_providers(**kwargs)
        except ClientError as e:
            warn(f"Could not list OAuth2 credential providers: {e}")
            return None
        for cp in resp.get("credentialProviders", []):
            if cp.get("name") == name:
                return cp
        token = resp.get("nextToken")
        if not token:
            return None
        kwargs["nextToken"] = token


def ensure_oauth2_credential_provider(
    sess: boto3.Session,
    *,
    name: str,
    discovery_url: str,
    client_id: str,
    client_secret: str,
) -> str:
    """Find-or-create the OAuth2 credential provider that backs both the
    Harness→Gateway and Gateway→Runtime legs.

    Returns the credential provider ARN.

    AgentCore Identity stores the (clientId, clientSecret, discoveryUrl)
    tuple under a `CustomOauth2` vendor. The provider then becomes the
    Token Vault entry that Harness `outboundAuth.oauth` and Gateway
    targets reference at invoke time — AgentCore handles the
    client_credentials exchange against the IdP for us.
    """
    existing = find_oauth2_credential_provider_by_name(sess, name)
    if existing:
        arn = existing.get("credentialProviderArn", "")
        info(f"Reusing OAuth2 credential provider: {arn}")
        return arn

    info(f"Creating OAuth2 credential provider: {name}")
    info(f"  discoveryUrl: {discovery_url}")
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        resp = ctrl.create_oauth2_credential_provider(
            name=name,
            credentialProviderVendor="CustomOauth2",
            oauth2ProviderConfigInput={
                "customOauth2ProviderConfig": {
                    "oauthDiscovery": {"discoveryUrl": discovery_url},
                    "clientId": client_id,
                    "clientSecret": client_secret,
                }
            },
        )
    except ClientError as e:
        err(f"create_oauth2_credential_provider failed: {e}")
        raise
    arn = resp["credentialProviderArn"]
    ok(f"OAuth2 credential provider created. ARN: {arn}")
    return arn


def delete_oauth2_credential_provider(sess: boto3.Session, name: str) -> None:
    """Best-effort delete. Silent on already-absent."""
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        ctrl.delete_oauth2_credential_provider(name=name)
        ok(f"Deleted OAuth2 credential provider: {name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            info(f"OAuth2 credential provider {name} already absent.")
        else:
            warn(f"Could not delete OAuth2 credential provider {name}: {e}")


# ──────────────────────────────────────────────────────────────────────────
# Amazon Cognito — User Pool + Resource Server + App Client + Domain
# ──────────────────────────────────────────────────────────────────────────
#
# Why ALL FOUR resources are needed for a client_credentials flow:
#   * User Pool        — the OIDC issuer; mints + signs JWTs.
#   * Resource Server  — defines the API "audience"; its identifier
#                        becomes the `aud` claim in issued tokens.
#                        Required because Gateway's customJWTAuthorizer
#                        validates `allowedAudience`, and Cognito refuses
#                        to issue M2M tokens without a custom scope to
#                        attach to.
#   * App Client       — the OAuth client_id / client_secret pair the
#                        Token Vault stores. Marked client_credentials-
#                        only so it cannot be used for user logins.
#   * Domain (hosted UI prefix) — needed for the /oauth2/token endpoint
#                        Cognito exposes. Cognito requires this even
#                        when only client_credentials is enabled (the
#                        token endpoint lives under the domain URL).
# ──────────────────────────────────────────────────────────────────────────

def _cognito_issuer(region: str, user_pool_id: str) -> str:
    """OIDC issuer URL for a Cognito User Pool."""
    return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"


def _cognito_discovery_url(region: str, user_pool_id: str) -> str:
    """OIDC well-known endpoint Cognito serves under its issuer."""
    return f"{_cognito_issuer(region, user_pool_id)}/.well-known/openid-configuration"


def _cognito_token_endpoint(region: str, domain_prefix: str) -> str:
    """Cognito's OAuth2 token endpoint (hosted on the App Client domain)."""
    return (
        f"https://{domain_prefix}.auth.{region}.amazoncognito.com/oauth2/token"
    )


def ensure_cognito_user_pool(
    sess: boto3.Session,
    name: str,
) -> str:
    """Find-or-create the User Pool. Returns the pool ID (e.g. us-east-1_abc123)."""
    idp = sess.client("cognito-idp")

    # No direct get-by-name on Cognito User Pools. List + filter (paginated).
    next_token: Optional[str] = None
    while True:
        kwargs: dict[str, Any] = {"MaxResults": 60}
        if next_token:
            kwargs["NextToken"] = next_token
        resp = idp.list_user_pools(**kwargs)
        for up in resp.get("UserPools", []):
            if up.get("Name") == name:
                pool_id = up["Id"]
                info(f"Reusing Cognito User Pool: {pool_id} (name={name})")
                return pool_id
        next_token = resp.get("NextToken")
        if not next_token:
            break

    info(f"Creating Cognito User Pool: {name}")
    # Minimal config — client_credentials only, no user sign-up, no email
    # verification. AdminCreateUserConfig disables self-registration; we
    # never create users in this pool.
    resp = idp.create_user_pool(
        PoolName=name,
        AdminCreateUserConfig={"AllowAdminCreateUserOnly": True},
        UserPoolTags={
            "managed-by": "zscaler-mcp-harness",
            "integration": "harness",
            "topology": "gateway",
        },
    )
    pool_id = resp["UserPool"]["Id"]
    ok(f"Cognito User Pool created: {pool_id}")
    return pool_id


def ensure_cognito_resource_server(
    sess: boto3.Session,
    *,
    user_pool_id: str,
    identifier: str,
    scope_name: str,
) -> str:
    """Find-or-create the Resource Server. Returns the audience (identifier).

    The identifier becomes the `aud` claim on tokens minted for this
    Resource Server (when the App Client requests its scope), which is
    what Gateway's customJWTAuthorizer validates via `allowedAudience`.
    """
    idp = sess.client("cognito-idp")
    try:
        existing = idp.describe_resource_server(
            UserPoolId=user_pool_id, Identifier=identifier
        ).get("ResourceServer")
        if existing:
            info(f"Reusing Cognito Resource Server: {identifier}")
            return identifier
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code != "ResourceNotFoundException":
            raise

    info(f"Creating Cognito Resource Server: identifier={identifier}, scope={scope_name}")
    idp.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier=identifier,
        Name="Zscaler MCP",
        Scopes=[{"ScopeName": scope_name, "ScopeDescription": "Invoke the MCP server"}],
    )
    ok(f"Cognito Resource Server created: {identifier}/{scope_name}")
    return identifier


def ensure_cognito_app_client(
    sess: boto3.Session,
    *,
    user_pool_id: str,
    name: str,
    allowed_scope: str,
) -> tuple[str, str]:
    """Find-or-create the client_credentials App Client.

    Returns (client_id, client_secret).
    """
    idp = sess.client("cognito-idp")

    next_token: Optional[str] = None
    while True:
        kwargs: dict[str, Any] = {"UserPoolId": user_pool_id, "MaxResults": 60}
        if next_token:
            kwargs["NextToken"] = next_token
        resp = idp.list_user_pool_clients(**kwargs)
        for c in resp.get("UserPoolClients", []):
            if c.get("ClientName") == name:
                client_id = c["ClientId"]
                desc = idp.describe_user_pool_client(
                    UserPoolId=user_pool_id, ClientId=client_id
                )["UserPoolClient"]
                client_secret = desc.get("ClientSecret", "")
                if not client_secret:
                    err(
                        f"Existing Cognito App Client {client_id} has no client secret. "
                        "Delete it manually and rerun deploy."
                    )
                    sys.exit(1)
                info(f"Reusing Cognito App Client: {client_id} (name={name})")
                return client_id, client_secret
        next_token = resp.get("NextToken")
        if not next_token:
            break

    info(f"Creating Cognito App Client: {name} (client_credentials grant)")
    # Cognito refuses to enable client_credentials unless we also list a
    # custom scope to attach to it. AllowedOAuthFlowsUserPoolClient must
    # be True for client_credentials to be honoured.
    resp = idp.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=[allowed_scope],
        AllowedOAuthFlowsUserPoolClient=True,
        # Refresh-token validity has no effect on client_credentials (no
        # refresh tokens minted) — accept Cognito's default 30 days.
        # Access-token validity: keep Cognito default (1 hour) — Harness
        # / Gateway / Token Vault all handle token refresh automatically.
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"],
    )
    client_id = resp["UserPoolClient"]["ClientId"]
    client_secret = resp["UserPoolClient"]["ClientSecret"]
    ok(f"Cognito App Client created: {client_id}")
    return client_id, client_secret


def ensure_cognito_user_pool_domain(
    sess: boto3.Session,
    *,
    user_pool_id: str,
    domain_prefix: str,
) -> str:
    """Find-or-create the User Pool domain. Returns the full prefix actually used.

    Cognito's hosted UI domain hosts the /oauth2/token endpoint that
    OAuth client_credentials clients hit. The domain prefix MUST be
    globally unique within a region, so we suffix it with the AWS
    account ID before creating. If a previous deploy left a domain in
    place (CREATING state, FAILED state, or live), we reuse it.
    """
    idp = sess.client("cognito-idp")

    # describe_user_pool_domain accepts the prefix only, not the FQDN.
    try:
        desc = idp.describe_user_pool_domain(Domain=domain_prefix).get(
            "DomainDescription"
        )
        if desc and desc.get("UserPoolId") == user_pool_id:
            status = desc.get("Status", "UNKNOWN")
            info(f"Reusing Cognito User Pool domain: {domain_prefix} (status={status})")
            return domain_prefix
        if desc and desc.get("UserPoolId"):
            warn(
                f"Cognito domain prefix '{domain_prefix}' already exists in this "
                f"region under a different User Pool ({desc['UserPoolId']}). "
                "Pick a different --cognito-domain-prefix."
            )
            sys.exit(1)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("ResourceNotFoundException", "InvalidParameterException"):
            raise

    info(f"Creating Cognito User Pool domain: {domain_prefix}")
    try:
        idp.create_user_pool_domain(
            Domain=domain_prefix,
            UserPoolId=user_pool_id,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "InvalidParameterException" and "already" in str(e).lower():
            warn(
                f"Cognito refused the domain prefix '{domain_prefix}' (likely a "
                "regional collision with another AWS account). Pick a different "
                "--cognito-domain-prefix and rerun."
            )
            sys.exit(1)
        raise
    ok(f"Cognito User Pool domain created: {domain_prefix}")
    return domain_prefix


def delete_cognito_user_pool(
    sess: boto3.Session,
    *,
    user_pool_id: str,
    domain_prefix: str,
) -> None:
    """Cascading delete: domain → user pool. Best-effort.

    Cognito requires the domain to be deleted BEFORE the User Pool can
    be deleted (else DeleteUserPool fails with InvalidParameterException
    "Domain exists for User Pool"). App Clients and Resource Servers are
    deleted automatically when the parent pool is deleted.
    """
    idp = sess.client("cognito-idp")

    if domain_prefix:
        try:
            idp.delete_user_pool_domain(
                Domain=domain_prefix, UserPoolId=user_pool_id
            )
            ok(f"Deleted Cognito domain: {domain_prefix}")
            # Cognito's domain delete is eventually-consistent; the User
            # Pool delete below can race. A few seconds is enough — the
            # domain teardown is the only async piece.
            time.sleep(5)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("ResourceNotFoundException", "InvalidParameterException"):
                info(f"Cognito domain {domain_prefix} already absent.")
            else:
                warn(f"Could not delete Cognito domain {domain_prefix}: {e}")

    try:
        idp.delete_user_pool(UserPoolId=user_pool_id)
        ok(f"Deleted Cognito User Pool: {user_pool_id}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            info(f"Cognito User Pool {user_pool_id} already absent.")
        else:
            warn(f"Could not delete Cognito User Pool {user_pool_id}: {e}")


# ──────────────────────────────────────────────────────────────────────────
# AgentCore Runtime (Gateway topology) — boto3 lift from runtime_provisioner.py
# ──────────────────────────────────────────────────────────────────────────

# Trust policy for the AgentCore Runtime execution role.
def _runtime_role_trust_policy() -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def _runtime_role_inline_policy(
    account_id: str,
    region: str,
    secret_arn: Optional[str],
    image_uri: str,
) -> dict[str, Any]:
    """Inline policy attached to the Runtime execution role.

    Grants the minimum the container needs at task start:
      * ECR image pull (cross-account aware if the image isn't in the
        current account, matching the ECS execution role policy).
      * CloudWatch Logs PutLogEvents under
        /aws/bedrock-agentcore/runtimes/<runtime-id>.
      * Secrets Manager GetSecretValue + KMS Decrypt on the Zscaler
        secret (only when one was provisioned).
      * Bedrock InvokeModel for the LLM (Runtime → Harness model
        invocations don't go through here, but the runtime's own
        bedrock-agentcore stack may need it for memory features).
    """
    statements: list[dict[str, Any]] = [
        {
            "Sid": "EcrAuthAndPull",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr-public:GetAuthorizationToken",
                "sts:GetServiceBearerToken",
            ],
            "Resource": "*",
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
            ],
            "Resource": (
                f"arn:aws:logs:{region}:{account_id}:log-group:"
                f"/aws/bedrock-agentcore/runtimes/*"
            ),
        },
        {
            "Sid": "BedrockInvokeModel",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
            ],
            "Resource": "*",
        },
    ]
    if secret_arn:
        # ResourceTagging on the secret would be nicer but the lifecycle
        # is fully script-managed, so we just scope to the ARN.
        statements.append(
            {
                "Sid": "SecretsManagerGet",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": secret_arn,
            }
        )
        statements.append(
            {
                "Sid": "KmsDecryptForSecrets",
                "Effect": "Allow",
                "Action": ["kms:Decrypt"],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "kms:ViaService": f"secretsmanager.{region}.amazonaws.com"
                    }
                },
            }
        )
    return {"Version": "2012-10-17", "Statement": statements}


def ensure_runtime_execution_role(
    sess: boto3.Session,
    *,
    role_name: str,
    region: str,
    secret_arn: Optional[str],
    image_uri: str,
) -> str:
    """Find-or-create the IAM role AgentCore Runtime assumes at task start."""
    iam = sess.client("iam")
    account_id = get_account_id(sess)
    trust = _runtime_role_trust_policy()
    inline = _runtime_role_inline_policy(account_id, region, secret_arn, image_uri)

    try:
        existing = iam.get_role(RoleName=role_name)["Role"]
        info(f"Reusing Runtime execution role: {existing['Arn']}")
        iam.update_assume_role_policy(
            RoleName=role_name, PolicyDocument=json.dumps(trust)
        )
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="ZscalerRuntimeInline",
            PolicyDocument=json.dumps(inline),
        )
        return existing["Arn"]
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise

    info(f"Creating Runtime execution role: {role_name}")
    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust),
        Description="Execution role for the Zscaler MCP Server on AgentCore Runtime",
        Tags=[
            {"Key": "managed-by", "Value": "zscaler-mcp-harness"},
            {"Key": "integration", "Value": "harness"},
            {"Key": "topology", "Value": "gateway"},
        ],
    )
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="ZscalerRuntimeInline",
        PolicyDocument=json.dumps(inline),
    )
    # IAM eventual consistency: AssumeRole calls from the AgentCore
    # control plane can race the role becoming "real" — wait briefly.
    time.sleep(8)
    ok(f"Runtime execution role created: {resp['Role']['Arn']}")
    return resp["Role"]["Arn"]


def delete_runtime_execution_role(sess: boto3.Session, role_name: str) -> None:
    """Best-effort delete (mirrors ensure_*)."""
    iam = sess.client("iam")
    try:
        iam.delete_role_policy(RoleName=role_name, PolicyName="ZscalerRuntimeInline")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            warn(f"Could not delete inline policy on {role_name}: {e}")
    try:
        iam.delete_role(RoleName=role_name)
        ok(f"Deleted Runtime execution role: {role_name}")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            warn(f"Could not delete role {role_name}: {e}")
        else:
            info(f"Role {role_name} already absent.")


def find_runtime_by_name(
    sess: boto3.Session, name: str
) -> Optional[dict[str, Any]]:
    """List + filter — Runtime API has no get-by-name."""
    ctrl = sess.client("bedrock-agentcore-control")
    kwargs: dict[str, Any] = {"maxResults": 100}
    while True:
        resp = ctrl.list_agent_runtimes(**kwargs)
        for rt in resp.get("agentRuntimes", []):
            if rt.get("agentRuntimeName") == name:
                return rt
        token = resp.get("nextToken")
        if not token:
            return None
        kwargs["nextToken"] = token


def build_runtime_mcp_url(runtime_arn: str, qualifier: str = "DEFAULT") -> str:
    """AgentCore Runtime invoke URL — built from the ARN, not in any API.

    AgentCore exposes the runtime at
    ``https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<arn>/
    invocations?qualifier=<q>``, with every ``:`` / ``/`` in the ARN
    percent-encoded. Returns ``""`` if the ARN doesn't parse.
    """
    arn = (runtime_arn or "").strip()
    if not arn.startswith("arn:") or ":" not in arn:
        return ""
    parts = arn.split(":", 5)
    if len(parts) < 6:
        return ""
    region = parts[3]
    if not region:
        return ""
    import urllib.parse as _ulib

    encoded_arn = _ulib.quote(arn, safe="")
    return (
        f"https://bedrock-agentcore.{region}.amazonaws.com"
        f"/runtimes/{encoded_arn}/invocations?qualifier={qualifier}"
    )


def _build_runtime_env_vars(
    raw_env: dict[str, str],
    *,
    secret_name: Optional[str],
) -> dict[str, str]:
    """Forward the operator's ``.env`` to the Runtime container, verbatim.

    Mirrors ``_build_container_env_vars`` (ECS topology): every key
    starting with ``ZSCALER_``, ``FASTMCP_``, or ``MCP_`` from the
    resolved ``.env`` is forwarded as-is. The script does NOT invent
    auth, transport, host-validation, or any other defaults — if a
    value isn't in ``.env``, it isn't in the container.

    The only additions are:

    * ``_RUNTIME_TOPOLOGY_FALLBACKS`` — the bare-minimum transport
      wiring the container needs to bind to the port AgentCore
      expects. Applied **only when the operator didn't set them**.
    * ``ZSCALER_SECRET_NAME`` — when Secrets Manager is in play,
      tells ``zscaler_mcp.config`` to fetch credentials at boot via
      the Runtime execution role's secretsmanager grant.

    Deploy-time-only keys (``ZSCALER_MCP_IMAGE_URI``) are stripped
    because they configure the deploy script, not the MCP server.
    """
    # Start with operator's .env — verbatim, no filtering, no skipping.
    _STRIP_KEYS = frozenset({"ZSCALER_MCP_IMAGE_URI", "MCP_URL"})
    env: dict[str, str] = {}
    for k, v in raw_env.items():
        if not v:
            continue
        if k in _STRIP_KEYS:
            continue
        if k.startswith(("ZSCALER_", "FASTMCP_", "MCP_")):
            env[k] = v

    # Fill in the bare-minimum topology wiring ONLY if the operator
    # didn't already set them. Operator's .env always wins.
    for k, v in _RUNTIME_TOPOLOGY_FALLBACKS.items():
        if k not in env:
            env[k] = v

    # Secrets Manager name — tells the container to fetch creds at boot.
    if secret_name:
        env["ZSCALER_SECRET_NAME"] = secret_name

    return env


def _build_runtime_inbound_auth_kwargs(
    *, discovery_url: str, scope: str, allowed_client_id: str
) -> dict[str, Any]:
    """Build the requestHeaderConfiguration + authorizerConfiguration
    kwargs for create_agent_runtime / update_agent_runtime in jwt mode.

    AgentCore enforces: the `Authorization` header is forwardable to the
    container ONLY when customJwtAuthorizer is configured.

    Cognito-specific gotcha: Cognito's `client_credentials` access tokens
    deliberately omit the `aud` claim — AWS's own docs spell this out:
    "The aud field is not set in an access token because, when a relying
    party validates the access token, the resource server is the
    audience, not the app client." Passing `allowedAudience` to the
    customJWTAuthorizer therefore causes every call to fail with
    "Claim 'aud' value mismatch with configuration."

    We rely on the Cognito-native validation pair instead:
      * `allowedClients` matches the `client_id` claim (always present).
      * `allowedScopes`  matches the `scope` claim (the
        ``resource_server/scope`` tuple — e.g. ``zscaler-mcp/invoke``).
    Either is sufficient on its own; using both is defense-in-depth.
    """
    custom_jwt: dict[str, Any] = {
        "discoveryUrl": discovery_url,
        "allowedClients": [allowed_client_id],
    }
    if scope:
        custom_jwt["allowedScopes"] = [scope]
    return {
        "authorizerConfiguration": {
            "customJWTAuthorizer": custom_jwt
        },
        "requestHeaderConfiguration": {
            "requestHeaderAllowlist": ["Authorization"],
        },
    }


def wait_for_runtime_status(
    sess: boto3.Session, runtime_id: str, target: str = "READY", timeout_s: int = 600
) -> dict[str, Any]:
    """Poll get_agent_runtime until status==target or terminal failure."""
    ctrl = sess.client("bedrock-agentcore-control")
    sp = Spinner(f"Waiting for Runtime status={target}").start()
    deadline = time.time() + timeout_s
    last_status = ""
    last: dict[str, Any] = {}
    while time.time() < deadline:
        try:
            last = ctrl.get_agent_runtime(agentRuntimeId=runtime_id)
        except ClientError as e:
            sp.stop()
            raise RuntimeError(f"get_agent_runtime failed: {e}") from e
        status = last.get("status", "UNKNOWN")
        if status != last_status:
            sp.stop(f"  Runtime status={status}")
            sp = Spinner(f"Waiting for Runtime status={target}").start()
            last_status = status
        if status == target:
            sp.stop(f"{GREEN}[OK]{NC}    Runtime status = {status}")
            return last
        if status in ("CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED", "FAILED"):
            sp.stop(f"{RED}[ERROR]{NC} Runtime status = {status}")
            return last
        time.sleep(8)
    sp.stop(
        f"{YELLOW}[WARN]{NC}  Timed out waiting for {target}. "
        f"Last status = {last.get('status')}"
    )
    return last


def ensure_runtime(
    sess: boto3.Session,
    *,
    runtime_name: str,
    image_uri: str,
    execution_role_arn: str,
    env: dict[str, str],
    inbound_auth_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Find-or-create AgentCore Runtime. Returns the runtime descriptor
    (with agentRuntimeArn + agentRuntimeId populated)."""
    ctrl = sess.client("bedrock-agentcore-control")
    existing = find_runtime_by_name(sess, runtime_name)
    artifact = {"containerConfiguration": {"containerUri": image_uri}}

    if existing:
        runtime_id = existing["agentRuntimeId"]
        info(f"Updating existing Runtime: {runtime_name} (id={runtime_id})")
        try:
            ctrl.update_agent_runtime(
                agentRuntimeId=runtime_id,
                agentRuntimeArtifact=artifact,
                roleArn=execution_role_arn,
                networkConfiguration={"networkMode": "PUBLIC"},
                protocolConfiguration={"serverProtocol": "MCP"},
                environmentVariables=env,
                **inbound_auth_kwargs,
            )
        except ClientError as e:
            err(f"update_agent_runtime failed: {e}")
            raise
    else:
        info(f"Creating Runtime: {runtime_name}")
        try:
            ctrl.create_agent_runtime(
                agentRuntimeName=runtime_name,
                agentRuntimeArtifact=artifact,
                roleArn=execution_role_arn,
                networkConfiguration={"networkMode": "PUBLIC"},
                protocolConfiguration={"serverProtocol": "MCP"},
                environmentVariables=env,
                **inbound_auth_kwargs,
            )
        except ClientError as e:
            err(f"create_agent_runtime failed: {e}")
            raise

    rt = find_runtime_by_name(sess, runtime_name)
    if not rt:
        raise RuntimeError(f"Runtime {runtime_name} disappeared after create/update.")
    final = wait_for_runtime_status(sess, rt["agentRuntimeId"], target="READY")
    return final


def delete_runtime(sess: boto3.Session, runtime_name: str) -> None:
    """Best-effort delete."""
    rt = find_runtime_by_name(sess, runtime_name)
    if not rt:
        info(f"Runtime {runtime_name} already absent.")
        return
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        ctrl.delete_agent_runtime(agentRuntimeId=rt["agentRuntimeId"])
        ok(f"Deleted Runtime: {runtime_name} (id={rt['agentRuntimeId']})")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            info(f"Runtime {runtime_name} already absent.")
        else:
            warn(f"Could not delete Runtime {runtime_name}: {e}")


# ──────────────────────────────────────────────────────────────────────────
# AgentCore Gateway + Target — boto3 lift from gateway_provisioner.py
# ──────────────────────────────────────────────────────────────────────────

# IAM role assumed by the Gateway service when invoking the Runtime
# target. Trust = bedrock-agentcore service; permissions = invoke any
# AgentCore Runtime in the account (scoped to the runtime ARN at deploy
# time).
def _gateway_role_trust_policy() -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def _gateway_role_inline_policy(runtime_arn: str) -> dict[str, Any]:
    """Inline policy for the Gateway service role.

    Gateway needs permission to invoke its targets. For an mcpServer
    target backed by an AgentCore Runtime, that's
    bedrock-agentcore:InvokeAgentRuntime on the Runtime's ARN.
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InvokeRuntimeTarget",
                "Effect": "Allow",
                "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
                "Resource": [
                    runtime_arn,
                    # Wildcard for runtime endpoint/qualifier sub-resources.
                    runtime_arn + "/*",
                    runtime_arn + ":*",
                ],
            },
            {
                "Sid": "Logging",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": "*",
            },
        ],
    }


def ensure_gateway_role(
    sess: boto3.Session, *, role_name: str, runtime_arn: str
) -> str:
    """Find-or-create the IAM role Gateway uses to invoke its Runtime target."""
    iam = sess.client("iam")
    trust = _gateway_role_trust_policy()
    inline = _gateway_role_inline_policy(runtime_arn)

    try:
        existing = iam.get_role(RoleName=role_name)["Role"]
        info(f"Reusing Gateway service role: {existing['Arn']}")
        iam.update_assume_role_policy(
            RoleName=role_name, PolicyDocument=json.dumps(trust)
        )
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="ZscalerGatewayInline",
            PolicyDocument=json.dumps(inline),
        )
        return existing["Arn"]
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise

    info(f"Creating Gateway service role: {role_name}")
    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust),
        Description="Service role used by AgentCore Gateway to invoke the Zscaler MCP Runtime",
        Tags=[
            {"Key": "managed-by", "Value": "zscaler-mcp-harness"},
            {"Key": "integration", "Value": "harness"},
            {"Key": "topology", "Value": "gateway"},
        ],
    )
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="ZscalerGatewayInline",
        PolicyDocument=json.dumps(inline),
    )
    time.sleep(8)  # IAM eventual consistency
    ok(f"Gateway service role created: {resp['Role']['Arn']}")
    return resp["Role"]["Arn"]


def delete_gateway_role(sess: boto3.Session, role_name: str) -> None:
    """Best-effort delete."""
    iam = sess.client("iam")
    try:
        iam.delete_role_policy(RoleName=role_name, PolicyName="ZscalerGatewayInline")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            warn(f"Could not delete inline policy on {role_name}: {e}")
    try:
        iam.delete_role(RoleName=role_name)
        ok(f"Deleted Gateway service role: {role_name}")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchEntity":
            warn(f"Could not delete role {role_name}: {e}")
        else:
            info(f"Role {role_name} already absent.")


def find_gateway_by_name(
    sess: boto3.Session, name: str
) -> Optional[dict[str, Any]]:
    ctrl = sess.client("bedrock-agentcore-control")
    kwargs: dict[str, Any] = {"maxResults": 100}
    while True:
        resp = ctrl.list_gateways(**kwargs)
        for gw in resp.get("items", []):
            if gw.get("name") == name:
                return gw
        token = resp.get("nextToken")
        if not token:
            return None
        kwargs["nextToken"] = token


def find_gateway_target_by_name(
    sess: boto3.Session, *, gateway_id: str, name: str
) -> Optional[dict[str, Any]]:
    ctrl = sess.client("bedrock-agentcore-control")
    kwargs: dict[str, Any] = {"gatewayIdentifier": gateway_id, "maxResults": 100}
    while True:
        resp = ctrl.list_gateway_targets(**kwargs)
        for t in resp.get("items", []):
            if t.get("name") == name:
                return t
        token = resp.get("nextToken")
        if not token:
            return None
        kwargs["nextToken"] = token


_GATEWAY_TERMINAL_FAILURE = (
    "FAILED",
    "CREATE_FAILED",
    "UPDATE_FAILED",
    "DELETE_FAILED",
)


def wait_for_gateway_status(
    sess: boto3.Session, gateway_id: str, target: str = "READY", timeout_s: int = 600
) -> dict[str, Any]:
    ctrl = sess.client("bedrock-agentcore-control")
    sp = Spinner(f"Waiting for Gateway status={target}").start()
    deadline = time.time() + timeout_s
    last_status = ""
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = ctrl.get_gateway(gatewayIdentifier=gateway_id)
        status = last.get("status", "UNKNOWN")
        if status != last_status:
            sp.stop(f"  Gateway status={status}")
            sp = Spinner(f"Waiting for Gateway status={target}").start()
            last_status = status
        if status == target:
            sp.stop(f"{GREEN}[OK]{NC}    Gateway status = {status}")
            return last
        if status in _GATEWAY_TERMINAL_FAILURE:
            sp.stop(f"{RED}[ERROR]{NC} Gateway status = {status}")
            return last
        time.sleep(8)
    sp.stop(
        f"{YELLOW}[WARN]{NC}  Timed out. Last Gateway status = {last.get('status')}"
    )
    return last


def wait_for_gateway_target_status(
    sess: boto3.Session,
    *,
    gateway_id: str,
    target_id: str,
    target_status: str = "READY",
    timeout_s: int = 600,
) -> dict[str, Any]:
    ctrl = sess.client("bedrock-agentcore-control")
    sp = Spinner(f"Waiting for Target status={target_status}").start()
    deadline = time.time() + timeout_s
    last_status = ""
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = ctrl.get_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target_id
        )
        status = last.get("status", "UNKNOWN")
        if status != last_status:
            sp.stop(f"  Target status={status}")
            sp = Spinner(f"Waiting for Target status={target_status}").start()
            last_status = status
        if status == target_status:
            sp.stop(f"{GREEN}[OK]{NC}    Target status = {status}")
            return last
        if status in _GATEWAY_TERMINAL_FAILURE:
            sp.stop(f"{RED}[ERROR]{NC} Target status = {status}")
            return last
        if status in ("CREATE_PENDING_AUTH", "UPDATE_PENDING_AUTH"):
            sp.stop(
                f"{RED}[ERROR]{NC} Target stuck in {status} — needs human OAuth consent. "
                "Likely indicates an OAuth misconfiguration on the Cognito side."
            )
            return last
        time.sleep(8)
    sp.stop(f"{YELLOW}[WARN]{NC}  Timed out. Last Target status = {last.get('status')}")
    return last


def ensure_gateway(
    sess: boto3.Session,
    *,
    name: str,
    role_arn: str,
    cognito_discovery_url: str,
    cognito_scope: str,
    cognito_client_id: str,
) -> dict[str, Any]:
    """Find-or-create the AgentCore Gateway with inbound CUSTOM_JWT auth.

    See ``_build_runtime_inbound_auth_kwargs`` for the rationale on why
    we use ``allowedClients`` + ``allowedScopes`` instead of
    ``allowedAudience`` — Cognito's M2M tokens omit the ``aud`` claim
    entirely, so any ``allowedAudience`` check fails 100% of the time.
    """
    ctrl = sess.client("bedrock-agentcore-control")
    existing = find_gateway_by_name(sess, name)

    custom_jwt: dict[str, Any] = {
        "discoveryUrl": cognito_discovery_url,
        "allowedClients": [cognito_client_id],
    }
    if cognito_scope:
        custom_jwt["allowedScopes"] = [cognito_scope]

    if existing:
        gw_id = existing["gatewayId"]
        # list_gateways returns a summary (gatewayId, name, status) — no
        # roleArn / protocolType / authorizerConfiguration. Fetch the full
        # descriptor before drift-checking or calling update_gateway, since
        # both require fields the summary doesn't carry.
        try:
            full = ctrl.get_gateway(gatewayIdentifier=gw_id)
        except ClientError as e:
            err(f"get_gateway({gw_id}) failed: {e}")
            raise
        cur_auth = (
            full.get("authorizerConfiguration", {}).get("customJWTAuthorizer", {})
        )
        # authorizerConfiguration is mutable via UpdateGateway. Detect drift —
        # specifically a stale `allowedAudience` from an older script revision
        # that misunderstood Cognito M2M token claims, or a stale client/scope
        # list. Roles, protocol, and authorizerType ARE immutable post-create,
        # but those don't change between script versions so reuse is safe.
        drift_fields: list[str] = []
        if cur_auth.get("discoveryUrl") != custom_jwt["discoveryUrl"]:
            drift_fields.append("discoveryUrl")
        if list(cur_auth.get("allowedClients") or []) != custom_jwt["allowedClients"]:
            drift_fields.append("allowedClients")
        if list(cur_auth.get("allowedScopes") or []) != custom_jwt.get("allowedScopes", []):
            drift_fields.append("allowedScopes")
        # Any allowedAudience at all is now wrong for Cognito M2M; force it gone.
        if cur_auth.get("allowedAudience"):
            drift_fields.append("allowedAudience (stale)")

        if drift_fields:
            warn(
                f"Gateway {name} (id={gw_id}) authorizer drift detected — "
                f"updating: {', '.join(drift_fields)}"
            )
            try:
                ctrl.update_gateway(
                    gatewayIdentifier=gw_id,
                    name=full["name"],
                    description=full.get("description", ""),
                    roleArn=full["roleArn"],
                    protocolType=full["protocolType"],
                    authorizerType=full["authorizerType"],
                    authorizerConfiguration={"customJWTAuthorizer": custom_jwt},
                )
            except ClientError as e:
                err(f"update_gateway failed: {e}")
                raise
            ok(f"Gateway {name} authorizer refreshed.")
            return wait_for_gateway_status(sess, gw_id, target="READY")
        info(f"Reusing Gateway: {name} (id={gw_id})")
        # Return the full descriptor (not the summary) so callers like
        # _deploy_gateway_topology can read gatewayArn / gatewayUrl.
        return full

    info(f"Creating Gateway: {name}")
    try:
        resp = ctrl.create_gateway(
            name=name,
            description="Zscaler MCP Server — AgentCore Gateway (Cognito-fronted)",
            clientToken=str(uuid.uuid4()),
            roleArn=role_arn,
            protocolType="MCP",
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={"customJWTAuthorizer": custom_jwt},
            tags={
                "managed-by": "zscaler-mcp-harness",
                "integration": "harness",
                "topology": "gateway",
            },
        )
    except ClientError as e:
        err(f"create_gateway failed: {e}")
        raise
    gw_id = resp["gatewayId"]
    ok(f"Gateway created: {name} (id={gw_id})")
    return wait_for_gateway_status(sess, gw_id, target="READY")


def delete_gateway(sess: boto3.Session, name: str) -> None:
    """Best-effort delete. Targets must already be deleted (caller handles)."""
    gw = find_gateway_by_name(sess, name)
    if not gw:
        info(f"Gateway {name} already absent.")
        return
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        ctrl.delete_gateway(gatewayIdentifier=gw["gatewayId"])
        ok(f"Deleted Gateway: {name} (id={gw['gatewayId']})")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            info(f"Gateway {name} already absent.")
        else:
            warn(f"Could not delete Gateway {name}: {e}")


def ensure_gateway_target(
    sess: boto3.Session,
    *,
    gateway_id: str,
    name: str,
    runtime_arn: str,
    oauth_provider_arn: str,
    cognito_scope: str,
) -> dict[str, Any]:
    """Find-or-create the mcpServer target wiring Gateway → Runtime.

    The target's outbound credentialProvider is the Cognito-backed OAuth2
    provider — Gateway uses it to fetch a client_credentials access token
    before invoking the Runtime, which is what Runtime's customJwtAuthorizer
    will then validate.

    ``cognito_scope`` (e.g. ``zscaler-mcp/invoke``) is forwarded to
    Cognito's token endpoint as ``scope=<value>``. This is REQUIRED —
    omitting it yields a Cognito M2M token with no ``scope`` claim,
    which then fails the Runtime authorizer's ``allowedScopes`` check
    and surfaces as ``Received error (401) from runtime`` at target
    create time. Cognito does NOT auto-attach the Resource Server's
    scopes when the request has no ``scope=`` parameter.

    Returns the target descriptor.
    """
    ctrl = sess.client("bedrock-agentcore-control")
    existing = find_gateway_target_by_name(
        sess, gateway_id=gateway_id, name=name
    )
    if existing:
        # If the existing target is in a healthy/transient state, reuse it.
        # If it's in any terminal-failure state, delete and recreate — there's
        # no UpdateGatewayTarget path that recovers from FAILED, and AgentCore
        # only re-runs the connectivity smoke-test on create.
        existing_status = existing.get("status", "UNKNOWN")
        existing_id = existing["targetId"]
        if existing_status in _GATEWAY_TERMINAL_FAILURE:
            warn(
                f"Existing Gateway target {name} (id={existing_id}) is in "
                f"status={existing_status} — deleting so it can be recreated."
            )
            try:
                ctrl.delete_gateway_target(
                    gatewayIdentifier=gateway_id, targetId=existing_id
                )
            except ClientError as e:
                err(f"Could not delete failed gateway target {existing_id}: {e}")
                raise
            # Poll until the target actually disappears (delete is async).
            for _ in range(30):
                if find_gateway_target_by_name(sess, gateway_id=gateway_id, name=name) is None:
                    break
                time.sleep(2)
            ok(f"Deleted failed Gateway target {name} (id={existing_id}).")
        else:
            info(f"Reusing Gateway target: {name} (id={existing_id}, status={existing_status})")
            return existing

    info(f"Creating Gateway target: {name}")
    target_configuration: dict[str, Any] = {
        "mcp": {
            "mcpServer": {
                "endpoint": build_runtime_mcp_url(runtime_arn),
                "listingMode": "DEFAULT",
            }
        }
    }
    credential_provider_configurations = [
        {
            "credentialProviderType": "OAUTH",
            "credentialProvider": {
                "oauthCredentialProvider": {
                    "providerArn": oauth_provider_arn,
                    # MUST send the scope explicitly. Cognito's
                    # client_credentials grant returns a token with NO
                    # `scope` claim when `scope=` is absent from the
                    # token request, and the Runtime's
                    # ``allowedScopes`` check then rejects it (401).
                    # See ensure_gateway_target docstring.
                    "scopes": [cognito_scope],
                    "grantType": "CLIENT_CREDENTIALS",
                }
            },
        }
    ]
    try:
        resp = ctrl.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=name,
            description="Zscaler MCP Server runtime — invoked via OAuth2 client_credentials",
            clientToken=str(uuid.uuid4()),
            targetConfiguration=target_configuration,
            credentialProviderConfigurations=credential_provider_configurations,
        )
    except ClientError as e:
        err(f"create_gateway_target failed: {e}")
        raise
    target_id = resp["targetId"]
    ok(f"Gateway target created: {name} (id={target_id})")
    return wait_for_gateway_target_status(
        sess, gateway_id=gateway_id, target_id=target_id, target_status="READY"
    )


def delete_gateway_target(
    sess: boto3.Session, *, gateway_id: str, name: str
) -> None:
    target = find_gateway_target_by_name(sess, gateway_id=gateway_id, name=name)
    if not target:
        info(f"Gateway target {name} already absent.")
        return
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        ctrl.delete_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target["targetId"]
        )
        ok(f"Deleted Gateway target: {name} (id={target['targetId']})")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            info(f"Gateway target {name} already absent.")
        else:
            warn(f"Could not delete Gateway target {name}: {e}")


# ──────────────────────────────────────────────────────────────────────────
# Token Vault credential provider
# ──────────────────────────────────────────────────────────────────────────

def ensure_credential_provider(
    sess: boto3.Session,
    name: str,
    client_id: str,
    client_secret: str,
) -> str:
    """Stash `Basic <base64>` in AgentCore Identity Token Vault.

    Stores the *complete* Authorization header value (prefix included)
    so Harness's `${arn:…provider}` substitution drops a ready-to-send
    value into the outbound header at invocation time.
    """
    basic_value = "Basic " + base64.b64encode(
        f"{client_id}:{client_secret}".encode("utf-8")
    ).decode("ascii")

    ctrl = sess.client("bedrock-agentcore-control")

    try:
        existing = ctrl.get_api_key_credential_provider(name=name)
        provider_arn = existing["credentialProviderArn"]
        info(f"Reusing Token Vault credential provider: {provider_arn}")
        try:
            ctrl.update_api_key_credential_provider(name=name, apiKey=basic_value)
            ok("Refreshed credential provider apiKey value.")
        except ClientError as e:
            warn(f"Could not refresh credential provider (continuing): {e}")
        return provider_arn
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("ResourceNotFoundException", "NotFoundException"):
            raise

    info(f"Creating Token Vault credential provider: {name}")
    resp = ctrl.create_api_key_credential_provider(
        name=name,
        apiKey=basic_value,
        tags={"managed-by": "zscaler-mcp-harness", "integration": "harness"},
    )
    provider_arn = resp["credentialProviderArn"]
    ok(f"Credential provider stored. ARN: {provider_arn}")
    return provider_arn


def delete_credential_provider(sess: boto3.Session, name: str) -> None:
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        ctrl.delete_api_key_credential_provider(name=name)
        ok(f"Deleted credential provider: {name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            info(f"Credential provider {name} already absent.")
        else:
            warn(f"Could not delete credential provider {name}: {e}")


# ──────────────────────────────────────────────────────────────────────────
# Harness
# ──────────────────────────────────────────────────────────────────────────

def build_remote_mcp_tool(
    mcp_url: str,
    credential_provider_arn: str,
    tool_name: str = DEFAULT_MCP_TOOL_NAME,
) -> dict[str, Any]:
    """Build the `remote_mcp` tool block for CreateHarness.

    The header value `${arn:…}` is whole-value substituted by Harness at
    invocation time with the credential provider's stored apiKey. We
    stored `Basic <base64>` so the wire header becomes the literal
    `Authorization: Basic <base64>` the MCP server's Zscaler-mode
    middleware expects.
    """
    return {
        "type": "remote_mcp",
        "name": tool_name,
        "config": {
            "remoteMcp": {
                "url": mcp_url,
                "headers": {
                    "Authorization": "${" + credential_provider_arn + "}",
                },
            }
        },
    }


def build_agentcore_gateway_tool(
    gateway_arn: str,
    oauth_provider_arn: str,
    tool_name: str = DEFAULT_MCP_TOOL_NAME,
) -> dict[str, Any]:
    """Build the `agentcore_gateway` tool block for CreateHarness.

    Shape locked against the botocore 2023-06-05 service-2.json schema for
    bedrock-agentcore-control:

        HarnessTool {
          type: "agentcore_gateway",
          name: <free-form>,
          config: {
            agentCoreGateway: {                  # ← camelCase, NOT agentcoreGateway
              gatewayArn: <Gateway ARN>,
              outboundAuth: {                    # union — exactly one of:
                oauth: {                         # ← we use this branch
                  providerArn: <OAuth provider ARN>,
                  scopes: [],
                  grantType: "CLIENT_CREDENTIALS",
                },
              }
            }
          }
        }

    Why `oauth` (not `awsIam` or `none`):
      * Gateway only supports `customJWTAuthorizer` inbound (CreateGateway's
        AuthorizerType enum has CUSTOM_JWT as its only documented variant),
        so SigV4 from Harness wouldn't pass inbound validation.
      * `none` would only work for an unauthenticated Gateway — not safe.

    The `oauth.providerArn` references an AgentCore Identity OAuth2
    credential provider (the one ensure_oauth2_credential_provider() just
    created/found). Harness will fetch a Cognito client_credentials access
    token via that provider and present it as a Bearer token to Gateway.
    Empty `scopes` lets Cognito use the Resource Server's default scopes.
    """
    return {
        "type": "agentcore_gateway",
        "name": tool_name,
        "config": {
            "agentCoreGateway": {
                "gatewayArn": gateway_arn,
                "outboundAuth": {
                    "oauth": {
                        "providerArn": oauth_provider_arn,
                        "scopes": [],
                        "grantType": "CLIENT_CREDENTIALS",
                    }
                },
            }
        },
    }


def create_harness(
    sess: boto3.Session,
    *,
    harness_name: str,
    execution_role_arn: str,
    model_id: str,
    tools: list[dict[str, Any]],
    system_prompt: str = SYSTEM_PROMPT,
) -> dict[str, Any]:
    """Submit CreateHarness with a caller-supplied tools list.

    Caller is responsible for constructing the tool block(s) via
    ``build_remote_mcp_tool`` or ``build_agentcore_gateway_tool`` (or
    any other valid HarnessTool variant). This keeps the topology-
    specific tool-wiring decision in the caller, not buried in here.
    """
    ctrl = sess.client("bedrock-agentcore-control")
    payload: dict[str, Any] = {
        "harnessName": harness_name,
        "executionRoleArn": execution_role_arn,
        "clientToken": str(uuid.uuid4()),
        "model": {
            "bedrockModelConfig": {
                # Per-response output cap. Claude Sonnet 4.5 hard-stops at
                # 64K, Claude Opus 4.7 at 32K, Amazon Nova Pro at ~5K, and
                # Llama 3.3 70B at 8K. Anything higher than the model's
                # cap surfaces as ``ValidationException: maximum tokens …
                # exceeds the model limit of <N>`` from the underlying
                # ConverseStream call — Harness doesn't pre-validate.
                # 8192 is the sweet spot: comfortably under every catalogue
                # model's limit AND large enough for multi-paragraph
                # reasoning + several tool calls in one turn. The full
                # 64K Sonnet ceiling is rarely useful for an agent loop
                # (each turn is one tool-or-reply, not a long-form essay)
                # and trades headroom for portability across the model
                # picker in step 11.
                "modelId": model_id,
                "maxTokens": 8192,
                "temperature": 0.2,
            },
        },
        "systemPrompt": [{"text": system_prompt}],
        "tools": tools,
    }
    info(f"Calling CreateHarness for {harness_name}…")
    resp = ctrl.create_harness(**payload)
    return resp["harness"]


def poll_harness_ready(sess: boto3.Session, harness_id: str, timeout_s: int = 300) -> dict[str, Any]:
    ctrl = sess.client("bedrock-agentcore-control")
    sp = Spinner("Waiting for Harness to reach READY").start()
    deadline = time.time() + timeout_s
    last: dict[str, Any] = {}
    while time.time() < deadline:
        try:
            last = ctrl.get_harness(harnessId=harness_id)["harness"]
        except ClientError as e:
            sp.stop()
            err(f"GetHarness failed: {e}")
            return last
        status = last.get("status", "UNKNOWN")
        if status in ("READY", "ACTIVE"):
            sp.stop(f"{GREEN}[OK]{NC}    Harness status = {status}")
            return last
        if status in ("FAILED", "DELETE_FAILED", "CREATE_FAILED"):
            sp.stop(f"{RED}[ERROR]{NC} Harness status = {status}")
            return last
        time.sleep(3)
    sp.stop(f"{YELLOW}[WARN]{NC}  Timed out waiting for READY. Last status = {last.get('status')}")
    return last


def get_harness(sess: boto3.Session, harness_id: str) -> Optional[dict[str, Any]]:
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        return ctrl.get_harness(harnessId=harness_id)["harness"]
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            return None
        raise


def delete_harness(sess: boto3.Session, harness_id: str) -> None:
    ctrl = sess.client("bedrock-agentcore-control")
    try:
        ctrl.delete_harness(harnessId=harness_id)
        ok(f"DeleteHarness submitted for {harness_id}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            info(f"Harness {harness_id} already absent.")
        else:
            warn(f"Could not delete harness {harness_id}: {e}")


# ──────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────

def _load_env_file(path: Path) -> dict[str, str]:
    """Read a KEY=VALUE .env file. Treats whitespace-only / 'NOT_SET' as absent.

    Mirrors the behaviour of integrations/aws/bedrock-agentcore/aws_mcp_operations.py
    so the same .env can drive both deployments if the operator chooses.
    """
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        # Strip an inline comment ONLY when there's whitespace before the
        # `#` — values like `Secret#1` are legitimate.
        value = v
        for i, ch in enumerate(value):
            if ch == "#" and i > 0 and value[i - 1] in (" ", "\t"):
                value = value[:i]
                break
        value = value.strip().strip('"').strip("'")
        if not value or value == "NOT_SET":
            continue
        out[k.strip()] = value
    return out


def _discover_env_file(explicit: Optional[str] = None) -> Optional[Path]:
    """Find the .env file to load, mirroring aws_mcp_operations.py.

    Precedence: explicit ``--env-file`` flag → ``SCRIPT_DIR/.env`` →
    ``Path.cwd()/.env`` → ``SCRIPT_DIR/env.properties`` →
    ``Path.cwd()/env.properties``. Returns ``None`` when nothing
    matched so the caller falls back to interactive prompts.
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            err(f"--env-file {p} does not exist.")
            sys.exit(1)
        return p
    candidates = [
        SCRIPT_DIR / ".env",
        Path.cwd() / ".env",
        SCRIPT_DIR / "env.properties",
        Path.cwd() / "env.properties",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _resolve_env_value(args: argparse.Namespace, env: dict[str, str], *keys: str) -> str:
    """Pick the first non-empty value across CLI arg → process env → .env → ""."""
    for k in keys:
        cli_attr = k.lower()
        # Hyphens collapse on argparse (e.g. --client-id → args.client_id).
        cli_val = getattr(args, cli_attr, None)
        if cli_val:
            return str(cli_val).strip()
        proc = os.environ.get(k, "").strip()
        if proc:
            return proc
        env_val = env.get(k, "").strip()
        if env_val:
            return env_val
    return ""


def _load_env_config(args: argparse.Namespace) -> dict[str, str]:
    """Load Zscaler creds + optional MCP feature flags from .env / env / args.

    Discovery order matches integrations/aws/bedrock-agentcore: an
    explicit ``--env-file`` flag wins, otherwise script dir > cwd >
    ``env.properties`` template (in either dir). Auth / host-validation /
    transport flags are read straight from the resolved file so the
    operator's ``.env`` always wins — the container is launched with
    *exactly* the values the operator set (or sensible defaults when
    unset).

    Returns a dict keyed by short names used elsewhere in the script.
    Empty strings mean "not provided" — callers decide whether to prompt
    or fail. The resolved env-file path is stored under the special
    ``__env_file__`` key for downstream display.
    """
    env_path = _discover_env_file(getattr(args, "env_file", None))
    env = _load_env_file(env_path) if env_path else {}
    # Short-key view, used for prompting and AWS-API calls in this
    # script. CLI flags (--client-id etc.) can override .env here, but
    # they NEVER reach the container's environment — only values
    # actually present in .env do. That's enforced in
    # _build_container_env_vars.
    cfg = {
        "client_id":         _resolve_env_value(args, env, "ZSCALER_CLIENT_ID"),
        "client_secret":     _resolve_env_value(args, env, "ZSCALER_CLIENT_SECRET"),
        "customer_id":       _resolve_env_value(args, env, "ZSCALER_CUSTOMER_ID"),
        "vanity_domain":     _resolve_env_value(args, env, "ZSCALER_VANITY_DOMAIN"),
        "image_uri":         _resolve_env_value(args, env, "ZSCALER_MCP_IMAGE_URI"),
        "mcp_url":           _resolve_env_value(args, env, "MCP_URL"),
        "model_id":          _resolve_env_value(args, env, "MODEL_ID"),
        "region":            _resolve_env_value(args, env, "AWS_REGION"),
    }
    cfg["__env_file__"] = str(env_path) if env_path else ""
    cfg["__raw_env__"] = env  # type: ignore[assignment]
    return cfg


def _ensure_zscaler_creds_interactive(cfg: dict[str, str], *, require_all: bool) -> None:
    """Fill in missing Zscaler credentials by prompting.

    ``require_all`` toggles whether ``customer_id`` and ``vanity_domain``
    are mandatory. They're needed for the ECS Express path (the MCP
    server itself talks to Zscaler OneAPI) but not when the operator
    already has a running MCP server elsewhere and only needs the
    Token Vault to hold the Basic credentials.
    """
    if not cfg["client_id"]:
        cfg["client_id"] = prompt("ZSCALER_CLIENT_ID")
    if not cfg["client_secret"]:
        cfg["client_secret"] = prompt("ZSCALER_CLIENT_SECRET", secret=True)
    if require_all and not cfg["customer_id"]:
        cfg["customer_id"] = prompt("ZSCALER_CUSTOMER_ID")
    if require_all and not cfg["vanity_domain"]:
        cfg["vanity_domain"] = prompt("ZSCALER_VANITY_DOMAIN")
    missing = [
        k for k in (
            ["client_id", "client_secret"]
            + (["customer_id", "vanity_domain"] if require_all else [])
        )
        if not cfg[k]
    ]
    if missing:
        err(f"Missing Zscaler credentials: {', '.join(missing)}")
        sys.exit(1)


def _normalise_mcp_url(raw: str) -> str:
    """Ensure the MCP URL ends with /mcp (no trailing slash).

    The AgentCore Harness console (and `remote_mcp` tool) stores the
    endpoint without a trailing slash. FastMCP's streamable-http mount
    serves both `/mcp` (returns 307 → `/mcp/`) and `/mcp/`, but the MCP
    client built into Harness issues POST requests and won't follow a
    307 on a non-idempotent method, so the trailing slash variant
    actually fails to initialise with a `TaskGroup (1 sub-exception)`.
    Mirroring the console form keeps us drift-free with what AWS
    renders in the Add Tool dialog.
    """
    url = raw.strip().rstrip("/")
    if not url:
        return ""
    if not url.endswith("/mcp"):
        url = url + "/mcp"
    return url


# ──────────────────────────────────────────────────────────────────────────
# Gateway topology orchestrators (PR #48)
# ──────────────────────────────────────────────────────────────────────────

def _deploy_gateway_topology(
    args: argparse.Namespace,
    *,
    sess: boto3.Session,
    region: str,
    account_id: str,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """End-to-end Gateway-topology provisioning.

    Returns a state dict to merge into the .aws-harness-state.json. The
    caller (cmd_deploy) is responsible for the topology-shared steps
    (Harness exec role, model selection, CreateHarness, summary print).

    Step ordering chosen so a partial failure leaves a tractable state:
      5a. Container image source.
      5b. Zscaler Secrets Manager secret (reuses ECS-path helpers).
      6.  Cognito User Pool + Resource Server + App Client + Domain.
      7.  OAuth2 credential provider in Token Vault (Cognito-backed).
      8.  Runtime IAM exec role + AgentCore Runtime (auth: jwt → Cognito).
      9.  Gateway IAM role.
      10. Gateway + mcpServer target (outbound: OAuth2 → Cognito).

    After each resource is created, ``persist_partial_state`` writes the
    current state to ``.aws-harness-state.json`` with ``state_partial=True``
    so a Ctrl-C, network drop, or downstream ValidationException leaves
    enough of a paper trail for ``cmd_destroy`` to clean up. The state
    is only marked ``state_partial=False`` when ``cmd_deploy`` reaches
    the final CreateHarness step and calls ``finalize_state``.
    """
    raw_env = cfg["__raw_env__"]

    # Seed an initial state file so `destroy` can find SOMETHING even if
    # we crash in Step 5 before any AWS resource is created.
    persist_partial_state(
        {
            "aws_region": region,
            "aws_account_id": account_id,
            "deploy_started_at": _utc_now_iso(),
        },
        phase="started",
        topology="gateway",
    )

    # ── Step 5a: Container image ─────────────────────────────────────────
    step("Step 5: Container image source")
    image_override = (cfg.get("image_uri") or "").strip()
    if image_override:
        image_uri = image_override
        info(f"Image: {image_uri} (overridden via ZSCALER_MCP_IMAGE_URI)")
    else:
        image_uri = MARKETPLACE_IMAGE
        info(f"Image: {image_uri} (AWS Marketplace default)")
        info("→ Subscribing to the Zscaler MCP Server in AWS Marketplace is required.")

    # AgentCore Runtime enforces same-region ECR. Validate BEFORE we
    # provision any IAM role so a mismatch costs nothing to recover from.
    _assert_runtime_image_region_compatible(image_uri, region)

    persist_partial_state({"image_uri": image_uri}, phase="image-resolved", topology="gateway")

    # ── Step 5b: Zscaler credentials → Secrets Manager ──────────────────
    # Same two-mode pattern as the ECS path (UseExisting / CreateNew /
    # plaintext) — the Runtime container reads the secret via boto3 at
    # boot using its executionRoleArn (zscaler_mcp/config.py picks it up
    # from ZSCALER_SECRET_NAME).
    secret_name: Optional[str] = None
    secret_arn: Optional[str] = None
    secret_managed_externally = False

    existing_secret_name = (raw_env.get("ZSCALER_SECRET_NAME") or "").strip()
    if args.no_secrets_manager:
        use_secrets_manager = False
    elif existing_secret_name:
        use_secrets_manager = True
    else:
        step("Step 5b: Zscaler credentials delivery")
        info("Two ways to ship credentials to the Runtime container:")
        info("  • Secrets Manager (default): values stored encrypted, fetched at boot")
        info("    by the container via boto3 (uses the Runtime exec role's IAM grants).")
        info("  • Plaintext env: ZSCALER_CLIENT_SECRET written to environmentVariables.")
        info("    Visible via GetAgentRuntime and CloudTrail — only for dev/debugging.")
        use_secrets_manager = prompt_bool(
            "Use AWS Secrets Manager for Zscaler credentials?", True
        )

    if not use_secrets_manager:
        step("Step 5b: Zscaler credentials (PLAINTEXT)")
        warn(
            "Plaintext mode: ZSCALER_CLIENT_SECRET will be in the Runtime's "
            "environmentVariables map. Production deploys should switch to "
            "Secrets Manager."
        )
    elif existing_secret_name:
        step("Step 5b: Zscaler credentials → Secrets Manager (UseExisting)")
        info(
            f"ZSCALER_SECRET_NAME={existing_secret_name} set in .env — "
            "treating as operator-managed. The script will reference it but "
            "will NOT overwrite its value or delete it on destroy."
        )
        secret_managed_externally = True
        secret_name, secret_arn, _ = ensure_zscaler_secret(
            sess, existing_secret_name, raw_env, reuse_existing=True,
        )
    else:
        step("Step 5b: Zscaler credentials → Secrets Manager (CreateNew)")
        merged_env = dict(raw_env)
        for cli_key, env_key in (
            ("client_id", "ZSCALER_CLIENT_ID"),
            ("client_secret", "ZSCALER_CLIENT_SECRET"),
            ("customer_id", "ZSCALER_CUSTOMER_ID"),
            ("vanity_domain", "ZSCALER_VANITY_DOMAIN"),
        ):
            if cfg.get(cli_key):
                merged_env[env_key] = cfg[cli_key]
        secret_name, secret_arn, _ = ensure_zscaler_secret(
            sess, args.secret_name, merged_env, reuse_existing=False,
        )

    persist_partial_state(
        {
            "zscaler_secret_name":              secret_name,
            "zscaler_secret_arn":               secret_arn,
            "zscaler_secret_managed_externally": secret_managed_externally,
            "zscaler_secret_use_secrets_manager": use_secrets_manager,
        },
        phase="secret-ready",
        topology="gateway",
    )

    # ── Step 6: Cognito (User Pool + Resource Server + App Client + Domain)
    step("Step 6: Provision Amazon Cognito (inbound IdP for Gateway)")
    pool_id = ensure_cognito_user_pool(sess, args.cognito_user_pool_name)
    audience = ensure_cognito_resource_server(
        sess,
        user_pool_id=pool_id,
        identifier=args.cognito_resource_server_identifier,
        scope_name=args.cognito_scope_name,
    )
    cognito_client_id, cognito_client_secret = ensure_cognito_app_client(
        sess,
        user_pool_id=pool_id,
        name=args.cognito_app_client_name,
        allowed_scope=f"{audience}/{args.cognito_scope_name}",
    )
    # Domain prefix is suffixed with account ID so two tenants don't
    # collide on the global Cognito prefix namespace.
    full_domain_prefix = f"{args.cognito_domain_prefix}-{account_id[-12:]}"
    domain_prefix = ensure_cognito_user_pool_domain(
        sess, user_pool_id=pool_id, domain_prefix=full_domain_prefix,
    )
    discovery_url = _cognito_discovery_url(region, pool_id)
    ok(f"Cognito ready. Pool={pool_id}  audience={audience}  client={cognito_client_id}")
    info(f"  OIDC discovery: {discovery_url}")
    info(f"  Token endpoint: {_cognito_token_endpoint(region, domain_prefix)}")

    persist_partial_state(
        {
            "cognito_user_pool_id":             pool_id,
            "cognito_resource_server_identifier": audience,
            "cognito_audience":                 audience,
            "cognito_scope_name":               args.cognito_scope_name,
            "cognito_app_client_id":            cognito_client_id,
            "cognito_app_client_name":          args.cognito_app_client_name,
            "cognito_domain_prefix":            domain_prefix,
            "cognito_discovery_url":            discovery_url,
            "cognito_token_endpoint":           _cognito_token_endpoint(region, domain_prefix),
        },
        phase="cognito-ready",
        topology="gateway",
    )

    # ── Step 7: OAuth2 credential provider in Token Vault ────────────────
    step("Step 7: Provision OAuth2 credential provider (Token Vault)")
    info(
        "One provider serves both auth legs: Harness→Gateway "
        "(HarnessGatewayOutboundAuth.oauth) and Gateway→Runtime "
        "(target outbound credentialProvider)."
    )
    oauth_provider_arn = ensure_oauth2_credential_provider(
        sess,
        name=args.oauth_provider_name,
        discovery_url=discovery_url,
        client_id=cognito_client_id,
        client_secret=cognito_client_secret,
    )

    persist_partial_state(
        {
            "oauth_provider_name": args.oauth_provider_name,
            "oauth_provider_arn":  oauth_provider_arn,
        },
        phase="oauth-provider-ready",
        topology="gateway",
    )

    # ── Step 8: Runtime IAM role + AgentCore Runtime ────────────────────
    step("Step 8: Provision AgentCore Runtime")
    runtime_exec_role_arn = ensure_runtime_execution_role(
        sess,
        role_name=args.runtime_execution_role_name,
        region=region,
        secret_arn=secret_arn,
        image_uri=image_uri,
    )
    # Cognito M2M tokens carry a `scope` claim of the form
    # ``<resource-server-identifier>/<scope-name>`` — e.g. ``zscaler-mcp/invoke``.
    # That's what the JWT authorizers validate via `allowedScopes` (since
    # Cognito client_credentials tokens don't carry `aud`). Build it once
    # here so the Runtime + Gateway authorizers agree on the exact value.
    cognito_scope = f"{audience}/{args.cognito_scope_name}"

    runtime_env = _build_runtime_env_vars(
        raw_env,
        secret_name=secret_name,
    )
    if not use_secrets_manager:
        # Plaintext path — inject the credentials directly into the
        # Runtime environment map (no Secrets Manager fetch at boot).
        for env_key in _ZSCALER_CRED_ENV_KEYS:
            val = (raw_env.get(env_key) or "").strip()
            if val:
                runtime_env[env_key] = val
    inbound_auth_kwargs = _build_runtime_inbound_auth_kwargs(
        discovery_url=discovery_url,
        scope=cognito_scope,
        allowed_client_id=cognito_client_id,
    )
    # Persist the Runtime exec role NAME before we call ensure_runtime — the
    # role is what the runtime depends on, and if create_agent_runtime fails
    # mid-call (validation error, region mismatch slipping past pre-flight,
    # etc.) we still need to know to clean up the role on destroy.
    persist_partial_state(
        {"runtime_execution_role_name": args.runtime_execution_role_name},
        phase="runtime-role-ready",
        topology="gateway",
    )

    runtime_desc = ensure_runtime(
        sess,
        runtime_name=args.runtime_name,
        image_uri=image_uri,
        execution_role_arn=runtime_exec_role_arn,
        env=runtime_env,
        inbound_auth_kwargs=inbound_auth_kwargs,
    )
    runtime_arn = runtime_desc["agentRuntimeArn"]
    runtime_id = runtime_desc["agentRuntimeId"]
    runtime_mcp_url = build_runtime_mcp_url(runtime_arn)
    ok(f"Runtime ready. id={runtime_id}")

    persist_partial_state(
        {
            "runtime_name":         args.runtime_name,
            "runtime_id":           runtime_id,
            "runtime_arn":          runtime_arn,
            "runtime_mcp_url":      runtime_mcp_url,
        },
        phase="runtime-ready",
        topology="gateway",
    )

    # ── Step 9: Gateway service role ─────────────────────────────────────
    step("Step 9: Provision Gateway service role")
    gateway_role_arn = ensure_gateway_role(
        sess, role_name=args.gateway_role_name, runtime_arn=runtime_arn,
    )

    persist_partial_state(
        {"gateway_role_name": args.gateway_role_name},
        phase="gateway-role-ready",
        topology="gateway",
    )

    # ── Step 10: Gateway + Target ────────────────────────────────────────
    step("Step 10: Provision AgentCore Gateway + Runtime target")
    gateway_desc = ensure_gateway(
        sess,
        name=args.gateway_name,
        role_arn=gateway_role_arn,
        cognito_discovery_url=discovery_url,
        cognito_scope=cognito_scope,
        cognito_client_id=cognito_client_id,
    )
    gateway_id = gateway_desc["gatewayId"]
    gateway_arn = gateway_desc.get("gatewayArn", "")
    gateway_url = gateway_desc.get("gatewayUrl", "")

    persist_partial_state(
        {
            "gateway_name":           args.gateway_name,
            "gateway_id":             gateway_id,
            "gateway_arn":            gateway_arn,
            "gateway_url":            gateway_url,
            "gateway_target_name":    args.gateway_target_name,
        },
        phase="gateway-ready",
        topology="gateway",
    )

    target_desc = ensure_gateway_target(
        sess,
        gateway_id=gateway_id,
        name=args.gateway_target_name,
        runtime_arn=runtime_arn,
        oauth_provider_arn=oauth_provider_arn,
        cognito_scope=cognito_scope,
    )
    target_id = target_desc["targetId"]
    # ensure_gateway_target waits for READY and returns the final descriptor.
    # If the target ended in FAILED (e.g. JWT validation against the Runtime
    # failed on the smoke-test that AgentCore runs at target-create time),
    # bail HARD with the actual API-reported reason — moving on past a
    # FAILED target produces a working Harness that 500s on every tool call,
    # which is much harder to diagnose later than a deploy-time failure.
    target_status = target_desc.get("status", "UNKNOWN")
    if target_status != "READY":
        reasons = target_desc.get("statusReasons") or ["(no status reason returned by AgentCore)"]
        err(f"Gateway target {target_id} ended in status={target_status} — aborting.")
        for reason in reasons:
            err(f"  reason: {reason}")
        err(
            "Common causes:\n"
            "  • The Runtime's customJWTAuthorizer rejects Cognito tokens "
            "(check allowedAudience vs. allowedClients/allowedScopes — "
            "Cognito M2M tokens have no aud claim, so allowedAudience can never match).\n"
            "  • The OAuth2 credential provider's discovery URL or client_id/secret "
            "are stale relative to the Cognito User Pool.\n"
            "  • Cognito App Client's AllowedOAuthScopes doesn't include the requested scope."
        )
        err(
            f"To clean up before retry:\n"
            f"  aws bedrock-agentcore-control delete-gateway-target "
            f"--gateway-identifier {gateway_id} --target-id {target_id} --region {region}"
        )
        # Stamp the target ID into the partial state file BEFORE we exit so
        # the user's next `destroy` run can find it (the script tries the
        # ensure_gateway_target FAILED-target-recreate path on its own first,
        # but if the user explicitly wants to back out, this gives destroy
        # the breadcrumb).
        persist_partial_state(
            {
                "gateway_target_id":      target_id,
                "gateway_target_status":  target_status,
            },
            phase="gateway-target-failed",
            topology="gateway",
        )
        sys.exit(1)
    ok(f"Gateway target ready. id={target_id}")

    persist_partial_state(
        {"gateway_target_id": target_id},
        phase="gateway-target-ready",
        topology="gateway",
    )

    return {
        # Topology marker for cmd_destroy + status to branch correctly.
        "topology": "gateway",

        # Cognito
        "cognito_user_pool_id":             pool_id,
        "cognito_resource_server_identifier": audience,
        "cognito_audience":                 audience,
        "cognito_scope_name":               args.cognito_scope_name,
        "cognito_app_client_id":            cognito_client_id,
        "cognito_app_client_name":          args.cognito_app_client_name,
        "cognito_domain_prefix":            domain_prefix,
        "cognito_discovery_url":            discovery_url,
        "cognito_token_endpoint":           _cognito_token_endpoint(region, domain_prefix),

        # OAuth2 credential provider
        "oauth_provider_name":              args.oauth_provider_name,
        "oauth_provider_arn":               oauth_provider_arn,

        # Runtime
        "runtime_name":                     args.runtime_name,
        "runtime_id":                       runtime_id,
        "runtime_arn":                      runtime_arn,
        "runtime_mcp_url":                  runtime_mcp_url,
        "runtime_execution_role_name":      args.runtime_execution_role_name,

        # Gateway
        "gateway_name":                     args.gateway_name,
        "gateway_id":                       gateway_id,
        "gateway_arn":                      gateway_arn,
        "gateway_url":                      gateway_url,
        "gateway_role_name":                args.gateway_role_name,
        "gateway_target_name":              args.gateway_target_name,
        "gateway_target_id":                target_id,

        # Image + secrets carry-over (so destroy / status / summary works)
        "image_uri":                        image_uri,
        "zscaler_secret_name":              secret_name,
        "zscaler_secret_arn":               secret_arn,
        "zscaler_secret_managed_externally": secret_managed_externally,
    }


def _destroy_gateway_topology(
    args: argparse.Namespace,
    *,
    sess: boto3.Session,
    state: dict[str, Any],
) -> None:
    """Reverse-order teardown for the Gateway topology.

    Order matters because of inter-resource dependencies:
        gateway target → gateway → gateway role → oauth provider
            → runtime → runtime role → cognito (domain → pool)
            → secret (last; only if WE created it)
    """
    gateway_id           = state.get("gateway_id", "")
    gateway_name         = state.get("gateway_name", "")
    gateway_target_name  = state.get("gateway_target_name", "")
    gateway_role_name    = state.get("gateway_role_name", "")
    oauth_provider_name  = state.get("oauth_provider_name", "")
    runtime_name         = state.get("runtime_name", "")
    runtime_role_name    = state.get("runtime_execution_role_name", "")
    pool_id              = state.get("cognito_user_pool_id", "")
    domain_prefix        = state.get("cognito_domain_prefix", "")
    secret_name          = state.get("zscaler_secret_name", "")
    secret_managed_externally = bool(state.get("zscaler_secret_managed_externally"))

    if gateway_id and gateway_target_name:
        step("Deleting Gateway target")
        delete_gateway_target(sess, gateway_id=gateway_id, name=gateway_target_name)
        # Small grace period — target delete is async on Gateway's side
        # and the Gateway delete a few lines down will 409 if the target
        # is still draining.
        time.sleep(5)

    if gateway_name:
        step("Deleting Gateway")
        delete_gateway(sess, gateway_name)

    if not args.keep_role and gateway_role_name:
        step("Deleting Gateway service role")
        delete_gateway_role(sess, gateway_role_name)

    if oauth_provider_name:
        step("Deleting OAuth2 credential provider")
        delete_oauth2_credential_provider(sess, oauth_provider_name)

    if runtime_name:
        step("Deleting AgentCore Runtime")
        delete_runtime(sess, runtime_name)

    if not args.keep_role and runtime_role_name:
        step("Deleting Runtime execution role")
        delete_runtime_execution_role(sess, runtime_role_name)

    if pool_id and not args.keep_cognito:
        step("Deleting Cognito User Pool (cascading: domain → pool)")
        delete_cognito_user_pool(
            sess, user_pool_id=pool_id, domain_prefix=domain_prefix,
        )
    elif pool_id:
        info(f"Keeping Cognito User Pool {pool_id} (--keep-cognito).")

    # Secret last — see ECS-path destroy for the same reasoning.
    if secret_name and not secret_managed_externally:
        if args.keep_secret:
            info(f"Keeping Zscaler Secrets Manager secret {secret_name} (--keep-secret).")
        else:
            step("Deleting Zscaler Secrets Manager secret")
            delete_zscaler_secret(sess, secret_name, force=args.force_secret_delete)
    elif secret_name and secret_managed_externally:
        info(
            f"Keeping Zscaler Secrets Manager secret {secret_name} "
            "(operator-managed via ZSCALER_SECRET_NAME in .env)."
        )


def _resolve_topology(args: argparse.Namespace, raw_env: dict[str, str]) -> str:
    """Pick the deployment topology with the same precedence as other
    values: CLI flag > env / .env > interactive prompt > default.

    Returns one of ``"ecs"`` or ``"gateway"``. The default
    (``DEFAULT_TOPOLOGY = "ecs"``) is intentional — it preserves PR #47
    behaviour for anyone re-running an old command line.
    """
    cli = (getattr(args, "topology", "") or "").strip().lower()
    if cli:
        if cli not in SUPPORTED_TOPOLOGIES:
            err(f"--topology {cli!r} not supported. Pick one of: {SUPPORTED_TOPOLOGIES}")
            sys.exit(1)
        return cli

    env_val = (raw_env.get("TOPOLOGY") or os.environ.get("TOPOLOGY") or "").strip().lower()
    if env_val:
        if env_val not in SUPPORTED_TOPOLOGIES:
            err(f"TOPOLOGY={env_val!r} not supported. Pick one of: {SUPPORTED_TOPOLOGIES}")
            sys.exit(1)
        info(f"Topology from env: {env_val}")
        return env_val

    # Interactive prompt — only triggered when nothing was specified.
    step("Pick deployment topology")
    print(
        f"  {BOLD}ecs{NC}      MCP server on Amazon ECS Express Mode; Harness uses\n"
        "           remote_mcp tool with Basic-auth via Token Vault. Simplest.\n"
        f"  {BOLD}gateway{NC}  MCP server on AgentCore Runtime; Harness uses\n"
        "           agentcore_gateway tool through an AgentCore Gateway\n"
        "           fronted by Amazon Cognito. Eliminates ALB/Fargate.\n"
    )
    idx = prompt_choice(
        "Topology",
        [
            "ecs      (default — current PR #47 deployment)",
            "gateway  (PR #48 — Runtime + Gateway + Cognito)",
        ],
        default_idx=0,
    )
    chosen = SUPPORTED_TOPOLOGIES[idx]
    info(f"Topology: {chosen}")
    return chosen


def cmd_deploy(args: argparse.Namespace) -> None:
    print_zscaler_logo()

    state = load_state()
    if state.get("harness_id"):
        warn(
            f"State file already references a harness ({state['harness_id']}). "
            "Re-deploying will create a NEW harness; the previous one will be left in place. "
            "Run `destroy` first if you want a clean redeploy."
        )
        if not prompt_bool("Continue and create a new harness?", default=False):
            info("Aborted.")
            return

    # Fail fast on an invalid harness name — the AgentCore API enforces
    # [a-zA-Z][a-zA-Z0-9_]{0,39} (letters, digits, underscores; no
    # hyphens) and we don't want to learn that 4 minutes into a deploy.
    if not HARNESS_NAME_PATTERN.match(args.harness_name):
        err(
            f"--harness-name {args.harness_name!r} is invalid. "
            f"AgentCore requires {HARNESS_NAME_PATTERN.pattern} — letters, "
            "digits, underscores only (no hyphens), max 40 chars. "
            "Example: zscaler_mcp_harness."
        )
        sys.exit(1)

    # ── Step 1: Load configuration ──────────────────────────────────────
    step("Step 1: Load configuration (.env / CLI / interactive)")
    cfg = _load_env_config(args)
    env_file = cfg.get("__env_file__") or ""
    if env_file:
        info(f"Loaded env overrides from {env_file}")
    else:
        warn(
            "No .env or env.properties found in the script dir or cwd "
            "— falling back to CLI flags + interactive prompts. Use "
            "--env-file <path> to point at a specific file."
        )
    if cfg.get("region"):
        info(f"AWS_REGION (from env) = {cfg['region']}")

    # ── Step 2: AWS session ─────────────────────────────────────────────
    step("Step 2: Verify AWS credentials")
    region = args.region or cfg.get("region") or DEFAULT_REGION
    sess = get_session(region, profile=args.profile)
    account_id = get_account_id(sess)
    ok(f"AWS account = {account_id}   region = {region}")

    # ── Topology pick (PR #48) ──────────────────────────────────────────
    # Default is "ecs" so PR #47 deploy commands still do exactly what
    # they used to. "gateway" hands off to _deploy_gateway_topology()
    # which provisions Cognito + Runtime + Gateway and skips Steps 3–9
    # of the ECS path entirely.
    topology = _resolve_topology(args, cfg["__raw_env__"])

    if topology == "gateway":
        # ── Step 3 (Gateway): Zscaler credentials ──────────────────────
        # Runtime container talks to Zscaler OneAPI directly (same as ECS
        # path) so we need all four creds. Equivalent to the ECS path's
        # require_all_creds=True branch.
        step("Step 3: Zscaler OneAPI credentials")
        _ensure_zscaler_creds_interactive(cfg, require_all=True)
        ok("OneAPI credentials loaded (4 values).")

        # ── Steps 5–10: Cognito / Runtime / Gateway provisioning ───────
        ecs_state = _deploy_gateway_topology(
            args, sess=sess, region=region, account_id=account_id, cfg=cfg,
        )
        # MCP URL surfaced in the summary points at the Gateway, since
        # that's where Harness actually talks. The Gateway URL is what
        # downstream non-Harness clients (e.g. a future Strands agent
        # using the same Gateway) would use too.
        mcp_url = ecs_state.get("gateway_url") or ecs_state.get("runtime_mcp_url", "")
        mcp_host_kind = "gateway"

        # ── Step 11 (Gateway): Pick model ──────────────────────────────
        step("Step 11: Pick a Bedrock reasoning model")
        env_model = cfg.get("model_id") or args.model_id
        if env_model:
            model_id = env_model
            info(f"Model (from env / --model-id): {model_id}")
        else:
            labels = [f"{m['label']}  —  {m['note']}" for m in MODEL_CATALOGUE]
            idx = prompt_choice("Available models", labels, default_idx=0)
            model_id = MODEL_CATALOGUE[idx]["id"]
        ok(f"Selected model: {model_id}")

        # ── Step 12 (Gateway): Harness exec role + CreateHarness ───────
        step("Step 12: Provision Harness execution role")
        role_arn = ensure_execution_role(sess, args.role_name, region, args.harness_name)

        step("Step 13: CreateHarness (agentcore_gateway tool)")
        tools = [
            build_agentcore_gateway_tool(
                ecs_state["gateway_arn"],
                ecs_state["oauth_provider_arn"],
            )
        ]
        try:
            harness = create_harness(
                sess,
                harness_name=args.harness_name,
                execution_role_arn=role_arn,
                model_id=model_id,
                tools=tools,
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            msg = e.response.get("Error", {}).get("Message", str(e))
            err(f"CreateHarness failed [{code}]: {msg}")
            sys.exit(1)
        except EndpointConnectionError as e:
            err(f"Could not reach bedrock-agentcore-control in {region}: {e}")
            sys.exit(1)

        harness_id = harness["harnessId"]
        harness_arn = harness["arn"]
        ok(f"CreateHarness submitted. harnessId = {harness_id}")
        final = poll_harness_ready(sess, harness_id)

        persisted: dict[str, Any] = {
            "region": region,
            "harness_id": harness_id,
            "harness_arn": harness_arn,
            "harness_name": args.harness_name,
            "execution_role_arn": role_arn,
            "role_name": args.role_name,
            # The Token Vault Basic-auth provider isn't used in this
            # topology (we use the OAuth2 provider instead), but the
            # state schema keeps the field so cmd_status / cmd_destroy
            # don't have to special-case it. Empty string = absent.
            "credential_provider_name": "",
            "credential_provider_arn": "",
            "mcp_url": mcp_url,
            "mcp_host_kind": mcp_host_kind,
            "model_id": model_id,
            "status": final.get("status", "UNKNOWN"),
            "deployed_at": datetime.now(timezone.utc).isoformat(),
        }
        persisted.update(ecs_state)
        # Final state write — flips state_partial=False so subsequent
        # `status` and `destroy` runs know the deploy crossed the finish line.
        finalize_state(persisted)

        _print_deploy_summary(
            region=region,
            harness_id=harness_id,
            harness_arn=harness_arn,
            mcp_url=mcp_url,
            mcp_host_kind=mcp_host_kind,
            ecs_state=ecs_state,
            model_id=model_id,
            role_arn=role_arn,
            provider_arn=ecs_state["oauth_provider_arn"],
        )
        return

    # ── Step 3: Pick MCP source ─────────────────────────────────────────
    # Harness's remote_mcp tool sends only static headers, so the MCP host
    # cannot require SigV4. Default path: deploy the same zscaler-mcp-server
    # container to Amazon ECS Express Mode (auto-managed ALB + HTTPS, ~3-4
    # min). Alternative: point at a pre-existing non-SigV4 MCP endpoint
    # (Cloud Run, Azure Container Apps, EC2 + nginx, on-prem with ngrok,
    # etc.) via MCP_URL.
    step("Step 3: Pick the MCP source for Harness")
    discovered = discover_runtime_url(region)
    if discovered:
        info(f"Found sibling AgentCore Runtime deployment (stack '{discovered['stack_name']}').")
        info(f"  URL: {discovered['url']}")
        if url_looks_sigv4_only(discovered["url"]):
            warn(
                "Sibling URL is SigV4-protected (AgentCore Runtime invoke endpoint). "
                "Harness's remote_mcp can't sign with SigV4, so this URL will return 403. "
                "Recommended: let this script deploy the MCP server to ECS Express Mode instead."
            )

    explicit_url = cfg.get("mcp_url") or args.mcp_url
    if explicit_url:
        info(f"Using MCP_URL from env / --mcp-url: {explicit_url}")
        mcp_url = _normalise_mcp_url(explicit_url)
        mcp_host_kind = "external"
    else:
        choices = [
            "Deploy a fresh Zscaler MCP server to Amazon ECS Express Mode (recommended)",
            "I already have a non-SigV4 MCP URL (paste it now)",
        ]
        idx = prompt_choice("How should Harness reach the MCP server?", choices, default_idx=0)
        if idx == 1:
            mcp_url = _normalise_mcp_url(prompt("Enter the MCP URL (https://…/mcp)"))
            mcp_host_kind = "external"
        else:
            mcp_url = ""  # filled in after ECS deploy below
            mcp_host_kind = "ecs"

    if mcp_host_kind == "external":
        if not mcp_url.lower().startswith("https://"):
            err("MCP URL must be HTTPS.")
            sys.exit(1)

    # ── Step 4: Zscaler credentials ─────────────────────────────────────
    # When deploying the MCP server ourselves we need all four creds (the
    # server talks to Zscaler OneAPI directly). When attaching to an
    # external URL we only need client_id + client_secret for the Token
    # Vault entry Harness will inject into the outbound Authorization
    # header. The values themselves are never echoed.
    step("Step 4: Zscaler OneAPI credentials")
    require_all_creds = mcp_host_kind == "ecs"
    _ensure_zscaler_creds_interactive(cfg, require_all=require_all_creds)
    needed = ("client_id", "client_secret") + (
        ("customer_id", "vanity_domain") if require_all_creds else ()
    )
    ok(f"OneAPI credentials loaded ({len(needed)} value{'s' if len(needed) != 1 else ''}).")

    # ── Steps 5-8: ECS Express deploy (skipped on the external-URL path) ─
    ecs_state: dict[str, Any] = {}
    if mcp_host_kind == "ecs":
        # Resolution policy: identical to bedrock-agentcore/aws_mcp_operations.py.
        # Default → MARKETPLACE_IMAGE; override → non-empty ZSCALER_MCP_IMAGE_URI
        # (whitespace-only is treated as unset).
        step("Step 5: Container image source")
        image_override = (cfg.get("image_uri") or "").strip()
        if image_override:
            image_uri = image_override
            info(f"Image: {image_uri} (overridden via ZSCALER_MCP_IMAGE_URI)")
            if "709825985650" not in image_uri:
                warn(
                    "Image URI is NOT the AWS Marketplace ECR — make sure it's "
                    "built for linux/amd64 (use `docker buildx build --platform "
                    "linux/amd64 …` on Apple Silicon). The ECS task execution "
                    "role's cross-account ECR policy will be auto-scoped to "
                    "whichever registry account is in the URI."
                )
        else:
            image_uri = MARKETPLACE_IMAGE
            info(f"Image: {image_uri} (AWS Marketplace default)")
            info("→ Subscribing to the Zscaler MCP Server in AWS Marketplace is required.")
            info("  https://aws.amazon.com/marketplace (search 'Zscaler MCP Server')")

        # ── Step 5b: Zscaler credentials delivery ───────────────────────
        # Mirrors the bedrock-agentcore CloudFormation pattern: two
        # well-defined modes plus a plaintext escape hatch. The mode
        # is picked by what's in .env (zero questions if the operator
        # was explicit) or by a single interactive prompt otherwise.
        #
        #   ZSCALER_SECRET_NAME in .env   → UseExisting (no prompt)
        #   --no-secrets-manager flag     → Plaintext   (no prompt)
        #   neither                       → Ask the operator [Y/n]
        #
        # When Secrets Manager IS used, we lean on ECS's native
        # secrets[] block: the ECS agent (which has executionRoleArn)
        # fetches the value at task boot and injects the named JSON
        # keys as regular env vars BEFORE the container starts. The
        # container sees os.environ['ZSCALER_CLIENT_SECRET'] as if it
        # were a plain env var — no boto3, no runtime IAM, no
        # taskRoleArn needed inside the container.
        secret_name: Optional[str] = None
        secret_arn: Optional[str] = None
        secret_keys: list[str] = []
        secret_managed_externally = False

        raw_env = cfg["__raw_env__"]
        existing_secret_name = (raw_env.get("ZSCALER_SECRET_NAME") or "").strip()
        use_secrets_manager: bool
        if args.no_secrets_manager:
            use_secrets_manager = False
        elif existing_secret_name:
            use_secrets_manager = True
        else:
            # No explicit signal in .env or CLI — ask the operator
            # once. Matches the bedrock-agentcore script's "the script
            # asks which one" UX. Default = Yes (the secure choice).
            step("Step 5b: Zscaler credentials delivery")
            info(
                "Two ways to ship credentials to the container:"
            )
            info(
                "  • Secrets Manager (default): values stored encrypted, "
                "injected by the ECS"
            )
            info(
                "    agent at task start. Nothing sensitive in the task "
                "definition or CloudTrail."
            )
            info(
                "  • Plaintext env: ZSCALER_CLIENT_SECRET written directly "
                "to the task def."
            )
            info(
                "    Visible via `aws ecs describe-task-definition` — only "
                "for dev / debugging."
            )
            use_secrets_manager = prompt_bool(
                "Use AWS Secrets Manager for Zscaler credentials?", True
            )

        if not use_secrets_manager:
            step("Step 5b: Zscaler credentials (PLAINTEXT)")
            warn(
                "Plaintext mode: ZSCALER_CLIENT_SECRET will be written "
                "directly to the ECS task definition. Visible to anyone "
                "with ecs:DescribeTaskDefinition and logged in CloudTrail. "
                "Production deploys should switch to Secrets Manager."
            )
        elif existing_secret_name:
            step("Step 5b: Zscaler credentials → Secrets Manager (UseExisting)")
            info(
                f"ZSCALER_SECRET_NAME={existing_secret_name} set in .env — "
                "treating as operator-managed (Terraform / CloudFormation / "
                "console). The script will reference it but will NOT "
                "overwrite its value or delete it on destroy."
            )
            secret_managed_externally = True
            secret_name, secret_arn, secret_keys = ensure_zscaler_secret(
                sess,
                existing_secret_name,
                raw_env,
                reuse_existing=True,
            )
        else:
            step("Step 5b: Zscaler credentials → Secrets Manager (CreateNew)")
            # Merge CLI overrides into the resolved env so a deploy that
            # passed --client-secret on the command line (rather than via
            # .env) still gets the override stored in the secret.
            merged_env = dict(raw_env)
            for cli_key, env_key in (
                ("client_id", "ZSCALER_CLIENT_ID"),
                ("client_secret", "ZSCALER_CLIENT_SECRET"),
                ("customer_id", "ZSCALER_CUSTOMER_ID"),
                ("vanity_domain", "ZSCALER_VANITY_DOMAIN"),
            ):
                if cfg.get(cli_key):
                    merged_env[env_key] = cfg[cli_key]
            secret_name, secret_arn, secret_keys = ensure_zscaler_secret(
                sess,
                args.secret_name,
                merged_env,
                reuse_existing=False,
            )

        # ── Step 6: IAM roles for ECS Express ───────────────────────────
        step("Step 6: Provision ECS task execution + infrastructure roles")
        exec_role_arn = ensure_ecs_task_execution_role(
            sess,
            args.ecs_execution_role_name,
            image_uri,
            region,
            secret_arn=secret_arn,
        )
        infra_role_arn = ensure_ecs_infrastructure_role(
            sess, args.ecs_infrastructure_role_name
        )

        # ── Step 7: ECS cluster + CloudWatch log group ─────────────────
        step("Step 7: Ensure ECS cluster + CloudWatch log group")
        # Surface the choice if the default cluster name already exists.
        # The resolver may mutate args.ecs_cluster_name to a fresh
        # auto-generated or operator-provided name — every downstream
        # call (service create, state file, destroy summary) keys off
        # this attribute, so we update it in place.
        args.ecs_cluster_name = resolve_ecs_cluster_name(
            sess,
            args.ecs_cluster_name,
            default_name=DEFAULT_ECS_CLUSTER_NAME,
        )
        cluster_arn, cluster_created = ensure_ecs_cluster(
            sess, args.ecs_cluster_name
        )
        log_group = args.ecs_log_group or DEFAULT_ECS_LOG_GROUP
        ensure_cloudwatch_log_group(sess, log_group)

        # ── Step 8: ECS Express service ────────────────────────────────
        step("Step 8: Deploy Zscaler MCP server to ECS Express Mode")
        env_vars = _build_container_env_vars(
            cfg["__raw_env__"], secret_keys=secret_keys
        )
        container_secrets = (
            _build_container_secrets(secret_arn, secret_keys)
            if secret_arn and secret_keys
            else None
        )
        # Surface the exact env-var set the container will receive so
        # the operator can audit it (names only; values may include
        # secrets like ZSCALER_CLIENT_SECRET).
        info(
            f"Container env from {cfg.get('__env_file__') or '<none>'}: "
            f"{', '.join(sorted(v['name'] for v in env_vars))}"
        )
        info(f"Service name: {args.ecs_service_name}")
        info(f"Container port: {DEFAULT_CONTAINER_PORT}")
        info(f"CPU/Memory: {DEFAULT_ECS_CPU} / {DEFAULT_ECS_MEMORY}")
        info("ECS Express auto-provisions: ALB, target groups, security groups, auto-scaling")
        try:
            svc = provision_ecs_express_service(
                sess,
                cluster_name=args.ecs_cluster_name,
                service_name=args.ecs_service_name,
                image_uri=image_uri,
                execution_role_arn=exec_role_arn,
                infrastructure_role_arn=infra_role_arn,
                log_group=log_group,
                env_vars=env_vars,
                health_check_path=DEFAULT_HEALTH_CHECK_PATH,
                secrets=container_secrets,
            )
        except ClientError as e:
            err(f"ECS Express CreateExpressGatewayService failed: {e}")
            sys.exit(1)
        status_code = (svc.get("status") or {}).get("statusCode")
        if status_code != "ACTIVE":
            err(
                f"ECS Express service did not reach ACTIVE (status={status_code}). "
                "Inspect with:\n"
                f"  aws ecs describe-express-gateway-service --region {region} "
                f"--service-arn {svc.get('serviceArn')}"
            )
            sys.exit(1)
        public_endpoint = _ecs_service_public_endpoint(svc)
        if not public_endpoint:
            err(
                "ECS Express reached ACTIVE but did not surface a PUBLIC ingress "
                "endpoint. The service may still be wiring up its ALB; retry "
                "`describe-express-gateway-service` in a minute."
            )
            sys.exit(1)
        service_url = (
            public_endpoint
            if public_endpoint.startswith("https://")
            else "https://" + public_endpoint
        )
        mcp_url = _normalise_mcp_url(service_url)

        # ECS Express has now told us the AWS-generated FQDN (e.g.
        # ``zs-<hash>.ecs.us-east-1.on.aws``). FastMCP's DNS-rebinding guard
        # rejects every POST whose Host header isn't in its allowlist with
        # ``421 Misdirected Request`` — which is exactly what the Harness
        # client sends — so we have to wire the FQDN into the container's
        # ``ZSCALER_MCP_ALLOWED_HOSTS``. The operator couldn't put it in
        # ``.env`` themselves because the FQDN isn't minted until create.
        # ``_build_container_env_vars`` skips this injection if the operator
        # already set ``ZSCALER_MCP_ALLOWED_HOSTS`` or
        # ``ZSCALER_MCP_DISABLE_HOST_VALIDATION``, so this is non-clobbering.
        # We compare DESIRED env to the **live** env on the running service
        # (not to the local pre-FQDN ``env_vars``) so re-deploys that already
        # have ALLOWED_HOSTS wired in stay idempotent — no surprise rolling
        # restarts on every invocation.
        fqdn_for_host_check = (
            public_endpoint
            if not public_endpoint.startswith("https://")
            else public_endpoint[len("https://"):]
        ).rstrip("/")
        desired_env = _build_container_env_vars(
            cfg["__raw_env__"],
            discovered_host=fqdn_for_host_check,
            secret_keys=secret_keys,
        )
        live_active = svc.get("activeConfigurations") or []
        live_env_raw = (
            live_active[-1].get("primaryContainer", {}).get("environment", [])
            if live_active
            else []
        )
        live_secrets_raw = (
            live_active[-1].get("primaryContainer", {}).get("secrets", [])
            if live_active
            else []
        )
        # ECS Express returns env / secrets as [{"name": ..., "value": ...}].
        # Compare as name→value dicts so list-order doesn't trigger a false
        # positive.
        live_env = {e["name"]: e["value"] for e in live_env_raw if "name" in e}
        desired_env_map = {e["name"]: e["value"] for e in desired_env}
        live_secrets = {
            s["name"]: s.get("valueFrom")
            for s in (live_secrets_raw or [])
            if "name" in s
        }
        desired_secrets_map = {
            s["name"]: s["valueFrom"] for s in (container_secrets or [])
        }
        if live_env != desired_env_map or live_secrets != desired_secrets_map:
            info(
                "Wiring discovered FQDN into ZSCALER_MCP_ALLOWED_HOSTS "
                f"(host={fqdn_for_host_check}) — required for FastMCP's "
                "DNS-rebinding guard."
            )
            ecs_client = sess.client("ecs")
            primary_container_update: dict[str, Any] = {
                "image": image_uri,
                "containerPort": DEFAULT_CONTAINER_PORT,
                "awsLogsConfiguration": {
                    "logGroup": log_group,
                    "logStreamPrefix": DEFAULT_ECS_LOG_STREAM_PREFIX,
                },
                "environment": desired_env,
            }
            if container_secrets:
                primary_container_update["secrets"] = container_secrets
            try:
                ecs_client.update_express_gateway_service(
                    serviceArn=svc["serviceArn"],
                    executionRoleArn=exec_role_arn,
                    healthCheckPath=DEFAULT_HEALTH_CHECK_PATH,
                    primaryContainer=primary_container_update,
                )
            except ClientError as e:
                err(f"UpdateExpressGatewayService (host injection) failed: {e}")
                sys.exit(1)
            svc = poll_ecs_express_active(sess, svc["serviceArn"])
            env_vars = desired_env

        ok(f"MCP server is live: {mcp_url}")

        ecs_state = {
            "ecs_service_arn":            svc["serviceArn"],
            "ecs_service_name":           args.ecs_service_name,
            "ecs_cluster_name":           args.ecs_cluster_name,
            "ecs_cluster_arn":            cluster_arn,
            "ecs_cluster_created_by_us":  cluster_created,
            "ecs_execution_role_name":    args.ecs_execution_role_name,
            "ecs_infrastructure_role_name": args.ecs_infrastructure_role_name,
            "ecs_log_group":              log_group,
            "ecs_service_url":            service_url,
            "image_uri":                  image_uri,
            "zscaler_secret_name":        secret_name,
            "zscaler_secret_arn":         secret_arn,
            # Marker so destroy knows whether WE created the secret (and
            # may therefore delete it) or it's operator-managed.
            "zscaler_secret_managed_externally": secret_managed_externally,
        }

    # ── Step 9: Stage creds in Token Vault ──────────────────────────────
    step("Step 9: Stage Zscaler credentials in AgentCore Token Vault")
    provider_arn = ensure_credential_provider(
        sess, args.credential_provider_name, cfg["client_id"], cfg["client_secret"]
    )

    # ── Step 10: Harness execution role ─────────────────────────────────
    step("Step 10: Provision Harness execution role")
    role_arn = ensure_execution_role(sess, args.role_name, region, args.harness_name)

    # ── Step 11: Pick model ─────────────────────────────────────────────
    step("Step 11: Pick a Bedrock reasoning model")
    env_model = cfg.get("model_id") or args.model_id
    if env_model:
        model_id = env_model
        info(f"Model (from env / --model-id): {model_id}")
    else:
        labels = [f"{m['label']}  —  {m['note']}" for m in MODEL_CATALOGUE]
        idx = prompt_choice("Available models", labels, default_idx=0)
        model_id = MODEL_CATALOGUE[idx]["id"]
    ok(f"Selected model: {model_id}")

    # ── Step 12: CreateHarness ──────────────────────────────────────────
    step("Step 12: CreateHarness")
    tools = [build_remote_mcp_tool(mcp_url, provider_arn)]
    try:
        harness = create_harness(
            sess,
            harness_name=args.harness_name,
            execution_role_arn=role_arn,
            model_id=model_id,
            tools=tools,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        msg = e.response.get("Error", {}).get("Message", str(e))
        err(f"CreateHarness failed [{code}]: {msg}")
        sys.exit(1)
    except EndpointConnectionError as e:
        err(f"Could not reach bedrock-agentcore-control in {region}: {e}")
        err("Confirm Harness is available in this region — it is currently preview, with limited regional coverage.")
        sys.exit(1)

    harness_id = harness["harnessId"]
    harness_arn = harness["arn"]
    ok(f"CreateHarness submitted. harnessId = {harness_id}")
    final = poll_harness_ready(sess, harness_id)

    # AgentCore Harness is implemented on top of an auto-managed
    # AgentCore Runtime. The runtime emits its own APPLICATION_LOGS
    # automatically to /aws/bedrock-agentcore/runtimes/<runtime-id>
    # without any vendedLogs wiring. The CloudWatch Logs PutDeliverySource
    # API does NOT accept `harness` as a logType resource — valid types
    # are limited to [code-interpreter, memory, payment-manager,
    # workload-identity, code-interpreter-custom, runtime, gateway].
    # So we skip the delivery-pipeline plumbing here; cmd_logs locates
    # the auto-generated log group at tail time.

    persisted: dict[str, Any] = {
        "region": region,
        "harness_id": harness_id,
        "harness_arn": harness_arn,
        "harness_name": args.harness_name,
        "execution_role_arn": role_arn,
        "role_name": args.role_name,
        "credential_provider_name": args.credential_provider_name,
        "credential_provider_arn": provider_arn,
        "mcp_url": mcp_url,
        "mcp_host_kind": mcp_host_kind,
        "model_id": model_id,
        "status": final.get("status", "UNKNOWN"),
        "deployed_at": datetime.now(timezone.utc).isoformat(),
    }
    persisted.update(ecs_state)
    # Final state write — flips state_partial=False so subsequent
    # `status` and `destroy` runs know the deploy crossed the finish line.
    finalize_state(persisted)

    _print_deploy_summary(
        region=region,
        harness_id=harness_id,
        harness_arn=harness_arn,
        mcp_url=mcp_url,
        mcp_host_kind=mcp_host_kind,
        ecs_state=ecs_state,
        model_id=model_id,
        role_arn=role_arn,
        provider_arn=provider_arn,
    )


def _print_deploy_summary(
    *,
    region: str,
    harness_id: str,
    harness_arn: str,
    mcp_url: str,
    mcp_host_kind: str,
    ecs_state: dict[str, Any],
    model_id: str,
    role_arn: str,
    provider_arn: str,
) -> None:
    step("Deployment summary")
    console_url = (
        f"https://{region}.console.aws.amazon.com/bedrock-agentcore/home"
        f"?region={region}#/harnesses/{harness_id}"
    )
    if mcp_host_kind == "ecs":
        host_line = (
            f"ECS Express — {ecs_state.get('ecs_service_name')} "
            f"(cluster: {ecs_state.get('ecs_cluster_name')})"
        )
    elif mcp_host_kind == "gateway":
        host_line = (
            f"AgentCore Runtime '{ecs_state.get('runtime_name')}' "
            f"(id={ecs_state.get('runtime_id')}) behind Gateway "
            f"'{ecs_state.get('gateway_name')}'"
        )
    else:
        host_line = "External (user-provided)"

    secret_name = ecs_state.get("zscaler_secret_name", "")
    secret_managed_externally = bool(
        ecs_state.get("zscaler_secret_managed_externally")
    )
    if secret_name:
        suffix = " (managed externally)" if secret_managed_externally else ""
        secret_line = (
            f"\n  {BOLD}Zscaler Secret{NC}         = {secret_name}{suffix}"
        )
    elif mcp_host_kind in ("ecs", "gateway"):
        secret_line = (
            f"\n  {BOLD}Zscaler Secret{NC}         = (none — "
            "credentials passed as plaintext env vars)"
        )
    else:
        secret_line = ""

    # Gateway topology — surface the Cognito + Runtime + Gateway resources
    # so the operator can wire Cursor/Claude/Strands clients against the
    # Gateway directly if they want (or just understand what was created).
    gateway_lines = ""
    if mcp_host_kind == "gateway":
        gateway_lines = (
            f"\n  {BOLD}Gateway URL{NC}            = "
            f"{ecs_state.get('gateway_url') or '(populated when Gateway is READY)'}"
            f"\n  {BOLD}Gateway ARN{NC}            = {ecs_state.get('gateway_arn', '')}"
            f"\n  {BOLD}Cognito Pool{NC}           = {ecs_state.get('cognito_user_pool_id', '')}"
            f"\n  {BOLD}Cognito Audience{NC}       = {ecs_state.get('cognito_audience', '')}"
            f"\n  {BOLD}Cognito Token URL{NC}      = {ecs_state.get('cognito_token_endpoint', '')}"
            f"\n  {BOLD}OAuth2 Provider{NC}        = {ecs_state.get('oauth_provider_arn', '')}"
        )

    cred_label = (
        "OAuth2 Provider (Cognito)" if mcp_host_kind == "gateway"
        else "Credential Provider"
    )

    print(f"""
  {BOLD}HarnessId{NC}              = {harness_id}
  {BOLD}HarnessArn{NC}             = {harness_arn}
  {BOLD}Model{NC}                  = {model_id}
  {BOLD}MCP URL{NC}                = {mcp_url}
  {BOLD}MCP Host{NC}               = {host_line}
  {BOLD}Execution Role{NC}         = {role_arn}
  {BOLD}{cred_label}{NC}    = {provider_arn}{secret_line}{gateway_lines}
  {BOLD}Logs{NC}                   = /aws/bedrock-agentcore/runtimes/* (auto-managed by AgentCore)
  {BOLD}Console{NC}                = {console_url}

  {DIM}Tail logs:{NC}      python harness_mcp_operations.py logs --region {region}
  {DIM}Smoke test:{NC}     python harness_mcp_operations.py invoke "list my zpa segment groups" --region {region}
  {DIM}Destroy all:{NC}    python harness_mcp_operations.py destroy --region {region}
""")


def cmd_status(args: argparse.Namespace) -> None:
    state = load_state()
    if not state:
        err("No state file found. Run `deploy` first.")
        sys.exit(1)
    region = args.region or state.get("region") or DEFAULT_REGION
    sess = get_session(region, profile=args.profile)
    harness_id = state.get("harness_id")
    if not harness_id:
        err("State file missing harness_id.")
        sys.exit(1)

    h = get_harness(sess, harness_id)
    if h is None:
        warn(f"Harness {harness_id} not found in {region} — it may have been deleted out-of-band.")
        return
    step("Harness status")
    tools_summary = ", ".join(t["name"] for t in h.get("tools", [])) or "(none)"
    print(f"""
  {BOLD}HarnessId{NC}        = {h.get('harnessId')}
  {BOLD}Name{NC}             = {h.get('harnessName')}
  {BOLD}Status{NC}           = {_color_status(h.get('status'))}
  {BOLD}Model{NC}            = {(h.get('model', {}).get('bedrockModelConfig', {}) or {}).get('modelId')}
  {BOLD}Tools{NC}            = {tools_summary}
  {BOLD}Created{NC}          = {h.get('createdAt')}
  {BOLD}Updated{NC}          = {h.get('updatedAt')}
  {BOLD}Role{NC}             = {h.get('executionRoleArn')}
""")

    host_kind = state.get("mcp_host_kind")
    if host_kind == "ecs":
        step("ECS Express MCP host")
        ecs_arn = state.get("ecs_service_arn", "")
        if ecs_arn:
            try:
                ecs_svc = sess.client("ecs").describe_express_gateway_service(
                    serviceArn=ecs_arn
                ).get("service", {})
            except ClientError as e:
                warn(f"DescribeExpressGatewayService failed: {e}")
                return
            status_code = (ecs_svc.get("status") or {}).get("statusCode")
            active = ecs_svc.get("activeConfigurations") or []
            cur_image = (
                active[-1].get("primaryContainer", {}).get("image", "")
                if active
                else ""
            )
            endpoint = _ecs_service_public_endpoint(ecs_svc) or "(not yet ready)"
            print(f"""
  {BOLD}ServiceName{NC}      = {ecs_svc.get('serviceName')}
  {BOLD}ServiceArn{NC}       = {ecs_svc.get('serviceArn')}
  {BOLD}Cluster{NC}          = {ecs_svc.get('cluster')}
  {BOLD}Status{NC}           = {_color_status(status_code)}
  {BOLD}Endpoint{NC}         = https://{endpoint}
  {BOLD}Image{NC}            = {cur_image}
""")
    elif host_kind == "gateway":
        ctrl = sess.client("bedrock-agentcore-control")

        step("AgentCore Runtime")
        runtime_name = state.get("runtime_name", "")
        runtime_id = state.get("runtime_id", "")
        if runtime_id:
            try:
                rt = ctrl.get_agent_runtime(agentRuntimeId=runtime_id)
            except ClientError as e:
                warn(f"get_agent_runtime failed: {e}")
                rt = {}
            print(f"""
  {BOLD}Name{NC}             = {runtime_name}
  {BOLD}RuntimeId{NC}        = {runtime_id}
  {BOLD}RuntimeArn{NC}       = {rt.get('agentRuntimeArn', state.get('runtime_arn',''))}
  {BOLD}Status{NC}           = {_color_status(rt.get('status'))}
  {BOLD}Image{NC}            = {(rt.get('agentRuntimeArtifact') or {}).get('containerConfiguration', {}).get('containerUri', state.get('image_uri',''))}
  {BOLD}MCP URL{NC}          = {state.get('runtime_mcp_url','')}
""")

        step("AgentCore Gateway")
        gateway_id = state.get("gateway_id", "")
        if gateway_id:
            try:
                gw = ctrl.get_gateway(gatewayIdentifier=gateway_id)
            except ClientError as e:
                warn(f"get_gateway failed: {e}")
                gw = {}
            target_id = state.get("gateway_target_id", "")
            target_status = "UNKNOWN"
            if target_id:
                try:
                    t = ctrl.get_gateway_target(
                        gatewayIdentifier=gateway_id, targetId=target_id
                    )
                    target_status = t.get("status", "UNKNOWN")
                except ClientError as e:
                    warn(f"get_gateway_target failed: {e}")
            print(f"""
  {BOLD}Name{NC}             = {state.get('gateway_name','')}
  {BOLD}GatewayId{NC}        = {gateway_id}
  {BOLD}Status{NC}           = {_color_status(gw.get('status'))}
  {BOLD}URL{NC}              = {gw.get('gatewayUrl', state.get('gateway_url',''))}
  {BOLD}Target{NC}           = {state.get('gateway_target_name','')}  status={_color_status(target_status)}
""")

        step("Amazon Cognito (inbound IdP)")
        print(f"""
  {BOLD}User Pool{NC}        = {state.get('cognito_user_pool_id','')}
  {BOLD}Audience{NC}         = {state.get('cognito_audience','')}
  {BOLD}Domain{NC}           = {state.get('cognito_domain_prefix','')}
  {BOLD}Token URL{NC}        = {state.get('cognito_token_endpoint','')}
  {BOLD}App Client{NC}       = {state.get('cognito_app_client_id','')}
""")


def _color_status(status: Optional[str]) -> str:
    if not status:
        return f"{DIM}UNKNOWN{NC}"
    if status in ("READY", "ACTIVE"):
        return f"{GREEN}{status}{NC}"
    if "FAILED" in status:
        return f"{RED}{status}{NC}"
    if "IN_PROGRESS" in status or status == "CREATING":
        return f"{CYAN}{status}{NC}"
    return f"{YELLOW}{status}{NC}"


def _discover_harness_runtime_log_groups(
    logs_client, harness_id: str, harness_name: str
) -> list[str]:
    """Find auto-managed AgentCore runtime log groups tied to a harness.

    AgentCore Harness sits on top of an auto-managed AgentCore Runtime
    that AWS provisions for you. That runtime writes APPLICATION_LOGS
    to `/aws/bedrock-agentcore/runtimes/<runtime-id>` (no operator
    wiring required — `harness` is not a valid resourceArn type for
    vendedLogs PutDeliverySource, so we never go that route).

    AWS doesn't surface the auto-managed runtime ID via GetHarness, so
    we discover the log group(s) by scanning the documented prefix for
    any whose name contains either the harness id or the harness name.
    Returns every match — there can be multiple while a harness rolls
    forward (old + new runtime running concurrently).
    """
    matches: list[str] = []
    needles = [n for n in (harness_id, harness_name) if n]
    next_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "logGroupNamePrefix": AGENTCORE_RUNTIME_LOG_PREFIX,
            "limit": 50,
        }
        if next_token:
            params["nextToken"] = next_token
        resp = logs_client.describe_log_groups(**params)
        for lg in resp.get("logGroups", []) or []:
            name = lg.get("logGroupName", "")
            if any(n and n in name for n in needles):
                matches.append(name)
        next_token = resp.get("nextToken")
        if not next_token:
            break
    return matches


def cmd_logs(args: argparse.Namespace) -> None:
    state = load_state()
    if not state:
        err("No state file found. Run `deploy` first.")
        sys.exit(1)
    region = args.region or state.get("region") or DEFAULT_REGION
    harness_id = state.get("harness_id") or ""
    harness_name = state.get("harness_name") or ""
    sess = get_session(region, profile=args.profile)
    logs = sess.client("logs")

    info(f"Searching for harness log groups under {AGENTCORE_RUNTIME_LOG_PREFIX}…")
    candidates = _discover_harness_runtime_log_groups(logs, harness_id, harness_name)
    if not candidates:
        warn(
            f"No AgentCore runtime log group found yet for harness "
            f"{harness_id or harness_name}. Logs auto-appear here on the "
            f"first InvokeHarness call — try invoking the harness once."
        )
        info(f"All groups beneath {AGENTCORE_RUNTIME_LOG_PREFIX} (for reference):")
        try:
            page = logs.describe_log_groups(
                logGroupNamePrefix=AGENTCORE_RUNTIME_LOG_PREFIX, limit=20
            )
            for lg in page.get("logGroups", []) or []:
                print(f"  {lg.get('logGroupName')}")
        except ClientError:
            pass
        return

    # Tail the most recently active one first; AgentCore Runtime
    # rotates the underlying container on each version bump and we
    # almost always want the freshest stream.
    log_group = candidates[0]
    if len(candidates) > 1:
        info(f"Found {len(candidates)} candidate log groups; tailing the first:")
        for c in candidates:
            print(f"  {c}")
    info(f"Tailing {log_group} (Ctrl-C to stop)…")

    start = int((time.time() - 600) * 1000)
    try:
        while True:
            try:
                resp = logs.filter_log_events(
                    logGroupName=log_group,
                    startTime=start,
                    limit=200,
                )
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code == "ResourceNotFoundException":
                    warn(
                        f"Log group {log_group} vanished mid-tail "
                        f"(harness may have been re-deployed). Re-run "
                        f"`logs` to pick up the new group."
                    )
                    return
                raise
            events = resp.get("events", [])
            for ev in events:
                ts = datetime.fromtimestamp(ev["timestamp"] / 1000, tz=timezone.utc).strftime("%H:%M:%S")
                print(f"{DIM}{ts}{NC}  {ev['message'].rstrip()}")
                start = max(start, ev["timestamp"] + 1)
            time.sleep(3)
    except KeyboardInterrupt:
        print()
        info("Stopped tailing.")


def cmd_invoke(args: argparse.Namespace) -> None:
    state = load_state()
    if not state:
        err("No state file found. Run `deploy` first.")
        sys.exit(1)
    region = args.region or state.get("region") or DEFAULT_REGION
    sess = get_session(region, profile=args.profile)
    harness_arn = state.get("harness_arn")
    if not harness_arn:
        err("State file missing harness_arn.")
        sys.exit(1)
    if not args.message:
        err("Provide a message: invoke \"list my zpa segment groups\"")
        sys.exit(1)

    runtime_session_id = "harness-smoke-" + uuid.uuid4().hex  # ≥33 chars
    data = sess.client("bedrock-agentcore")

    step("Sending message to Harness")
    info(f"runtimeSessionId = {runtime_session_id}")
    info(f"message          = {args.message}")
    try:
        resp = data.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=runtime_session_id,
            messages=[
                {"role": "user", "content": [{"text": args.message}]}
            ],
        )
    except ClientError as e:
        err(f"InvokeHarness failed: {e}")
        sys.exit(1)
    # InvokeHarness returns an event stream. Print every text chunk as it lands.
    stream = resp.get("eventStream") or resp.get("stream") or resp.get("body")
    if stream is None:
        warn("No event stream in response — printing raw payload.")
        print(json.dumps({k: v for k, v in resp.items() if k != "ResponseMetadata"}, default=str, indent=2))
        return

    print()
    print(f"{BOLD}Assistant:{NC}")
    for event in stream:
        if not isinstance(event, dict):
            continue
        for key, payload in event.items():
            if key == "contentBlockDelta":
                delta = payload.get("delta", {})
                if "text" in delta:
                    sys.stdout.write(delta["text"])
                    sys.stdout.flush()
            elif key == "metadata":
                usage = payload.get("usage", {})
                if usage:
                    print()
                    info(
                        f"Tokens — input: {usage.get('inputTokens')}, "
                        f"output: {usage.get('outputTokens')}, "
                        f"total: {usage.get('totalTokens')}"
                    )
            elif key == "runtimeClientError":
                print()
                err(f"runtimeClientError: {payload}")
            elif key == "messageStop":
                stop_reason = payload.get("stopReason", "")
                if stop_reason and stop_reason != "end_turn":
                    print()
                    info(f"stopReason = {stop_reason}")
    print()


def cmd_destroy(args: argparse.Namespace) -> None:
    state = load_state()
    if not state:
        err("No state file found — nothing to destroy.")
        sys.exit(1)
    region = args.region or state.get("region") or args.region or state.get("aws_region") or DEFAULT_REGION
    sess = get_session(region, profile=args.profile)

    topology = state.get("topology") or (
        "gateway" if state.get("gateway_id") else "ecs"
    )

    # Surface partial-deploy state up front. A partial state file means
    # the user's previous deploy was interrupted before CreateHarness —
    # destroy will still attempt to clean up whatever resources WERE
    # created and recorded, but the user should know they're not running
    # against a fully-deployed system.
    if state.get("state_partial"):
        warn(
            "State file marked partial — previous deploy did not complete.\n"
            f"  Last phase reached: {state.get('phase', '<unknown>')}\n"
            "  Resources created up to that point are recorded and will be "
            "cleaned up below. If the deploy crashed AFTER a resource was "
            "created but BEFORE the partial-state write, you may need to "
            "delete that resource manually — `aws bedrock-agentcore-control "
            "list-runtimes / list-gateways` will show any orphans."
        )

    if topology == "gateway":
        harness_id = state.get("harness_id")
        role_name = state.get("role_name") or DEFAULT_ROLE_NAME

        print(f"\n{BOLD}About to destroy (topology: gateway):{NC}")
        print(f"  Harness              : {harness_id}")
        print(f"  Harness exec role    : {role_name}")
        print(f"  AgentCore Gateway    : {state.get('gateway_name', '')} ({state.get('gateway_id', '')})")
        print(f"    └ Target           : {state.get('gateway_target_name', '')}")
        if state.get("gateway_role_name"):
            print(f"  Gateway service role : {state['gateway_role_name']}")
        print(f"  OAuth2 provider      : {state.get('oauth_provider_name', '')}")
        print(f"  AgentCore Runtime    : {state.get('runtime_name', '')} ({state.get('runtime_id', '')})")
        if state.get("runtime_execution_role_name"):
            print(f"  Runtime exec role    : {state['runtime_execution_role_name']}")
        pool_id = state.get("cognito_user_pool_id", "")
        if pool_id:
            cog_note = "  (will be kept — --keep-cognito)" if args.keep_cognito else ""
            print(f"  Cognito User Pool    : {pool_id}{cog_note}")
            if state.get("cognito_domain_prefix"):
                print(f"    └ Domain           : {state['cognito_domain_prefix']}")
        secret_name = state.get("zscaler_secret_name", "")
        secret_managed_externally = bool(state.get("zscaler_secret_managed_externally"))
        if secret_name:
            if secret_managed_externally:
                disp = "  (will be kept — managed externally / .env)"
            elif args.keep_secret:
                disp = "  (will be kept — --keep-secret)"
            elif args.force_secret_delete:
                disp = "  (will be PERMANENTLY deleted — --force-secret-delete)"
            else:
                disp = "  (will be soft-deleted with 7-day recovery window)"
            print(f"  Zscaler secret       : {secret_name}{disp}")
        print(f"  Region               : {region}")
        print()
        if not args.yes and not prompt_bool("Proceed?", default=False):
            info("Aborted.")
            return

        if harness_id:
            step("Deleting harness")
            delete_harness(sess, harness_id)
            time.sleep(5)
        if not args.keep_role:
            step("Deleting Harness execution role")
            delete_execution_role(sess, role_name)
        else:
            info(f"Keeping Harness execution role {role_name} (--keep-role).")

        _destroy_gateway_topology(args, sess=sess, state=state)

        remove_state()
        ok("State file deleted.")
        return

    harness_id = state.get("harness_id")
    role_name = state.get("role_name") or DEFAULT_ROLE_NAME
    cred_name = state.get("credential_provider_name") or DEFAULT_CREDENTIAL_PROVIDER_NAME
    ecs_arn = state.get("ecs_service_arn", "")
    ecs_service_name = state.get("ecs_service_name", "")
    ecs_cluster_name = state.get("ecs_cluster_name", "")
    ecs_cluster_created = bool(state.get("ecs_cluster_created_by_us"))
    ecs_exec_role = state.get("ecs_execution_role_name", "")
    ecs_infra_role = state.get("ecs_infrastructure_role_name", "")
    ecs_log_group = state.get("ecs_log_group", "")
    secret_name = state.get("zscaler_secret_name", "")
    secret_managed_externally = bool(state.get("zscaler_secret_managed_externally"))
    has_ecs = state.get("mcp_host_kind") == "ecs" and ecs_arn

    print(f"\n{BOLD}About to destroy:{NC}")
    print(f"  Harness              : {harness_id}")
    print(f"  Credential provider  : {cred_name}")
    print(f"  Harness exec role    : {role_name}")
    if has_ecs:
        print(f"  ECS Express service  : {ecs_service_name} ({ecs_arn})")
        # Re-check the cluster's owner tag NOW (not just trust the state
        # file boolean from the deploy that wrote it). Tag-based ownership
        # is the durable source of truth and survives destroy/deploy
        # cycles where the boolean would be stale.
        cluster_owned_now = ecs_cluster_created
        if ecs_cluster_name:
            try:
                desc = sess.client("ecs").describe_clusters(
                    clusters=[ecs_cluster_name],
                    include=["TAGS"],
                )
                clusters = desc.get("clusters") or []
                if clusters and clusters[0].get("status") == "ACTIVE":
                    cluster_owned_now = _cluster_is_script_owned(clusters[0])
            except ClientError:
                pass  # fall back to state-file boolean
        if cluster_owned_now:
            cluster_note = "  (will be deleted — tagged managed-by=zscaler-mcp-harness)"
        else:
            cluster_note = "  (will be kept — no owner tag, treated as pre-existing)"
        print(f"  ECS cluster          : {ecs_cluster_name}{cluster_note}")
        if ecs_exec_role:
            print(f"  ECS execution role   : {ecs_exec_role}")
        if ecs_infra_role:
            print(f"  ECS infra role       : {ecs_infra_role}")
        if ecs_log_group:
            print(f"  ECS log group        : {ecs_log_group}")
        if secret_name:
            if secret_managed_externally:
                disp = "  (will be kept — managed externally / .env)"
            elif args.keep_secret:
                disp = "  (will be kept — --keep-secret)"
            elif args.force_secret_delete:
                disp = "  (will be PERMANENTLY deleted — --force-secret-delete)"
            else:
                disp = "  (will be soft-deleted with 7-day recovery window)"
            print(f"  Zscaler secret       : {secret_name}{disp}")
    print(f"  Region               : {region}")
    print()
    if not args.yes and not prompt_bool("Proceed?", default=False):
        info("Aborted.")
        return

    if harness_id:
        step("Deleting harness")
        delete_harness(sess, harness_id)
        # AgentCore Harness application logs at
        # /aws/bedrock-agentcore/runtimes/<runtime-id> are auto-managed
        # by AWS — deleting the harness drains them in the background.
        # No vendedLogs teardown needed.
        # Wait briefly so the delete-driven detach completes before the
        # role + credential provider are removed.
        time.sleep(5)

    step("Deleting credential provider")
    delete_credential_provider(sess, cred_name)

    if not args.keep_role:
        step("Deleting Harness execution role")
        delete_execution_role(sess, role_name)
    else:
        info(f"Keeping Harness execution role {role_name} (--keep-role).")

    if has_ecs and not args.keep_ecs:
        step("Deleting ECS Express service")
        delete_ecs_express_service(sess, ecs_arn)
        # ECS Express auto-registers a fresh task-definition revision on
        # every create + every update_express_gateway_service. The naming
        # convention is ``{cluster}-{service}`` (visible in the ECS console
        # under "Task definitions"). Deleting the service does NOT clean
        # these up, so they pile up across deploy cycles. Tear them down
        # explicitly so the operator's account doesn't accumulate stale
        # task-definition history.
        if ecs_cluster_name and ecs_service_name:
            step("Cleaning up ECS task definitions")
            deregister_and_delete_task_definitions(
                sess, family=f"{ecs_cluster_name}-{ecs_service_name}"
            )
        if ecs_log_group:
            step("Deleting CloudWatch log group")
            delete_cloudwatch_log_group(sess, ecs_log_group)
        # Re-evaluate cluster ownership at destroy time (not just the
        # state-file boolean). The boolean can be stale after a deploy
        # that reused an existing cluster — only the cluster TAG is
        # durable across deploy cycles. ``cluster_owned_now`` is the
        # value the pre-flight summary just printed, so we stay
        # consistent with what we told the operator.
        if cluster_owned_now and ecs_cluster_name:
            step("Deleting ECS cluster")
            delete_ecs_cluster(sess, ecs_cluster_name)
        elif ecs_cluster_name:
            info(
                f"Keeping ECS cluster {ecs_cluster_name} — it does not "
                "carry the managed-by=zscaler-mcp-harness tag (treated as "
                "pre-existing or operator-managed)."
            )
        if not args.keep_role:
            if ecs_exec_role:
                step("Deleting ECS task execution role")
                delete_ecs_task_execution_role(sess, ecs_exec_role)
            if ecs_infra_role:
                step("Deleting ECS infrastructure role")
                delete_ecs_infrastructure_role(sess, ecs_infra_role)
        # Secret deletion runs last (after the role is gone) so a half-failed
        # destroy on the role side doesn't leave an orphan secret that
        # blocks a subsequent deploy with the same name. We only delete
        # secrets that THIS script created — operator-managed secrets
        # (the ``ZSCALER_SECRET_NAME``-in-.env path) are always preserved.
        if secret_name and not secret_managed_externally:
            if args.keep_secret:
                info(
                    f"Keeping Zscaler Secrets Manager secret {secret_name} "
                    "(--keep-secret)."
                )
            else:
                step("Deleting Zscaler Secrets Manager secret")
                delete_zscaler_secret(
                    sess, secret_name, force=args.force_secret_delete
                )
        elif secret_name and secret_managed_externally:
            info(
                f"Keeping Zscaler Secrets Manager secret {secret_name} "
                "(operator-managed via ZSCALER_SECRET_NAME in .env)."
            )
    elif has_ecs:
        info(
            f"Keeping ECS Express service {ecs_service_name} (--keep-ecs). "
            "Note: an idle ECS Express service still incurs cost (ALB + minimum task)."
        )

    remove_state()
    ok("State file deleted.")


# ──────────────────────────────────────────────────────────────────────────
# Argparse
# ──────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="harness_mcp_operations.py",
        description=(
            "Deploy the Zscaler MCP Server as an AWS Bedrock AgentCore Harness "
            "remote_mcp tool. Sibling of bedrock-agentcore/aws_mcp_operations.py."
        ),
    )
    # Shared --region / --profile parent. We only attach them to the
    # subparsers (not the top-level parser) so users can put the flags
    # AFTER the subcommand. This matches what the deployment summary
    # prints and what `--help` shows. Mixing the two definitions (parent
    # + subparser) caused the subparser default of None to overwrite a
    # prefix-position value — counter-intuitive for ops staff.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--region", help=f"AWS region (default: {DEFAULT_REGION})")
    common.add_argument("--profile", help="AWS profile name to use")
    common.add_argument(
        "--env-file",
        help=(
            "Path to .env / env.properties. Auto-discovered when omitted "
            "(precedence: script dir → cwd → env.properties fallback)."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    pd = sub.add_parser(
        "deploy",
        parents=[common],
        help=(
            "End-to-end deploy. Two topologies:\n"
            "  --topology ecs       MCP server on ECS Express + remote_mcp tool (default).\n"
            "  --topology gateway   MCP server on AgentCore Runtime + Cognito + Gateway +\n"
            "                       agentcore_gateway tool. Skips all ECS plumbing."
        ),
    )
    pd.add_argument(
        "--topology",
        choices=list(SUPPORTED_TOPOLOGIES),
        default=None,
        help=(
            "Deployment topology. Defaults to 'ecs' (PR #47 behaviour). Use 'gateway' "
            "(PR #48) to deploy the MCP server on AgentCore Runtime fronted by an "
            "AgentCore Gateway with Amazon Cognito as the inbound IdP. Equivalent to "
            "TOPOLOGY in .env. Omit to be prompted interactively."
        ),
    )
    pd.add_argument("--harness-name", default=DEFAULT_HARNESS_NAME)
    pd.add_argument("--role-name", default=DEFAULT_ROLE_NAME,
                    help="Harness execution role name")
    pd.add_argument("--credential-provider-name", default=DEFAULT_CREDENTIAL_PROVIDER_NAME)
    pd.add_argument("--ecs-cluster-name", default=DEFAULT_ECS_CLUSTER_NAME,
                    help="ECS cluster (created if missing; deleted on destroy only if we created it)")
    pd.add_argument("--ecs-service-name", default=DEFAULT_ECS_SERVICE_NAME,
                    help="ECS Express service name")
    pd.add_argument("--ecs-execution-role-name", default=DEFAULT_ECS_EXECUTION_ROLE_NAME,
                    help="Task execution role (pulls image, writes container logs)")
    pd.add_argument("--ecs-infrastructure-role-name", default=DEFAULT_ECS_INFRASTRUCTURE_ROLE_NAME,
                    help="Infrastructure role (manages ALB, target groups, security groups, auto-scaling)")
    pd.add_argument("--ecs-log-group", default=DEFAULT_ECS_LOG_GROUP,
                    help="CloudWatch log group for container logs")
    pd.add_argument(
        "--mcp-url",
        help=(
            "Skip the ECS Express deploy and consume this pre-existing MCP URL. "
            "Equivalent to MCP_URL in .env. Useful when the MCP server already "
            "runs on Cloud Run / ACA / EC2 / on-prem."
        ),
    )
    pd.add_argument(
        "--model-id",
        help=(
            "Bedrock inference-profile model ID. Skips the interactive picker. "
            "Equivalent to MODEL_ID in .env."
        ),
    )
    pd.add_argument("--client-id", help="ZSCALER_CLIENT_ID (else env or .env or prompt)")
    pd.add_argument("--client-secret", help="ZSCALER_CLIENT_SECRET (else env or .env or prompt)")
    pd.add_argument("--customer-id", help="ZSCALER_CUSTOMER_ID (else env or .env or prompt)")
    pd.add_argument(
        "--vanity-domain",
        help="ZSCALER_VANITY_DOMAIN (else env or .env or prompt)",
    )
    pd.add_argument(
        "--secret-name",
        default=DEFAULT_ECS_SECRET_NAME,
        help=(
            "AWS Secrets Manager secret name for Zscaler credentials "
            f"(default: {DEFAULT_ECS_SECRET_NAME}). Created or refreshed at "
            "deploy time so the container never receives plaintext "
            "credentials via the ECS task env. Override only if you need "
            "a custom name (e.g. multiple harness deployments in one "
            "account). To bring your own pre-existing secret, set "
            "ZSCALER_SECRET_NAME=<arn-or-name> in .env instead — the "
            "script will reuse it and never overwrite its value."
        ),
    )
    pd.add_argument(
        "--no-secrets-manager",
        action="store_true",
        help=(
            "OPT-OUT: keep the legacy plaintext-env behaviour where "
            "ZSCALER_CLIENT_SECRET / CLIENT_ID / VANITY_DOMAIN / "
            "CUSTOMER_ID / CLOUD are passed directly in the ECS task "
            "definition. Visible in `aws ecs describe-task-definition` "
            "and CloudTrail. Only for dev / debugging — production "
            "deploys should leave this off (the default)."
        ),
    )

    # ── Gateway topology flags (PR #48) — only meaningful when
    # --topology gateway is set. Defaults are namespaced so the script
    # can drop into a fresh AWS account without collisions.
    pd.add_argument(
        "--runtime-name",
        default=DEFAULT_RUNTIME_NAME,
        help=(
            "AgentCore Runtime name (gateway topology). Must match "
            "[a-zA-Z][a-zA-Z0-9_]{0,39} — underscores only, no hyphens, max 40 chars."
        ),
    )
    pd.add_argument(
        "--runtime-execution-role-name",
        default=DEFAULT_RUNTIME_EXECUTION_ROLE_NAME,
        help="IAM role assumed by the AgentCore Runtime container (gateway topology).",
    )
    pd.add_argument(
        "--gateway-name",
        default=DEFAULT_GATEWAY_NAME,
        help="AgentCore Gateway name (gateway topology).",
    )
    pd.add_argument(
        "--gateway-target-name",
        default=DEFAULT_GATEWAY_TARGET_NAME,
        help="Name of the mcpServer target on the Gateway (gateway topology).",
    )
    pd.add_argument(
        "--gateway-role-name",
        default=DEFAULT_GATEWAY_ROLE_NAME,
        help="IAM service role the Gateway assumes to invoke its Runtime target.",
    )
    pd.add_argument(
        "--oauth-provider-name",
        default=DEFAULT_OAUTH_PROVIDER_NAME,
        help=(
            "AgentCore Identity OAuth2 credential provider name (gateway topology). "
            "Backs both the Harness→Gateway and Gateway→Runtime auth legs."
        ),
    )
    pd.add_argument(
        "--cognito-user-pool-name",
        default=DEFAULT_COGNITO_USER_POOL_NAME,
        help="Amazon Cognito User Pool name (gateway topology).",
    )
    pd.add_argument(
        "--cognito-resource-server-identifier",
        default=DEFAULT_COGNITO_RESOURCE_SERVER_IDENTIFIER,
        help=(
            "Cognito Resource Server identifier — becomes the `aud` claim on "
            "minted tokens (gateway topology)."
        ),
    )
    pd.add_argument(
        "--cognito-scope-name",
        default=DEFAULT_COGNITO_SCOPE_NAME,
        help=(
            "Cognito Resource Server scope name — must be attached to the App "
            "Client's AllowedOAuthScopes for client_credentials to mint tokens."
        ),
    )
    pd.add_argument(
        "--cognito-app-client-name",
        default=DEFAULT_COGNITO_APP_CLIENT_NAME,
        help="Cognito App Client name (gateway topology).",
    )
    pd.add_argument(
        "--cognito-domain-prefix",
        default=DEFAULT_COGNITO_DOMAIN_PREFIX,
        help=(
            "Cognito hosted-UI domain prefix (gateway topology). Auto-suffixed "
            "with the AWS account ID for global uniqueness."
        ),
    )

    pd.set_defaults(func=cmd_deploy)

    ps = sub.add_parser("status", parents=[common],
                        help="Show harness status / model / tools")
    ps.set_defaults(func=cmd_status)

    pl = sub.add_parser("logs", parents=[common],
                        help="Tail the harness CloudWatch log group")
    pl.set_defaults(func=cmd_logs)

    pi = sub.add_parser("invoke", parents=[common],
                        help="One-shot smoke test invocation")
    pi.add_argument("message", help="Prompt to send (e.g. 'list my zpa segment groups')")
    pi.set_defaults(func=cmd_invoke)

    pdes = sub.add_parser(
        "destroy",
        parents=[common],
        help="Tear down harness + credential provider + execution role + ECS Express service",
    )
    pdes.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    pdes.add_argument(
        "--keep-role",
        action="store_true",
        help="Don't delete the IAM roles (Harness exec, ECS task execution, ECS infrastructure)",
    )
    pdes.add_argument(
        "--keep-ecs",
        action="store_true",
        help="Don't delete the ECS Express service (use to swap Harness while preserving the MCP host)",
    )
    pdes.add_argument(
        "--keep-secret",
        action="store_true",
        help=(
            "Don't delete the Zscaler credentials secret in Secrets Manager "
            "(use when the secret is managed by Terraform/CloudFormation, "
            "or when you want to redeploy without re-entering credentials)."
        ),
    )
    pdes.add_argument(
        "--force-secret-delete",
        action="store_true",
        help=(
            "Bypass the 7-day Secrets Manager recovery window — the secret "
            "is permanently deleted immediately. Use for CI / repeated test "
            "deploys where the soft-delete window otherwise blocks re-create."
        ),
    )
    pdes.add_argument(
        "--keep-cognito",
        action="store_true",
        help=(
            "Gateway topology only: don't delete the Cognito User Pool / domain. "
            "Useful when the User Pool is shared with other MCP/Gateway deployments "
            "or when you'd rather destroy it manually via the Cognito console."
        ),
    )
    pdes.set_defaults(func=cmd_destroy)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        info("Interrupted by user.")
        sys.exit(130)
