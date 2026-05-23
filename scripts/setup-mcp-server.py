#!/usr/bin/env python3
"""
Zscaler MCP Server — Interactive Local Deployment

Single entry point for deploying the Zscaler MCP Server locally with any of
the five supported authentication modes, then auto-configuring every detected
AI agent to use it.

What it does:

  1. Prompts for authentication mode (jwt | zscaler | api-key | oidcproxy | none)
  2. Prompts for transport (streamable-http | stdio); rejects incompatible combos
  3. Prompts for an .env file path OR collects credentials interactively
  4. Pulls zscaler/zscaler-mcp-server:latest from Docker Hub (no local build)
  5. Starts the container with the right entrypoint + env wiring for the mode
  6. Verifies the endpoint responds correctly for the chosen auth mode
  7. Auto-detects installed AI agents (Claude Desktop, Claude Code, Cursor,
     Gemini CLI, VS Code, Windsurf, Copilot CLI) and offers to configure each

Supported on macOS, Linux, and Windows.

Image source: docker.io/zscaler/zscaler-mcp-server:latest (Docker Hub).
The image is consumed as-is. For OIDCProxy mode the script overrides the
container's entrypoint with an inline Python program that constructs the
OIDCProxy auth provider — there are no image modifications.

Re-run anytime: this script is idempotent. Re-running with a different auth
mode tears down the previous container and reconfigures all agents.
"""

from __future__ import annotations

import argparse
import atexit
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
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

# ════════════════════════════════════════════════════════════════════════
#  Constants
# ════════════════════════════════════════════════════════════════════════

DOCKER_IMAGE = "zscaler/zscaler-mcp-server:latest"
CONTAINER_NAME = "zscaler-mcp-server"
DEFAULT_PORT = "8000"
DEFAULT_AUDIENCE = "zscaler-mcp-server"
SYSTEM = platform.system()
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

AUTH_MODES = ("jwt", "zscaler", "api-key", "oidcproxy", "none")
TRANSPORT_MODES = ("streamable-http", "stdio")

# Auth modes that require an HTTP transport. Stdio with these is rejected.
HTTP_ONLY_AUTH_MODES = {"jwt", "zscaler", "api-key", "oidcproxy"}


# ════════════════════════════════════════════════════════════════════════
#  ANSI colors
# ════════════════════════════════════════════════════════════════════════

_COLOURS_ENABLED = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

if _COLOURS_ENABLED and SYSTEM == "Windows":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        _COLOURS_ENABLED = False

RED = "\033[0;31m" if _COLOURS_ENABLED else ""
GREEN = "\033[0;32m" if _COLOURS_ENABLED else ""
YELLOW = "\033[1;33m" if _COLOURS_ENABLED else ""
BLUE = "\033[0;34m" if _COLOURS_ENABLED else ""
CYAN = "\033[0;36m" if _COLOURS_ENABLED else ""
BOLD = "\033[1m" if _COLOURS_ENABLED else ""
DIM = "\033[2m" if _COLOURS_ENABLED else ""
NC = "\033[0m" if _COLOURS_ENABLED else ""


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


def banner(title: str) -> None:
    print()
    print("=" * 76)
    print(f"  {BOLD}{title}{NC}")
    print("=" * 76)
    print()


def section(title: str) -> None:
    print()
    print(f"{CYAN}── {title} {'─' * (72 - len(title))}{NC}")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Inline entrypoint for OIDCProxy mode
# ════════════════════════════════════════════════════════════════════════
#
# OIDCProxy is the only auth mode that cannot be wired up via env vars
# alone — it needs to be passed programmatically as `auth=` to
# ZscalerMCPServer. So we override the container entrypoint with this
# inline Python program. Copy of the source-of-truth in
# local_dev/scripts/setup-oidcproxy-auth.py — keep them in sync if you
# change the OIDCProxy bootstrap.

_OIDCPROXY_INLINE_ENTRYPOINT = '''
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
'''


# ════════════════════════════════════════════════════════════════════════
#  Shell + HTTP helpers
# ════════════════════════════════════════════════════════════════════════


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, **kwargs)


def http_get(url: str, *, headers: dict[str, str] | None = None, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)


def http_post(
    url: str,
    *,
    data: dict | str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> tuple[int, str]:
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        body = data.encode("utf-8")
    else:
        body = b""

    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in (headers or {}).items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)


# ════════════════════════════════════════════════════════════════════════
#  .env file handling
# ════════════════════════════════════════════════════════════════════════


def load_env(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.is_file():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


# ────────────────────────────────────────────────────────────────────────
# Docker's --env-file parser is much stricter than typical .env loaders:
# only `#` is a comment marker, no `export` prefix, no whitespace in keys.
# We sanitize a copy to a temp file rather than mutating the user's .env.
# ────────────────────────────────────────────────────────────────────────

_TEMP_ENV_FILES: list[Path] = []
_VALID_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitise_env_for_docker(env_path: Path) -> Path:
    raw = env_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")

    sanitised: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            sanitised.append(line.rstrip())
            continue
        if stripped.startswith(";"):
            sanitised.append("# " + stripped.lstrip(";").lstrip())
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        if not key or not _VALID_KEY.match(key):
            continue
        sanitised.append(f"{key}={value}")

    text_out = "\n".join(sanitised).rstrip() + "\n"

    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        prefix=".env.docker-sanitised-", suffix=".env",
        delete=False,
    )
    try:
        tmp.write(text_out)
    finally:
        tmp.close()
    p = Path(tmp.name)
    _TEMP_ENV_FILES.append(p)
    return p


def _cleanup_temp_env_files() -> None:
    for p in _TEMP_ENV_FILES:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


atexit.register(_cleanup_temp_env_files)


# Stable directory for persisted stdio env files (survives script exit).
_STDIO_ENV_DIR = Path.home() / ".config" / "zscaler-mcp"


