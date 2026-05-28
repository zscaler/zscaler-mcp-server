#!/usr/bin/env python3
"""Zscaler MCP Server — AWS Bedrock AgentCore deployment & lifecycle.

Mirrors the UX of integrations/azure/azure_mcp_operations.py and
integrations/google/gcp/gcp_mcp_operations.py. Wraps the modular
CloudFormation templates in cloudformation/ and ships them via S3 to a
nested-stack root.

Commands:
    deploy              Interactive deployment (IAM + Secrets + Runtime [+ Gateway])
    status              Show stack + runtime + gateway state
    logs                Tail the CFN custom-resource Lambda CloudWatch logs
    destroy             Tear everything down
    export-tool-schema  Capture the live MCP tools/list as a Gateway target schema

Image source: AWS Marketplace ECR
    709825985650.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:0.10.4-bedrock

The Marketplace listing publishes immutable "<semver>-bedrock" tags only
(there is no moving "latest" tag). Customers must subscribe to the
Zscaler MCP Server listing in AWS Marketplace before this script can
pull the image. Subscription is free (BYOL) and grants the calling AWS
account permission to pull from the seller-side ECR repository.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("ERROR: boto3 is required.  pip install boto3", file=sys.stderr)
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────
# Branding (matches the Zenith Live lab convention)
# ──────────────────────────────────────────────────────────────────────────

_ZSCALER_ART = [
    "███████╗███████╗ ██████╗ █████╗ ██╗     ███████╗██████╗ ",
    "╚══███╔╝██╔════╝██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗",
    "  ███╔╝ ███████╗██║     ███████║██║     █████╗  ██████╔╝",
    " ███╔╝  ╚════██║██║     ██╔══██║██║     ██╔══╝  ██╔══██╗",
    "███████╗███████║╚██████╗██║  ██║███████╗███████╗██║  ██║",
    "╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
]
_TAGLINE = "AWS Bedrock AgentCore Deployment   |   Image source: AWS Marketplace"


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
    """Render a chunky Zscaler ASCII logo with a left-to-right blue gradient."""
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
        out = []
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
# Constants
# ──────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
CFN_DIR = SCRIPT_DIR / "cloudformation"
LAMBDA_DIR = CFN_DIR / "lambda"
STATE_FILE = SCRIPT_DIR / ".aws-deploy-state.json"

LAMBDA_PACKAGES = [
    # (source .py file, output .zip key suffix, extra pip dependencies)
    #
    # The Lambda Python 3.12 runtime ships with a boto3 that predates the
    # AgentCore Runtime ``requestHeaderConfiguration`` parameter
    # (https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-header-allowlist.html).
    # Bundling a recent boto3+botocore directly into the Lambda zip lets the
    # provisioner call CreateAgentRuntime / UpdateAgentRuntime with the new
    # shape regardless of when AWS upgrades the runtime-bundled SDK.
    ("runtime_provisioner.py", "runtime_provisioner.zip", ["boto3>=1.40.0"]),
    # The Gateway provisioner calls create_gateway_target with the mcpServer
    # target type, which is only present in boto3 >= 1.40.0 (~Oct 2025). The
    # Lambda Python 3.12 runtime still ships a substantially older SDK, so
    # we vendor a recent boto3+botocore into the zip the same way we do for
    # the runtime provisioner.
    ("gateway_provisioner.py", "gateway_provisioner.zip", ["boto3>=1.40.0"]),
]

MARKETPLACE_IMAGE = (
    "709825985650.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:0.10.4-bedrock"
)

NESTED_TEMPLATES = ["iam.yaml", "secrets.yaml", "runtime.yaml", "gateway.yaml"]
ROOT_TEMPLATE = "zscaler-mcp-root.yaml"

DEFAULT_REGION = "us-east-1"
DEFAULT_STACK_NAME = "zscaler-mcp-agentcore"
DEFAULT_RESOURCE_PREFIX = "zscaler-mcp"

# ──────────────────────────────────────────────────────────────────────────
# AgentCore Runtime VPC mode — supported Availability Zone IDs per region
# ──────────────────────────────────────────────────────────────────────────
# Source: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html#supported-az
#
# IMPORTANT: these are AZ IDs (e.g. ``use1-az1``), NOT AZ names
# (e.g. ``us-east-1a``). AWS randomises the AZ name → AZ ID mapping per
# account to spread load — so the same subnet in two different accounts
# in the same region may report different AZ names but identical AZ IDs.
# Every validation here keys off the ID returned by
# ``ec2:DescribeSubnets`` → ``AvailabilityZoneId``.
#
# When AWS extends VPC mode to a new region, update this map AND bump
# the comment with the doc revision date. A missing region in this map
# means VPC mode is unsupported in that region.
SUPPORTED_AGENTCORE_AZ_IDS: dict[str, set[str]] = {
    "us-east-1":      {"use1-az1", "use1-az2", "use1-az4"},
    "us-east-2":      {"use2-az1", "use2-az2", "use2-az3"},
    "us-west-2":      {"usw2-az1", "usw2-az2", "usw2-az3"},
    "ap-southeast-2": {"apse2-az1", "apse2-az2", "apse2-az3"},
    "ap-south-1":     {"aps1-az1", "aps1-az2", "aps1-az3"},
    "ap-southeast-1": {"apse1-az1", "apse1-az2", "apse1-az3"},
    "ap-northeast-1": {"apne1-az1", "apne1-az2", "apne1-az4"},
    "eu-west-1":      {"euw1-az1", "euw1-az2", "euw1-az3"},
    "eu-central-1":   {"euc1-az1", "euc1-az2", "euc1-az3"},
    "eu-north-1":     {"eun1-az1", "eun1-az2", "eun1-az3"},
    "eu-west-3":      {"euw3-az1", "euw3-az2", "euw3-az3"},
    "ap-northeast-2": {"apne2-az1", "apne2-az2", "apne2-az3"},
    "eu-west-2":      {"euw2-az1", "euw2-az2", "euw2-az3"},
    "ca-central-1":   {"cac1-az1", "cac1-az2", "cac1-az4"},
    "sa-east-1":      {"sae1-az1", "sae1-az2", "sae1-az3"},
    "us-gov-west-1":  {"usgw1-az1", "usgw1-az2", "usgw1-az3"},
}


# ──────────────────────────────────────────────────────────────────────────
# ANSI colours
# ──────────────────────────────────────────────────────────────────────────
# Colours / spinner enabled only when stdout is attached to a real TTY.
# When piped, tee'd, or running in CI, ``stdout.isatty()`` returns False
# so logs stay plain text (no escape codes leaking into log files).
# Matches the styling used by integrations/azure and integrations/google/gcp.

COLOURS = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
if COLOURS and platform.system() == "Windows":
    # Best-effort: enable VT escapes on Windows 10+ consoles. If
    # SetConsoleMode fails we fall back to plain text rather than spew
    # raw escape sequences.
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


# ──────────────────────────────────────────────────────────────────────────
# Pretty-print helpers
# ──────────────────────────────────────────────────────────────────────────

def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{NC}  {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{NC}    {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def err(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}", file=sys.stderr)


def step(title: str) -> None:
    bar = "─" * (80 - len(title) - 5)
    print(f"\n{SKY_BLUE}── {BOLD}{title}{NC}{SKY_BLUE} {bar}{NC}")


# ──────────────────────────────────────────────────────────────────────────
# CloudFormation wait spinner
# ──────────────────────────────────────────────────────────────────────────
# Used by wait_for_stack to render a live "we're still here" indicator
# with elapsed time + colour-coded status, while still rate-limiting the
# actual CloudFormation API polls to one every ~15s. CloudFormation has
# no progress-percent API — elapsed time is the most honest progress
# signal we can show.

_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def _color_for_stack_status(status: str) -> str:
    """Pick a colour for a CloudFormation stack status string.

    Mapping:
      green   → *_COMPLETE        (success)
      red     → *_FAILED, ROLLBACK_*   (failure / unwinding)
      cyan    → *_IN_PROGRESS     (working)
      yellow  → anything else     (transient / unknown)
    """
    if not status:
        return NC
    if "FAILED" in status or "ROLLBACK" in status:
        return RED
    if status.endswith("_COMPLETE"):
        return GREEN
    if status.endswith("_IN_PROGRESS"):
        return CYAN
    return YELLOW


def _fmt_elapsed(seconds: float) -> str:
    """Format seconds as '12s', '2m 14s', or '1h 23m 04s' for display."""
    total = int(seconds)
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m {total % 60:02d}s"
    return f"{total // 3600}h {(total % 3600) // 60:02d}m {(total % 60):02d}s"


def _clear_spinner_line() -> None:
    """Carriage-return + ANSI 'erase to end of line'. Used to overwrite
    the live spinner line cleanly before printing a permanent log line."""
    if COLOURS:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


# ──────────────────────────────────────────────────────────────────────────
# .env loader
# ──────────────────────────────────────────────────────────────────────────

def _derive_jwks_uri(issuer: str) -> str:
    """Resolve the IdP's JWKS URI from its OIDC discovery document.

    Every OIDC-compliant IdP exposes a `jwks_uri` field at
    `<issuer>/.well-known/openid-configuration`. Fetching it makes us
    vendor-neutral (Auth0, Okta, Cognito, Entra ID, Google, Keycloak,
    ADFS, Ping, etc.) rather than hard-coding any specific IdP's URL
    convention. Returns an empty string on any failure so the caller
    can fall back to an explicit override / prompt.
    """
    issuer = (issuer or "").strip()
    if not issuer:
        return ""
    import urllib.error
    import urllib.request
    discovery_url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(discovery_url, timeout=5) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError):
        return ""
    return (doc.get("jwks_uri") or "").strip()


def _infer_client_claim_name(discovery_or_issuer: str) -> str:
    """Pick the JWT claim that carries the OAuth client ID, by IdP.

    Empirically verified contract for AgentCore Gateway's `customJWTAuthorizer`:
    its built-in `allowedClients` matcher reads the **`client_id` claim** —
    a Cognito-native convention. Auth0/Okta/Entra/Keycloak/Google emit the
    RFC-7519 `azp` claim instead (Okta uses `cid`); for those, the Lambda
    emits a `customClaims` matcher on the named claim. See
    `local_dev/Bedrock_Agent_Core/idp-compatibility-findings.md`.

    Returns the claim name to use. Best-effort; users can always override
    via GATEWAY_INBOUND_CLIENT_CLAIM_NAME.
    """
    s = (discovery_or_issuer or "").lower()
    if not s:
        return "client_id"
    if "cognito-idp." in s or ".amazoncognito.com" in s:
        return "client_id"
    if ".auth0.com" in s or ".eu.auth0.com" in s or ".us.auth0.com" in s:
        return "azp"
    if ".okta.com" in s or ".oktapreview.com" in s:
        return "cid"
    if (
        "login.microsoftonline.com" in s
        or "sts.windows.net" in s
        or ".ciamlogin.com" in s
    ):
        return "azp"
    if "accounts.google.com" in s:
        return "azp"
    if "/realms/" in s:  # Keycloak path convention
        return "azp"
    return "client_id"


def _strip_inline_comment(value: str) -> str:
    """Drop trailing '# ...' from an env-file value, preserving '#' inside quotes."""
    if not value:
        return value
    if value[0] in ('"', "'"):
        quote = value[0]
        end = value.find(quote, 1)
        if end == -1:
            return value
        return value[1:end]
    hash_idx = value.find("#")
    if hash_idx == -1:
        return value
    return value[:hash_idx].rstrip()


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = _strip_inline_comment(val.strip()).strip().strip('"').strip("'")
        if val and val != "NOT_SET":
            env[key] = val
    return env


def discover_env_file() -> Path | None:
    # .env wins over env.properties (template). Script dir wins over cwd.
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


# ──────────────────────────────────────────────────────────────────────────
# State (so status / destroy / logs know what to look at)
# ──────────────────────────────────────────────────────────────────────────

def save_state(data: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(data, indent=2))


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text())


# ──────────────────────────────────────────────────────────────────────────
# Interactive prompts
# ──────────────────────────────────────────────────────────────────────────

def prompt(label: str, default: str | None = None, *, secret: bool = False) -> str:
    suffix = f" {DIM}[{default}]{NC}" if default else ""
    line = f"{BOLD}{label}{NC}{suffix}: "
    if secret:
        try:
            import getpass

            val = getpass.getpass(line)
        except Exception:
            val = input(line).strip()
    else:
        val = input(line).strip()
    return val or (default or "")


def prompt_choice(label: str, choices: list[str], default: str) -> str:
    print(f"\n{BOLD}{label}{NC}")
    for i, c in enumerate(choices, 1):
        marker = f"{DIM} (default){NC}" if c == default else ""
        print(f"  {CYAN}[{i}]{NC} {c}{marker}")
    default_idx = choices.index(default) + 1
    raw = input(
        f"Pick {CYAN}1-{len(choices)}{NC} {DIM}[{default_idx}]{NC}: "
    ).strip()
    if not raw:
        return default
    try:
        return choices[int(raw) - 1]
    except (ValueError, IndexError):
        warn(f"Invalid choice; using default '{default}'")
        return default


def prompt_bool(label: str, default: bool) -> bool:
    d = "Y/n" if default else "y/N"
    raw = input(f"{BOLD}{label}{NC} {CYAN}[{d}]{NC}: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "true", "1")


def prompt_multi_choice(
    label: str,
    items: list[tuple[str, str]],
    *,
    min_count: int = 1,
) -> list[str]:
    """Comma-separated multi-select. Returns the IDs the operator picked.

    ``items`` is a list of (id, display_label) pairs. Operators enter
    something like ``1,3,4`` to pick the 1st, 3rd, and 4th rows. The
    loop re-prompts until at least ``min_count`` valid rows are picked
    (and Ctrl-C is honoured as an explicit abort).
    """
    print(f"\n{BOLD}{label}{NC}")
    for i, (_, lbl) in enumerate(items, 1):
        print(f"  {CYAN}[{i}]{NC} {lbl}")
    while True:
        try:
            raw = input(
                f"Pick {CYAN}1-{len(items)}{NC} "
                f"(comma-separated, min {min_count}): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            err("\nAborted.")
            sys.exit(1)
        if not raw:
            warn(f"At least {min_count} selection required.")
            continue
        try:
            picks = [int(p) for p in raw.replace(" ", "").split(",") if p]
        except ValueError:
            warn(f"Invalid input: {raw!r}. Use comma-separated row numbers.")
            continue
        if not all(1 <= p <= len(items) for p in picks):
            warn(f"All numbers must be between 1 and {len(items)}.")
            continue
        if len(set(picks)) < min_count:
            warn(f"Pick at least {min_count} distinct row(s).")
            continue
        return [items[p - 1][0] for p in dict.fromkeys(picks)]


# ──────────────────────────────────────────────────────────────────────────
# AgentCore VPC discovery + validation
# ──────────────────────────────────────────────────────────────────────────

def list_vpcs(sess: boto3.Session) -> list[dict]:
    """Return all VPCs in the region, ordered with the default VPC first."""
    ec2 = sess.client("ec2")
    resp = ec2.describe_vpcs()
    vpcs = resp.get("Vpcs", [])
    # Pin the default VPC to the top so admins see "the obvious choice" first.
    vpcs.sort(key=lambda v: (not v.get("IsDefault", False), v["VpcId"]))
    return vpcs


def list_subnets_for_vpc(sess: boto3.Session, vpc_id: str) -> list[dict]:
    """Return every subnet in ``vpc_id``, including its AvailabilityZoneId."""
    ec2 = sess.client("ec2")
    resp = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}],
    )
    return resp.get("Subnets", [])


def list_security_groups_for_vpc(sess: boto3.Session, vpc_id: str) -> list[dict]:
    """Return every security group in ``vpc_id``."""
    ec2 = sess.client("ec2")
    resp = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}],
    )
    return resp.get("SecurityGroups", [])


def supported_agentcore_az_ids(region: str) -> set[str]:
    """Supported AgentCore AZ IDs for ``region`` (empty set if unsupported)."""
    return SUPPORTED_AGENTCORE_AZ_IDS.get(region, set())


def validate_subnet_az_ids(
    sess: boto3.Session,
    subnet_ids: list[str],
    region: str,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Resolve each subnet → AZ ID and split into supported / unsupported.

    Returns ``(ok_subnet_ids, [(bad_subnet_id, bad_az_id), ...])``.

    Calls ``ec2:DescribeSubnets`` once for the full set so this is a
    single API hit regardless of how many subnets were supplied.
    """
    if not subnet_ids:
        return [], []
    supported = supported_agentcore_az_ids(region)
    if not supported:
        # Region not in the support map → don't pretend to validate.
        return list(subnet_ids), []
    ec2 = sess.client("ec2")
    try:
        resp = ec2.describe_subnets(SubnetIds=list(subnet_ids))
    except ClientError as e:
        warn(
            f"Could not describe subnets for AZ-ID validation: "
            f"{_short_aws_error(e)}"
        )
        return list(subnet_ids), []
    ok_, bad = [], []
    for s in resp.get("Subnets", []):
        sid = s["SubnetId"]
        az_id = s.get("AvailabilityZoneId", "")
        if az_id in supported:
            ok_.append(sid)
        else:
            bad.append((sid, az_id or "<unknown>"))
    return ok_, bad


