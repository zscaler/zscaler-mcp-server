#!/usr/bin/env python3
"""
Zscaler MCP Server — Kubernetes (Helm) Deployment (Interactive)

Fully interactive deployment script for the zscaler-mcp-server Helm chart
shipped under integrations/helm-chart/charts/zscaler-mcp-server/.

Follows the same pattern as integrations/google/gcp/gcp_mcp_operations.py
and integrations/azure/azure_mcp_operations.py:

  - Prompts the user for namespace, release name, image tag, and exposure
    mode (port-forward vs. Ingress)
  - Builds the Kubernetes Secret directly from the user's existing .env
    via `kubectl create secret --from-env-file=...` — no value translation
    into values.yaml required
  - Installs/upgrades the chart with the right --set overrides
  - Waits for the Deployment rollout to finish before declaring success
  - Starts kubectl port-forward in the background (when no Ingress is
    configured) so the MCP endpoint is immediately reachable on localhost
  - Updates Claude Desktop and Cursor configs with the correct
    Authorization header
  - Persists deployment state in .helm-deploy-state.json so destroy /
    status / logs / configure / test know which release to target

Supported MCP client authentication modes:
  - JWT        — Server validates Bearer tokens against a JWKS endpoint
  - API Key    — Shared secret in the Authorization header
  - Zscaler    — OneAPI Basic-auth (default; the chart's primary path)
  - None       — No client auth (development only)

Credential resolution (first non-empty wins):
  1. Values from .env file (default: project-root .env)
  2. Interactive prompt for whatever's missing

Usage:
  python helm_mcp_operations.py deploy        # interactive guided deploy
  python helm_mcp_operations.py destroy       # uninstall + clean Secret
  python helm_mcp_operations.py status        # show release health
  python helm_mcp_operations.py logs          # tail Deployment logs
  python helm_mcp_operations.py configure     # refresh Cursor / Claude
  python helm_mcp_operations.py test          # run `helm test`

Requirements: kubectl, helm 3, a reachable Kubernetes cluster. No cloud
SDK is needed — the script is hyperscaler-agnostic.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
CHART_DIR = SCRIPT_DIR / "charts" / "zscaler-mcp-server"
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SYSTEM = platform.system()

SERVER_NAME = "zscaler-mcp-server"          # used in MCP client configs
CHART_RELEASE_DEFAULT = "zscaler-mcp"
NAMESPACE_DEFAULT = "zscaler-mcp"
DOCKER_HUB_IMAGE_REPO = "zscaler/zscaler-mcp-server"
DOCKER_HUB_IMAGE_TAG = "latest"

STATE_FILE = SCRIPT_DIR / ".helm-deploy-state.json"

LOCAL_PORT_DEFAULT = "8000"
SERVICE_PORT_DEFAULT = "80"

# ── ANSI colours ──────────────────────────────────────────────────────────

COLOURS = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
if COLOURS and SYSTEM == "Windows":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        COLOURS = False

RED = "\033[0;31m" if COLOURS else ""
GREEN = "\033[0;32m" if COLOURS else ""
YELLOW = "\033[1;33m" if COLOURS else ""
BLUE = "\033[0;34m" if COLOURS else ""
SKY_BLUE = "\033[34;01m" if COLOURS else ""
BOLD = "\033[1m" if COLOURS else ""
DIM = "\033[2m" if COLOURS else ""
NC = "\033[0m" if COLOURS else ""

_ZSCALER_ART = [
    "███████╗███████╗ ██████╗ █████╗ ██╗     ███████╗██████╗ ",
    "╚══███╔╝██╔════╝██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗",
    "  ███╔╝ ███████╗██║     ███████║██║     █████╗  ██████╔╝",
    " ███╔╝  ╚════██║██║     ██╔══██║██║     ██╔══╝  ██╔══██╗",
    "███████╗███████║╚██████╗██║  ██║███████╗███████╗██║  ██║",
    "╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
]
_TAGLINE = "Kubernetes (Helm) Deployment   |   Image source: Docker Hub"


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


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{NC}  {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{NC}    {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def error(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}")


def die(msg: str) -> None:
    error(msg)
    sys.exit(1)


# ── Subprocess helpers ────────────────────────────────────────────────────


def run_kubectl(
    args: list[str], *, check: bool = True, capture: bool = False, quiet: bool = False
) -> subprocess.CompletedProcess:
    cmd = ["kubectl"] + args
    if not quiet:
        info(f"  $ kubectl {' '.join(args[:8])}{'...' if len(args) > 8 else ''}")
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if check and r.returncode != 0:
            die(f"kubectl command failed:\n  {r.stderr.strip()}")
        return r
    r = subprocess.run(cmd)
    if check and r.returncode != 0:
        die(f"kubectl command failed (exit code {r.returncode})")
    return r


def run_helm(
    args: list[str], *, check: bool = True, capture: bool = False, quiet: bool = False
) -> subprocess.CompletedProcess:
    cmd = ["helm"] + args
    if not quiet:
        info(f"  $ helm {' '.join(args[:8])}{'...' if len(args) > 8 else ''}")
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if check and r.returncode != 0:
            die(f"helm command failed:\n  {r.stderr.strip()}")
        return r
    r = subprocess.run(cmd)
    if check and r.returncode != 0:
        die(f"helm command failed (exit code {r.returncode})")
    return r


def run_cmd(
    args: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    if capture:
        r = subprocess.run(args, capture_output=True, text=True)
        if check and r.returncode != 0:
            die(f"Command failed: {r.stderr.strip()}")
        return r
    r = subprocess.run(args)
    if check and r.returncode != 0:
        die(f"Command failed (exit code {r.returncode})")
    return r


def _require_binaries() -> None:
    for binary in ("kubectl", "helm"):
        if shutil.which(binary) is None:
            die(f"{binary} not found in PATH. Install it before running this script.")


# ── State helpers ─────────────────────────────────────────────────────────


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _clear_state() -> None:
    if STATE_FILE.is_file():
        STATE_FILE.unlink()


# ── .env helpers ──────────────────────────────────────────────────────────


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def resolve(env: dict[str, str], *keys: str) -> str:
    for key in keys:
        val = env.get(key, "").strip() or os.environ.get(key, "").strip()
        if val:
            return val
    return ""


# ── Config file helpers ───────────────────────────────────────────────────


def _claude_config_path() -> Path:
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


def _cursor_config_path() -> Path:
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json"
    return Path.home() / ".cursor" / "mcp.json"


CLAUDE_CONFIG = _claude_config_path()
CURSOR_CONFIG = _cursor_config_path()


def upsert_json_config(path: Path, updater) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if path.is_file():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}
    updater(config)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


# ── Interactive prompt helpers ────────────────────────────────────────────


def _prompt(label: str, *, default: str = "", secret: bool = False) -> str:
    display = f"  {label} [{default}]: " if default else f"  {label}: "
    while True:
        val = getpass.getpass(display) if secret else input(display)
        val = val.strip()
        if val:
            return val
        if default:
            return default
        error(f"  {label} is required.")


def _prompt_choice(title: str, options: list[tuple[str, str]]) -> str:
    print()
    print(f"  {BOLD}{title}{NC}")
    print()
    for idx, (_, label) in enumerate(options, 1):
        print(f"    [{idx}] {label}")
    print()
    while True:
        try:
            raw = input(f"  Choice [1-{len(options)}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            die("\nAborted.")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        error(f"  Invalid choice: {raw}")


def _prompt_yes_no(question: str, *, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {question} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


# ════════════════════════════════════════════════════════════════════════
#  Cluster / Helm helpers
# ════════════════════════════════════════════════════════════════════════


def _kubectl_context() -> str:
    r = run_kubectl(
        ["config", "current-context"], check=False, capture=True
    )
    return r.stdout.strip() if r.returncode == 0 else "(unknown)"


def _cluster_server_url(context: str) -> str:
    """Return the API server URL of `context`, or '' if it can't be resolved."""
    r = run_kubectl(
        [
            "config",
            "view",
            "--minify",
            "-o",
            f"jsonpath={{.clusters[?(@.name==\"{context}\")].cluster.server}}",
        ],
        check=False,
        capture=True,
    )
    return r.stdout.strip() if r.returncode == 0 else ""