def _persist_env_for_stdio(source: Path) -> Path:
    """Copy the sanitized env file to a stable location that survives
    script exit, so that AI agents can reference it in ``--env-file``
    long after this script has terminated."""
    _STDIO_ENV_DIR.mkdir(parents=True, exist_ok=True)
    dest = _STDIO_ENV_DIR / "docker-stdio.env"
    dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


# ════════════════════════════════════════════════════════════════════════
#  JSON config writer (idempotent merge)
# ════════════════════════════════════════════════════════════════════════


def upsert_json_config(path: Path, updater: Callable[[dict], None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if path.is_file():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            warn(f"  Could not parse existing {path.name} — starting fresh")
            config = {}

    updater(config)

    try:
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        die(f"Failed to write config to {path}: {exc}")


# ════════════════════════════════════════════════════════════════════════
#  Interactive prompts
# ════════════════════════════════════════════════════════════════════════


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val or default


def prompt_secret(label: str) -> str:
    return getpass.getpass(f"  {label}: ").strip()


def prompt_choice(label: str, options: list[str], default: str | None = None) -> str:
    print(f"\n  {BOLD}{label}{NC}")
    for i, opt in enumerate(options, start=1):
        marker = f"{DIM}(default){NC}" if opt == default else ""
        print(f"    {i}. {opt}  {marker}")
    while True:
        raw = input(f"\n  Choose [1-{len(options)}]: ").strip()
        if not raw and default:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        warn(f"  Enter a number 1-{len(options)}.")


def prompt_yes_no(label: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"  {label} {suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False


# ════════════════════════════════════════════════════════════════════════
#  AI agent registry — config paths + writers
# ════════════════════════════════════════════════════════════════════════
#
# Each agent declares:
#   - name:         display name
#   - config_path:  function returning the OS-specific config path
#   - exists_check: function returning True if the agent appears installed
#   - write_http:   writer for HTTP transport (Bearer | basic | none)
#   - write_stdio:  writer for stdio transport (docker run -i ...)
#
# The writer signature is:
#   def writer(config: dict, ctx: AgentWriteContext) -> None
#
# All agents share the same `mcpServers` JSON shape (the de-facto standard
# from Claude Desktop). VS Code uses a slightly different shape under
# `servers`, handled per-agent.


class AgentWriteContext:
    """Everything the per-agent writers need to render a server entry."""

    def __init__(
        self,
        *,
        server_name: str,
        transport: str,
        auth_mode: str,
        url: str,
        headers: dict[str, str],
        env_file_path: Optional[Path],
        env_inline: dict[str, str],
        image: str,
    ) -> None:
        self.server_name = server_name
        self.transport = transport
        self.auth_mode = auth_mode
        self.url = url
        self.headers = headers
        self.env_file_path = env_file_path
        self.env_inline = env_inline
        self.image = image


def _claude_desktop_path() -> Path:
    if SYSTEM == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _claude_code_path() -> Path:
    return Path.home() / ".claude.json"


def _cursor_path() -> Path:
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json"
    return Path.home() / ".cursor" / "mcp.json"


def _gemini_cli_path() -> Path:
    return Path.home() / ".gemini" / "settings.json"


def _vscode_path() -> Path:
    if SYSTEM == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Code" / "User" / "mcp.json"
    return Path.home() / ".config" / "Code" / "User" / "mcp.json"


def _windsurf_path() -> Path:
    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def _copilot_cli_path() -> Path:
    if SYSTEM == "Darwin":
        return Path.home() / "Library" / "Application Support" / "github-copilot" / "mcp.json"
    if SYSTEM == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "github-copilot" / "mcp.json"
    return Path.home() / ".config" / "github-copilot" / "mcp.json"


# ── HTTP-mode entry builders (mcp-remote shim) ───────────────────────────


def _build_mcp_remote_args(ctx: AgentWriteContext) -> list[str]:
    args = ["-y", "mcp-remote", ctx.url]
    for k, v in ctx.headers.items():
        args.extend(["--header", f"{k}: {v}"])
    return args


def _http_command_entry(ctx: AgentWriteContext) -> dict:
    """For agents that spawn mcp-remote via npx (Claude Desktop, Claude Code)."""
    if SYSTEM == "Windows":
        return {
            "command": "cmd",
            "args": ["/c", "npx", *_build_mcp_remote_args(ctx)],
        }
    return {
        "command": "npx",
        "args": _build_mcp_remote_args(ctx),
    }


def _http_url_entry(ctx: AgentWriteContext) -> dict:
    """For agents that speak HTTP/SSE natively (Cursor, Windsurf, VS Code)."""
    return {
        "url": ctx.url,
        "headers": dict(ctx.headers) if ctx.headers else {},
    }


# ── Stdio-mode entry builder (docker run -i ...) ─────────────────────────


def _stdio_docker_entry(ctx: AgentWriteContext) -> dict:
    args = ["run", "--rm", "-i"]

    if ctx.env_file_path is not None:
        args.extend(["--env-file", str(ctx.env_file_path)])

    for k, v in ctx.env_inline.items():
        args.extend(["-e", f"{k}={v}"])

    args.append(ctx.image)
    args.extend(["--transport", "stdio"])

    return {"command": "docker", "args": args}


# ── Per-agent config writers ─────────────────────────────────────────────


def _write_claude_desktop(config: dict, ctx: AgentWriteContext) -> None:
    config.setdefault("mcpServers", {})
    if ctx.transport == "stdio":
        config["mcpServers"][ctx.server_name] = _stdio_docker_entry(ctx)
    else:
        config["mcpServers"][ctx.server_name] = _http_command_entry(ctx)


def _write_claude_code(config: dict, ctx: AgentWriteContext) -> None:
    # Claude Code stores per-project + global servers under "mcpServers"
    # at the top level of ~/.claude.json. Same shape as Desktop.
    _write_claude_desktop(config, ctx)


def _write_cursor(config: dict, ctx: AgentWriteContext) -> None:
    config.setdefault("mcpServers", {})
    if ctx.transport == "stdio":
        config["mcpServers"][ctx.server_name] = _stdio_docker_entry(ctx)
    else:
        config["mcpServers"][ctx.server_name] = _http_url_entry(ctx)


def _write_gemini_cli(config: dict, ctx: AgentWriteContext) -> None:
    config.setdefault("mcpServers", {})
    if ctx.transport == "stdio":
        config["mcpServers"][ctx.server_name] = _stdio_docker_entry(ctx)
    else:
        # Gemini CLI uses {url, httpHeaders} for HTTP transport.
        entry: dict = {"url": ctx.url}
        if ctx.headers:
            entry["httpHeaders"] = dict(ctx.headers)
        config["mcpServers"][ctx.server_name] = entry


def _write_vscode(config: dict, ctx: AgentWriteContext) -> None:
    # VS Code's MCP config uses "servers" (not "mcpServers").
    config.setdefault("servers", {})
    if ctx.transport == "stdio":
        config["servers"][ctx.server_name] = {
            "type": "stdio",
            **_stdio_docker_entry(ctx),
        }
    else:
        entry: dict = {"type": "http", "url": ctx.url}
        if ctx.headers:
            entry["headers"] = dict(ctx.headers)
        config["servers"][ctx.server_name] = entry


def _write_windsurf(config: dict, ctx: AgentWriteContext) -> None:
    # Windsurf uses the Claude Desktop shape.
    _write_claude_desktop(config, ctx)


def _write_copilot_cli(config: dict, ctx: AgentWriteContext) -> None:
    config.setdefault("mcpServers", {})
    if ctx.transport == "stdio":
        config["mcpServers"][ctx.server_name] = _stdio_docker_entry(ctx)
    else:
        config["mcpServers"][ctx.server_name] = _http_url_entry(ctx)


# ── Detection (does the agent appear installed?) ─────────────────────────


def _claude_desktop_installed() -> bool:
    if SYSTEM == "Darwin":
        return Path("/Applications/Claude.app").exists() or _claude_desktop_path().exists()
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
    if cmd_exists("cursor"):
        return True
    return _cursor_path().exists()


def _gemini_cli_installed() -> bool:
    return cmd_exists("gemini") or _gemini_cli_path().exists()


def _vscode_installed() -> bool:
    if SYSTEM == "Darwin" and Path("/Applications/Visual Studio Code.app").exists():
        return True
    if cmd_exists("code"):
        return True
    return _vscode_path().exists()


def _windsurf_installed() -> bool:
    if SYSTEM == "Darwin" and Path("/Applications/Windsurf.app").exists():
        return True
    return cmd_exists("windsurf") or _windsurf_path().exists()


def _copilot_cli_installed() -> bool:
    return cmd_exists("gh") and (cmd_exists("copilot") or _copilot_cli_path().exists())


AGENTS: list[dict] = [
    {
        "id": "claude_desktop",
        "name": "Claude Desktop",
        "path_fn": _claude_desktop_path,
        "installed_fn": _claude_desktop_installed,
        "writer": _write_claude_desktop,
    },
    {
        "id": "claude_code",
        "name": "Claude Code (CLI)",
        "path_fn": _claude_code_path,
        "installed_fn": _claude_code_installed,
        "writer": _write_claude_code,
    },
    {
        "id": "cursor",
        "name": "Cursor",
        "path_fn": _cursor_path,
        "installed_fn": _cursor_installed,
        "writer": _write_cursor,
    },
    {
        "id": "gemini_cli",
        "name": "Gemini CLI",
        "path_fn": _gemini_cli_path,
        "installed_fn": _gemini_cli_installed,
        "writer": _write_gemini_cli,
    },
    {
        "id": "vscode",
        "name": "VS Code (MCP)",
        "path_fn": _vscode_path,
        "installed_fn": _vscode_installed,
        "writer": _write_vscode,
    },
    {
        "id": "windsurf",
        "name": "Windsurf",
        "path_fn": _windsurf_path,
        "installed_fn": _windsurf_installed,
        "writer": _write_windsurf,
    },
    {
        "id": "copilot_cli",
        "name": "GitHub Copilot CLI",
        "path_fn": _copilot_cli_path,
        "installed_fn": _copilot_cli_installed,
        "writer": _write_copilot_cli,
    },
]


# ════════════════════════════════════════════════════════════════════════
#  Auth-mode prompts (collect what each mode needs)
# ════════════════════════════════════════════════════════════════════════


def collect_jwt_creds(env_vars: dict[str, str]) -> dict[str, str]:
    domain = env_vars.get("AUTH0_DOMAIN", "").strip()
    client_id = env_vars.get("AUTH0_CLIENT_ID", "").strip()
    client_secret = env_vars.get("AUTH0_CLIENT_SECRET", "").strip()
    audience = env_vars.get("AUTH0_AUDIENCE", "").strip() or DEFAULT_AUDIENCE

    if not domain:
        domain = prompt("Auth0 Domain (e.g. your-tenant.us.auth0.com)")
    if not client_id:
        client_id = prompt("Auth0 M2M Client ID")
    if not client_secret:
        client_secret = prompt_secret("Auth0 M2M Client Secret")
    if not env_vars.get("AUTH0_AUDIENCE"):
        audience = prompt("Auth0 API Audience", default=audience)

    if not (domain and client_id and client_secret):
        die("Auth0 domain, client ID, and client secret are all required for jwt mode.")

    return {
        "AUTH0_DOMAIN": domain,
        "AUTH0_CLIENT_ID": client_id,
        "AUTH0_CLIENT_SECRET": client_secret,
        "AUTH0_AUDIENCE": audience,
    }


def collect_zscaler_creds(env_vars: dict[str, str]) -> dict[str, str]:
    cid = env_vars.get("ZSCALER_CLIENT_ID", "").strip()
    csec = env_vars.get("ZSCALER_CLIENT_SECRET", "").strip()
    vd = env_vars.get("ZSCALER_VANITY_DOMAIN", "").strip()
    cust = env_vars.get("ZSCALER_CUSTOMER_ID", "").strip()
    cloud = env_vars.get("ZSCALER_CLOUD", "").strip() or "production"

    if not cid:
        cid = prompt("Zscaler OneAPI Client ID")
    if not csec:
        csec = prompt_secret("Zscaler OneAPI Client Secret")
    if not vd:
        vd = prompt("Zscaler Vanity Domain (no scheme, e.g. 'customer')")
    if not cust:
        cust = prompt("Zscaler Customer ID")
    if not env_vars.get("ZSCALER_CLOUD"):
        cloud = prompt("Zscaler Cloud", default=cloud)

    if not (cid and csec and vd and cust):
        die("ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, ZSCALER_VANITY_DOMAIN, and ZSCALER_CUSTOMER_ID are all required.")

    return {
        "ZSCALER_CLIENT_ID": cid,
        "ZSCALER_CLIENT_SECRET": csec,
        "ZSCALER_VANITY_DOMAIN": vd,
        "ZSCALER_CUSTOMER_ID": cust,
        "ZSCALER_CLOUD": cloud,
    }


def collect_api_key(env_vars: dict[str, str]) -> dict[str, str]:
    api_key = env_vars.get("ZSCALER_MCP_AUTH_API_KEY", "").strip()
    if api_key:
        ok(f"  API key loaded from .env: {api_key[:6]}…")
        return {"ZSCALER_MCP_AUTH_API_KEY": api_key}

    print()
    print("  No ZSCALER_MCP_AUTH_API_KEY found in .env.")
    if prompt_yes_no("  Generate a new random 32-char API key?", default=True):
        alphabet = string.ascii_letters + string.digits
        api_key = "sk-" + "".join(secrets.choice(alphabet) for _ in range(32))
        ok(f"  Generated API key: {api_key}")
        warn("  Save this key — it will be needed by every MCP client.")
    else:
        api_key = prompt_secret("Enter API key")

    if not api_key:
        die("API key is required for api-key mode.")
    return {"ZSCALER_MCP_AUTH_API_KEY": api_key}


def collect_oidcproxy_creds(env_vars: dict[str, str], port: str) -> dict[str, str]:
    domain = env_vars.get("AUTH0_DOMAIN", "").strip()
    client_id = env_vars.get("AUTH0_CLIENT_ID", "").strip()
    client_secret = env_vars.get("AUTH0_CLIENT_SECRET", "").strip()
    audience = env_vars.get("AUTH0_AUDIENCE", "").strip() or DEFAULT_AUDIENCE

    if not domain:
        domain = prompt("Auth0 Domain (e.g. your-tenant.us.auth0.com)")
    if not client_id:
        client_id = prompt("Auth0 Application Client ID")
    if not client_secret:
        client_secret = prompt_secret("Auth0 Application Client Secret")
    if not env_vars.get("AUTH0_AUDIENCE"):
        audience = prompt("Auth0 API Audience", default=audience)

    if not (domain and client_id and client_secret):
        die("Auth0 domain, client ID, and client secret are all required for oidcproxy mode.")

    return {
        "OIDCPROXY_CONFIG_URL": f"https://{domain}/.well-known/openid-configuration",
        "OIDCPROXY_CLIENT_ID": client_id,
        "OIDCPROXY_CLIENT_SECRET": client_secret,
        "OIDCPROXY_BASE_URL": f"http://localhost:{port}",
        "OIDCPROXY_AUDIENCE": audience,
    }


# ════════════════════════════════════════════════════════════════════════
#  Container management
# ════════════════════════════════════════════════════════════════════════


def docker_ready() -> None:
    if not cmd_exists("docker"):
        die("Docker is not installed or not in PATH.\nInstall Docker Desktop: https://docs.docker.com/get-docker/")
    r = run(["docker", "info"])
    if r.returncode != 0:
        die("Docker is installed but the daemon is not running. Start Docker Desktop and re-run.")
    ok("Docker is ready.")


def docker_pull_image() -> None:
    info(f"Pulling {DOCKER_IMAGE} from Docker Hub…")
    r = subprocess.run(["docker", "pull", DOCKER_IMAGE])
    if r.returncode != 0:
        die(f"docker pull {DOCKER_IMAGE} failed. Check network and Docker Hub access.")
    ok(f"Image pulled: {DOCKER_IMAGE}")


def docker_remove_existing(name: str) -> None:
    run(["docker", "stop", name])
    run(["docker", "rm", name])


def docker_run_http(
    *,
    container_name: str,
    port: str,
    env_file: Path,
    extra_env: dict[str, str],
    auth_mode: str,
    debug: bool,
    bind_mount_source: Optional[Path] = None,
) -> None:
    docker_remove_existing(container_name)

    # The two .env paths are deliberately distinct:
    #
    # * ``env_file`` is the Docker-sanitised copy (a temp file) used by
    #   ``--env-file`` to seed os.environ at container boot. Docker's
    #   parser is strict and chokes on `export FOO=bar`, comments mid-
    #   line, etc., so we always sanitise.
    #
    # * ``bind_mount_source`` is the OPERATOR-EDITED .env on the host.
    #   When set, it gets bind-mounted at /app/.env so the in-container
    #   reload path (`docker exec <container> zscaler-mcp restart`) sees
    #   live edits without recreating the container. Skipped when the
    #   resolved env file was synthesized from prompts (temp, vanishes
    #   on script exit) or when the operator opted out via
    #   ``--legacy-env-file``.
    args = [
        "docker", "run", "-d",
        "--restart=unless-stopped",
        "--name", container_name,
        "-p", f"{port}:{port}",
        "--env-file", str(env_file),
    ]

    if bind_mount_source is not None:
        args.extend(["-v", f"{bind_mount_source}:/app/.env:ro"])
        args.extend(["-e", "ZSCALER_MCP_DOTENV_PATH=/app/.env"])

    for k, v in extra_env.items():
        args.extend(["-e", f"{k}={v}"])

    if debug:
        args.extend(["-e", "FASTMCP_DEBUG=true"])

    if auth_mode == "oidcproxy":
        # Override entrypoint with the inline Python program that wires
        # OIDCProxy as the auth= parameter to ZscalerMCPServer.
        args.extend([
            "--entrypoint", "python",
            DOCKER_IMAGE,
            "-c", _OIDCPROXY_INLINE_ENTRYPOINT,
        ])
    else:
        args.extend([
            DOCKER_IMAGE,
            "--transport", "streamable-http",
            "--host", "0.0.0.0",
            "--port", str(port),
        ])

    r = subprocess.run(args)
    if r.returncode != 0:
        die("Failed to start Docker container.")

    info("Waiting for container to initialize…")
    time.sleep(8)

    r = run([
        "docker", "ps",
        "--filter", f"name={container_name}",
        "--filter", "status=running",
        "-q",
    ])
    if not r.stdout.strip():
        error("Container failed to stay running. Recent logs:")
        r = run(["docker", "logs", container_name])
        print((r.stdout or "") + (r.stderr or ""))
        die("Inspect the logs above and re-run.")

    ok(f"Container running: {container_name}")


# ════════════════════════════════════════════════════════════════════════
#  Endpoint verification
# ════════════════════════════════════════════════════════════════════════


def verify_endpoint(url: str, auth_mode: str, headers: dict[str, str]) -> None:
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "setup-mcp-server", "version": "1.0"},
        },
    })
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        **headers,
    }

    code, body = http_post(url, data=payload, headers=h, timeout=30)

    if code in (200, 202):
        ok(f"Endpoint accepted authenticated request (HTTP {code}).")
    elif code == 401:
        if auth_mode == "none":
            error("Endpoint returned 401 even though auth is disabled — server may be misconfigured.")
            print(body[:400])
        else:
            error("Endpoint returned 401 — credentials were rejected.")
            print(body[:400])
            warn("Check the credentials / audience / issuer above and re-run.")
    elif code == 0:
        warn(f"Could not reach {url}: {body}")
        warn("If the container just started, give it a few seconds and try again.")
    else:
        warn(f"Endpoint returned HTTP {code}. Auth may still be OK; inspect logs:")
        print(f"    docker logs {CONTAINER_NAME}")


