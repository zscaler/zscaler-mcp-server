#!/usr/bin/env python3
"""Zscaler MCP Server — AWS EKS deployment & lifecycle.

Sibling of ``integrations/aws/ecs-fargate/`` and ``integrations/aws/ec2/``.
This script provisions (or attaches to) an EKS cluster and runs the Zscaler
MCP Server as a single-replica K8s Deployment fronted by an NLB-backed
LoadBalancer Service. CloudFormation provisions the cluster + IRSA Pod
identity role; the script then renders the K8s manifests and applies them
via ``kubectl``.

Topology::

    User / MCP client  ─────►  NLB (public, port 80)
                                    │
                                    ▼
                            K8s Service (LoadBalancer)
                                    │
                                    ▼
                            Deployment: zscaler-mcp-server
                            (Docker image from Docker Hub)
                                    │ HTTPS
                                    ▼
                              Zscaler OneAPI

Commands:
    deploy           Provision cluster (if needed) + render+apply manifests
    status           Show stack + Pod + Service state
    logs             Stream Pod logs via `kubectl logs -f`
    kubectl          Shortcut for `kubectl --context <ctx>` with the right ctx
    rotate-secrets   Re-fetch creds from Secrets Manager and re-apply the K8s Secret
    destroy          Delete manifests then `cloudformation delete-stack`
    configure        (Re)write MCP client configs without touching AWS

Credentials are pulled from AWS Secrets Manager (existing or freshly created)
at deploy + rotate time. The K8s Pod consumes them via `envFrom: secretRef`
on a managed K8s Secret — no Secrets Store CSI driver dependency.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import platform
import re
import secrets
import shutil
import string
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import boto3
    from botocore.exceptions import (
        ClientError,
        EndpointConnectionError,
        NoCredentialsError,
        ProfileNotFound,
    )
except ImportError:
    print(
        "ERROR: boto3 is required.  pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════
#  Branding
# ════════════════════════════════════════════════════════════════════════

_ZSCALER_ART = [
    "███████╗███████╗ ██████╗ █████╗ ██╗     ███████╗██████╗ ",
    "╚══███╔╝██╔════╝██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗",
    "  ███╔╝ ███████╗██║     ███████║██║     █████╗  ██████╔╝",
    " ███╔╝  ╚════██║██║     ██╔══██║██║     ██╔══╝  ██╔══██╗",
    "███████╗███████║╚██████╗██║  ██║███████╗███████╗██║  ██║",
    "╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
]
_TAGLINE = "AWS EKS Deployment"


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


def print_zscaler_logo() -> None:
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        for line in _ZSCALER_ART:
            print(line)
        print(_TAGLINE)
        print()
        return
    reset = "\x1b[0m"
    if _supports_truecolor():
        start = (37, 99, 235)
        end = (147, 197, 253)
        for i, line in enumerate(_ZSCALER_ART):
            t = i / max(1, len(_ZSCALER_ART) - 1)
            r = int(start[0] + (end[0] - start[0]) * t)
            g = int(start[1] + (end[1] - start[1]) * t)
            b = int(start[2] + (end[2] - start[2]) * t)
            print(f"{_rgb(r, g, b)}{line}{reset}")
        print(f"{_rgb(96, 165, 250)}{_TAGLINE}{reset}")
    else:
        for line in _ZSCALER_ART:
            print(f"\x1b[34m{line}{reset}")
        print(f"\x1b[36m{_TAGLINE}{reset}")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Constants & paths
# ════════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).resolve().parent
CFN_DIR = SCRIPT_DIR / "cloudformation"
K8S_DIR = SCRIPT_DIR / "k8s-manifests"
STATE_FILE = SCRIPT_DIR / ".aws-deploy-state.json"
NESTED_TEMPLATES = ["network.yaml", "cluster.yaml", "iam.yaml", "secrets.yaml"]
ROOT_TEMPLATE = "zscaler-mcp-root.yaml"
K8S_MANIFESTS = [
    "00-namespace.yaml",
    "01-service-account.yaml",
    "02-secret.yaml",
    "03-deployment.yaml",
    "04-service.yaml",
]

DEFAULT_REGION = "us-east-1"
DEFAULT_STACK = "zscaler-mcp-eks"
DEFAULT_CLUSTER = "zscaler-mcp-eks"
DEFAULT_PREFIX = "zscaler-mcp"
DEFAULT_NAMESPACE = "zscaler-mcp"
DEFAULT_SA_NAME = "zscaler-mcp-sa"
DEFAULT_NODE_TYPE = "t3.medium"
# 1.33 is the lowest version that does NOT immediately drop into AWS's
# "extended support" tier (and the version AWS's own console recommends in
# the pre-deploy banner). Bump this when AWS publishes a newer standard-
# support default — the catalog of AllowedValues in cluster.yaml limits how
# far ahead this can be set without also updating the template.
DEFAULT_KUBE_VERSION = "1.33"
DEFAULT_IMAGE = "zscaler/zscaler-mcp-server:latest"
DEFAULT_SERVER_NAME = "zscaler-mcp-aws-eks"

SYSTEM = platform.system()


# ════════════════════════════════════════════════════════════════════════
#  Console helpers
# ════════════════════════════════════════════════════════════════════════


def _ansi(code: str, msg: str) -> str:
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return msg
    return f"\x1b[{code}m{msg}\x1b[0m"


def info(msg: str) -> None:
    print(f"{_ansi('36', 'ℹ')} {msg}")


def ok(msg: str) -> None:
    print(f"{_ansi('32', '✓')} {msg}")


def warn(msg: str) -> None:
    print(f"{_ansi('33', '⚠')} {msg}")


def err(msg: str) -> None:
    print(f"{_ansi('31', '✗')} {msg}", file=sys.stderr)


def step(title: str) -> None:
    bar = "─" * 72
    print()
    print(_ansi("1;36", bar))
    print(_ansi("1;36", f"  {title}"))
    print(_ansi("1;36", bar))


def die(msg: str, code: int = 1) -> None:
    err(msg)
    sys.exit(code)


def _color_for_stack_status(status: str) -> str:
    if status.endswith("_COMPLETE"):
        return "32"
    if status.endswith("_IN_PROGRESS"):
        return "36"
    if status.endswith("_FAILED") or "ROLLBACK" in status:
        return "31"
    return "33"


def _fmt_elapsed(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60}m{seconds % 60:02d}s"


# ════════════════════════════════════════════════════════════════════════
#  Env file & state persistence
# ════════════════════════════════════════════════════════════════════════


def _strip_inline_comment(value: str) -> str:
    out: list[str] = []
    in_single = in_double = False
    for ch in value:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out).strip()


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        val = _strip_inline_comment(val)
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        out[key] = val
    return out


def discover_env_file() -> Path | None:
    for candidate in (
        SCRIPT_DIR / ".env",
        SCRIPT_DIR / "env.properties",
        Path.cwd() / ".env",
    ):
        if candidate.exists():
            return candidate
    return None


def resolve_env_file_path(
    cli_env_file: str | None, non_interactive: bool
) -> Path | None:
    """Resolve which .env / env.properties file to load.

    Precedence:
      1. ``--env-file <path>`` on the CLI wins; missing file is fatal.
      2. In interactive mode, the user is prompted, with the auto-discovered
         file (if any) pre-filled as the default. Typing ``none`` skips loading
         any file (everything must then be answered at the prompts).
      3. In ``--non-interactive`` mode, fall back silently to auto-discovery.
    """
    if cli_env_file:
        path = Path(cli_env_file).expanduser().resolve()
        if not path.exists() or not path.is_file():
            die(f"--env-file {path} does not exist.")
        return path

    discovered = discover_env_file()
    if non_interactive:
        return discovered

    default_str = str(discovered) if discovered else "none"
    while True:
        raw = prompt(
            "Path to .env / env.properties (or 'none' to skip)",
            default=default_str,
        )
        if raw.lower() == "none":
            return None
        candidate = Path(raw).expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            return candidate
        print(f"  {candidate} does not exist — try again or type 'none'.")


def save_state(data: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(data, indent=2, sort_keys=True))


def save_partial_state(partial: dict[str, Any], *, phase: str) -> None:
    """Merge ``partial`` onto the current state file, mark it in-progress,
    and persist. Best-effort — never raises.

    Written eagerly throughout ``cmd_deploy`` so a half-failed deploy still
    leaves enough breadcrumbs for ``cmd_destroy`` to clean up the partial
    CFN stack and any K8s objects we may have applied. Without this, a
    Ctrl-C or a nested-stack failure during the long ``wait_for_stack``
    poll would orphan the stack — the user would have no state file and
    ``destroy`` would refuse to run.
    """
    try:
        current = load_state()
        current.update(partial)
        current["phase"] = phase
        current["state_partial"] = True
        save_state(current)
    except OSError as e:
        warn(f"Could not persist partial state ({phase}): {e}")


def finalize_state(data: dict[str, Any]) -> None:
    """Stamp the state file as the result of a successful deploy."""
    data["state_partial"] = False
    data["deploy_completed_at"] = datetime.now(timezone.utc).isoformat()
    save_state(data)


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        warn(f"State file {STATE_FILE} is corrupt; ignoring.")
        return {}


def _apply_state_for_redeploy(state: dict[str, Any], env: dict[str, str]) -> None:
    """Pre-populate ``env`` from saved state so a re-deploy is friction-free.

    Mirrors the ECS-Fargate / EC2 behaviour with EKS-specific additions:
    ``cluster_mode``, ``cluster_name``, and the K8s namespace are also
    treated as locked dimensions (CFN can't swap clusters between deploys
    without a destroy; the namespace is part of the manifest contract).
    See the matching helper in ``ecs_fargate_mcp_operations.py`` for the
    full rationale on the three categories of values (locked / forced
    UseExisting / soft defaults).
    """
    # Locked dimensions — CFN can't change these between deploys
    if state.get("region"):
        env["AWS_REGION"] = state["region"]
    if state.get("stack_name"):
        env["AWS_STACK_NAME"] = state["stack_name"]
    if state.get("prefix"):
        env["AWS_RESOURCE_NAME_PREFIX"] = state["prefix"]
    if state.get("cluster_mode"):
        env["AWS_CLUSTER_MODE"] = state["cluster_mode"]
    if state.get("cluster_name"):
        env["AWS_CLUSTER_NAME"] = state["cluster_name"]
    if state.get("namespace"):
        env["AWS_K8S_NAMESPACE"] = state["namespace"]
    if state.get("network_mode"):
        env["AWS_NETWORK_MODE"] = state["network_mode"]

    # Forced UseExisting for credentials
    if state.get("secret_arn"):
        env["ZSCALER_SECRET_NAME"] = state["secret_arn"]

    # Soft defaults — .env can still override
    if state.get("tls_mode"):
        env.setdefault("AWS_TLS_MODE", state["tls_mode"])
    if state.get("auth_mode"):
        env.setdefault("ZSCALER_MCP_AUTH_MODE", state["auth_mode"])
    if state.get("image"):
        env.setdefault("ZSCALER_MCP_IMAGE_URI", state["image"])
    if state.get("server_name"):
        env.setdefault("MCP_SERVER_NAME", state["server_name"])


def _dump_recent_pod_logs(
    namespace: str,
    *,
    deployment: str = "zscaler-mcp-server",
    lines: int = 80,
    context: str | None = None,
) -> None:
    """Surface Pod stdout/stderr inline on EKS deploy failure.

    When a Pod CrashLoopBackoffs (bad image arch, missing env var, application
    crash), CFN itself just reports "kubectl apply failed" or "Pod not ready
    after N seconds" — neither of which contains the actual Python stack
    trace. Running ``kubectl logs deployment/zscaler-mcp-server -n <ns>``
    inline saves the operator a manual context-switch and an `eks update-
    kubeconfig` invocation.

    Best-effort: silent no-op if kubectl isn't on PATH or the deployment
    doesn't exist yet (cluster came up but workload manifest never applied).
    """
    import shutil
    import subprocess

    if not shutil.which("kubectl"):
        info(
            "kubectl not on PATH — skipping inline Pod log dump. "
            "Install kubectl, then run "
            f"`python {Path(__file__).name} logs --tail {lines}`."
        )
        return

    cmd = ["kubectl", "logs", f"deployment/{deployment}", "-n", namespace, f"--tail={lines}"]
    if context:
        cmd[1:1] = ["--context", context]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15, check=False
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        warn(f"Could not fetch Pod logs ({exc}). Run `kubectl logs ...` manually.")
        return

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if "not found" in stderr.lower() or "no such" in stderr.lower():
            info(
                f"Deployment {deployment} not found in namespace {namespace} — "
                "the workload manifest may not have been applied (cluster "
                "came up but K8s apply step never ran). Check the script's "
                "step output above for the failure point."
            )
        else:
            warn(f"kubectl logs failed: {stderr or 'no stderr'}")
        return

    output = result.stdout.rstrip()
    if not output:
        info(f"No log lines from deployment {deployment} yet.")
        return

    print()
    info(f"Last {lines} lines from deployment/{deployment} (ns={namespace}):")
    print("  " + "─" * 72)
    for line in output.splitlines():
        print(f"  {line}")
    print("  " + "─" * 72)


# ════════════════════════════════════════════════════════════════════════
#  Prompts
# ════════════════════════════════════════════════════════════════════════


def prompt(
    label: str,
    default: str | None = None,
    *,
    secret: bool = False,
    allow_empty: bool = False,
) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        if secret:
            val = getpass.getpass(f"{label}{suffix}: ").strip()
        else:
            val = input(f"{label}{suffix}: ").strip()
        if not val and default is not None:
            return default
        if val:
            return val
        if allow_empty:
            return ""
        print("  (required)")


def prompt_choice(label: str, choices: list[str], default: str) -> str:
    """Render `choices` as a numbered menu and accept a 1-based number.

    Matches the convention used in ``aws_mcp_operations.py`` (Bedrock
    AgentCore) — render the menu inline, prompt for ``Pick 1-N [default]:``,
    fall back to the default on empty input, warn + use default on garbage.
    """
    print()
    print(_ansi("1;36", label))
    for i, c in enumerate(choices, 1):
        marker = _ansi("2", " (default)") if c == default else ""
        print(f"  {_ansi('36', f'[{i}]')} {c}{marker}")
    default_idx = choices.index(default) + 1 if default in choices else 1
    raw = input(
        f"Pick {_ansi('36', f'1-{len(choices)}')}"
        f" {_ansi('2', f'[{default_idx}]')}: "
    ).strip()
    if not raw:
        return default
    try:
        return choices[int(raw) - 1]
    except (ValueError, IndexError):
        warn(f"Invalid choice; using default '{default}'")
        return default


def prompt_bool(label: str, default: bool) -> bool:
    dflt = "y" if default else "n"
    while True:
        raw = input(f"{label} (y/n) [{dflt}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes", "true", "1"):
            return True
        if raw in ("n", "no", "false", "0"):
            return False


def prompt_int(label: str, default: int, *, lo: int = 1, hi: int = 9999) -> int:
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            v = int(raw)
        except ValueError:
            print("  must be an integer")
            continue
        if lo <= v <= hi:
            return v
        print(f"  must be between {lo} and {hi}")


# ════════════════════════════════════════════════════════════════════════
#  AWS session, asset bucket, nested-template upload
# ════════════════════════════════════════════════════════════════════════


def get_session(region: str, profile: str | None = None) -> boto3.Session:
    try:
        sess = boto3.Session(region_name=region, profile_name=profile)
        sts = sess.client("sts")
        ident = sts.get_caller_identity()
        ok(f"AWS credentials valid — account {ident['Account']} as {ident['Arn']}")
        return sess
    except (NoCredentialsError, ProfileNotFound) as e:
        die(f"No AWS credentials: {e}. Run `aws configure` or export AWS_PROFILE.")
    except EndpointConnectionError as e:
        die(f"Cannot reach AWS endpoint in {region}: {e}")
    except ClientError as e:
        die(f"AWS credential check failed: {e}")


def ensure_asset_bucket(sess: boto3.Session, bucket_name: str) -> None:
    s3 = sess.client("s3")
    region = sess.region_name or DEFAULT_REGION
    try:
        s3.head_bucket(Bucket=bucket_name)
        ok(f"Asset bucket exists: s3://{bucket_name}")
        return
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
            die(f"Cannot access asset bucket {bucket_name}: {e}")

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


def upload_nested_templates(sess: boto3.Session, bucket: str, prefix: str) -> str:
    s3 = sess.client("s3")
    if not prefix.endswith("/"):
        prefix += "/"
    info(f"Uploading nested templates to s3://{bucket}/{prefix}")
    for tpl in NESTED_TEMPLATES:
        path = CFN_DIR / tpl
        if not path.exists():
            die(f"Missing nested template: {path}")
        s3.upload_file(str(path), bucket, f"{prefix}{tpl}")
        ok(f"  uploaded {tpl}")
    return prefix


# ════════════════════════════════════════════════════════════════════════
#  VPC / subnet / hosted-zone interactive pickers
# ════════════════════════════════════════════════════════════════════════


def list_vpcs(sess: boto3.Session) -> list[dict]:
    ec2 = sess.client("ec2")
    vpcs = ec2.describe_vpcs()["Vpcs"]
    out = []
    for v in vpcs:
        name = next(
            (t["Value"] for t in v.get("Tags", []) if t["Key"] == "Name"),
            "",
        )
        out.append(
            {
                "id": v["VpcId"],
                "cidr": v.get("CidrBlock", ""),
                "name": name,
                "default": v.get("IsDefault", False),
            }
        )
    return out


def list_subnets_for_vpc(sess: boto3.Session, vpc_id: str) -> list[dict]:
    ec2 = sess.client("ec2")
    subs = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
        "Subnets"
    ]
    rts = ec2.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
        "RouteTables"
    ]
    main_rt_id = next(
        (
            rt["RouteTableId"]
            for rt in rts
            if any(a.get("Main") for a in rt.get("Associations", []))
        ),
        None,
    )

    def is_public(subnet_id: str) -> bool:
        for rt in rts:
            explicit = any(
                a.get("SubnetId") == subnet_id for a in rt.get("Associations", [])
            )
            if explicit or rt["RouteTableId"] == main_rt_id:
                for r in rt.get("Routes", []):
                    if (
                        r.get("DestinationCidrBlock") == "0.0.0.0/0"
                        and r.get("GatewayId", "").startswith("igw-")
                    ):
                        return True
        return False

    out = []
    for s in subs:
        name = next(
            (t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"),
            "",
        )
        out.append(
            {
                "id": s["SubnetId"],
                "cidr": s["CidrBlock"],
                "az": s["AvailabilityZone"],
                "name": name,
                "public": is_public(s["SubnetId"]),
            }
        )
    out.sort(key=lambda s: (not s["public"], s["az"], s["id"]))
    return out


def pick_subnets(
    subnets: list[dict], kind: str, *, want_public: bool, min_count: int = 2
) -> list[str]:
    """Render and pick subnet IDs interactively. `kind` is 'public' or 'private'."""
    candidates = [s for s in subnets if s["public"] == want_public]
    if not candidates:
        die(
            f"No {kind} subnets found in this VPC. Provision them first or pick"
            f" NetworkMode=CreateNew."
        )
    print(f"\n  {kind.upper()} subnets in this VPC:")
    for i, s in enumerate(candidates, 1):
        flag = "🌐" if s["public"] else "🔒"
        print(
            f"    {i:>2}. {s['id']:<24} {s['az']:<14} {s['cidr']:<20}"
            f" {flag} {s['name']}"
        )

    while True:
        raw = input(
            f"  Pick {kind} subnet numbers (comma-separated, >= {min_count}): "
        ).strip()
        if not raw:
            continue
        try:
            picks = [int(p) for p in raw.replace(" ", "").split(",") if p]
        except ValueError:
            print("  invalid input — use comma-separated numbers")
            continue
        if len(picks) < min_count:
            print(f"  pick at least {min_count} subnets")
            continue
        if any(p < 1 or p > len(candidates) for p in picks):
            print(f"  numbers must be 1..{len(candidates)}")
            continue
        chosen = [candidates[p - 1]["id"] for p in picks]
        azs = {candidates[p - 1]["az"] for p in picks}
        if len(azs) < 2:
            warn(
                f"  All {kind} subnets are in the same AZ ({azs.pop()}). "
                "AWS recommends >= 2 AZs for HA."
            )
            if not prompt_bool("  Proceed anyway?", default=False):
                continue
        return chosen


def list_hosted_zones(sess: boto3.Session) -> list[dict]:
    r53 = sess.client("route53")
    paginator = r53.get_paginator("list_hosted_zones")
    out = []
    for page in paginator.paginate():
        for hz in page["HostedZones"]:
            out.append(
                {
                    "id": hz["Id"].split("/")[-1],
                    "name": hz["Name"].rstrip("."),
                    "private": hz.get("Config", {}).get("PrivateZone", False),
                }
            )
    return out


def list_acm_certs(sess: boto3.Session) -> list[dict]:
    acm = sess.client("acm")
    paginator = acm.get_paginator("list_certificates")
    out = []
    for page in paginator.paginate(CertificateStatuses=["ISSUED"]):
        for c in page["CertificateSummaryList"]:
            out.append(
                {
                    "arn": c["CertificateArn"],
                    "domain": c.get("DomainName", ""),
                }
            )
    return out


# ════════════════════════════════════════════════════════════════════════
#  Stack lifecycle helpers
# ════════════════════════════════════════════════════════════════════════


def stack_status(sess: boto3.Session, stack_name: str) -> str | None:
    cfn = sess.client("cloudformation")
    try:
        r = cfn.describe_stacks(StackName=stack_name)
        return r["Stacks"][0]["StackStatus"]
    except ClientError as e:
        if "does not exist" in str(e):
            return None
        raise


def stack_outputs(sess: boto3.Session, stack_name: str) -> dict[str, str]:
    cfn = sess.client("cloudformation")
    try:
        r = cfn.describe_stacks(StackName=stack_name)
    except ClientError:
        return {}
    out: dict[str, str] = {}
    for o in r["Stacks"][0].get("Outputs", []):
        out[o["OutputKey"]] = o["OutputValue"]
    return out


def latest_failure_reasons(
    sess: boto3.Session, stack_name: str, *, limit: int = 10
) -> list[tuple[str, str, str]]:
    cfn = sess.client("cloudformation")
    out: list[tuple[str, str, str]] = []
    try:
        paginator = cfn.get_paginator("describe_stack_events")
        for page in paginator.paginate(StackName=stack_name):
            for ev in page["StackEvents"]:
                status = ev.get("ResourceStatus", "")
                if "FAILED" in status or status == "ROLLBACK_IN_PROGRESS":
                    out.append(
                        (
                            ev["LogicalResourceId"],
                            status,
                            ev.get("ResourceStatusReason", ""),
                        )
                    )
                if len(out) >= limit:
                    return out
    except ClientError:
        pass
    return out


_ROLLBACK_STATES = (
    "ROLLBACK_IN_PROGRESS",
    "ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_IN_PROGRESS",
    "UPDATE_ROLLBACK_COMPLETE",
    "DELETE_IN_PROGRESS",
)


def wait_for_stack(
    sess: boto3.Session,
    stack_name: str,
    *,
    operation: str,
    timeout_min: int = 30,
) -> str:
    """Poll the stack with a spinner until it reaches a terminal state.

    Defensive against the ``OnFailure=DELETE`` failure mode where CFN deletes
    the failed stack the moment any nested resource fails. We snapshot the
    failure reasons the first time a rollback/delete state is observed so
    they remain available after the stack disappears.
    """
    cfn = sess.client("cloudformation")
    deadline = time.monotonic() + timeout_min * 60
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    start = time.monotonic()
    last_status = ""
    captured_failures: list[tuple[str, str, str]] = []
    info(f"Waiting for stack {stack_name} to {operation}...")
    while time.monotonic() < deadline:
        try:
            r = cfn.describe_stacks(StackName=stack_name)
            status = r["Stacks"][0]["StackStatus"]
        except ClientError as e:
            if "does not exist" in str(e):
                sys.stdout.write("\r" + " " * 80 + "\r")
                sys.stdout.flush()
                if operation == "delete":
                    ok(f"Stack {stack_name} deleted ({_fmt_elapsed(time.monotonic() - start)})")
                    return "DELETE_COMPLETE"
                err(
                    f"Stack {stack_name} no longer exists "
                    f"({_fmt_elapsed(time.monotonic() - start)} elapsed)."
                )
                if captured_failures:
                    err("Failure reasons captured before deletion:")
                    for lid, st, reason in captured_failures:
                        print(f"    {_ansi('31', st)} {lid}: {reason}")
                else:
                    info(
                        "No failure events were captured before the stack "
                        "disappeared. Switch to OnFailure=DO_NOTHING to "
                        "preserve failed stacks for inspection."
                    )
                return "STACK_DELETED"
            raise

        if status != last_status:
            sys.stdout.write("\r" + " " * 80 + "\r")
            color = _color_for_stack_status(status)
            info(f"  {_ansi(color, status)}  (elapsed: {_fmt_elapsed(time.monotonic() - start)})")
            last_status = status

        if (
            operation in ("create", "update")
            and status in _ROLLBACK_STATES
            and not captured_failures
        ):
            try:
                captured_failures = list(latest_failure_reasons(sess, stack_name))
            except ClientError:
                pass

        if status in ("CREATE_COMPLETE", "UPDATE_COMPLETE", "DELETE_COMPLETE"):
            ok(f"Stack {operation} complete ({_fmt_elapsed(time.monotonic() - start)})")
            return status
        if status.endswith("_FAILED") or "ROLLBACK_COMPLETE" in status:
            err(f"Stack {stack_name} reached {status}")
            reasons = captured_failures or list(latest_failure_reasons(sess, stack_name))
            for lid, st, reason in reasons:
                print(f"    {_ansi('31', st)} {lid}: {reason}")
            return status

        sys.stdout.write(
            f"\r  {spinner[i % len(spinner)]} {status}"
            f"  (elapsed: {_fmt_elapsed(time.monotonic() - start)})"
        )
        sys.stdout.flush()
        i += 1
        time.sleep(3)

    err(f"Timed out after {timeout_min}m waiting for {stack_name}")
    return last_status or "TIMEOUT"


_ECR_URI_RE = re.compile(
    r"^(?P<account>\d+)\.dkr\.ecr\.(?P<region>[a-z0-9-]+)\.amazonaws\.com/"
    r"(?P<repo>[^:]+):(?P<tag>.+)$"
)


def _check_image_compatibility(
    sess: boto3.Session,
    image_uri: str,
    *,
    non_interactive: bool = False,
) -> None:
    """Pre-flight: catch CPU architecture mismatches before deploying.

    EKS managed node groups default to the ``AL2_x86_64`` AMI family unless
    the operator explicitly picks Graviton. Pushing a single-arch ``arm64``
    image (the default ``docker build`` output on an M-series Mac) results
    in ``exec /usr/local/bin/python: exec format error`` and the pod
    crashlooping. This pre-flight inspects ECR-hosted images via the ECR
    API (no docker pull required) and warns before we spend ~15 minutes
    waiting for the cluster + workload to come up.

    Marketplace constraint: we do NOT pin a CPU architecture in the K8s
    Deployment spec. The right fix is always "publish a multi-arch image".
    The official ``zscaler/zscaler-mcp-server:latest`` is already multi-arch.

    Scope: only ECR images are inspected. Public Docker Hub / ECR Public
    images are skipped silently (the official one is multi-arch by design).
    """
    m = _ECR_URI_RE.match(image_uri.strip())
    if not m:
        return

    account = m.group("account")
    region = m.group("region")
    repo = m.group("repo")
    tag = m.group("tag")

    try:
        ecr = sess.client("ecr", region_name=region)
        resp = ecr.batch_get_image(
            registryId=account,
            repositoryName=repo,
            imageIds=[{"imageTag": tag}],
            acceptedMediaTypes=[
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.oci.image.index.v1+json",
            ],
        )
    except ClientError as exc:
        warn(
            f"Skipping image-arch pre-flight ({exc.response.get('Error', {}).get('Code', '')}). "
            "Ensure your image was built with `docker buildx build --platform linux/amd64`."
        )
        return

    images = resp.get("images", [])
    if not images:
        warn(f"Image {image_uri} not found in ECR — push it first.")
        return

    manifest_str = images[0].get("imageManifest", "")
    try:
        manifest = json.loads(manifest_str)
    except json.JSONDecodeError:
        return

    media_type = manifest.get("mediaType", "") or images[0].get("imageManifestMediaType", "")

    if "manifest.list" in media_type or "image.index" in media_type or "manifests" in manifest:
        arches = sorted(
            {
                m.get("platform", {}).get("architecture", "")
                for m in manifest.get("manifests", [])
            }
            - {""}
        )
        if "amd64" in arches:
            info(f"  Image {image_uri} is multi-arch ({', '.join(arches)}).")
            return
        warn(
            f"Image {image_uri} is multi-arch ({', '.join(arches) or '?'}) "
            "but does NOT include amd64. Most EKS managed node groups default "
            "to x86_64 nodes."
        )
        if not non_interactive and not prompt_bool("Continue anyway?", default=False):
            die("Aborted by user.")
        return

    config_digest = manifest.get("config", {}).get("digest")
    if not config_digest:
        return
    try:
        url_resp = ecr.get_download_url_for_layer(
            registryId=account,
            repositoryName=repo,
            layerDigest=config_digest,
        )
        import urllib.request

        with urllib.request.urlopen(url_resp["downloadUrl"], timeout=10) as r:
            config = json.loads(r.read())
        arch = config.get("architecture", "")
    except Exception:  # noqa: BLE001
        return

    if not arch or arch == "amd64":
        if arch == "amd64":
            info(f"  Image {image_uri} is single-arch amd64 — compatible with x86_64 nodes.")
        return

    err(
        f"Image {image_uri} is single-arch {arch}-only.\n"
        "  EKS managed node groups default to LINUX/X86_64. Running an "
        f"{arch} image on x86 nodes produces:\n"
        "      exec /usr/local/bin/python: exec format error\n"
        "  and the pod CrashLoopBackoffs.\n\n"
        "  Fixes (pick one):\n"
        "    1. Use the public multi-arch image (recommended):\n"
        "         unset ZSCALER_MCP_IMAGE_URI in .env\n"
        "    2. Rebuild multi-arch from your Mac:\n"
        f'         docker buildx build --platform linux/amd64,linux/arm64 -t {image_uri} --push .\n'
        "    3. Rebuild as amd64-only:\n"
        f'         docker buildx build --platform linux/amd64 -t {image_uri} --push .\n'
    )
    if not non_interactive and not prompt_bool("Continue anyway?", default=False):
        die("Aborted by user — fix the image and re-run.")


# ════════════════════════════════════════════════════════════════════════
#  MCP client config writers (7 clients — same set as setup-mcp-server.py)
# ════════════════════════════════════════════════════════════════════════


def cmd_exists(cmd: str) -> bool:
    from shutil import which

    return which(cmd) is not None


def _claude_desktop_path() -> Path:
    if SYSTEM == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _claude_code_path() -> Path:
    return Path.home() / ".claude.json"


def _cursor_path() -> Path:
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return (
            Path(appdata)
            / "Cursor"
            / "User"
            / "globalStorage"
            / "cursor.mcp"
            / "mcp.json"
        )
    return Path.home() / ".cursor" / "mcp.json"


def _gemini_cli_path() -> Path:
    return Path.home() / ".gemini" / "settings.json"


def _vscode_path() -> Path:
    if SYSTEM == "Darwin":
        return (
            Path.home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
        )
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Code" / "User" / "mcp.json"
    return Path.home() / ".config" / "Code" / "User" / "mcp.json"


def _windsurf_path() -> Path:
    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def _copilot_cli_path() -> Path:
    if SYSTEM == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "github-copilot"
            / "mcp.json"
        )
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "github-copilot" / "mcp.json"
    return Path.home() / ".config" / "github-copilot" / "mcp.json"


def _build_mcp_remote_args(url: str, headers: dict[str, str]) -> list[str]:
    args = ["-y", "mcp-remote", url]
    # mcp-remote refuses non-HTTPS URLs by default to keep bearer tokens off
    # the wire in cleartext — sensible default, wrong default for the EKS
    # *preview* deployment which fronts the cluster with a Network Load
    # Balancer on plain HTTP (TLS is a follow-up item, see README "Enterprise
    # Hardening" section). Inject --allow-http for any non-localhost http://
    # URL so Claude Desktop / Claude Code / Windsurf don't choke with
    # `Error: Non-HTTPS URLs are only allowed for localhost or when
    # --allow-http flag is provided`. Localhost is already exempted by
    # mcp-remote itself, so we don't double-flag it.
    url_lower = url.lower()
    is_plain_http = url_lower.startswith("http://")
    is_localhost = "localhost" in url_lower or "127.0.0.1" in url_lower
    if is_plain_http and not is_localhost:
        args.append("--allow-http")
    for k, v in headers.items():
        args.extend(["--header", f"{k}: {v}"])
    return args


def _http_command_entry(url: str, headers: dict[str, str]) -> dict:
    """For agents that spawn mcp-remote via npx (Claude Desktop, Claude Code, Windsurf)."""
    if SYSTEM == "Windows":
        return {"command": "cmd", "args": ["/c", "npx", *_build_mcp_remote_args(url, headers)]}
    return {"command": "npx", "args": _build_mcp_remote_args(url, headers)}


def _http_url_entry(url: str, headers: dict[str, str]) -> dict:
    return {"url": url, "headers": dict(headers) if headers else {}}


def _read_json_or_default(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        warn(f"  {path} is not valid JSON; will overwrite the mcpServers entry only.")
        return {}


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    tmp.replace(path)


def _write_claude_desktop(server_name: str, url: str, headers: dict[str, str]) -> Path:
    p = _claude_desktop_path()
    cfg = _read_json_or_default(p)
    cfg.setdefault("mcpServers", {})
    cfg["mcpServers"][server_name] = _http_command_entry(url, headers)
    _atomic_write_json(p, cfg)
    return p


def _write_claude_code(server_name: str, url: str, headers: dict[str, str]) -> Path:
    p = _claude_code_path()
    cfg = _read_json_or_default(p)
    cfg.setdefault("mcpServers", {})
    cfg["mcpServers"][server_name] = _http_command_entry(url, headers)
    _atomic_write_json(p, cfg)
    return p


def _write_cursor(server_name: str, url: str, headers: dict[str, str]) -> Path:
    p = _cursor_path()
    cfg = _read_json_or_default(p)
    cfg.setdefault("mcpServers", {})
    cfg["mcpServers"][server_name] = _http_url_entry(url, headers)
    _atomic_write_json(p, cfg)
    return p


def _write_gemini_cli(server_name: str, url: str, headers: dict[str, str]) -> Path:
    p = _gemini_cli_path()
    cfg = _read_json_or_default(p)
    cfg.setdefault("mcpServers", {})
    entry: dict = {"url": url}
    if headers:
        entry["httpHeaders"] = dict(headers)
    cfg["mcpServers"][server_name] = entry
    _atomic_write_json(p, cfg)
    return p


def _write_vscode(server_name: str, url: str, headers: dict[str, str]) -> Path:
    p = _vscode_path()
    cfg = _read_json_or_default(p)
    cfg.setdefault("servers", {})
    entry: dict = {"type": "http", "url": url}
    if headers:
        entry["headers"] = dict(headers)
    cfg["servers"][server_name] = entry
    _atomic_write_json(p, cfg)
    return p


def _write_windsurf(server_name: str, url: str, headers: dict[str, str]) -> Path:
    p = _windsurf_path()
    cfg = _read_json_or_default(p)
    cfg.setdefault("mcpServers", {})
    cfg["mcpServers"][server_name] = _http_command_entry(url, headers)
    _atomic_write_json(p, cfg)
    return p


def _write_copilot_cli(server_name: str, url: str, headers: dict[str, str]) -> Path:
    p = _copilot_cli_path()
    cfg = _read_json_or_default(p)
    cfg.setdefault("mcpServers", {})
    cfg["mcpServers"][server_name] = _http_url_entry(url, headers)
    _atomic_write_json(p, cfg)
    return p


def _claude_desktop_installed() -> bool:
    if SYSTEM == "Darwin":
        return (
            Path("/Applications/Claude.app").exists() or _claude_desktop_path().exists()
        )
    if SYSTEM == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        if local and (Path(local) / "AnthropicClaude").exists():
            return True
        return _claude_desktop_path().exists()
    return _claude_desktop_path().exists()


def _claude_code_installed() -> bool:
    return cmd_exists("claude") or _claude_code_path().exists()


def _cursor_installed() -> bool:
    if SYSTEM == "Darwin" and Path("/Applications/Cursor.app").exists():
        return True
    return cmd_exists("cursor") or _cursor_path().exists()


def _gemini_cli_installed() -> bool:
    return cmd_exists("gemini") or _gemini_cli_path().exists()


def _vscode_installed() -> bool:
    if SYSTEM == "Darwin" and Path("/Applications/Visual Studio Code.app").exists():
        return True
    return cmd_exists("code") or _vscode_path().exists()


def _windsurf_installed() -> bool:
    if SYSTEM == "Darwin" and Path("/Applications/Windsurf.app").exists():
        return True
    return cmd_exists("windsurf") or _windsurf_path().exists()


def _copilot_cli_installed() -> bool:
    return cmd_exists("gh") and (cmd_exists("copilot") or _copilot_cli_path().exists())


AGENTS: list[dict] = [
    {"id": "claude_desktop", "name": "Claude Desktop", "path_fn": _claude_desktop_path, "installed_fn": _claude_desktop_installed, "writer": _write_claude_desktop},
    {"id": "claude_code",    "name": "Claude Code (CLI)", "path_fn": _claude_code_path, "installed_fn": _claude_code_installed, "writer": _write_claude_code},
    {"id": "cursor",         "name": "Cursor",          "path_fn": _cursor_path,         "installed_fn": _cursor_installed,         "writer": _write_cursor},
    {"id": "gemini_cli",     "name": "Gemini CLI",      "path_fn": _gemini_cli_path,     "installed_fn": _gemini_cli_installed,     "writer": _write_gemini_cli},
    {"id": "vscode",         "name": "VS Code (MCP)",   "path_fn": _vscode_path,         "installed_fn": _vscode_installed,         "writer": _write_vscode},
    {"id": "windsurf",       "name": "Windsurf",        "path_fn": _windsurf_path,       "installed_fn": _windsurf_installed,       "writer": _write_windsurf},
    {"id": "copilot_cli",    "name": "GitHub Copilot CLI", "path_fn": _copilot_cli_path, "installed_fn": _copilot_cli_installed,    "writer": _write_copilot_cli},
]


def _build_auth_headers(
    auth_mode: str,
    *,
    zscaler_client_id: str,
    zscaler_client_secret: str,
    api_key: str,
) -> dict[str, str]:
    """Compute the HTTP header(s) an MCP client must send to authenticate."""
    if auth_mode == "zscaler" and zscaler_client_id and zscaler_client_secret:
        token = base64.b64encode(
            f"{zscaler_client_id}:{zscaler_client_secret}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}"}
    if auth_mode == "api-key" and api_key:
        return {"X-Api-Key": api_key}
    return {}


def configure_clients(
    server_name: str,
    url: str,
    headers: dict[str, str],
    selected_ids: list[str],
) -> dict[str, str]:
    """Write MCP client configs for the selected agent IDs. Returns id→path."""
    written: dict[str, str] = {}
    for agent in AGENTS:
        if agent["id"] not in selected_ids:
            continue
        try:
            p = agent["writer"](server_name, url, headers)
            ok(f"  Configured {agent['name']:<22} → {p}")
            written[agent["id"]] = str(p)
        except Exception as e:  # noqa: BLE001 — surface anything unexpected
            warn(f"  Failed to configure {agent['name']}: {e}")
    return written


# ════════════════════════════════════════════════════════════════════════
#  Credential / network / TLS / auth resolution (interactive)
# ════════════════════════════════════════════════════════════════════════


def resolve_credentials(
    sess: boto3.Session, env: dict[str, str], non_interactive: bool
) -> dict[str, str]:
    """Decide whether to point at an existing SM secret or create a new one.

    On the UseExisting path we resolve the secret ARN via DescribeSecret so the
    EC2 instance-role policy can be scoped to that exact ARN — never wildcarded.
    """
    existing = env.get("ZSCALER_SECRET_NAME", "").strip()
    use_existing = bool(existing)
    if not non_interactive:
        info(
            "Credential storage — pick ONE:\n"
            "  1) Reuse an EXISTING AWS Secrets Manager secret you've already populated\n"
            "  2) CREATE a new secret from the Zscaler creds in your .env"
        )
        mode = prompt_choice(
            "Source", ["existing", "create"], default="existing" if existing else "create"
        )
        use_existing = mode == "existing"
        if use_existing:
            existing = prompt(
                "Existing Secrets Manager secret name (e.g. zscaler/mcp/credentials)",
                default=existing or None,
            )

    if use_existing:
        existing_arn = env.get("ZSCALER_SECRET_ARN", "").strip()
        if not existing_arn:
            info(f"Looking up ARN for secret '{existing}'...")
            try:
                sm = sess.client("secretsmanager")
                existing_arn = sm.describe_secret(SecretId=existing)["ARN"]
                ok(f"  Secret ARN: {existing_arn}")
            except ClientError as e:
                die(
                    f"Could not describe secret '{existing}': {e}. "
                    "Verify the name is correct and your caller can secretsmanager:DescribeSecret."
                )
        return {
            "CredentialSource": "UseExisting",
            "ExistingSecretName": existing,
            "ExistingSecretArn": existing_arn,
        }

    # CreateNew path. Values already in the .env are consumed silently — we
    # NEVER re-display secrets in the prompt brackets. Only the missing
    # fields trigger a prompt.
    placeholders = ("", "NOT_SET", "REPLACE_ME")
    client_id = env.get("ZSCALER_CLIENT_ID", "")
    client_secret = env.get("ZSCALER_CLIENT_SECRET", "")
    vanity = env.get("ZSCALER_VANITY_DOMAIN", "")
    customer = env.get("ZSCALER_CUSTOMER_ID", "")
    cloud = env.get("ZSCALER_CLOUD", "production")
    loaded_from_env = [
        name
        for name, value in (
            ("ZSCALER_CLIENT_ID", client_id),
            ("ZSCALER_CLIENT_SECRET", client_secret),
            ("ZSCALER_VANITY_DOMAIN", vanity),
            ("ZSCALER_CUSTOMER_ID", customer),
        )
        if value not in placeholders
    ]
    if loaded_from_env and not non_interactive:
        ok(f"Using {', '.join(loaded_from_env)} from env file (values redacted).")

    if not non_interactive:
        if client_id in placeholders:
            client_id = prompt("ZSCALER_CLIENT_ID")
        if client_secret in placeholders:
            client_secret = prompt("ZSCALER_CLIENT_SECRET", secret=True)
        if vanity in placeholders:
            vanity = prompt("ZSCALER_VANITY_DOMAIN")
        if customer in placeholders:
            customer = prompt("ZSCALER_CUSTOMER_ID")
        if cloud in ("",):
            cloud = prompt("ZSCALER_CLOUD", default="production")

    for label, value in [
        ("ZSCALER_CLIENT_ID", client_id),
        ("ZSCALER_CLIENT_SECRET", client_secret),
        ("ZSCALER_VANITY_DOMAIN", vanity),
        ("ZSCALER_CUSTOMER_ID", customer),
    ]:
        if value in placeholders:
            die(f"{label} is required to create a new Secrets Manager secret.")

    return {
        "CredentialSource": "CreateNew",
        "ExistingSecretName": "",
        "ExistingSecretArn": "",
        "ZscalerClientId": client_id,
        "ZscalerClientSecret": client_secret,
        "ZscalerVanityDomain": vanity,
        "ZscalerCustomerId": customer,
        "ZscalerCloud": cloud,
    }


def resolve_network(
    sess: boto3.Session, env: dict[str, str], non_interactive: bool
) -> dict[str, str]:
    """Decide VPC topology — new vs existing."""
    requested = env.get("AWS_NETWORK_MODE", "").strip()
    if not requested and not non_interactive:
        info(
            "Network — pick ONE:\n"
            "  1) NEW VPC (script provisions VPC + 2 public + 2 private subnets + NAT)\n"
            "  2) EXISTING VPC (you point at one you already operate)"
        )
        mode = prompt_choice("Network", ["new", "existing"], default="new")
        requested = "CreateNew" if mode == "new" else "UseExisting"
    elif not requested:
        requested = "CreateNew"

    if requested == "CreateNew":
        cidr = env.get("AWS_VPC_CIDR", "").strip() or "10.42.0.0/16"
        if not non_interactive:
            cidr = prompt("New VPC CIDR block", default=cidr)
        return {
            "NetworkMode": "CreateNew",
            "NewVpcCidr": cidr,
            "ExistingVpcId": "",
            "ExistingPublicSubnetIds": "",
            "ExistingPrivateSubnetIds": "",
        }

    # UseExisting path
    vpc_id = env.get("AWS_VPC_ID", "").strip()
    pub_subs = env.get("AWS_PUBLIC_SUBNET_IDS", "").strip()
    priv_subs = env.get("AWS_PRIVATE_SUBNET_IDS", "").strip()

    if not (vpc_id and pub_subs and priv_subs) and not non_interactive:
        info("Discovering VPCs...")
        vpcs = list_vpcs(sess)
        if not vpcs:
            die("No VPCs found in this region. Pick NetworkMode=CreateNew instead.")
        print("\n  Available VPCs:")
        for i, v in enumerate(vpcs, 1):
            flag = "(default)" if v["default"] else ""
            print(
                f"    {i:>2}. {v['id']:<24} {v['cidr']:<18} {flag:<10} {v['name']}"
            )
        while True:
            raw = input(f"  Pick a VPC [1-{len(vpcs)}]: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(vpcs):
                vpc_id = vpcs[int(raw) - 1]["id"]
                break
        info(f"Discovering subnets in {vpc_id}...")
        subs = list_subnets_for_vpc(sess, vpc_id)
        pub_list = pick_subnets(subs, "public", want_public=True)
        priv_list = pick_subnets(subs, "private", want_public=False)
        pub_subs = ",".join(pub_list)
        priv_subs = ",".join(priv_list)

    if not (vpc_id and pub_subs and priv_subs):
        die(
            "AWS_VPC_ID, AWS_PUBLIC_SUBNET_IDS, and AWS_PRIVATE_SUBNET_IDS are all "
            "required when NetworkMode=UseExisting in non-interactive mode."
        )

    return {
        "NetworkMode": "UseExisting",
        "NewVpcCidr": "10.42.0.0/16",
        "ExistingVpcId": vpc_id,
        "ExistingPublicSubnetIds": pub_subs,
        "ExistingPrivateSubnetIds": priv_subs,
    }


def resolve_cluster(
    sess: boto3.Session, env: dict[str, str], non_interactive: bool
) -> dict[str, str]:
    """Decide whether to create a new EKS cluster or attach to an existing one."""
    requested = env.get("AWS_CLUSTER_MODE", "").strip()
    if not requested and not non_interactive:
        info(
            "EKS cluster — pick ONE:\n"
            "  1) NEW cluster (script provisions cluster + managed node group)\n"
            "  2) EXISTING cluster (attach to one you already operate)"
        )
        mode = prompt_choice("Cluster", ["new", "existing"], default="new")
        requested = "CreateNew" if mode == "new" else "UseExisting"
    elif not requested:
        requested = "CreateNew"

    if requested == "CreateNew":
        cluster_name = env.get("AWS_CLUSTER_NAME", "").strip() or DEFAULT_CLUSTER
        k8s_version = env.get("AWS_KUBE_VERSION", "").strip() or DEFAULT_KUBE_VERSION
        node_type = env.get("AWS_NODE_INSTANCE_TYPE", "").strip() or DEFAULT_NODE_TYPE
        if not non_interactive:
            cluster_name = prompt("Cluster name", default=cluster_name)
            k8s_version = prompt("Kubernetes version", default=k8s_version)
            node_type = prompt("Node instance type", default=node_type)
        return {
            "ClusterMode": "CreateNew",
            "ClusterName": cluster_name,
            "KubernetesVersion": k8s_version,
            "NodeInstanceType": node_type,
            "ExistingClusterOidcProviderArn": "",
        }

    # UseExisting path: pick from the regional list
    eks = sess.client("eks")
    iam = sess.client("iam")
    cluster_name = env.get("AWS_CLUSTER_NAME", "").strip()
    if not cluster_name and not non_interactive:
        info("Discovering EKS clusters in this region...")
        clusters = eks.list_clusters().get("clusters", [])
        if not clusters:
            die(
                f"No EKS clusters found in {sess.region_name}. "
                "Pick ClusterMode=CreateNew instead."
            )
        print("\n  Available clusters:")
        for i, c in enumerate(clusters, 1):
            print(f"    {i:>2}. {c}")
        while True:
            raw = input(f"  Pick cluster [1-{len(clusters)}]: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(clusters):
                cluster_name = clusters[int(raw) - 1]
                break

    if not cluster_name:
        die("AWS_CLUSTER_NAME is required when ClusterMode=UseExisting.")

    try:
        desc = eks.describe_cluster(name=cluster_name)["cluster"]
    except ClientError as e:
        die(f"Could not describe cluster '{cluster_name}': {e}")
    issuer = desc.get("identity", {}).get("oidc", {}).get("issuer", "")
    if not issuer:
        die(
            f"Cluster {cluster_name} has no OIDC issuer. IRSA requires one; "
            "enable IAM OIDC on the cluster first (aws eks ...)."
        )

    # Find or report the OIDC provider ARN
    issuer_host = issuer.replace("https://", "")
    try:
        providers = iam.list_open_id_connect_providers()["OpenIDConnectProviderList"]
    except ClientError as e:
        die(f"Could not list IAM OIDC providers: {e}")
    matching = [p["Arn"] for p in providers if issuer_host in p["Arn"]]
    if not matching:
        die(
            f"No IAM OIDC provider registered for {issuer}. "
            f"Create one with:  eksctl utils associate-iam-oidc-provider "
            f"--cluster {cluster_name} --approve"
        )
    oidc_provider_arn = matching[0]
    ok(f"  Cluster {cluster_name}: OIDC provider {oidc_provider_arn}")

    return {
        "ClusterMode": "UseExisting",
        "ClusterName": cluster_name,
        "KubernetesVersion": DEFAULT_KUBE_VERSION,
        "NodeInstanceType": DEFAULT_NODE_TYPE,
        "ExistingClusterOidcProviderArn": oidc_provider_arn,
    }


# Kept for arity-compat with the older signature; EKS v1 doesn't expose TLS yet.
def resolve_tls(
    sess: boto3.Session, env: dict[str, str], non_interactive: bool
) -> dict[str, str]:
    """Decide TLS path — managed ACM via Route53, existing cert ARN, or none."""
    mode = env.get("AWS_TLS_MODE", "").strip()
    if not mode and not non_interactive:
        info(
            "TLS — pick ONE:\n"
            "  1) AcmManaged   — stack provisions a Route53-validated ACM cert + alias\n"
            "  2) AcmExisting  — attach an ACM cert you already have\n"
            "  3) None         — plaintext HTTP on the ALB (demo only)"
        )
        mode = prompt_choice(
            "TLS mode",
            ["AcmManaged", "AcmExisting", "None"],
            default="AcmManaged",
        )
    elif not mode:
        mode = "None"

    if mode == "AcmManaged":
        zone_id = env.get("AWS_HOSTED_ZONE_ID", "").strip()
        domain = env.get("AWS_DOMAIN_NAME", "").strip()
        if (not zone_id or not domain) and not non_interactive:
            info("Discovering Route53 hosted zones...")
            zones = [z for z in list_hosted_zones(sess) if not z["private"]]
            if not zones:
                die("No public Route53 hosted zones found. Pick AcmExisting or None.")
            print("\n  Public hosted zones:")
            for i, z in enumerate(zones, 1):
                print(f"    {i:>2}. {z['name']:<40} {z['id']}")
            while True:
                raw = input(f"  Pick zone [1-{len(zones)}]: ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(zones):
                    zone = zones[int(raw) - 1]
                    zone_id = zone["id"]
                    suggestion = f"mcp.{zone['name']}"
                    break
            domain = prompt("Public FQDN for the MCP server", default=suggestion)
        if not (zone_id and domain):
            die("AWS_HOSTED_ZONE_ID and AWS_DOMAIN_NAME required for AcmManaged TLS.")
        return {
            "TlsMode": "AcmManaged",
            "HostedZoneId": zone_id,
            "DomainName": domain,
            "ExistingCertArn": "",
        }

    if mode == "AcmExisting":
        arn = env.get("AWS_CERT_ARN", "").strip()
        if not arn and not non_interactive:
            info("Discovering ISSUED ACM certs in this region...")
            certs = list_acm_certs(sess)
            if not certs:
                die("No ISSUED ACM certs in this region. Provision one or pick another TLS mode.")
            print("\n  Available certs:")
            for i, c in enumerate(certs, 1):
                print(f"    {i:>2}. {c['domain']:<40} {c['arn']}")
            while True:
                raw = input(f"  Pick cert [1-{len(certs)}]: ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(certs):
                    arn = certs[int(raw) - 1]["arn"]
                    break
        if not arn:
            die("AWS_CERT_ARN required for AcmExisting TLS mode.")
        return {
            "TlsMode": "AcmExisting",
            "HostedZoneId": "",
            "DomainName": "",
            "ExistingCertArn": arn,
        }

    # None
    return {
        "TlsMode": "None",
        "HostedZoneId": "",
        "DomainName": "",
        "ExistingCertArn": "",
    }


def resolve_auth(env: dict[str, str], non_interactive: bool) -> dict[str, str]:
    """Decide MCP-client auth mode + collect mode-specific params."""
    mode = env.get("ZSCALER_MCP_AUTH_MODE", "").strip()
    if not mode and not non_interactive:
        info(
            "MCP client auth — pick ONE:\n"
            "  1) zscaler    — HTTP Basic with Zscaler OneAPI creds (simplest)\n"
            "  2) jwt        — IdP-issued bearer (Auth0, Cognito, Entra...)\n"
            "  3) api-key    — shared secret (X-Api-Key header)\n"
            "  4) oidcproxy  — full OAuth 2.1 with Dynamic Client Registration\n"
            "  5) none       — no client auth (cluster-internal use only)"
        )
        mode = prompt_choice(
            "Auth mode",
            ["zscaler", "jwt", "api-key", "oidcproxy", "none"],
            default="zscaler",
        )
    elif not mode:
        mode = "zscaler"

    out: dict[str, str] = {"McpAuthMode": mode}
    if mode == "jwt":
        out["JwtJwksUri"] = env.get("ZSCALER_MCP_AUTH_JWKS_URI", "")
        out["JwtIssuer"] = env.get("ZSCALER_MCP_AUTH_ISSUER", "")
        out["JwtAudience"] = env.get("ZSCALER_MCP_AUTH_AUDIENCE", "") or "zscaler-mcp-server"
        if not non_interactive:
            if not out["JwtJwksUri"]:
                out["JwtJwksUri"] = prompt("JWT JWKS URI")
            if not out["JwtIssuer"]:
                out["JwtIssuer"] = prompt("JWT Issuer")
            out["JwtAudience"] = prompt("JWT Audience", default=out["JwtAudience"])
    elif mode == "api-key":
        out["ApiKey"] = env.get("ZSCALER_MCP_AUTH_API_KEY", "")
        if not out["ApiKey"]:
            out["ApiKey"] = "mcp-" + "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(40)
            )
            info(f"  Auto-generated API key: {out['ApiKey']}")
    elif mode == "oidcproxy":
        out["OidcProxyClientId"] = env.get("OIDCPROXY_CLIENT_ID", "")
        out["OidcProxyClientSecret"] = env.get("OIDCPROXY_CLIENT_SECRET", "")
        out["OidcProxyIssuer"] = env.get("OIDCPROXY_ISSUER", "")
        out["OidcProxyAudience"] = env.get("OIDCPROXY_AUDIENCE", "")
        if not non_interactive:
            if not out["OidcProxyClientId"]:
                out["OidcProxyClientId"] = prompt("OIDCProxy Client ID")
            if not out["OidcProxyClientSecret"]:
                out["OidcProxyClientSecret"] = prompt(
                    "OIDCProxy Client Secret", secret=True
                )
            if not out["OidcProxyIssuer"]:
                out["OidcProxyIssuer"] = prompt("OIDCProxy Issuer")
            out["OidcProxyAudience"] = prompt(
                "OIDCProxy Audience", default=out["OidcProxyAudience"] or "zscaler-mcp"
            )
    return out


# ════════════════════════════════════════════════════════════════════════
#  kubectl / manifest helpers
# ════════════════════════════════════════════════════════════════════════


def _ensure_kubectl() -> None:
    if not shutil.which("kubectl"):
        die(
            "`kubectl` is required for the EKS deployment.\n"
            "  Install instructions: https://kubernetes.io/docs/tasks/tools/#kubectl"
        )
    if not shutil.which("aws"):
        die("`aws` CLI v2 is required for `aws eks update-kubeconfig`.")


def run_kubectl(
    args: list[str], *, context: str | None = None, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    """Invoke kubectl with the cluster's context. Returns the CompletedProcess."""
    cmd = ["kubectl"]
    if context:
        cmd += ["--context", context]
    cmd += args
    if capture:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    return subprocess.run(cmd, check=check)


