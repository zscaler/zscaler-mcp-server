#!/usr/bin/env python3
"""
Zscaler MCP Agent — ADK Operations (Interactive)

Fully interactive deployment script for the Zscaler MCP ADK agent.
Supports four deployment targets:
  1. Local (adk web)           — run the agent locally for development
  2. Cloud Run                 — deploy to Google Cloud Run with web UI
  3. Vertex AI Agent Engine    — deploy to fully managed Agent Engine
  4. Agentspace                — register with Google Agentspace catalog

Management operations:
  status    Show deployment status
  logs      Stream deployment logs
  destroy   Tear down deployed resources

Usage:
  python adk_agent_operations.py deploy     # interactive guided deploy
  python adk_agent_operations.py status     # show deployment status
  python adk_agent_operations.py logs       # stream logs
  python adk_agent_operations.py destroy    # tear down resources
"""

from __future__ import annotations

import argparse
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
AGENT_DIR = SCRIPT_DIR / "zscaler_agent"
ENV_FILE = AGENT_DIR / ".env"
ENV_TEMPLATE = AGENT_DIR / "env.properties"
ENV_BACKUP = ENV_FILE.with_suffix(".env.bak")
STATE_FILE = SCRIPT_DIR / ".adk-deploy-state.json"
INVALID_VALUE = "NOT_SET"
SERVICE_NAME = "zscaler-agent-service"
SYSTEM = platform.system()

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


def elapsed_str(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


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
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) > 1:
            value = value[1:-1]
        env[key] = value
    return env


def resolve(env: dict[str, str], key: str) -> str:
    return env.get(key, os.environ.get(key, ""))


# ── Interactive prompt helpers ────────────────────────────────────────────


def _prompt(label: str, *, default: str = "", secret: bool = False) -> str:
    if default:
        display = f"  {label} [{default}]: "
    else:
        display = f"  {label}: "
    while True:
        try:
            if secret:
                import getpass
                val = getpass.getpass(display)
            else:
                val = input(display)
        except (EOFError, KeyboardInterrupt):
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print(f"\n{YELLOW}[INTERRUPTED]{NC} Operation cancelled.")
            os._exit(130)
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
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print(f"\n{YELLOW}[INTERRUPTED]{NC} Operation cancelled.")
            os._exit(130)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            key = options[int(raw) - 1][0]
            return key
        error(f"  Invalid choice: {raw}")