# ════════════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════════════


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Interactive local deployment for the Zscaler MCP Server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--auth-mode", choices=AUTH_MODES,
                    help="Skip the auth-mode prompt.")
    p.add_argument("--transport", choices=TRANSPORT_MODES,
                    help="Skip the transport prompt.")
    p.add_argument("--env-file",
                    help="Path to a .env file. If omitted, the script prompts.")
    p.add_argument("--port", default=DEFAULT_PORT,
                    help=f"HTTP port for the server (default: {DEFAULT_PORT}).")
    p.add_argument("--container-name", default=CONTAINER_NAME,
                    help=f"Docker container name (default: {CONTAINER_NAME}).")
    p.add_argument("--debug", action="store_true",
                    help="Enable FASTMCP_DEBUG inside the container.")
    p.add_argument("--skip-pull", action="store_true",
                    help="Skip 'docker pull' (use the locally cached image).")
    p.add_argument("--skip-verify", action="store_true",
                    help="Skip endpoint verification.")
    p.add_argument("--skip-agent-config", action="store_true",
                    help="Don't auto-configure any AI agents.")
    p.add_argument("--legacy-env-file", action="store_true",
                    help=(
                        "Use the legacy --env-file behaviour only "
                        "(snapshot at container start). The default now "
                        "ALSO bind-mounts the .env into /app/.env so "
                        "`docker exec <container> zscaler-mcp restart` "
                        "picks up live edits. Pass this flag to opt out "
                        "(e.g. when you want the .env to live elsewhere "
                        "or when the source is a temp file)."
                    ))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    banner("Zscaler MCP Server — Interactive Local Deployment")

    # ── Step 0: Auth mode + transport ────────────────────────────────────

    section("Step 0: Choose authentication and transport")

    auth_mode = args.auth_mode or prompt_choice(
        "Authentication mode:",
        list(AUTH_MODES),
        default="zscaler",
    )

    transport = args.transport or prompt_choice(
        "Transport:",
        list(TRANSPORT_MODES),
        default="streamable-http",
    )

    if transport == "stdio" and auth_mode in HTTP_ONLY_AUTH_MODES:
        die(
            f"Auth mode '{auth_mode}' requires HTTP transport — there's no HTTP "
            f"boundary in stdio mode for the auth middleware to enforce.\n\n"
            f"  Either:\n"
            f"    • Re-run and choose transport='streamable-http' (keeps {auth_mode} auth), or\n"
            f"    • Re-run and choose auth-mode='none' (single-user local stdio)."
        )

    ok(f"Auth mode: {BOLD}{auth_mode}{NC}")
    ok(f"Transport: {BOLD}{transport}{NC}")

    # ── Step 1: Env file or interactive credential entry ────────────────

    section("Step 1: Locate environment / credentials")

    env_file: Optional[Path] = None
    env_vars: dict[str, str] = {}

    if args.env_file:
        env_file = Path(args.env_file).resolve()
        if not env_file.is_file():
            die(f"--env-file {env_file} does not exist.")
        env_vars = load_env(env_file)
        ok(f".env loaded from {env_file}")
    else:
        # Auto-discover an existing .env in the standard locations.
        # Order: cwd → script dir → project root.
        discovered: Path | None = None
        for guess in (Path.cwd() / ".env", SCRIPT_DIR / ".env", PROJECT_ROOT / ".env"):
            if guess.is_file():
                discovered = guess.resolve()
                break

        if discovered is not None:
            print()
            ok(f".env auto-detected at {discovered}")
            info("  (use --env-file to point at a different file, or pick option 2 below to enter creds manually)")
            print()
            print("  How do you want to provide credentials?")
            print(f"    1. Use the auto-detected .env above  {DIM}(recommended){NC}")
            print("    2. Enter credentials interactively (ignores the .env above)")
            choice = ""
            while choice not in ("1", "2"):
                choice = input("\n  Choose [1-2] (Enter = 1): ").strip() or "1"

            if choice == "1":
                env_file = discovered
                env_vars = load_env(env_file)
                ok(f".env loaded from {env_file}")
        else:
            print()
            warn("No .env auto-detected in cwd, scripts/, or project root.")
            print()
            print("  How do you want to provide credentials?")
            print("    1. Path to an existing .env file")
            print("    2. Enter credentials interactively")
            choice = ""
            while choice not in ("1", "2"):
                choice = input("\n  Choose [1-2]: ").strip()

            if choice == "1":
                path_str = prompt(".env file path")
                if not path_str:
                    die("An .env path is required when option 1 is chosen.")
                env_file = Path(path_str).expanduser().resolve()
                if not env_file.is_file():
                    die(f".env not found at {env_file}")
                env_vars = load_env(env_file)
                ok(f".env loaded from {env_file}")

    # If we still don't have an env file, build one in tmp from prompts so
    # docker --env-file always has something to read.
    auth_extra_env = collect_mode_credentials(auth_mode, env_vars, args.port)

    env_file_was_synthesized = False
    if env_file is None:
        merged = {**env_vars, **auth_extra_env}
        # Always need Zscaler API creds (regardless of MCP auth mode)
        if "ZSCALER_CLIENT_ID" not in merged:
            print()
            warn("ZSCALER_CLIENT_ID not set — collecting Zscaler OneAPI credentials")
            zs = collect_zscaler_creds({})
            merged.update(zs)
        env_file = _materialize_env_file(merged)
        env_file_was_synthesized = True
        ok(f"Synthesized .env at {env_file}")

    # Sanitize for Docker's strict parser regardless of source.
    docker_env_file = sanitise_env_for_docker(env_file)

    # Bind-mount decision: default ON (so `docker exec ... zscaler-mcp
    # restart` inside the container picks up live host-side .env edits),
    # but skip when the source is a synthesized temp file (which is
    # auto-deleted on script exit, orphaning the bind mount) or when
    # the operator explicitly opted out.
    bind_mount_source: Optional[Path] = None
    if args.legacy_env_file:
        info("Using --legacy-env-file: .env is snapshotted at container start.")
    elif env_file_was_synthesized:
        info(
            "Synthesized .env is a temp file — falling back to --env-file "
            "snapshot. To use the live-reload path, point --env-file at a "
            "persistent .env on disk and re-run."
        )
    else:
        bind_mount_source = env_file
        info(f"Bind-mounting {env_file} → /app/.env (live-reload enabled).")

    # ── Step 2: Docker readiness + image pull ──────────────────────────

    section("Step 2: Docker image")

    docker_ready()

    if not args.skip_pull:
        docker_pull_image()
    else:
        info("Skipping docker pull (--skip-pull). Verifying image is locally available…")
        r = run(["docker", "image", "inspect", DOCKER_IMAGE])
        if r.returncode != 0:
            die(f"--skip-pull was set but {DOCKER_IMAGE} is not available locally.")
        ok(f"Using cached image {DOCKER_IMAGE}")

    # ── Step 3: Start the server (HTTP modes only) ──────────────────────

    server_url = f"http://localhost:{args.port}/mcp"

    if transport == "streamable-http":
        section("Step 3: Start the MCP server container")

        extra_env = _http_runtime_env(auth_mode, auth_extra_env, args.port)

        docker_run_http(
            container_name=args.container_name,
            port=args.port,
            env_file=docker_env_file,
            extra_env=extra_env,
            auth_mode=auth_mode,
            debug=args.debug,
            bind_mount_source=bind_mount_source,
        )

        # ── Step 4: Verify ────────────────────────────────────────────

        if args.skip_verify:
            warn("Skipping endpoint verification (--skip-verify).")
        else:
            section("Step 4: Verify the endpoint responds")
            verify_headers = _client_auth_headers(auth_mode, auth_extra_env, env_vars)
            verify_endpoint(server_url, auth_mode, verify_headers)
    else:
        section("Step 3: Stdio mode — no long-running container")
        info("Stdio servers are spawned by the AI agent on demand. The agent")
        info("will run the configured `docker run --rm -i …` command itself.")
        info("Skipping container start and endpoint verification.")

    # ── Step 5: Configure AI agents ─────────────────────────────────────

    if args.skip_agent_config:
        warn("Skipping agent configuration (--skip-agent-config).")
    else:
        section("Step 5: Configure AI agents")
        client_headers = _client_auth_headers(auth_mode, auth_extra_env, env_vars)

        # For stdio mode, persist the sanitized env file to a stable path
        # that survives script exit. The temp file gets cleaned up by atexit,
        # but agents spawn the container long after this script terminates.
        stdio_env_path: Optional[Path] = None
        if transport == "stdio":
            stdio_env_path = _persist_env_for_stdio(docker_env_file)
            ok(f"Persisted stdio env file to {stdio_env_path}")

        ctx = AgentWriteContext(
            server_name=args.container_name,
            transport=transport,
            auth_mode=auth_mode,
            url=server_url,
            headers=client_headers,
            env_file_path=stdio_env_path if transport == "stdio" else None,
            env_inline=auth_extra_env if transport == "stdio" else {},
            image=DOCKER_IMAGE,
        )
        configure_agents(ctx)

    # ── Summary ────────────────────────────────────────────────────────

    print_summary(
        auth_mode=auth_mode,
        transport=transport,
        url=server_url,
        port=args.port,
        container_name=args.container_name,
        auth_extra_env=auth_extra_env,
    )