def _assert_cluster_reachable(context: str) -> None:
    """Probe the API server. Fails fast with a friendly message if it's down.

    Hits /healthz with a 5-second request timeout. Any non-zero exit means
    the kubeconfig is pointing at something that can't answer — typical
    causes: kind/minikube cluster was stopped, Docker Desktop / Colima is
    off, VPN is disconnected, or the kubeconfig has expired creds.
    """
    info(f"Probing cluster reachability for context {BOLD}{context}{NC} …")
    r = run_kubectl(
        ["get", "--raw=/healthz", "--request-timeout=5s"],
        check=False,
        capture=True,
    )
    if r.returncode == 0:
        ok("Cluster is reachable.")
        return

    server = _cluster_server_url(context) or "(unknown — check your kubeconfig)"
    err_msg = (r.stderr or r.stdout or "").strip()
    error("Cluster API server is not reachable.")
    print(f"        Context:     {context}")
    print(f"        API server:  {server}")
    if err_msg:
        # Trim noisy "Unable to connect to the server:" prefix kubectl adds.
        clean = err_msg.replace("Unable to connect to the server:", "").strip()
        print(f"        kubectl says: {clean}")
    print()
    print("  Common causes:")
    print("    - kind / minikube cluster was stopped → `kind get clusters` / `minikube status`")
    print("    - Docker Desktop / Colima isn't running")
    print("    - You're disconnected from VPN that fronts the cluster")
    print("    - kubeconfig has expired credentials (re-auth with your cloud CLI)")
    print()
    print("  Fix the cluster, then re-run. Or switch context:")
    print(f"    {DIM}kubectl config get-contexts{NC}")
    print(f"    {DIM}kubectl config use-context <name>{NC}")
    die("Aborting — cluster unreachable.")


def _namespace_exists(namespace: str) -> bool:
    r = run_kubectl(
        ["get", "namespace", namespace], check=False, capture=True
    )
    return r.returncode == 0


def _secret_exists(namespace: str, name: str) -> bool:
    r = run_kubectl(
        ["-n", namespace, "get", "secret", name],
        check=False,
        capture=True,
    )
    return r.returncode == 0


def _release_exists(release: str, namespace: str) -> bool:
    r = run_helm(
        ["status", release, "-n", namespace, "-o", "json"],
        check=False,
        capture=True,
    )
    return r.returncode == 0


