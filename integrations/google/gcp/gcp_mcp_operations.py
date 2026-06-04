#!/usr/bin/env python3
"""
Zscaler MCP Server — GCP Deployment (Interactive)

Fully interactive deployment script supporting three deployment targets:
  1. Cloud Run       — managed, serverless container (Docker Hub / GCP Marketplace image)
  2. GKE             — Kubernetes deployment (Docker image, self-managed cluster)
  3. Compute Engine  — Ubuntu VM, self-managed (Python library from PyPI via systemd)

All options:
  - Prompt the user for auth mode, credentials, and GCP options
  - Optionally store credentials in GCP Secret Manager
  - Update Claude Desktop / Cursor configs with correct auth headers
  - Provide destroy / status / logs / ssh operations

Supported MCP client authentication modes:
  - JWT:        Validate tokens against a JWKS endpoint
  - API Key:    Shared secret (auto-generated if not provided)
  - Zscaler:    Validate via Zscaler OneAPI client credentials
  - None:       No MCP client authentication (development only)

Credential resolution (first non-empty wins):
  1. Values from .env file (if the user provides a path)
  2. Interactive prompt (if no .env or value missing)
  3. Shell environment variables

Usage:
  python gcp_mcp_operations.py deploy     # interactive guided deploy
  python gcp_mcp_operations.py destroy    # tear down all resources
  python gcp_mcp_operations.py status     # show deployment status
  python gcp_mcp_operations.py logs       # stream logs
  python gcp_mcp_operations.py ssh        # SSH into VM (VM deployments only)
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import platform
import secrets as _secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
SYSTEM = platform.system()

SERVER_NAME = "zscaler-mcp-server"
DOCKER_HUB_IMAGE = "zscaler/zscaler-mcp-server:latest"
GCP_MARKETPLACE_IMAGE = "us-docker.pkg.dev/business-development-sa-team/zscaler/zscaler-mcp-server:latest"
PYPI_PACKAGE = "zscaler-mcp"

STATE_FILE = SCRIPT_DIR / ".gcp-deploy-state.json"

VM_IMAGE_FAMILY = "debian-12"
VM_IMAGE_PROJECT = "debian-cloud"
VM_MACHINE_TYPE = "e2-small"
VM_ADMIN_USER = "zscaler"

MCP_PORT = "8000"

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
_TAGLINE = "GCP Cloud Run / GKE / Compute Engine Deployment   |   Image source: Docker Hub"


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


def run_gcloud(
    args: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    cmd = ["gcloud"] + args
    info(f"  $ gcloud {' '.join(args[:8])}{'...' if len(args) > 8 else ''}")
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if check and r.returncode != 0:
            die(f"gcloud command failed:\n  {r.stderr.strip()}")
        return r
    else:
        r = subprocess.run(cmd)
        if check and r.returncode != 0:
            die(f"gcloud command failed (exit code {r.returncode})")
        return r


def run_kubectl(
    args: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    cmd = ["kubectl"] + args
    info(f"  $ kubectl {' '.join(args[:8])}{'...' if len(args) > 8 else ''}")
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if check and r.returncode != 0:
            die(f"kubectl command failed:\n  {r.stderr.strip()}")
        return r
    else:
        r = subprocess.run(cmd)
        if check and r.returncode != 0:
            die(f"kubectl command failed (exit code {r.returncode})")
        return r


def run_cmd(
    args: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    if capture:
        r = subprocess.run(args, capture_output=True, text=True)
        if check and r.returncode != 0:
            die(f"Command failed: {r.stderr.strip()}")
        return r
    else:
        r = subprocess.run(args)
        if check and r.returncode != 0:
            die(f"Command failed (exit code {r.returncode})")
        return r


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
    if default:
        display = f"  {label} [{default}]: "
    else:
        display = f"  {label}: "
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
            key = options[int(raw) - 1][0]
            return key
        error(f"  Invalid choice: {raw}")


def _prompt_yes_no(question: str, *, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {question} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


# ════════════════════════════════════════════════════════════════════════
#  Common credential/config collection
# ════════════════════════════════════════════════════════════════════════


def _collect_credentials() -> dict:
    """Collect all credentials and config interactively."""

    cred_source = _prompt_choice(
        "How would you like to provide credentials?",
        [
            ("env", "From a .env file (provide file path)"),
            ("prompt", "Enter manually (interactive prompts)"),
        ],
    )

    env: dict[str, str] = {}
    if cred_source == "env":
        local_env = SCRIPT_DIR / ".env"
        default_env = str(local_env) if local_env.is_file() else str(PROJECT_ROOT / ".env")
        env_path_str = _prompt("Path to .env file", default=default_env)
        env_path = Path(env_path_str).expanduser().resolve()
        if not env_path.is_file():
            die(f".env file not found: {env_path}")
        env = load_env(env_path)
        ok(f".env loaded from {env_path} ({len(env)} variables)")
    print()

    # ── Zscaler API credentials ───────────────────────────────────────
    info("Zscaler API credentials")
    print(f"  {BOLD}These authenticate the MCP server to the Zscaler API.{NC}")
    print()

    zscaler_client_id = resolve(env, "ZSCALER_CLIENT_ID")
    zscaler_client_secret = resolve(env, "ZSCALER_CLIENT_SECRET")
    zscaler_vanity_domain = resolve(env, "ZSCALER_VANITY_DOMAIN")
    zscaler_customer_id = resolve(env, "ZSCALER_CUSTOMER_ID")
    zscaler_cloud = resolve(env, "ZSCALER_CLOUD")

    if not zscaler_client_id:
        zscaler_client_id = _prompt("Zscaler Client ID")
    else:
        ok(f"Zscaler Client ID: {zscaler_client_id[:8]}...")

    if not zscaler_client_secret:
        zscaler_client_secret = _prompt("Zscaler Client Secret", secret=True)
    else:
        ok("Zscaler Client Secret: ********")

    if not zscaler_vanity_domain:
        zscaler_vanity_domain = _prompt("Zscaler Vanity Domain")
    else:
        ok(f"Zscaler Vanity Domain: {zscaler_vanity_domain}")

    if not zscaler_customer_id:
        zscaler_customer_id = _prompt("Zscaler Customer ID")
    else:
        ok(f"Zscaler Customer ID: {zscaler_customer_id}")

    if not zscaler_cloud:
        zscaler_cloud = _prompt("Zscaler Cloud (e.g. production, beta)", default="production")
    else:
        ok(f"Zscaler Cloud: {zscaler_cloud}")
    print()

    # ── MCP client auth mode ──────────────────────────────────────────
    auth_mode = _prompt_choice(
        "Select MCP client authentication mode:",
        [
            ("jwt", "JWT        — Validate tokens against a JWKS endpoint"),
            ("api-key", "API Key    — Shared secret (auto-generated if not provided)"),
            ("zscaler", "Zscaler    — Validate via OneAPI client credentials"),
            ("none", "None       — No authentication (development only)"),
        ],
    )
    ok(f"Auth mode: {auth_mode}")
    print()

    # ── Auth-mode-specific credentials ────────────────────────────────
    jwks_uri = jwt_issuer = jwt_audience = ""
    api_key = ""

    if auth_mode == "jwt":
        info("JWT credentials")
        jwks_uri = resolve(env, "ZSCALER_MCP_AUTH_JWKS_URI")
        jwt_issuer = resolve(env, "ZSCALER_MCP_AUTH_ISSUER")
        jwt_audience = resolve(env, "ZSCALER_MCP_AUTH_AUDIENCE") or "zscaler-mcp-server"

        if not jwks_uri:
            jwks_uri = _prompt("JWKS URI (e.g. https://your-idp/.well-known/jwks.json)")
        else:
            ok(f"JWKS URI: {jwks_uri}")
        if not jwt_issuer:
            jwt_issuer = _prompt("JWT Issuer (e.g. https://your-idp/)")
        else:
            ok(f"JWT Issuer: {jwt_issuer}")
        jwt_audience = _prompt("JWT Audience", default=jwt_audience)

        # Token-minting credentials — used to obtain a Bearer JWT so client
        # configs (Claude, Cursor) ship with a working Authorization header.
        # Supports any OAuth2 provider that accepts client_credentials grant.
        # Falls back gracefully: configs get a placeholder if these are absent.
        token_endpoint = resolve(env, "TOKEN_ENDPOINT")
        token_client_id = resolve(env, "TOKEN_CLIENT_ID")
        token_client_secret = resolve(env, "TOKEN_CLIENT_SECRET")
        # Optional explicit scope (Cognito/Okta/Keycloak style); when present
        # we issue a form-encoded request and skip the Auth0 audience body.
        token_scope = resolve(env, "TOKEN_SCOPE")

        # Common convention: AUTH0_DOMAIN → derive endpoint automatically.
        auth0_domain = resolve(env, "AUTH0_DOMAIN")
        if not token_endpoint and auth0_domain:
            token_endpoint = f"https://{auth0_domain}/oauth/token"
        if not token_client_id:
            token_client_id = resolve(env, "AUTH0_CLIENT_ID")
        if not token_client_secret:
            token_client_secret = resolve(env, "AUTH0_CLIENT_SECRET")

    elif auth_mode == "api-key":
        info("API Key configuration")
        api_key = resolve(env, "ZSCALER_MCP_AUTH_API_KEY")
        if not api_key:
            if _prompt_yes_no("Auto-generate a secure API key?"):
                api_key = _secrets.token_urlsafe(32)
                ok(f"Generated API key: {api_key}")
            else:
                api_key = _prompt("API Key", secret=True)
        else:
            ok("API Key: loaded from .env")

    elif auth_mode == "zscaler":
        info("Zscaler auth uses the same OneAPI credentials (no extra config)")
        ok("Will validate MCP clients against Zscaler token endpoint")

    else:
        info("No authentication selected")
        warn("Anyone with the URL can access the MCP server. For development only.")
    print()

    # ── MCP server options ────────────────────────────────────────────
    info("MCP server options")
    write_enabled = resolve(env, "ZSCALER_MCP_WRITE_ENABLED")
    write_tools = resolve(env, "ZSCALER_MCP_WRITE_TOOLS")
    disabled_tools = resolve(env, "ZSCALER_MCP_DISABLED_TOOLS")
    disabled_services = resolve(env, "ZSCALER_MCP_DISABLED_SERVICES")

    if not write_enabled:
        if _prompt_yes_no("Enable write tools (create/update/delete)?", default=False):
            write_enabled = "true"
            write_tools = _prompt(
                "Write tool patterns (e.g. zpa_*,zia_*)", default="zpa_*,zia_*,zdx_*"
            )
    if write_enabled:
        ok(f"Write tools enabled: {write_tools or '*'}")
    else:
        ok("Write tools disabled (read-only)")
    print()

    return {
        "env": env,
        "zscaler_client_id": zscaler_client_id,
        "zscaler_client_secret": zscaler_client_secret,
        "zscaler_vanity_domain": zscaler_vanity_domain,
        "zscaler_customer_id": zscaler_customer_id,
        "zscaler_cloud": zscaler_cloud,
        "auth_mode": auth_mode,
        "jwks_uri": jwks_uri,
        "jwt_issuer": jwt_issuer,
        "jwt_audience": jwt_audience,
        "token_endpoint": token_endpoint if auth_mode == "jwt" else "",
        "token_client_id": token_client_id if auth_mode == "jwt" else "",
        "token_client_secret": token_client_secret if auth_mode == "jwt" else "",
        "token_scope": token_scope if auth_mode == "jwt" else "",
        "api_key": api_key,
        "write_enabled": write_enabled,
        "write_tools": write_tools,
        "disabled_tools": disabled_tools,
        "disabled_services": disabled_services,
    }


# ── Shared helpers ────────────────────────────────────────────────────────


def _build_mcp_env_vars(creds: dict, *, use_secret_manager: bool, project: str) -> dict[str, str]:
    """Build the env var dict for the MCP server container / VM."""
    env_vars: dict[str, str] = {
        "ZSCALER_MCP_ALLOW_HTTP": "true",
        "ZSCALER_MCP_DISABLE_HOST_VALIDATION": "true",
    }

    if use_secret_manager:
        env_vars["ZSCALER_MCP_GCP_SECRET_MANAGER"] = "true"
        env_vars["GCP_PROJECT_ID"] = project
    else:
        env_vars["ZSCALER_CLIENT_ID"] = creds["zscaler_client_id"]
        env_vars["ZSCALER_CLIENT_SECRET"] = creds["zscaler_client_secret"]
        env_vars["ZSCALER_VANITY_DOMAIN"] = creds["zscaler_vanity_domain"]
        env_vars["ZSCALER_CUSTOMER_ID"] = creds["zscaler_customer_id"]
        env_vars["ZSCALER_CLOUD"] = creds["zscaler_cloud"]

    auth_mode = creds["auth_mode"]
    if auth_mode == "jwt":
        env_vars["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        env_vars["ZSCALER_MCP_AUTH_MODE"] = "jwt"
        env_vars["ZSCALER_MCP_AUTH_JWKS_URI"] = creds["jwks_uri"]
        env_vars["ZSCALER_MCP_AUTH_ISSUER"] = creds["jwt_issuer"]
        env_vars["ZSCALER_MCP_AUTH_AUDIENCE"] = creds["jwt_audience"]
    elif auth_mode == "api-key":
        env_vars["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        env_vars["ZSCALER_MCP_AUTH_MODE"] = "api-key"
        env_vars["ZSCALER_MCP_AUTH_API_KEY"] = creds["api_key"]
    elif auth_mode == "zscaler":
        env_vars["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        env_vars["ZSCALER_MCP_AUTH_MODE"] = "zscaler"
    else:
        env_vars["ZSCALER_MCP_AUTH_ENABLED"] = "false"

    for key in ("ZSCALER_MCP_WRITE_ENABLED", "ZSCALER_MCP_WRITE_TOOLS",
                "ZSCALER_MCP_DISABLED_TOOLS", "ZSCALER_MCP_DISABLED_SERVICES"):
        cred_key = key.lower().replace("zscaler_mcp_", "")
        val = creds.get(cred_key, "")
        if val:
            env_vars[key] = val

    if creds.get("write_enabled"):
        env_vars["ZSCALER_MCP_WRITE_ENABLED"] = creds["write_enabled"]
    if creds.get("write_tools"):
        env_vars["ZSCALER_MCP_WRITE_TOOLS"] = creds["write_tools"]
    if creds.get("disabled_tools"):
        env_vars["ZSCALER_MCP_DISABLED_TOOLS"] = creds["disabled_tools"]
    if creds.get("disabled_services"):
        env_vars["ZSCALER_MCP_DISABLED_SERVICES"] = creds["disabled_services"]

    return env_vars


def _setup_secret_manager(project: str, creds: dict) -> None:
    """Store Zscaler credentials in GCP Secret Manager."""
    info("Setting up GCP Secret Manager...")

    run_gcloud(
        ["services", "enable", "secretmanager.googleapis.com", "--project", project, "--quiet"],
        capture=True,
    )

    r = run_gcloud(
        ["projects", "describe", project, "--format", "value(projectNumber)"],
        capture=True,
    )
    project_number = r.stdout.strip()
    sa = f"{project_number}-compute@developer.gserviceaccount.com"

    secrets = {
        "zscaler-client-id": creds["zscaler_client_id"],
        "zscaler-client-secret": creds["zscaler_client_secret"],
        "zscaler-vanity-domain": creds["zscaler_vanity_domain"],
        "zscaler-customer-id": creds["zscaler_customer_id"],
        "zscaler-cloud": creds["zscaler_cloud"],
    }

    for name, value in secrets.items():
        if not value:
            continue
        r = run_gcloud(
            ["secrets", "describe", name, "--project", project],
            check=False, capture=True,
        )
        if r.returncode != 0:
            subprocess.run(
                ["gcloud", "secrets", "create", name,
                 "--replication-policy", "automatic", "--project", project],
                capture_output=True, text=True,
            )
        subprocess.run(
            ["gcloud", "secrets", "versions", "add", name,
             "--data-file=-", "--project", project],
            input=value, capture_output=True, text=True,
        )
        run_gcloud(
            ["secrets", "add-iam-policy-binding", name,
             "--member", f"serviceAccount:{sa}",
             "--role", "roles/secretmanager.secretAccessor",
             "--project", project, "--quiet"],
            check=False, capture=True,
        )

    ok(f"Credentials stored in Secret Manager ({len(secrets)} secrets)")
    print()


def _mint_bearer_token(creds: dict) -> str | None:
    """Mint a Bearer token via OAuth2 ``client_credentials`` grant.

    Two dialects are supported, picked from the configured fields:

    * **scope-based (RFC 6749 / Cognito / Okta / Keycloak / Entra ID)** —
      triggered by ``TOKEN_SCOPE`` or by a token endpoint that looks like
      one of those IdPs. Body is form-encoded; credentials go in the
      ``Authorization: Basic`` header.

    * **audience-based (Auth0)** — fallback when no scope is configured.
      Body is JSON with ``audience`` + credentials inline. This is the
      original behaviour and the legacy ``.env`` shape continues to work.

    Returns the ``access_token`` string, or ``None`` on any failure
    (logged as a warning so the surrounding deploy keeps going).
    """
    token_endpoint = (creds.get("token_endpoint") or "").strip()
    client_id = (creds.get("token_client_id") or "").strip()
    client_secret = (creds.get("token_client_secret") or "").strip()
    audience = (creds.get("jwt_audience") or "").strip()
    scope = (creds.get("token_scope") or "").strip()

    if not (token_endpoint and client_id and client_secret):
        return None

    cognito_like_hosts = ("amazoncognito.com", "okta.com", "keycloak", "microsoftonline.com")
    use_form_style = bool(scope) or any(h in token_endpoint for h in cognito_like_hosts)

    if use_form_style:
        fields = [("grant_type", "client_credentials")]
        if scope:
            fields.append(("scope", scope))
        elif audience:
            # Edge case: Auth0 also accepts form-encoded + audience field.
            fields.append(("audience", audience))
        body = urllib.parse.urlencode(fields).encode()
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = urllib.request.Request(
            token_endpoint,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic}",
                "Accept": "application/json",
            },
            method="POST",
        )
    else:
        if not audience:
            warn("  Token mint skipped: neither TOKEN_SCOPE nor ZSCALER_MCP_AUTH_AUDIENCE set")
            return None
        payload = json.dumps({
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": audience,
            "grant_type": "client_credentials",
        }).encode()
        req = urllib.request.Request(
            token_endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace") if exc.fp else ""
        warn(f"  Token mint failed: HTTP {exc.code} {exc.reason} — {detail[:200]}")
        return None
    except urllib.error.URLError as exc:
        warn(f"  Token mint failed: {exc}")
        return None

    token = body.get("access_token")
    if not token:
        warn("  Token response missing access_token")
        return None

    expires_in = int(body.get("expires_in", 0) or 0)
    if expires_in:
        hours, mins = divmod(expires_in // 60, 60)
        ok(f"  Bearer token minted (expires in ~{hours}h{mins:02d}m)")
    else:
        ok("  Bearer token minted")
    return token


def _build_auth_header(creds: dict) -> str | None:
    auth_mode = creds["auth_mode"]
    if auth_mode == "api-key":
        return f"Bearer {creds['api_key']}"
    if auth_mode == "zscaler":
        b64 = base64.b64encode(
            f"{creds['zscaler_client_id']}:{creds['zscaler_client_secret']}".encode()
        ).decode()
        return f"Basic {b64}"
    if auth_mode == "jwt":
        token = _mint_bearer_token(creds)
        if token:
            return f"Bearer {token}"
    return None


def _update_client_configs(mcp_url: str, creds: dict) -> None:
    """Update Claude Desktop and Cursor configs."""
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
#  Deploy — Cloud Run
# ════════════════════════════════════════════════════════════════════════


def _ensure_public_and_ready(
    service_name: str,
    region: str,
    project: str,
    mcp_url: str,
    *,
    attempts: int = 24,
    delay: int = 5,
) -> bool:
    """Make the Cloud Run service publicly invokable, then wait until requests
    actually reach the MCP app (not Cloud Run's ingress).

    Why this exists: ``gcloud run deploy --allow-unauthenticated`` applies the
    ``allUsers`` invoker binding as a *separate* step that propagates a few
    seconds after the revision starts serving. During that window Cloud Run's
    ingress returns 401 to every request — and ``mcp-remote`` (the Claude /
    Cursor bridge) latches onto that 401 as an OAuth challenge and gets stuck.
    So we (1) re-assert the binding explicitly (idempotent) and (2) block until
    a probe reaches the app, before writing client configs and declaring done.

    Returns True when the app is reachable; False if public access could not be
    granted (e.g. an org policy blocks ``allUsers``) or it never came up.
    """
    info("Ensuring public invoker access (allUsers)...")
    res = run_gcloud(
        [
            "run", "services", "add-iam-policy-binding", service_name,
            "--region", region, "--project", project,
            "--member=allUsers", "--role=roles/run.invoker", "--quiet",
        ],
        check=False,
        capture=True,
    )
    if res.returncode != 0:
        warn("Could not grant public access (allUsers).")
        warn("Your GCP org likely enforces constraints/iam.allowedPolicyMemberDomains.")
        warn("Cloud Run will require IAM auth, which mcp-remote cannot satisfy.")
        warn("Use the Compute Engine VM or GKE target, or IAP — see")
        warn("integrations/google/README.md ('Enterprise Considerations').")
        return False
    ok("Public access granted")

    info("Waiting for the service to become reachable (this is the fix for the")
    info("transient 401s during rollout — not a manual step you need to repeat)...")
    probe = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "deploy-readiness-check", "version": "1"},
            },
        }
    ).encode()

    for _ in range(attempts):
        try:
            req = urllib.request.Request(
                mcp_url,
                data=probe,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode(errors="replace")
            # A JSON-RPC body means the request reached the MCP app itself.
            if "jsonrpc" in body:
                ok("Service is reachable — MCP app is responding")
                return True
        except urllib.error.HTTPError as exc:
            # The app returns 401 (with a jsonrpc body) when no creds are sent;
            # that still proves we got *past* Cloud Run's ingress to the app.
            body = exc.read().decode(errors="replace") if exc.fp else ""
            if "jsonrpc" in body:
                ok("Service is reachable — MCP app is responding")
                return True
        except urllib.error.URLError:
            pass
        time.sleep(delay)

    warn("Service did not become reachable within the timeout.")
    warn("It may still be propagating; if your client shows 401s, wait ~1 min")
    warn("and fully restart Claude / Cursor so mcp-remote reconnects.")
    return False


def _deploy_cloud_run(creds: dict) -> None:
    """Deploy to Google Cloud Run."""
    env = creds["env"]

    info("Cloud Run configuration")
    project = resolve(env, "GCP_PROJECT_ID", "PROJECT_ID")
    if not project:
        project = _prompt("GCP Project ID")
    else:
        ok(f"GCP Project: {project}")

    region = resolve(env, "GCP_REGION", "REGION") or "us-central1"
    region = _prompt("GCP Region", default=region)

    image = _prompt("Container image", default=DOCKER_HUB_IMAGE)
    service_name = _prompt("Cloud Run service name", default=SERVER_NAME)

    use_sm = _prompt_yes_no("Store credentials in GCP Secret Manager? (recommended)")
    print()

    _auth_labels = {
        "jwt": "JWT",
        "api-key": "API Key",
        "zscaler": "Zscaler",
        "none": "None (no auth)",
    }

    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          Google Cloud Run")
    print(f"    Image:           {image}")
    print(f"    Project:         {project}")
    print(f"    Region:          {region}")
    print(f"    Service:         {service_name}")
    print(f"    Secret Manager:  {'Yes' if use_sm else 'No'}")
    print(f"    Auth mode:       {_auth_labels.get(creds['auth_mode'], creds['auth_mode'])}")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    # Enable APIs
    info("Enabling required APIs...")
    for api in ["run.googleapis.com", "secretmanager.googleapis.com"]:
        run_gcloud(
            ["services", "enable", api, "--project", project, "--quiet"],
            capture=True,
        )
    ok("APIs enabled")
    print()

    if use_sm:
        _setup_secret_manager(project, creds)

    mcp_env = _build_mcp_env_vars(creds, use_secret_manager=use_sm, project=project)

    info(f"Deploying Cloud Run service (image: {image})")

    env_file_path = Path(tempfile.mktemp(suffix=".yaml"))
    try:
        env_file_path.write_text(
            "\n".join(f"{k}: '{v}'" for k, v in mcp_env.items()) + "\n",
            encoding="utf-8",
        )

        deploy_result = run_gcloud([
            "run", "deploy", service_name,
            "--image", image,
            "--region", region,
            "--platform", "managed",
            "--port", MCP_PORT,
            f"--args=--transport,streamable-http,--host,0.0.0.0,--port,{MCP_PORT}",
            "--env-vars-file", str(env_file_path),
            "--memory", "512Mi",
            "--no-cpu-throttling",
            "--allow-unauthenticated",
            "--project", project,
        ], check=False, capture=True)
    finally:
        env_file_path.unlink(missing_ok=True)

    if deploy_result.returncode != 0:
        die(f"Deployment failed:\n{deploy_result.stderr}")

    r = run_gcloud([
        "run", "services", "describe", service_name,
        "--region", region, "--format", "value(status.url)", "--project", project,
    ], capture=True)
    service_url = r.stdout.strip()
    mcp_url = f"{service_url}/mcp"

    ok(f"Deployed: {service_url}")
    print()

    _save_state({
        "deployment_type": "cloud_run",
        "project": project,
        "region": region,
        "service_name": service_name,
        "service_url": service_url,
        "mcp_url": mcp_url,
        "auth_mode": creds["auth_mode"],
        "use_secret_manager": use_sm,
    })

    # Guarantee public access is in effect AND the app is actually answering
    # before we hand a config to the MCP client. This closes the rollout-window
    # race that otherwise leaves mcp-remote stuck on a transient ingress 401.
    if creds["auth_mode"] != "none":
        _ensure_public_and_ready(service_name, region, project, mcp_url)
        print()

    _update_client_configs(mcp_url, creds)

    print("=" * 76)
    print(f"  {GREEN}Cloud Run deployment complete — {_auth_labels.get(creds['auth_mode'], '')}{NC}")
    print("=" * 76)
    print()
    print(f"  MCP URL:         {mcp_url}")
    print(f"  Image:           {image}")
    print(f"  Project:         {project}")
    print(f"  Region:          {region}")
    print(f"  Secret Manager:  {'Yes' if use_sm else 'No'}")
    print()
    print("  Next steps:")
    print("    1. Restart Claude Desktop / Cursor")
    print("    2. Ask: \"List all ZPA application segments\"")
    print()
    print("  Management:")
    print("    python gcp_mcp_operations.py status     — Check deployment")
    print("    python gcp_mcp_operations.py logs       — Stream logs")
    print("    python gcp_mcp_operations.py destroy    — Tear down")
    print()
    warn("Enterprise GCP orgs may enforce IAM policies that block public access")
    warn("to Cloud Run (constraints/iam.allowedPolicyMemberDomains). If clients")
    warn("receive 401 errors, see integrations/google/README.md for guidance on")
    warn("VPC-only ingress, Identity-Aware Proxy, or alternative deployment targets.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Deploy — GKE
# ════════════════════════════════════════════════════════════════════════


def _deploy_gke(creds: dict) -> None:
    """Deploy to Google Kubernetes Engine."""
    env = creds["env"]

    info("GKE configuration")
    project = resolve(env, "GCP_PROJECT_ID", "PROJECT_ID")
    if not project:
        project = _prompt("GCP Project ID")
    else:
        ok(f"GCP Project: {project}")

    region = resolve(env, "GCP_REGION", "REGION") or "us-central1"
    region = _prompt("GCP Region / Zone", default=region)

    # Cluster: create new or use existing
    cluster_mode = _prompt_choice(
        "GKE Cluster:",
        [
            ("new", "Create a new GKE Autopilot cluster (PoC / testing)"),
            ("existing", "Use an existing GKE cluster (production)"),
        ],
    )

    if cluster_mode == "new":
        cluster_name = _prompt("New cluster name", default="zscaler-mcp-cluster")
    else:
        cluster_name = _prompt("Existing cluster name")

    namespace = _prompt("Kubernetes namespace", default="default")
    image = _prompt("Container image", default=DOCKER_HUB_IMAGE)
    use_sm = _prompt_yes_no("Use GCP Secret Manager for credentials? (recommended)")

    sa_name = "zscaler-mcp-sa"
    print()

    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          GKE (Kubernetes)")
    print(f"    Cluster:         {cluster_name} ({'new Autopilot' if cluster_mode == 'new' else 'existing'})")
    print(f"    Image:           {image}")
    print(f"    Project:         {project}")
    print(f"    Region:          {region}")
    print(f"    Namespace:       {namespace}")
    print(f"    Secret Manager:  {'Yes' if use_sm else 'No'}")
    print(f"    Auth mode:       {creds['auth_mode']}")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    # Enable GKE API
    info("Enabling GKE API...")
    run_gcloud(
        ["services", "enable", "container.googleapis.com", "--project", project, "--quiet"],
        capture=True,
    )
    ok("GKE API enabled")
    print()

    # Create cluster if requested
    if cluster_mode == "new":
        info(f"Creating GKE Autopilot cluster '{cluster_name}' (this may take 5-10 minutes)...")
        run_gcloud([
            "container", "clusters", "create-auto", cluster_name,
            "--region", region,
            "--project", project,
        ])
        ok(f"Cluster '{cluster_name}' created")
        print()

    # Get cluster credentials
    info("Fetching GKE cluster credentials...")
    run_gcloud([
        "container", "clusters", "get-credentials", cluster_name,
        "--region", region, "--project", project,
    ])
    ok("Cluster credentials fetched")
    print()

    if use_sm:
        _setup_secret_manager(project, creds)

    mcp_env = _build_mcp_env_vars(creds, use_secret_manager=use_sm, project=project)

    # Build K8s manifest
    env_entries = "\n".join(
        f"        - name: {k}\n          value: \"{v}\"" for k, v in mcp_env.items()
    )

    manifest = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {SERVER_NAME}
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {SERVER_NAME}
  template:
    metadata:
      labels:
        app: {SERVER_NAME}
    spec:
      serviceAccountName: {sa_name}
      containers:
      - name: zscaler-mcp
        image: {image}
        args: ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "{MCP_PORT}"]
        ports:
        - containerPort: {MCP_PORT}
        env:
{env_entries}
---
apiVersion: v1
kind: Service
metadata:
  name: {SERVER_NAME}
  namespace: {namespace}
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: {MCP_PORT}
  selector:
    app: {SERVER_NAME}
"""

    manifest_path = SCRIPT_DIR / ".gke-manifest.yaml"
    manifest_path.write_text(manifest, encoding="utf-8")
    ok(f"K8s manifest written to {manifest_path}")
    print()

    # Create service account if it doesn't exist
    info(f"Ensuring K8s service account '{sa_name}'...")
    r = run_kubectl(
        ["get", "serviceaccount", sa_name, "-n", namespace],
        check=False, capture=True,
    )
    if r.returncode != 0:
        run_kubectl(["create", "serviceaccount", sa_name, "-n", namespace])
        ok(f"Service account '{sa_name}' created")
    else:
        ok(f"Service account '{sa_name}' already exists")

    # Bind Workload Identity so the K8s SA can access Secret Manager
    if use_sm:
        info("Configuring Workload Identity for Secret Manager access...")
        r = run_gcloud(
            ["projects", "describe", project, "--format", "value(projectNumber)"],
            capture=True,
        )
        project_number = r.stdout.strip()
        gcp_sa = f"{project_number}-compute@developer.gserviceaccount.com"
        wi_member = f"serviceAccount:{project}.svc.id.goog[{namespace}/{sa_name}]"

        run_gcloud([
            "iam", "service-accounts", "add-iam-policy-binding", gcp_sa,
            "--role", "roles/iam.workloadIdentityUser",
            "--member", wi_member,
            "--project", project, "--quiet",
        ], check=False, capture=True)

        run_kubectl([
            "annotate", "serviceaccount", sa_name,
            "--namespace", namespace,
            f"iam.gke.io/gcp-service-account={gcp_sa}",
            "--overwrite",
        ])
        ok(f"Workload Identity: {sa_name} → {gcp_sa}")
        print()

    # Apply manifest
    info("Applying K8s manifest...")
    run_kubectl(["apply", "-f", str(manifest_path)])
    ok("Deployment applied")
    print()

    info("Waiting for LoadBalancer external IP...")
    external_ip = ""
    for _ in range(30):
        import time
        time.sleep(10)
        r = run_kubectl([
            "get", "svc", SERVER_NAME, "-n", namespace,
            "-o", "jsonpath={.status.loadBalancer.ingress[0].ip}",
        ], check=False, capture=True)
        if r.stdout.strip():
            external_ip = r.stdout.strip()
            break
        info("  Waiting for external IP...")

    if external_ip:
        mcp_url = f"http://{external_ip}/mcp"
        ok(f"External IP: {external_ip}")
    else:
        warn("External IP not yet assigned. Check with: kubectl get svc " + SERVER_NAME)
        mcp_url = "http://<PENDING>/mcp"

    _save_state({
        "deployment_type": "gke",
        "project": project,
        "region": region,
        "cluster_name": cluster_name,
        "cluster_created": cluster_mode == "new",
        "namespace": namespace,
        "service_name": SERVER_NAME,
        "mcp_url": mcp_url,
        "external_ip": external_ip,
        "auth_mode": creds["auth_mode"],
        "use_secret_manager": use_sm,
    })

    if external_ip:
        _update_client_configs(mcp_url, creds)

    print()
    print("=" * 76)
    print(f"  {GREEN}GKE deployment complete{NC}")
    print("=" * 76)
    print()
    print(f"  MCP URL:         {mcp_url}")
    print(f"  Cluster:         {cluster_name}")
    print(f"  Namespace:       {namespace}")
    print()
    print("  Management:")
    print("    python gcp_mcp_operations.py status     — Check deployment")
    print("    python gcp_mcp_operations.py logs       — Stream logs")
    print("    python gcp_mcp_operations.py destroy    — Tear down")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Deploy — Compute Engine VM
# ════════════════════════════════════════════════════════════════════════


def _generate_vm_setup_script(creds: dict, *, mcp_port: str) -> str:
    """Generate bash setup script for VM."""
    mcp_env = _build_mcp_env_vars(creds, use_secret_manager=False, project="")
    env_lines = [f'{k}="{v}"' for k, v in mcp_env.items()]
    env_content = "\n".join(env_lines)

    return f"""#!/bin/bash
set -e

echo "=== Zscaler MCP Server Setup ==="

apt-get update
apt-get install -y python3 python3-pip python3-venv

echo "Creating application directory..."
mkdir -p /opt/zscaler-mcp
chmod 755 /opt/zscaler-mcp

echo "Writing environment file..."
cat > /opt/zscaler-mcp/env << 'ENVEOF'
{env_content}
ENVEOF
chmod 600 /opt/zscaler-mcp/env

echo "Creating systemd service..."
cat > /etc/systemd/system/zscaler-mcp.service << 'SVCEOF'
[Unit]
Description=Zscaler MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/zscaler-mcp
EnvironmentFile=/opt/zscaler-mcp/env
ExecStart=/opt/zscaler-mcp/venv/bin/zscaler-mcp --transport streamable-http --host 0.0.0.0 --port {mcp_port}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF
chmod 644 /etc/systemd/system/zscaler-mcp.service

echo "Creating Python virtual environment..."
python3 -m venv /opt/zscaler-mcp/venv
/opt/zscaler-mcp/venv/bin/pip install --upgrade pip wheel
echo "Installing zscaler-mcp package..."
/opt/zscaler-mcp/venv/bin/pip install {PYPI_PACKAGE}[gcp]

echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable zscaler-mcp.service
systemctl start zscaler-mcp.service

echo "=== Setup Complete ==="
systemctl status zscaler-mcp.service --no-pager || true
"""


def _deploy_vm(creds: dict) -> None:
    """Deploy to Compute Engine VM."""
    env = creds["env"]

    info("Compute Engine VM configuration")
    project = resolve(env, "GCP_PROJECT_ID", "PROJECT_ID")
    if not project:
        project = _prompt("GCP Project ID")
    else:
        ok(f"GCP Project: {project}")

    zone = resolve(env, "GCP_ZONE") or "us-central1-a"
    zone = _prompt("GCP Zone", default=zone)

    vm_name = _prompt("VM name", default=SERVER_NAME)
    machine_type = _prompt("Machine type", default=VM_MACHINE_TYPE)
    mcp_port = _prompt("MCP port", default=MCP_PORT)

    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          Compute Engine VM (Debian 12)")
    print(f"    Package:         {PYPI_PACKAGE} (from PyPI)")
    print(f"    Project:         {project}")
    print(f"    Zone:            {zone}")
    print(f"    VM Name:         {vm_name}")
    print(f"    Machine Type:    {machine_type}")
    print(f"    MCP Port:        {mcp_port}")
    print(f"    Auth mode:       {creds['auth_mode']}")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    # Enable API
    info("Enabling Compute Engine API...")
    run_gcloud(
        ["services", "enable", "compute.googleapis.com", "--project", project, "--quiet"],
        capture=True,
    )
    ok("API enabled")
    print()

    # Create firewall rule
    info(f"Creating firewall rule for port {mcp_port}...")
    r = run_gcloud(
        ["compute", "firewall-rules", "describe", f"allow-mcp-{mcp_port}", "--project", project],
        check=False, capture=True,
    )
    if r.returncode != 0:
        run_gcloud([
            "compute", "firewall-rules", "create", f"allow-mcp-{mcp_port}",
            "--allow", f"tcp:{mcp_port}",
            "--target-tags", "mcp-server",
            "--project", project,
        ], capture=True)
        ok(f"Firewall rule created for port {mcp_port}")
    else:
        ok("Firewall rule already exists")
    print()

    # Generate startup script
    startup_script = _generate_vm_setup_script(creds, mcp_port=mcp_port)

    startup_file = Path(tempfile.mktemp(suffix=".sh"))
    startup_file.write_text(startup_script, encoding="utf-8")

    # Create VM
    info(f"Creating VM '{vm_name}'...")
    try:
        run_gcloud([
            "compute", "instances", "create", vm_name,
            "--zone", zone,
            "--machine-type", machine_type,
            "--image-family", VM_IMAGE_FAMILY,
            "--image-project", VM_IMAGE_PROJECT,
            "--tags", "mcp-server",
            "--metadata-from-file", f"startup-script={startup_file}",
            "--project", project,
        ])
    finally:
        startup_file.unlink(missing_ok=True)

    ok(f"VM '{vm_name}' created")
    print()

    # Get external IP
    r = run_gcloud([
        "compute", "instances", "describe", vm_name,
        "--zone", zone,
        "--format", "value(networkInterfaces[0].accessConfigs[0].natIP)",
        "--project", project,
    ], capture=True)
    public_ip = r.stdout.strip()
    mcp_url = f"http://{public_ip}:{mcp_port}/mcp"

    _save_state({
        "deployment_type": "vm",
        "project": project,
        "zone": zone,
        "vm_name": vm_name,
        "public_ip": public_ip,
        "mcp_port": mcp_port,
        "mcp_url": mcp_url,
        "auth_mode": creds["auth_mode"],
    })

    _update_client_configs(mcp_url, creds)

    print("=" * 76)
    print(f"  {GREEN}Compute Engine VM deployment complete{NC}")
    print("=" * 76)
    print()
    print(f"  MCP URL:         {mcp_url}")
    print(f"  VM Name:         {vm_name}")
    print(f"  Public IP:       {public_ip}")
    print(f"  Zone:            {zone}")
    print()
    print("  The startup script is installing the MCP server (takes 2-3 minutes).")
    print("  Check progress with:")
    print("    python gcp_mcp_operations.py logs")
    print("    python gcp_mcp_operations.py ssh")
    print()
    print("  Management:")
    print("    python gcp_mcp_operations.py status     — Check deployment")
    print("    python gcp_mcp_operations.py logs       — View logs")
    print("    python gcp_mcp_operations.py ssh        — SSH into VM")
    print("    python gcp_mcp_operations.py destroy    — Tear down")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Deploy (main entry point)
# ════════════════════════════════════════════════════════════════════════


def op_deploy(args: argparse.Namespace) -> None:
    """Fully interactive deployment to GCP."""

    print_zscaler_logo()
    print("=" * 76)
    print(f"  {BOLD}Zscaler MCP Server — GCP Deployment{NC}")
    print("=" * 76)
    print()

    # Prerequisites
    info("Step 1: Checking prerequisites")
    if not shutil.which("gcloud"):
        die("gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install")

    r = run_gcloud(
        ["config", "get-value", "project"], capture=True, check=False
    )
    current_project = r.stdout.strip()
    if current_project and current_project != "(unset)":
        ok(f"gcloud CLI: project '{current_project}'")
    else:
        warn("No default project set. You'll be prompted for it.")
    print()

    # Deployment target
    deploy_target = _prompt_choice(
        "Select deployment target:",
        [
            ("cloud_run", "Cloud Run         — managed, serverless container (Docker image)"),
            ("gke", "GKE (Kubernetes)  — container on existing GKE cluster"),
            ("vm", "Compute Engine    — Debian 12 VM, self-managed (Python from PyPI)"),
        ],
    )
    ok(f"Deployment target: {deploy_target}")
    print()

    # Collect credentials (shared)
    info("Step 2: Collecting credentials and configuration")
    creds = _collect_credentials()

    # Branch to target-specific deployment
    if deploy_target == "cloud_run":
        _deploy_cloud_run(creds)
    elif deploy_target == "gke":
        _deploy_gke(creds)
    else:
        _deploy_vm(creds)


# ════════════════════════════════════════════════════════════════════════
#  Destroy
# ════════════════════════════════════════════════════════════════════════


def op_destroy(args: argparse.Namespace) -> None:
    """Tear down GCP resources."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if not deployment_type:
        die("No deployment found. Deploy first.")

    project = state.get("project", "")

    print()
    print("=" * 76)
    print(f"  {RED}DESTROY — Tearing down GCP resources{NC}")
    print("=" * 76)
    print()

    if deployment_type == "cloud_run":
        service_name = state.get("service_name", SERVER_NAME)
        region = state.get("region", "us-central1")
        warn(f"This will delete Cloud Run service: {service_name}")
        print()

        if not args.yes:
            confirm = input(f"  Type '{service_name}' to confirm: ").strip()
            if confirm != service_name:
                die("Destruction cancelled.")

        info(f"Deleting Cloud Run service '{service_name}'...")
        run_gcloud([
            "run", "services", "delete", service_name,
            "--region", region, "--project", project, "--quiet",
        ], check=False)
        ok("Cloud Run service deleted")

    elif deployment_type == "gke":
        namespace = state.get("namespace", "default")
        cluster_name = state.get("cluster_name", "")
        region = state.get("region", "us-central1")
        cluster_created = state.get("cluster_created", False)

        warn(f"This will delete K8s deployment '{SERVER_NAME}' in namespace '{namespace}'")
        if cluster_created:
            warn(f"The cluster '{cluster_name}' was created by this script and will also be deleted.")
        print()

        if not args.yes:
            confirm = input(f"  Type '{SERVER_NAME}' to confirm: ").strip()
            if confirm != SERVER_NAME:
                die("Destruction cancelled.")

        # Fetch credentials so kubectl works
        run_gcloud([
            "container", "clusters", "get-credentials", cluster_name,
            "--region", region, "--project", project,
        ], check=False, capture=True)

        info("Deleting K8s resources...")
        manifest_path = SCRIPT_DIR / ".gke-manifest.yaml"
        if manifest_path.is_file():
            run_kubectl(["delete", "-f", str(manifest_path)], check=False)
            manifest_path.unlink(missing_ok=True)
        else:
            run_kubectl(["delete", "deployment", SERVER_NAME, "-n", namespace], check=False)
            run_kubectl(["delete", "svc", SERVER_NAME, "-n", namespace], check=False)
        ok("K8s resources deleted")

        if cluster_created:
            info(f"Deleting GKE cluster '{cluster_name}' (runs in background)...")
            run_gcloud([
                "container", "clusters", "delete", cluster_name,
                "--region", region, "--project", project, "--quiet", "--async",
            ], check=False)
            ok(f"Cluster '{cluster_name}' deletion initiated")

    elif deployment_type == "vm":
        vm_name = state.get("vm_name", SERVER_NAME)
        zone = state.get("zone", "us-central1-a")
        warn(f"This will delete VM: {vm_name}")
        print()

        if not args.yes:
            confirm = input(f"  Type '{vm_name}' to confirm: ").strip()
            if confirm != vm_name:
                die("Destruction cancelled.")

        info(f"Deleting VM '{vm_name}'...")
        run_gcloud([
            "compute", "instances", "delete", vm_name,
            "--zone", zone, "--project", project, "--quiet",
        ], check=False)
        ok("VM deleted")

    # Clean up local configs
    for path_label, path in [("Claude Desktop", CLAUDE_CONFIG), ("Cursor", CURSOR_CONFIG)]:
        if path.is_file():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
                servers = config.get("mcpServers", {})
                if SERVER_NAME in servers:
                    del servers[SERVER_NAME]
                    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
                    ok(f"Removed '{SERVER_NAME}' from {path_label} config")
            except (json.JSONDecodeError, OSError):
                warn(f"Could not update {path_label} config")

    _clear_state()
    print()
    ok("Destroy complete. Restart Claude Desktop / Cursor.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Status
# ════════════════════════════════════════════════════════════════════════


def op_status(args: argparse.Namespace) -> None:
    """Show deployment status."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if not deployment_type:
        die("No deployment found. Deploy first.")

    print()

    if deployment_type == "cloud_run":
        service_name = state.get("service_name", SERVER_NAME)
        region = state.get("region", "")
        project = state.get("project", "")

        info(f"Status of Cloud Run service '{service_name}'")
        print()

        r = run_gcloud([
            "run", "services", "describe", service_name,
            "--region", region, "--project", project, "--format", "json",
        ], capture=True, check=False)

        if r.returncode != 0:
            error("Service not found.")
            return

        svc = json.loads(r.stdout)
        url = svc.get("status", {}).get("url", "?")
        conditions = svc.get("status", {}).get("conditions", [])
        ready = next((c for c in conditions if c.get("type") == "Ready"), {})

        print(f"  Service:         {service_name}")
        print(f"  URL:             {url}")
        print(f"  Ready:           {ready.get('status', '?')}")
        print(f"  MCP URL:         {state.get('mcp_url', '?')}")
        print(f"  Auth mode:       {state.get('auth_mode', '?')}")

    elif deployment_type == "gke":
        namespace = state.get("namespace", "default")
        info(f"Status of GKE deployment '{SERVER_NAME}'")
        print()
        run_kubectl(["get", "deployment", SERVER_NAME, "-n", namespace, "-o", "wide"], check=False)
        print()
        run_kubectl(["get", "svc", SERVER_NAME, "-n", namespace, "-o", "wide"], check=False)
        print()
        print(f"  MCP URL:         {state.get('mcp_url', '?')}")
        print(f"  Auth mode:       {state.get('auth_mode', '?')}")

    elif deployment_type == "vm":
        vm_name = state.get("vm_name", "")
        zone = state.get("zone", "")
        project = state.get("project", "")

        info(f"Status of VM '{vm_name}'")
        print()

        r = run_gcloud([
            "compute", "instances", "describe", vm_name,
            "--zone", zone, "--project", project, "--format", "json",
        ], capture=True, check=False)

        if r.returncode != 0:
            error("VM not found.")
            return

        vm = json.loads(r.stdout)
        status = vm.get("status", "?")
        print(f"  VM Name:         {vm_name}")
        print(f"  Public IP:       {state.get('public_ip', '?')}")
        print(f"  Status:          {status}")
        print(f"  MCP URL:         {state.get('mcp_url', '?')}")
        print(f"  Auth mode:       {state.get('auth_mode', '?')}")

    print()


# ════════════════════════════════════════════════════════════════════════
#  Logs
# ════════════════════════════════════════════════════════════════════════


def _print_cloud_run_logs(service_name: str, project: str) -> None:
    """Pull last 24h of Cloud Run logs and print one line per event.

    Format: HH:MM:SS  SEVERITY  MESSAGE
    Order: chronological (oldest first), so the latest events are at the
    bottom of the terminal — closest to your prompt, like `tail`.
    """
    log_filter = (
        f'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="{service_name}"'
    )
    info(
        f"  $ gcloud logging read '{log_filter[:60]}...' "
        f"--project {project} --freshness 24h"
    )
    r = subprocess.run(
        [
            "gcloud", "logging", "read", log_filter,
            "--project", project,
            "--freshness", "24h",
            "--order", "desc",
            "--format", "json",
        ],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        error(f"gcloud failed: {r.stderr.strip()}")
        return
    try:
        entries = json.loads(r.stdout or "[]")
    except json.JSONDecodeError as exc:
        error(f"Could not parse gcloud output as JSON: {exc}")
        return

    if not entries:
        warn("No log entries in the last 24h.")
        return

    # gcloud returned newest-first; flip so latest appears at the bottom.
    entries.reverse()

    sev_colour = {
        "DEBUG":    DIM,
        "INFO":     "",
        "NOTICE":   BLUE,
        "WARNING":  YELLOW,
        "ERROR":    RED,
        "CRITICAL": RED + BOLD,
        "ALERT":    RED + BOLD,
        "EMERGENCY": RED + BOLD,
    }

    for entry in entries:
        ts = entry.get("timestamp", "")
        # 2026-05-15T01:13:02.690123456Z → 01:13:02.690
        clock = ""
        if "T" in ts:
            tail = ts.split("T", 1)[1]
            clock = tail.split("Z", 1)[0][:12]

        severity = entry.get("severity", "INFO") or "INFO"

        # Extract the payload — Python apps log via jsonPayload, Cloud Run's
        # built-in HTTP access logs come through textPayload.
        msg = ""
        text_payload = entry.get("textPayload")
        json_payload = entry.get("jsonPayload") or {}
        if text_payload:
            msg = str(text_payload).rstrip()
        elif isinstance(json_payload, dict):
            msg = (
                json_payload.get("message")
                or json_payload.get("msg")
                or json.dumps(json_payload, separators=(",", ":"))
            )
            msg = str(msg).rstrip()
        else:
            http_request = entry.get("httpRequest") or {}
            if http_request:
                method = http_request.get("requestMethod", "")
                url = http_request.get("requestUrl", "")
                status = http_request.get("status", "")
                msg = f"{method} {url} → {status}"

        if not msg:
            continue

        colour = sev_colour.get(severity, "")
        print(f"{DIM}{clock}{NC}  {colour}{severity:<8}{NC}  {msg}")


def op_logs(args: argparse.Namespace) -> None:
    """Stream logs."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if not deployment_type:
        die("No deployment found. Deploy first.")

    if deployment_type == "cloud_run":
        service_name = state.get("service_name", SERVER_NAME)
        project = state.get("project", "")
        info(f"Reading last 24h of logs for Cloud Run service '{service_name}'...")
        print()
        _print_cloud_run_logs(service_name, project)

    elif deployment_type == "gke":
        namespace = state.get("namespace", "default")
        info(f"Streaming logs for GKE deployment '{SERVER_NAME}'...")
        info("Press Ctrl+C to stop")
        print()
        run_kubectl([
            "logs", f"deployment/{SERVER_NAME}", "-n", namespace, "--tail", "100", "-f",
        ], check=False)

    elif deployment_type == "vm":
        vm_name = state.get("vm_name", "")
        zone = state.get("zone", "")
        project = state.get("project", "")
        info(f"Fetching logs for VM '{vm_name}'...")
        print()
        r = run_gcloud([
            "compute", "ssh", vm_name,
            "--zone", zone, "--project", project,
            "--command", "sudo journalctl -u zscaler-mcp -n 100 --no-pager",
        ], check=False, capture=True)
        if r.returncode == 0:
            print(r.stdout)
        else:
            error(f"Could not fetch logs: {r.stderr}")


# ════════════════════════════════════════════════════════════════════════
#  SSH (VM only)
# ════════════════════════════════════════════════════════════════════════


def op_ssh(args: argparse.Namespace) -> None:
    """SSH into VM."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if deployment_type != "vm":
        die("SSH is only available for VM deployments.")

    vm_name = state.get("vm_name", "")
    zone = state.get("zone", "")
    project = state.get("project", "")

    info(f"Connecting to VM '{vm_name}'...")
    os.execvp("gcloud", [
        "gcloud", "compute", "ssh", vm_name,
        "--zone", zone, "--project", project,
    ])


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Zscaler MCP Server — GCP Deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "MCP Server Operations:\n"
            "  deploy         Interactive guided deployment to GCP\n"
            "  destroy        Tear down GCP resources\n"
            "  status         Show deployment status and health\n"
            "  logs           Stream container/VM logs\n"
            "  ssh            SSH into VM (VM deployments only)\n"
        ),
    )
    sub = p.add_subparsers(dest="operation")

    sub.add_parser("deploy", help="Interactive guided deployment to GCP")

    ds = sub.add_parser("destroy", help="Tear down GCP resources")
    ds.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    sub.add_parser("status", help="Show deployment status")
    sub.add_parser("logs", help="Stream logs")
    sub.add_parser("ssh", help="SSH into VM (VM deployments only)")

    return p


OPERATIONS = {
    "deploy": op_deploy,
    "destroy": op_destroy,
    "status": op_status,
    "logs": op_logs,
    "ssh": op_ssh,
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