# ════════════════════════════════════════════════════════════════════════
#  Helpers consumed by main()
# ════════════════════════════════════════════════════════════════════════


def collect_mode_credentials(
    auth_mode: str,
    env_vars: dict[str, str],
    port: str,
) -> dict[str, str]:
    print()
    info(f"Collecting credentials for auth mode: {auth_mode}")

    if auth_mode == "jwt":
        return collect_jwt_creds(env_vars)
    if auth_mode == "zscaler":
        # Zscaler mode reuses the ZSCALER_* OneAPI creds — already in env_file
        # most of the time. Only prompt if missing.
        if not env_vars.get("ZSCALER_CLIENT_ID"):
            return collect_zscaler_creds(env_vars)
        ok("  Zscaler OneAPI credentials already present in .env.")
        return {}
    if auth_mode == "api-key":
        return collect_api_key(env_vars)
    if auth_mode == "oidcproxy":
        return collect_oidcproxy_creds(env_vars, port)
    if auth_mode == "none":
        warn("  Auth mode 'none' — server will accept all connections without authentication.")
        warn("  This is intended for single-user local development only. Do NOT expose the port.")
        return {}
    die(f"Unknown auth mode: {auth_mode}")


def _http_runtime_env(
    auth_mode: str,
    creds: dict[str, str],
    port: str,
) -> dict[str, str]:
    """Per-mode env vars passed to the container for the HTTP server."""
    common = {
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": str(port),
        "ZSCALER_MCP_ALLOW_HTTP": "true",
    }

    if auth_mode == "jwt":
        domain = creds["AUTH0_DOMAIN"]
        return {
            **common,
            "ZSCALER_MCP_AUTH_ENABLED": "true",
            "ZSCALER_MCP_AUTH_MODE": "jwt",
            "ZSCALER_MCP_AUTH_JWKS_URI": f"https://{domain}/.well-known/jwks.json",
            "ZSCALER_MCP_AUTH_ISSUER": f"https://{domain}/",
            "ZSCALER_MCP_AUTH_AUDIENCE": creds.get("AUTH0_AUDIENCE", DEFAULT_AUDIENCE),
        }
    if auth_mode == "zscaler":
        return {
            **common,
            "ZSCALER_MCP_AUTH_ENABLED": "true",
            "ZSCALER_MCP_AUTH_MODE": "zscaler",
        }
    if auth_mode == "api-key":
        return {
            **common,
            "ZSCALER_MCP_AUTH_ENABLED": "true",
            "ZSCALER_MCP_AUTH_MODE": "api-key",
            "ZSCALER_MCP_AUTH_API_KEY": creds["ZSCALER_MCP_AUTH_API_KEY"],
        }
    if auth_mode == "oidcproxy":
        # OIDCProxy uses the inline entrypoint and reads OIDCPROXY_* directly;
        # ZSCALER_MCP_AUTH_ENABLED is forced false there.
        return {
            **common,
            "OIDCPROXY_CONFIG_URL": creds["OIDCPROXY_CONFIG_URL"],
            "OIDCPROXY_CLIENT_ID": creds["OIDCPROXY_CLIENT_ID"],
            "OIDCPROXY_CLIENT_SECRET": creds["OIDCPROXY_CLIENT_SECRET"],
            "OIDCPROXY_BASE_URL": creds["OIDCPROXY_BASE_URL"],
            "OIDCPROXY_AUDIENCE": creds.get("OIDCPROXY_AUDIENCE", DEFAULT_AUDIENCE),
        }
    if auth_mode == "none":
        return {
            **common,
            "ZSCALER_MCP_AUTH_ENABLED": "false",
        }
    die(f"Unknown auth mode: {auth_mode}")


