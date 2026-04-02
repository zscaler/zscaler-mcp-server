#!/usr/bin/env python3
"""
Zscaler MCP Server — GCP Cloud Run Deployment

Deploys the Zscaler MCP Server container to Google Cloud Run.
Reads credentials from a .env file or prompts interactively.
Optionally stores credentials in GCP Secret Manager.

Usage:
  python deploy-gcp.py                      # interactive prompts
  python deploy-gcp.py --env-file .env      # read from .env file
  python deploy-gcp.py --teardown           # delete the service
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

# ── Colours ──────────────────────────────────────────────────────────────

_TTY = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
G = "\033[0;32m" if _TTY else ""
B = "\033[0;34m" if _TTY else ""
Y = "\033[1;33m" if _TTY else ""
R = "\033[0;31m" if _TTY else ""
N = "\033[0m" if _TTY else ""


def info(msg):  print(f"{B}[INFO]{N}  {msg}")
def ok(msg):    print(f"{G}[OK]{N}    {msg}")
def warn(msg):  print(f"{Y}[WARN]{N}  {msg}")
def die(msg):   print(f"{R}[ERROR]{N} {msg}"); sys.exit(1)


# ── Helpers ──────────────────────────────────────────────────────────────

def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def run_ok(args, msg, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        die(f"{msg}\n{r.stderr or r.stdout}")
    return r


def load_env(path: Path) -> dict[str, str]:
    env = {}
    if not path.is_file():
        return env
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val or default


def ask_secret(prompt: str) -> str:
    return getpass.getpass(f"  {prompt}: ").strip()


def ask_yn(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    val = input(f"  {prompt} ({d}): ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deploy Zscaler MCP Server to GCP Cloud Run")
    parser.add_argument("--env-file", help="Path to .env file with credentials")
    parser.add_argument("--teardown", action="store_true", help="Delete the Cloud Run service")
    args = parser.parse_args()

    print()
    print("=" * 64)
    print("  Zscaler MCP Server — GCP Cloud Run Deployment")
    print("=" * 64)
    print()

    # ── Load .env if provided ────────────────────────────────────────

    env = {}
    if args.env_file:
        p = Path(args.env_file).resolve()
        if not p.is_file():
            die(f".env file not found: {p}")
        env = load_env(p)
        ok(f"Loaded {len(env)} vars from {p}")
    else:
        for candidate in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"]:
            if candidate.is_file():
                env = load_env(candidate)
                ok(f"Loaded {len(env)} vars from {candidate}")
                break

    print()

    # ── GCP config ───────────────────────────────────────────────────

    info("GCP Configuration")
    project = env.get("GCP_PROJECT_ID") or env.get("PROJECT_ID") or ""
    region = env.get("GCP_REGION") or env.get("REGION") or "us-central1"

    project = ask("GCP Project ID", project)
    region = ask("GCP Region", region)

    if not project:
        die("GCP Project ID is required")

    image = env.get("GCP_IMAGE", "")
    if not image:
        image = ask(
            "Container image",
            "marketplace.gcr.io/zscaler/zscaler-mcp-server:latest",
        )

    print()

    # ── Teardown ─────────────────────────────────────────────────────

    if args.teardown:
        info("Deleting Cloud Run service...")
        run(["gcloud", "run", "services", "delete", "zscaler-mcp-server",
             "--region", region, "--project", project, "--quiet"])
        ok("Service deleted")
        return

    # ── Zscaler credentials ──────────────────────────────────────────

    info("Zscaler API Credentials")

    client_id = env.get("ZSCALER_CLIENT_ID", "")
    client_secret = env.get("ZSCALER_CLIENT_SECRET", "")
    vanity_domain = env.get("ZSCALER_VANITY_DOMAIN", "")
    customer_id = env.get("ZSCALER_CUSTOMER_ID", "")
    cloud = env.get("ZSCALER_CLOUD", "production")

    if client_id:
        ok(f"  Client ID:      {client_id[:10]}... (from .env)")
    else:
        client_id = ask("Zscaler Client ID")

    if client_secret:
        ok(f"  Client Secret:  ******** (from .env)")
    else:
        client_secret = ask_secret("Zscaler Client Secret")

    if vanity_domain:
        ok(f"  Vanity Domain:  {vanity_domain} (from .env)")
    else:
        vanity_domain = ask("Zscaler Vanity Domain")

    if customer_id:
        ok(f"  Customer ID:    {customer_id[:10]}... (from .env)")
    else:
        customer_id = ask("Zscaler Customer ID")

    cloud = ask("Zscaler Cloud", cloud)

    if not client_id or not client_secret:
        die("Client ID and Client Secret are required")

    print()

    # ── Secret Manager ───────────────────────────────────────────────

    info("Credential Storage")
    use_sm = ask_yn("Store credentials in GCP Secret Manager? (recommended)", default=True)

    print()

    # ── Prerequisites ────────────────────────────────────────────────

    info("Checking prerequisites...")

    r = run(["gcloud", "version"])
    if r.returncode != 0:
        die("gcloud CLI is not installed. Install from https://cloud.google.com/sdk")

    run_ok(["gcloud", "config", "set", "project", project], "Failed to set project")

    for api in ["run.googleapis.com", "secretmanager.googleapis.com"]:
        run(["gcloud", "services", "enable", api, "--project", project, "--quiet"])

    ok("Prerequisites verified")
    print()

    # ── Secret Manager setup ─────────────────────────────────────────

    if use_sm:
        info("Setting up Secret Manager...")

        creds = {
            "zscaler-client-id": client_id,
            "zscaler-client-secret": client_secret,
            "zscaler-vanity-domain": vanity_domain,
            "zscaler-customer-id": customer_id,
            "zscaler-cloud": cloud,
        }

        r = run(["gcloud", "projects", "describe", project, "--format", "value(projectNumber)"])
        project_number = r.stdout.strip()
        sa = f"{project_number}-compute@developer.gserviceaccount.com"

        for name, value in creds.items():
            if not value:
                continue

            r = run(["gcloud", "secrets", "describe", name, "--project", project])
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

            run(["gcloud", "secrets", "add-iam-policy-binding", name,
                 "--member", f"serviceAccount:{sa}",
                 "--role", "roles/secretmanager.secretAccessor",
                 "--project", project, "--quiet"])

        ok(f"Credentials stored in Secret Manager ({len(creds)} secrets)")
        print()

    # ── Deploy ───────────────────────────────────────────────────────

    info("Deploying to Cloud Run...")

    MCP_CONFIG_KEYS = [
        "ZSCALER_MCP_WRITE_ENABLED",
        "ZSCALER_MCP_WRITE_TOOLS",
        "ZSCALER_MCP_SERVICES",
        "ZSCALER_MCP_DISABLED_SERVICES",
        "ZSCALER_MCP_DISABLED_TOOLS",
        "ZSCALER_MCP_SKIP_CONFIRMATIONS",
    ]

    extra_env = []
    for key in MCP_CONFIG_KEYS:
        val = env.get(key, "").strip()
        if val:
            extra_env.append(f"{key}={val}")

    # Default to "zscaler" auth mode — clients authenticate with the same
    # Zscaler OneAPI credentials (client_id:client_secret) via Basic auth.
    # No external IdP, JWT, or API key setup required.
    extra_env.extend([
        "ZSCALER_MCP_AUTH_ENABLED=true",
        "ZSCALER_MCP_AUTH_MODE=zscaler",
    ])

    auth_header_value = "Basic " + base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    base_env = [
        "ZSCALER_MCP_ALLOW_HTTP=true",
        "ZSCALER_MCP_DISABLE_HOST_VALIDATION=true",
    ]

    if use_sm:
        base_env.extend([
            f"ZSCALER_MCP_GCP_SECRET_MANAGER=true",
            f"GCP_PROJECT_ID={project}",
        ])
    else:
        base_env.extend([
            f"ZSCALER_CLIENT_ID={client_id}",
            f"ZSCALER_CLIENT_SECRET={client_secret}",
            f"ZSCALER_VANITY_DOMAIN={vanity_domain}",
            f"ZSCALER_CUSTOMER_ID={customer_id}",
            f"ZSCALER_CLOUD={cloud}",
        ])

    all_env = {}
    for pair in base_env + extra_env:
        k, _, v = pair.partition("=")
        all_env[k] = v

    import tempfile  # noqa: E401

    env_file_path = Path(tempfile.mktemp(suffix=".yaml"))
    try:
        env_file_path.write_text(
            "\n".join(f"{k}: '{v}'" for k, v in all_env.items()) + "\n",
            encoding="utf-8",
        )

        deploy_result = subprocess.run([
            "gcloud", "run", "deploy", "zscaler-mcp-server",
            "--image", image,
            "--region", region,
            "--platform", "managed",
            "--port", "8000",
            "--args=--transport,streamable-http,--host,0.0.0.0,--port,8000",
            "--env-vars-file", str(env_file_path),
            "--memory", "512Mi",
            "--no-cpu-throttling",
            "--allow-unauthenticated",
            "--project", project,
        ], capture_output=True, text=True)
    finally:
        env_file_path.unlink(missing_ok=True)

    if deploy_result.returncode != 0:
        die(f"Deployment failed:\n{deploy_result.stderr}")

    r = run(["gcloud", "run", "services", "describe", "zscaler-mcp-server",
             "--region", region, "--format", "value(status.url)", "--project", project])
    service_url = r.stdout.strip()
    mcp_url = f"{service_url}/mcp"

    ok(f"Deployed: {service_url}")
    print()

    # ── Configure Claude Desktop + Cursor ────────────────────────────

    info("Configuring Claude Desktop and Cursor...")

    system = platform.system()

    if system == "Darwin":
        claude_cfg = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        claude_cfg = Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        claude_cfg = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    if system == "Windows":
        cursor_cfg = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json"
    else:
        cursor_cfg = Path.home() / ".cursor" / "mcp.json"

    claude_args = ["-y", "mcp-remote", mcp_url, "--header",
                   f"Authorization: {auth_header_value}"]
    if system == "Windows":
        claude_args = ["/c", "npx"] + claude_args

    for cfg_path, name, entry in [
        (claude_cfg, "Claude Desktop", {
            "command": "cmd" if system == "Windows" else "npx",
            "args": claude_args,
        }),
        (cursor_cfg, "Cursor", {
            "url": mcp_url,
            "headers": {"Authorization": auth_header_value},
        }),
    ]:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        config = {}
        if cfg_path.is_file():
            try:
                config = json.loads(cfg_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                config = {}

        config.setdefault("mcpServers", {})
        config["mcpServers"]["zscaler-mcp-server"] = entry

        try:
            cfg_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            ok(f"  {name}: {cfg_path}")
        except OSError as exc:
            warn(f"  Could not write {name} config: {exc}")

    print()

    # ── Done ─────────────────────────────────────────────────────────

    print("=" * 64)
    print(f"  {G}Deployment complete{N}")
    print("=" * 64)
    print()
    print(f"  MCP Endpoint:    {mcp_url}")
    print(f"  Auth Mode:       zscaler (Zscaler OneAPI credentials)")
    print(f"  Secret Manager:  {'Yes' if use_sm else 'No'}")
    print()
    print("  Next steps:")
    print("    1. Restart Claude Desktop / Cursor")
    print("    2. Ask: \"List all ZPA application segments\"")
    print()
    print(f"  Logs:    gcloud run services logs read zscaler-mcp-server --region {region}")
    print(f"  Delete:  python {Path(__file__).name} --teardown")
    print()


if __name__ == "__main__":
    main()
