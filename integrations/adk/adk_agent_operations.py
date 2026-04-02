#!/usr/bin/env python3
"""
Zscaler MCP Agent — ADK Operations Script

Runs or deploys the Zscaler MCP ADK agent. Supports local development,
Cloud Run deployment, Vertex AI Agent Engine deployment, and Agentspace
registration.

Usage:
    python adk_agent_operations.py local_run
    python adk_agent_operations.py cloudrun_deploy
    python adk_agent_operations.py agent_engine_deploy
    python adk_agent_operations.py agentspace_register
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).parent / "zscaler_agent"
ENV_FILE = AGENT_DIR / ".env"
ENV_TEMPLATE = AGENT_DIR / "env.properties"
ENV_BACKUP = ENV_FILE.with_suffix(".env.bak")
INVALID_VALUE = "NOT_SET"

REQUIRED_VARS: dict[str, list[str]] = {
    "local_run": [
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_API_KEY",
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
    ],
    "cloudrun_deploy": [
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
        "PROJECT_ID",
        "REGION",
    ],
    "agent_engine_deploy": [
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
        "PROJECT_ID",
        "REGION",
        "AGENT_ENGINE_STAGING_BUCKET",
    ],
    "agentspace_register": [
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_MODEL",
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CUSTOMER_ID",
        "PROJECT_ID",
        "REGION",
        "PROJECT_NUMBER",
        "AGENT_LOCATION",
        "REASONING_ENGINE_NUMBER",
        "AGENT_SPACE_APP_NAME",
    ],
}


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file and return key-value pairs (skips comments and blanks)."""
    env: dict[str, str] = {}
    if not path.exists():
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


def export_env(env: dict[str, str]) -> None:
    """Export variables into the current process environment."""
    for key, value in env.items():
        os.environ[key] = value


def validate_vars(mode: str, env: dict[str, str]) -> bool:
    """Validate that all required vars for the given mode are set and non-empty."""
    required = REQUIRED_VARS[mode]
    all_valid = True
    log.info("Validating required environment variables for '%s' mode", mode)
    for var in required:
        value = env.get(var, "")
        if not value:
            log.error("Required variable '%s' is missing or empty.", var)
            all_valid = False
        elif value == INVALID_VALUE:
            log.error("Required variable '%s' has invalid value: '%s'.", var, INVALID_VALUE)
            all_valid = False
        else:
            log.info("Variable '%s' is set and valid.", var)
    if not all_valid:
        log.error("Validation FAILED. Please check '%s'.", ENV_FILE)
    else:
        log.info("All required environment variables are VALID.")
    return all_valid


SECURITY_VARS = [
    "ZSCALER_MCP_AUTH_ENABLED",
    "ZSCALER_MCP_ALLOW_HTTP",
    "ZSCALER_MCP_ALLOWED_HOSTS",
    "ZSCALER_MCP_ALLOWED_SOURCE_IPS",
    "ZSCALER_MCP_TLS_CERTFILE",
    "ZSCALER_MCP_TLS_KEYFILE",
    "ZSCALER_MCP_DISABLE_HOST_VALIDATION",
    "ZSCALER_MCP_SKIP_CONFIRMATIONS",
    "ZSCALER_MCP_CONFIRMATION_TTL",
]


