"""
Zscaler MCP Agent for Google ADK

This module provides a Google ADK-based agent integrated with the zscaler-mcp server.
It can be deployed to Cloud Run, Vertex AI Agent Engine, or Agentspace.
"""

import logging
import os
import sys
from typing import List, Optional, TextIO, Union

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import ToolPredicate
from google.adk.tools.mcp_tool import MCPTool
from google.adk.tools.mcp_tool.mcp_session_manager import (
    SseConnectionParams,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
    retry_on_closed_resource,
)
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from mcp import StdioServerParameters
from mcp.types import ListToolsResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tools cache for performance optimization
tools_cache = {}


def make_tools_compatible(tools: List[BaseTool]) -> List[BaseTool]:
    """
    Make the schema compatible with Gemini/Vertex AI API.
    
    This function is needed when:
    - API used is Gemini and model is other than 2.5 models
    - API used is VertexAI (for ALL models)
    
    Args:
        tools: List of MCP tools to process
        
    Returns:
        List of tools with compatible schemas
    """
    for tool in tools:
        for key in tool._mcp_tool.inputSchema.keys():
            if key == "properties":
                for prop_name in tool._mcp_tool.inputSchema["properties"].keys():
                    if "anyOf" in tool._mcp_tool.inputSchema["properties"][prop_name].keys():
                        any_of = tool._mcp_tool.inputSchema["properties"][prop_name]["anyOf"]
                        if any_of[0]["type"] == "array":
                            tool._mcp_tool.inputSchema["properties"][prop_name]["type"] = (
                                any_of[0]["items"]["type"]
                            )
                        else:
                            tool._mcp_tool.inputSchema["properties"][prop_name]["type"] = (
                                any_of[0]["type"]
                            )
                        tool._mcp_tool.inputSchema["properties"][prop_name].pop("anyOf")
    return tools


class MCPToolSetWithSchemaAccess(MCPToolset):
    """
    Extended MCPToolset with schema compatibility and caching.
    
    This class makes MCP tools schema compatible with Vertex AI API and older
    Gemini models, while also providing performance improvements through caching.
    """

    def __init__(
        self,
        *,
        tool_set_name: str,
        connection_params: Union[
            StdioServerParameters,
            StdioConnectionParams,
            SseConnectionParams,
            StreamableHTTPConnectionParams,
        ],
        tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
        errlog: TextIO = sys.stderr,
    ):
        """
        Initialize the MCPToolset with schema access.
        
        Args:
            tool_set_name: Name identifier for this toolset (used for caching)
            connection_params: Connection parameters for the MCP server
            tool_filter: Optional filter for available tools
            errlog: Error output stream
        """
        super().__init__(
            connection_params=connection_params,
            tool_filter=tool_filter,
            errlog=errlog
        )
        self.tool_set_name = tool_set_name
        logger.info(f"MCPToolSetWithSchemaAccess initialized: '{self.tool_set_name}'")
        self._session = None

    @retry_on_closed_resource
    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:
        """
        Return all tools in the toolset based on the provided context.

        Args:
            readonly_context: Context used to filter tools available to the agent.
                If None, all tools in the toolset are returned.

        Returns:
            List[BaseTool]: A list of tools available under the specified context.
        """
        # Get session from session manager
        session = await self._mcp_session_manager.create_session()

        # Check cache first for performance
        if self.tool_set_name in tools_cache:
            logger.info(f"Tools found in cache for toolset '{self.tool_set_name}'")
            return tools_cache[self.tool_set_name]
        
        logger.info(f"Loading tools for toolset '{self.tool_set_name}'")

        # Fetch available tools from the MCP server
        tools_response: ListToolsResult = await session.list_tools()

        # Apply filtering based on context and tool_filter
        tools = []
        for tool in tools_response.tools:
            mcp_tool = MCPTool(
                mcp_tool=tool,
                mcp_session_manager=self._mcp_session_manager,
                auth_scheme=self._auth_scheme,
                auth_credential=self._auth_credential,
            )

            if self._is_tool_selected(mcp_tool, readonly_context):
                tools.append(mcp_tool)

        # Check if schema compatibility is needed
        model = os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")
        use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "False").upper() == "TRUE"
        
        try:
            model_version = float(model.split("-")[1])
            needs_compat = model_version < 2.5 or use_vertex
        except (IndexError, ValueError):
            # If we can't parse the version, assume we need compatibility
            needs_compat = True

        if needs_compat:
            logger.info(f"Model '{model}' needs Gemini-compatible tools, updating schema...")
            tools = make_tools_compatible(tools)
        else:
            logger.info(f"Model '{model}' does not need schema updates")

        # Cache the tools
        tools_cache[self.tool_set_name] = tools
        logger.info(f"Loaded {len(tools)} tools for toolset '{self.tool_set_name}'")

        return tools