def _pod_phase_snapshot(namespace: str, release: str) -> list[dict]:
    """Return per-pod {name, phase, container_states, reasons, messages} for the release."""
    r = run_kubectl(
        [
            "-n",
            namespace,
            "get",
            "pods",
            "-l",
            f"app.kubernetes.io/instance={release}",
            "-o",
            "json",
        ],
        check=False,
        capture=True,
        quiet=True,
    )
    if r.returncode != 0:
        return []
    try:
        payload = json.loads(r.stdout)
    except json.JSONDecodeError:
        return []

    pods = []
    for item in payload.get("items", []):
        meta = item.get("metadata", {})
        status = item.get("status", {})
        reasons: list[str] = []
        messages: list[str] = []
        for cs in status.get("containerStatuses", []) or []:
            waiting = (cs.get("state") or {}).get("waiting") or {}
            if waiting.get("reason"):
                reasons.append(f"{cs.get('name')}: {waiting['reason']}")
                if waiting.get("message"):
                    messages.append(f"{cs.get('name')}: {waiting['message']}")
            terminated = (cs.get("state") or {}).get("terminated") or {}
            if terminated.get("reason"):
                reasons.append(f"{cs.get('name')}: {terminated['reason']} (exit {terminated.get('exitCode')})")
                if terminated.get("message"):
                    messages.append(f"{cs.get('name')}: {terminated['message']}")
        pods.append(
            {
                "name": meta.get("name", "?"),
                "phase": status.get("phase", "?"),
                "reasons": reasons,
                "messages": messages,
            }
        )
    return pods


# Kubernetes "container.state.waiting.reason" / "terminated.reason" values
# that mean the pod is NOT going to become Ready without operator action.
# Distinct from transient states like ContainerCreating / PodInitializing.
_IMAGE_PULL_REASONS = {"ImagePullBackOff", "ErrImagePull", "InvalidImageName", "ImageInspectError"}
_CONFIG_ERROR_REASONS = {
    "CreateContainerConfigError",
    "CreateContainerError",
    "RunContainerError",
    "InvalidImageName",
    "ConfigError",
}
_CRASH_REASONS = {"CrashLoopBackOff", "Error", "OOMKilled"}
_TERMINAL_REASONS = _IMAGE_PULL_REASONS | _CONFIG_ERROR_REASONS | _CRASH_REASONS


def _pod_terminal_reason(pods: list[dict]) -> str:
    """Return the first terminal reason found across pods, or '' if none."""
    for p in pods:
        for r in p["reasons"]:
            for token in _TERMINAL_REASONS:
                if token in r:
                    return token
    return ""


def _is_image_pull_failure(reason: str) -> bool:
    return reason in _IMAGE_PULL_REASONS


def _is_kind_context(context: str) -> bool:
    return context.startswith("kind-")


def _kind_cluster_name(context: str) -> str:
    """kind contexts are always 'kind-<cluster-name>'."""
    return context[len("kind-"):] if context.startswith("kind-") else ""


def _dump_pod_events(namespace: str, release: str, *, tail: int = 20) -> None:
    """Print the most recent events for the release's pods. Stdlib-only."""
    r = run_kubectl(
        [
            "-n",
            namespace,
            "get",
            "events",
            "--sort-by=.lastTimestamp",
            "--field-selector=involvedObject.kind=Pod",
            "-o",
            "json",
        ],
        check=False,
        capture=True,
        quiet=True,
    )
    if r.returncode != 0:
        return
    try:
        events = json.loads(r.stdout).get("items", [])
    except json.JSONDecodeError:
        return
    # Filter to events involving pods that carry our release label.
    pods = _pod_phase_snapshot(namespace, release)
    pod_names = {p["name"] for p in pods}
    relevant = [
        e for e in events
        if e.get("involvedObject", {}).get("name", "") in pod_names
    ][-tail:]
    if not relevant:
        return
    print()
    print(f"  {BOLD}Recent pod events (most recent last):{NC}")
    for e in relevant:
        ts = e.get("lastTimestamp") or e.get("eventTime") or ""
        kind = e.get("type", "")
        reason = e.get("reason", "")
        msg = (e.get("message") or "").strip().replace("\n", " ")[:240]
        marker = f"{RED}!{NC}" if kind == "Warning" else f"{DIM}·{NC}"
        print(f"    {marker} [{ts[-8:-1] if ts else '--'}] {kind:<7} {reason:<28} {msg}")


def _print_config_error_recovery(
    *, namespace: str, fullname: str, release: str, pods: list[dict]
) -> None:
    print()
    error("Pod is stuck in CreateContainerConfigError / CreateContainerError.")
    print(f"        Namespace:   {namespace}")
    print(f"        Deployment:  {fullname}")
    print()
    print("  This means the kubelet pulled the image fine but couldn't")
    print("  construct the container — almost always one of:")
    print("    - A Secret/ConfigMap key referenced by the Pod doesn't exist")
    print("    - An env-var name in the Secret is not a valid C identifier")
    print("    - A volume mount points at a missing Secret/ConfigMap")
    print()
    # Print container.state.waiting.message if Kubernetes gave us one — it's
    # usually a precise sentence like:
    #   "couldn't find key FOO in Secret bar/baz"
    for p in pods:
        for m in p["messages"]:
            print(f"  {YELLOW}Kubernetes says:{NC} {m}")
    print()
    print("  Diagnose:")
    print(f"    {DIM}kubectl -n {namespace} describe pod \\")
    print(f"      -l app.kubernetes.io/instance={release}{NC}")
    print()