def warn_security_posture(env: dict[str, str], mode: str) -> None:
    """Log warnings about MCP server security enforcement defaults."""
    if mode == "local_run":
        log.info(
            "Local mode uses stdio transport — auth, TLS, and host validation "
            "are not applicable."
        )
        return

    log.info("--- MCP Server Security Posture ---")
    log.info(
        "The MCP server enforces authentication, HTTPS, and host validation "
        "by default. For Cloud Run / Agent Engine deployments, review these settings:"
    )
    for var in SECURITY_VARS:
        val = env.get(var, "")
        if val:
            log.info("  %s = %s", var, val)
        else:
            log.info("  %s = (not set, using server default)", var)

    if not env.get("ZSCALER_MCP_AUTH_ENABLED"):
        log.warning(
            "ZSCALER_MCP_AUTH_ENABLED is not set. The MCP server enables "
            "authentication by default for HTTP transports. Set to 'false' "
            "to disable if authentication is handled by Cloud Run / IAP."
        )
    if not env.get("ZSCALER_MCP_ALLOWED_HOSTS"):
        log.warning(
            "ZSCALER_MCP_ALLOWED_HOSTS is not set. The MCP server validates "
            "Host headers by default. Set this to your Cloud Run service URL "
            "or set ZSCALER_MCP_DISABLE_HOST_VALIDATION=true."
        )
    if not env.get("ZSCALER_MCP_ALLOW_HTTP") and not env.get("ZSCALER_MCP_TLS_CERTFILE"):
        log.warning(
            "Neither ZSCALER_MCP_ALLOW_HTTP nor ZSCALER_MCP_TLS_CERTFILE is set. "
            "The MCP server requires HTTPS by default. For Cloud Run (where TLS "
            "is terminated by the load balancer), set ZSCALER_MCP_ALLOW_HTTP=true."
        )
    log.info("--- End Security Posture ---")


def run_cmd(args: list[str], check: bool = True) -> int:
    """Run a subprocess command, streaming output to the terminal."""
    log.info("Running: %s", " ".join(args))
    result = subprocess.run(args, check=False)
    if check and result.returncode != 0:
        log.error("Command failed with exit code %d", result.returncode)
        sys.exit(result.returncode)
    return result.returncode


def prepare_deploy_env() -> None:
    """Backup .env and modify it for Vertex AI deployment (remove API key, enable Vertex)."""
    log.info("Backing up '%s' to '%s'", ENV_FILE, ENV_BACKUP)
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
    log.info("Modified '%s': removed GOOGLE_API_KEY, set GOOGLE_GENAI_USE_VERTEXAI=True", ENV_FILE)


def restore_env() -> None:
    """Restore .env from backup if it exists."""
    if ENV_BACKUP.exists():
        log.info("Restoring '%s' from backup.", ENV_FILE)
        shutil.move(str(ENV_BACKUP), str(ENV_FILE))


def ensure_env_file() -> None:
    """If .env doesn't exist, copy from env.properties template."""
    if ENV_FILE.exists():
        return
    if not ENV_TEMPLATE.exists():
        log.error("Template '%s' not found. Cannot create '%s'.", ENV_TEMPLATE, ENV_FILE)
        sys.exit(1)
    log.info("Copying template '%s' to '%s'.", ENV_TEMPLATE, ENV_FILE)
    shutil.copy2(ENV_TEMPLATE, ENV_FILE)
    log.info("Please update the variables in '%s' before running an operation.", ENV_FILE)
    sys.exit(0)


def op_local_run(env: dict[str, str]) -> None:
    """Run the agent locally with `adk web`."""
    if not validate_vars("local_run", env):
        sys.exit(1)
    warn_security_posture(env, "local_run")
    export_env(env)
    log.info("Running ADK Agent for local development...")
    run_cmd(["adk", "web"])
    log.info("'adk web' completed successfully.")


def op_cloudrun_deploy(env: dict[str, str]) -> None:
    """Deploy the agent to Cloud Run."""
    if not validate_vars("cloudrun_deploy", env):
        sys.exit(1)
    warn_security_posture(env, "cloudrun_deploy")
    export_env(env)

    prepare_deploy_env()
    try:
        log.info("Deploying ADK Agent to Cloud Run...")
        run_cmd([
            "adk", "deploy", "cloud_run",
            f"--project={env['PROJECT_ID']}",
            f"--region={env['REGION']}",
            "--service_name=zscaler-agent-service",
            "--with_ui",
            str(AGENT_DIR),
        ])
        log.info("Cloud Run deployment completed successfully.")
    finally:
        restore_env()