def validate_resources_share_vpc(
    sess: boto3.Session,
    subnet_ids: list[str],
    sg_ids: list[str],
    expected_vpc_id: str = "",
) -> str:
    """Verify every subnet + SG lives in the same VPC. Returns that VPC ID.

    Two checks in one round trip:

    1. ``ec2:DescribeSubnets`` resolves the VpcId for each subnet — must
       collapse to a single value.
    2. ``ec2:DescribeSecurityGroups`` does the same for each SG — must
       match the subnets' VpcId.

    If ``expected_vpc_id`` is set, both sets must also match THAT — this
    catches typos when the operator pinned ``AGENTCORE_VPC_ID`` in .env.

    Raises ``SystemExit`` with a clear error message when any check
    fails. AWS rejects ``CreateAgentRuntime`` for cross-VPC selections
    too, but it takes 5+ minutes into the stack launch — failing here
    saves the cycle.
    """
    if not subnet_ids or not sg_ids:
        return ""
    ec2 = sess.client("ec2")

    subnet_vpcs: dict[str, str] = {}
    try:
        resp = ec2.describe_subnets(SubnetIds=list(subnet_ids))
    except ClientError as e:
        err(
            "Could not describe subnets for VPC cross-validation: "
            f"{_short_aws_error(e)}"
        )
        sys.exit(1)
    for s in resp.get("Subnets", []):
        subnet_vpcs[s["SubnetId"]] = s.get("VpcId", "")
    missing = sorted(set(subnet_ids) - subnet_vpcs.keys())
    if missing:
        err(f"These subnet IDs do not exist in this region: {missing}")
        sys.exit(1)

    distinct_subnet_vpcs = {v for v in subnet_vpcs.values() if v}
    if len(distinct_subnet_vpcs) > 1:
        err("Subnets span multiple VPCs — pick subnets in ONE VPC:")
        for sid, vid in subnet_vpcs.items():
            print(f"    {sid}  →  {vid}")
        sys.exit(1)
    if not distinct_subnet_vpcs:
        err(f"Could not resolve VpcId for subnets: {subnet_ids}")
        sys.exit(1)
    subnet_vpc = next(iter(distinct_subnet_vpcs))

    sg_vpcs: dict[str, str] = {}
    try:
        resp = ec2.describe_security_groups(GroupIds=list(sg_ids))
    except ClientError as e:
        err(
            "Could not describe security groups for VPC cross-validation: "
            f"{_short_aws_error(e)}"
        )
        sys.exit(1)
    for g in resp.get("SecurityGroups", []):
        sg_vpcs[g["GroupId"]] = g.get("VpcId", "")
    missing = sorted(set(sg_ids) - sg_vpcs.keys())
    if missing:
        err(f"These security group IDs do not exist in this region: {missing}")
        sys.exit(1)

    mismatched_sgs = {gid: vid for gid, vid in sg_vpcs.items() if vid != subnet_vpc}
    if mismatched_sgs:
        err(
            f"Subnets are in VPC {subnet_vpc!r}, but these security groups "
            "are in a different VPC:"
        )
        for gid, vid in mismatched_sgs.items():
            print(f"    {gid}  →  {vid}")
        info(
            "AgentCore requires all subnets AND security groups to share "
            "ONE VPC. Pick SGs that belong to the same VPC as the subnets."
        )
        sys.exit(1)

    if expected_vpc_id and expected_vpc_id != subnet_vpc:
        err(
            f"AGENTCORE_VPC_ID={expected_vpc_id!r} does not match the VPC "
            f"of the supplied subnets/SGs ({subnet_vpc!r})."
        )
        info(
            "Either drop AGENTCORE_VPC_ID (it's optional — subnet IDs "
            "already encode the VPC), or pick resources from the named VPC."
        )
        sys.exit(1)

    return subnet_vpc


def _format_subnet_row(s: dict, supported_azs: set[str]) -> str:
    """Single-line summary used by the interactive subnet picker."""
    name = next(
        (
            t["Value"]
            for t in s.get("Tags", []) or []
            if t.get("Key") == "Name"
        ),
        "",
    )
    az_id = s.get("AvailabilityZoneId", "")
    badge = ""
    if supported_azs:
        badge = (
            f" {GREEN}[ok]{NC}"
            if az_id in supported_azs
            else f" {YELLOW}[unsupported AZ]{NC}"
        )
    label = f"  {name}" if name else ""
    return (
        f"{s['SubnetId']:24s}  "
        f"az={az_id:11s}  "
        f"cidr={s.get('CidrBlock', '?'):20s}"
        f"{label}{badge}"
    )


def _format_sg_row(g: dict) -> str:
    """Single-line summary used by the interactive security-group picker."""
    return (
        f"{g['GroupId']:22s}  "
        f"{(g.get('GroupName') or ''):28s}  "
        f"{(g.get('Description') or '')[:60]}"
    )


