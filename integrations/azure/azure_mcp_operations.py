#!/usr/bin/env python3
"""
Zscaler MCP Server — Azure Deployment (Interactive)

Fully interactive deployment script supporting three deployment targets:
  1. Azure Container Apps (managed, serverless) — pulls from Docker Hub
  2. Azure Virtual Machine (Ubuntu 22.04) — installs Python library via pip
  3. Azure Kubernetes Service (AKS) — deploys to a Kubernetes cluster (PREVIEW)

All options:
  - Prompt the user for auth mode, credentials, and Azure options
  - Store secrets in Azure Key Vault (Container Apps & VM); env vars on AKS (Preview)
  - Update Claude Desktop / Cursor configs with correct auth headers
  - Provide destroy / status / logs operations

NOTE: AKS support is in PREVIEW. Cluster provisioning, K8s manifests, and
LoadBalancer Service are validated, but Workload Identity + Key Vault CSI
integration is planned for a future release. For now, AKS injects secrets
as Kubernetes environment variables on the Deployment.

Supported MCP client authentication modes:
  - OIDCProxy:  OAuth 2.1 + DCR via any OIDC provider (browser-based login)
  - JWT:        Validate JWTs against a JWKS endpoint
  - API Key:    Shared secret (auto-generated if not provided)
  - Zscaler:    Validate via Zscaler OneAPI client credentials
  - None:       No MCP client authentication (development only)

Credential resolution (first non-empty wins):
  1. Values from .env file (if the user provides a path)
  2. Interactive prompt (if no .env or value missing)
  3. Shell environment variables

Usage:
  python azure_mcp_operations.py deploy     # interactive guided deploy
  python azure_mcp_operations.py destroy    # tear down all resources
  python azure_mcp_operations.py status     # show deployment status
  python azure_mcp_operations.py logs       # stream container/VM/pod logs
  python azure_mcp_operations.py ssh        # SSH into VM (VM deployments only)
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
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SYSTEM = platform.system()

SERVER_NAME = "zscaler-mcp-server"
DOCKER_HUB_IMAGE = "zscaler/zscaler-mcp-server:latest"
PYPI_PACKAGE = "zscaler-mcp"

STATE_FILE = SCRIPT_DIR / ".azure-deploy-state.json"

VM_IMAGE = "Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest"
VM_SIZE = "Standard_B2s"
VM_ADMIN_USER = "azureuser"

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
NC = "\033[0m" if COLOURS else ""

ZSCALER_LOGO = f"""{SKY_BLUE}
  ______              _
 |___  /             | |
    / / ___  ___ __ _| | ___ _ __
   / / / __|/ __/ _` | |/ _ \\ '__|
  / /__\\__ \\ (_| (_| | |  __/ |
 /_____|___/\\___\\__,_|_|\\___|_|
{NC}"""


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


def run_az(
    args: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    cmd = ["az"] + args
    info(f"  $ az {' '.join(args[:8])}{'...' if len(args) > 8 else ''}")
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if check and r.returncode != 0:
            die(f"az command failed:\n  {r.stderr.strip()}")
        return r
    else:
        r = subprocess.run(cmd)
        if check and r.returncode != 0:
            die(f"az command failed (exit code {r.returncode})")
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
    """Return the first non-empty value from .env keys or OS env."""
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


# Words a user can type at any prompt to gracefully exit the script
# (in addition to picking the explicit "Cancel / Exit" menu entry).
_EXIT_WORDS = ("exit", "quit", "q", "cancel")


def _cancel(reason: str = "Operation cancelled by user.") -> None:
    """Friendly, idempotent exit point used by every interactive prompt
    when the user requests to bail out (either by selecting the explicit
    Cancel option or by typing ``exit`` / ``quit`` / ``q`` / ``cancel``).
    """
    print()
    info(reason)
    sys.exit(0)


def _prompt(label: str, *, default: str = "", secret: bool = False) -> str:
    """Prompt the user for a value, with optional default.

    Typing ``exit`` / ``quit`` / ``q`` / ``cancel`` at any prompt aborts
    the script gracefully.
    """
    if default:
        display = f"  {label} [{default}]: "
    else:
        display = f"  {label}: "
    while True:
        try:
            val = getpass.getpass(display) if secret else input(display)
        except (EOFError, KeyboardInterrupt):
            _cancel()
        val = val.strip()
        if val.lower() in _EXIT_WORDS and not secret:
            _cancel()
        if val:
            return val
        if default:
            return default
        error(f"  {label} is required (or type 'exit' to cancel).")


def _prompt_choice(
    title: str,
    options: list[tuple[str, str]],
    *,
    allow_exit: bool = True,
) -> str:
    """Display a numbered menu and return the chosen key.

    Unless ``allow_exit=False`` is passed, an additional "Cancel / Exit"
    entry is appended as the last numbered option so the user can bail
    out without resorting to Ctrl+C.
    """
    print()
    print(f"  {BOLD}{title}{NC}")
    print()
    display_options = list(options)
    if allow_exit:
        display_options = display_options + [("__exit__", "Cancel / Exit")]
    for idx, (_, label) in enumerate(display_options, 1):
        print(f"    [{idx}] {label}")
    print()
    while True:
        try:
            raw = input(f"  Choice [1-{len(display_options)}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            _cancel()
        if allow_exit and raw.lower() in _EXIT_WORDS:
            _cancel()
        if raw.isdigit() and 1 <= int(raw) <= len(display_options):
            key = display_options[int(raw) - 1][0]
            if key == "__exit__":
                _cancel()
            return key
        error(f"  Invalid choice: {raw}")


def _prompt_yes_no(question: str, *, default: bool = True) -> bool:
    """Yes/No prompt.  Typing ``exit`` / ``quit`` / ``q`` / ``cancel``
    aborts the script gracefully.
    """
    hint = "Y/n" if default else "y/N"
    try:
        raw = input(f"  {question} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        _cancel()
    if raw in _EXIT_WORDS:
        _cancel()
    if not raw:
        return default
    return raw in ("y", "yes")


# ── OIDCProxy inline entrypoint (for Container Apps) ─────────────────────

_INLINE_ENTRYPOINT = """
import os, sys, logging
if os.environ.get("FASTMCP_DEBUG", "").lower() in ("true", "1", "yes"):
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s %(message)s")
config_url    = os.environ["OIDCPROXY_CONFIG_URL"]
client_id     = os.environ["OIDCPROXY_CLIENT_ID"]
client_secret = os.environ["OIDCPROXY_CLIENT_SECRET"]
base_url      = os.environ["OIDCPROXY_BASE_URL"]
audience      = os.environ.get("OIDCPROXY_AUDIENCE", "zscaler-mcp-server")
host          = os.environ.get("MCP_HOST", "0.0.0.0")
port          = int(os.environ.get("MCP_PORT", "8000"))
os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "false"
os.environ["ZSCALER_MCP_ALLOW_HTTP"]   = "true"
os.environ.pop("ZSCALER_MCP_TLS_CERTFILE", None)
os.environ.pop("ZSCALER_MCP_TLS_KEYFILE", None)
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from zscaler_mcp.server import ZscalerMCPServer
auth = OIDCProxy(config_url=config_url, client_id=client_id, client_secret=client_secret, base_url=base_url, audience=audience, verify_id_token=True)
if auth.client_registration_options:
    auth.client_registration_options.valid_scopes = ["openid", "profile", "email"]
ew = os.environ.get("ZSCALER_MCP_WRITE_ENABLED", "").lower() in ("true", "1", "yes")
wt_raw = os.environ.get("ZSCALER_MCP_WRITE_TOOLS", "")
write_tools = set(t.strip() for t in wt_raw.split(",") if t.strip()) if wt_raw else None
dt = os.environ.get("ZSCALER_MCP_DISABLED_TOOLS", "")
disabled_tools = set(t.strip() for t in dt.split(",") if t.strip()) if dt else None
ds = os.environ.get("ZSCALER_MCP_DISABLED_SERVICES", "")
disabled_services = set(s.strip() for s in ds.split(",") if s.strip()) if ds else None
server = ZscalerMCPServer(auth=auth, enable_write_tools=ew, write_tools=write_tools, disabled_tools=disabled_tools, disabled_services=disabled_services)
server.run("streamable-http", host=host, port=port)
"""

_ENTRYPOINT_B64 = base64.b64encode(_INLINE_ENTRYPOINT.encode()).decode()


# ── VM setup script generator ─────────────────────────────────────────────


def _generate_vm_setup_script(
    *,
    mcp_port: str,
    zscaler_client_id: str,
    zscaler_client_secret: str,
    zscaler_vanity_domain: str,
    zscaler_customer_id: str,
    zscaler_cloud: str,
    auth_mode: str,
    oidc_domain: str = "",
    oidc_client_id: str = "",
    oidc_client_secret: str = "",
    oidc_audience: str = "",
    jwks_uri: str = "",
    jwt_issuer: str = "",
    jwt_audience: str = "",
    api_key: str = "",
    write_enabled: str = "",
    write_tools: str = "",
    disabled_tools: str = "",
    disabled_services: str = "",
    vm_public_ip: str = "",
) -> str:
    """Generate bash setup script for VM."""

    env_lines = [
        f'ZSCALER_CLIENT_ID="{zscaler_client_id}"',
        f'ZSCALER_CLIENT_SECRET="{zscaler_client_secret}"',
        f'ZSCALER_VANITY_DOMAIN="{zscaler_vanity_domain}"',
        f'ZSCALER_CUSTOMER_ID="{zscaler_customer_id}"',
        f'ZSCALER_CLOUD="{zscaler_cloud}"',
        f'MCP_PORT="{mcp_port}"',
        'ZSCALER_MCP_ALLOW_HTTP="true"',
        'ZSCALER_MCP_DISABLE_HOST_VALIDATION="true"',
    ]

    if write_enabled:
        env_lines.append(f'ZSCALER_MCP_WRITE_ENABLED="{write_enabled}"')
    if write_tools:
        env_lines.append(f'ZSCALER_MCP_WRITE_TOOLS="{write_tools}"')
    if disabled_tools:
        env_lines.append(f'ZSCALER_MCP_DISABLED_TOOLS="{disabled_tools}"')
    if disabled_services:
        env_lines.append(f'ZSCALER_MCP_DISABLED_SERVICES="{disabled_services}"')

    if auth_mode == "oidcproxy":
        config_url = f"https://{oidc_domain}/.well-known/openid-configuration"
        base_url = (
            f"http://{vm_public_ip}:{mcp_port}" if vm_public_ip else f"http://localhost:{mcp_port}"
        )
        env_lines += [
            'ZSCALER_MCP_AUTH_ENABLED="false"',
            f'OIDCPROXY_CONFIG_URL="{config_url}"',
            f'OIDCPROXY_CLIENT_ID="{oidc_client_id}"',
            f'OIDCPROXY_CLIENT_SECRET="{oidc_client_secret}"',
            f'OIDCPROXY_BASE_URL="{base_url}"',
            f'OIDCPROXY_AUDIENCE="{oidc_audience}"',
        ]
    elif auth_mode == "jwt":
        env_lines += [
            'ZSCALER_MCP_AUTH_ENABLED="true"',
            'ZSCALER_MCP_AUTH_MODE="jwt"',
            f'ZSCALER_MCP_AUTH_JWKS_URI="{jwks_uri}"',
            f'ZSCALER_MCP_AUTH_ISSUER="{jwt_issuer}"',
            f'ZSCALER_MCP_AUTH_AUDIENCE="{jwt_audience}"',
        ]
    elif auth_mode == "api-key":
        env_lines += [
            'ZSCALER_MCP_AUTH_ENABLED="true"',
            'ZSCALER_MCP_AUTH_MODE="api-key"',
            f'ZSCALER_MCP_AUTH_API_KEY="{api_key}"',
        ]
    elif auth_mode == "zscaler":
        env_lines += [
            'ZSCALER_MCP_AUTH_ENABLED="true"',
            'ZSCALER_MCP_AUTH_MODE="zscaler"',
        ]
    else:
        env_lines.append('ZSCALER_MCP_AUTH_ENABLED="false"')

    env_content = "\n".join(env_lines)

    if auth_mode == "oidcproxy":
        exec_start = '/opt/zscaler-mcp/venv/bin/python -c \'exec(__import__("base64").b64decode(__import__("os").environ["ENTRYPOINT_B64"]).decode())\''
        env_lines.append(f'ENTRYPOINT_B64="{_ENTRYPOINT_B64}"')
        env_content = "\n".join(env_lines)
    else:
        exec_start = f"/opt/zscaler-mcp/venv/bin/zscaler-mcp --transport streamable-http --host 0.0.0.0 --port {mcp_port}"

    return f"""#!/bin/bash
set -e

echo "=== Zscaler MCP Server Setup ==="

# Add deadsnakes PPA for Python 3.11
echo "Adding Python 3.11 PPA..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/zscaler-mcp
chmod 755 /opt/zscaler-mcp

# Write environment file
echo "Writing environment file..."
cat > /opt/zscaler-mcp/env << 'ENVEOF'
{env_content}
ENVEOF
chmod 600 /opt/zscaler-mcp/env

# Create systemd service file
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
ExecStart={exec_start}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF
chmod 644 /etc/systemd/system/zscaler-mcp.service

# Create Python virtual environment and install package
echo "Creating Python virtual environment..."
python3.11 -m venv /opt/zscaler-mcp/venv
/opt/zscaler-mcp/venv/bin/pip install --upgrade pip wheel
echo "Installing zscaler-mcp package..."
/opt/zscaler-mcp/venv/bin/pip install {PYPI_PACKAGE}

# Enable and start the service
echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable zscaler-mcp.service
systemctl start zscaler-mcp.service

echo "=== Setup Complete ==="
systemctl status zscaler-mcp.service --no-pager || true
"""


# ════════════════════════════════════════════════════════════════════════
#  Common credential/config collection
# ════════════════════════════════════════════════════════════════════════


def _collect_credentials(account: dict) -> dict:
    """Collect all credentials and config interactively. Returns a dict with all values."""

    # ── Credential source ─────────────────────────────────────────────
    cred_source = _prompt_choice(
        "How would you like to provide credentials?",
        [
            ("env", "From a .env file (provide file path)"),
            ("prompt", "Enter manually (interactive prompts)"),
        ],
    )

    env: dict[str, str] = {}
    if cred_source == "env":
        env_path_str = _prompt("Path to .env file", default=str(PROJECT_ROOT / ".env"))
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
            ("oidcproxy", "OIDCProxy  — OAuth 2.1 + DCR via OIDC provider (browser login)"),
            ("jwt", "JWT        — Validate tokens against a JWKS endpoint"),
            ("api-key", "API Key    — Shared secret (auto-generated if not provided)"),
            ("zscaler", "Zscaler    — Validate via OneAPI client credentials"),
            ("none", "None       — No authentication (development only)"),
        ],
    )
    ok(f"Auth mode: {auth_mode}")
    print()

    # ── Auth-mode-specific credentials ────────────────────────────────
    oidc_domain = oidc_client_id = oidc_client_secret = oidc_audience = ""
    jwks_uri = jwt_issuer = jwt_audience = ""
    api_key = ""

    if auth_mode == "oidcproxy":
        info("OIDCProxy credentials (supports Entra ID, Okta, Auth0, etc.)")
        oidc_domain = resolve(env, "OIDCPROXY_DOMAIN", "AUTH0_DOMAIN", "OIDCPROXY_AUTH0_DOMAIN")
        oidc_client_id = resolve(env, "OIDCPROXY_CLIENT_ID", "AUTH0_CLIENT_ID")
        oidc_client_secret = resolve(env, "OIDCPROXY_CLIENT_SECRET", "AUTH0_CLIENT_SECRET")
        oidc_audience = resolve(env, "OIDCPROXY_AUDIENCE", "AUTH0_AUDIENCE") or "zscaler-mcp-server"

        if not oidc_domain:
            oidc_domain = _prompt(
                "OIDC Domain (e.g. login.microsoftonline.com/<tenant>/v2.0 or tenant.auth0.com)"
            )
        else:
            ok(f"OIDC Domain: {oidc_domain}")
        if not oidc_client_id:
            oidc_client_id = _prompt("OIDC Client ID")
        else:
            ok(f"OIDC Client ID: {oidc_client_id[:12]}...")
        if not oidc_client_secret:
            oidc_client_secret = _prompt("OIDC Client Secret", secret=True)
        else:
            ok("OIDC Client Secret: ********")
        oidc_audience = _prompt("OIDC Audience / API Identifier", default=oidc_audience)

    elif auth_mode == "jwt":
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
        "oidc_domain": oidc_domain,
        "oidc_client_id": oidc_client_id,
        "oidc_client_secret": oidc_client_secret,
        "oidc_audience": oidc_audience,
        "jwks_uri": jwks_uri,
        "jwt_issuer": jwt_issuer,
        "jwt_audience": jwt_audience,
        "api_key": api_key,
        "write_enabled": write_enabled,
        "write_tools": write_tools,
        "disabled_tools": disabled_tools,
        "disabled_services": disabled_services,
    }


def _setup_keyvault(
    account: dict,
    resource_group: str,
    location: str,
    keyvault_name: str,
    kv_choice: str,
    creds: dict,
) -> None:
    """Create or verify Key Vault and store secrets."""
    info("Setting up Key Vault")
    if kv_choice == "new":
        r = run_az(
            ["keyvault", "show", "--name", keyvault_name, "--output", "none"],
            check=False,
            capture=True,
        )
        if r.returncode != 0:
            r_del = run_az(
                ["keyvault", "show-deleted", "--name", keyvault_name, "--output", "none"],
                check=False,
                capture=True,
            )
            if r_del.returncode == 0:
                warn(f"  Soft-deleted vault '{keyvault_name}' found — purging...")
                run_az(["keyvault", "purge", "--name", keyvault_name, "--location", location])
                ok("  Purged soft-deleted vault")

            run_az(
                [
                    "keyvault",
                    "create",
                    "--name",
                    keyvault_name,
                    "--resource-group",
                    resource_group,
                    "--location",
                    location,
                    "--enable-rbac-authorization",
                    "true",
                    "--output",
                    "none",
                ]
            )
            ok(f"Key Vault '{keyvault_name}' created")
        else:
            ok(f"Key Vault '{keyvault_name}' already exists")
    else:
        r = run_az(
            ["keyvault", "show", "--name", keyvault_name, "--output", "none"],
            check=False,
            capture=True,
        )
        if r.returncode != 0:
            die(f"Key Vault '{keyvault_name}' not found. Verify the name and try again.")
        ok(f"Key Vault '{keyvault_name}' found")

    # Assign RBAC role
    info("  Assigning Key Vault Secrets Officer role...")
    r = run_az(
        ["ad", "signed-in-user", "show", "--query", "id", "--output", "tsv"],
        capture=True,
        check=False,
    )
    user_oid = r.stdout.strip()
    if user_oid:
        kv_scope = (
            f"/subscriptions/{account['id']}/resourceGroups/{resource_group}"
            f"/providers/Microsoft.KeyVault/vaults/{keyvault_name}"
        )
        run_az(
            [
                "role",
                "assignment",
                "create",
                "--role",
                "Key Vault Secrets Officer",
                "--assignee",
                user_oid,
                "--scope",
                kv_scope,
                "--output",
                "none",
            ],
            check=False,
            capture=True,
        )
        ok("  RBAC role assigned")
        if kv_choice == "new":
            info("  Waiting for RBAC propagation (30s)...")
            time.sleep(30)
    else:
        warn("  Could not determine user ID — secret writes may fail")

    # Store secrets
    info("  Storing secrets in Key Vault...")
    kv_secrets: dict[str, str] = {
        "zscaler-client-id": creds["zscaler_client_id"],
        "zscaler-client-secret": creds["zscaler_client_secret"],
        "zscaler-vanity-domain": creds["zscaler_vanity_domain"],
        "zscaler-customer-id": creds["zscaler_customer_id"],
    }
    if creds["auth_mode"] == "oidcproxy":
        kv_secrets["oidcproxy-client-id"] = creds["oidc_client_id"]
        kv_secrets["oidcproxy-client-secret"] = creds["oidc_client_secret"]
    elif creds["auth_mode"] == "api-key":
        kv_secrets["mcp-api-key"] = creds["api_key"]

    for name, value in kv_secrets.items():
        run_az(
            [
                "keyvault",
                "secret",
                "set",
                "--vault-name",
                keyvault_name,
                "--name",
                name,
                "--value",
                value,
                "--output",
                "none",
            ],
            capture=True,
        )
    ok(f"All secrets stored in Key Vault ({len(kv_secrets)} secrets)")
    print()


def _update_client_configs(mcp_url: str, auth_mode: str, creds: dict) -> None:
    """Update Claude Desktop and Cursor configs."""
    auth_header: str | None = None
    if auth_mode == "api-key":
        auth_header = f"Bearer {creds['api_key']}"
    elif auth_mode == "zscaler":
        b64 = base64.b64encode(
            f"{creds['zscaler_client_id']}:{creds['zscaler_client_secret']}".encode()
        ).decode()
        auth_header = f"Basic {b64}"

    info("Updating Claude Desktop config")

    # Check if URL is non-localhost HTTP (requires --allow-http flag for mcp-remote)
    needs_allow_http = mcp_url.startswith("http://") and not any(
        h in mcp_url for h in ["localhost", "127.0.0.1", "::1"]
    )

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
#  Deploy — Container Apps
# ════════════════════════════════════════════════════════════════════════


def _build_kv_secret_map(auth_mode: str) -> list[tuple[str, str]]:
    """Return [(env_var_name, kv_secret_name), ...] for sensitive values that
    should be stored in Key Vault when the user picks the Key Vault storage
    option. Non-sensitive values (URLs, ports, audiences) stay as plain env
    vars regardless of storage choice."""
    secret_map: list[tuple[str, str]] = [
        ("ZSCALER_CLIENT_ID", "zscaler-client-id"),
        ("ZSCALER_CLIENT_SECRET", "zscaler-client-secret"),
        ("ZSCALER_VANITY_DOMAIN", "zscaler-vanity-domain"),
        ("ZSCALER_CUSTOMER_ID", "zscaler-customer-id"),
    ]
    if auth_mode == "oidcproxy":
        secret_map += [
            ("OIDCPROXY_CLIENT_ID", "oidcproxy-client-id"),
            ("OIDCPROXY_CLIENT_SECRET", "oidcproxy-client-secret"),
        ]
    elif auth_mode == "api-key":
        secret_map.append(("ZSCALER_MCP_AUTH_API_KEY", "mcp-api-key"))
    return secret_map


def _setup_containerapp_keyvault_refs(
    *,
    account: dict,
    container_app_name: str,
    resource_group: str,
    keyvault_name: str,
    auth_mode: str,
) -> None:
    """Switch a Container App from inline env vars to Key Vault secret
    references. Enables system-assigned managed identity on the app, grants
    it 'Key Vault Secrets User' on the vault, defines Container Apps
    `keyvaultref:` secrets, and updates the env vars to use `secretref:`.
    """
    secret_map = _build_kv_secret_map(auth_mode)

    info("Switching Container App to Key Vault secret references")

    # Step 1 — enable system-assigned managed identity on the Container App
    info("  Enabling system-assigned managed identity...")
    r = run_az(
        [
            "containerapp",
            "identity",
            "assign",
            "--name",
            container_app_name,
            "--resource-group",
            resource_group,
            "--system-assigned",
            "--output",
            "json",
        ],
        capture=True,
    )
    try:
        identity = json.loads(r.stdout) if r.stdout.strip() else {}
    except json.JSONDecodeError:
        identity = {}
    principal_id = identity.get("principalId", "")
    if not principal_id:
        # Fall back to a follow-up show
        r2 = run_az(
            [
                "containerapp",
                "show",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--query",
                "identity.principalId",
                "--output",
                "tsv",
            ],
            capture=True,
            check=False,
        )
        principal_id = r2.stdout.strip()
    if not principal_id:
        die("Could not retrieve the Container App's managed identity principalId.")
    ok(f"  Managed identity principal ID: {principal_id}")

    # Step 2 — grant Key Vault Secrets User role to the MI
    info("  Granting 'Key Vault Secrets User' role on the vault...")
    kv_scope = (
        f"/subscriptions/{account['id']}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.KeyVault/vaults/{keyvault_name}"
    )
    run_az(
        [
            "role",
            "assignment",
            "create",
            "--role",
            "Key Vault Secrets User",
            "--assignee-object-id",
            principal_id,
            "--assignee-principal-type",
            "ServicePrincipal",
            "--scope",
            kv_scope,
            "--output",
            "none",
        ],
        check=False,
        capture=True,
    )
    ok("  RBAC role assigned")

    # Step 3 — wait for RBAC propagation
    info("  Waiting for RBAC propagation (45s)...")
    time.sleep(45)

    # Step 4 — bind Container Apps secrets to Key Vault
    info("  Defining Container App secrets bound to Key Vault...")
    secrets_args = [
        f"{secret_name}=keyvaultref:https://{keyvault_name}.vault.azure.net/secrets/{secret_name},"
        f"identityref:system"
        for _, secret_name in secret_map
    ]
    run_az(
        [
            "containerapp",
            "secret",
            "set",
            "--name",
            container_app_name,
            "--resource-group",
            resource_group,
            "--secrets",
            *secrets_args,
            "--output",
            "none",
        ]
    )
    ok(f"  {len(secret_map)} secrets now resolved from Key Vault at runtime")

    # Step 5 — update env vars to use secret references
    info("  Updating Container App env vars to use Key Vault secret references...")
    env_var_args = [f"{env_name}=secretref:{secret_name}" for env_name, secret_name in secret_map]
    run_az(
        [
            "containerapp",
            "update",
            "--name",
            container_app_name,
            "--resource-group",
            resource_group,
            "--set-env-vars",
            *env_var_args,
            "--output",
            "none",
        ]
    )
    ok("  Env vars now reference Key Vault secrets (revision recreated)")
    print()


def _deploy_container_app(account: dict, creds: dict) -> None:
    """Deploy to Azure Container Apps."""
    env = creds["env"]
    suffix = _secrets.token_hex(3)

    info("Azure Container Apps configuration")
    location = _prompt("Azure region", default=resolve(env, "AZURE_LOCATION") or "eastus")
    resource_group = _prompt(
        "Resource group name",
        default=resolve(env, "AZURE_RESOURCE_GROUP") or f"zscaler-mcp-rg-{suffix}",
    )
    container_app_env_name = f"zscaler-mcp-env-{suffix}"
    container_app_name = _prompt(
        "Container App name",
        default=resolve(env, "AZURE_CONTAINER_APP") or f"zscaler-mcp-{suffix}",
    )
    mcp_port = _prompt("MCP server port", default=resolve(env, "MCP_PORT") or "8000")
    print()

    # Credential storage strategy
    info("Credential storage")
    storage_choice = _prompt_choice(
        "How should credentials be stored and injected into the container?",
        [
            (
                "keyvault",
                "Azure Key Vault (recommended for production)  — secrets stored in KV,"
                " pulled at runtime via Container Apps secret references",
            ),
            (
                "envvars",
                "Direct environment variables (PoC / dev)       — credentials injected"
                " as plain env vars at deploy time, no Key Vault provisioned",
            ),
        ],
    )

    keyvault_name = ""
    kv_choice = ""
    if storage_choice == "keyvault":
        info("Azure Key Vault")
        kv_choice = _prompt_choice(
            "Key Vault for storing secrets:",
            [
                ("new", "Create a new Key Vault"),
                ("existing", "Use an existing Key Vault"),
            ],
        )
        if kv_choice == "existing":
            keyvault_name = _prompt("Existing Key Vault name")
        else:
            keyvault_name = _prompt(
                "New Key Vault name",
                default=resolve(env, "AZURE_KEYVAULT_NAME") or f"zscalermcpkv{suffix}",
            )
    else:
        warn("Credentials will be passed as plain environment variables on the Container App.")
        warn("  They are visible to anyone with read access via 'az containerapp show'.")
        warn("  For production, re-run and choose the Key Vault option.")
    print()

    # Confirmation
    auth_mode = creds["auth_mode"]
    _auth_labels = {
        "oidcproxy": f"OIDCProxy ({creds['oidc_domain']})",
        "jwt": f"JWT (JWKS: {creds['jwks_uri']})",
        "api-key": "API Key (shared secret)",
        "zscaler": "Zscaler (OneAPI credentials)",
        "none": "None (no auth)",
    }

    if storage_choice == "keyvault":
        storage_label = (
            f"Azure Key Vault — {keyvault_name} "
            f"({'new' if kv_choice == 'new' else 'existing'}); runtime secret refs"
        )
    else:
        storage_label = "Plain env vars (no Key Vault)"

    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          Azure Container Apps")
    print(f"    Image:           {DOCKER_HUB_IMAGE}")
    print(f"    Resource Group:  {resource_group}")
    print(f"    Location:        {location}")
    print(f"    Credentials:     {storage_label}")
    print(f"    Container App:   {container_app_name}")
    print(f"    Auth mode:       {_auth_labels[auth_mode]}")
    print(f"    Zscaler Cloud:   {creds['zscaler_cloud']}")
    print(f"    Port:            {mcp_port}")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    # Create resource group
    info("Creating resource group")
    run_az(
        ["group", "create", "--name", resource_group, "--location", location, "--output", "none"]
    )
    ok(f"Resource group '{resource_group}' ready")
    print()

    # Key Vault (only when the user chose the keyvault path)
    if storage_choice == "keyvault":
        _setup_keyvault(account, resource_group, location, keyvault_name, kv_choice, creds)

    # Container Apps environment
    info("Creating Container Apps environment")
    r = run_az(
        [
            "containerapp",
            "env",
            "show",
            "--name",
            container_app_env_name,
            "--resource-group",
            resource_group,
            "--output",
            "none",
        ],
        check=False,
        capture=True,
    )
    if r.returncode != 0:
        run_az(
            [
                "containerapp",
                "env",
                "create",
                "--name",
                container_app_env_name,
                "--resource-group",
                resource_group,
                "--location",
                location,
                "--output",
                "none",
            ]
        )
        ok(f"Container Apps environment '{container_app_env_name}' created")
    else:
        ok(f"Container Apps environment '{container_app_env_name}' already exists")
    print()

    # Deploy Container App
    info(f"Deploying Container App (image: {DOCKER_HUB_IMAGE})")

    r = run_az(
        [
            "containerapp",
            "show",
            "--name",
            container_app_name,
            "--resource-group",
            resource_group,
            "--output",
            "none",
        ],
        check=False,
        capture=True,
    )
    app_exists = r.returncode == 0

    # Build env vars
    optional_env: list[str] = []
    if creds["zscaler_cloud"]:
        optional_env.append(f"ZSCALER_CLOUD={creds['zscaler_cloud']}")
    if creds["write_enabled"]:
        optional_env.append(f"ZSCALER_MCP_WRITE_ENABLED={creds['write_enabled']}")
    if creds["write_tools"]:
        optional_env.append(f"ZSCALER_MCP_WRITE_TOOLS={creds['write_tools']}")
    if creds["disabled_tools"]:
        optional_env.append(f"ZSCALER_MCP_DISABLED_TOOLS={creds['disabled_tools']}")
    if creds["disabled_services"]:
        optional_env.append(f"ZSCALER_MCP_DISABLED_SERVICES={creds['disabled_services']}")

    env_vars_list = [
        "ZSCALER_MCP_ALLOW_HTTP=true",
        "ZSCALER_MCP_DISABLE_HOST_VALIDATION=true",
        "MCP_HOST=0.0.0.0",
        f"MCP_PORT={mcp_port}",
        f"ZSCALER_CLIENT_ID={creds['zscaler_client_id']}",
        f"ZSCALER_CLIENT_SECRET={creds['zscaler_client_secret']}",
        f"ZSCALER_VANITY_DOMAIN={creds['zscaler_vanity_domain']}",
        f"ZSCALER_CUSTOMER_ID={creds['zscaler_customer_id']}",
        *optional_env,
    ]

    use_inline_entrypoint = auth_mode == "oidcproxy"
    config_url = (
        f"https://{creds['oidc_domain']}/.well-known/openid-configuration"
        if auth_mode == "oidcproxy"
        else ""
    )

    if auth_mode == "oidcproxy":
        placeholder_base_url = "https://placeholder.azurecontainerapps.io"
        env_vars_list += [
            "ZSCALER_MCP_AUTH_ENABLED=false",
            f"OIDCPROXY_CONFIG_URL={config_url}",
            f"OIDCPROXY_CLIENT_ID={creds['oidc_client_id']}",
            f"OIDCPROXY_CLIENT_SECRET={creds['oidc_client_secret']}",
            f"OIDCPROXY_BASE_URL={placeholder_base_url}",
            f"OIDCPROXY_AUDIENCE={creds['oidc_audience']}",
            f"ENTRYPOINT_B64={_ENTRYPOINT_B64}",
        ]
    elif auth_mode == "jwt":
        env_vars_list += [
            "ZSCALER_MCP_AUTH_ENABLED=true",
            "ZSCALER_MCP_AUTH_MODE=jwt",
            f"ZSCALER_MCP_AUTH_JWKS_URI={creds['jwks_uri']}",
            f"ZSCALER_MCP_AUTH_ISSUER={creds['jwt_issuer']}",
            f"ZSCALER_MCP_AUTH_AUDIENCE={creds['jwt_audience']}",
        ]
    elif auth_mode == "api-key":
        env_vars_list += [
            "ZSCALER_MCP_AUTH_ENABLED=true",
            "ZSCALER_MCP_AUTH_MODE=api-key",
            f"ZSCALER_MCP_AUTH_API_KEY={creds['api_key']}",
        ]
    elif auth_mode == "zscaler":
        env_vars_list += [
            "ZSCALER_MCP_AUTH_ENABLED=true",
            "ZSCALER_MCP_AUTH_MODE=zscaler",
        ]
    else:
        env_vars_list += ["ZSCALER_MCP_AUTH_ENABLED=false"]

    if app_exists:
        info("  Container App exists — updating...")
        run_az(
            [
                "containerapp",
                "update",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--image",
                DOCKER_HUB_IMAGE,
                "--set-env-vars",
                *env_vars_list,
                "--output",
                "none",
            ]
        )
    else:
        info("  Creating new Container App...")
        run_az(
            [
                "containerapp",
                "create",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--environment",
                container_app_env_name,
                "--image",
                DOCKER_HUB_IMAGE,
                "--target-port",
                mcp_port,
                "--ingress",
                "external",
                "--min-replicas",
                "1",
                "--max-replicas",
                "3",
                "--cpu",
                "0.5",
                "--memory",
                "1Gi",
                "--env-vars",
                *env_vars_list,
                "--output",
                "none",
            ]
        )

    # Apply command override
    info("  Applying command override...")
    r = run_az(
        [
            "containerapp",
            "show",
            "--name",
            container_app_name,
            "--resource-group",
            resource_group,
            "--output",
            "json",
        ],
        capture=True,
    )
    app_spec = json.loads(r.stdout)
    containers = app_spec.get("properties", {}).get("template", {}).get("containers", [])
    if not containers:
        die("Could not find container spec")

    if use_inline_entrypoint:
        containers[0]["command"] = ["python"]
        containers[0]["args"] = [
            "-c",
            "import base64,os;exec(base64.b64decode(os.environ['ENTRYPOINT_B64']).decode())",
        ]
    else:
        containers[0]["command"] = ["/app/.venv/bin/zscaler-mcp"]
        containers[0]["args"] = [
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            mcp_port,
        ]

    yaml_path = os.path.join(tempfile.gettempdir(), f"containerapp-{container_app_name}.json")
    try:
        with open(yaml_path, "w") as f:
            json.dump(app_spec, f)
        run_az(
            [
                "containerapp",
                "update",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--yaml",
                yaml_path,
                "--output",
                "none",
            ]
        )
    finally:
        if os.path.exists(yaml_path):
            os.unlink(yaml_path)

    ok(f"Container App '{container_app_name}' deployed")
    print()

    # Get FQDN
    info("Getting Container App URL")
    r = run_az(
        [
            "containerapp",
            "show",
            "--name",
            container_app_name,
            "--resource-group",
            resource_group,
            "--query",
            "properties.configuration.ingress.fqdn",
            "--output",
            "tsv",
        ],
        capture=True,
    )
    fqdn = r.stdout.strip()
    if not fqdn:
        die("Could not retrieve Container App FQDN")

    mcp_url = f"https://{fqdn}/mcp"
    ok(f"FQDN: {fqdn}")
    ok(f"MCP endpoint: {mcp_url}")

    if auth_mode == "oidcproxy":
        real_base_url = f"https://{fqdn}"
        info("  Updating OIDCPROXY_BASE_URL...")
        run_az(
            [
                "containerapp",
                "update",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--set-env-vars",
                f"OIDCPROXY_BASE_URL={real_base_url}",
                "--output",
                "none",
            ],
            capture=True,
        )
        ok("OIDCProxy base_url updated")

        azure_callback = f"https://{fqdn}/auth/callback"
        print()
        warn(
            f"{BOLD}ACTION REQUIRED:{NC}{YELLOW} Add this callback URL to your identity provider:{NC}"
        )
        warn(f"  {BOLD}{azure_callback}{NC}")
    print()

    # Switch to Key Vault secret references (if user chose KV storage)
    if storage_choice == "keyvault":
        _setup_containerapp_keyvault_refs(
            account=account,
            container_app_name=container_app_name,
            resource_group=resource_group,
            keyvault_name=keyvault_name,
            auth_mode=auth_mode,
        )

    # Save state
    _save_state(
        {
            "deployment_type": "container_app",
            "resource_group": resource_group,
            "location": location,
            "credential_storage": storage_choice,
            "keyvault_name": keyvault_name,
            "container_app_env": container_app_env_name,
            "container_app": container_app_name,
            "fqdn": fqdn,
            "mcp_url": mcp_url,
            "auth_mode": auth_mode,
            "suffix": suffix,
        }
    )

    # Wait for healthy
    info("Waiting for container to become healthy")
    for attempt in range(12):
        r = run_az(
            [
                "containerapp",
                "show",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--query",
                "properties.runningStatus",
                "--output",
                "tsv",
            ],
            capture=True,
            check=False,
        )
        status = r.stdout.strip()
        if status and "running" in status.lower():
            ok(f"Container is running (status: {status})")
            break
        info(f"  Waiting... (attempt {attempt + 1}/12)")
        time.sleep(10)
    else:
        warn("Container may not be fully ready. Check: python azure_mcp_operations.py logs")
    print()

    # Update client configs
    _update_client_configs(mcp_url, auth_mode, creds)

    # Summary
    print("=" * 76)
    print(f"  {GREEN}Container Apps deployment complete — {_auth_labels[auth_mode]}{NC}")
    print("=" * 76)
    print()
    print(f"  MCP URL:         {mcp_url}")
    print(f"  Image:           {DOCKER_HUB_IMAGE}")
    print(f"  Resource Group:  {resource_group}")
    print(f"  Container App:   {container_app_name}")
    if storage_choice == "keyvault":
        print(f"  Key Vault:       {keyvault_name} (runtime secret refs)")
    else:
        print("  Credentials:     Plain env vars (no Key Vault)")
    print(f"  Auth mode:       {_auth_labels[auth_mode]}")

    if auth_mode == "api-key":
        print(f"  API Key:         {creds['api_key']}")
    elif auth_mode == "oidcproxy":
        print(f"  OIDC Domain:     {creds['oidc_domain']}")
    elif auth_mode == "jwt":
        print(f"  JWKS URI:        {creds['jwks_uri']}")

    print()
    print(f"  {BOLD}Next steps:{NC}")
    if auth_mode == "oidcproxy":
        print(f"    1. {BOLD}Add the callback URL to your identity provider{NC} (see above)")
        print("    2. Restart Claude Desktop — browser login will open")
    elif auth_mode == "jwt":
        print(f"    1. {BOLD}Obtain a valid JWT{NC} from your identity provider")
        print("    2. Update Claude/Cursor config with: Authorization: Bearer <JWT>")
    elif auth_mode in ("api-key", "zscaler"):
        print("    1. Restart Claude Desktop — auth headers are pre-configured")
    else:
        print("    1. Restart Claude Desktop / Cursor")
    print()
    print("  Management:")
    print("    python azure_mcp_operations.py status     — Check deployment health")
    print("    python azure_mcp_operations.py logs       — Stream container logs")
    print("    python azure_mcp_operations.py destroy    — Tear down all resources")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Deploy — Virtual Machine
# ════════════════════════════════════════════════════════════════════════


def _deploy_vm(account: dict, creds: dict) -> None:
    """Deploy to Azure Virtual Machine (Ubuntu 22.04)."""
    env = creds["env"]
    suffix = _secrets.token_hex(3)

    info("Azure Virtual Machine configuration")
    location = _prompt("Azure region", default=resolve(env, "AZURE_LOCATION") or "eastus")
    resource_group = _prompt(
        "Resource group name",
        default=resolve(env, "AZURE_RESOURCE_GROUP") or f"zscaler-mcp-rg-{suffix}",
    )
    vm_name = _prompt(
        "VM name",
        default=resolve(env, "AZURE_VM_NAME") or f"zscaler-mcp-vm-{suffix}",
    )
    vm_size = _prompt("VM size", default=VM_SIZE)
    mcp_port = _prompt("MCP server port", default=resolve(env, "MCP_PORT") or "8000")
    print()

    # Key Vault
    info("Azure Key Vault")
    kv_choice = _prompt_choice(
        "Key Vault for storing secrets:",
        [
            ("new", "Create a new Key Vault"),
            ("existing", "Use an existing Key Vault"),
        ],
    )
    if kv_choice == "existing":
        keyvault_name = _prompt("Existing Key Vault name")
    else:
        keyvault_name = _prompt(
            "New Key Vault name",
            default=resolve(env, "AZURE_KEYVAULT_NAME") or f"zscalermcpkv{suffix}",
        )
    print()

    # SSH key
    info("SSH access")
    ssh_key_path = Path.home() / ".ssh" / "id_rsa.pub"
    if ssh_key_path.is_file():
        use_existing_key = _prompt_yes_no(f"Use existing SSH key ({ssh_key_path})?")
        if use_existing_key:
            ssh_public_key = ssh_key_path.read_text().strip()
        else:
            ssh_public_key = _prompt("SSH public key (paste the full key)")
    else:
        warn(f"No SSH key found at {ssh_key_path}")
        generate_key = _prompt_yes_no("Generate a new SSH key pair?")
        if generate_key:
            info("Generating SSH key pair...")
            run_cmd(
                [
                    "ssh-keygen",
                    "-t",
                    "rsa",
                    "-b",
                    "4096",
                    "-f",
                    str(ssh_key_path.with_suffix("")),
                    "-N",
                    "",
                ]
            )
            ssh_public_key = ssh_key_path.read_text().strip()
            ok(f"SSH key generated: {ssh_key_path}")
        else:
            ssh_public_key = _prompt("SSH public key (paste the full key)")
    print()

    # Confirmation
    auth_mode = creds["auth_mode"]
    _auth_labels = {
        "oidcproxy": f"OIDCProxy ({creds['oidc_domain']})",
        "jwt": f"JWT (JWKS: {creds['jwks_uri']})",
        "api-key": "API Key (shared secret)",
        "zscaler": "Zscaler (OneAPI credentials)",
        "none": "None (no auth)",
    }

    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          Azure Virtual Machine (Ubuntu 22.04)")
    print(f"    Package:         {PYPI_PACKAGE} (from PyPI)")
    print(f"    Resource Group:  {resource_group}")
    print(f"    Location:        {location}")
    print(f"    VM Name:         {vm_name}")
    print(f"    VM Size:         {vm_size}")
    print(f"    Key Vault:       {keyvault_name} ({'new' if kv_choice == 'new' else 'existing'})")
    print(f"    Auth mode:       {_auth_labels[auth_mode]}")
    print(f"    Zscaler Cloud:   {creds['zscaler_cloud']}")
    print(f"    Port:            {mcp_port}")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    # Create resource group
    info("Creating resource group")
    run_az(
        ["group", "create", "--name", resource_group, "--location", location, "--output", "none"]
    )
    ok(f"Resource group '{resource_group}' ready")
    print()

    # Key Vault
    _setup_keyvault(account, resource_group, location, keyvault_name, kv_choice, creds)

    # Create NSG
    nsg_name = f"{vm_name}-nsg"
    info(f"Creating Network Security Group '{nsg_name}'")
    run_az(
        [
            "network",
            "nsg",
            "create",
            "--name",
            nsg_name,
            "--resource-group",
            resource_group,
            "--location",
            location,
            "--output",
            "none",
        ]
    )
    ok(f"NSG '{nsg_name}' created")

    # Add NSG rules
    info("  Adding SSH rule (port 22)...")
    run_az(
        [
            "network",
            "nsg",
            "rule",
            "create",
            "--nsg-name",
            nsg_name,
            "--resource-group",
            resource_group,
            "--name",
            "AllowSSH",
            "--priority",
            "1000",
            "--destination-port-ranges",
            "22",
            "--access",
            "Allow",
            "--protocol",
            "Tcp",
            "--direction",
            "Inbound",
            "--output",
            "none",
        ]
    )
    ok("  SSH rule added")

    info(f"  Adding MCP rule (port {mcp_port})...")
    run_az(
        [
            "network",
            "nsg",
            "rule",
            "create",
            "--nsg-name",
            nsg_name,
            "--resource-group",
            resource_group,
            "--name",
            "AllowMCP",
            "--priority",
            "1010",
            "--destination-port-ranges",
            mcp_port,
            "--access",
            "Allow",
            "--protocol",
            "Tcp",
            "--direction",
            "Inbound",
            "--output",
            "none",
        ]
    )
    ok(f"  MCP rule added (port {mcp_port})")
    print()

    # Create public IP
    public_ip_name = f"{vm_name}-ip"
    info(f"Creating public IP '{public_ip_name}'")
    run_az(
        [
            "network",
            "public-ip",
            "create",
            "--name",
            public_ip_name,
            "--resource-group",
            resource_group,
            "--location",
            location,
            "--allocation-method",
            "Static",
            "--sku",
            "Standard",
            "--output",
            "none",
        ]
    )
    r = run_az(
        [
            "network",
            "public-ip",
            "show",
            "--name",
            public_ip_name,
            "--resource-group",
            resource_group,
            "--query",
            "ipAddress",
            "--output",
            "tsv",
        ],
        capture=True,
    )
    public_ip = r.stdout.strip()
    ok(f"Public IP: {public_ip}")
    print()

    # Create VM (without custom-data — we'll run setup script after)
    info(f"Creating VM '{vm_name}' (this may take a few minutes)")
    run_az(
        [
            "vm",
            "create",
            "--name",
            vm_name,
            "--resource-group",
            resource_group,
            "--location",
            location,
            "--image",
            VM_IMAGE,
            "--size",
            vm_size,
            "--admin-username",
            VM_ADMIN_USER,
            "--ssh-key-values",
            ssh_public_key,
            "--public-ip-address",
            public_ip_name,
            "--nsg",
            nsg_name,
            "--output",
            "none",
        ]
    )
    ok(f"VM '{vm_name}' created")
    print()

    mcp_url = f"http://{public_ip}:{mcp_port}/mcp"

    # Save state early so we can destroy if setup fails
    _save_state(
        {
            "deployment_type": "vm",
            "resource_group": resource_group,
            "location": location,
            "keyvault_name": keyvault_name,
            "vm_name": vm_name,
            "public_ip": public_ip,
            "mcp_url": mcp_url,
            "auth_mode": auth_mode,
            "mcp_port": mcp_port,
            "suffix": suffix,
        }
    )

    # Generate setup script
    info("Running setup script on VM (this takes 2-4 minutes)...")
    info("  Installing Python 3.11, creating venv, installing zscaler-mcp")
    setup_script = _generate_vm_setup_script(
        mcp_port=mcp_port,
        zscaler_client_id=creds["zscaler_client_id"],
        zscaler_client_secret=creds["zscaler_client_secret"],
        zscaler_vanity_domain=creds["zscaler_vanity_domain"],
        zscaler_customer_id=creds["zscaler_customer_id"],
        zscaler_cloud=creds["zscaler_cloud"],
        auth_mode=auth_mode,
        oidc_domain=creds["oidc_domain"],
        oidc_client_id=creds["oidc_client_id"],
        oidc_client_secret=creds["oidc_client_secret"],
        oidc_audience=creds["oidc_audience"],
        jwks_uri=creds["jwks_uri"],
        jwt_issuer=creds["jwt_issuer"],
        jwt_audience=creds["jwt_audience"],
        api_key=creds["api_key"],
        write_enabled=creds["write_enabled"],
        write_tools=creds["write_tools"],
        disabled_tools=creds["disabled_tools"],
        disabled_services=creds["disabled_services"],
        vm_public_ip=public_ip,
    )

    # Write script to temp file
    script_path = os.path.join(tempfile.gettempdir(), f"setup-{vm_name}.sh")
    with open(script_path, "w") as f:
        f.write(setup_script)

    # Run the setup script via az vm run-command
    try:
        r = run_az(
            [
                "vm",
                "run-command",
                "invoke",
                "--name",
                vm_name,
                "--resource-group",
                resource_group,
                "--command-id",
                "RunShellScript",
                "--scripts",
                f"@{script_path}",
            ],
            capture=True,
            check=False,
        )
        # Parse the output to show results
        try:
            output = json.loads(r.stdout)
            stdout_msg = output.get("value", [{}])[0].get("message", "")
            if "=== Setup Complete ===" in stdout_msg:
                ok("Setup script completed successfully")
                # Extract and show service status
                if "Active: active" in stdout_msg or "active (running)" in stdout_msg:
                    ok("MCP server is running")
                else:
                    warn(
                        "Service may not be running yet. Check with: python azure_mcp_operations.py logs"
                    )
            else:
                warn("Setup script output:")
                print(stdout_msg[:2000] if len(stdout_msg) > 2000 else stdout_msg)
        except (json.JSONDecodeError, KeyError, IndexError):
            if r.returncode == 0:
                ok("Setup script executed")
            else:
                warn("Setup script may have issues. Check logs on VM.")
    finally:
        if os.path.exists(script_path):
            os.unlink(script_path)
    print()

    # Update client configs
    _update_client_configs(mcp_url, auth_mode, creds)

    # OIDC callback warning for OIDCProxy
    if auth_mode == "oidcproxy":
        callback_url = f"http://{public_ip}:{mcp_port}/auth/callback"
        print()
        warn(
            f"{BOLD}ACTION REQUIRED:{NC}{YELLOW} Add this callback URL to your identity provider:{NC}"
        )
        warn(f"  {BOLD}{callback_url}{NC}")
        warn("  NOTE: HTTP callback URLs may need to be explicitly allowed in your IdP settings.")
        print()

    # Summary
    print("=" * 76)
    print(f"  {GREEN}VM deployment complete — {_auth_labels[auth_mode]}{NC}")
    print("=" * 76)
    print()
    print(f"  MCP URL:         {mcp_url}")
    print(f"  Package:         {PYPI_PACKAGE}")
    print(f"  Resource Group:  {resource_group}")
    print(f"  VM Name:         {vm_name}")
    print(f"  Public IP:       {public_ip}")
    print(f"  Key Vault:       {keyvault_name}")
    print(f"  Auth mode:       {_auth_labels[auth_mode]}")

    if auth_mode == "api-key":
        print(f"  API Key:         {creds['api_key']}")
    elif auth_mode == "oidcproxy":
        print(f"  OIDC Domain:     {creds['oidc_domain']}")
    elif auth_mode == "jwt":
        print(f"  JWKS URI:        {creds['jwks_uri']}")

    print()
    print(f"  {BOLD}SSH Access:{NC}")
    print(f"    ssh {VM_ADMIN_USER}@{public_ip}")
    print()
    print(f"  {BOLD}Service Management (on VM):{NC}")
    print("    sudo systemctl status zscaler-mcp   # check status")
    print("    sudo journalctl -u zscaler-mcp -f   # stream logs")
    print("    sudo systemctl restart zscaler-mcp  # restart")
    print()
    print(f"  {BOLD}Next steps:{NC}")
    if auth_mode == "oidcproxy":
        print(f"    1. {BOLD}Add the callback URL to your identity provider{NC} (see above)")
        print("    2. Restart Claude Desktop — browser login will open")
    elif auth_mode == "jwt":
        print(f"    1. {BOLD}Obtain a valid JWT{NC} from your identity provider")
        print("    2. Update Claude/Cursor config with: Authorization: Bearer <JWT>")
    elif auth_mode in ("api-key", "zscaler"):
        print("    1. Restart Claude Desktop — auth headers are pre-configured")
    else:
        print("    1. Restart Claude Desktop / Cursor")
    print()
    print("  Management:")
    print("    python azure_mcp_operations.py status     — Check deployment health")
    print("    python azure_mcp_operations.py logs       — View service logs")
    print("    python azure_mcp_operations.py ssh        — SSH into VM")
    print("    python azure_mcp_operations.py destroy    — Tear down all resources")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Deploy — Azure Kubernetes Service (AKS)  [PREVIEW]
# ════════════════════════════════════════════════════════════════════════


def _build_aks_env_vars(creds: dict, mcp_port: str) -> list[tuple[str, str]]:
    """Build the env vars to inject into the AKS pod (auth + Zscaler creds)
    for the **envvars** storage path.  Used when the user opts out of Key
    Vault integration on AKS.
    """
    auth_mode = creds["auth_mode"]
    env_vars: list[tuple[str, str]] = [
        ("ZSCALER_MCP_ALLOW_HTTP", "true"),
        ("ZSCALER_MCP_DISABLE_HOST_VALIDATION", "true"),
        ("MCP_HOST", "0.0.0.0"),
        ("MCP_PORT", mcp_port),
        ("ZSCALER_CLIENT_ID", creds["zscaler_client_id"]),
        ("ZSCALER_CLIENT_SECRET", creds["zscaler_client_secret"]),
        ("ZSCALER_VANITY_DOMAIN", creds["zscaler_vanity_domain"]),
        ("ZSCALER_CUSTOMER_ID", creds["zscaler_customer_id"]),
    ]
    if creds["zscaler_cloud"]:
        env_vars.append(("ZSCALER_CLOUD", creds["zscaler_cloud"]))
    if creds["write_enabled"]:
        env_vars.append(("ZSCALER_MCP_WRITE_ENABLED", creds["write_enabled"]))
    if creds["write_tools"]:
        env_vars.append(("ZSCALER_MCP_WRITE_TOOLS", creds["write_tools"]))
    if creds["disabled_tools"]:
        env_vars.append(("ZSCALER_MCP_DISABLED_TOOLS", creds["disabled_tools"]))
    if creds["disabled_services"]:
        env_vars.append(("ZSCALER_MCP_DISABLED_SERVICES", creds["disabled_services"]))

    if auth_mode == "jwt":
        env_vars += [
            ("ZSCALER_MCP_AUTH_ENABLED", "true"),
            ("ZSCALER_MCP_AUTH_MODE", "jwt"),
            ("ZSCALER_MCP_AUTH_JWKS_URI", creds["jwks_uri"]),
            ("ZSCALER_MCP_AUTH_ISSUER", creds["jwt_issuer"]),
            ("ZSCALER_MCP_AUTH_AUDIENCE", creds["jwt_audience"]),
        ]
    elif auth_mode == "api-key":
        env_vars += [
            ("ZSCALER_MCP_AUTH_ENABLED", "true"),
            ("ZSCALER_MCP_AUTH_MODE", "api-key"),
            ("ZSCALER_MCP_AUTH_API_KEY", creds["api_key"]),
        ]
    elif auth_mode == "zscaler":
        env_vars += [
            ("ZSCALER_MCP_AUTH_ENABLED", "true"),
            ("ZSCALER_MCP_AUTH_MODE", "zscaler"),
        ]
    else:
        env_vars.append(("ZSCALER_MCP_AUTH_ENABLED", "false"))
    return env_vars


# ────────────────────────────────────────────────────────────────────────
#  AKS — Workload Identity Federation + Key Vault CSI driver helpers
# ────────────────────────────────────────────────────────────────────────


# K8s ServiceAccount + Secret name used by the AKS deployment.  These
# stay constant per deployment because the federated credential subject
# embeds the ServiceAccount name.
AKS_SERVICE_ACCOUNT_NAME = "zscaler-mcp-sa"
AKS_K8S_SECRET_NAME = "zscaler-mcp-secrets"
AKS_SPC_NAME = "zscaler-mcp-spc"


def _build_aks_kv_env_vars(creds: dict, mcp_port: str) -> list[dict]:
    """Build the Deployment env vars for the **keyvault** storage path.

    Sensitive values reference a synced Kubernetes Secret (populated by
    the Key Vault CSI driver via the SecretProviderClass).  Non-sensitive
    values stay inline.

    Returns a list of dict env entries ready to be rendered as YAML.
    """
    auth_mode = creds["auth_mode"]
    secret_map = _build_kv_secret_map(auth_mode)
    secret_keys = {env_name: kv_name for env_name, kv_name in secret_map}

    inline: list[tuple[str, str]] = [
        ("ZSCALER_MCP_ALLOW_HTTP", "true"),
        ("ZSCALER_MCP_DISABLE_HOST_VALIDATION", "true"),
        ("MCP_HOST", "0.0.0.0"),
        ("MCP_PORT", mcp_port),
    ]
    if creds["zscaler_cloud"]:
        inline.append(("ZSCALER_CLOUD", creds["zscaler_cloud"]))
    if creds["write_enabled"]:
        inline.append(("ZSCALER_MCP_WRITE_ENABLED", creds["write_enabled"]))
    if creds["write_tools"]:
        inline.append(("ZSCALER_MCP_WRITE_TOOLS", creds["write_tools"]))
    if creds["disabled_tools"]:
        inline.append(("ZSCALER_MCP_DISABLED_TOOLS", creds["disabled_tools"]))
    if creds["disabled_services"]:
        inline.append(("ZSCALER_MCP_DISABLED_SERVICES", creds["disabled_services"]))

    if auth_mode == "jwt":
        inline += [
            ("ZSCALER_MCP_AUTH_ENABLED", "true"),
            ("ZSCALER_MCP_AUTH_MODE", "jwt"),
            ("ZSCALER_MCP_AUTH_JWKS_URI", creds["jwks_uri"]),
            ("ZSCALER_MCP_AUTH_ISSUER", creds["jwt_issuer"]),
            ("ZSCALER_MCP_AUTH_AUDIENCE", creds["jwt_audience"]),
        ]
    elif auth_mode == "api-key":
        inline += [
            ("ZSCALER_MCP_AUTH_ENABLED", "true"),
            ("ZSCALER_MCP_AUTH_MODE", "api-key"),
        ]
    elif auth_mode == "zscaler":
        inline += [
            ("ZSCALER_MCP_AUTH_ENABLED", "true"),
            ("ZSCALER_MCP_AUTH_MODE", "zscaler"),
        ]
    else:
        inline.append(("ZSCALER_MCP_AUTH_ENABLED", "false"))

    rendered: list[dict] = [{"name": k, "value": v} for k, v in inline]
    for env_name, kv_secret_name in secret_keys.items():
        rendered.append(
            {
                "name": env_name,
                "valueFrom": {
                    "secretKeyRef": {
                        "name": AKS_K8S_SECRET_NAME,
                        "key": kv_secret_name,
                    }
                },
            }
        )
    return rendered


def _enable_aks_workload_identity(cluster_name: str, resource_group: str) -> str:
    """Enable Workload Identity + OIDC issuer on the AKS cluster and return
    the cluster's OIDC issuer URL.
    """
    info("  Enabling Workload Identity + OIDC issuer on the cluster...")
    run_az(
        [
            "aks",
            "update",
            "--name",
            cluster_name,
            "--resource-group",
            resource_group,
            "--enable-workload-identity",
            "--enable-oidc-issuer",
            "--output",
            "none",
        ]
    )
    r = run_az(
        [
            "aks",
            "show",
            "--name",
            cluster_name,
            "--resource-group",
            resource_group,
            "--query",
            "oidcIssuerProfile.issuerUrl",
            "--output",
            "tsv",
        ],
        capture=True,
    )
    issuer_url = r.stdout.strip()
    if not issuer_url:
        die("Could not retrieve OIDC issuer URL from the AKS cluster.")
    ok(f"  OIDC issuer URL: {issuer_url}")
    return issuer_url


def _enable_aks_kv_csi(cluster_name: str, resource_group: str) -> None:
    """Enable the Azure Key Vault provider for Secrets Store CSI driver on
    the AKS cluster.  Idempotent — succeeds quietly if already enabled.
    """
    info("  Enabling Key Vault CSI driver addon...")
    r = run_az(
        [
            "aks",
            "enable-addons",
            "--name",
            cluster_name,
            "--resource-group",
            resource_group,
            "--addons",
            "azure-keyvault-secrets-provider",
            "--enable-secret-rotation",
            "--rotation-poll-interval",
            "2m",
            "--output",
            "none",
        ],
        check=False,
        capture=True,
    )
    if r.returncode != 0 and "already enabled" not in (r.stderr or "").lower():
        # Some Azure CLI versions return a non-zero exit if already enabled
        # but emit a clear message — surface anything unexpected.
        warn(f"  enable-addons returned non-zero ({r.returncode}); continuing.")
        if r.stderr:
            warn(f"  stderr: {r.stderr.strip()[:200]}")
    ok("  Key Vault CSI driver addon ready")


def _create_uami(uami_name: str, resource_group: str, location: str) -> dict:
    """Create (idempotent) a User-Assigned Managed Identity and return its
    ``{clientId, principalId, id}`` payload.
    """
    info(f"  Creating User-Assigned Managed Identity '{uami_name}'...")
    r = run_az(
        [
            "identity",
            "create",
            "--name",
            uami_name,
            "--resource-group",
            resource_group,
            "--location",
            location,
            "--output",
            "json",
        ],
        capture=True,
    )
    payload = json.loads(r.stdout) if r.stdout.strip() else {}
    client_id = payload.get("clientId", "")
    principal_id = payload.get("principalId", "")
    resource_id = payload.get("id", "")
    if not (client_id and principal_id and resource_id):
        die("Failed to create / retrieve the User-Assigned Managed Identity.")
    ok(f"  UAMI clientId: {client_id}")
    return {"client_id": client_id, "principal_id": principal_id, "id": resource_id}


def _grant_uami_kv_role(
    *, account: dict, uami_principal_id: str, resource_group: str, keyvault_name: str
) -> None:
    """Grant the UAMI 'Key Vault Secrets User' on the Key Vault scope."""
    info("  Granting 'Key Vault Secrets User' role to the UAMI...")
    kv_scope = (
        f"/subscriptions/{account['id']}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.KeyVault/vaults/{keyvault_name}"
    )
    run_az(
        [
            "role",
            "assignment",
            "create",
            "--role",
            "Key Vault Secrets User",
            "--assignee-object-id",
            uami_principal_id,
            "--assignee-principal-type",
            "ServicePrincipal",
            "--scope",
            kv_scope,
            "--output",
            "none",
        ],
        check=False,
        capture=True,
    )
    ok("  RBAC role assigned")


def _create_federated_credential(
    *,
    uami_name: str,
    resource_group: str,
    issuer_url: str,
    namespace: str,
    service_account: str,
) -> None:
    """Create (idempotent) a federated credential linking the K8s
    ServiceAccount to the UAMI.
    """
    fc_name = f"{uami_name}-fed-{namespace}-{service_account}"
    subject = f"system:serviceaccount:{namespace}:{service_account}"
    info(f"  Creating federated credential for {subject} ...")
    # Check whether a credential with this name already exists
    r = run_az(
        [
            "identity",
            "federated-credential",
            "show",
            "--identity-name",
            uami_name,
            "--resource-group",
            resource_group,
            "--name",
            fc_name,
            "--output",
            "none",
        ],
        check=False,
        capture=True,
    )
    if r.returncode == 0:
        ok(f"  Federated credential '{fc_name}' already exists")
        return

    run_az(
        [
            "identity",
            "federated-credential",
            "create",
            "--identity-name",
            uami_name,
            "--resource-group",
            resource_group,
            "--name",
            fc_name,
            "--issuer",
            issuer_url,
            "--subject",
            subject,
            "--audiences",
            "api://AzureADTokenExchange",
            "--output",
            "none",
        ]
    )
    ok(f"  Federated credential '{fc_name}' created")


def _build_aks_kv_manifest(
    *,
    image: str,
    namespace: str,
    mcp_port: str,
    creds: dict,
    keyvault_name: str,
    tenant_id: str,
    uami_client_id: str,
) -> str:
    """Generate the full K8s manifest for the **keyvault** storage path:
    ServiceAccount + SecretProviderClass + Deployment + Service.

    The Deployment uses a federated workload identity to mount the
    SecretProviderClass volume, which causes the CSI driver to pull every
    Zscaler secret from Key Vault and sync them into a Kubernetes Secret
    that the Pod's env vars read via ``valueFrom.secretKeyRef``.
    """
    auth_mode = creds["auth_mode"]
    secret_map = _build_kv_secret_map(auth_mode)

    spc_objects_yaml = "\n".join(
        f"          - |\n"
        f"            objectName: {kv_name}\n"
        f"            objectType: secret"
        for _, kv_name in secret_map
    )
    secret_data_yaml = "\n".join(
        f"      - objectName: {kv_name}\n        key: {kv_name}" for _, kv_name in secret_map
    )

    env_entries_yaml = ""
    for entry in _build_aks_kv_env_vars(creds, mcp_port):
        if "value" in entry:
            env_entries_yaml += (
                f"        - name: {entry['name']}\n"
                f"          value: {json.dumps(str(entry['value']))}\n"
            )
        else:
            ref = entry["valueFrom"]["secretKeyRef"]
            env_entries_yaml += (
                f"        - name: {entry['name']}\n"
                f"          valueFrom:\n"
                f"            secretKeyRef:\n"
                f"              name: {ref['name']}\n"
                f"              key: {ref['key']}\n"
            )

    manifest = f"""apiVersion: v1
kind: ServiceAccount
metadata:
  name: {AKS_SERVICE_ACCOUNT_NAME}
  namespace: {namespace}
  annotations:
    azure.workload.identity/client-id: {uami_client_id}
  labels:
    azure.workload.identity/use: "true"
---
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: {AKS_SPC_NAME}
  namespace: {namespace}
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: {uami_client_id}
    keyvaultName: {keyvault_name}
    tenantId: {tenant_id}
    objects: |
      array:
{spc_objects_yaml}
  secretObjects:
  - secretName: {AKS_K8S_SECRET_NAME}
    type: Opaque
    data:
{secret_data_yaml}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {SERVER_NAME}
  namespace: {namespace}
  labels:
    app: {SERVER_NAME}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {SERVER_NAME}
  template:
    metadata:
      labels:
        app: {SERVER_NAME}
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: {AKS_SERVICE_ACCOUNT_NAME}
      containers:
      - name: zscaler-mcp
        image: {image}
        command: ["/app/.venv/bin/zscaler-mcp"]
        args: ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "{mcp_port}"]
        ports:
        - containerPort: {mcp_port}
        env:
{env_entries_yaml}        volumeMounts:
        - name: zscaler-secrets-store
          mountPath: /mnt/secrets-store
          readOnly: true
        resources:
          requests:
            cpu: "200m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
      volumes:
      - name: zscaler-secrets-store
        csi:
          driver: secrets-store.csi.k8s.io
          readOnly: true
          volumeAttributes:
            secretProviderClass: {AKS_SPC_NAME}
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
    targetPort: {mcp_port}
    protocol: TCP
  selector:
    app: {SERVER_NAME}
"""
    return manifest


def _deploy_aks(account: dict, creds: dict) -> None:
    """Deploy to Azure Kubernetes Service (AKS) — PREVIEW."""
    env = creds["env"]
    suffix = _secrets.token_hex(3)

    # Auth-mode guard for Preview
    if creds["auth_mode"] == "oidcproxy":
        die(
            "OIDCProxy auth mode is not yet supported on AKS (Preview).\n"
            "  Use 'jwt', 'api-key', 'zscaler', or 'none' for AKS deployments."
        )

    print()
    warn(
        f"{BOLD}AKS deployment is in PREVIEW.{NC}{YELLOW} "
        "Cluster + LoadBalancer + K8s manifests are validated;"
    )
    warn("  TLS Ingress, OIDCProxy auth, and HPA are planned for a future release.")
    print()

    if not shutil.which("kubectl"):
        die(
            "kubectl not found. Install: https://kubernetes.io/docs/tasks/tools/\n"
            "  On macOS: brew install kubernetes-cli"
        )

    info("AKS configuration")
    location = _prompt("Azure region", default=resolve(env, "AZURE_LOCATION") or "eastus")
    resource_group = _prompt(
        "Resource group name",
        default=resolve(env, "AZURE_RESOURCE_GROUP") or f"zscaler-mcp-rg-{suffix}",
    )

    cluster_mode = _prompt_choice(
        "AKS cluster:",
        [
            ("new", "Create a new AKS cluster (PoC / testing)"),
            ("existing", "Use an existing AKS cluster (production)"),
        ],
    )

    if cluster_mode == "new":
        cluster_name = _prompt(
            "New cluster name",
            default=resolve(env, "AZURE_AKS_CLUSTER") or f"zscaler-mcp-aks-{suffix}",
        )
        node_count = _prompt("Node count", default="1")
        node_size = _prompt("Node VM size", default="Standard_B2s")
    else:
        cluster_name = _prompt(
            "Existing cluster name",
            default=resolve(env, "AZURE_AKS_CLUSTER") or "",
        )
        node_count = ""
        node_size = ""

    namespace = _prompt("Kubernetes namespace", default="default")
    image = _prompt("Container image", default=DOCKER_HUB_IMAGE)
    mcp_port = _prompt("MCP server port", default=resolve(env, "MCP_PORT") or "8000")
    print()

    # Credential storage strategy
    info("Credential storage")
    storage_choice = _prompt_choice(
        "How should credentials be stored and injected into the pods?",
        [
            (
                "keyvault",
                "Azure Key Vault (recommended)  — Workload Identity Federation + Key Vault"
                " CSI driver, secrets mounted at runtime",
            ),
            (
                "envvars",
                "Direct environment variables   — credentials baked into the Deployment manifest"
                " at deploy time, no Key Vault provisioned",
            ),
        ],
    )

    keyvault_name = ""
    kv_choice = ""
    uami_name = ""
    if storage_choice == "keyvault":
        info("Azure Key Vault")
        kv_choice = _prompt_choice(
            "Key Vault for storing secrets:",
            [
                ("new", "Create a new Key Vault"),
                ("existing", "Use an existing Key Vault"),
            ],
        )
        if kv_choice == "existing":
            keyvault_name = _prompt("Existing Key Vault name")
        else:
            keyvault_name = _prompt(
                "New Key Vault name",
                default=resolve(env, "AZURE_KEYVAULT_NAME") or f"zscalermcpkv{suffix}",
            )
        uami_name = _prompt(
            "User-Assigned Managed Identity name",
            default=f"zscaler-mcp-uami-{suffix}",
        )
    else:
        warn("Credentials will be passed as plain environment variables on the Deployment.")
        warn("  They are visible to anyone with read access via 'kubectl describe deployment'.")
        warn("  For production, re-run and choose the Key Vault option.")
    print()

    auth_mode = creds["auth_mode"]
    _auth_labels = {
        "jwt": f"JWT (JWKS: {creds['jwks_uri']})",
        "api-key": "API Key (shared secret)",
        "zscaler": "Zscaler (OneAPI credentials)",
        "none": "None (no auth)",
    }

    if storage_choice == "keyvault":
        storage_label = (
            f"Azure Key Vault — {keyvault_name} "
            f"({'new' if kv_choice == 'new' else 'existing'}); KV CSI + Workload Identity"
        )
    else:
        storage_label = "Plain env vars (no Key Vault)"

    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          Azure Kubernetes Service (AKS) [PREVIEW]")
    print(f"    Image:           {image}")
    print(f"    Resource Group:  {resource_group}")
    print(f"    Location:        {location}")
    print(f"    Cluster:         {cluster_name} ({'new' if cluster_mode == 'new' else 'existing'})")
    if cluster_mode == "new":
        print(f"    Node count:      {node_count}")
        print(f"    Node size:       {node_size}")
    print(f"    Namespace:       {namespace}")
    print(f"    Credentials:     {storage_label}")
    if storage_choice == "keyvault":
        print(f"    UAMI:            {uami_name}")
    print(f"    Auth mode:       {_auth_labels.get(auth_mode, auth_mode)}")
    print(f"    Zscaler Cloud:   {creds['zscaler_cloud']}")
    print(f"    Port:            {mcp_port}")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    # Resource group
    info("Ensuring resource group")
    run_az(
        ["group", "create", "--name", resource_group, "--location", location, "--output", "none"]
    )
    ok(f"Resource group '{resource_group}' ready")
    print()

    # AKS cluster
    if cluster_mode == "new":
        info(f"Creating AKS cluster '{cluster_name}' (this may take 5-10 minutes)...")
        new_cluster_args = [
            "aks",
            "create",
            "--name",
            cluster_name,
            "--resource-group",
            resource_group,
            "--location",
            location,
            "--node-count",
            node_count,
            "--node-vm-size",
            node_size,
            "--enable-managed-identity",
            "--generate-ssh-keys",
            "--load-balancer-sku",
            "standard",
        ]
        # Enable Workload Identity + OIDC issuer + KV CSI driver up front
        # when the user picked the Key Vault path so the cluster comes up
        # ready for federated identity.  For envvars path we skip these
        # extras.
        if storage_choice == "keyvault":
            new_cluster_args += [
                "--enable-workload-identity",
                "--enable-oidc-issuer",
                "--enable-addons",
                "azure-keyvault-secrets-provider",
            ]
        new_cluster_args += ["--output", "none"]
        run_az(new_cluster_args)
        ok(f"AKS cluster '{cluster_name}' created")
        print()
    else:
        info(f"Verifying existing cluster '{cluster_name}'...")
        r = run_az(
            [
                "aks",
                "show",
                "--name",
                cluster_name,
                "--resource-group",
                resource_group,
                "--output",
                "none",
            ],
            check=False,
            capture=True,
        )
        if r.returncode != 0:
            die(
                f"AKS cluster '{cluster_name}' not found in resource group '{resource_group}'.\n"
                "  Verify the cluster name and resource group, or create a new cluster."
            )
        ok(f"Cluster '{cluster_name}' found")
        print()

    # kubectl credentials
    info("Fetching kubectl credentials...")
    run_az(
        [
            "aks",
            "get-credentials",
            "--name",
            cluster_name,
            "--resource-group",
            resource_group,
            "--overwrite-existing",
            "--output",
            "none",
        ]
    )
    ok("kubectl context set to cluster")
    print()

    # Namespace
    info(f"Ensuring namespace '{namespace}'...")
    r = run_kubectl(["get", "namespace", namespace], check=False, capture=True)
    if r.returncode != 0:
        run_kubectl(["create", "namespace", namespace])
        ok(f"Namespace '{namespace}' created")
    else:
        ok(f"Namespace '{namespace}' already exists")
    print()

    # Key Vault + Workload Identity Federation (only for the keyvault path)
    uami_payload: dict = {}
    issuer_url = ""
    tenant_id = ""
    if storage_choice == "keyvault":
        info("Setting up Key Vault + Workload Identity Federation for AKS")
        # 1. Provision / verify the vault and store every Zscaler secret in
        #    it (reuses the helper used by Container Apps).
        _setup_keyvault(account, resource_group, location, keyvault_name, kv_choice, creds)

        # 2. For existing clusters we may need to enable Workload Identity
        #    + OIDC issuer + the KV CSI addon retroactively.  For new
        #    clusters this was already done at create time.
        if cluster_mode == "existing":
            issuer_url = _enable_aks_workload_identity(cluster_name, resource_group)
            _enable_aks_kv_csi(cluster_name, resource_group)
        else:
            r = run_az(
                [
                    "aks",
                    "show",
                    "--name",
                    cluster_name,
                    "--resource-group",
                    resource_group,
                    "--query",
                    "oidcIssuerProfile.issuerUrl",
                    "--output",
                    "tsv",
                ],
                capture=True,
            )
            issuer_url = r.stdout.strip()
            if not issuer_url:
                die("Could not retrieve OIDC issuer URL from the new AKS cluster.")
            ok(f"  OIDC issuer URL: {issuer_url}")

        # 3. Capture the tenant ID — needed by the SecretProviderClass.
        tenant_id = account.get("tenantId", "")
        if not tenant_id:
            r = run_az(
                ["account", "show", "--query", "tenantId", "--output", "tsv"], capture=True
            )
            tenant_id = r.stdout.strip()
        if not tenant_id:
            die("Could not determine Azure tenant ID for the SecretProviderClass.")
        ok(f"  Azure tenant ID: {tenant_id}")

        # 4. Create the User-Assigned Managed Identity, grant it
        #    'Key Vault Secrets User' on the vault, and create the
        #    federated credential bridging the K8s ServiceAccount.
        uami_payload = _create_uami(uami_name, resource_group, location)
        _grant_uami_kv_role(
            account=account,
            uami_principal_id=uami_payload["principal_id"],
            resource_group=resource_group,
            keyvault_name=keyvault_name,
        )
        _create_federated_credential(
            uami_name=uami_name,
            resource_group=resource_group,
            issuer_url=issuer_url,
            namespace=namespace,
            service_account=AKS_SERVICE_ACCOUNT_NAME,
        )

        info("  Waiting for federated identity propagation (45s)...")
        time.sleep(45)
        print()

    # Build manifest
    if storage_choice == "keyvault":
        manifest = _build_aks_kv_manifest(
            image=image,
            namespace=namespace,
            mcp_port=mcp_port,
            creds=creds,
            keyvault_name=keyvault_name,
            tenant_id=tenant_id,
            uami_client_id=uami_payload["client_id"],
        )
    else:
        env_vars = _build_aks_env_vars(creds, mcp_port)
        env_entries = "\n".join(
            f"        - name: {k}\n          value: {json.dumps(v)}" for k, v in env_vars
        )
        manifest = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {SERVER_NAME}
  namespace: {namespace}
  labels:
    app: {SERVER_NAME}
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
      containers:
      - name: zscaler-mcp
        image: {image}
        command: ["/app/.venv/bin/zscaler-mcp"]
        args: ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "{mcp_port}"]
        ports:
        - containerPort: {mcp_port}
        env:
{env_entries}
        resources:
          requests:
            cpu: "200m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
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
    targetPort: {mcp_port}
    protocol: TCP
  selector:
    app: {SERVER_NAME}
"""

    manifest_path = SCRIPT_DIR / ".aks-manifest.yaml"
    manifest_path.write_text(manifest, encoding="utf-8")
    ok(f"K8s manifest written to {manifest_path}")
    print()

    info("Applying K8s manifest...")
    run_kubectl(["apply", "-f", str(manifest_path)])
    ok("Deployment + Service applied")
    print()

    # Wait for LoadBalancer external IP
    info("Waiting for LoadBalancer external IP (this may take 1-3 minutes)...")
    external_ip = ""
    for attempt in range(30):
        time.sleep(10)
        r = run_kubectl(
            [
                "get",
                "svc",
                SERVER_NAME,
                "-n",
                namespace,
                "-o",
                "jsonpath={.status.loadBalancer.ingress[0].ip}",
            ],
            check=False,
            capture=True,
        )
        if r.stdout.strip():
            external_ip = r.stdout.strip()
            break
        info(f"  Waiting for external IP... (attempt {attempt + 1}/30)")

    if external_ip:
        mcp_url = f"http://{external_ip}/mcp"
        ok(f"External IP: {external_ip}")
    else:
        warn(
            "External IP not yet assigned. Check later with: "
            f"kubectl get svc {SERVER_NAME} -n {namespace}"
        )
        mcp_url = "http://<PENDING>/mcp"
    print()

    # Save state
    _save_state(
        {
            "deployment_type": "aks",
            "resource_group": resource_group,
            "location": location,
            "cluster_name": cluster_name,
            "cluster_created": cluster_mode == "new",
            "namespace": namespace,
            "service_name": SERVER_NAME,
            "external_ip": external_ip,
            "mcp_url": mcp_url,
            "auth_mode": auth_mode,
            "suffix": suffix,
            "credential_storage": storage_choice,
            "keyvault_name": keyvault_name,
            "uami_name": uami_name,
            "service_account_name": (
                AKS_SERVICE_ACCOUNT_NAME if storage_choice == "keyvault" else ""
            ),
        }
    )

    if external_ip:
        _update_client_configs(mcp_url, auth_mode, creds)

    # Summary
    print("=" * 76)
    print(f"  {GREEN}AKS deployment complete (PREVIEW){NC}")
    print("=" * 76)
    print()
    print(f"  MCP URL:         {mcp_url}")
    print(f"  Image:           {image}")
    print(f"  Resource Group:  {resource_group}")
    print(f"  Cluster:         {cluster_name}")
    print(f"  Namespace:       {namespace}")
    print(f"  External IP:     {external_ip or '<PENDING>'}")
    if storage_choice == "keyvault":
        print(f"  Key Vault:       {keyvault_name} (CSI + Workload Identity)")
        print(f"  UAMI:            {uami_name}")
    else:
        print("  Credentials:     Plain env vars (no Key Vault)")
    print(f"  Auth mode:       {_auth_labels.get(auth_mode, auth_mode)}")

    if auth_mode == "api-key":
        print(f"  API Key:         {creds['api_key']}")
    elif auth_mode == "jwt":
        print(f"  JWKS URI:        {creds['jwks_uri']}")
    print()
    print(f"  {BOLD}Next steps:{NC}")
    if auth_mode == "jwt":
        print(f"    1. {BOLD}Obtain a valid JWT{NC} from your identity provider")
        print("    2. Update Claude/Cursor config with: Authorization: Bearer <JWT>")
    elif auth_mode in ("api-key", "zscaler"):
        print("    1. Restart Claude Desktop — auth headers are pre-configured")
    else:
        print("    1. Restart Claude Desktop / Cursor")
    print()
    print(f"  {BOLD}Kubernetes commands:{NC}")
    print(f"    kubectl get pods -n {namespace}")
    print(f"    kubectl logs deployment/{SERVER_NAME} -n {namespace} -f")
    print(f"    kubectl get svc {SERVER_NAME} -n {namespace}")
    print()
    print("  Management:")
    print("    python azure_mcp_operations.py status     — Check deployment health")
    print("    python azure_mcp_operations.py logs       — Stream pod logs")
    print("    python azure_mcp_operations.py destroy    — Tear down all resources")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Deploy (main entry point)
# ════════════════════════════════════════════════════════════════════════


def op_deploy(args: argparse.Namespace) -> None:
    """Fully interactive deployment to Azure."""

    print(ZSCALER_LOGO)
    print("=" * 76)
    print(f"  {BOLD}Zscaler MCP Server — Azure Deployment{NC}")
    print("=" * 76)
    print()

    # Prerequisites
    info("Step 1: Checking prerequisites")
    if not shutil.which("az"):
        die("Azure CLI (az) not found. Install: https://aka.ms/installazurecli")

    r = run_az(["account", "show", "--output", "json"], capture=True, check=False)
    if r.returncode != 0:
        die("Not logged in to Azure. Run: az login")
    account = json.loads(r.stdout)
    ok(f"Azure CLI: subscription '{account.get('name', 'unknown')}'")
    print()

    # Deployment target
    deploy_target = _prompt_choice(
        "Select deployment target:",
        [
            ("container_app", "Azure Container Apps  — managed, serverless (Docker Hub image)"),
            ("vm", "Azure Virtual Machine — Ubuntu 22.04, self-managed (Python library)"),
            ("aks", "Azure Kubernetes Service (AKS) — Kubernetes deployment [PREVIEW]"),
        ],
    )
    ok(f"Deployment target: {deploy_target}")
    print()

    # Collect credentials (shared)
    info("Step 2: Collecting credentials and configuration")
    creds = _collect_credentials(account)

    # Branch to target-specific deployment
    if deploy_target == "container_app":
        _deploy_container_app(account, creds)
    elif deploy_target == "vm":
        _deploy_vm(account, creds)
    else:
        _deploy_aks(account, creds)


# ════════════════════════════════════════════════════════════════════════
#  Destroy
# ════════════════════════════════════════════════════════════════════════


def op_destroy(args: argparse.Namespace) -> None:
    """Tear down all Azure resources."""
    state = _load_state()
    resource_group = args.resource_group or state.get("resource_group", "")
    keyvault_name = state.get("keyvault_name", "")
    location = state.get("location", "eastus")
    deployment_type = state.get("deployment_type", "container_app")

    if not resource_group:
        die("No resource group found. Pass --resource-group or deploy first.")

    print()
    print("=" * 76)
    print(f"  {RED}DESTROY — Tearing down all Azure resources{NC}")
    print("=" * 76)
    print()
    cluster_created = state.get("cluster_created", False)
    cluster_name = state.get("cluster_name", "")
    namespace = state.get("namespace", "default")

    aks_keep_cluster = deployment_type == "aks" and not cluster_created

    if aks_keep_cluster:
        warn(
            f"AKS cluster '{cluster_name}' was pre-existing — only the K8s "
            "Deployment + Service will be removed."
        )
        warn("The AKS cluster and resource group will NOT be deleted.")
        if state.get("credential_storage") == "keyvault":
            warn("Also removing: ServiceAccount, SecretProviderClass, synced Secret,")
            warn("  the per-deployment UAMI, and its federated credential.")
            warn("  Key Vault itself is NOT deleted (it may be shared).")
    else:
        warn(f"This will delete the ENTIRE resource group: {resource_group}")
        if deployment_type == "vm":
            warn("Includes: Virtual Machine, NSG, Public IP, Key Vault, and all data.")
        elif deployment_type == "aks":
            warn(
                f"Includes: AKS cluster '{cluster_name}', LoadBalancer, all K8s resources, "
                "and any other resources in the group."
            )
        else:
            if keyvault_name:
                warn("Includes: Container App, Key Vault, and all data.")
            else:
                warn("Includes: Container App and all data (no Key Vault was provisioned).")
    print()

    if not args.yes:
        prompt_target = (
            cluster_name if aks_keep_cluster and cluster_name else resource_group
        )
        try:
            confirm = input(f"  Type '{prompt_target}' to confirm (or 'exit' to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            _cancel("Destruction cancelled.")
        if confirm.lower() in _EXIT_WORDS:
            _cancel("Destruction cancelled.")
        if confirm != prompt_target:
            _cancel("Destruction cancelled — confirmation text did not match.")

    print()

    if aks_keep_cluster:
        info(f"Removing K8s resources from cluster '{cluster_name}'...")
        r = run_az(
            [
                "aks",
                "get-credentials",
                "--name",
                cluster_name,
                "--resource-group",
                resource_group,
                "--overwrite-existing",
                "--output",
                "none",
            ],
            check=False,
            capture=True,
        )
        if r.returncode == 0:
            # Clean up the K8s objects we created.  When the keyvault path
            # is in use, we also delete the ServiceAccount and the
            # SecretProviderClass so re-deploying into the same cluster
            # works cleanly.
            extra_kinds = ""
            if state.get("credential_storage") == "keyvault":
                extra_kinds = ",serviceaccount,secretproviderclass,secret"
            run_kubectl(
                [
                    "delete",
                    f"deployment,service{extra_kinds}",
                    "-l",
                    f"app={SERVER_NAME}",
                    "-n",
                    namespace,
                    "--ignore-not-found",
                ],
                check=False,
            )
            # Selector won't catch the SA / SPC / synced Secret (we don't
            # apply a label to them), so delete by name as well.
            if state.get("credential_storage") == "keyvault":
                run_kubectl(
                    [
                        "delete",
                        "serviceaccount",
                        AKS_SERVICE_ACCOUNT_NAME,
                        "-n",
                        namespace,
                        "--ignore-not-found",
                    ],
                    check=False,
                )
                run_kubectl(
                    [
                        "delete",
                        "secretproviderclass",
                        AKS_SPC_NAME,
                        "-n",
                        namespace,
                        "--ignore-not-found",
                    ],
                    check=False,
                )
                run_kubectl(
                    [
                        "delete",
                        "secret",
                        AKS_K8S_SECRET_NAME,
                        "-n",
                        namespace,
                        "--ignore-not-found",
                    ],
                    check=False,
                )
            # Also remove the Deployment + Service explicitly in case the
            # selector-based delete missed them.
            run_kubectl(
                [
                    "delete",
                    "deployment,service",
                    SERVER_NAME,
                    "-n",
                    namespace,
                    "--ignore-not-found",
                ],
                check=False,
            )
            ok("K8s resources removed (Deployment + Service" + (
                " + SA + SPC + Secret)" if state.get("credential_storage") == "keyvault" else ")"
            ))
        else:
            warn("Could not connect to AKS cluster to clean up K8s resources.")

        # When the keyvault path is in use, also remove the per-deployment
        # UAMI + federated credential.  The Vault itself may be shared and
        # is left intact.
        uami_name = state.get("uami_name", "")
        sa_name = state.get("service_account_name", "") or AKS_SERVICE_ACCOUNT_NAME
        if uami_name:
            info(f"Removing federated credential + UAMI '{uami_name}'...")
            fc_name = f"{uami_name}-fed-{namespace}-{sa_name}"
            run_az(
                [
                    "identity",
                    "federated-credential",
                    "delete",
                    "--identity-name",
                    uami_name,
                    "--resource-group",
                    resource_group,
                    "--name",
                    fc_name,
                    "--yes",
                    "--output",
                    "none",
                ],
                check=False,
                capture=True,
            )
            run_az(
                [
                    "identity",
                    "delete",
                    "--name",
                    uami_name,
                    "--resource-group",
                    resource_group,
                    "--output",
                    "none",
                ],
                check=False,
                capture=True,
            )
            ok(f"UAMI '{uami_name}' deleted")

        # Skip resource group + Key Vault cleanup paths
        for path_label, path in [("Claude Desktop", CLAUDE_CONFIG), ("Cursor", CURSOR_CONFIG)]:
            if path.is_file():
                try:
                    config = json.loads(path.read_text(encoding="utf-8"))
                    servers = config.get("mcpServers", {})
                    if SERVER_NAME in servers:
                        del servers[SERVER_NAME]
                        path.write_text(
                            json.dumps(config, indent=2) + "\n", encoding="utf-8"
                        )
                        ok(f"Removed '{SERVER_NAME}' from {path_label} config")
                except (json.JSONDecodeError, OSError):
                    warn(f"Could not update {path_label} config")
        _clear_state()
        print()
        ok("Destroy complete (cluster preserved). Restart Claude Desktop / Cursor.")
        print()
        return

    info(f"Deleting resource group '{resource_group}'...")
    run_az(["group", "delete", "--name", resource_group, "--yes", "--no-wait"], check=False)
    ok(f"Resource group '{resource_group}' deletion initiated")
    print()

    if keyvault_name:
        info(f"Purging Key Vault '{keyvault_name}' (background)...")
        run_az(
            ["keyvault", "purge", "--name", keyvault_name, "--location", location, "--no-wait"],
            check=False,
            capture=True,
        )
        ok("Key Vault purge initiated (runs in background)")
        print()

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
    resource_group = args.resource_group or state.get("resource_group", "")
    deployment_type = state.get("deployment_type", "container_app")

    if not resource_group:
        die("No deployment found. Deploy first or pass --resource-group.")

    print()

    if deployment_type == "aks":
        cluster_name = state.get("cluster_name", "")
        namespace = state.get("namespace", "default")
        if not cluster_name:
            die("No AKS cluster name in state. Redeploy or check manually.")

        info(f"Status of AKS cluster '{cluster_name}' in '{resource_group}'")
        print()

        r = run_az(
            [
                "aks",
                "show",
                "--name",
                cluster_name,
                "--resource-group",
                resource_group,
                "--output",
                "json",
            ],
            capture=True,
            check=False,
        )
        if r.returncode != 0:
            error("AKS cluster not found.")
            return

        cluster = json.loads(r.stdout)
        print(f"  Cluster:         {cluster_name}")
        print(f"  Provisioning:    {cluster.get('provisioningState', '?')}")
        print(f"  Power State:     {cluster.get('powerState', {}).get('code', '?')}")
        print(f"  K8s version:     {cluster.get('kubernetesVersion', '?')}")
        print(f"  Namespace:       {namespace}")
        print(f"  External IP:     {state.get('external_ip', '?')}")
        print(f"  MCP URL:         {state.get('mcp_url', '?')}")
        print(f"  Auth mode:       {state.get('auth_mode', '?')}")
        print()

        info("Refreshing kubectl credentials...")
        run_az(
            [
                "aks",
                "get-credentials",
                "--name",
                cluster_name,
                "--resource-group",
                resource_group,
                "--overwrite-existing",
                "--output",
                "none",
            ],
            check=False,
            capture=True,
        )

        info("Pods:")
        run_kubectl(
            [
                "get",
                "pods",
                "-n",
                namespace,
                "-l",
                f"app={SERVER_NAME}",
                "-o",
                "wide",
            ],
            check=False,
        )
        print()
        info("Service:")
        run_kubectl(
            ["get", "svc", SERVER_NAME, "-n", namespace, "-o", "wide"],
            check=False,
        )

    elif deployment_type == "vm":
        vm_name = state.get("vm_name", "")
        if not vm_name:
            die("No VM name in state. Redeploy or check manually.")

        info(f"Status of VM '{vm_name}' in '{resource_group}'")
        print()

        r = run_az(
            [
                "vm",
                "show",
                "--name",
                vm_name,
                "--resource-group",
                resource_group,
                "--show-details",
                "--output",
                "json",
            ],
            capture=True,
            check=False,
        )
        if r.returncode != 0:
            error("VM not found.")
            return

        vm = json.loads(r.stdout)
        print(f"  VM Name:         {vm_name}")
        print(f"  Public IP:       {state.get('public_ip', '?')}")
        print(f"  Power State:     {vm.get('powerState', '?')}")
        print(f"  MCP URL:         {state.get('mcp_url', '?')}")
        print(f"  Auth mode:       {state.get('auth_mode', '?')}")
        print()

        info("Checking MCP service status...")
        r = run_az(
            [
                "vm",
                "run-command",
                "invoke",
                "--name",
                vm_name,
                "--resource-group",
                resource_group,
                "--command-id",
                "RunShellScript",
                "--scripts",
                "systemctl status zscaler-mcp --no-pager",
            ],
            capture=True,
            check=False,
        )
        if r.returncode == 0:
            output = json.loads(r.stdout)
            message = output.get("value", [{}])[0].get("message", "")
            print(message)

    else:
        container_app_name = state.get("container_app", "")
        if not container_app_name:
            die("No container app in state. Redeploy or check manually.")

        info(f"Status of '{container_app_name}' in '{resource_group}'")
        print()

        r = run_az(
            [
                "containerapp",
                "show",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--output",
                "json",
            ],
            capture=True,
            check=False,
        )
        if r.returncode != 0:
            error("Container App not found.")
            return

        app = json.loads(r.stdout)
        fqdn = (
            app.get("properties", {}).get("configuration", {}).get("ingress", {}).get("fqdn", "?")
        )
        running = app.get("properties", {}).get("runningStatus", "?")
        replicas = app.get("properties", {}).get("template", {}).get("scale", {})

        print(f"  Container App:   {container_app_name}")
        print(f"  FQDN:            {fqdn}")
        print(f"  Running Status:  {running}")
        print(f"  Min Replicas:    {replicas.get('minReplicas', '?')}")
        print(f"  Max Replicas:    {replicas.get('maxReplicas', '?')}")
        print(f"  MCP URL:         https://{fqdn}/mcp")
        print(f"  Auth mode:       {state.get('auth_mode', '?')}")
        print()

        info("Active revisions:")
        run_az(
            [
                "containerapp",
                "revision",
                "list",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--output",
                "table",
            ]
        )
    print()


# ════════════════════════════════════════════════════════════════════════
#  Logs
# ════════════════════════════════════════════════════════════════════════


def op_logs(args: argparse.Namespace) -> None:
    """Stream logs."""
    state = _load_state()
    resource_group = args.resource_group or state.get("resource_group", "")
    deployment_type = state.get("deployment_type", "container_app")

    if not resource_group:
        die("No deployment found. Deploy first or pass --resource-group.")

    if deployment_type == "aks":
        cluster_name = state.get("cluster_name", "")
        namespace = state.get("namespace", "default")
        if not cluster_name:
            die("No AKS cluster in state.")

        info(f"Refreshing kubectl credentials for cluster '{cluster_name}'...")
        run_az(
            [
                "aks",
                "get-credentials",
                "--name",
                cluster_name,
                "--resource-group",
                resource_group,
                "--overwrite-existing",
                "--output",
                "none",
            ],
            check=False,
            capture=True,
        )
        info(f"Streaming logs for deployment/{SERVER_NAME} in namespace '{namespace}'...")
        info("Press Ctrl+C to stop")
        print()
        try:
            run_kubectl(
                [
                    "logs",
                    f"deployment/{SERVER_NAME}",
                    "-n",
                    namespace,
                    "--tail",
                    "100",
                    "-f",
                ],
                check=False,
            )
        except KeyboardInterrupt:
            print()
            info("Log streaming stopped.")
        return

    if deployment_type == "vm":
        vm_name = state.get("vm_name", "")
        if not vm_name:
            die("No VM name in state.")

        info(f"Fetching logs for VM '{vm_name}'...")
        print()

        r = run_az(
            [
                "vm",
                "run-command",
                "invoke",
                "--name",
                vm_name,
                "--resource-group",
                resource_group,
                "--command-id",
                "RunShellScript",
                "--scripts",
                "journalctl -u zscaler-mcp -n 100 --no-pager",
            ],
            capture=True,
            check=False,
        )
        if r.returncode == 0:
            output = json.loads(r.stdout)
            message = output.get("value", [{}])[0].get("message", "")
            print(message)
        else:
            error("Could not fetch logs.")
    else:
        container_app_name = state.get("container_app", "")
        if not container_app_name:
            die("No container app in state.")

        info(f"Streaming logs for '{container_app_name}'...")
        info("Press Ctrl+C to stop")
        print()

        run_az(
            [
                "containerapp",
                "logs",
                "show",
                "--name",
                container_app_name,
                "--resource-group",
                resource_group,
                "--follow",
            ],
            check=False,
        )


# ════════════════════════════════════════════════════════════════════════
#  SSH (VM only)
# ════════════════════════════════════════════════════════════════════════


def op_ssh(args: argparse.Namespace) -> None:
    """SSH into VM."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if deployment_type != "vm":
        die("SSH is only available for VM deployments.")

    public_ip = state.get("public_ip", "")
    if not public_ip:
        die("No public IP in state. Redeploy or SSH manually.")

    ssh_cmd = ["ssh", f"{VM_ADMIN_USER}@{public_ip}"]
    info(f"Connecting: {' '.join(ssh_cmd)}")
    os.execvp("ssh", ssh_cmd)


# ════════════════════════════════════════════════════════════════════════
#  Foundry Agent Operations
# ════════════════════════════════════════════════════════════════════════


def _load_foundry_module():
    """Load the foundry_agent module from the same directory."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("foundry_agent", SCRIPT_DIR / "foundry_agent.py")
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    die("Could not load foundry_agent module.")


def op_agent_create(args: argparse.Namespace) -> None:
    """Create a Foundry agent pointing to the deployed MCP server."""
    # Load deployment state to get MCP URL
    state = _load_state()
    if not state:
        die(
            "No deployment found. Deploy the MCP server first with 'deploy' command.\n"
            "The Foundry agent needs a running MCP server to connect to."
        )

    mcp_url = state.get("mcp_url", "")
    if not mcp_url:
        die("MCP URL not found in deployment state. Redeploy the MCP server.")

    auth_mode = state.get("auth_mode", "none")

    # Offer .env file or manual input for MCP auth credentials
    env: dict[str, str] = {}
    if auth_mode in ("api-key", "zscaler"):
        info(f"Deployment uses '{auth_mode}' authentication.")
        choice = _prompt_choice(
            "How would you like to provide MCP auth credentials?",
            [
                ("env", "Load from a .env file"),
                ("manual", "Enter manually"),
            ],
        )
        if choice == "env":
            env_path_str = _prompt("Path to .env file", default=str(PROJECT_ROOT / ".env"))
            env_path = Path(env_path_str).expanduser().resolve()
            if not env_path.is_file():
                die(f".env file not found: {env_path}")
            env = load_env(env_path)
            ok(f".env loaded from {env_path} ({len(env)} variables)")

            # Promote Foundry-specific values into the process env so the
            # downstream prompt_foundry_config() picks them up without
            # re-prompting the user for the same .env path.
            for k in (
                "AZURE_AI_PROJECT_ENDPOINT",
                "AZURE_OPENAI_MODEL",
                "AZURE_FOUNDRY_CONNECTION_NAME",
            ):
                if env.get(k) and not os.environ.get(k):
                    os.environ[k] = env[k]

    # Collect auth credentials based on deployment auth mode
    client_id: str | None = None
    client_secret: str | None = None
    api_key_value: str | None = None

    if auth_mode == "api-key":
        api_key_value = env.get("ZSCALER_MCP_AUTH_API_KEY", "")
        if not api_key_value:
            api_key_value = _prompt("Enter the MCP server API key", secret=True)
    elif auth_mode == "zscaler":
        client_id = env.get("ZSCALER_CLIENT_ID", env.get("ZSCALER_MCP_CLIENT_ID", ""))
        client_secret = env.get("ZSCALER_CLIENT_SECRET", env.get("ZSCALER_MCP_CLIENT_SECRET", ""))
        if not client_id:
            client_id = _prompt("Enter Zscaler client ID for MCP auth")
        if not client_secret:
            client_secret = _prompt("Enter Zscaler client secret", secret=True)
    elif auth_mode in ("jwt", "oidcproxy"):
        warn(
            f"Auth mode '{auth_mode}' requires token-based auth.\n"
            "  The Foundry agent will need a valid token at runtime.\n"
            "  Consider using 'api-key' or 'zscaler' mode for Foundry."
        )

    foundry_agent = _load_foundry_module()
    foundry_agent.op_agent_create(
        mcp_url=mcp_url,
        auth_mode=auth_mode,
        client_id=client_id,
        client_secret=client_secret,
        api_key_value=api_key_value,
    )


def op_agent_status(args: argparse.Namespace) -> None:
    """Show Foundry agent status."""
    foundry_agent = _load_foundry_module()
    foundry_agent.op_agent_status()


def op_agent_chat(args: argparse.Namespace) -> None:
    """Start interactive chat with the Foundry agent."""
    initial_message = getattr(args, "message", None)
    foundry_agent = _load_foundry_module()
    foundry_agent.op_agent_chat(initial_message)


def op_agent_destroy(args: argparse.Namespace) -> None:
    """Delete the Foundry agent."""
    yes = getattr(args, "yes", False)
    foundry_agent = _load_foundry_module()
    foundry_agent.op_agent_destroy(yes)


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Zscaler MCP Server — Azure Deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "MCP Server Operations:\n"
            "  deploy         Interactive guided deployment to Azure\n"
            "  destroy        Tear down all Azure resources (rollback)\n"
            "  status         Show deployment status and health\n"
            "  logs           Stream container/VM logs\n"
            "  ssh            SSH into VM (VM deployments only)\n"
            "\n"
            "Foundry Agent Operations:\n"
            "  agent_create   Create a Foundry agent with Zscaler MCP tools\n"
            "  agent_status   Show Foundry agent status\n"
            "  agent_chat     Start interactive chat with the agent\n"
            "  agent_destroy  Delete the Foundry agent\n"
        ),
    )
    sub = p.add_subparsers(dest="operation")

    # MCP Server operations
    sub.add_parser("deploy", help="Interactive guided deployment to Azure")

    ds = sub.add_parser("destroy", help="Tear down all Azure resources")
    ds.add_argument("--resource-group", default=None, help="Azure resource group")
    ds.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    st = sub.add_parser("status", help="Show deployment status")
    st.add_argument("--resource-group", default=None, help="Azure resource group")

    lg = sub.add_parser("logs", help="Stream container/VM logs")
    lg.add_argument("--resource-group", default=None, help="Azure resource group")

    sub.add_parser("ssh", help="SSH into VM (VM deployments only)")

    # Foundry Agent operations
    sub.add_parser("agent_create", help="Create Foundry agent with Zscaler MCP tools")
    sub.add_parser("agent_status", help="Show Foundry agent status")

    ac = sub.add_parser("agent_chat", help="Interactive chat with Foundry agent")
    ac.add_argument("--message", "-m", default=None, help="Initial message to send")

    ad = sub.add_parser("agent_destroy", help="Delete Foundry agent")
    ad.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    return p


OPERATIONS = {
    "deploy": op_deploy,
    "destroy": op_destroy,
    "status": op_status,
    "logs": op_logs,
    "ssh": op_ssh,
    "agent_create": op_agent_create,
    "agent_status": op_agent_status,
    "agent_chat": op_agent_chat,
    "agent_destroy": op_agent_destroy,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.operation:
        parser.print_help()
        sys.exit(1)

    OPERATIONS[args.operation](args)


if __name__ == "__main__":
    main()
