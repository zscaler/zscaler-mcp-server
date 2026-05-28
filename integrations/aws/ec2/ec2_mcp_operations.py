#!/usr/bin/env python3
"""Zscaler MCP Server — AWS EC2 deployment & lifecycle.

Sibling of ``integrations/aws/ecs-fargate/ecs_fargate_mcp_operations.py``.
Where that script runs the MCP server as a container on ECS-Fargate, **this**
script installs the ``zscaler-mcp-server`` Python package straight from PyPI
onto an Amazon Linux 2023 EC2 instance, manages it via systemd, and fronts it
with an Application Load Balancer with an ACM TLS certificate — same public
HTTPS topology, no container runtime needed.

Topology::

    User / MCP client  ─────►  ALB (TLS @ 443)
                                   │
                                   ▼
                            EC2 instance  ──►  Zscaler OneAPI
                            (AL2023 + systemd + pip-installed package)

Commands:
    deploy      Build asset bucket, upload nested templates, launch root stack
    status      Show stack status, MCP URL, ALB DNS, instance + target health
    logs        Tail the CloudWatch log group
    ssh         Open an interactive SSM Session Manager shell to the instance
    destroy     Reverse-order tear-down (CFN delete-stack)
    configure   (Re)write MCP client configs without touching AWS

All credential / VPC / TLS / auth choices are gathered interactively from a
``.env`` file plus prompts. The script never embeds your secrets in the
CloudFormation template parameters — credentials are placed into Secrets
Manager and the EC2 launcher pulls them at boot via the instance role.
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
_TAGLINE = "AWS EC2 Deployment"


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
STATE_FILE = SCRIPT_DIR / ".aws-deploy-state.json"
NESTED_TEMPLATES = ["network.yaml", "iam.yaml", "secrets.yaml", "instance.yaml"]
ROOT_TEMPLATE = "zscaler-mcp-root.yaml"

DEFAULT_REGION = "us-east-1"
DEFAULT_STACK = "zscaler-mcp-ec2"
DEFAULT_PREFIX = "zscaler-mcp"
DEFAULT_INSTANCE_TYPE = "t3.small"
DEFAULT_SERVER_NAME = "zscaler-mcp-aws-ec2"

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
    CFN stack. Without this, a Ctrl-C or a nested-stack failure during the
    long ``wait_for_stack`` poll would orphan the stack — the user would
    have no state file and ``destroy`` would refuse to run.
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


def _apply_state_for_redeploy(state: dict[str, Any], env: dict[str, str]) -> None:
    """Pre-populate ``env`` from saved state so a re-deploy is friction-free.

    Mirrors the ECS-Fargate behaviour: a re-deploy against an existing stack
    treats region / stack-name / prefix / network-mode as LOCKED (CFN can't
    swap these without a destroy), credentials as forced UseExisting (the
    Secrets Manager secret already exists), and TLS/auth-mode as soft
    defaults that ``.env`` can still override. See the matching helper in
    ``ecs_fargate_mcp_operations.py`` for the full rationale; the EC2
    variant has the same semantics minus the image URI (PyPI install path,
    no container image to pin).
    """
    if state.get("region"):
        env["AWS_REGION"] = state["region"]
    if state.get("stack_name"):
        env["AWS_STACK_NAME"] = state["stack_name"]
    if state.get("prefix"):
        env["AWS_RESOURCE_NAME_PREFIX"] = state["prefix"]
    if state.get("network_mode"):
        env["AWS_NETWORK_MODE"] = state["network_mode"]
    if state.get("secret_arn"):
        env["ZSCALER_SECRET_NAME"] = state["secret_arn"]
    if state.get("tls_mode"):
        env.setdefault("AWS_TLS_MODE", state["tls_mode"])
    if state.get("auth_mode"):
        env.setdefault("ZSCALER_MCP_AUTH_MODE", state["auth_mode"])
    if state.get("server_name"):
        env.setdefault("MCP_SERVER_NAME", state["server_name"])


def _dump_recent_instance_logs(
    sess: boto3.Session,
    log_group: str,
    *,
    streams: int = 3,
    lines_per_stream: int = 40,
) -> None:
    """Surface the EC2 instance's stdout inline on deploy failure.

    The CloudWatch Agent on the EC2 instance ships ``/var/log/cloud-init-
    output.log`` and the ``zscaler-mcp.service`` systemd journal to
    ``/aws/ec2/<prefix>``. When the stack fails (cloud-init crash, systemd
    service refuses to start, ALB target health-check timeout), dumping the
    last few log entries inline saves the operator from manually finding
    the right ``aws logs tail`` invocation or having to ``ssh`` into a
    not-yet-fully-booted instance.

    Best-effort: silent no-op when the log group doesn't exist yet (the
    CloudWatch Agent itself failed to install, which we surface via the
    explicit "log group does not exist" branch).
    """
    try:
        logs = sess.client("logs")
        resp = logs.describe_log_streams(
            logGroupName=log_group,
            orderBy="LastEventTime",
            descending=True,
            limit=streams,
        )
        stream_names = [s["logStreamName"] for s in resp.get("logStreams", [])]
        if not stream_names:
            info(
                f"No log streams yet in {log_group} — the CloudWatch Agent "
                "may not have started shipping (cloud-init still running, "
                "or the agent itself failed to install). SSH into the "
                "instance for /var/log/cloud-init-output.log."
            )
            return
        print()
        info(f"Last instance logs from {log_group}:")
        print("  " + "─" * 72)
        for name in stream_names:
            try:
                events = logs.get_log_events(
                    logGroupName=log_group,
                    logStreamName=name,
                    limit=lines_per_stream,
                    startFromHead=False,
                ).get("events", [])
            except ClientError:
                continue
            if not events:
                continue
            print(f"  ── stream: {name} ─")
            for ev in events:
                line = ev.get("message", "").rstrip()
                if line:
                    print(f"  {line}")
        print("  " + "─" * 72)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "LogGroupNotFound"):
            info(
                f"Log group {log_group} does not exist — the CloudWatch "
                "Agent never started shipping. SSH into the instance: "
                f"`python {Path(__file__).name} ssh` then `journalctl -u "
                "zscaler-mcp -n 80` or `cat /var/log/cloud-init-output.log`."
            )
        else:
            warn(f"Could not fetch instance logs ({code}): {exc}")
    except Exception as exc:  # noqa: BLE001
        warn(f"Could not fetch instance logs: {exc}")


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        warn(f"State file {STATE_FILE} is corrupt; ignoring.")
        return {}


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
    # the wire in cleartext. The EC2 deployment's `TlsMode=None` path
    # (demo / PoC only) lands on an ALB HTTP listener with no certificate —
    # without --allow-http, Claude Desktop / Claude Code / Windsurf fail
    # with `Error: Non-HTTPS URLs are only allowed for localhost or when
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
#  Deploy
# ════════════════════════════════════════════════════════════════════════


def cmd_deploy(args: argparse.Namespace) -> None:
    print_zscaler_logo()
    step("1/6  Configuration")

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
                "as defaults — check the CFN console first if the "
                "previous stack is in a CREATE_FAILED state."
            )
        else:
            ok(
                f"Found existing deployment "
                f"(stack={existing_state.get('stack_name', '?')}, "
                f"region={existing_state.get('region', '?')}). "
                "Re-using saved values — CFN will run an in-place update."
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

    # ── 2. Resolve credentials, network, TLS, auth, capacity ──────────
    step("2/6  Credentials & networking")
    creds = resolve_credentials(sess, env, args.non_interactive)
    network = resolve_network(sess, env, args.non_interactive)
    tls = resolve_tls(sess, env, args.non_interactive)
    auth = resolve_auth(env, args.non_interactive)

    # EC2-specific knobs: instance type + optional SSH access. We push SSM
    # Session Manager as the default access pattern (no inbound 22 needed).
    instance_type = env.get("AWS_INSTANCE_TYPE", "").strip() or DEFAULT_INSTANCE_TYPE
    ssh_cidr = env.get("AWS_SSH_INGRESS_CIDR", "").strip()
    key_pair = env.get("AWS_KEY_PAIR_NAME", "").strip()
    if not args.non_interactive:
        instance_type = prompt("EC2 instance type", default=instance_type)
        info(
            "SSH access (optional). Leave blank to skip — the instance is "
            "registered with AWS SSM Session Manager so you can shell into "
            "it with no inbound 22 needed."
        )
        ssh_cidr = prompt(
            "SSH ingress CIDR (or empty for SSM-only)",
            default=ssh_cidr or "",
            allow_empty=True,
        )
        if ssh_cidr:
            key_pair = prompt(
                "EC2 key-pair NAME (the resource name, NOT the .pem file path)",
                default=key_pair or None,
            )

    # Normalize + pre-flight the key pair. EC2 key-pair resources have no
    # file extension; the .pem is the local private-key file. Operators
    # routinely paste in the local file name (or sometimes the full path),
    # then lose ~6 minutes to a CFN "key pair does not exist" rollback.
    # Strip the common extensions and verify with describe-key-pairs before
    # we ever submit the stack.
    if key_pair:
        original_key_pair = key_pair
        # Strip a path prefix if pasted in (e.g. ./SGIO-us-east-1-KeyPair.pem)
        key_pair = Path(key_pair).name
        # Strip the common private-key file extensions.
        for ext in (".pem", ".cer", ".crt", ".key"):
            if key_pair.lower().endswith(ext):
                key_pair = key_pair[: -len(ext)]
                break
        if key_pair != original_key_pair:
            info(
                f"Normalized key-pair name: {original_key_pair!r} → {key_pair!r} "
                "(EC2 key-pair resources have no file extension)."
            )
        # Verify it exists before submitting the stack — fails in <1s instead
        # of after a ~6 minute CFN CREATE → ROLLBACK round trip.
        try:
            sess.client("ec2").describe_key_pairs(KeyNames=[key_pair])
            ok(f"Key pair {key_pair!r} exists in {sess.region_name}.")
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "InvalidKeyPair.NotFound":
                # Show what IS available so the operator can self-correct
                # without context-switching to the console.
                try:
                    available = [
                        kp["KeyName"]
                        for kp in sess.client("ec2").describe_key_pairs().get("KeyPairs", [])
                    ]
                except ClientError:
                    available = []
                die(
                    f"Key pair {key_pair!r} not found in region "
                    f"{sess.region_name}. Available key pairs: "
                    f"{available or '(none)'}. "
                    "Set AWS_KEY_PAIR_NAME in .env to a name from the list "
                    "(no .pem extension) or leave AWS_SSH_INGRESS_CIDR blank "
                    "to skip SSH entirely (the instance is reachable via "
                    "SSM Session Manager regardless)."
                )
            die(f"Could not verify key pair {key_pair!r}: {exc}")

    # MCP feature flags (passed through as-is from .env)
    flags = {
        "WriteToolsEnabled": env.get("ZSCALER_MCP_WRITE_ENABLED", "false"),
        "WriteToolsAllowlist": env.get("ZSCALER_MCP_WRITE_TOOLS", ""),
        "DisabledTools": env.get("ZSCALER_MCP_DISABLED_TOOLS", ""),
        "DisabledServices": env.get("ZSCALER_MCP_DISABLED_SERVICES", ""),
        "Toolsets": env.get("ZSCALER_MCP_TOOLSETS", ""),
        "DisabledToolsets": env.get("ZSCALER_MCP_DISABLED_TOOLSETS", ""),
        "EnableToolCallLogging": env.get("ZSCALER_MCP_LOG_TOOL_CALLS", "true"),
        "InstanceType": instance_type,
        "SshIngressCidr": ssh_cidr,
        "KeyPairName": key_pair,
        "ContainerPort": str(env.get("AWS_MCP_PORT", "8000")),
        "LogRetentionDays": str(env.get("AWS_LOG_RETENTION_DAYS", "14")),
    }

    # ── 3. Confirm summary ─────────────────────────────────────────────
    step("3/6  Review")
    print(f"  Stack:          {stack_name}")
    print(f"  Region:         {region}")
    print(f"  Account:        {account}")
    print(f"  Asset bucket:   {bucket}")
    print(f"  Credentials:    {creds['CredentialSource']}"
          + (f" ({creds.get('ExistingSecretName')})" if creds["CredentialSource"] == "UseExisting" else ""))
    print(f"  Network:        {network['NetworkMode']}"
          + (f" (VPC {network['ExistingVpcId']})" if network["NetworkMode"] == "UseExisting" else f" ({network['NewVpcCidr']})"))
    print(f"  TLS:            {tls['TlsMode']}"
          + (f" ({tls['DomainName']})" if tls["TlsMode"] == "AcmManaged" else ""))
    print(f"  MCP auth:       {auth['McpAuthMode']}")
    print(f"  Instance type:  {flags['InstanceType']}")
    print(
        "  Access:         "
        + (
            "SSH from " + flags["SshIngressCidr"] + " + SSM"
            if flags["SshIngressCidr"]
            else "SSM Session Manager only"
        )
    )

    if not args.non_interactive and not prompt_bool(
        "\nProceed with deployment?", default=True
    ):
        info("Aborted by user.")
        return

    # ── 4. Asset bucket + nested-template upload ───────────────────────
    step("4/6  Upload CloudFormation assets")
    ensure_asset_bucket(sess, bucket)
    prefix_key = upload_nested_templates(sess, bucket, "zscaler-mcp/")

    # ── 5. Stack create/update ─────────────────────────────────────────
    step("5/6  CloudFormation deploy")
    cfn = sess.client("cloudformation")
    params: list[dict] = [
        {"ParameterKey": "AssetBucket",      "ParameterValue": bucket},
        {"ParameterKey": "AssetPrefix",      "ParameterValue": prefix_key},
        {"ParameterKey": "ResourceNamePrefix", "ParameterValue": prefix},
    ]
    for d in (creds, network, tls, auth, flags):
        for k, v in d.items():
            params.append({"ParameterKey": k, "ParameterValue": str(v)})

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
                {"Key": "Deployment", "Value": "ec2"},
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
    # 30+ minutes and the user might Ctrl-C, the script may crash, or
    # the stack may end up CREATE_FAILED. In any of those cases,
    # `destroy` needs to know the stack name and region to clean up.
    log_group_name = f"/aws/ec2/{prefix}"
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
                "network_mode": network["NetworkMode"],
                "tls_mode": tls["TlsMode"],
                "auth_mode": auth["McpAuthMode"],
                "log_group": log_group_name,
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
            # Best-effort: surface the EC2 instance's stdout/cloud-init log
            # inline so the operator sees the real error instead of just
            # "ServiceTls CREATE_FAILED" from CloudFormation.
            _dump_recent_instance_logs(sess, log_group_name)
            console_url = (
                f"https://{region}.console.aws.amazon.com/cloudformation/home"
                f"?region={region}#/stacks?filteringText={stack_name}"
            )
            info(f"Inspect the failed stack in the CFN console: {console_url}")
            info(
                f"Tail more logs:  python {Path(__file__).name} logs --since 60"
            )
            info(
                f"Run `python {Path(__file__).name} destroy` to clean it up "
                f"before re-deploying."
            )
            die(f"Stack deploy failed: {final}")

    # ── 6. Configure clients + summary ─────────────────────────────────
    step("6/6  Configure MCP clients")
    outputs = stack_outputs(sess, stack_name)
    mcp_url = outputs.get("McpUrl", "")
    if not mcp_url:
        warn("Stack didn't expose McpUrl. Skipping client configuration.")
        return

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
            "secret_name": outputs.get("SecretName", ""),
            "network_mode": network["NetworkMode"],
            "vpc_id": outputs.get("VpcId", ""),
            "tls_mode": tls["TlsMode"],
            "mcp_url": mcp_url,
            "auth_mode": auth["McpAuthMode"],
            "log_group": outputs.get("LogGroupName", ""),
            "instance_id": outputs.get("InstanceId", ""),
            "instance_type": flags["InstanceType"],
            "alb_dns": outputs.get("AlbDnsName", ""),
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
    print()
    bar = "═" * 72
    print(_ansi("1;32", bar))
    print(_ansi("1;32", "  ✓  Zscaler MCP Server deployed on AWS EC2"))
    print(_ansi("1;32", bar))
    print()
    print(f"  Stack name:     {stack_name}")
    print(f"  Region:         {region}")
    print(f"  Instance ID:    {outputs.get('InstanceId', '(unknown)')}")
    print(f"  ALB DNS:        {outputs.get('AlbDnsName', '(unknown)')}")
    if outputs.get("VpcId"):
        print(f"  VPC:            {outputs['VpcId']}")
    if outputs.get("LogGroupName"):
        print(f"  Log group:      {outputs['LogGroupName']}")
    if outputs.get("SecretName"):
        print(f"  Secret:         {outputs['SecretName']}")
    print()
    print(_ansi("1;36", "  Publicly accessible MCP URL"))
    print(_ansi("1;36", "  ──────────────────────────"))
    print(f"  {_ansi('1;33', outputs.get('McpUrl', '(unknown)'))}")
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
    print("    • Tail logs:    python ec2_mcp_operations.py logs -f")
    print("    • Stack status: python ec2_mcp_operations.py status")
    print("    • SSM shell:    python ec2_mcp_operations.py ssh")
    print("    • Tear down:    python ec2_mcp_operations.py destroy")
    print()
    info(
        "Bootstrapping the instance (pip install + systemd start) takes "
        "another 60-180 seconds after the stack reports CREATE_COMPLETE. "
        "Run `status` to see when the ALB target reports healthy."
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

    instance_id = outputs.get("InstanceId") or state.get("instance_id")
    if instance_id:
        try:
            ec2 = sess.client("ec2")
            r = ec2.describe_instances(InstanceIds=[instance_id])
            for res in r["Reservations"]:
                for inst in res["Instances"]:
                    print()
                    print(
                        f"  EC2 state:      {inst['State']['Name']:<14}"
                        f"({inst.get('InstanceType', '?')}, {inst.get('PrivateIpAddress', '?')})"
                    )
                    reason = inst.get("StateTransitionReason", "")
                    if reason:
                        print(f"  Transition:     {reason}")
        except ClientError as e:
            warn(f"Could not describe EC2 instance: {e}")

    # ALB target health — the authoritative answer to "is the MCP server up?"
    if outputs.get("AlbDnsName"):
        try:
            elbv2 = sess.client("elbv2")
            albs = elbv2.describe_load_balancers(
                Names=[f"{state.get('prefix', 'zscaler-mcp')}-alb"]
            )["LoadBalancers"]
            if albs:
                tgs = elbv2.describe_target_groups(
                    LoadBalancerArn=albs[0]["LoadBalancerArn"]
                )["TargetGroups"]
                for tg in tgs:
                    health = elbv2.describe_target_health(
                        TargetGroupArn=tg["TargetGroupArn"]
                    )["TargetHealthDescriptions"]
                    if health:
                        print()
                        print(f"  ALB target health ({tg['TargetGroupName']}):")
                        for h in health:
                            state_name = h["TargetHealth"]["State"]
                            color2 = "32" if state_name == "healthy" else (
                                "33" if state_name == "initial" else "31"
                            )
                            reason = h["TargetHealth"].get("Reason", "")
                            print(
                                f"    {h['Target']['Id']:<22} "
                                f"{_ansi(color2, state_name):<20}{reason}"
                            )
        except ClientError as e:
            warn(f"Could not query ALB target health: {e}")


def _ssm_plugin_install_hint() -> str:
    """OS-specific install instructions for the AWS Session Manager plugin.

    The plugin is its own binary outside the AWS CLI itself — installing
    awscli does NOT install it. We surface this up-front because the
    failure mode otherwise is a single line directing the operator to a
    docs page, which then sends them back here to figure out why we picked
    SSM over plain SSH in the first place.
    """
    plat = sys.platform
    if plat == "darwin":
        return (
            "Install on macOS:\n"
            "    brew install --cask session-manager-plugin"
        )
    if plat.startswith("linux"):
        return (
            "Install on Ubuntu/Debian:\n"
            "    curl 'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb' -o sm.deb\n"
            "    sudo dpkg -i sm.deb\n"
            "Install on Amazon Linux / RHEL:\n"
            "    sudo dnf install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm"
        )
    if plat.startswith("win"):
        return (
            "Install on Windows (PowerShell):\n"
            "    Invoke-WebRequest 'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe' -OutFile SessionManagerPluginSetup.exe\n"
            "    .\\SessionManagerPluginSetup.exe"
        )
    return (
        "See https://docs.aws.amazon.com/systems-manager/latest/userguide/"
        "session-manager-working-with-install-plugin.html"
    )


def cmd_ssh(args: argparse.Namespace) -> None:
    """Open an SSM Session Manager shell to the instance.

    SSM, not plain SSH-over-port-22, is deliberate: the EC2 instance lives
    in a *private* subnet (no public IP, no inbound 22 from the internet,
    no bastion). SSM gives the same SSH UX without any of the attack
    surface — no key files to rotate, no IP allowlists to maintain, every
    session audited in CloudTrail. The trade-off is that the client needs
    the Session Manager plugin installed alongside the AWS CLI. We
    pre-flight that here so the failure mode is a clear install hint
    rather than the plugin's own docs URL.
    """
    state = load_state()
    if not state:
        die("No state file. Run `deploy` first.")
    instance_id = state.get("instance_id")
    if not instance_id:
        die("State file has no instance ID recorded.")
    region = state["region"]

    if shutil.which("aws") is None:
        die(
            "The AWS CLI is required for `ssh` (we shell out to "
            "`aws ssm start-session`). Install it from "
            "https://aws.amazon.com/cli/ — or use `python ec2_mcp_operations.py "
            "logs --stream mcp` for service logs without needing CLI access."
        )

    # session-manager-plugin is a separate binary from the AWS CLI. The
    # CLI installer does NOT pull it in. Detect it up front; if it's
    # missing the AWS CLI's own error message just points at a docs URL
    # without telling the operator what to actually install.
    if shutil.which("session-manager-plugin") is None:
        die(
            "The AWS Session Manager plugin is not installed (the EC2 "
            "instance is in a private subnet, so SSM is the only path "
            "in — there is no public IP for plain SSH).\n\n"
            f"{_ssm_plugin_install_hint()}\n\n"
            "After installing, re-run `python ec2_mcp_operations.py ssh`.\n\n"
            "If you only need to inspect MCP service logs (and not poke "
            "around on the box), `python ec2_mcp_operations.py logs "
            "--stream mcp -f` reads them straight from CloudWatch with no "
            "plugin required."
        )

    info(f"Connecting to {instance_id} via SSM Session Manager...")
    cmd = ["aws", "--region", region, "ssm", "start-session", "--target", instance_id]
    os.execvp("aws", cmd)


# Map ``--stream`` shorthand to the CloudWatch Agent stream prefix declared
# in cloudformation/instance.yaml's amazon-cloudwatch-agent.json. Keep these
# in lockstep with that template — operators rely on this default to see
# MCP service output first ("logs -f" should Just Work after a successful
# deploy), and "all" remains the escape hatch for cross-stream debugging.
_LOG_STREAM_PREFIXES: dict[str, str | None] = {
    "mcp": "mcp-server-",
    "bootstrap": "bootstrap-",
    "system": "system-",
    "all": None,
}


def cmd_logs(args: argparse.Namespace) -> None:
    """Tail the EC2 instance's CloudWatch log group via boto3.

    Pure boto3 (no ``aws logs tail`` shell-out) so the command works on
    AWS CLI v1, v2, and machines without the CLI installed. boto3 is
    already a hard dependency, so this path has zero new requirements.

    ``--stream`` (default ``mcp``) narrows the read to one of the three
    streams shipped by the on-instance CloudWatch Agent. The MCP service
    output is the one operators care about 95% of the time, so we surface
    it as the default — bootstrap and system messages are reachable via
    explicit opt-in, and ``--stream all`` keeps the prior interleaved
    behaviour for cross-stream debugging.
    """
    state = load_state()
    if not state:
        die("No state file. Run `deploy` first.")
    log_group = state.get("log_group")
    if not log_group:
        die("State file has no log group recorded.")
    region = state["region"]

    stream_choice = getattr(args, "stream", "mcp") or "mcp"
    if stream_choice not in _LOG_STREAM_PREFIXES:
        die(
            f"Unknown --stream value {stream_choice!r}. "
            f"Choose one of: {', '.join(_LOG_STREAM_PREFIXES)}."
        )
    stream_prefix = _LOG_STREAM_PREFIXES[stream_choice]

    sess = get_session(region, profile=os.environ.get("AWS_PROFILE"))
    logs = sess.client("logs")

    since_min = max(int(getattr(args, "since", 30) or 30), 1)
    start_ms = int((time.time() - since_min * 60) * 1000)

    scope = (
        f"stream={stream_choice} (prefix={stream_prefix})"
        if stream_prefix
        else "all streams"
    )
    info(
        f"Reading {log_group} (region={region}, {scope}, since={since_min}m)"
        + (" — follow mode, Ctrl-C to exit" if args.follow else "")
    )

    def _emit(events: list[dict]) -> int:
        latest_ts = 0
        for ev in events:
            ts_ms = ev.get("timestamp", 0)
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            stream = ev.get("logStreamName", "")
            msg = ev.get("message", "").rstrip()
            print(f"{ts}Z  {stream}  {msg}")
            latest_ts = max(latest_ts, ts_ms)
        return latest_ts

    saw_any_event = False
    try:
        token: str | None = None
        last_ts = start_ms
        while True:
            params: dict = {
                "logGroupName": log_group,
                "startTime": last_ts,
                "interleaved": True,
                "limit": 1000,
            }
            if stream_prefix:
                params["logStreamNamePrefix"] = stream_prefix
            if token:
                params["nextToken"] = token
            try:
                resp = logs.filter_log_events(**params)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in ("ResourceNotFoundException",):
                    warn(
                        f"Log group {log_group} does not exist yet. "
                        "Either the CloudWatch Agent hasn't started shipping "
                        "logs, or the deploy is still in flight."
                    )
                    return
                raise

            events = resp.get("events", [])
            if events:
                saw_any_event = True
                latest = _emit(events)
                if latest:
                    last_ts = latest + 1

            token = resp.get("nextToken")
            if token:
                continue

            if not args.follow:
                # One-shot mode — if we asked for the MCP service stream and
                # got nothing, almost always either (a) the CW Agent on an
                # older instance was built before this stream existed, or
                # (b) the service hasn't logged anything yet. Give a hint
                # instead of leaving the operator staring at silence.
                if not saw_any_event and stream_choice == "mcp":
                    warn(
                        "No events on the 'mcp-server-*' stream yet. If this "
                        "instance was deployed before the MCP-server log "
                        "stream was added to the CloudWatch Agent config, "
                        "re-run `python ec2_mcp_operations.py deploy` to push "
                        "the updated template (CFN will replace the instance "
                        "and the new stream will appear). To browse other "
                        "streams in the meantime, retry with `--stream "
                        "bootstrap` or `--stream all`."
                    )
                return
            time.sleep(2)
    except KeyboardInterrupt:
        info("Stopped.")


def cmd_destroy(args: argparse.Namespace) -> None:
    """Tear down the deployment.

    Resilient to missing or partial state: a failed deploy writes a
    partial-state file early (see ``save_partial_state``) so this command
    can still find the stack name. When no state exists at all (state
    file wiped, or deploy crashed before the first partial-state write),
    we fall back to ``DEFAULT_STACK`` / ``DEFAULT_REGION`` and let the
    operator override via ``--stack-name`` / ``--region``.
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
            f"Override with --stack-name / --region if needed."
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
        f"Delete stack {stack_name} in {region}? "
        "This removes the ALB, EC2 instance, IAM roles, VPC (if we created it), "
        "and (if CredentialSource=CreateNew) the Secrets Manager secret.",
        default=False,
    ):
        info("Aborted.")
        return
    cfn = sess.client("cloudformation")
    info(f"Deleting stack {stack_name}...")
    cfn.delete_stack(StackName=stack_name)
    final = wait_for_stack(sess, stack_name, operation="delete", timeout_min=45)
    if final == "DELETE_COMPLETE":
        STATE_FILE.unlink(missing_ok=True)
        ok("Tear-down complete; state file removed.")
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
        prog="ec2_mcp_operations.py",
        description="Deploy & manage the Zscaler MCP Server on AWS EC2.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_deploy = sub.add_parser(
        "deploy",
        help="Deploy a new stack OR push an in-place update to an existing one "
             "(auto-detected via state file).",
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

    p_status = sub.add_parser("status", help="Show stack + EC2 + ALB target health.")
    p_status.set_defaults(func=cmd_status)

    p_logs = sub.add_parser(
        "logs",
        help="Tail the CloudWatch log group (boto3, AWS CLI not required).",
    )
    p_logs.add_argument(
        "-f", "--follow", action="store_true",
        help="Keep polling and print new events as they arrive (Ctrl-C to stop).",
    )
    p_logs.add_argument(
        "--since", type=int, default=30, metavar="MINUTES",
        help="How many minutes of history to dump on first poll (default: 30).",
    )
    p_logs.add_argument(
        "--stream",
        choices=sorted(_LOG_STREAM_PREFIXES),
        default="mcp",
        help=(
            "Which on-instance log stream to read: 'mcp' = MCP service "
            "stdout/stderr (default — what you usually want), 'bootstrap' = "
            "cloud-init / pip-install output, 'system' = /var/log/messages, "
            "'all' = interleave every stream in the log group."
        ),
    )
    p_logs.set_defaults(func=cmd_logs)

    p_ssh = sub.add_parser("ssh", help="Open SSM Session Manager shell to the instance.")
    p_ssh.set_defaults(func=cmd_ssh)

    p_destroy = sub.add_parser("destroy", help="Tear down the MCP stack.")
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