def resolve_network_config(
    sess: boto3.Session,
    region: str,
    env: dict[str, str],
    non_interactive: bool,
) -> dict[str, str]:
    """Resolve the three network-related CFN parameters.

    Returns a dict ready to splat into the deploy script's ``parameters``
    list:

        {
            "NetworkMode":          "PUBLIC" | "VPC",
            "VpcSubnetIds":         "subnet-aaa,subnet-bbb",       # "" in PUBLIC
            "VpcSecurityGroupIds":  "sg-aaa,sg-bbb",               # "" in PUBLIC
        }

    Resolution order:
      1. ``env`` (AGENTCORE_NETWORK_MODE, AGENTCORE_VPC_SUBNETS,
         AGENTCORE_VPC_SECURITY_GROUPS)
      2. Interactive prompts (when ``non_interactive`` is False)
      3. Default: PUBLIC

    For VPC mode, the function:
      - Validates the region appears in SUPPORTED_AGENTCORE_AZ_IDS
        (warns only — AWS may extend support before this table is updated).
      - Validates every supplied subnet maps to an AgentCore-supported
        AZ ID via ``ec2:DescribeSubnets`` (hard fail; AgentCore rejects
        unsupported AZs).
      - For interactive runs, drives the operator through a 3-step picker
        (VPC → subnets → SGs) filtered to AgentCore-eligible AZs.
    """
    mode_default = (env.get("AGENTCORE_NETWORK_MODE") or "PUBLIC").strip().upper()
    if mode_default not in ("PUBLIC", "VPC"):
        warn(
            f"AGENTCORE_NETWORK_MODE={mode_default!r} is invalid. "
            "Using PUBLIC."
        )
        mode_default = "PUBLIC"

    # ── 1. Pick the mode ─────────────────────────────────────────────────
    if non_interactive:
        mode = mode_default
        info(f"Network mode: {mode} (from .env)")
    elif "AGENTCORE_NETWORK_MODE" in env:
        mode = mode_default
        info(f"Network mode: {mode} (from .env)")
    else:
        print()
        print(
            "Choose how AgentCore Runtime connects to the network:\n"
            "\n"
            f"  {CYAN}[1]{NC} {BOLD}PUBLIC{NC}  "
            f"{GREEN}(recommended for evaluation){NC}\n"
            "      - Runs on the AWS-managed network. Outbound internet\n"
            "        works out of the box — Zscaler OneAPI is reachable.\n"
            "      - No VPC plumbing, no NAT gateway, no extra cost.\n"
            "      - Cannot reach private resources (RDS, internal APIs,\n"
            "        Zscaler private DNS).\n"
            "\n"
            f"  {CYAN}[2]{NC} {BOLD}VPC{NC}     "
            f"{YELLOW}(needed for private-network access){NC}\n"
            "      - AgentCore places ENIs in subnets + SGs you own.\n"
            "      - Subnets MUST be in AgentCore-supported AZ IDs. The\n"
            "        deploy script validates this against AWS's published\n"
            "        per-region AZ-ID table.\n"
            "      - For outbound internet (required by Zscaler OneAPI),\n"
            "        place the ENIs in PRIVATE subnets with a NAT gateway.\n"
            "        Public subnets do NOT provide internet to AgentCore.\n"
            "      - First deploy in this account also brings up the\n"
            "        AWSServiceRoleForBedrockAgentCoreNetwork SLR — the\n"
            "        IAM stack grants the narrow CreateServiceLinkedRole\n"
            "        perm needed for that automatically.\n"
        )
        default_idx = "2" if mode_default == "VPC" else "1"
        raw = input(
            f"  {BOLD}Choice{NC} {CYAN}[1-2]{NC} "
            f"{DIM}(default {default_idx}){NC}: "
        ).strip()
        mode = {"1": "PUBLIC", "2": "VPC"}.get(raw, mode_default)
        ok(f"Chose: {mode}")

    if mode == "PUBLIC":
        return {
            "NetworkMode": "PUBLIC",
            "VpcSubnetIds": "",
            "VpcSecurityGroupIds": "",
        }

    # ── 2. VPC mode — region support sanity check ────────────────────────
    supported_azs = supported_agentcore_az_ids(region)
    if not supported_azs:
        warn(
            f"Region {region!r} is not in the AgentCore VPC support table "
            "this script ships with. AgentCore may have added support since — "
            "the deploy will still try, and AgentCore's API will reject "
            "unsupported AZs at create time. If it fails, see "
            "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html#supported-az"
        )

    # ── 3. VPC mode — resolve subnets + SGs ──────────────────────────────
    raw_subnets = env.get("AGENTCORE_VPC_SUBNETS", "").strip()
    raw_sgs = env.get("AGENTCORE_VPC_SECURITY_GROUPS", "").strip()
    env_vpc_id = env.get("AGENTCORE_VPC_ID", "").strip()
    have_env_selection = bool(raw_subnets and raw_sgs)

    if non_interactive and not have_env_selection:
        err(
            "NetworkMode=VPC requires AGENTCORE_VPC_SUBNETS and "
            "AGENTCORE_VPC_SECURITY_GROUPS in .env when running with "
            "--non-interactive."
        )
        sys.exit(1)

    if have_env_selection:
        subnet_ids = [s.strip() for s in raw_subnets.split(",") if s.strip()]
        sg_ids = [s.strip() for s in raw_sgs.split(",") if s.strip()]
        info(
            f"VPC subnets: {','.join(subnet_ids)} "
            f"(from AGENTCORE_VPC_SUBNETS)"
        )
        info(
            f"VPC security groups: {','.join(sg_ids)} "
            f"(from AGENTCORE_VPC_SECURITY_GROUPS)"
        )
        # Cross-validate the env-supplied IDs ALL belong to the same VPC
        # (and, if AGENTCORE_VPC_ID is also set, that they match it). AWS
        # would catch a cross-VPC selection at CreateAgentRuntime time, but
        # only after 5+ minutes of stack launch. Failing here is much
        # cheaper. Returns the resolved VPC ID for the deploy log.
        resolved_vpc = validate_resources_share_vpc(
            sess, subnet_ids, sg_ids, expected_vpc_id=env_vpc_id
        )
        if resolved_vpc:
            info(f"All resources resolved to VPC: {resolved_vpc}")
    else:
        # Interactive 3-step picker: VPC → subnets → SGs.
        # ── 3a. VPC ──────────────────────────────────────────────────
        try:
            vpcs = list_vpcs(sess)
        except ClientError as e:
            err(f"Could not list VPCs: {_short_aws_error(e)}")
            sys.exit(1)
        if not vpcs:
            err(
                "No VPCs found in this region. Create one (or pick a "
                "region that has one) and re-run."
            )
            sys.exit(1)
        vpc_items: list[tuple[str, str]] = []
        for v in vpcs:
            name = next(
                (
                    t["Value"]
                    for t in v.get("Tags", []) or []
                    if t.get("Key") == "Name"
                ),
                "",
            )
            default_badge = f" {GREEN}[default]{NC}" if v.get("IsDefault") else ""
            label = (
                f"{v['VpcId']:22s}  cidr={v.get('CidrBlock', '?'):20s}"
                f"  {name}{default_badge}"
            )
            vpc_items.append((v["VpcId"], label))
        if env_vpc_id and any(v["VpcId"] == env_vpc_id for v in vpcs):
            vpc_id = env_vpc_id
            info(f"VPC: {vpc_id} (from AGENTCORE_VPC_ID)")
        else:
            print()
            print(f"{BOLD}Select VPC for AgentCore Runtime ENIs{NC}")
            for i, (_, lbl) in enumerate(vpc_items, 1):
                print(f"  {CYAN}[{i}]{NC} {lbl}")
            while True:
                raw = input(
                    f"Pick {CYAN}1-{len(vpc_items)}{NC}: "
                ).strip()
                try:
                    vpc_id = vpc_items[int(raw) - 1][0]
                    break
                except (ValueError, IndexError):
                    warn(f"Invalid choice: {raw!r}.")
            ok(f"Selected VPC: {vpc_id}")

        # ── 3b. Subnets (filtered to supported AZs) ──────────────────
        try:
            all_subnets = list_subnets_for_vpc(sess, vpc_id)
        except ClientError as e:
            err(f"Could not list subnets for {vpc_id}: {_short_aws_error(e)}")
            sys.exit(1)
        if supported_azs:
            eligible = [
                s
                for s in all_subnets
                if s.get("AvailabilityZoneId") in supported_azs
            ]
            ineligible_count = len(all_subnets) - len(eligible)
        else:
            eligible = all_subnets
            ineligible_count = 0
        if not eligible:
            err(
                f"VPC {vpc_id} has no subnets in AgentCore-supported AZ IDs "
                f"({sorted(supported_azs) or 'region unsupported'}). "
                "Create subnets in the supported AZs and re-run."
            )
            sys.exit(1)
        if ineligible_count:
            warn(
                f"Hiding {ineligible_count} subnet(s) in unsupported AZ IDs "
                "(AgentCore would reject them at create time)."
            )
        subnet_items: list[tuple[str, str]] = [
            (s["SubnetId"], _format_subnet_row(s, supported_azs))
            for s in eligible
        ]
        subnet_ids = prompt_multi_choice(
            "Select subnets (recommend >=2 in different AZs)",
            subnet_items,
            min_count=1,
        )
        # AZ-spread check (advisory).
        chosen_azs = {
            s["AvailabilityZoneId"]
            for s in eligible
            if s["SubnetId"] in subnet_ids
        }
        if len(chosen_azs) < 2:
            warn(
                f"Only one Availability Zone selected ({next(iter(chosen_azs), '?')}). "
                "AWS strongly recommends >=2 AZs for HA — consider picking "
                "another subnet."
            )

        # ── 3c. Security groups ──────────────────────────────────────
        try:
            sgs = list_security_groups_for_vpc(sess, vpc_id)
        except ClientError as e:
            err(
                f"Could not list security groups for {vpc_id}: "
                f"{_short_aws_error(e)}"
            )
            sys.exit(1)
        if not sgs:
            err(f"VPC {vpc_id} has no security groups. (This shouldn't happen.)")
            sys.exit(1)
        sg_items: list[tuple[str, str]] = [
            (g["GroupId"], _format_sg_row(g)) for g in sgs
        ]
        sg_ids = prompt_multi_choice(
            "Select security group(s) (outbound must allow your Zscaler "
            "OneAPI tenant + any private resources the container will "
            "talk to)",
            sg_items,
            min_count=1,
        )

    # ── 4. Hard-validate AZ-IDs (catches stale env-driven subnet lists) ──
    ok_subnets, bad_subnets = validate_subnet_az_ids(sess, subnet_ids, region)
    if bad_subnets:
        err(
            "The following subnets are in AZ IDs AgentCore does NOT support "
            f"in {region}:"
        )
        for sid, az in bad_subnets:
            print(f"    {sid}  →  {az}")
        print()
        info(
            f"Supported AZ IDs for {region}: "
            f"{sorted(supported_agentcore_az_ids(region))}"
        )
        info(
            "Either pick subnets in supported AZs, or remove the bad ones "
            "from AGENTCORE_VPC_SUBNETS and re-run."
        )
        sys.exit(1)

    return {
        "NetworkMode": "VPC",
        "VpcSubnetIds": ",".join(ok_subnets),
        "VpcSecurityGroupIds": ",".join(sg_ids),
    }


# ──────────────────────────────────────────────────────────────────────────
# AWS helpers
# ──────────────────────────────────────────────────────────────────────────

def get_session(region: str) -> boto3.Session:
    try:
        sess = boto3.Session(region_name=region)
        sts = sess.client("sts")
        ident = sts.get_caller_identity()
        ok(f"AWS credentials valid — account {ident['Account']} as {ident['Arn']}")
        return sess
    except NoCredentialsError:
        err("No AWS credentials found. Run `aws configure` or export AWS_PROFILE.")
        sys.exit(1)
    except ClientError as e:
        err(f"AWS credential check failed: {e}")
        sys.exit(1)


def ensure_asset_bucket(sess: boto3.Session, bucket_name: str) -> None:
    s3 = sess.client("s3")
    region = sess.region_name or DEFAULT_REGION
    try:
        s3.head_bucket(Bucket=bucket_name)
        ok(f"Asset bucket exists: s3://{bucket_name}")
        return
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
            err(f"Cannot access asset bucket {bucket_name}: {e}")
            sys.exit(1)

    info(f"Creating asset bucket: s3://{bucket_name}")
    if region == "us-east-1":
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"},
    )
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    ok(f"Created bucket s3://{bucket_name}")


def upload_nested_templates(
    sess: boto3.Session, bucket: str, prefix: str
) -> str:
    s3 = sess.client("s3")
    if not prefix.endswith("/"):
        prefix += "/"
    info(f"Uploading nested templates to s3://{bucket}/{prefix}")
    for tpl in NESTED_TEMPLATES:
        path = CFN_DIR / tpl
        if not path.exists():
            err(f"Missing nested template: {path}")
            sys.exit(1)
        s3.upload_file(str(path), bucket, f"{prefix}{tpl}")
        ok(f"  uploaded {tpl}")
    return prefix