def _prompt_yes_no(question: str, *, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        raw = input(f"  {question} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        print(f"\n{YELLOW}[INTERRUPTED]{NC} Operation cancelled.")
        os._exit(130)
    if not raw:
        return default
    return raw in ("y", "yes")


# ── Env validation ────────────────────────────────────────────────────────

REQUIRED_VARS: dict[str, list[str]] = {
    "local_run": [
        "GOOGLE_API_KEY",
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
    ],
    "cloudrun_deploy": [
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
    ],
    "agent_engine_deploy": [
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
    ],
    "agentspace_register": [
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
        "PROJECT_NUMBER",
        "REASONING_ENGINE_NUMBER",
        "AGENT_SPACE_APP_NAME",
    ],
}


def validate_env(mode: str, env: dict[str, str]) -> bool:
    required = REQUIRED_VARS.get(mode, [])
    missing: list[str] = []
    for var in required:
        value = env.get(var, "")
        if not value or value == INVALID_VALUE:
            missing.append(var)
    if missing:
        error("Missing required variables:")
        for var in missing:
            print(f"    - {var}")
        print()
        error(f"Please update '{ENV_FILE}' and try again.")
        return False
    ok(f"All required variables validated ({len(required)} checked)")
    return True


# ── .env modification for Vertex AI deployment ───────────────────────────


def prepare_deploy_env() -> None:
    info("Backing up .env for Vertex AI deployment")
    shutil.copy2(ENV_FILE, ENV_BACKUP)

    lines = ENV_FILE.read_text().splitlines()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("GOOGLE_API_KEY="):
            continue
        if stripped.startswith("GOOGLE_GENAI_USE_VERTEXAI="):
            new_lines.append("GOOGLE_GENAI_USE_VERTEXAI=True")
        else:
            new_lines.append(line)
    ENV_FILE.write_text("\n".join(new_lines) + "\n")
    ok("Removed GOOGLE_API_KEY, set GOOGLE_GENAI_USE_VERTEXAI=True")


def restore_env() -> None:
    if ENV_BACKUP.exists():
        info("Restoring .env from backup")
        shutil.move(str(ENV_BACKUP), str(ENV_FILE))
        ok(".env restored")


def export_env(env: dict[str, str]) -> None:
    for key, value in env.items():
        os.environ[key] = value


def ensure_env_file() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_TEMPLATE.exists():
        die(f"Template '{ENV_TEMPLATE}' not found. Cannot create .env.")
    info(f"Creating .env from template '{ENV_TEMPLATE.name}'")
    shutil.copy2(ENV_TEMPLATE, ENV_FILE)
    ok(f"Created '{ENV_FILE}'. Please update the variables before running.")
    sys.exit(0)


# ════════════════════════════════════════════════════════════════════════
#  Deploy
# ════════════════════════════════════════════════════════════════════════


def op_deploy(args: argparse.Namespace) -> None:
    """Interactive guided deployment."""

    print(ZSCALER_LOGO)
    print("=" * 72)
    print(f"  {BOLD}Zscaler MCP Agent — ADK Deployment{NC}")
    print("=" * 72)
    print()

    # Prerequisites
    info("Step 1: Checking prerequisites")
    if not shutil.which("gcloud"):
        die("gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install")
    if not shutil.which("adk"):
        die("ADK CLI not found. Install: pip install google-adk")

    r = run_gcloud(["config", "get-value", "project"], capture=True, check=False)
    current_project = r.stdout.strip() if r.returncode == 0 else ""
    if current_project:
        ok(f"gcloud CLI: project '{current_project}'")
    else:
        warn("No default gcloud project set")
    ok("ADK CLI found")
    print()

    # Deployment target
    deploy_target = _prompt_choice(
        "Select deployment target:",
        [
            ("local_run", "Local development  — run with 'adk web' on localhost"),
            ("cloudrun_deploy", "Google Cloud Run   — deploy as managed container with web UI"),
            ("agent_engine_deploy", "Vertex AI Agent Engine — fully managed agent hosting"),
            ("agentspace_register", "Google Agentspace  — register in enterprise agent catalog"),
        ],
    )
    ok(f"Deployment target: {deploy_target}")
    print()

    # Load env
    info("Step 2: Loading credentials")
    cred_source = _prompt_choice(
        "How would you like to provide credentials?",
        [
            ("env", f"From .env file ({ENV_FILE.relative_to(SCRIPT_DIR)})"),
            ("custom", "From a custom .env file path"),
        ],
    )

    if cred_source == "custom":
        env_path_str = _prompt("Path to .env file")
        env_path = Path(env_path_str).expanduser().resolve()
        if not env_path.is_file():
            die(f".env file not found: {env_path}")
        env = load_env(env_path)
    else:
        if not ENV_FILE.is_file():
            die(f".env not found at {ENV_FILE}. Run the script once to generate from template.")
        env = load_env(ENV_FILE)

    ok(f".env loaded ({len(env)} variables)")
    print()

    # Validate required vars
    info("Step 3: Validating environment")
    if not validate_env(deploy_target, env):
        sys.exit(1)
    print()

    # Target-specific configuration and deployment
    if deploy_target == "local_run":
        _deploy_local(env)
    elif deploy_target == "cloudrun_deploy":
        _deploy_cloudrun(env, current_project)
    elif deploy_target == "agent_engine_deploy":
        _deploy_agent_engine(env, current_project)
    elif deploy_target == "agentspace_register":
        _deploy_agentspace(env)


def _deploy_local(env: dict[str, str]) -> None:
    """Run the agent locally with adk web."""
    print()
    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:      Local (adk web)")
    print(f"    Model:       {env.get('GOOGLE_MODEL', 'gemini-2.5-flash')}")
    print(f"    Zscaler:     {env.get('ZSCALER_VANITY_DOMAIN', 'N/A')}")
    print("    Access:      http://localhost:8000")
    print()

    if not _prompt_yes_no("Start the local agent?"):
        die("Cancelled.")
    print()

    export_env(env)
    info("Starting ADK agent locally...")
    print()
    print(f"  {GREEN}Open your browser at http://localhost:8000{NC}")
    print(f"  {YELLOW}Press Ctrl+C to stop{NC}")
    print()
    run_cmd(["adk", "web", str(AGENT_DIR)])


def _deploy_cloudrun(env: dict[str, str], current_project: str) -> None:
    """Deploy to Cloud Run."""
    info("Cloud Run configuration")
    project = _prompt("GCP Project", default=resolve(env, "PROJECT_ID") or current_project)
    region = _prompt("GCP Region", default=resolve(env, "REGION") or "us-central1")
    service_name = _prompt("Cloud Run service name", default=SERVICE_NAME)
    model = env.get("GOOGLE_MODEL", "gemini-2.5-flash")
    print()

    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          Google Cloud Run")
    print(f"    GCP Project:     {project}")
    print(f"    Region:          {region}")
    print(f"    Service name:    {service_name}")
    print(f"    Model:           {model} (via Vertex AI)")
    print(f"    Zscaler Cloud:   {env.get('ZSCALER_VANITY_DOMAIN', 'N/A')}")
    print("    Build:           From source via Cloud Build")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    t0 = time.time()

    export_env(env)
    prepare_deploy_env()

    try:
        info("Deploying ADK Agent to Cloud Run...")
        print()
        run_cmd([
            "adk", "deploy", "cloud_run",
            f"--project={project}",
            f"--region={region}",
            f"--service_name={service_name}",
            "--with_ui",
            str(AGENT_DIR),
        ])
    finally:
        restore_env()

    elapsed = time.time() - t0

    # Save state
    _save_state({
        "deployment_type": "cloudrun",
        "project": project,
        "region": region,
        "service_name": service_name,
    })

    # Retrieve service URL
    r = run_gcloud([
        "run", "services", "describe", service_name,
        "--region", region, "--project", project,
        "--format", "value(status.url)",
    ], capture=True, check=False)
    service_url = r.stdout.strip() if r.returncode == 0 else "(could not retrieve)"

    print()
    print("=" * 72)
    print(f"  {GREEN}{BOLD}ADK Agent — Cloud Run Deployment Complete{NC}")
    print("=" * 72)
    print()
    print(f"  Service URL:   {service_url}")
    print(f"  Project:       {project}")
    print(f"  Region:        {region}")
    print(f"  Elapsed:       {elapsed_str(elapsed)}")
    print()
    print(f"  {BOLD}Access:{NC}")
    print(f"    Open in browser:    {service_url}")
    print(f"    Via gcloud proxy:   gcloud run services proxy {service_name} --region {region}")
    print()
    print(f"  {BOLD}Management:{NC}")
    print(f"    Status:   python {Path(__file__).name} status")
    print(f"    Logs:     python {Path(__file__).name} logs")
    print(f"    Destroy:  python {Path(__file__).name} destroy")
    print()


def _deploy_agent_engine(env: dict[str, str], current_project: str) -> None:
    """Deploy to Vertex AI Agent Engine."""
    info("Agent Engine configuration")
    project = _prompt("GCP Project", default=resolve(env, "PROJECT_ID") or current_project)
    region = _prompt("GCP Region", default=resolve(env, "REGION") or "us-central1")
    staging_bucket = _prompt(
        "Staging bucket (gs://...)",
        default=resolve(env, "AGENT_ENGINE_STAGING_BUCKET"),
    )
    model = env.get("GOOGLE_MODEL", "gemini-2.5-flash")
    print()

    print(f"  {BOLD}Deployment summary:{NC}")
    print("    Target:          Vertex AI Agent Engine")
    print(f"    GCP Project:     {project}")
    print(f"    Region:          {region}")
    print(f"    Staging bucket:  {staging_bucket}")
    print(f"    Model:           {model} (via Vertex AI)")
    print(f"    Zscaler Cloud:   {env.get('ZSCALER_VANITY_DOMAIN', 'N/A')}")
    print()

    if not _prompt_yes_no("Proceed with deployment?"):
        die("Deployment cancelled.")
    print()

    t0 = time.time()

    export_env(env)
    prepare_deploy_env()

    try:
        info("Deploying ADK Agent to Vertex AI Agent Engine...")
        print()
        run_cmd([
            "adk", "deploy", "agent_engine",
            f"--project={project}",
            f"--region={region}",
            f"--staging_bucket={staging_bucket}",
            "--display_name=zscaler_agent",
            str(AGENT_DIR),
        ])
    finally:
        restore_env()

    elapsed = time.time() - t0

    _save_state({
        "deployment_type": "agent_engine",
        "project": project,
        "region": region,
        "staging_bucket": staging_bucket,
    })

    print()
    print("=" * 72)
    print(f"  {GREEN}{BOLD}ADK Agent — Agent Engine Deployment Complete{NC}")
    print("=" * 72)
    print()
    print(f"  Project:   {project}")
    print(f"  Region:    {region}")
    print(f"  Elapsed:   {elapsed_str(elapsed)}")
    print()
    print(f"  {BOLD}Management:{NC}")
    print(f"    Status:   python {Path(__file__).name} status")
    print(f"    Logs:     python {Path(__file__).name} logs")
    print(f"    Destroy:  python {Path(__file__).name} destroy")
    print()


def _deploy_agentspace(env: dict[str, str]) -> None:
    """Register with Google Agentspace."""
    info("Agentspace configuration")
    project_id = _prompt("GCP Project", default=resolve(env, "PROJECT_ID"))
    project_number = _prompt("GCP Project Number", default=resolve(env, "PROJECT_NUMBER"))
    region = _prompt("Agent Engine Region", default=resolve(env, "REGION") or "us-central1")
    agent_location = _prompt("Agentspace Location", default=resolve(env, "AGENT_LOCATION") or "global")
    reasoning_engine_number = _prompt("Reasoning Engine ID", default=resolve(env, "REASONING_ENGINE_NUMBER"))
    app_name = _prompt("Agentspace App Name", default=resolve(env, "AGENT_SPACE_APP_NAME"))
    print()

    print(f"  {BOLD}Registration summary:{NC}")
    print("    Target:               Google Agentspace")
    print(f"    GCP Project:          {project_id}")
    print(f"    Reasoning Engine:     {reasoning_engine_number}")
    print(f"    Agentspace App:       {app_name}")
    print(f"    Agent Location:       {agent_location}")
    print()

    if not _prompt_yes_no("Proceed with registration?"):
        die("Registration cancelled.")
    print()

    t0 = time.time()

    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
        f"/locations/{agent_location}/collections/default_collection"
        f"/engines/{app_name}/assistants/default_assistant/agents"
    )

    payload = {
        "displayName": "Zscaler Zero Trust Agent",
        "description": "Manage and query the Zscaler Zero Trust Exchange via AI",
        "adk_agent_definition": {
            "tool_settings": {
                "tool_description": (
                    "Zscaler Zero Trust Exchange tools "
                    "(ZPA, ZIA, ZDX, ZCC, EASM, ZIdentity, ZTW, Z-Insights, ZMS)"
                ),
            },
            "provisioned_reasoning_engine": {
                "reasoning_engine": (
                    f"projects/{project_number}/locations/{region}"
                    f"/reasoningEngines/{reasoning_engine_number}"
                ),
            },
        },
    }

    info("Registering agent with Agentspace...")
    r = run_gcloud(["auth", "print-access-token"], capture=True)
    access_token = r.stdout.strip()

    run_cmd([
        "curl", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", f"X-Goog-User-Project: {project_id}",
        "-d", json.dumps(payload),
        url,
    ])

    elapsed = time.time() - t0

    print()
    print("=" * 72)
    print(f"  {GREEN}{BOLD}ADK Agent — Agentspace Registration Complete{NC}")
    print("=" * 72)
    print()
    print(f"  Project:   {project_id}")
    print(f"  App:       {app_name}")
    print(f"  Elapsed:   {elapsed_str(elapsed)}")
    print()


# ════════════════════════════════════════════════════════════════════════
#  Status
# ════════════════════════════════════════════════════════════════════════


def op_status(args: argparse.Namespace) -> None:
    """Show deployment status."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if not deployment_type:
        die("No deployment found. Deploy first with 'deploy' command.")

    project = state.get("project", "")
    region = state.get("region", "")

    print()
    print(f"  {BOLD}ADK Agent — Deployment Status{NC}")
    print()

    if deployment_type == "cloudrun":
        service_name = state.get("service_name", SERVICE_NAME)
        info(f"Cloud Run service: {service_name}")
        run_gcloud([
            "run", "services", "describe", service_name,
            "--region", region, "--project", project, "--format",
            "table(status.url,status.conditions[0].status,metadata.creationTimestamp)",
        ])

    elif deployment_type == "agent_engine":
        info(f"Agent Engine deployment in project '{project}'")
        run_gcloud([
            "ai", "reasoning-engines", "list",
            "--project", project, "--region", region,
        ])

    print()


# ════════════════════════════════════════════════════════════════════════
#  Logs
# ════════════════════════════════════════════════════════════════════════


def op_logs(args: argparse.Namespace) -> None:
    """Stream deployment logs."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if not deployment_type:
        die("No deployment found. Deploy first.")

    project = state.get("project", "")
    region = state.get("region", "")

    if deployment_type == "cloudrun":
        service_name = state.get("service_name", SERVICE_NAME)
        info(f"Streaming logs for Cloud Run service '{service_name}'...")
        run_gcloud([
            "run", "services", "logs", "read", service_name,
            "--region", region, "--project", project, "--limit", "100",
        ])

    elif deployment_type == "agent_engine":
        info("Fetching Agent Engine logs...")
        run_gcloud([
            "logging", "read",
            'resource.type="aiplatform.googleapis.com/ReasoningEngine"',
            "--project", project, "--limit", "50",
            "--format", "value(textPayload)",
        ])

    print()


# ════════════════════════════════════════════════════════════════════════
#  Destroy
# ════════════════════════════════════════════════════════════════════════


def op_destroy(args: argparse.Namespace) -> None:
    """Tear down deployed resources."""
    state = _load_state()
    deployment_type = state.get("deployment_type", "")

    if not deployment_type:
        die("No deployment found. Nothing to destroy.")

    project = state.get("project", "")
    region = state.get("region", "")

    print()
    print("=" * 72)
    print(f"  {RED}DESTROY — Tearing down ADK Agent resources{NC}")
    print("=" * 72)
    print()

    if deployment_type == "cloudrun":
        service_name = state.get("service_name", SERVICE_NAME)
        warn(f"This will delete Cloud Run service: {service_name}")
        print()

        yes = getattr(args, "yes", False)
        if not yes:
            confirm = input(f"  Type '{service_name}' to confirm: ").strip()
            if confirm != service_name:
                die("Destruction cancelled.")

        print()
        t0 = time.time()
        info(f"Deleting Cloud Run service '{service_name}'...")
        run_gcloud([
            "run", "services", "delete", service_name,
            "--region", region, "--project", project, "--quiet",
        ])
        elapsed = time.time() - t0
        ok(f"Cloud Run service deleted ({elapsed_str(elapsed)})")

    elif deployment_type == "agent_engine":
        warn("Agent Engine deployments must be deleted via the Google Cloud Console")
        warn("or using 'gcloud ai reasoning-engines delete <ENGINE_ID>'.")
        print()
        info("Listing current deployments:")
        run_gcloud([
            "ai", "reasoning-engines", "list",
            "--project", project, "--region", region,
        ])
        print()
        info("Delete the engine manually using the ID above.")

    _clear_state()
    print()
    ok("Destroy complete.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════


OPERATIONS = {
    "deploy": op_deploy,
    "status": op_status,
    "logs": op_logs,
    "destroy": op_destroy,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Zscaler MCP Agent — ADK Operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Operations:\n"
            "  deploy     Interactive guided deployment (local, Cloud Run, Agent Engine, Agentspace)\n"
            "  status     Show deployment status\n"
            "  logs       Stream deployment logs\n"
            "  destroy    Tear down deployed resources\n"
        ),
    )
    sub = p.add_subparsers(dest="operation")

    sub.add_parser("deploy", help="Interactive guided deployment")
    sub.add_parser("status", help="Show deployment status")
    sub.add_parser("logs", help="Stream deployment logs")

    ds = sub.add_parser("destroy", help="Tear down deployed resources")
    ds.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.operation:
        print(ZSCALER_LOGO)
        parser.print_help()
        sys.exit(1)

    ensure_env_file()

    try:
        OPERATIONS[args.operation](args)
    except KeyboardInterrupt:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        print(f"\n{YELLOW}[INTERRUPTED]{NC} Operation cancelled.")
        os._exit(130)


if __name__ == "__main__":
    main()
