#!/usr/bin/env python3
"""
Azure AI Foundry Agent — Zscaler MCP Integration

Creates an Azure AI Foundry agent that uses the deployed Zscaler MCP Server
as a tool. The agent is hosted by Azure and uses GPT-4o to process requests.

This module provides:
  - Agent creation with MCPTool pointing to your deployed MCP server
  - Interactive chat session with tool approval handling
  - Agent lifecycle management (create, status, chat, destroy)
  - Animated spinner with live elapsed-time counter during requests
  - Per-response token usage tracking (input/output/total)
  - End-of-session summary (duration, cumulative tokens)
  - Multi-turn response chaining for conversation continuity

Authentication:
  MCP server auth uses custom headers (X-Zscaler-Client-ID /
  X-Zscaler-Client-Secret or X-MCP-API-Key) via MCPTool.headers.
  The Authorization header and project_connection_id are NOT used
  due to Foundry restrictions (sensitive header blocking, URI parsing bug).

Prerequisites:
  - Azure AI Foundry project (https://ai.azure.com)
  - Azure OpenAI deployment (GPT-4o or GPT-4)
  - Deployed Zscaler MCP Server (Container Apps or VM)
  - Python packages: azure-ai-projects, azure-identity
  - Azure CLI authenticated: az login

Usage:
  python azure_mcp_operations.py agent_create              # create agent
  python azure_mcp_operations.py agent_chat                # interactive chat
  python azure_mcp_operations.py agent_chat -m "query"     # chat with initial message
  python azure_mcp_operations.py agent_status              # show agent info
  python azure_mcp_operations.py agent_destroy             # delete agent (with prompt)
  python azure_mcp_operations.py agent_destroy -y          # delete agent (no prompt)
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────

AGENT_NAME = "zscaler-mcp-agent"
DEFAULT_MODEL = "gpt-4o"

AGENT_INSTRUCTIONS = """You are a Zscaler security assistant powered by the Zscaler MCP Server.

You have access to 300+ tools for managing the Zscaler Zero Trust Exchange:
- ZPA (Zscaler Private Access): Application segments, access policies, connectors
- ZIA (Zscaler Internet Access): URL filtering, firewall rules, locations
- ZDX (Zscaler Digital Experience): User experience monitoring, device health
- ZCC (Zscaler Client Connector): Device management, enrollment
- EASM (External Attack Surface Management): Asset discovery, risk assessment
- ZTW (Zscaler Workload Segmentation): Workload protection policies

Guidelines:
1. Always use list/get tools first to understand current state before making changes
2. For ZIA changes: remind the user that zia_activate_configuration() is required after modifications
3. Be precise with IDs — always treat them as strings
4. For destructive operations (delete), the MCP server will return an HMAC confirmation token
5. When you receive a confirmation token, explain what will be deleted and ask the user to confirm
6. Only proceed with deletion after user explicitly confirms