def update_kubeconfig(region: str, cluster_name: str) -> str:
    """Run `aws eks update-kubeconfig` and return the resulting context name."""
    info(f"Updating kubeconfig for cluster {cluster_name}...")
    result = subprocess.run(
        [
            "aws",
            "eks",
            "update-kubeconfig",
            "--region",
            region,
            "--name",
            cluster_name,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # `arn:aws:eks:<rgn>:<acct>:cluster/<name>` — what aws eks update-kubeconfig
    # writes as the current context name.
    sts_resp = boto3.Session(region_name=region).client("sts").get_caller_identity()
    context = f"arn:aws:eks:{region}:{sts_resp['Account']}:cluster/{cluster_name}"
    ok(f"  kubeconfig context: {context}")
    if result.stderr:
        for line in result.stderr.splitlines():
            if line.strip():
                print(f"    {line}")
    return context


def fetch_secret_values(sess: boto3.Session, secret_id: str) -> dict[str, str]:
    """Pull the JSON SM secret and return its keys as a dict."""
    sm = sess.client("secretsmanager")
    r = sm.get_secret_value(SecretId=secret_id)
    raw = json.loads(r["SecretString"])
    return {str(k): str(v) for k, v in raw.items()}


def render_manifests(substitutions: dict[str, str]) -> Path:
    """Render every k8s-manifests/*.yaml via ${VAR} interpolation and write the
    result into a tmpdir under SCRIPT_DIR. Returns the directory path."""
    target = SCRIPT_DIR / ".rendered-manifests"
    if target.exists():
        for f in target.iterdir():
            f.unlink()
    else:
        target.mkdir()

    for name in K8S_MANIFESTS:
        src = K8S_DIR / name
        if not src.exists():
            die(f"Missing manifest: {src}")
        text = src.read_text()
        # Substitute ${VAR} occurrences. Unmatched placeholders become "".
        def _sub(match: re.Match[str]) -> str:
            return substitutions.get(match.group(1), "")
        rendered = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", _sub, text)
        (target / name).write_text(rendered)
    return target


def apply_manifests(rendered_dir: Path, context: str) -> None:
    info(f"Applying K8s manifests from {rendered_dir}...")
    # Apply in order — namespace first, then everything else.
    for name in K8S_MANIFESTS:
        path = rendered_dir / name
        run_kubectl(["apply", "-f", str(path)], context=context)
    ok("  All manifests applied.")


def wait_for_loadbalancer(
    context: str, namespace: str, service: str, timeout_s: int = 600
) -> str:
    """Poll until the LoadBalancer Service has an externally-reachable hostname.
    Returns the hostname (or IP)."""
    info(f"Waiting for LoadBalancer hostname (timeout {timeout_s}s)...")
    deadline = time.monotonic() + timeout_s
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    start = time.monotonic()
    last_status = ""
    while time.monotonic() < deadline:
        try:
            r = run_kubectl(
                [
                    "get",
                    "service",
                    service,
                    "-n",
                    namespace,
                    "-o",
                    "json",
                ],
                context=context,
                capture=True,
                check=False,
            )
            if r.returncode != 0:
                status = "not-yet-created"
            else:
                svc = json.loads(r.stdout)
                ingress = (
                    svc.get("status", {})
                    .get("loadBalancer", {})
                    .get("ingress", [])
                )
                if ingress:
                    host = ingress[0].get("hostname") or ingress[0].get("ip", "")
                    if host:
                        sys.stdout.write("\r" + " " * 80 + "\r")
                        ok(f"LoadBalancer ready: {host}  ({_fmt_elapsed(time.monotonic() - start)})")
                        return host
                    status = "pending"
                else:
                    status = "pending"
        except Exception as e:  # noqa: BLE001
            status = f"error:{e}"

        if status != last_status:
            sys.stdout.write("\r" + " " * 80 + "\r")
            info(f"  {status}  (elapsed: {_fmt_elapsed(time.monotonic() - start)})")
            last_status = status

        sys.stdout.write(
            f"\r  {spinner[i % len(spinner)]} {status}"
            f"  (elapsed: {_fmt_elapsed(time.monotonic() - start)})"
        )
        sys.stdout.flush()
        i += 1
        time.sleep(5)

    err(f"Timed out after {timeout_s}s waiting for LoadBalancer hostname.")
    return ""


# ════════════════════════════════════════════════════════════════════════
#  Deploy
# ════════════════════════════════════════════════════════════════════════


def cmd_deploy(args: argparse.Namespace) -> None:
    print_zscaler_logo()
    _ensure_kubectl()
    step("1/7  Configuration")

    env_file = resolve_env_file_path(args.env_file, args.non_interactive)
    env = load_env_file(env_file) if env_file else {}
    if env_file:
        ok(f"Loaded env from {env_file}")
    else:
        info("No .env / env.properties loaded — proceeding interactively.")

    # ── State-file-driven re-deploy ────────────────────────────────────────
    # If a prior deploy left a state file behind, treat this run as an
    # in-place update. Operator can opt out with --fresh.
    existing_state = load_state() if not getattr(args, "fresh", False) else {}
    if existing_state:
        partial = existing_state.get("state_partial", False)
        phase = existing_state.get("phase", "<unknown>")
        if partial:
            warn(
                f"Found PARTIAL state file from a failed deploy "
                f"(last phase: {phase}). Re-running with saved values "
                "as defaults — check the CFN console and `kubectl get pods` "
                "first if the previous deploy left objects in a Failed state."
            )
        else:
            ok(
                f"Found existing deployment "
                f"(stack={existing_state.get('stack_name', '?')}, "
                f"cluster={existing_state.get('cluster_name', '?')}, "
                f"region={existing_state.get('region', '?')}). "
                "Re-using saved values — CFN runs an in-place update + "
                "`kubectl apply` rolls out the new manifest."
            )
        _apply_state_for_redeploy(existing_state, env)

    region = env.get("AWS_REGION", "").strip() or DEFAULT_REGION
    stack_name = env.get("AWS_STACK_NAME", "").strip() or DEFAULT_STACK
    prefix = env.get("AWS_RESOURCE_NAME_PREFIX", "").strip() or DEFAULT_PREFIX

    if not args.non_interactive:
        region = prompt("AWS region", default=region)
        stack_name = prompt("CloudFormation stack name", default=stack_name)
        prefix = prompt("Resource name prefix (lowercase, 3-32 chars)", default=prefix)

    if not re.match(r"^[a-z][a-z0-9-]{1,30}[a-z0-9]$", prefix):
        die("Resource name prefix must match ^[a-z][a-z0-9-]{1,30}[a-z0-9]$")

    sess = get_session(region, profile=os.environ.get("AWS_PROFILE"))
    account = sess.client("sts").get_caller_identity()["Account"]

    bucket = (
        env.get("AWS_ASSET_BUCKET", "").strip()
        or f"{prefix}-cfn-{account}-{region}"
    )

    # ── 2. Resolve cluster, credentials, network, auth ────────────────
    step("2/7  Cluster & credentials")
    cluster = resolve_cluster(sess, env, args.non_interactive)
    creds = resolve_credentials(sess, env, args.non_interactive)
    # Network is only relevant when we're creating a brand-new cluster.
    if cluster["ClusterMode"] == "CreateNew":
        network = resolve_network(sess, env, args.non_interactive)
    else:
        # Mirror the schema so the CFN params loop downstream still iterates.
        network = {
            "NetworkMode": "UseExisting",
            "NewVpcCidr": "",
            "ExistingVpcId": "",
            "ExistingPublicSubnetIds": "",
            "ExistingPrivateSubnetIds": "",
        }
    auth = resolve_auth(env, args.non_interactive)

    namespace = env.get("AWS_K8S_NAMESPACE", "").strip() or DEFAULT_NAMESPACE
    sa_name = env.get("AWS_K8S_SA_NAME", "").strip() or DEFAULT_SA_NAME
    image_uri = env.get("ZSCALER_MCP_IMAGE_URI", "").strip() or DEFAULT_IMAGE
    _check_image_compatibility(sess, image_uri, non_interactive=args.non_interactive)
    replicas = int(env.get("AWS_REPLICAS", "1") or "1")
    if not args.non_interactive:
        namespace = prompt("K8s namespace", default=namespace)
        replicas = prompt_int("Replica count", default=replicas, lo=1, hi=20)

    # MCP feature flags + Pod knobs (passed through as-is from .env)
    flags = {
        "WriteToolsEnabled": env.get("ZSCALER_MCP_WRITE_ENABLED", "false"),
        "WriteToolsAllowlist": env.get("ZSCALER_MCP_WRITE_TOOLS", ""),
        "DisabledTools": env.get("ZSCALER_MCP_DISABLED_TOOLS", ""),
        "DisabledServices": env.get("ZSCALER_MCP_DISABLED_SERVICES", ""),
        "Toolsets": env.get("ZSCALER_MCP_TOOLSETS", ""),
        "DisabledToolsets": env.get("ZSCALER_MCP_DISABLED_TOOLSETS", ""),
        "EnableToolCallLogging": env.get("ZSCALER_MCP_LOG_TOOL_CALLS", "true"),
        "K8sNamespace": namespace,
        "K8sServiceAccountName": sa_name,
        "NodeDesiredCount": str(env.get("AWS_NODE_DESIRED_COUNT", "1")),
        "NodeMinCount": str(env.get("AWS_NODE_MIN_COUNT", "1")),
        "NodeMaxCount": str(env.get("AWS_NODE_MAX_COUNT", "3")),
        "NodeDiskSize": str(env.get("AWS_NODE_DISK_SIZE", "20")),
    }

    # ── 3. Confirm summary ─────────────────────────────────────────────
    step("3/7  Review")
    print(f"  Stack:          {stack_name}")
    print(f"  Region:         {region}")
    print(f"  Account:        {account}")
    print(f"  Asset bucket:   {bucket}")
    print(f"  Cluster:        {cluster['ClusterMode']} ({cluster['ClusterName']})")
    if cluster["ClusterMode"] == "CreateNew":
        print(f"  K8s version:    {cluster['KubernetesVersion']}")
        print(f"  Node type:      {cluster['NodeInstanceType']}")
    print(f"  Credentials:    {creds['CredentialSource']}"
          + (f" ({creds.get('ExistingSecretName')})" if creds["CredentialSource"] == "UseExisting" else ""))
    if cluster["ClusterMode"] == "CreateNew":
        print(f"  Network:        {network['NetworkMode']}"
              + (f" (VPC {network['ExistingVpcId']})" if network["NetworkMode"] == "UseExisting" else f" ({network['NewVpcCidr']})"))
    print(f"  MCP auth:       {auth['McpAuthMode']}")
    print(f"  Namespace:      {namespace}")
    print(f"  Image:          {image_uri}")
    print(f"  Replicas:       {replicas}")

    if not args.non_interactive and not prompt_bool(
        "\nProceed with deployment?", default=True
    ):
        info("Aborted by user.")
        return

    # ── 4. Asset bucket + nested-template upload ───────────────────────
    step("4/7  Upload CloudFormation assets")
    ensure_asset_bucket(sess, bucket)
    prefix_key = upload_nested_templates(sess, bucket, "zscaler-mcp/")

    # ── 5. Stack create/update ─────────────────────────────────────────
    step("5/7  CloudFormation deploy")
    cfn = sess.client("cloudformation")
    # Allowlist of keys the EKS root template (cloudformation/zscaler-mcp-root.yaml)
    # actually declares as Parameters. Anything outside this set is an
    # MCP-runtime knob that belongs on the Kubernetes Deployment manifest
    # (rendered into `substitutions` later in this function), NOT on the
    # CFN stack. EKS has no Task Definition / UserData where runtime env
    # vars get baked at stack time — the pod spec carries them — so we
    # have to gate the params loop explicitly. Flat-flattening every
    # resolver dict into CFN produced ValidationError on
    # [Toolsets, McpAuthMode, WriteToolsAllowlist, DisabledToolsets,
    #  ExistingSecretName, DisabledServices, DisabledTools,
    #  WriteToolsEnabled, EnableToolCallLogging].
    # Keep this list in lockstep with the template's Parameters block.
    _CFN_PARAM_ALLOWLIST: frozenset[str] = frozenset({
        # Cluster
        "ClusterMode", "ClusterName", "KubernetesVersion",
        "NodeInstanceType", "NodeDesiredCount", "NodeMinCount",
        "NodeMaxCount", "NodeDiskSize",
        # Credentials
        "CredentialSource", "ZscalerClientId", "ZscalerClientSecret",
        "ZscalerVanityDomain", "ZscalerCustomerId", "ZscalerCloud",
        "ExistingSecretArn",
        # Network
        "NetworkMode", "NewVpcCidr", "ExistingVpcId",
        "ExistingPublicSubnetIds", "ExistingPrivateSubnetIds",
        # K8s identity (consumed by IAM stack to scope the IRSA trust policy)
        "K8sNamespace", "K8sServiceAccountName",
        "ExistingClusterOidcProviderArn",
    })
    params: list[dict] = [
        {"ParameterKey": "AssetBucket",      "ParameterValue": bucket},
        {"ParameterKey": "AssetPrefix",      "ParameterValue": prefix_key},
        {"ParameterKey": "ResourceNamePrefix", "ParameterValue": prefix},
    ]
    dropped: list[str] = []
    for d in (cluster, creds, network, auth, flags):
        for k, v in d.items():
            if k in _CFN_PARAM_ALLOWLIST:
                params.append({"ParameterKey": k, "ParameterValue": str(v)})
            else:
                dropped.append(k)
    if dropped:
        # Visibility-only — these are correctly applied to the K8s manifest
        # downstream; we just don't want them masquerading as CFN params.
        info(
            "Not forwarding to CloudFormation (applied to K8s manifest "
            f"instead): {', '.join(sorted(set(dropped)))}"
        )

    template_url = f"https://{bucket}.s3.amazonaws.com/{prefix_key}{ROOT_TEMPLATE}"
    # Upload root template alongside the nested ones so CFN can fetch it
    sess.client("s3").upload_file(
        str(CFN_DIR / ROOT_TEMPLATE), bucket, f"{prefix_key}{ROOT_TEMPLATE}"
    )

    existing = stack_status(sess, stack_name)
    if existing is None:
        info(f"Creating stack {stack_name}...")
        cfn.create_stack(
            StackName=stack_name,
            TemplateURL=template_url,
            Parameters=params,
            Capabilities=["CAPABILITY_NAMED_IAM"],
            # DO_NOTHING keeps the failed stack around in CREATE_FAILED so
            # the operator can inspect resource-level events in the CFN
            # console. Cleanup is explicit via `destroy`.
            OnFailure="DO_NOTHING",
            Tags=[
                {"Key": "Application", "Value": "zscaler-mcp-server"},
                {"Key": "Deployment", "Value": "eks"},
            ],
        )
        operation = "create"
    elif existing.endswith("_COMPLETE") and "ROLLBACK" not in existing:
        info(f"Updating stack {stack_name} (current status {existing})...")
        try:
            cfn.update_stack(
                StackName=stack_name,
                TemplateURL=template_url,
                Parameters=params,
                Capabilities=["CAPABILITY_NAMED_IAM"],
            )
            operation = "update"
        except ClientError as e:
            msg = str(e)
            if "No updates are to be performed" in msg:
                ok("Stack is already up to date — nothing to do.")
                operation = "noop"
            else:
                die(f"update-stack failed: {e}")
    else:
        die(
            f"Stack {stack_name} is in {existing} state. Run "
            f"`{Path(__file__).name} destroy` first to clean it up."
        )

    # Persist the minimum state needed for `destroy` to find this stack —
    # has to happen BEFORE `wait_for_stack` because that call can take
    # 30+ minutes (EKS clusters take ~12 min just to come up) and the
    # user might Ctrl-C, the script may crash, or the stack may end up
    # CREATE_FAILED. In any of those cases, `destroy` needs to know the
    # stack name and region to clean up.
    if operation != "noop":
        save_partial_state(
            {
                "stack_name": stack_name,
                "region": region,
                "account": account,
                "asset_bucket": bucket,
                "prefix": prefix,
                "operation": operation,
                "credential_source": creds["CredentialSource"],
                "cluster_mode": cluster["ClusterMode"],
                "network_mode": network["NetworkMode"],
                "auth_mode": auth["McpAuthMode"],
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            phase="stack_submitted",
        )

    if operation != "noop":
        final = wait_for_stack(sess, stack_name, operation=operation, timeout_min=45)
        if final == "STACK_DELETED" or not final.endswith("_COMPLETE") or "ROLLBACK" in final:
            save_partial_state(
                {"last_status": final},
                phase="stack_failed",
            )
            region = sess.region_name or "us-east-1"
            console_url = (
                f"https://{region}.console.aws.amazon.com/cloudformation/home"
                f"?region={region}#/stacks?filteringText={stack_name}"
            )
            info(f"Inspect the failed stack in the CFN console: {console_url}")
            info(
                f"Run `python {Path(__file__).name} destroy` to clean it up "
                f"before re-deploying."
            )
            die(f"Stack deploy failed: {final}")

    # ── 6. K8s manifests ───────────────────────────────────────────────
    step("6/7  Apply Kubernetes manifests")
    outputs = stack_outputs(sess, stack_name)
    cluster_name = outputs.get("ClusterName") or cluster["ClusterName"]
    pod_role_arn = outputs.get("PodRoleArn", "")
    secret_arn = outputs.get("SecretArn") or creds.get("ExistingSecretArn", "")
    if not secret_arn:
        die("Stack did not expose SecretArn — cannot fetch creds for the K8s Secret.")
    if not pod_role_arn:
        die("Stack did not expose PodRoleArn — IRSA wiring missing.")

    context = update_kubeconfig(region, cluster_name)
    info("Fetching credentials from Secrets Manager (for the K8s Secret)...")
    sm_values = fetch_secret_values(sess, secret_arn)
    required = (
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
    )
    for k in required:
        if not sm_values.get(k):
            die(f"Secret is missing required key: {k}")

    substitutions: dict[str, str] = {
        "NAMESPACE": namespace,
        "SA_NAME": sa_name,
        "POD_ROLE_ARN": pod_role_arn,
        "AWS_REGION": region,
        "SECRET_NAME": outputs.get("SecretName", "") or creds.get("ExistingSecretName", ""),
        "IMAGE": image_uri,
        "REPLICAS": str(replicas),
        "AUTH_MODE": auth["McpAuthMode"],
        "AUTH_ENABLED": "false" if auth["McpAuthMode"] == "none" else "true",
        "JWT_JWKS_URI": auth.get("JwtJwksUri", ""),
        "JWT_ISSUER": auth.get("JwtIssuer", ""),
        "JWT_AUDIENCE": auth.get("JwtAudience", ""),
        "API_KEY": auth.get("ApiKey", ""),
        "WRITE_ENABLED": flags["WriteToolsEnabled"],
        "WRITE_TOOLS": flags["WriteToolsAllowlist"],
        "DISABLED_TOOLS": flags["DisabledTools"],
        "DISABLED_SERVICES": flags["DisabledServices"],
        "TOOLSETS": flags["Toolsets"],
        "DISABLED_TOOLSETS": flags["DisabledToolsets"],
        "LOG_TOOL_CALLS": flags["EnableToolCallLogging"],
        "OIDC_CLIENT_ID": auth.get("OidcProxyClientId", ""),
        "OIDC_CLIENT_SECRET": auth.get("OidcProxyClientSecret", ""),
        "OIDC_ISSUER": auth.get("OidcProxyIssuer", ""),
        "OIDC_AUDIENCE": auth.get("OidcProxyAudience", ""),
        # Base64 of each cred for the K8s Secret manifest
        "B64_CLIENT_ID": base64.b64encode(sm_values["ZSCALER_CLIENT_ID"].encode()).decode(),
        "B64_CLIENT_SECRET": base64.b64encode(sm_values["ZSCALER_CLIENT_SECRET"].encode()).decode(),
        "B64_VANITY_DOMAIN": base64.b64encode(sm_values["ZSCALER_VANITY_DOMAIN"].encode()).decode(),
        "B64_CUSTOMER_ID": base64.b64encode(sm_values["ZSCALER_CUSTOMER_ID"].encode()).decode(),
        "B64_CLOUD": base64.b64encode(sm_values.get("ZSCALER_CLOUD", "production").encode()).decode(),
    }
    rendered_dir = render_manifests(substitutions)
    apply_manifests(rendered_dir, context)

    lb_host = wait_for_loadbalancer(context, namespace, "zscaler-mcp-server", timeout_s=600)
    if not lb_host:
        warn(
            "LoadBalancer didn't surface a hostname in time — most likely "
            "cause is Pod CrashLoopBackoff (image arch mismatch, missing "
            "env var, application crash). Dumping recent Pod logs:"
        )
        _dump_recent_pod_logs(namespace, context=context)
        info(
            "Re-run `python eks_mcp_operations.py status` to check Pod state, "
            "and `python eks_mcp_operations.py logs --tail 200` for more."
        )
        return
    mcp_url = f"http://{lb_host}/mcp"

    # ── 7. Configure clients + summary ─────────────────────────────────
    step("7/7  Configure MCP clients")
    headers = _build_auth_headers(
        auth["McpAuthMode"],
        zscaler_client_id=creds.get("ZscalerClientId", env.get("ZSCALER_CLIENT_ID", "")),
        zscaler_client_secret=creds.get("ZscalerClientSecret", env.get("ZSCALER_CLIENT_SECRET", "")),
        api_key=auth.get("ApiKey", ""),
    )
    server_name = env.get("MCP_SERVER_NAME", "").strip() or DEFAULT_SERVER_NAME

    selected_ids: list[str] = []
    if args.skip_client_config:
        info("Skipping MCP client configuration (--skip-client-config).")
    else:
        installed = [a for a in AGENTS if a["installed_fn"]()]
        if not installed:
            info("No supported MCP clients detected on this machine.")
        elif args.non_interactive:
            selected_ids = [a["id"] for a in installed]
        else:
            print("\n  Detected MCP clients:")
            for i, a in enumerate(installed, 1):
                print(f"    {i:>2}. {a['name']}")
            raw = input(
                "  Configure which? (comma-separated numbers, 'all', or empty to skip): "
            ).strip().lower()
            if raw == "all":
                selected_ids = [a["id"] for a in installed]
            elif raw:
                try:
                    picks = [int(p) for p in raw.replace(" ", "").split(",")]
                    selected_ids = [installed[p - 1]["id"] for p in picks if 1 <= p <= len(installed)]
                except (ValueError, IndexError):
                    warn("  Invalid selection — skipping client config.")

    written = configure_clients(server_name, mcp_url, headers, selected_ids) if selected_ids else {}

    # Merge final outputs onto the partial state we wrote earlier, then
    # stamp it as complete via `finalize_state`.
    state = load_state()
    state.update(
        {
            "stack_name": stack_name,
            "region": region,
            "account": account,
            "asset_bucket": bucket,
            "prefix": prefix,
            "credential_source": creds["CredentialSource"],
            "secret_name": outputs.get("SecretName", "") or creds.get("ExistingSecretName", ""),
            "secret_arn": secret_arn,
            "network_mode": network["NetworkMode"],
            "vpc_id": outputs.get("VpcId", ""),
            "cluster_mode": cluster["ClusterMode"],
            "cluster_name": cluster_name,
            "k8s_context": context,
            "namespace": namespace,
            "service_account": sa_name,
            "pod_role_arn": pod_role_arn,
            "image": image_uri,
            "mcp_url": mcp_url,
            "lb_host": lb_host,
            "auth_mode": auth["McpAuthMode"],
            "server_name": server_name,
            "configured_clients": written,
        }
    )
    finalize_state(state)

    _print_deploy_summary(stack_name, region, outputs, auth, headers)


def _print_deploy_summary(
    stack_name: str,
    region: str,
    outputs: dict[str, str],
    auth: dict[str, str],
    headers: dict[str, str],
) -> None:
    state = load_state()
    print()
    bar = "═" * 72
    print(_ansi("1;32", bar))
    print(_ansi("1;32", "  ✓  Zscaler MCP Server deployed on AWS EKS"))
    print(_ansi("1;32", bar))
    print()
    print(f"  Stack name:     {stack_name}")
    print(f"  Region:         {region}")
    print(f"  Cluster:        {state.get('cluster_name', '(unknown)')}")
    print(f"  Namespace:      {state.get('namespace', '(unknown)')}")
    if outputs.get("VpcId"):
        print(f"  VPC:            {outputs['VpcId']}")
    if outputs.get("PodRoleArn"):
        print(f"  Pod role:       {outputs['PodRoleArn']}")
    if outputs.get("SecretName"):
        print(f"  Secret:         {outputs['SecretName']}")
    print()
    print(_ansi("1;36", "  Publicly accessible MCP URL"))
    print(_ansi("1;36", "  ──────────────────────────"))
    print(f"  {_ansi('1;33', state.get('mcp_url', '(unknown)'))}")
    print()
    print(f"  MCP client auth: {auth['McpAuthMode']}")
    if headers:
        print("  Required header(s) when connecting:")
        for k, v in headers.items():
            value = v if len(v) <= 30 else v[:14] + "..." + v[-12:]
            print(f"    {k}: {value}")
    print()
    print(_ansi("1;36", "  Next steps"))
    print(_ansi("1;36", "  ──────────"))
    print("    • Tail logs:    python eks_mcp_operations.py logs -f")
    print("    • Stack status: python eks_mcp_operations.py status")
    print("    • kubectl:      python eks_mcp_operations.py kubectl -- get pods")
    print("    • Rotate creds: python eks_mcp_operations.py rotate-secrets")
    print("    • Tear down:    python eks_mcp_operations.py destroy")
    print()
    warn(
        "TLS termination is NOT enabled in this preview — the NLB serves "
        "plain HTTP. For production, layer an ALB Ingress + cert-manager "
        "or NGINX Ingress + ACM in front of the Service. See the README."
    )


# ════════════════════════════════════════════════════════════════════════
#  Status / logs / destroy / configure
# ════════════════════════════════════════════════════════════════════════


def cmd_status(args: argparse.Namespace) -> None:
    state = load_state()
    if not state:
        die("No state file. Run `deploy` first.")
    sess = get_session(state["region"], profile=os.environ.get("AWS_PROFILE"))
    s = stack_status(sess, state["stack_name"])
    if s is None:
        warn(f"Stack {state['stack_name']} does not exist.")
        return
    color = _color_for_stack_status(s)
    info(f"Stack {state['stack_name']}: {_ansi(color, s)}")
    outputs = stack_outputs(sess, state["stack_name"])
    if outputs:
        print()
        for k, v in outputs.items():
            print(f"  {k}: {v}")

    if not shutil.which("kubectl"):
        warn("kubectl not found on PATH — skipping K8s status.")
        return
    context = state.get("k8s_context")
    namespace = state.get("namespace", DEFAULT_NAMESPACE)

    print()
    info("Pods:")
    run_kubectl(["get", "pods", "-n", namespace, "-o", "wide"], context=context, check=False)
    print()
    info("Deployments:")
    run_kubectl(["get", "deployment", "-n", namespace], context=context, check=False)
    print()
    info("Service:")
    run_kubectl(["get", "svc", "-n", namespace], context=context, check=False)
    if state.get("mcp_url"):
        print()
        print(f"  MCP URL: {_ansi('1;33', state['mcp_url'])}")


def cmd_kubectl(args: argparse.Namespace) -> None:
    """Pass-through to kubectl with the cluster's context preset.

    Use:  python eks_mcp_operations.py kubectl -- get pods -n zscaler-mcp
    The `--` separator is what argparse uses to forward unknown args.
    """
    state = load_state()
    if not state:
        die("No state file. Run `deploy` first.")
    context = state.get("k8s_context")
    if not context:
        die("State file has no kubectl context recorded.")
    forwarded = args.kubectl_args or []
    if not forwarded:
        die("No kubectl args supplied. Example:  ... kubectl -- get pods")
    info(f"kubectl --context {context} {' '.join(forwarded)}")
    os.execvp("kubectl", ["kubectl", "--context", context, *forwarded])


def cmd_rotate_secrets(args: argparse.Namespace) -> None:
    """Re-fetch creds from Secrets Manager and re-apply the K8s Secret.

    Pods consume the Secret via envFrom; the existing Pods continue to run on
    the old values until they're restarted. We trigger a rollout after the
    Secret is updated so the new values land immediately.
    """
    state = load_state()
    if not state:
        die("No state file. Run `deploy` first.")
    sess = get_session(state["region"], profile=os.environ.get("AWS_PROFILE"))
    secret_arn = state.get("secret_arn")
    if not secret_arn:
        die("State file has no SecretArn recorded.")

    info("Fetching credentials from Secrets Manager...")
    sm_values = fetch_secret_values(sess, secret_arn)
    namespace = state.get("namespace", DEFAULT_NAMESPACE)
    context = state.get("k8s_context")

    substitutions: dict[str, str] = {
        "NAMESPACE": namespace,
        "B64_CLIENT_ID": base64.b64encode(sm_values["ZSCALER_CLIENT_ID"].encode()).decode(),
        "B64_CLIENT_SECRET": base64.b64encode(sm_values["ZSCALER_CLIENT_SECRET"].encode()).decode(),
        "B64_VANITY_DOMAIN": base64.b64encode(sm_values["ZSCALER_VANITY_DOMAIN"].encode()).decode(),
        "B64_CUSTOMER_ID": base64.b64encode(sm_values["ZSCALER_CUSTOMER_ID"].encode()).decode(),
        "B64_CLOUD": base64.b64encode(sm_values.get("ZSCALER_CLOUD", "production").encode()).decode(),
    }
    rendered_text = (K8S_DIR / "02-secret.yaml").read_text()
    def _sub(match: re.Match[str]) -> str:
        return substitutions.get(match.group(1), "")
    rendered = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", _sub, rendered_text)
    tmp = SCRIPT_DIR / ".rendered-manifests" / "02-secret.yaml"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(rendered)

    info(f"Applying updated Secret to {namespace}...")
    run_kubectl(["apply", "-f", str(tmp)], context=context)
    info("Rolling the deployment so Pods pick up new env vars...")
    run_kubectl(
        ["rollout", "restart", "deployment/zscaler-mcp-server", "-n", namespace],
        context=context,
    )
    run_kubectl(
        ["rollout", "status", "deployment/zscaler-mcp-server", "-n", namespace],
        context=context,
    )
    ok("Rotated.")


def cmd_logs(args: argparse.Namespace) -> None:
    state = load_state()
    if not state:
        die("No state file. Run `deploy` first.")
    context = state.get("k8s_context")
    namespace = state.get("namespace", DEFAULT_NAMESPACE)
    if not context:
        die("State file has no kubectl context recorded.")
    kubectl_args = ["logs", "deployment/zscaler-mcp-server", "-n", namespace]
    if args.follow:
        kubectl_args.append("-f")
    if args.tail is not None:
        kubectl_args.extend(["--tail", str(args.tail)])
    info(f"kubectl --context {context} {' '.join(kubectl_args)}")
    os.execvp("kubectl", ["kubectl", "--context", context, *kubectl_args])


def cmd_destroy(args: argparse.Namespace) -> None:
    """Tear down the deployment.

    Resilient to missing or partial state: a failed deploy writes a
    partial-state file early (see ``save_partial_state``) so this command
    can still find the stack name. When no state exists at all, we fall
    back to ``DEFAULT_STACK`` / ``DEFAULT_REGION`` and let the operator
    override via ``--stack-name`` / ``--region``. K8s-object cleanup is
    skipped when no kube context was recorded.
    """
    state = load_state()
    region = (
        getattr(args, "region", None)
        or state.get("region")
        or os.environ.get("AWS_REGION", "").strip()
        or DEFAULT_REGION
    )
    stack_name = (
        getattr(args, "stack_name", None)
        or state.get("stack_name")
        or DEFAULT_STACK
    )

    if not state:
        warn(
            f"No state file found — falling back to defaults "
            f"(stack='{stack_name}', region='{region}'). "
            f"Override with --stack-name / --region if needed. "
            "K8s objects (if any) will not be cleaned up — only the CFN "
            "stack will be deleted."
        )
    elif state.get("state_partial"):
        warn(
            f"State file is partial — last phase reached was "
            f"'{state.get('phase', '<unknown>')}'. The CFN stack is "
            "probably in CREATE_FAILED. Cleaning it up below."
        )

    sess = get_session(region, profile=os.environ.get("AWS_PROFILE"))

    if stack_status(sess, stack_name) is None:
        ok(f"Stack {stack_name} does not exist — nothing to delete.")
        STATE_FILE.unlink(missing_ok=True)
        return

    if not args.yes and not prompt_bool(
        f"Delete K8s manifests + stack {stack_name} in {region}? "
        "If we created the cluster, the entire EKS cluster + node group + VPC is "
        "deleted. If we attached to an existing cluster, only the K8s objects we "
        "created and the IRSA + (CreateNew) Secrets Manager resources go away.",
        default=False,
    ):
        info("Aborted.")
        return

    # 1. Delete the K8s objects first — needed when we're attaching to an
    #    existing cluster (so the LB Service hostname releases cleanly).
    #    We only attempt this when we know the kube context that was
    #    used during deploy. A bare-stack-name destroy skips this step.
    context = state.get("k8s_context")
    namespace = state.get("namespace", DEFAULT_NAMESPACE)
    if context and shutil.which("kubectl"):
        info(f"Deleting K8s resources in namespace {namespace}...")
        run_kubectl(
            ["delete", "namespace", namespace, "--ignore-not-found=true", "--wait=true"],
            context=context,
            check=False,
        )

    # 2. Delete the CloudFormation stack.
    cfn = sess.client("cloudformation")
    info(f"Deleting stack {stack_name}...")
    cfn.delete_stack(StackName=stack_name)
    final = wait_for_stack(
        sess, stack_name, operation="delete", timeout_min=60
    )
    if final == "DELETE_COMPLETE":
        STATE_FILE.unlink(missing_ok=True)
        rendered = SCRIPT_DIR / ".rendered-manifests"
        if rendered.exists():
            for f in rendered.iterdir():
                f.unlink()
            rendered.rmdir()
        ok("Tear-down complete; state file + rendered manifests removed.")
    else:
        die(f"Stack delete ended in {final} — manual cleanup may be required.")


def cmd_configure(args: argparse.Namespace) -> None:
    """Re-write MCP client configs without touching AWS — handy after re-installing
    a client on a new machine or rotating an API key."""
    state = load_state()
    if not state:
        die("No state file. Run `deploy` first.")
    mcp_url = state.get("mcp_url")
    if not mcp_url:
        die("State file has no MCP URL recorded.")

    # Rebuild headers from .env (basic auth in zscaler mode requires creds we
    # don't store in the state file for security reasons).
    env_file = resolve_env_file_path(args.env_file, non_interactive=False)
    env = load_env_file(env_file) if env_file else {}
    headers = _build_auth_headers(
        state.get("auth_mode", "zscaler"),
        zscaler_client_id=env.get("ZSCALER_CLIENT_ID", ""),
        zscaler_client_secret=env.get("ZSCALER_CLIENT_SECRET", ""),
        api_key=env.get("ZSCALER_MCP_AUTH_API_KEY", ""),
    )
    server_name = state.get("server_name", DEFAULT_SERVER_NAME)

    installed = [a for a in AGENTS if a["installed_fn"]()]
    if not installed:
        die("No supported MCP clients detected on this machine.")

    print("Detected MCP clients:")
    for i, a in enumerate(installed, 1):
        print(f"  {i:>2}. {a['name']}")
    raw = input(
        "Configure which? (comma-separated numbers, 'all', or empty to skip): "
    ).strip().lower()
    if raw == "all":
        selected = [a["id"] for a in installed]
    elif raw:
        try:
            picks = [int(p) for p in raw.replace(" ", "").split(",")]
            selected = [installed[p - 1]["id"] for p in picks if 1 <= p <= len(installed)]
        except (ValueError, IndexError):
            die("Invalid selection.")
    else:
        info("No clients selected.")
        return

    written = configure_clients(server_name, mcp_url, headers, selected)
    state["configured_clients"] = {**state.get("configured_clients", {}), **written}
    save_state(state)
    ok(f"Configured {len(written)} client(s).")


# ════════════════════════════════════════════════════════════════════════
#  main
# ════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eks_mcp_operations.py",
        description="Deploy & manage the Zscaler MCP Server on AWS EKS.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_deploy = sub.add_parser(
        "deploy",
        help="Deploy a new stack OR push an in-place update (auto-detected "
             "via state file). Both the CFN stack and the K8s manifests are "
             "updated.",
    )
    p_deploy.add_argument("--env-file", help="Path to a .env / env.properties file.")
    p_deploy.add_argument("--non-interactive", action="store_true",
                          help="Never prompt; rely on env vars (CI mode).")
    p_deploy.add_argument(
        "--fresh", action="store_true",
        help="Ignore any existing state file and prompt as if it were a "
             "first-time deploy. Use this only when the prior stack was "
             "destroyed out-of-band (e.g. via the CFN console) and the "
             "state file is stale.",
    )
    p_deploy.add_argument("--skip-client-config", action="store_true",
                          help="Skip auto-configuring local MCP clients.")
    p_deploy.set_defaults(func=cmd_deploy)

    p_status = sub.add_parser("status", help="Show stack + Pod + Service state.")
    p_status.set_defaults(func=cmd_status)

    p_logs = sub.add_parser("logs", help="Stream Pod logs (kubectl logs).")
    p_logs.add_argument("-f", "--follow", action="store_true",
                        help="Pass -f to kubectl logs.")
    p_logs.add_argument("--tail", type=int, default=None,
                        help="Only show the last N log lines.")
    p_logs.set_defaults(func=cmd_logs)

    p_kubectl = sub.add_parser(
        "kubectl",
        help="Pass-through to kubectl with the cluster context preset.",
    )
    p_kubectl.add_argument("kubectl_args", nargs=argparse.REMAINDER,
                            help="Args forwarded to kubectl (use `--` to separate).")
    p_kubectl.set_defaults(func=cmd_kubectl)

    p_rotate = sub.add_parser(
        "rotate-secrets",
        help="Re-fetch creds from Secrets Manager and roll the Deployment.",
    )
    p_rotate.set_defaults(func=cmd_rotate_secrets)

    p_destroy = sub.add_parser("destroy", help="Tear down K8s manifests + the CFN stack.")
    p_destroy.add_argument("-y", "--yes", action="store_true",
                           help="Skip the confirmation prompt.")
    p_destroy.add_argument(
        "--stack-name", default=None,
        help="Override the CFN stack name. Defaults to the state-file "
             "value or DEFAULT_STACK. Useful when the state file is "
             "missing because a previous deploy crashed early.",
    )
    p_destroy.add_argument(
        "--region", default=None,
        help="Override the AWS region. Defaults to the state-file value, "
             "AWS_REGION env var, or DEFAULT_REGION.",
    )
    p_destroy.set_defaults(func=cmd_destroy)

    p_config = sub.add_parser("configure",
                              help="Re-write MCP client configs without redeploying.")
    p_config.add_argument("--env-file", help="Path to a .env / env.properties file.")
    p_config.set_defaults(func=cmd_configure)

    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        info("Interrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