def cleanup_orphaned_resources(
    sess: boto3.Session, prefix: str, *, non_interactive: bool
) -> None:
    """Sweep up resources that get orphaned when CFN OnFailure=DELETE rolls back.

    The most common case: a prior failed deploy created the provisioner Lambda
    but the rollback couldn't clean it up before CFN gave up. The next deploy
    then fails at "Function already exists". Same can happen with the secret
    (Secrets Manager has a 7-day soft-delete window by default).
    """
    lam = sess.client("lambda")
    sm = sess.client("secretsmanager")
    orphans: list[tuple[str, str, callable]] = []  # (kind, name, deleter)

    # Lambdas
    for fn_name in (
        f"{prefix}-runtime-provisioner",
        f"{prefix}-gateway-provisioner",
    ):
        try:
            lam.get_function(FunctionName=fn_name)
            orphans.append(("Lambda", fn_name, lambda n=fn_name: lam.delete_function(FunctionName=n)))
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                warn(f"  could not check Lambda {fn_name}: {_short_aws_error(e)}")

    # Secrets Manager (only the one we'd create — not user-supplied existing secrets)
    secret_name = f"{prefix}/credentials"
    try:
        sm.describe_secret(SecretId=secret_name)
        orphans.append((
            "Secret", secret_name,
            lambda n=secret_name: sm.delete_secret(
                SecretId=n, ForceDeleteWithoutRecovery=True,
            ),
        ))
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            warn(f"  could not check secret {secret_name}: {_short_aws_error(e)}")

    if not orphans:
        return

    warn(
        "Found resources from a previous failed deploy that would block this one:"
    )
    for kind, name, _ in orphans:
        print(f"    [{kind}] {name}")

    if non_interactive:
        info("Auto-cleaning (running --non-interactive).")
    else:
        confirm = input(
            f"  {BOLD}Delete these now so the deploy can proceed?{NC} "
            f"{CYAN}[Y/n]{NC}: "
        ).strip().lower()
        if confirm in ("n", "no"):
            err("Cannot proceed — clean these up manually and re-run.")
            sys.exit(1)

    for kind, name, deleter in orphans:
        try:
            deleter()
            ok(f"    deleted {kind} {name}")
        except ClientError as e:
            warn(f"    could not delete {kind} {name}: {_short_aws_error(e)}")


def _pip_install_into(target_dir: Path, requirements: list[str]) -> None:
    """Install ``requirements`` into ``target_dir`` via ``pip --target``.

    Uses the current Python interpreter's pip. Pure-Python wheels (boto3,
    botocore, urllib3, jmespath, python-dateutil, six) install cleanly
    across platforms — no manylinux wheel selection needed for Lambda.
    """
    import subprocess

    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(target_dir),
        "--upgrade",
        "--quiet",
        "--no-compile",   # don't ship .pyc — Lambda will rebuild at cold start
        *requirements,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        err("Could not run pip — is Python's pip module available in this env?")
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        err(f"pip install failed for {requirements}: {exc.stderr or exc.stdout}")
        raise SystemExit(1) from exc


def _build_lambda_zip(src_path: Path, extra_deps: list[str]) -> bytes:
    """Build a Lambda deployment zip in memory.

    The zip contains the handler module at the top level plus any
    ``extra_deps`` installed via pip into the same directory tree. Files
    are deflated; ``.pyc`` cache directories are excluded.
    """
    import io
    import shutil
    import tempfile
    import zipfile

    stage = Path(tempfile.mkdtemp(prefix="zscaler-mcp-lambda-"))
    try:
        shutil.copy(src_path, stage / src_path.name)
        if extra_deps:
            _pip_install_into(stage, extra_deps)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(stage.rglob("*")):
                if path.is_dir():
                    continue
                # Skip cache artefacts and metadata that bloat the zip
                # without contributing to the function's runtime behavior.
                rel = path.relative_to(stage).as_posix()
                if "__pycache__/" in rel or rel.endswith(".pyc"):
                    continue
                if rel.endswith(".dist-info/RECORD"):
                    continue
                zf.write(path, arcname=rel)
        buf.seek(0)
        return buf.getvalue()
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def upload_lambda_packages(sess: boto3.Session, bucket: str, prefix: str) -> dict[str, str]:
    """Zip each provisioner Lambda and upload it to S3 under a hash-suffixed key.

    For Lambdas that need newer SDK shapes than the runtime ships, the
    relevant pip requirements are listed alongside the source in
    ``LAMBDA_PACKAGES`` and installed into the zip via ``pip --target``.

    Returns a mapping ``{zip_name: full_s3_key}`` so callers can pass the
    actual S3 key into CloudFormation as a stack parameter. The key embeds
    an 8-char SHA-256 digest of the **source .py file only** (not the
    vendored pip artefacts, whose mtimes are non-deterministic). When the
    source changes, the key changes, which:

    1. Triggers a CFN property change on the ``AWS::Lambda::Function``
       resource — so the Lambda function is actually redeployed.
    2. Triggers a property change on the ``Custom::AgentCoreGateway``
       resource — so its ``ensure_target`` codepath actually re-runs,
       cleanly reconciling the Gateway target (delete-and-recreate is
       baked into ``ensure_target`` to defeat AWS's apparent merge
       semantics on ``mcpToolSchema``).

    The legacy unsuffixed key (``lambda/<name>.zip``) is no longer written.
    Old stacks that were last deployed with the previous script will keep
    referencing the unsuffixed key; the very next deploy under this script
    swaps them onto a hash-suffixed key via the new CFN parameters.
    """
    import hashlib

    s3 = sess.client("s3")
    if not prefix.endswith("/"):
        prefix += "/"
    info(f"Packaging + uploading Lambda code to s3://{bucket}/{prefix}lambda/")
    keys: dict[str, str] = {}
    for src_name, zip_name, extra_deps in LAMBDA_PACKAGES:
        src_path = LAMBDA_DIR / src_name
        if not src_path.exists():
            err(f"Missing Lambda source: {src_path}")
            sys.exit(1)
        if extra_deps:
            info(f"  vendoring deps into {zip_name}: {', '.join(extra_deps)}")
        payload = _build_lambda_zip(src_path, extra_deps)
        digest = hashlib.sha256(src_path.read_bytes()).hexdigest()[:8]
        stem = zip_name.rsplit(".", 1)[0]
        key = f"{prefix}lambda/{stem}-{digest}.zip"
        s3.put_object(Bucket=bucket, Key=key, Body=payload)
        ok(f"  uploaded {key} ({len(payload):,} bytes)")
        keys[zip_name] = key
    return keys


def stack_status(sess: boto3.Session, stack_name: str) -> str | None:
    cfn = sess.client("cloudformation")
    try:
        resp = cfn.describe_stacks(StackName=stack_name)
        return resp["Stacks"][0]["StackStatus"]
    except ClientError as e:
        if "does not exist" in str(e):
            return None
        raise


# Stack states that are not updatable and require a delete first.
NON_UPDATABLE_STATES = {
    "CREATE_FAILED",
    "ROLLBACK_FAILED",
    "ROLLBACK_COMPLETE",
    "DELETE_FAILED",
    "UPDATE_ROLLBACK_FAILED",
}


def latest_failure_reasons(
    sess: boto3.Session, stack_name: str, max_events: int = 10
) -> list[str]:
    """Pull the most recent failure events from a stack so we can show *why* it failed."""
    cfn = sess.client("cloudformation")
    try:
        events = cfn.describe_stack_events(StackName=stack_name).get("StackEvents", [])
    except ClientError:
        return []
    reasons = []
    for evt in events:
        status = evt.get("ResourceStatus", "")
        reason = evt.get("ResourceStatusReason")
        if reason and ("FAILED" in status or "ROLLBACK" in status):
            res_id = evt.get("LogicalResourceId", "?")
            reasons.append(f"  • [{res_id}] {reason}")
            if len(reasons) >= max_events:
                break
    return reasons


def wait_for_stack(
    sess: boto3.Session,
    stack_name: str,
    terminal: list[str],
    *,
    capture_failures_at: tuple[str, ...] = (
        "CREATE_FAILED",
        "ROLLBACK_IN_PROGRESS",
        "DELETE_IN_PROGRESS",
        "UPDATE_ROLLBACK_IN_PROGRESS",
    ),
) -> tuple[str, list[str]]:
    """Poll a stack until it reaches a terminal state.

    Returns (final_status, failure_reasons). If `OnFailure=DELETE` was used on
    create_stack, the stack is destroyed at the end of a failed create — so we
    snapshot the failure reasons the first time we see a rollback/delete state
    so we can surface them after the stack disappears.

    If the stack is deleted mid-poll, returns ('STACK_DELETED', captured_reasons).
    """
    cfn = sess.client("cloudformation")
    info(f"Waiting for stack '{stack_name}'…")
    last_status = ""
    captured_failures: list[str] = []

    # Poll cadence: hit DescribeStacks at most every ~15s (CloudFormation
    # rate-limits it, and faster polling adds no real-world value because
    # stack updates flip status on the order of seconds-to-minutes). The
    # spinner redraws much faster than that so the user sees a live ticker.
    poll_interval = 15.0
    spinner_interval = 0.15
    use_spinner = COLOURS

    started = time.monotonic()
    last_poll = -poll_interval  # force a poll on the very first iteration
    spinner_idx = 0
    status = ""

    try:
        while True:
            now = time.monotonic()
            if now - last_poll >= poll_interval:
                last_poll = now
                try:
                    resp = cfn.describe_stacks(StackName=stack_name)
                except ClientError as e:
                    if "does not exist" in str(e):
                        # Likely OnFailure=DELETE swept the stack away after a failure
                        _clear_spinner_line()
                        return "STACK_DELETED", captured_failures
                    raise
                status = resp["Stacks"][0]["StackStatus"]
                if status != last_status:
                    _clear_spinner_line()
                    color = _color_for_stack_status(status)
                    elapsed = _fmt_elapsed(now - started)
                    print(
                        f"  {DIM}→{NC} status={color}{status}{NC} "
                        f"{DIM}(at {elapsed}){NC}"
                    )
                    last_status = status
                # Snapshot failure reasons early — once the stack is deleted they're gone
                if status in capture_failures_at and not captured_failures:
                    captured_failures = latest_failure_reasons(sess, stack_name)
                if status in terminal:
                    _clear_spinner_line()
                    return status, captured_failures

            if use_spinner and status:
                frame = _SPINNER_FRAMES[spinner_idx % len(_SPINNER_FRAMES)]
                color = _color_for_stack_status(status)
                elapsed = _fmt_elapsed(now - started)
                sys.stdout.write(
                    f"\r  {CYAN}{frame}{NC} waiting [{BOLD}{elapsed}{NC}] — "
                    f"{color}{status}{NC}   "
                )
                sys.stdout.flush()
                spinner_idx += 1

            time.sleep(spinner_interval if use_spinner else poll_interval)
    except KeyboardInterrupt:
        _clear_spinner_line()
        warn(
            f"Interrupted while waiting. Stack '{stack_name}' will continue "
            "in CloudFormation — re-run this script to resume monitoring."
        )
        raise


def handle_unrecoverable_state(
    sess: boto3.Session, stack_name: str, status: str, *, non_interactive: bool
) -> None:
    """Print a friendly explanation for a non-updatable stack state and offer to delete.

    Exits the program either way — the caller can re-run the deploy after cleanup.
    """
    err(f"Stack '{stack_name}' is in state {status} and cannot be updated.")
    print()
    if status == "ROLLBACK_COMPLETE":
        print(
            "  This means the previous CREATE failed and was rolled back. "
            "CloudFormation cannot update a rolled-back stack — it has to be "
            "deleted first, then re-created."
        )
    elif status == "DELETE_FAILED":
        print(
            "  This means a previous delete attempt failed partway through. "
            "Some resources are still around. Re-deleting usually works on the "
            "second try (CFN retries with --retain-resources for stuck items)."
        )
    elif status == "CREATE_FAILED":
        print(
            "  CloudFormation never got past the initial CREATE — possibly a "
            "permissions or quota error. The stack must be deleted before retrying."
        )
    elif status in ("ROLLBACK_FAILED", "UPDATE_ROLLBACK_FAILED"):
        print(
            "  CloudFormation tried to rollback after a failure and the rollback "
            "itself failed. You may need to manually clean up some resources "
            "before deletion will succeed."
        )

    reasons = latest_failure_reasons(sess, stack_name)
    if reasons:
        print()
        print("  Recent failure reasons from CloudFormation:")
        for r in reasons:
            print(r)
    print()

    if non_interactive:
        info("Re-run interactively (without --non-interactive) to delete and retry.")
        sys.exit(1)

    confirm = input(
        f"  {BOLD}Delete the stack {YELLOW}'{stack_name}'{NC}{BOLD} now and re-run deploy?{NC} "
        f"{CYAN}[y/N]{NC}: "
    ).strip().lower()
    if confirm not in ("y", "yes"):
        info("Aborted. Run `aws cloudformation delete-stack --stack-name "
             f"{stack_name}` (or this script's `destroy` command) to clean up.")
        sys.exit(1)

    info(f"Deleting stack '{stack_name}'…")
    cfn = sess.client("cloudformation")
    try:
        cfn.delete_stack(StackName=stack_name)
    except ClientError as e:
        err(f"Delete request failed: {_short_aws_error(e)}")
        sys.exit(1)
    final, captured = wait_for_stack(
        sess, stack_name, ["DELETE_COMPLETE", "DELETE_FAILED"],
    )
    if final in ("DELETE_COMPLETE", "STACK_DELETED"):
        ok(f"Stack '{stack_name}' deleted. Re-run `python aws_mcp_operations.py deploy`.")
        sys.exit(0)
    err(f"Stack delete ended in {final}.")
    for r in captured or latest_failure_reasons(sess, stack_name):
        print(r)
    info(
        "Some resources may need manual cleanup. Open the AWS Console → "
        "CloudFormation → click the stack → Events tab to see what's stuck."
    )
    sys.exit(1)