def _print_image_pull_recovery(
    *, namespace: str, fullname: str, image: str, context: str, release: str
) -> None:
    print()
    error("Pod is stuck on ImagePullBackOff / ErrImagePull.")
    print(f"        Image:       {image}")
    print(f"        Namespace:   {namespace}")
    print(f"        Deployment:  {fullname}")
    print()
    print("  What this means: your cluster can't reach Docker Hub for that")
    print("  image. Could be rate-limiting, slow / blocked egress, or the")
    print("  image simply isn't published for your node's architecture.")
    print()
    print("  Diagnose:")
    print(f"    {DIM}kubectl -n {namespace} describe pod \\")
    print(f"      -l app.kubernetes.io/instance={release} \\")
    print(f"      | sed -n '/Events:/,$p'{NC}")
    print()
    if _is_kind_context(context):
        cluster = _kind_cluster_name(context)
        print(f"  {BOLD}You're on kind ({cluster}). Side-load the image into the cluster:{NC}")
        print(f"    {DIM}docker pull {image}{NC}")
        print(f"    {DIM}kind load docker-image {image} --name {cluster}{NC}")
        print(f"    {DIM}kubectl -n {namespace} rollout restart deployment/{fullname}{NC}")
        print()
        print("  …then re-run `python helm_mcp_operations.py status` to confirm.")
    else:
        print("  Workarounds:")
        print("    - Mirror the image into your private registry, then re-run with")
        print(f"      {DIM}--set image.repository=<your-mirror>{NC} via helm upgrade.")
        print("    - Pre-pull the image on every node out-of-band.")
        print("    - Configure an `imagePullSecrets` entry if Docker Hub auth fixes it.")
    print()


def _wait_for_rollout(
    *,
    namespace: str,
    fullname: str,
    release: str,
    timeout_seconds: int = 240,
    poll_seconds: int = 5,
) -> None:
    """Poll the Deployment until it's healthy, with live per-pod feedback.

    Detects terminal failure states (ImagePullBackOff, CreateContainerConfigError,
    CrashLoopBackOff, etc.) and short-circuits with a focused recovery hint
    instead of spinning until timeout.
    """
    info(f"Waiting for Deployment {fullname} to become healthy (timeout {timeout_seconds}s)…")
    start = time.time()
    last_summary = ""
    # Give the kubelet a few seconds to settle before treating a reason as
    # terminal — `ContainerCreating` briefly flips to `CreateContainerError`
    # on slow kind nodes before recovering.
    terminal_grace_seconds = 15

    while True:
        elapsed = int(time.time() - start)
        if elapsed > timeout_seconds:
            print()
            error(f"Timed out waiting for rollout after {timeout_seconds}s.")
            _dump_pod_events(namespace, release)
            print()
            print("  Inspect what's going on:")
            print(f"    {DIM}kubectl -n {namespace} get pods{NC}")
            print(f"    {DIM}kubectl -n {namespace} describe deployment/{fullname}{NC}")
            print(f"    {DIM}kubectl -n {namespace} logs deployment/{fullname} --tail=200{NC}")
            print()
            print("  When you're ready to retry, run:")
            print(f"    {DIM}python helm_mcp_operations.py status{NC}")
            die("Rollout timed out.")

        pods = _pod_phase_snapshot(namespace, release)
        if pods:
            summary = ", ".join(
                f"{p['name'].rsplit('-', 1)[-1]}={p['phase']}"
                + (f" [{';'.join(p['reasons'])}]" if p['reasons'] else "")
                for p in pods
            )
            if summary != last_summary:
                info(f"  [{elapsed:>3}s] {summary}")
                last_summary = summary

            reason = _pod_terminal_reason(pods)
            if reason and elapsed >= terminal_grace_seconds:
                _dump_pod_events(namespace, release)
                if _is_image_pull_failure(reason):
                    _print_image_pull_recovery(
                        namespace=namespace,
                        fullname=fullname,
                        image=f"{DOCKER_HUB_IMAGE_REPO}:{DOCKER_HUB_IMAGE_TAG}",
                        context=_kubectl_context(),
                        release=release,
                    )
                else:
                    _print_config_error_recovery(
                        namespace=namespace,
                        fullname=fullname,
                        release=release,
                        pods=pods,
                    )
                die(f"Aborting rollout wait — terminal pod state: {reason}.")

        # Definitive success check — silenced so it doesn't flood the output.
        r = run_kubectl(
            [
                "-n",
                namespace,
                "rollout",
                "status",
                f"deployment/{fullname}",
                "--timeout=2s",
            ],
            check=False,
            capture=True,
            quiet=True,
        )
        if r.returncode == 0 and "successfully rolled out" in (r.stdout or ""):
            ok(f"Deployment {fullname} is healthy.")
            return

        time.sleep(poll_seconds)


def _fullname(release: str) -> str:
    """Mirror the chart's fullname helper.

    The chart's `_helpers.tpl::zscaler-mcp-server.fullname` returns the
    release name verbatim if it already contains the chart name, else
    "<release>-<chart-name>". Our `release` is operator-chosen and the
    chart name is fixed to `zscaler-mcp-server`, so this re-implements
    the same logic.
    """
    chart = "zscaler-mcp-server"
    if chart in release:
        return release
    return f"{release}-{chart}"


# ════════════════════════════════════════════════════════════════════════
#  Credential collection (from .env, with prompted fallback)
# ════════════════════════════════════════════════════════════════════════


