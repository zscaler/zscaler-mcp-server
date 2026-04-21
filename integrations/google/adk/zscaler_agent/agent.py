import logging
import os
import shutil
from typing import Any

from google.adk.agents import LlmAgent  # type: ignore[import-untyped]
from google.adk.agents.callback_context import CallbackContext  # type: ignore[import-untyped]
from google.adk.agents.readonly_context import ReadonlyContext  # type: ignore[import-untyped]
from google.adk.models import LlmRequest, LlmResponse  # type: ignore[import-untyped]
from google.adk.tools.base_tool import BaseTool  # type: ignore[import-untyped]
from google.adk.tools.mcp_tool.mcp_session_manager import (  # type: ignore[import-untyped]
    StdioConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset  # type: ignore[import-untyped]
from mcp import StdioServerParameters

tools_cache: dict[str, list[BaseTool]] = {}


def _sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Flatten anyOf/oneOf constructs in JSON schemas for Vertex AI compatibility.

    Vertex AI function calling requires every parameter to have an explicit
    ``type`` field. MCP tools using Python ``Union`` types produce ``anyOf``
    schemas (e.g. ``Union[List[str], str]`` -> ``{"anyOf": [...]}``) which
    Vertex AI rejects. This function collapses those to the simplest
    compatible type while preserving descriptions and other metadata.
    """
    if not isinstance(schema, dict):
        return schema

    if "anyOf" in schema or "oneOf" in schema:
        variants = schema.get("anyOf") or schema.get("oneOf", [])
        types = [v.get("type") for v in variants if isinstance(v, dict) and "type" in v]

        result: dict[str, Any] = {}
        if schema.get("description"):
            result["description"] = schema["description"]

        if "string" in types:
            result["type"] = "string"
        elif "array" in types:
            array_variant = next(
                (v for v in variants if isinstance(v, dict) and v.get("type") == "array"), None
            )
            result["type"] = "array"
            if array_variant and "items" in array_variant:
                result["items"] = _sanitize_schema(array_variant["items"])
        elif types:
            result["type"] = types[0]
        else:
            result["type"] = "string"

        for key in ("default", "enum", "title"):
            if key in schema:
                result[key] = schema[key]
        return result

    sanitized = {}
    for key, value in schema.items():
        if key == "properties" and isinstance(value, dict):
            sanitized[key] = {k: _sanitize_schema(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            sanitized[key] = _sanitize_schema(value)
        else:
            sanitized[key] = value
    return sanitized


def _sanitize_tool_schemas(tools: list[BaseTool]) -> list[BaseTool]:
    """Post-process MCP tools to ensure Vertex AI schema compatibility."""
    fixed = 0
    for tool in tools:
        if hasattr(tool, "_mcp_tool") and hasattr(tool._mcp_tool, "inputSchema"):
            original = tool._mcp_tool.inputSchema
            if original:
                sanitized = _sanitize_schema(original)
                if sanitized != original:
                    tool._mcp_tool.inputSchema = sanitized
                    fixed += 1
    if fixed:
        logging.info(f"Sanitized {fixed} tool schemas for Vertex AI compatibility")
    return tools


class CachedMCPToolset(MCPToolset):
    """Adds tool caching and schema sanitization on top of MCPToolset.

    Caches tools to avoid repeated MCP server round-trips and sanitizes
    input schemas to ensure compatibility with Vertex AI function calling.

    Note: ADK's ``require_confirmation`` is intentionally NOT used here
    because the ``adk web`` developer UI does not implement the
    ``adk_request_confirmation`` protocol, causing the agent to stall.
    Delete confirmations are handled by the MCP server's HMAC token flow
    (transport-agnostic, works in both stdio and streamable-http).
    """

    def __init__(self, *, tool_set_name: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.tool_set_name = tool_set_name
        logging.info(f"CachedMCPToolset initialized: '{self.tool_set_name}'")

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        if self.tool_set_name in tools_cache:
            logging.info(f"Returning cached tools for '{self.tool_set_name}'")
            return tools_cache[self.tool_set_name]

        logging.info(f"Fetching tools for '{self.tool_set_name}' from MCP server")
        tools = await super().get_tools(readonly_context)
        tools = _sanitize_tool_schemas(tools)
        tools_cache[self.tool_set_name] = tools
        logging.info(f"Cached {len(tools)} tools for '{self.tool_set_name}'")
        return tools


# Context size management for Model response time and cost optimization
# https://github.com/google/adk-python/issues/752#issuecomment-2948152979
def bmc_trim_llm_request(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    max_prev_user_interactions = int(os.environ.get("MAX_PREV_USER_INTERACTIONS", "-1"))

    logging.info(
        f"Number of contents going to LLM - {len(llm_request.contents)}, MAX_PREV_USER_INTERACTIONS = {max_prev_user_interactions}"
    )

    if max_prev_user_interactions == -1:
        return None

    temp_processed_list = []
    user_message_count = 0
    for i in range(len(llm_request.contents) - 1, -1, -1):
        item = llm_request.contents[i]

        if (
            item.role == "user"
            and item.parts[0]
            and item.parts[0].text
            and item.parts[0].text != "For context:"
        ):
            logging.info(f"Encountered a user message => {item.parts[0].text}")
            user_message_count += 1

        if user_message_count > max_prev_user_interactions:
            logging.info(f"Breaking at user_message_count => {user_message_count}")
            temp_processed_list.append(item)
            break

        temp_processed_list.append(item)

    final_list = temp_processed_list[::-1]

    if user_message_count < max_prev_user_interactions:
        logging.info(
            "User message count did not reach the allowed limit. List remains unchanged."
        )
    else:
        logging.info(
            f"User message count reached {max_prev_user_interactions}. List truncated."
        )
        llm_request.contents = final_list

    return None


_google_model = os.environ.get("GOOGLE_MODEL", "")

_AGENT_INSTRUCTION = """\
You are a Zscaler Zero Trust security assistant with access to ZPA, ZIA, ZDX, \
ZCC, EASM, ZIdentity, ZTW, Z-Insights, and ZMS tools. Help users query and \
manage their Zscaler Zero Trust Exchange environment.

Rules:
- Always use the available tools directly to fulfill requests.
- Never generate code, import modules, or write scripts.
- When asked to create resources with random or example values, choose \
reasonable names yourself and call the appropriate tool immediately.
- Explain your findings clearly and suggest next steps when appropriate.
- You are a tool-calling agent, not a code interpreter.

HMAC Confirmation Protocol (mandatory for delete operations):
- When you call a delete tool, the server will NOT delete immediately. \
Instead it returns a CONFIRMATION REQUIRED message containing a \
confirmation_token and the operation details.
- You MUST show the full confirmation message to the user and ask for \
explicit approval.
- If the user approves, re-call the SAME tool with the SAME arguments \
plus kwargs set to the JSON string containing the token, for example: \
kwargs='{"confirmation_token": "1234567890:abcdef..."}'
- If the user declines, do NOT re-call the tool. Acknowledge the \
cancellation.
- NEVER auto-confirm. NEVER skip the confirmation step. This is a \
zero-trust security requirement.
"""
_zscaler_client_id = os.environ.get("ZSCALER_CLIENT_ID", "")
_zscaler_client_secret = os.environ.get("ZSCALER_CLIENT_SECRET", "")
_zscaler_vanity_domain = os.environ.get("ZSCALER_VANITY_DOMAIN", "")
_zscaler_customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
_zscaler_cloud = os.environ.get("ZSCALER_CLOUD", "")

_mcp_services = os.environ.get("ZSCALER_MCP_SERVICES", "")
_mcp_write_enabled = os.environ.get("ZSCALER_MCP_WRITE_ENABLED", "")
_mcp_write_tools = os.environ.get("ZSCALER_MCP_WRITE_TOOLS", "")

_mcp_env: dict[str, str] = {
    "ZSCALER_CLIENT_ID": _zscaler_client_id,
    "ZSCALER_CLIENT_SECRET": _zscaler_client_secret,
    "ZSCALER_VANITY_DOMAIN": _zscaler_vanity_domain,
    "ZSCALER_CUSTOMER_ID": _zscaler_customer_id,
    "ZSCALER_CLOUD": _zscaler_cloud,
}

# Optional MCP configuration vars — only pass if set
_OPTIONAL_MCP_VARS = [
    "ZSCALER_MCP_SERVICES",
    "ZSCALER_MCP_WRITE_ENABLED",
    "ZSCALER_MCP_WRITE_TOOLS",
    "ZSCALER_MCP_DISABLED_SERVICES",
    "ZSCALER_MCP_DISABLED_TOOLS",
    # Security enforcement — these default to restrictive settings in the MCP
    # server (auth enabled, HTTPS required, host validation on). For stdio
    # transport auth/TLS/host-validation are not applicable, but for Cloud Run
    # or Agent Engine deployments where the server may be exposed over HTTP
    # these must be configured explicitly.
    "ZSCALER_MCP_AUTH_ENABLED",
    "ZSCALER_MCP_ALLOW_HTTP",
    "ZSCALER_MCP_ALLOWED_HOSTS",
    "ZSCALER_MCP_ALLOWED_SOURCE_IPS",
    "ZSCALER_MCP_TLS_CERTFILE",
    "ZSCALER_MCP_TLS_KEYFILE",
    "ZSCALER_MCP_DISABLE_HOST_VALIDATION",
    # Write-operation safety
    "ZSCALER_MCP_SKIP_CONFIRMATIONS",
    "ZSCALER_MCP_CONFIRMATION_TTL",
]

for _var in _OPTIONAL_MCP_VARS:
    _val = os.environ.get(_var, "")
    if _val:
        _mcp_env[_var] = _val

_mcp_command = "uvx" if shutil.which("uvx") else "zscaler-mcp"
_mcp_args: list[str] = ["zscaler-mcp"] if _mcp_command == "uvx" else []
if _mcp_services:
    _mcp_args.extend(["--services", _mcp_services])

root_agent = LlmAgent(
    model=_google_model,
    name="zscaler_agent",
    instruction=_AGENT_INSTRUCTION,
    before_model_callback=bmc_trim_llm_request,
    tools=[
        CachedMCPToolset(
            tool_set_name="zscaler-tools",
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=_mcp_command,
                    args=_mcp_args,
                    env=_mcp_env,
                ),
                timeout=60.0,
            ),
        ),
    ],
)