def _short_aws_error(e: ClientError) -> str:
    """Boil a boto3 ClientError down to one human-readable line."""
    err_dict = e.response.get("Error", {})
    code = err_dict.get("Code", "Unknown")
    msg = err_dict.get("Message", str(e))
    return f"{code}: {msg}"


def stack_outputs(sess: boto3.Session, stack_name: str) -> dict[str, str]:
    cfn = sess.client("cloudformation")
    try:
        resp = cfn.describe_stacks(StackName=stack_name)
    except ClientError:
        return {}
    outs = resp["Stacks"][0].get("Outputs", []) or []
    return {o["OutputKey"]: o["OutputValue"] for o in outs}


# ──────────────────────────────────────────────────────────────────────────
# DEPLOY
# ──────────────────────────────────────────────────────────────────────────

def cmd_deploy(args: argparse.Namespace) -> None:
    print_zscaler_logo()

    # ── Step 1: env file ────────────────────────────────────────────────
    step("Step 1: Load configuration")
    env_path = Path(args.env_file) if args.env_file else discover_env_file()
    env: dict[str, str] = {}
    if env_path and env_path.exists():
        env = load_env_file(env_path)
        ok(f"Loaded {len(env)} variables from {env_path}")
    else:
        warn("No env.properties found — falling back to interactive prompts.")

    # ── Step 2: AWS session ─────────────────────────────────────────────
    step("Step 2: Verify AWS credentials")
    region = env.get("AWS_REGION") or prompt("AWS region", DEFAULT_REGION)
    sess = get_session(region)
    account_id = sess.client("sts").get_caller_identity()["Account"]

    # ── Step 3: Stack-level params ──────────────────────────────────────
    step("Step 3: Stack configuration")
    stack_name = env.get("AWS_STACK_NAME") or prompt("Stack name", DEFAULT_STACK_NAME)
    resource_prefix = env.get("AWS_RESOURCE_NAME_PREFIX") or prompt(
        "Resource name prefix (lowercase, dashes)", DEFAULT_RESOURCE_PREFIX
    )
    asset_bucket = env.get("AWS_ASSET_BUCKET") or f"zscaler-mcp-cfn-{account_id}-{region}"
    info(f"Using asset bucket: {asset_bucket}")

    # ── Step 4: Image source ────────────────────────────────────────────
    # Resolution policy: the AWS Marketplace ECR is ALWAYS the default. The
    # only way to deviate is to explicitly set a non-empty ZSCALER_MCP_IMAGE_URI
    # in .env (whitespace-only / empty values are treated as unset).
    step("Step 4: Container image source")
    image_override = (env.get("ZSCALER_MCP_IMAGE_URI") or "").strip()
    if image_override:
        image_uri = image_override
        info(f"Image: {image_uri} (overridden via ZSCALER_MCP_IMAGE_URI)")
        if "709825985650" not in image_uri:
            warn(
                "Image URI is NOT the AWS Marketplace ECR — make sure your "
                "AgentCore execution role can pull it. Unsupported configuration."
            )
    else:
        image_uri = MARKETPLACE_IMAGE
        info(f"Image: {image_uri} (AWS Marketplace default)")
        info("→ Subscribing to the Zscaler MCP Server in AWS Marketplace is required.")
        info("  https://aws.amazon.com/marketplace (search 'Zscaler MCP Server')")

    # ── Step 5: Zscaler credentials in Secrets Manager ──────────────────
    step("Step 5: Zscaler OneAPI credentials in Secrets Manager")
    existing_secret = env.get("ZSCALER_SECRET_NAME")
    have_inline_creds = all(
        env.get(k)
        for k in ("ZSCALER_CLIENT_ID", "ZSCALER_CLIENT_SECRET",
                  "ZSCALER_VANITY_DOMAIN", "ZSCALER_CUSTOMER_ID")
    )

    cred_params: dict[str, str] = {}
    if existing_secret:
        cred_source = "UseExisting"
        info(f"Will reference existing Secrets Manager secret: {existing_secret}")
        info("(set in .env as ZSCALER_SECRET_NAME)")
        cred_params["ExistingSecretName"] = existing_secret
    elif have_inline_creds:
        cred_source = "CreateNew"
        info("Will create a new Secrets Manager secret from credentials in .env")
        info(
            f"  Secret name will be: {resource_prefix}/credentials "
            "(in the AWS_REGION above)"
        )
        cred_params["ZscalerClientId"]      = env["ZSCALER_CLIENT_ID"]
        cred_params["ZscalerClientSecret"]  = env["ZSCALER_CLIENT_SECRET"]
        cred_params["ZscalerVanityDomain"]  = env["ZSCALER_VANITY_DOMAIN"]
        cred_params["ZscalerCustomerId"]    = env["ZSCALER_CUSTOMER_ID"]
        cred_params["ZscalerCloud"]         = env.get("ZSCALER_CLOUD", "production")
    else:
        warn(
            "Neither ZSCALER_SECRET_NAME nor a complete set of "
            "ZSCALER_CLIENT_ID/SECRET/VANITY_DOMAIN/CUSTOMER_ID was found in .env."
        )
        if args.non_interactive:
            err("Cannot continue in --non-interactive mode without credentials.")
            sys.exit(1)
        # Fall back to interactive prompts, defaulting to CreateNew
        cred_source = "CreateNew"
        cred_params["ZscalerClientId"] = prompt("ZSCALER_CLIENT_ID", secret=True)
        cred_params["ZscalerClientSecret"] = prompt("ZSCALER_CLIENT_SECRET", secret=True)
        cred_params["ZscalerVanityDomain"] = prompt("ZSCALER_VANITY_DOMAIN")
        cred_params["ZscalerCustomerId"] = prompt("ZSCALER_CUSTOMER_ID")
        cred_params["ZscalerCloud"] = env.get("ZSCALER_CLOUD") or prompt(
            "ZSCALER_CLOUD", "production"
        )

    # ── Step 6: MCP server feature flags ────────────────────────────────
    # Just the lightweight feature toggles. Write-tools is the only knob that
    # belongs here — auth + Gateway architecture get their own steps below.
    step("Step 6: MCP server feature flags")
    if "ZSCALER_MCP_WRITE_ENABLED" in env:
        write_enabled = env["ZSCALER_MCP_WRITE_ENABLED"].lower() == "true"
        info(f"Write tools: {'enabled' if write_enabled else 'disabled'} (from .env)")
    elif args.non_interactive:
        write_enabled = False
    else:
        write_enabled = prompt_bool("Enable MCP write tools?", False)
    write_allowlist = env.get("ZSCALER_MCP_WRITE_TOOLS", "")
    if write_enabled and not write_allowlist and not args.non_interactive:
        write_allowlist = prompt(
            "Write-tool allowlist (comma-separated, blank = ALL writes)",
            "zpa_create_*,zia_update_*",
        )

    # ── Step 7: Architecture — how downstream agents reach the runtime ──
    # This is the most important architectural decision. It dictates the
    # auth options available in Step 8 and whether Step 9 (Gateway IdP)
    # runs at all. Explanation is laid out before the prompt so operators
    # don't have to read the docs to make an informed choice.
    #
    # Style note: bracketed [N] menu + looped re-prompt matches the Azure
    # and GCP deployment scripts (integrations/azure, integrations/google/gcp)
    # so operators get the same UX across hyperscalers.
    step("Step 7: Architecture — how downstream agents reach the runtime")
    print(
        "\nChoose how downstream agents (Amazon Quick Suite, Bedrock Agents,\n"
        "custom MCP clients) will reach the Zscaler MCP Server. This dictates\n"
        "which auth options are available in the next step.\n"
    )
    # Tag styling: green [recommended] for the safe path, yellow
    # [experimental] for the Gateway paths. Marker numbers follow suit so
    # the eye can pick out the recommended row at a glance.
    tag_recommended = f"{BOLD}{GREEN}[recommended]{NC}"
    tag_experimental = f"{BOLD}{YELLOW}[experimental]{NC}"
    marker_safe = f"{GREEN}[1]{NC}"
    marker_exp_2 = f"{YELLOW}[2]{NC}"
    marker_exp_3 = f"{YELLOW}[3]{NC}"

    print(f"  {marker_safe} {BOLD}Direct runtime (no Gateway){NC}  {tag_recommended}")
    print("      - Callers invoke the runtime via bedrock-agentcore:InvokeAgentRuntime")
    print("        (boto3, agentcore CLI, AgentCore Sandbox, Lambda, etc.)")
    print("      - Any auth mode works: jwt / zscaler / api-key / none")
    print("      - Simplest deploy — no external IdP needed\n")
    print(
        f"  {marker_exp_2} {BOLD}Provision a new AgentCore Gateway in front of the runtime{NC}  "
        f"{tag_experimental}"
    )
    print("      - Gateway exposes a single OAuth-fronted MCP URL")
    print("      - REQUIRES a JWT/OIDC IdP (Auth0, Cognito, Okta, Entra, etc.)")
    print("        — AWS Gateway only supports CUSTOM_JWT inbound auth.")
    print("      - You'll provide the IdP's discovery URL + audience + client ID")
    print("        in Step 9. Make sure that IdP exists BEFORE proceeding.")
    print(
        f"      - {YELLOW}Known limitation:{NC} tools/list propagation through the Gateway"
    )
    print("        target is currently inconsistent — downstream clients may")
    print("        see a subset of MCP tools or none at all.\n")
    print(
        f"  {marker_exp_3} {BOLD}Attach the runtime as a target on an existing AgentCore Gateway{NC}  "
        f"{tag_experimental}"
    )
    print("      - You already operate a Gateway — we'll just add our target")
    print("      - The existing Gateway's IdP is reused (no IdP setup needed here)")
    print("      - You'll provide the existing Gateway's ID in Step 9")
    print(
        f"      - Same Gateway tool-discovery {YELLOW}limitation{NC} as option 2 applies.\n"
    )

    architecture_options = {
        "1": ("Direct runtime (no Gateway)",                                                   "false", "create"),
        "2": ("Provision a new AgentCore Gateway in front of the runtime [experimental]",     "true",  "create"),
        "3": ("Attach to an existing AgentCore Gateway [experimental]",                        "true",  "attach"),
    }

    # Compute the displayed default from .env. The .env value pre-fills
    # the prompt for repeat deploys, but the user can always override at
    # the prompt — we no longer silently skip the question when .env has
    # ENABLE_AGENTCORE_GATEWAY set (the previous behavior surprised users
    # who carried over =true from an earlier Gateway-enabled deploy).
    env_mode_default = (env.get("GATEWAY_MODE") or "create").strip().lower()
    if env_mode_default not in ("create", "attach"):
        env_mode_default = "create"
    env_gw_enabled = (
        "ENABLE_AGENTCORE_GATEWAY" in env
        and env["ENABLE_AGENTCORE_GATEWAY"].lower() == "true"
    )
    if not env_gw_enabled:
        default_arch_key = "1"
    elif env_mode_default == "attach":
        default_arch_key = "3"
    else:
        default_arch_key = "2"

    if args.non_interactive:
        # Non-interactive mode: silently use the .env-derived default so
        # CI / scripted deploys remain reproducible.
        arch_key = default_arch_key
        env_origin = (
            f"ENABLE_AGENTCORE_GATEWAY={env['ENABLE_AGENTCORE_GATEWAY'].lower()}"
            if "ENABLE_AGENTCORE_GATEWAY" in env
            else "no .env override"
        )
        if env_gw_enabled:
            env_origin += f", GATEWAY_MODE={env_mode_default}"
        info(
            f"Architecture: {architecture_options[arch_key][0]} "
            f"(non-interactive — {env_origin})"
        )
    else:
        # Always prompt in interactive mode. Loop until we get a valid
        # number; an empty response accepts the displayed default.
        while True:
            try:
                raw = input(
                    f"  {BOLD}Choice{NC} {CYAN}[1-3]{NC} "
                    f"{DIM}(default {default_arch_key}){NC}: "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                err("\nAborted.")
                sys.exit(1)
            if not raw:
                arch_key = default_arch_key
                break
            if raw in architecture_options:
                arch_key = raw
                break
            warn(f"Invalid choice: {raw!r}. Pick 1-3 or press Enter for default.")

    arch_label, enable_flag, mode = architecture_options[arch_key]
    gateway_enabled = enable_flag == "true"
    ok(f"Chose: {arch_label}")
    gw_params: dict[str, str] = {
        "EnableAgentCoreGateway": enable_flag,
        "GatewayMode": mode,
    }

    # ── Step 7.5: Network mode (PUBLIC vs VPC) ──────────────────────────
    # Distinct from Step 7 (which controls the inbound topology — Gateway
    # vs direct). This step controls AgentCore's OUTBOUND network: where
    # the container's ENIs live. PUBLIC keeps everything on the
    # AWS-managed network; VPC injects ENIs into customer-owned subnets
    # so the container can reach private RDS/internal APIs/Zscaler
    # private DNS. The validator inside resolve_network_config() hard-
    # fails on subnets in AZ IDs AgentCore doesn't support — AWS rejects
    # those at create time anyway, but we'd rather block before the
    # 10-minute stack launch than after.
    step("Step 7.5: Network mode (PUBLIC vs VPC)")
    network_params = resolve_network_config(
        sess, region, env, non_interactive=args.non_interactive
    )

    # ── Step 8: Runtime authentication ──────────────────────────────────
    # Auth enforced on the runtime's HTTP endpoint itself. Independent of
    # any Gateway in front (when a Gateway is present, this controls how
    # the GATEWAY authenticates TO the runtime).
    step("Step 8: Runtime authentication")
    if gateway_enabled:
        print(
            "\nYou chose to deploy with a Gateway. The runtime auth mode is\n"
            "forced to 'jwt' because AgentCore Gateway always reaches the\n"
            "runtime with an OAuth Bearer token — the runtime needs a\n"
            "customJWTAuthorizer to accept it. The JWT issuer/audience are\n"
            "auto-derived from the Gateway settings below (Step 9), so you\n"
            "don't need ZSCALER_MCP_AUTH_* variables in .env separately.\n"
        )
    else:
        print(
            "\nAuth enforced on the runtime's MCP endpoint. Callers using\n"
            "bedrock-agentcore:InvokeAgentRuntime must either present matching\n"
            "credentials in allowlisted headers OR rely on the container-side\n"
            "env-var fallback (useful for the AgentCore Sandbox playground).\n"
        )
    # When Gateway is enabled, runtime auth is forced to 'jwt'. AgentCore
    # Gateway always calls the runtime with an OAuth Bearer token; any other
    # runtime mode (none/zscaler/api-key — all SigV4 under the hood) makes
    # the runtime reject the call with "Authorization method mismatch".
    # The Gateway and runtime always share the same IdP and audience in
    # this topology, so we derive the JWT settings from the Gateway block
    # instead of duplicating them in the .env.
    if gateway_enabled:
        auth_mode = "jwt"
        env_auth_mode = env.get("ZSCALER_MCP_AUTH_MODE")
        if env_auth_mode and env_auth_mode != "jwt":
            warn(
                f"ZSCALER_MCP_AUTH_MODE={env_auth_mode!r} is ignored when "
                "ENABLE_AGENTCORE_GATEWAY=true — Gateway-fronted runtimes "
                "must use 'jwt' (the only mode that accepts the Gateway's "
                "OAuth Bearer)."
            )
        info("MCP auth mode: jwt (auto — required when Gateway is enabled)")
    else:
        auth_mode = env.get("ZSCALER_MCP_AUTH_MODE") or env.get("MCP_AUTH_MODE")
        if auth_mode:
            info(f"MCP auth mode: {auth_mode} (from .env)")
        elif not args.non_interactive:
            auth_mode = prompt_choice(
                "MCP-client authentication mode",
                ["jwt", "zscaler", "api-key", "none"],
                "zscaler",
            )
        auth_mode = auth_mode or "zscaler"

    auth_params: dict[str, str] = {"McpAuthMode": auth_mode}
    if auth_mode == "jwt":
        if gateway_enabled:
            # Pull straight from the Gateway block — the runtime's JWT
            # config is mathematically identical to the Gateway's inbound
            # config (same IdP, same audience). Requiring users to repeat
            # these values in ZSCALER_MCP_AUTH_* is what pushed admins into
            # mismatched configs in earlier iterations.
            gw_issuer = env.get("GATEWAY_INBOUND_ISSUER", "").strip()
            gw_discovery = env.get("GATEWAY_INBOUND_DISCOVERY_URL", "").strip()
            if not gw_issuer and gw_discovery:
                # Derive issuer from "<issuer>/.well-known/openid-configuration"
                gw_issuer = gw_discovery.rsplit(
                    "/.well-known/openid-configuration", 1
                )[0] + "/"
            auth_params["JwtIssuer"] = (
                env.get("ZSCALER_MCP_AUTH_ISSUER") or gw_issuer
            )
            auth_params["JwtAudience"] = (
                env.get("ZSCALER_MCP_AUTH_AUDIENCE")
                or env.get("GATEWAY_INBOUND_ALLOWED_AUDIENCE", "")
            )
            auth_params["JwtDiscoveryUrl"] = (
                env.get("ZSCALER_MCP_AUTH_JWT_DISCOVERY_URL") or gw_discovery
            )
            auth_params["JwtAllowedClients"] = env.get(
                "ZSCALER_MCP_AUTH_JWT_ALLOWED_CLIENTS", ""
            )
        else:
            auth_params["JwtIssuer"] = env.get("ZSCALER_MCP_AUTH_ISSUER") or prompt(
                "Runtime JWT issuer (e.g. https://my-tenant.us.auth0.com/)"
            )
            auth_params["JwtAudience"] = (
                env.get("ZSCALER_MCP_AUTH_AUDIENCE") or "zscaler-mcp-server"
            )
            auth_params["JwtDiscoveryUrl"] = env.get(
                "ZSCALER_MCP_AUTH_JWT_DISCOVERY_URL", ""
            )
            auth_params["JwtAllowedClients"] = env.get(
                "ZSCALER_MCP_AUTH_JWT_ALLOWED_CLIENTS", ""
            )
        # JWKS URI: take from .env if provided, otherwise derive from the
        # issuer's OIDC discovery doc. Every compliant OIDC IdP publishes
        # `jwks_uri` at <issuer>/.well-known/openid-configuration — this
        # gives us a vendor-neutral default that works for Auth0, Okta,
        # Cognito, Entra ID, Google, Keycloak, etc. We only prompt as a
        # last resort.
        auth_params["JwtJwksUri"] = (
            env.get("ZSCALER_MCP_AUTH_JWKS_URI")
            or _derive_jwks_uri(auth_params["JwtIssuer"])
            or prompt(
                "Runtime JWKS URI "
                "(could not auto-derive from issuer; "
                "e.g. https://my-tenant.us.auth0.com/.well-known/jwks.json)"
            )
        )
    elif auth_mode == "api-key":
        auth_params["ApiKey"] = env.get("ZSCALER_MCP_AUTH_API_KEY") or prompt(
            "API key (blank = auto-generate)", secret=True
        )
        if not auth_params["ApiKey"]:
            import secrets

            auth_params["ApiKey"] = secrets.token_urlsafe(32)
            ok("Auto-generated API key (saved to deploy-state)")

    # No additional incompatibility check needed — auth_mode is auto-forced
    # to 'jwt' above when gateway_enabled is true.

    # ── Step 9: Gateway IdP / target details (conditional) ──────────────
    if gateway_enabled:
        step("Step 9: Gateway IdP and target details")
        if mode == "attach":
            existing_id = env.get("EXISTING_GATEWAY_ID") or (
                "" if args.non_interactive else prompt(
                    "Existing Gateway ID to attach to "
                    "(aws bedrock-agentcore-control list-gateways)"
                )
            )
            if not existing_id:
                err("EXISTING_GATEWAY_ID is required when attaching to an existing Gateway.")
                sys.exit(1)
            gw_params["ExistingGatewayId"] = existing_id
            info(
                "Attach mode: this stack will only register a target on the existing "
                "Gateway. The Gateway itself is owned by you — destroy will not touch it."
            )
        else:
            print(
                "\nProvisioning a NEW AgentCore Gateway with a CUSTOM_JWT authorizer.\n"
                "Three values are required (all from the IdP you set up earlier):\n"
                "\n"
                "  - Discovery URL or Issuer (the IdP's well-known endpoint)\n"
                "  - Allowed audience (the API identifier / resource server URI)\n"
                "  - Allowed client ID(s) (the application(s) authorized to call us)\n"
                "\n"
                "If you haven't set these up yet, abort now (Ctrl-C), create the IdP\n"
                "objects, and re-run. The Auth0 quick-start in the deployment guide\n"
                "shows what to create: docs/deployment/amazon_bedrock_agentcore.md\n"
            )
            gw_params["GatewayInboundDiscoveryUrl"] = env.get(
                "GATEWAY_INBOUND_DISCOVERY_URL", ""
            ).strip()
            gw_params["GatewayInboundIssuer"] = env.get(
                "GATEWAY_INBOUND_ISSUER", ""
            ).strip()
            if not gw_params["GatewayInboundDiscoveryUrl"] and not gw_params["GatewayInboundIssuer"]:
                if args.non_interactive:
                    err(
                        "Either GATEWAY_INBOUND_DISCOVERY_URL or GATEWAY_INBOUND_ISSUER "
                        "must be set when provisioning a new Gateway."
                    )
                    sys.exit(1)
                gw_params["GatewayInboundIssuer"] = prompt(
                    "Gateway inbound OIDC issuer (e.g. https://my-tenant.us.auth0.com/)"
                )
            gw_params["GatewayInboundAllowedAudience"] = env.get(
                "GATEWAY_INBOUND_ALLOWED_AUDIENCE", ""
            ).strip()
            if not gw_params["GatewayInboundAllowedAudience"]:
                if args.non_interactive:
                    err(
                        "GATEWAY_INBOUND_ALLOWED_AUDIENCE must be set when provisioning a "
                        "new Gateway. This is the API Identifier from your IdP "
                        "(in Auth0: Applications > APIs > Identifier)."
                    )
                    sys.exit(1)
                gw_params["GatewayInboundAllowedAudience"] = prompt(
                    "Allowed audience (Auth0: API Identifier, e.g. urn:zscaler-mcp:gateway)"
                )
            gw_params["GatewayInboundAllowedScopes"] = env.get(
                "GATEWAY_INBOUND_ALLOWED_SCOPES", ""
            ).strip()
            gw_params["GatewayOAuthClientId"] = env.get(
                "GATEWAY_OAUTH_CLIENT_ID", ""
            ).strip()
            if not gw_params["GatewayOAuthClientId"]:
                if args.non_interactive:
                    err(
                        "GATEWAY_OAUTH_CLIENT_ID must be set when provisioning a new "
                        "Gateway. This is the Auth0/IdP Application Client ID."
                    )
                    sys.exit(1)
                gw_params["GatewayOAuthClientId"] = prompt(
                    "OAuth client ID(s) accepted by the Gateway (Auth0: Application Client ID; "
                    "comma-separated for multiple)"
                )
            # Choose the JWT claim that carries the OAuth client ID. The
            # Gateway's built-in `allowedClients` matcher reads `client_id`
            # specifically and reports any mismatch as 403 insufficient_scope.
            # That works out of the box for Cognito only — Auth0/Okta/Entra/
            # Keycloak/Google use the RFC-7519-standard `azp` (Okta uses
            # `cid`). For non-Cognito IdPs the Lambda emits a `customClaims`
            # matcher on the named claim instead, which is the IdP-agnostic
            # equivalent of `allowedClients`.
            gw_params["GatewayInboundClientClaimName"] = env.get(
                "GATEWAY_INBOUND_CLIENT_CLAIM_NAME", ""
            ).strip()
            if not gw_params["GatewayInboundClientClaimName"]:
                gw_params["GatewayInboundClientClaimName"] = _infer_client_claim_name(
                    gw_params["GatewayInboundDiscoveryUrl"]
                    or gw_params["GatewayInboundIssuer"]
                )
                info(
                    f"Inbound JWT client-id claim auto-detected as "
                    f"'{gw_params['GatewayInboundClientClaimName']}' "
                    f"(override via GATEWAY_INBOUND_CLIENT_CLAIM_NAME)."
                )
            # Outbound credential provider for Gateway → Runtime. MCP-server
            # targets only accept OAUTH (AWS rejects JWT_PASSTHROUGH at the
            # API), so we either reuse a customer-supplied provider via
            # GATEWAY_OAUTH_PROVIDER_ARN or auto-create one from the inbound
            # IdP details + a client secret.
            gw_params["GatewayOAuthProviderArn"] = env.get(
                "GATEWAY_OAUTH_PROVIDER_ARN", ""
            ).strip()
            if gw_params["GatewayOAuthProviderArn"]:
                gw_params["GatewayOAuthProviderScopes"] = env.get(
                    "GATEWAY_OAUTH_PROVIDER_SCOPES", ""
                ).strip()
                gw_params["GatewayOAuthProviderGrantType"] = env.get(
                    "GATEWAY_OAUTH_PROVIDER_GRANT_TYPE", "CLIENT_CREDENTIALS"
                ).strip()
                info(
                    "Reusing existing OAuth2 credential provider — "
                    "GATEWAY_OAUTH_CLIENT_SECRET will be ignored."
                )
            else:
                gw_params["GatewayOAuthClientSecret"] = env.get(
                    "GATEWAY_OAUTH_CLIENT_SECRET", ""
                ).strip()
                if not gw_params["GatewayOAuthClientSecret"]:
                    if args.non_interactive:
                        err(
                            "GATEWAY_OAUTH_CLIENT_SECRET must be set when provisioning a "
                            "new Gateway (unless GATEWAY_OAUTH_PROVIDER_ARN is set). "
                            "This is the Auth0/IdP Application Client Secret — the "
                            "Gateway uses it (with the client ID above) via the "
                            "client_credentials grant to mint tokens for the runtime."
                        )
                        sys.exit(1)
                    gw_params["GatewayOAuthClientSecret"] = prompt(
                        "OAuth client secret (Auth0: Application Client Secret) — "
                        "used by the Gateway to mint tokens for the runtime",
                        secret=True,
                    )
                gw_params["GatewayOAuthProviderGrantType"] = env.get(
                    "GATEWAY_OAUTH_PROVIDER_GRANT_TYPE", "CLIENT_CREDENTIALS"
                ).strip()
                # Optional: override the requested scopes (default is to
                # pass the audience as a single scope value).
                gw_params["GatewayOAuthProviderScopes"] = env.get(
                    "GATEWAY_OAUTH_PROVIDER_SCOPES", ""
                ).strip()

            # IdP-agnostic escape hatch — applies whether we're auto-
            # provisioning or reusing an existing provider. Used to splice
            # IdP-specific query params (Auth0 audience, Entra v1 resource,
            # RFC 8707 resource indicators, etc.) into the token endpoint
            # URL when AgentCore's customOauth2 schema can't carry them.
            gw_params["GatewayTokenEndpointQuery"] = env.get(
                "GATEWAY_OAUTH_TOKEN_ENDPOINT_QUERY", ""
            ).strip()

        # Optional curated tool schema — applies in both modes.
        schema_file = env.get("GATEWAY_TOOL_SCHEMA_FILE", "")
        if schema_file:
            schema_path = Path(schema_file)
            if not schema_path.is_absolute():
                schema_path = SCRIPT_DIR / schema_path
            if schema_path.exists():
                gw_params["GatewayToolSchemaJson"] = schema_path.read_text().strip()
                ok(f"Loaded tool schema from {schema_path}")
            else:
                warn(
                    f"GATEWAY_TOOL_SCHEMA_FILE={schema_file} not found. "
                    "Deploying without a curated schema (ImplicitSync). The Gateway "
                    "will crawl the runtime live during target creation."
                )

    # ── Step 10: Upload nested templates + Lambda code ──────────────────
    step("Step 10: Upload nested templates + Lambda code")
    ensure_asset_bucket(sess, asset_bucket)
    asset_prefix = upload_nested_templates(sess, asset_bucket, "zscaler-mcp/")
    lambda_keys = upload_lambda_packages(sess, asset_bucket, asset_prefix)

    # ── Step 10b: Sweep up orphaned resources from prior failed deploys ─
    cleanup_orphaned_resources(
        sess, resource_prefix, non_interactive=args.non_interactive,
    )

    # ── Step 11: Launch root stack ──────────────────────────────────────
    step("Step 11: Launch CloudFormation stack")
    cfn = sess.client("cloudformation")

    parameters = [
        {"ParameterKey": "AssetBucket", "ParameterValue": asset_bucket},
        {"ParameterKey": "AssetPrefix", "ParameterValue": asset_prefix},
        {"ParameterKey": "ImageUri", "ParameterValue": image_uri},
        {"ParameterKey": "ResourceNamePrefix", "ParameterValue": resource_prefix},
        {"ParameterKey": "CredentialSource", "ParameterValue": cred_source},
        {"ParameterKey": "WriteToolsEnabled", "ParameterValue": "true" if write_enabled else "false"},
        {"ParameterKey": "WriteToolsAllowlist", "ParameterValue": write_allowlist},
        {"ParameterKey": "DisabledTools", "ParameterValue": env.get("ZSCALER_MCP_DISABLED_TOOLS", "")},
        {"ParameterKey": "DisabledServices", "ParameterValue": env.get("ZSCALER_MCP_DISABLED_SERVICES", "")},
        {"ParameterKey": "EnableToolCallLogging", "ParameterValue": env.get("ZSCALER_MCP_LOG_TOOL_CALLS", "true")},
        # Hash-suffixed Lambda S3 keys. When source changes, key changes,
        # which forces both the AWS::Lambda::Function resource AND the
        # Custom::AgentCoreGateway resource to update — see commentary on
        # upload_lambda_packages() and gateway_provisioner.ensure_target().
        {
            "ParameterKey": "RuntimeProvisionerLambdaKey",
            "ParameterValue": lambda_keys.get(
                "runtime_provisioner.zip",
                f"{asset_prefix}lambda/runtime_provisioner.zip",
            ),
        },
        {
            "ParameterKey": "GatewayProvisionerLambdaKey",
            "ParameterValue": lambda_keys.get(
                "gateway_provisioner.zip",
                f"{asset_prefix}lambda/gateway_provisioner.zip",
            ),
        },
    ]
    for k, v in cred_params.items():
        parameters.append({"ParameterKey": k, "ParameterValue": v})
    for k, v in auth_params.items():
        parameters.append({"ParameterKey": k, "ParameterValue": v})
    for k, v in gw_params.items():
        parameters.append({"ParameterKey": k, "ParameterValue": v})
    for k, v in network_params.items():
        parameters.append({"ParameterKey": k, "ParameterValue": v})

    template_url = f"https://{asset_bucket}.s3.amazonaws.com/{asset_prefix}{ROOT_TEMPLATE}"
    info(f"Uploading root template → {template_url}")
    sess.client("s3").upload_file(
        str(CFN_DIR / ROOT_TEMPLATE), asset_bucket, f"{asset_prefix}{ROOT_TEMPLATE}"
    )

    existing = stack_status(sess, stack_name)
    if existing in NON_UPDATABLE_STATES:
        handle_unrecoverable_state(
            sess, stack_name, existing, non_interactive=args.non_interactive,
        )
        return  # handle_unrecoverable_state always exits

    if existing:
        info(f"Updating existing stack (current state: {existing})")
        try:
            cfn.update_stack(
                StackName=stack_name,
                TemplateURL=template_url,
                Parameters=parameters,
                Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
            )
        except ClientError as e:
            msg = _short_aws_error(e)
            if "No updates are to be performed" in msg:
                ok("No changes to apply — stack already matches the requested state.")
                _print_outputs(sess, stack_name, gateway_enabled)
                return
            err(f"CloudFormation refused the update: {msg}")
            sys.exit(1)
        terminal = ["UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE", "UPDATE_FAILED"]
    else:
        info(f"Creating new stack '{stack_name}'")
        try:
            cfn.create_stack(
                StackName=stack_name,
                TemplateURL=template_url,
                Parameters=parameters,
                Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
                OnFailure="DELETE",
            )
        except ClientError as e:
            err(f"CloudFormation rejected the stack: {_short_aws_error(e)}")
            sys.exit(1)
        terminal = ["CREATE_COMPLETE", "CREATE_FAILED", "ROLLBACK_COMPLETE", "ROLLBACK_FAILED"]

    final, captured_failures = wait_for_stack(sess, stack_name, terminal)
    if final not in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        if final == "STACK_DELETED":
            err(
                "Stack create failed and CloudFormation rolled back by deleting "
                "everything (OnFailure=DELETE)."
            )
        else:
            err(f"Stack ended in non-success state: {final}")
        # Prefer the captured failures; fall back to a fresh fetch if the stack still exists
        reasons = captured_failures or latest_failure_reasons(sess, stack_name)
        if reasons:
            print()
            print("  Why it failed (most recent first):")
            for r in reasons:
                print(r)
        else:
            print()
            warn("Could not retrieve failure reasons — events were already gone.")
        print()
        info(
            "Tail the provisioner Lambda logs for the full picture:\n"
            f"  python aws_mcp_operations.py logs --target all --region {region}"
        )
        sys.exit(1)
    ok(f"Stack '{stack_name}' is {final}")

    # ── Step 12: persist + outputs ──────────────────────────────────────
    save_state({
        "region": region,
        "stack_name": stack_name,
        "resource_prefix": resource_prefix,
        "asset_bucket": asset_bucket,
        "image_uri": image_uri,
        "gateway_enabled": gateway_enabled,
        "gateway_mode": gw_params.get("GatewayMode", "create") if gateway_enabled else "",
        "auth_mode": auth_mode,
        "api_key": auth_params.get("ApiKey", ""),
        "network_mode": network_params["NetworkMode"],
        "vpc_subnets": network_params["VpcSubnetIds"],
        "vpc_security_groups": network_params["VpcSecurityGroupIds"],
    })
    _print_outputs(sess, stack_name, gateway_enabled)


def _print_outputs(sess: boto3.Session, stack_name: str, gateway_enabled: bool) -> None:
    step("Deployment summary")
    outs = stack_outputs(sess, stack_name)
    if not outs:
        warn("No stack outputs available yet.")
        return
    for k in (
        "RuntimeId",
        "RuntimeArn",
        "RuntimeMcpUrl",
        "NetworkMode",
        "GatewayLifecycleMode",
        "GatewayId",
        "GatewayMcpUrl",
        "GatewayTargetId",
        "SecretName",
        "ExecutionRoleArn",
    ):
        if k in outs:
            print(f"  {k:22s} = {outs[k]}")
    print()
    if gateway_enabled and "GatewayMcpUrl" in outs:
        mode = outs.get("GatewayLifecycleMode", "create")
        if mode == "attach":
            info(
                "Gateway MCP endpoint (target registered on your existing Gateway):"
            )
        else:
            info(
                "Gateway MCP endpoint (downstream agent platforms — Amazon Quick "
                "Suite, Bedrock Agents, custom MCP clients — register this URL):"
            )
        print(f"    {outs['GatewayMcpUrl']}")
    if "RuntimeMcpUrl" in outs:
        info(
            "Direct runtime MCP endpoint (callable via bedrock-agentcore "
            "InvokeAgentRuntime or AgentCore Sandbox playground):"
        )
        print(f"    {outs['RuntimeMcpUrl']}")


# ──────────────────────────────────────────────────────────────────────────
# STATUS / LOGS / DESTROY
# ──────────────────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    state = load_state()
    region = args.region or state.get("region") or DEFAULT_REGION
    stack_name = args.stack_name or state.get("stack_name") or DEFAULT_STACK_NAME
    sess = get_session(region)

    status = stack_status(sess, stack_name)
    if not status:
        err(f"Stack '{stack_name}' not found in {region}.")
        sys.exit(1)
    ok(f"Stack '{stack_name}' status: {status}")
    _print_outputs(sess, stack_name, gateway_enabled=state.get("gateway_enabled", False))


def cmd_logs(args: argparse.Namespace) -> None:
    state = load_state()
    region = args.region or state.get("region") or DEFAULT_REGION
    prefix = args.resource_prefix or state.get("resource_prefix") or DEFAULT_RESOURCE_PREFIX
    sess = get_session(region)
    logs = sess.client("logs")

    target = args.target
    log_groups = []
    if target in ("runtime", "all"):
        log_groups.append(f"/aws/lambda/{prefix}-runtime-provisioner")
    if target in ("gateway", "all"):
        log_groups.append(f"/aws/lambda/{prefix}-gateway-provisioner")

    # When tailing "all", silently skip log groups that don't exist (e.g. the
    # gateway-provisioner Lambda when the user opted out of the AgentCore Gateway
    # at deploy time). When the user explicitly asks for a single target, surface
    # the missing-group condition as a clear info line instead of an opaque
    # ResourceNotFoundException stacktrace.
    existing_groups: set[str] = set()
    try:
        paginator = logs.get_paginator("describe_log_groups")
        for page in paginator.paginate(logGroupNamePrefix=f"/aws/lambda/{prefix}-"):
            for grp in page.get("logGroups", []):
                existing_groups.add(grp["logGroupName"])
    except ClientError:
        # Fall back to per-group probing if the describe call itself fails.
        existing_groups = set(log_groups)

    for lg in log_groups:
        if lg not in existing_groups:
            if target == "all":
                continue  # silently skip — not all Lambdas are provisioned in every deployment
            info(f"Log group {lg} does not exist (the corresponding Lambda was not deployed).")
            continue
        info(f"Tailing {lg}")
        try:
            streams = logs.describe_log_streams(
                logGroupName=lg, orderBy="LastEventTime", descending=True, limit=1
            ).get("logStreams", [])
        except ClientError as e:
            warn(f"  cannot describe {lg}: {e}")
            continue
        if not streams:
            warn(f"  no streams in {lg} yet")
            continue
        events = logs.get_log_events(
            logGroupName=lg, logStreamName=streams[0]["logStreamName"], limit=200
        )
        for evt in events.get("events", []):
            print(f"  {evt['message'].rstrip()}")
        print()


def cmd_destroy(args: argparse.Namespace) -> None:
    state = load_state()
    region = args.region or state.get("region") or DEFAULT_REGION
    stack_name = args.stack_name or state.get("stack_name") or DEFAULT_STACK_NAME
    sess = get_session(region)

    if not args.yes:
        confirm = input(
            f"{BOLD}Delete stack {YELLOW}'{stack_name}'{NC}{BOLD} in {region}?{NC} "
            f"{DIM}This removes the AgentCore Runtime, Gateway (if enabled), "
            f"Lambdas, and IAM roles.{NC} {CYAN}[y/N]{NC}: "
        ).strip().lower()
        if confirm not in ("y", "yes"):
            info("Aborted.")
            return

    cfn = sess.client("cloudformation")

    # Short-circuit when the stack is already gone (deleted manually, or
    # the previous destroy run already removed it but left the state file
    # behind). Otherwise delete_stack would raise a ClientError.
    current = stack_status(sess, stack_name)
    if current is None:
        ok(f"Stack '{stack_name}' does not exist — nothing to delete.")
        _remove_state_file()
        return

    info(f"Deleting stack '{stack_name}'")
    cfn.delete_stack(StackName=stack_name)
    final, captured = wait_for_stack(
        sess, stack_name, ["DELETE_COMPLETE", "DELETE_FAILED"],
    )
    if final in ("DELETE_COMPLETE", "STACK_DELETED"):
        ok(f"Stack '{stack_name}' deleted.")
        _remove_state_file()
    else:
        err(f"Stack delete ended in {final}")
        for r in captured:
            print(r)
        warn(
            f"Local state file '{STATE_FILE.name}' preserved so you can "
            "re-run 'destroy' once the failed resources are cleaned up."
        )
        sys.exit(1)


def _remove_state_file() -> None:
    """Delete the local deploy state file so subsequent runs start clean.

    Called from every destroy path that observes the stack as gone — both
    the success case and the "stack already deleted out-of-band" case. The
    failure case (DELETE_FAILED) deliberately preserves the file so a
    follow-up destroy can target the same stack.
    """
    if STATE_FILE.exists():
        try:
            STATE_FILE.unlink()
            info(f"Removed local state file: {STATE_FILE.name}")
        except OSError as e:
            warn(f"Could not remove state file '{STATE_FILE.name}': {e}")


# ──────────────────────────────────────────────────────────────────────────
# EXPORT-TOOL-SCHEMA
# ──────────────────────────────────────────────────────────────────────────

def _decode_mcp_response(raw: str) -> dict:
    """Decode an MCP Streamable HTTP response body.

    The runtime negotiates per-request between plain JSON and SSE framing
    based on the Accept header. SSE bodies look like:

        event: message
        data: {"jsonrpc":"2.0",...}

    Plain JSON bodies are just the object. Handle both.
    """
    text = raw.strip()
    if not text:
        raise RuntimeError("Empty response body from runtime.")
    if text.startswith("{"):
        return json.loads(text)
    last_data = None
    for line in text.splitlines():
        if line.startswith("data:"):
            last_data = line[5:].strip()
    if last_data is None:
        raise RuntimeError(f"Unrecognized response body: {text[:200]!r}")
    return json.loads(last_data)


def cmd_export_tool_schema(args: argparse.Namespace) -> None:
    """Capture the upstream MCP server's tools/list response as a Gateway target schema.

    Used to populate GATEWAY_TOOL_SCHEMA_FILE for SchemaUpfront target
    registration — avoids the interactive admin OAuth consent that
    ImplicitSync triggers during target creation.
    """
    try:
        import urllib.request
    except ImportError:
        err("urllib unavailable — cannot fetch tool schema.")
        sys.exit(1)

    state = load_state()
    region = args.region or state.get("region") or DEFAULT_REGION
    stack_name = args.stack_name or state.get("stack_name") or DEFAULT_STACK_NAME
    sess = get_session(region)
    outs = stack_outputs(sess, stack_name)
    runtime_url = outs.get("RuntimeMcpUrl")
    if not runtime_url:
        err("No RuntimeMcpUrl in stack outputs — deploy the runtime first.")
        sys.exit(1)

    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    ).encode()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }
    if args.bearer:
        headers["Authorization"] = f"Bearer {args.bearer}"
    if args.api_key:
        headers["X-MCP-API-Key"] = args.api_key
    if args.zscaler_id and args.zscaler_secret:
        headers["X-Zscaler-Client-ID"] = args.zscaler_id
        headers["X-Zscaler-Client-Secret"] = args.zscaler_secret

    info(f"Fetching tools/list from {runtime_url}")
    req = urllib.request.Request(runtime_url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
    body = _decode_mcp_response(raw)

    tools = body.get("result", {}).get("tools", [])
    if not tools:
        err(f"tools/list returned 0 tools — got: {body}")
        sys.exit(1)

    out_path = Path(args.output) if args.output else SCRIPT_DIR / "tool-schema.json"
    out_path.write_text(json.dumps(tools, indent=2))
    ok(f"Wrote {len(tools)} tool definitions → {out_path}")
    info(
        "Set GATEWAY_TOOL_SCHEMA_FILE=tool-schema.json in env.properties and re-run "
        "'aws_mcp_operations.py deploy' to wire it into the Gateway target."
    )


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Deploy and manage the Zscaler MCP Server on AWS Bedrock AgentCore. "
            "Pulls the official container image from AWS Marketplace ECR. "
            "Optionally provisions an AgentCore Gateway in front of the runtime."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_deploy = sub.add_parser("deploy", help="Interactive nested-stack deployment")
    p_deploy.add_argument("--env-file", help="Path to env.properties (auto-discovered if omitted)")
    p_deploy.add_argument(
        "--non-interactive",
        action="store_true",
        help="Take all values from env file; fail if anything is missing.",
    )
    p_deploy.set_defaults(func=cmd_deploy)

    p_status = sub.add_parser("status", help="Show stack and component status")
    p_status.add_argument("--region")
    p_status.add_argument("--stack-name")
    p_status.set_defaults(func=cmd_status)

    p_logs = sub.add_parser("logs", help="Tail provisioner Lambda CloudWatch logs")
    p_logs.add_argument("--region")
    p_logs.add_argument("--resource-prefix")
    p_logs.add_argument(
        "--target",
        choices=["runtime", "gateway", "all"],
        default="all",
        help="Which Lambda to tail.",
    )
    p_logs.set_defaults(func=cmd_logs)

    p_destroy = sub.add_parser("destroy", help="Delete the entire stack")
    p_destroy.add_argument("--region")
    p_destroy.add_argument("--stack-name")
    p_destroy.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    p_destroy.set_defaults(func=cmd_destroy)

    p_schema = sub.add_parser(
        "export-tool-schema",
        help="Capture tools/list from the deployed runtime for SchemaUpfront Gateway targets",
    )
    p_schema.add_argument("--region")
    p_schema.add_argument("--stack-name")
    p_schema.add_argument("--output", help="Output JSON path (default: ./tool-schema.json)")
    p_schema.add_argument("--bearer", help="JWT bearer token for the upstream MCP server")
    p_schema.add_argument("--api-key", help="API key for the upstream MCP server")
    p_schema.add_argument("--zscaler-id", help="X-Zscaler-Client-ID header value")
    p_schema.add_argument("--zscaler-secret", help="X-Zscaler-Client-Secret header value")
    p_schema.set_defaults(func=cmd_export_tool_schema)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        info("Interrupted. Stack operations in flight will continue running on AWS — "
             "use `python aws_mcp_operations.py status` to check.")
        sys.exit(130)
    except NoCredentialsError:
        err("No AWS credentials found. Run `aws configure` or export AWS_PROFILE.")
        sys.exit(1)
    except ClientError as e:
        err(_short_aws_error(e))
        sys.exit(1)
    except Exception as e:
        # Last resort. Show the type + message, not the whole traceback.
        # (Set DEBUG=1 to see the traceback.)
        if os.environ.get("DEBUG"):
            raise
        err(f"{type(e).__name__}: {e}")
        info("Re-run with DEBUG=1 for the full traceback.")
        sys.exit(1)