def _collect_credentials() -> dict:
    """Load credentials from .env and prompt for whatever's missing.

    Returns a dict containing:
      env          — full .env contents (passed verbatim into the K8s Secret)
      env_path     — Path of the .env file used
      auth_mode    — selected MCP client auth mode
      api_key      — only set for auth_mode=api-key (server side)
    """

    print_zscaler_logo()
    print(f"  {BOLD}Helm chart deployment for the Zscaler MCP Server{NC}")
    print()

    default_env = PROJECT_ROOT / ".env"
    if not default_env.is_file():
        default_env = SCRIPT_DIR / ".env"
    env_path_str = _prompt(
        "Path to .env file (will be loaded into a K8s Secret as-is)",
        default=str(default_env),
    )
    env_path = Path(env_path_str).expanduser().resolve()
    if not env_path.is_file():
        die(f".env file not found: {env_path}")
    env = load_env(env_path)
    ok(f".env loaded from {env_path} ({len(env)} variables)")
    print()

    # OneAPI sanity-check — these are what the chart depends on.
    cid = resolve(env, "ZSCALER_CLIENT_ID")
    csec = resolve(env, "ZSCALER_CLIENT_SECRET")
    if not cid or not csec:
        warn("  ZSCALER_CLIENT_ID / ZSCALER_CLIENT_SECRET missing from .env —")
        warn("  the server will fail to authenticate to the Zscaler API.")
        if not _prompt_yes_no("  Continue anyway?", default=False):
            die("Aborted.")

    # Auth mode — defaults to whatever's in .env, falls back to "zscaler".
    env_auth_mode = resolve(env, "ZSCALER_MCP_AUTH_MODE").lower()
    if env_auth_mode in {"jwt", "api-key", "zscaler", "none"}:
        info(f"Auth mode from .env: {BOLD}{env_auth_mode}{NC}")
        if not _prompt_yes_no("  Use this auth mode?"):
            env_auth_mode = ""
    else:
        env_auth_mode = ""

    if env_auth_mode:
        auth_mode = env_auth_mode
    else:
        auth_mode = _prompt_choice(
            "Select MCP client authentication mode:",
            [
                ("zscaler", "Zscaler    — OneAPI Basic-auth (recommended)"),
                ("jwt", "JWT        — Validate tokens against a JWKS endpoint"),
                ("api-key", "API Key    — Shared secret in Authorization header"),
                ("none", "None       — No authentication (dev only)"),
            ],
        )
        ok(f"Auth mode: {auth_mode}")

    api_key = ""
    if auth_mode == "api-key":
        api_key = resolve(env, "ZSCALER_MCP_AUTH_API_KEY")
        if not api_key:
            api_key = _prompt(
                "Server-side API key (also goes into the Secret)", secret=True
            )

    return {
        "env": env,
        "env_path": env_path,
        "auth_mode": auth_mode,
        "api_key": api_key,
    }


# ── Auth-header builder + MCP client config writers ──────────────────────


def _build_auth_header(creds: dict) -> str | None:
    auth_mode = creds["auth_mode"]
    env = creds["env"]
    if auth_mode == "api-key":
        api_key = creds.get("api_key") or resolve(env, "ZSCALER_MCP_AUTH_API_KEY")
        return f"Bearer {api_key}" if api_key else None
    if auth_mode == "zscaler":
        cid = resolve(env, "ZSCALER_CLIENT_ID")
        csec = resolve(env, "ZSCALER_CLIENT_SECRET")
        if not (cid and csec):
            return None
        b64 = base64.b64encode(f"{cid}:{csec}".encode()).decode()
        return f"Basic {b64}"
    if auth_mode == "jwt":
        # JWT minting is out of scope for the Helm chart — operators run their
        # own IdP. The client config gets a placeholder the user replaces.
        return None
    return None


def _update_client_configs(mcp_url: str, creds: dict) -> None:
    auth_header = _build_auth_header(creds)
    auth_mode = creds["auth_mode"]

    needs_allow_http = mcp_url.startswith("http://") and not any(
        h in mcp_url for h in ["localhost", "127.0.0.1", "::1"]
    )

    info("Updating Claude Desktop config")

    def _claude_updater(config: dict) -> None:
        config.setdefault("mcpServers", {})
        mcp_args = ["-y", "mcp-remote", mcp_url]
        if needs_allow_http:
            mcp_args.append("--allow-http")
        if auth_header:
            mcp_args += ["--header", f"Authorization:{auth_header}"]
        elif auth_mode == "jwt":
            mcp_args += ["--header", "Authorization:Bearer <YOUR_JWT_TOKEN>"]
        if SYSTEM == "Windows":
            config["mcpServers"][SERVER_NAME] = {
                "command": "cmd",
                "args": ["/c", "npx", *mcp_args],
            }
        else:
            config["mcpServers"][SERVER_NAME] = {
                "command": "npx",
                "args": mcp_args,
            }

    upsert_json_config(CLAUDE_CONFIG, _claude_updater)
    ok(f"Claude Desktop config updated: {CLAUDE_CONFIG}")

    info("Updating Cursor config")

    def _cursor_updater(config: dict) -> None:
        config.setdefault("mcpServers", {})
        entry: dict = {"url": mcp_url}
        if auth_header:
            entry["headers"] = {"Authorization": auth_header}
        elif auth_mode == "jwt":
            entry["headers"] = {"Authorization": "Bearer <YOUR_JWT_TOKEN>"}
        config["mcpServers"][SERVER_NAME] = entry

    upsert_json_config(CURSOR_CONFIG, _cursor_updater)
    ok(f"Cursor config updated: {CURSOR_CONFIG}")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Port-forward management
# ════════════════════════════════════════════════════════════════════════


def _port_forward_log(release: str) -> Path:
    return Path("/tmp") / f"zscaler-mcp-{release}-port-forward.log"


def _port_forward_pid(release: str) -> Path:
    return Path("/tmp") / f"zscaler-mcp-{release}-port-forward.pid"