def _client_auth_headers(
    auth_mode: str,
    creds: dict[str, str],
    env_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    """HTTP headers the AI agent should send when calling the MCP server.

    `creds` carries values that were collected interactively for the chosen
    auth mode (may be empty if .env already had everything). `env_vars`
    carries the full loaded .env so we can fall back to it for zscaler /
    api-key modes when nothing was newly collected.
    """
    env_vars = env_vars or {}

    def _pick(*keys: str) -> str:
        for k in keys:
            v = creds.get(k) or env_vars.get(k)
            if v:
                return v
        return ""

    if auth_mode == "jwt":
        domain = _pick("AUTH0_DOMAIN")
        client_id = _pick("AUTH0_CLIENT_ID")
        client_secret = _pick("AUTH0_CLIENT_SECRET")
        audience = _pick("AUTH0_AUDIENCE") or DEFAULT_AUDIENCE
        token = _fetch_auth0_jwt(
            domain=domain,
            client_id=client_id,
            client_secret=client_secret,
            audience=audience,
        )
        return {"Authorization": f"Bearer {token}"}
    if auth_mode == "zscaler":
        cid = _pick("ZSCALER_CLIENT_ID")
        csec = _pick("ZSCALER_CLIENT_SECRET")
        if not (cid and csec):
            warn(
                "  ZSCALER_CLIENT_ID / ZSCALER_CLIENT_SECRET are missing from both "
                "the .env and the interactively-collected credentials — endpoint "
                "verification will fail with 401."
            )
        # Emit a single `Authorization: Basic base64(id:secret)` header
        # rather than the raw X-Zscaler-Client-ID / -Secret pair. The
        # MCP server accepts both formats (see
        # zscaler_mcp/auth.py::ZscalerAuthProvider), but every other
        # surface in this repo that writes agent configs — the GCP
        # Cloud Run script, the Azure Container Apps / VM / AKS scripts,
        # and the server's own --generate-auth-token sample output —
        # uses the Basic header. Aligning here keeps the JSON written
        # into Claude Desktop / Cursor / VS Code / Windsurf / Gemini /
        # Copilot configs uniform: one credential header, regardless of
        # whether the server is local-via-Docker or remote-via-Cloud-Run.
        b64 = base64.b64encode(f"{cid}:{csec}".encode()).decode()
        return {"Authorization": f"Basic {b64}"}
    if auth_mode == "api-key":
        return {"Authorization": f"Bearer {_pick('ZSCALER_MCP_AUTH_API_KEY')}"}
    if auth_mode == "oidcproxy":
        return {}  # mcp-remote handles OAuth flow; no static header
    return {}


def _fetch_auth0_jwt(*, domain: str, client_id: str, client_secret: str, audience: str) -> str:
    info("  Requesting JWT from Auth0 (client_credentials)…")
    code, body = http_post(
        f"https://{domain}/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": audience,
            "grant_type": "client_credentials",
        },
        headers={"Content-Type": "application/json"},
    )
    try:
        token = json.loads(body).get("access_token", "")
    except json.JSONDecodeError:
        token = ""
    if not token:
        error("Could not get a JWT from Auth0. Response:")
        print(body[:500])
        die("Check Auth0 credentials, audience, and that the M2M grant is enabled.")
    expires_in = json.loads(body).get("expires_in", 0)
    ok(f"  JWT obtained (expires in ~{expires_in // 3600}h).")
    return token