When tools require approval, explain what the tool will do and wait for user approval.
"""

# ── ANSI colours ──────────────────────────────────────────────────────────

COLOURS = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
RED = "\033[0;31m" if COLOURS else ""
GREEN = "\033[0;32m" if COLOURS else ""
YELLOW = "\033[1;33m" if COLOURS else ""
BLUE = "\033[0;34m" if COLOURS else ""
BOLD = "\033[1m" if COLOURS else ""
SKY_BLUE = "\033[34;01m" if COLOURS else ""
CYAN = "\033[0;36m" if COLOURS else ""
DIM = "\033[2m" if COLOURS else ""
NC = "\033[0m" if COLOURS else ""

ZSCALER_LOGO = f"""{SKY_BLUE}
  ______              _
 |___  /             | |
    / / ___  ___ __ _| | ___ _ __
   / / / __|/ __/ _` | |/ _ \\ '__|
  / /__\\__ \\ (_| (_| | |  __/ |
 /_____|___/\\___\\__,_|_|\\___|_|
{NC}"""


class Spinner:
    """Animated spinner for long-running operations."""

    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Thinking") -> None:
        self._message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time = 0.0

    def start(self) -> "Spinner":
        self._start_time = time.time()
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def _spin(self) -> None:
        idx = 0
        while not self._stop.is_set():
            elapsed = time.time() - self._start_time
            frame = self._FRAMES[idx % len(self._FRAMES)]
            sys.stdout.write(
                f"\r{CYAN}{frame}{NC} {self._message}"
                f" {DIM}({elapsed:.0f}s){NC}   "
            )
            sys.stdout.flush()
            idx += 1
            self._stop.wait(0.08)

    def stop(self) -> float:
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()
        return time.time() - self._start_time


def _format_stats(elapsed: float, response: object) -> str:
    """Format timing and token usage stats."""
    parts = [f"{elapsed:.1f}s"]
    usage = getattr(response, "usage", None)
    if usage:
        input_t = getattr(usage, "input_tokens", 0)
        output_t = getattr(usage, "output_tokens", 0)
        total = getattr(usage, "total_tokens", 0) or (input_t + output_t)
        if total:
            parts.append(f"{total:,} tokens")
            if input_t or output_t:
                parts.append(f"in:{input_t:,} out:{output_t:,}")
    return f"{DIM}[{' | '.join(parts)}]{NC}"


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{NC}  {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{NC}    {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def die(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}", file=sys.stderr)
    sys.exit(1)


# ── SDK Import Check ──────────────────────────────────────────────────────


def check_sdk_installed() -> bool:
    """Check if required Azure AI SDKs are installed."""
    try:
        import azure.ai.projects  # noqa: F401
        import azure.identity  # noqa: F401

        return True
    except ImportError:
        return False


def install_sdk_prompt() -> None:
    """Prompt user to install required SDKs."""
    warn("Required Azure AI SDKs not found.")
    print()
    print("Install with:")
    print(f"  {BOLD}pip install azure-ai-projects azure-identity{NC}")
    print()
    print("Or add to requirements.txt:")
    print("  azure-ai-projects>=1.0.0")
    print("  azure-identity>=1.15.0")
    print()


# ── Agent Operations ──────────────────────────────────────────────────────


def _build_mcp_headers(
    auth_mode: str,
    client_id: str | None = None,
    client_secret: str | None = None,
    api_key_value: str | None = None,
) -> dict[str, str]:
    """
    Build MCP server authentication headers based on the auth mode.

    Azure Foundry blocks ``Authorization`` and other sensitive headers
    in MCPTool.headers (returns ``invalid_payload``).  Foundry's
    ``project_connection_id`` / CustomKeys alternative triggers an
    ``Invalid URI`` parsing bug in the service backend.

    The workaround is to use the MCP server's custom header authentication:
    ``X-Zscaler-Client-ID`` + ``X-Zscaler-Client-Secret`` for Zscaler auth,
    or ``X-MCP-API-Key`` for API-key auth. These are non-sensitive custom
    headers that Foundry passes through without issues.

    Args:
        auth_mode: MCP server auth mode (zscaler, api-key, jwt, none)
        client_id: Zscaler client ID (for zscaler auth)
        client_secret: Zscaler client secret (for zscaler auth)
        api_key_value: API key (for api-key auth)

    Returns:
        dict of headers to pass to MCPTool
    """
    headers: dict[str, str] = {}

    if auth_mode == "zscaler":
        if not client_id or not client_secret:
            die(
                "Zscaler auth requires ZSCALER_CLIENT_ID and "
                "ZSCALER_CLIENT_SECRET."
            )
        headers["X-Zscaler-Client-ID"] = client_id
        headers["X-Zscaler-Client-Secret"] = client_secret

    elif auth_mode == "api-key":
        if not api_key_value:
            die("API-key auth requires ZSCALER_MCP_AUTH_API_KEY.")
        headers["X-MCP-API-Key"] = api_key_value

    return headers


def create_agent(
    project_endpoint: str,
    mcp_server_url: str,
    model: str = DEFAULT_MODEL,
    require_approval: str = "always",
    mcp_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a Foundry agent with MCPTool pointing to the Zscaler MCP Server.

    Args:
        project_endpoint: Azure AI Foundry project endpoint
            Format: https://{resource}.services.ai.azure.com/api/projects/{project}
        mcp_server_url: URL of the deployed MCP server
        model: Azure OpenAI model deployment name (default: gpt-4o)
        require_approval: Tool approval mode ("always", "never", or tool list)
        mcp_headers: Custom headers for MCP server authentication
            (X-Zscaler-Client-ID, X-Zscaler-Client-Secret, etc.)

    Returns:
        dict with agent details (id, name, version)
    """
    if not check_sdk_installed():
        install_sdk_prompt()
        die("Cannot create agent without Azure AI SDKs.")

    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import MCPTool, PromptAgentDefinition
    from azure.identity import DefaultAzureCredential

    info(f"Connecting to Foundry project: {project_endpoint}")
    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    # Build MCP tool with custom auth headers
    mcp_tool = MCPTool(
        server_label="zscaler",
        server_url=mcp_server_url,
        require_approval=require_approval,
    )
    if mcp_headers:
        mcp_tool.headers = mcp_headers

    info(f"Creating agent '{AGENT_NAME}' with model '{model}'")
    info(f"MCP Server URL: {mcp_server_url}")
    if mcp_headers:
        header_names = ", ".join(mcp_headers.keys())
        info(f"Auth headers: {header_names}")

    try:
        agent = project.agents.create_version(
            agent_name=AGENT_NAME,
            definition=PromptAgentDefinition(
                model=model,
                instructions=AGENT_INSTRUCTIONS,
                tools=[mcp_tool],
            ),
        )
    except Exception as exc:
        _handle_api_error(exc)
        die("Agent creation failed. Resolve the issue above and try again.")

    ok(f"Agent created: {agent.name} (version {agent.version})")
    return {
        "id": agent.id,
        "name": agent.name,
        "version": agent.version,
        "model": model,
        "mcp_url": mcp_server_url,
    }


def get_agent_status(project_endpoint: str) -> dict[str, Any] | None:
    """Get status of the Zscaler MCP agent."""
    if not check_sdk_installed():
        install_sdk_prompt()
        die("Cannot check agent status without Azure AI SDKs.")

    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    try:
        # List versions of our agent
        versions = list(project.agents.list_versions(agent_name=AGENT_NAME))
        if not versions:
            return None

        latest = versions[-1]
        return {
            "id": latest.id,
            "name": latest.name,
            "version": latest.version,
            "status": "active",
        }
    except Exception as e:
        if "not found" in str(e).lower():
            return None
        raise


def delete_agent(project_endpoint: str, version: str | None = None) -> bool:
    """Delete the Zscaler MCP agent."""
    if not check_sdk_installed():
        install_sdk_prompt()
        die("Cannot delete agent without Azure AI SDKs.")

    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    try:
        if version:
            project.agents.delete_version(agent_name=AGENT_NAME, agent_version=version)
            ok(f"Deleted agent version: {AGENT_NAME} v{version}")
        else:
            # Delete all versions
            versions = list(project.agents.list_versions(agent_name=AGENT_NAME))
            for v in versions:
                project.agents.delete_version(
                    agent_name=AGENT_NAME, agent_version=v.version
                )
                info(f"Deleted version {v.version}")
            ok(f"Deleted all versions of agent: {AGENT_NAME}")
        return True
    except Exception as e:
        if "not found" in str(e).lower():
            warn(f"Agent '{AGENT_NAME}' not found.")
            return False
        raise


def _handle_api_error(exc: Exception) -> None:
    """
    Translate common Azure OpenAI / Foundry API errors into actionable
    user-facing messages instead of raw tracebacks.
    """
    msg = str(exc).lower()
    error_body = getattr(exc, "body", None) or {}
    code = ""
    if isinstance(error_body, dict):
        inner = error_body.get("error", error_body)
        code = (inner.get("code") or "").lower() if isinstance(inner, dict) else ""

    if "deploymentnotfound" in code or "deployment" in msg and "not exist" in msg:
        print()
        warn("Model deployment not found in your Foundry project.")
        print()
        print(f"  {BOLD}How to fix:{NC}")
        print("    1. Go to https://ai.azure.com → open your project")
        print("    2. Click 'Models' in the left sidebar")
        print("    3. Click '+ Deploy model' → 'Deploy base model'")
        print("    4. Select 'gpt-4o' (or the model in your .env)")
        print("    5. Click 'Deploy' and wait for it to be ready")
        print("    6. Run 'agent_chat' again")
        print()
        print(f"  {DIM}If you just deployed the model, wait 2-3 minutes for")
        print(f"  it to propagate and try again.{NC}")

    elif "authenticationerror" in type(exc).__name__.lower() or "401" in msg:
        print()
        warn("Authentication failed.")
        print()
        print(f"  {BOLD}How to fix:{NC}")
        print("    1. Run 'az login' to refresh your Azure credentials")
        print("    2. Verify your subscription has access to the Foundry project")
        print("    3. Try again")

    elif "ratelimit" in type(exc).__name__.lower() or "429" in msg:
        print()
        warn("Rate limit exceeded.")
        print()
        print(f"  {BOLD}How to fix:{NC}")
        print("    Wait a moment and try again. If this persists, check your")
        print("    Azure OpenAI quota in the Azure portal.")

    elif "notfounderror" in type(exc).__name__.lower() or "404" in msg:
        print()
        warn("Resource not found (404).")
        print()
        print(f"  {BOLD}Possible causes:{NC}")
        print("    - Model deployment doesn't exist (deploy it in the Foundry portal)")
        print("    - Project endpoint is incorrect (check AZURE_AI_PROJECT_ENDPOINT)")
        print("    - Agent was deleted (re-run 'agent_create')")

    elif "connection" in msg or "timeout" in msg:
        print()
        warn("Connection error.")
        print()
        print(f"  {BOLD}How to fix:{NC}")
        print("    - Check your internet connection")
        print("    - Verify the MCP server is running: python azure_mcp_operations.py status")
        print("    - Try again in a moment")

    else:
        print()
        warn(f"Unexpected error: {type(exc).__name__}")
        print(f"  {exc}")

    print()


def chat_session(
    project_endpoint: str,
    initial_message: str | None = None,
) -> None:
    """
    Start an interactive chat session with the Zscaler MCP agent.

    Handles MCP tool approval requests interactively.
    """
    if not check_sdk_installed():
        install_sdk_prompt()
        die("Cannot start chat without Azure AI SDKs.")

    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )
    openai = project.get_openai_client()

    # Check agent exists
    status = get_agent_status(project_endpoint)
    if not status:
        die(f"Agent '{AGENT_NAME}' not found. Run 'agent_create' first.")

    print(ZSCALER_LOGO)
    print("=" * 60)
    print(f"  {BOLD}Zscaler MCP Agent Chat{NC}")
    print(f"  Agent: {status['name']} (v{status['version']})")
    print(f"  Type {DIM}'help'{NC} for available commands.")
    print("=" * 60)
    print()

    # Track last response ID for proper chaining across the conversation.
    # Foundry requires approval followups to be chained via previous_response_id,
    # and subsequent user messages must reference the last response in the chain
    # to avoid "MCP approval requests do not have an approval" errors.
    last_response_id: str | None = None

    agent_ref = {"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}}

    # Cumulative stats for the session
    session_start = time.time()
    total_tokens = 0
    message_count = 0

    def process_response(response: Any, spinner: Spinner | None = None) -> str | None:
        """Process response and handle MCP approval requests."""
        nonlocal last_response_id, total_tokens
        last_response_id = response.id

        # Accumulate tokens
        usage = getattr(response, "usage", None)
        if usage:
            total_tokens += getattr(usage, "total_tokens", 0) or (
                getattr(usage, "input_tokens", 0)
                + getattr(usage, "output_tokens", 0)
            )

        approval_requests = []
        for item in response.output:
            if item.type == "mcp_approval_request" and item.id:
                approval_requests.append(item)

        if approval_requests:
            if spinner:
                spinner.stop()

            approval_responses = []
            for req in approval_requests:
                print()
                print(f"{YELLOW}MCP Tool Approval Requested:{NC}")
                print(f"  Server: {req.server_label}")
                print(f"  Tool:   {getattr(req, 'name', '<unknown>')}")
                args = getattr(req, "arguments", None)
                if args:
                    print(f"  Args:   {json.dumps(args, indent=2, default=str)}")
                print()

                while True:
                    answer = input("Approve this tool call? (y/n): ").strip().lower()
                    if answer in ("y", "yes"):
                        approval_responses.append(
                            {
                                "type": "mcp_approval_response",
                                "approval_request_id": req.id,
                                "approve": True,
                            }
                        )
                        break
                    elif answer in ("n", "no"):
                        approval_responses.append(
                            {
                                "type": "mcp_approval_response",
                                "approval_request_id": req.id,
                                "approve": False,
                            }
                        )
                        break
                    else:
                        print("Please enter 'y' or 'n'.")

            sp = Spinner("Executing tool").start()
            followup = openai.responses.create(
                input=approval_responses,
                previous_response_id=response.id,
                extra_body=agent_ref,
            )
            return process_response(followup, sp)

        if spinner:
            spinner.stop()
        return response.output_text if hasattr(response, "output_text") else None

    def send_message(user_input: str) -> tuple[str | None, str]:
        """Send a user message with spinner, return (text, stats)."""
        nonlocal message_count
        message_count += 1
        sp = Spinner("Thinking").start()
        t0 = time.time()
        try:
            if last_response_id:
                response = openai.responses.create(
                    input=user_input,
                    previous_response_id=last_response_id,
                    extra_body=agent_ref,
                )
            else:
                response = openai.responses.create(
                    input=user_input,
                    extra_body=agent_ref,
                )
            output = process_response(response, sp)
        except Exception as exc:
            sp.stop()
            _handle_api_error(exc)
            return None, ""
        elapsed = time.time() - t0
        stats = _format_stats(elapsed, response)
        return output, stats

    # Initial message if provided
    if initial_message:
        print(f"{BOLD}You:{NC} {initial_message}")
        output, stats = send_message(initial_message)
        if output:
            print()
            print(f"{GREEN}Agent:{NC} {output}")
            print(f"       {stats}")
        print()

    def show_help() -> None:
        """Display available chat commands."""
        print()
        print(f"  {BOLD}Available Commands{NC}")
        print(f"  {'─' * 40}")
        print(f"  {CYAN}help{NC}           Show this help message")
        print(f"  {CYAN}status{NC}         Show agent and session info")
        print(f"  {CYAN}clear{NC}          Clear the screen")
        print(f"  {CYAN}reset{NC}          Reset conversation (start fresh)")
        print(f"  {CYAN}quit{NC} / {CYAN}exit{NC}   End the chat session")
        print()
        print(f"  {BOLD}Usage{NC}")
        print(f"  {'─' * 40}")
        print("  Type any message to chat with the agent.")
        print("  The agent has access to 300+ Zscaler tools.")
        print()
        print(f"  {BOLD}Examples{NC}")
        print(f"  {'─' * 40}")
        print(f"  {DIM}List all ZPA application segments{NC}")
        print(f"  {DIM}What Zscaler services are available?{NC}")
        print(f"  {DIM}Show ZIA firewall rules{NC}")
        print(f"  {DIM}Get ZDX application health for the last 24 hours{NC}")
        print()

    def show_status() -> None:
        """Display current session and agent info."""
        elapsed = time.time() - session_start
        print()
        print(f"  {BOLD}Session Info{NC}")
        print(f"  {'─' * 40}")
        print(f"  Agent:          {status['name']} (v{status['version']})")
        print(f"  Project:        {project_endpoint}")
        print(f"  Duration:       {elapsed:.0f}s")
        print(f"  Total tokens:   {total_tokens:,}")
        print(f"  Messages sent:  {message_count}")
        print()

    # Interactive loop
    try:
        while True:
            try:
                user_input = input(f"{BOLD}You:{NC} ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            cmd = user_input.lower()
            if cmd in ("quit", "exit", "q"):
                break
            if cmd == "help":
                show_help()
                continue
            if cmd == "status":
                show_status()
                continue
            if cmd == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue
            if cmd == "reset":
                last_response_id = None
                total_tokens = 0
                message_count = 0
                session_start = time.time()
                ok("Conversation reset. Starting fresh.")
                print()
                continue

            output, stats = send_message(user_input)
            if output:
                print()
                print(f"{GREEN}Agent:{NC} {output}")
                print(f"       {stats}")
            print()

    except KeyboardInterrupt:
        print()

    # Session summary
    session_elapsed = time.time() - session_start
    print()
    print(f"{DIM}{'─' * 50}{NC}")
    print(
        f"{DIM}Session: {session_elapsed:.0f}s"
        f" | Messages: {message_count}"
        f" | Tokens: {total_tokens:,}{NC}"
    )
    print(f"{DIM}{'─' * 50}{NC}")
    info("Chat session ended.")


# ── State Management ──────────────────────────────────────────────────────

AGENT_STATE_FILE = Path(__file__).resolve().parent / ".azure-agent-state.json"


def save_agent_state(state: dict[str, Any]) -> None:
    """Save agent state to file."""
    with open(AGENT_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_agent_state() -> dict[str, Any] | None:
    """Load agent state from file."""
    if not AGENT_STATE_FILE.exists():
        return None
    with open(AGENT_STATE_FILE) as f:
        return json.load(f)


def clear_agent_state() -> None:
    """Clear agent state file."""
    if AGENT_STATE_FILE.exists():
        AGENT_STATE_FILE.unlink()


# ── CLI Integration ───────────────────────────────────────────────────────


def _load_env_file(path: str) -> dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars: dict[str, str] = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value and value.upper() != "NOT_SET":
                        env_vars[key] = value
    except FileNotFoundError:
        warn(f"File not found: {path}")
    return env_vars


def prompt_foundry_config() -> dict[str, str]:
    """Interactively prompt for Foundry configuration."""
    print()
    print(f"{BOLD}Azure AI Foundry Configuration{NC}")
    print("-" * 40)
    print()
    print("You need an Azure AI Foundry project with Azure OpenAI.")
    print("Create one at: https://ai.azure.com")
    print()

    # Check for existing values from environment
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
    model = os.environ.get("AZURE_OPENAI_MODEL", "")

    # Offer to load from .env file
    if not endpoint:
        print("How would you like to provide Foundry configuration?")
        print("  1. Load from a .env file")
        print("  2. Enter manually")
        print()
        choice = input("Select [1/2]: ").strip()

        if choice == "1":
            env_path = input("Path to .env file: ").strip()
            if env_path:
                env_vars = _load_env_file(env_path)
                endpoint = env_vars.get("AZURE_AI_PROJECT_ENDPOINT", "")
                model = env_vars.get("AZURE_OPENAI_MODEL", "")
                if endpoint:
                    ok(f"Loaded project endpoint from {env_path}")
                else:
                    warn("AZURE_AI_PROJECT_ENDPOINT not found in .env file")

    # Prompt for endpoint if still empty
    if not endpoint:
        print()
        print("Project endpoint format:")
        print("  https://{resource}.services.ai.azure.com/api/projects/{project}")
        print()
        print("To find your endpoint:")
        print("  1. Go to https://ai.azure.com")
        print("  2. Open your project → Overview")
        print("  3. Copy the 'Microsoft Foundry project endpoint' URL")
        print()
        endpoint = input("Foundry project endpoint: ").strip()

    if not endpoint:
        die("Project endpoint is required.")

    # Model deployment
    if not model:
        model = DEFAULT_MODEL
    model_input = input(f"Model deployment name [{model}]: ").strip()
    if model_input:
        model = model_input

    return {
        "project_endpoint": endpoint,
        "model": model,
    }


def op_agent_create(
    mcp_url: str,
    auth_mode: str = "none",
    client_id: str | None = None,
    client_secret: str | None = None,
    api_key_value: str | None = None,
) -> None:
    """Create the Foundry agent."""
    config = prompt_foundry_config()

    # Build MCP auth headers
    mcp_headers = _build_mcp_headers(
        auth_mode=auth_mode,
        client_id=client_id,
        client_secret=client_secret,
        api_key_value=api_key_value,
    )

    print()
    info("Creating Foundry agent with Zscaler MCP tools...")
    print()

    agent_info = create_agent(
        project_endpoint=config["project_endpoint"],
        mcp_server_url=mcp_url,
        model=config["model"],
        require_approval="always",
        mcp_headers=mcp_headers if mcp_headers else None,
    )

    # Save state
    state = {
        **config,
        **agent_info,
    }
    save_agent_state(state)

    print()
    print("=" * 60)
    print(f"  {GREEN}Foundry Agent Created{NC}")
    print("=" * 60)
    print()
    print(f"  Agent Name:    {agent_info['name']}")
    print(f"  Version:       {agent_info['version']}")
    print(f"  Model:         {agent_info['model']}")
    print(f"  MCP Server:    {agent_info['mcp_url']}")
    print()
    print(f"  {BOLD}Next steps:{NC}")
    print("    1. Start a chat session:")
    print("       python azure_mcp_operations.py agent_chat")
    print()
    print("    2. Or use the Foundry portal:")
    print(f"       {config['project_endpoint'].replace('/api/projects/', '/projects/')}")
    print()


def op_agent_status() -> None:
    """Show agent status."""
    state = load_agent_state()
    if not state:
        warn("No agent state found. Run 'agent_create' first.")
        return

    project_endpoint = state.get("project_endpoint", "")
    if not project_endpoint:
        die("Project endpoint not found in state.")

    info(f"Checking agent status in: {project_endpoint}")
    print()

    status = get_agent_status(project_endpoint)
    if status:
        print(f"  Agent Name:    {status['name']}")
        print(f"  Version:       {status['version']}")
        print(f"  Status:        {GREEN}active{NC}")
        print(f"  MCP Server:    {state.get('mcp_url', 'unknown')}")
    else:
        warn(f"Agent '{AGENT_NAME}' not found in Foundry project.")


def op_agent_chat(initial_message: str | None = None) -> None:
    """Start interactive chat session."""
    state = load_agent_state()
    if not state:
        warn("No agent state found. Run 'agent_create' first.")
        return

    project_endpoint = state.get("project_endpoint", "")
    if not project_endpoint:
        die("Project endpoint not found in state.")

    chat_session(project_endpoint, initial_message)


def op_agent_destroy(yes: bool = False) -> None:
    """Delete the agent."""
    state = load_agent_state()
    if not state:
        warn("No agent state found.")
        return

    project_endpoint = state.get("project_endpoint", "")
    if not project_endpoint:
        die("Project endpoint not found in state.")

    if not yes:
        confirm = input(f"Delete agent '{AGENT_NAME}'? (y/N): ").strip().lower()
        if confirm not in ("y", "yes"):
            info("Cancelled.")
            return

    info(f"Deleting agent from: {project_endpoint}")
    if delete_agent(project_endpoint):
        clear_agent_state()
        ok("Agent deleted and state cleared.")


if __name__ == "__main__":
    # Simple test
    print("Foundry Agent Module")
    print(f"SDK installed: {check_sdk_installed()}")