def _start_port_forward(
    *, namespace: str, service: str, local_port: str, service_port: str, release: str
) -> int | None:
    log_file = _port_forward_log(release)
    pid_file = _port_forward_pid(release)

    # If a prior port-forward is still running, leave it alone.
    if pid_file.is_file():
        try:
            existing_pid = int(pid_file.read_text().strip())
            os.kill(existing_pid, 0)
            ok(f"Port-forward already running (pid={existing_pid})")
            return existing_pid
        except (ValueError, ProcessLookupError, PermissionError):
            pid_file.unlink(missing_ok=True)

    info(f"Starting kubectl port-forward (localhost:{local_port} → svc/{service}:{service_port})")
    with open(log_file, "w", encoding="utf-8") as fh:
        proc = subprocess.Popen(
            [
                "kubectl",
                "-n",
                namespace,
                "port-forward",
                f"svc/{service}",
                f"{local_port}:{service_port}",
            ],
            stdout=fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    time.sleep(1.0)
    if proc.poll() is not None:
        warn(f"port-forward exited immediately — see {log_file}")
        return None
    pid_file.write_text(str(proc.pid))
    ok(f"port-forward running (pid={proc.pid}, log={log_file})")
    return proc.pid


def _stop_port_forward(release: str) -> None:
    pid_file = _port_forward_pid(release)
    if not pid_file.is_file():
        return
    try:
        pid = int(pid_file.read_text().strip())
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        ok(f"Stopped port-forward (pid={pid})")
    except (ValueError, ProcessLookupError, PermissionError):
        pass
    pid_file.unlink(missing_ok=True)


# ════════════════════════════════════════════════════════════════════════
#  Deploy
# ════════════════════════════════════════════════════════════════════════


def op_deploy(args: argparse.Namespace) -> None:
    _require_binaries()

    context = _kubectl_context()
    info(f"Current kubectl context: {BOLD}{context}{NC}")
    if not _prompt_yes_no("  Deploy into this cluster?"):
        die("Aborted. Switch contexts with `kubectl config use-context <name>` and re-run.")
    print()

    # Probe before asking anything else so a dead cluster doesn't waste the
    # user's time on prompts they'd have to re-enter after restarting kind.
    _assert_cluster_reachable(context)
    print()

    creds = _collect_credentials()
    print()

    info("Helm chart configuration")
    namespace = _prompt("Kubernetes namespace", default=NAMESPACE_DEFAULT)
    release = _prompt("Helm release name", default=CHART_RELEASE_DEFAULT)

    image_repo = _prompt("Container image repository", default=DOCKER_HUB_IMAGE_REPO)
    image_tag = _prompt("Container image tag", default=DOCKER_HUB_IMAGE_TAG)

    expose = _prompt_choice(
        "How should the MCP endpoint be exposed?",
        [
            ("portforward", "kubectl port-forward (local dev — recommended for testing)"),
            ("ingress", "Ingress (requires an Ingress controller in the cluster)"),
            ("none", "Neither — just install the workload (I'll wire networking later)"),
        ],
    )

    ingress_host = ""
    ingress_class = ""
    if expose == "ingress":
        ingress_host = _prompt("Ingress hostname (e.g. zscaler-mcp.example.com)")
        ingress_class = _prompt("Ingress className", default="nginx")
    print()

    fullname = _fullname(release)
    secret_name = f"{fullname}-creds"
    local_port = LOCAL_PORT_DEFAULT
    service_port = SERVICE_PORT_DEFAULT

    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print(f"    Cluster context:  {context}")
    print(f"    Namespace:        {namespace}")
    print(f"    Release:          {release}")
    print(f"    Image:            {image_repo}:{image_tag}")
    print(f"    Auth mode:        {creds['auth_mode']}")
    print(f"    Secret source:    {creds['env_path']}  →  {secret_name}")
    if expose == "ingress":
        print(f"    Exposure:         Ingress ({ingress_class}) at {ingress_host}")
    elif expose == "portforward":
        print(f"    Exposure:         kubectl port-forward localhost:{local_port} → svc/{fullname}:{service_port}")
    else:
        print("    Exposure:         (none — install only)")
    print()
    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    # ── 1) Namespace ────────────────────────────────────────────────────
    if not _namespace_exists(namespace):
        info(f"Creating namespace: {namespace}")
        run_kubectl(["create", "namespace", namespace])
    else:
        ok(f"Namespace {namespace} already exists")

    # ── 2) Secret from .env (re-create on each deploy → idempotent) ─────
    info(f"Materializing Secret {secret_name} from {creds['env_path']}")
    # `create --dry-run=client -o yaml | apply -f -` is the canonical idempotent
    # form. We assemble it as two subprocesses piped together.
    create_cmd = [
        "kubectl",
        "-n",
        namespace,
        "create",
        "secret",
        "generic",
        secret_name,
        f"--from-env-file={creds['env_path']}",
        "--dry-run=client",
        "-o",
        "yaml",
    ]
    apply_cmd = ["kubectl", "-n", namespace, "apply", "-f", "-"]
    info(f"  $ kubectl create secret generic {secret_name} --from-env-file=... | kubectl apply -f -")
    p1 = subprocess.Popen(create_cmd, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(apply_cmd, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    p1.stdout.close() if p1.stdout else None  # type: ignore[func-returns-value]
    stdout, stderr = p2.communicate()
    if p2.returncode != 0:
        die(f"Failed to apply Secret:\n{stderr}")
    ok(f"Secret applied: {stdout.strip()}")

    # ── 3) helm upgrade --install ──────────────────────────────────────
    helm_args = [
        "upgrade",
        "--install",
        release,
        str(CHART_DIR),
        "-n",
        namespace,
        "--set",
        "secret.create=false",
        "--set",
        f"secret.existingName={secret_name}",
        "--set",
        f"image.repository={image_repo}",
        "--set",
        f"image.tag={image_tag}",
        "--set",
        f"mcp.auth.mode={creds['auth_mode']}",
        "--set",
        f"mcp.auth.enabled={'true' if creds['auth_mode'] != 'none' else 'false'}",
    ]

    if expose == "ingress":
        helm_args += [
            "--set",
            "ingress.enabled=true",
            "--set",
            f"ingress.className={ingress_class}",
            "--set",
            f"ingress.hosts[0].host={ingress_host}",
            "--set",
            "ingress.hosts[0].paths[0].path=/",
            "--set",
            "ingress.hosts[0].paths[0].pathType=Prefix",
        ]

    # Deliberately NOT passing `--wait` here. helm's --wait blocks silently
    # for up to 5 minutes, which is a terrible UX when the pod is in
    # ImagePullBackOff. Instead we let helm return immediately after
    # creating the Deployment, then drive our own waiting loop below with
    # live `kubectl get pods` feedback.

    info("Installing/upgrading Helm release")
    run_helm(helm_args)
    ok(f"Release {release} dispatched to the API server.")
    print()

    # ── 4) Wait for rollout with live feedback ─────────────────────────
    _wait_for_rollout(namespace=namespace, fullname=fullname, release=release)
    print()

    # ── 5) Build the MCP URL ───────────────────────────────────────────
    if expose == "ingress":
        mcp_url = f"https://{ingress_host}/mcp"
        port_forward_pid = None
    elif expose == "portforward":
        port_forward_pid = _start_port_forward(
            namespace=namespace,
            service=fullname,
            local_port=local_port,
            service_port=service_port,
            release=release,
        )
        mcp_url = f"http://localhost:{local_port}/mcp"
    else:
        port_forward_pid = None
        mcp_url = "(not exposed — wire your own Service/Ingress before connecting)"
    print()

    # ── 6) Persist deployment state ─────────────────────────────────────
    _save_state(
        {
            "release": release,
            "namespace": namespace,
            "fullname": fullname,
            "secret_name": secret_name,
            "image": f"{image_repo}:{image_tag}",
            "auth_mode": creds["auth_mode"],
            "expose": expose,
            "ingress_host": ingress_host,
            "ingress_class": ingress_class,
            "local_port": local_port,
            "service_port": service_port,
            "mcp_url": mcp_url,
            "env_path": str(creds["env_path"]),
            "port_forward_pid": port_forward_pid,
        }
    )

    # ── 7) Update Claude / Cursor configs ──────────────────────────────
    if expose in {"portforward", "ingress"}:
        _update_client_configs(mcp_url, creds)
    else:
        warn("Skipping MCP client config update — no exposure configured.")
        print()

    # ── 8) Summary ──────────────────────────────────────────────────────
    print("=" * 76)
    print(f"  {GREEN}Helm deployment complete — auth_mode={creds['auth_mode']}{NC}")
    print("=" * 76)
    print()
    print(f"  MCP URL:     {mcp_url}")
    print(f"  Release:     {release}  (ns={namespace})")
    print(f"  Image:       {image_repo}:{image_tag}")
    print(f"  Secret:      {secret_name}  (sourced from {creds['env_path']})")
    print()
    print("  Next steps:")
    print("    1. Restart Claude Desktop / Cursor — the zscaler entry is wired up.")
    print("    2. Try: \"List all ZPA segment groups\"")
    print()
    print("  Management:")
    print("    python helm_mcp_operations.py status     — Show release health")
    print("    python helm_mcp_operations.py logs       — Tail server logs")
    print("    python helm_mcp_operations.py configure  — Re-write client configs")
    print("    python helm_mcp_operations.py test       — Run `helm test`")
    print("    python helm_mcp_operations.py destroy    — Uninstall everything")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Destroy
# ════════════════════════════════════════════════════════════════════════


def op_destroy(args: argparse.Namespace) -> None:
    _require_binaries()
    state = _load_state()
    if not state:
        die("No deployment state found (.helm-deploy-state.json missing). Did you run `deploy`?")

    _assert_cluster_reachable(_kubectl_context())

    release = state["release"]
    namespace = state["namespace"]
    secret_name = state.get("secret_name", "")
    delete_namespace = False

    print(f"  {BOLD}About to tear down:{NC}")
    print(f"    Release:        {release}")
    print(f"    Namespace:      {namespace}")
    print(f"    Secret:         {secret_name}")
    print(f"    Port-forward:   pid={state.get('port_forward_pid')}")
    print()

    if not args.yes and not _prompt_yes_no("  Continue?", default=False):
        die("Cancelled.")

    if not args.yes:
        delete_namespace = _prompt_yes_no(
            f"  Also delete the namespace {namespace}? (destroys ALL workloads in it)",
            default=False,
        )

    _stop_port_forward(release)

    if _release_exists(release, namespace):
        info(f"Uninstalling Helm release {release}")
        run_helm(["uninstall", release, "-n", namespace])
    else:
        warn(f"Release {release} not found — skipping helm uninstall.")

    if secret_name and _secret_exists(namespace, secret_name):
        info(f"Deleting Secret {secret_name}")
        run_kubectl(["-n", namespace, "delete", "secret", secret_name, "--ignore-not-found"])

    if delete_namespace and _namespace_exists(namespace):
        info(f"Deleting namespace {namespace}")
        run_kubectl(["delete", "namespace", namespace, "--ignore-not-found", "--wait=false"])

    _clear_state()
    print()
    ok("Tear-down complete.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Status
# ════════════════════════════════════════════════════════════════════════


def op_status(args: argparse.Namespace) -> None:
    _require_binaries()
    state = _load_state()
    if not state:
        die("No deployment state found (.helm-deploy-state.json missing). Did you run `deploy`?")

    _assert_cluster_reachable(_kubectl_context())

    release = state["release"]
    namespace = state["namespace"]
    fullname = state["fullname"]

    print()
    print(f"  {BOLD}Release{NC}:    {release}")
    print(f"  {BOLD}Namespace{NC}:  {namespace}")
    print(f"  {BOLD}MCP URL{NC}:    {state.get('mcp_url')}")
    print(f"  {BOLD}Image{NC}:      {state.get('image')}")
    print(f"  {BOLD}Auth mode{NC}:  {state.get('auth_mode')}")
    print()

    info("Helm status")
    run_helm(["status", release, "-n", namespace, "--show-resources"], check=False)
    print()

    info("Pod status")
    run_kubectl(["-n", namespace, "get", "pods", "-l", f"app.kubernetes.io/instance={release}", "-o", "wide"])
    print()

    info("Service status")
    run_kubectl(["-n", namespace, "get", "svc", fullname], check=False)
    print()

    pid_file = _port_forward_pid(release)
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            ok(f"port-forward running (pid={pid}, log={_port_forward_log(release)})")
        except (ValueError, ProcessLookupError, PermissionError):
            warn("port-forward pid file exists but process is gone.")
            pid_file.unlink(missing_ok=True)
    else:
        info("No active port-forward.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Logs
# ════════════════════════════════════════════════════════════════════════


def op_logs(args: argparse.Namespace) -> None:
    _require_binaries()
    state = _load_state()
    if not state:
        die("No deployment state found (.helm-deploy-state.json missing). Did you run `deploy`?")

    _assert_cluster_reachable(_kubectl_context())

    namespace = state["namespace"]
    fullname = state["fullname"]

    info(f"Tailing logs for deployment/{fullname} in ns={namespace} (Ctrl-C to stop)")
    try:
        run_kubectl(
            [
                "-n",
                namespace,
                "logs",
                f"deployment/{fullname}",
                "--tail=200",
                "-f",
            ],
            check=False,
        )
    except KeyboardInterrupt:
        pass


# ════════════════════════════════════════════════════════════════════════
#  Configure (re-write MCP client configs)
# ════════════════════════════════════════════════════════════════════════


def op_configure(args: argparse.Namespace) -> None:
    _require_binaries()
    state = _load_state()
    if not state:
        die("No deployment state found (.helm-deploy-state.json missing). Did you run `deploy`?")

    _assert_cluster_reachable(_kubectl_context())

    env_path = Path(state.get("env_path", ""))
    if not env_path.is_file():
        die(f".env path recorded in state no longer exists: {env_path}. Re-run `deploy`.")

    env = load_env(env_path)
    creds = {
        "env": env,
        "env_path": env_path,
        "auth_mode": state["auth_mode"],
        "api_key": resolve(env, "ZSCALER_MCP_AUTH_API_KEY"),
    }

    if state.get("expose") == "portforward":
        _start_port_forward(
            namespace=state["namespace"],
            service=state["fullname"],
            local_port=state.get("local_port", LOCAL_PORT_DEFAULT),
            service_port=state.get("service_port", SERVICE_PORT_DEFAULT),
            release=state["release"],
        )
        print()

    _update_client_configs(state["mcp_url"], creds)
    print()
    ok("Client configs refreshed.")
    print()
    print(f"  MCP URL:    {state['mcp_url']}")
    print(f"  Auth mode:  {creds['auth_mode']}")
    print()
    print("  Restart Claude Desktop / Cursor to pick up the change.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Test (run `helm test`)
# ════════════════════════════════════════════════════════════════════════


def op_test(args: argparse.Namespace) -> None:
    _require_binaries()
    state = _load_state()
    if not state:
        die("No deployment state found (.helm-deploy-state.json missing). Did you run `deploy`?")

    _assert_cluster_reachable(_kubectl_context())

    info(f"Running `helm test {state['release']}` in ns={state['namespace']}")
    run_helm(["test", state["release"], "-n", state["namespace"]], check=False)


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Zscaler MCP Server — Kubernetes (Helm) Deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "MCP Server Operations:\n"
            "  deploy         Interactive guided helm install (from .env)\n"
            "  destroy        Helm uninstall + clean Secret + optional namespace deletion\n"
            "  status         Show release health, pods, service, port-forward state\n"
            "  logs           Tail Deployment logs\n"
            "  configure      Refresh Cursor / Claude Desktop configs from saved state\n"
            "  test           Run `helm test` on the deployed release\n"
        ),
    )
    sub = p.add_subparsers(dest="operation")

    sub.add_parser("deploy", help="Interactive guided Helm deploy")
    ds = sub.add_parser("destroy", help="Uninstall the Helm release")
    ds.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")
    sub.add_parser("status", help="Show release health")
    sub.add_parser("logs", help="Tail server logs")
    sub.add_parser("configure", help="Refresh Cursor / Claude Desktop configs")
    sub.add_parser("test", help="Run `helm test`")

    return p


OPERATIONS = {
    "deploy": op_deploy,
    "destroy": op_destroy,
    "status": op_status,
    "logs": op_logs,
    "configure": op_configure,
    "test": op_test,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.operation:
        parser.print_help()
        sys.exit(1)

    try:
        OPERATIONS[args.operation](args)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INTERRUPTED]{NC} Operation cancelled.")
        sys.exit(130)


if __name__ == "__main__":
    main()