def _materialize_env_file(env: dict[str, str]) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        prefix=".env.zscaler-mcp-", suffix=".env",
        delete=False,
    )
    try:
        for k, v in env.items():
            tmp.write(f"{k}={v}\n")
    finally:
        tmp.close()
    p = Path(tmp.name)
    _TEMP_ENV_FILES.append(p)
    return p


# ════════════════════════════════════════════════════════════════════════
#  Agent configuration loop
# ════════════════════════════════════════════════════════════════════════


def configure_agents(ctx: AgentWriteContext) -> None:
    print("  Detecting installed AI agents…\n")

    detected: list[dict] = []
    for agent in AGENTS:
        try:
            installed = agent["installed_fn"]()
        except Exception:
            installed = False
        marker = f"{GREEN}detected{NC}" if installed else f"{DIM}not found{NC}"
        path = agent["path_fn"]()
        print(f"    • {agent['name']:<25} {marker}    {DIM}{path}{NC}")
        if installed:
            detected.append(agent)

    if not detected:
        print()
        warn("  No AI agents detected. You can still configure manually using the URL/headers above.")
        return

    print()
    if not prompt_yes_no(f"  Configure all {len(detected)} detected agent(s)?", default=True):
        print()
        info("  Per-agent confirmation:")
        keep: list[dict] = []
        for agent in detected:
            if prompt_yes_no(f"    Configure {agent['name']}?", default=True):
                keep.append(agent)
        detected = keep

    if not detected:
        warn("  Nothing to configure — skipping.")
        return

    print()
    for agent in detected:
        path: Path = agent["path_fn"]()
        info(f"  Updating {agent['name']} → {path}")
        try:
            upsert_json_config(path, lambda cfg, a=agent: a["writer"](cfg, ctx))
            ok(f"    Wrote {path}")
        except Exception as exc:
            error(f"    Failed: {exc}")