def op_agent_engine_deploy(env: dict[str, str]) -> None:
    """Deploy the agent to Vertex AI Agent Engine."""
    if not validate_vars("agent_engine_deploy", env):
        sys.exit(1)
    warn_security_posture(env, "agent_engine_deploy")
    export_env(env)

    prepare_deploy_env()
    try:
        log.info("Deploying ADK Agent to Vertex AI Agent Engine...")
        run_cmd([
            "adk", "deploy", "agent_engine",
            f"--project={env['PROJECT_ID']}",
            f"--region={env['REGION']}",
            f"--staging_bucket={env['AGENT_ENGINE_STAGING_BUCKET']}",
            "--display_name=zscaler_agent",
            str(AGENT_DIR),
        ])
        log.info("Agent Engine deployment completed successfully.")
    finally:
        restore_env()


def op_agentspace_register(env: dict[str, str]) -> None:
    """Register the deployed agent with Google Agentspace."""
    if not validate_vars("agentspace_register", env):
        sys.exit(1)
    warn_security_posture(env, "agentspace_register")
    export_env(env)

    project_id = env["PROJECT_ID"]
    project_number = env["PROJECT_NUMBER"]
    region = env["REGION"]
    agent_location = env["AGENT_LOCATION"]
    reasoning_engine_number = env["REASONING_ENGINE_NUMBER"]
    agent_space_app_name = env["AGENT_SPACE_APP_NAME"]

    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
        f"/locations/{agent_location}/collections/default_collection"
        f"/engines/{agent_space_app_name}/assistants/default_assistant/agents"
    )

    payload = {
        "displayName": "Zscaler Zero Trust Agent",
        "description": "Manage and query the Zscaler Zero Trust Exchange via AI",
        "adk_agent_definition": {
            "tool_settings": {
                "tool_description": "Zscaler Zero Trust Exchange tools (ZPA, ZIA, ZDX, ZCC, EASM, ZIdentity, ZTW, Z-Insights, ZMS)",
            },
            "provisioned_reasoning_engine": {
                "reasoning_engine": (
                    f"projects/{project_number}/locations/{region}"
                    f"/reasoningEngines/{reasoning_engine_number}"
                ),
            },
        },
    }

    log.info("Registering agent with Agentspace: %s", url)
    log.info("Request body:\n%s", json.dumps(payload, indent=2))

    token_result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
        check=True,
    )
    access_token = token_result.stdout.strip()

    run_cmd([
        "curl", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", f"X-Goog-User-Project: {project_id}",
        "-d", json.dumps(payload),
        url,
    ])
    log.info("Agentspace registration completed.")


OPERATIONS = {
    "local_run": op_local_run,
    "cloudrun_deploy": op_cloudrun_deploy,
    "agent_engine_deploy": op_agent_engine_deploy,
    "agentspace_register": op_agentspace_register,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zscaler MCP Agent — ADK Operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Operation modes:\n"
            "  local_run            Run the agent locally with 'adk web'\n"
            "  cloudrun_deploy      Deploy to Google Cloud Run\n"
            "  agent_engine_deploy  Deploy to Vertex AI Agent Engine\n"
            "  agentspace_register  Register with Google Agentspace\n"
        ),
    )
    parser.add_argument(
        "operation",
        nargs="?",
        choices=OPERATIONS.keys(),
        help="Operation mode to execute",
    )
    args = parser.parse_args()

    ensure_env_file()

    if args.operation is None:
        parser.print_help()
        sys.exit(1)

    env = load_env_file(ENV_FILE)
    log.info("Loaded environment from '%s'", ENV_FILE)

    operation_fn = OPERATIONS[args.operation]
    log.info("Operation mode: '%s'", args.operation)
    operation_fn(env)
    log.info("Operation '%s' complete.", args.operation)


if __name__ == "__main__":
    main()