def trim_llm_request(
    callback_context: CallbackContext, 
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Trim LLM request to control context size for performance and cost optimization.
    
    This callback limits the number of previous user interactions sent to the LLM,
    which helps reduce response time and API costs.
    
    Reference: https://github.com/google/adk-python/issues/752#issuecomment-2948152979
    
    Args:
        callback_context: The callback context
        llm_request: The LLM request to potentially trim
        
    Returns:
        None (modifies llm_request in place if needed)
    """
    max_prev = int(os.environ.get("MAX_PREV_USER_INTERACTIONS", "-1"))

    logger.debug(
        f"LLM request contents: {len(llm_request.contents)}, "
        f"MAX_PREV_USER_INTERACTIONS: {max_prev}"
    )

    if max_prev == -1:
        return None

    temp_list = []
    user_count = 0

    for i in range(len(llm_request.contents) - 1, -1, -1):
        item = llm_request.contents[i]

        if (
            item.role == "user" 
            and item.parts 
            and item.parts[0] 
            and item.parts[0].text 
            and item.parts[0].text != "For context:"
        ):
            logger.debug(f"User message: {item.parts[0].text[:50]}...")
            user_count += 1

        if user_count > max_prev:
            logger.debug(f"Breaking at user_message_count: {user_count}")
            temp_list.append(item)
            break

        temp_list.append(item)

    if user_count >= max_prev:
        logger.info(f"Trimmed conversation to {max_prev} user interactions")
        llm_request.contents = temp_list[::-1]
    else:
        logger.debug("Conversation within limits, no trimming needed")

    return None


def build_mcp_env() -> dict:
    """
    Build environment variables for the Zscaler MCP server subprocess.
    
    Returns:
        Dictionary of environment variables
    """
    env = {}
    
    # Required Zscaler credentials
    env_vars = [
        "ZSCALER_CLIENT_ID",
        "ZSCALER_CLIENT_SECRET",
        "ZSCALER_VANITY_DOMAIN",
    ]
    
    # Optional credentials
    optional_vars = [
        "ZSCALER_CUSTOMER_ID",
        "ZSCALER_CLOUD",
        "ZSCALER_MCP_SERVICES",
        "ZSCALER_MCP_DEBUG",
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value and value != "NOT_SET":
            env[var] = value
        else:
            logger.warning(f"Required environment variable {var} is not set")
    
    for var in optional_vars:
        value = os.environ.get(var)
        if value and value != "NOT_SET" and value.strip():
            env[var] = value
    
    return env


# =============================================================================
# Agent Definition
# =============================================================================

# Default agent prompt if not provided via environment
DEFAULT_PROMPT = """You are a helpful Zscaler security assistant with access to the Zscaler Zero Trust Exchange platform.

You can help users with:
- **ZIA (Zscaler Internet Access)**: Firewall rules, URL filtering, DLP policies, locations, users
- **ZPA (Zscaler Private Access)**: Application segments, access policies, connectors, server groups
- **ZDX (Zscaler Digital Experience)**: Device monitoring, application performance, alerts, software inventory
- **ZCC (Zscaler Client Connector)**: Device enrollment, trusted networks, forwarding profiles
- **EASM (External Attack Surface Management)**: Organizations, findings, lookalike domains
- **ZIdentity**: Users, groups, identity management

When responding:
1. Clearly explain what action you're taking
2. Provide concise summaries of results
3. If a query returns many results, summarize the key findings
4. Ask for clarification if the request is ambiguous
5. Always prioritize security best practices in your recommendations
"""

# Get agent prompt from environment or use default
agent_prompt = os.environ.get("ZSCALER_AGENT_PROMPT", DEFAULT_PROMPT)
if agent_prompt == "NOT_SET":
    agent_prompt = DEFAULT_PROMPT

# Create the root agent
root_agent = LlmAgent(
    model=os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash"),
    name="zscaler_agent",
    instruction=agent_prompt,
    before_model_callback=trim_llm_request,
    tools=[
        MCPToolSetWithSchemaAccess(
            tool_set_name="zscaler-tools",
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="zscaler-mcp",
                    env=build_mcp_env(),
                )
            ),
        ),
    ],
)