# ════════════════════════════════════════════════════════════════════════
#  Summary
# ════════════════════════════════════════════════════════════════════════


def print_summary(
    *,
    auth_mode: str,
    transport: str,
    url: str,
    port: str,
    container_name: str,
    auth_extra_env: dict[str, str],
) -> None:
    print()
    print("=" * 76)
    print(f"  {GREEN}Setup complete{NC}")
    print("=" * 76)
    print()
    print(f"  Auth mode:    {BOLD}{auth_mode}{NC}")
    print(f"  Transport:    {BOLD}{transport}{NC}")

    if transport == "streamable-http":
        print(f"  URL:          {url}")
        print(f"  Container:    {container_name}")
        print(f"  Image:        {DOCKER_IMAGE}")
        print()
        print("  Container management:")
        print(f"    Logs:   {DIM}docker logs -f {container_name}{NC}")
        print(f"    Stop:   {DIM}docker stop {container_name}{NC}")
        print(f"    Start:  {DIM}docker start {container_name}{NC}")
    else:
        print(f"  Image:        {DOCKER_IMAGE}")
        print()
        print(f"  {DIM}Stdio mode: agents spawn the container themselves on demand.{NC}")

    print()
    print("  Next steps:")
    print("    1. Restart any AI agent you just configured.")
    if auth_mode == "jwt":
        print("    2. The Bearer token expires in ~1 hour. Re-run this script to refresh it.")
    elif auth_mode == "oidcproxy":
        print("    2. On first connect from an agent, mcp-remote will open a browser for the OAuth flow.")
    elif auth_mode == "api-key":
        api_key = auth_extra_env.get("ZSCALER_MCP_AUTH_API_KEY", "")
        if api_key:
            print(f"    2. Save your API key safely: {api_key}")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Entry point
# ════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        warn("Interrupted by user.")
        sys.exit(130)
