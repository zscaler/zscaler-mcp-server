# pylint: disable=line-too-long,logging-fstring-interpolation
"""
Zscaler MCP Genesis Wrapper

AWS Genesis wrapper for the Zscaler MCP Server.
Provides FastAPI endpoints for Genesis integration with streaming NDJSON responses.

This module implements a FastAPI-based web server that acts as an adapter between
AWS Genesis runtime and the Zscaler MCP Server. It handles Genesis-specific
HTTP requests and translates them to MCP tool calls, returning results in the required
streaming NDJSON format.

Key Components:
    - FastAPI application with Genesis-compatible endpoints
    - Streaming NDJSON response generation for Genesis runtime
    - Tool call dispatcher using FastMCP's call_tool mechanism
    - Proper error handling and logging for production deployment

Genesis Protocol:
    - Accepts HTTP POST requests with tool name and arguments
    - Returns streaming NDJSON with start/data/end signals
    - Handles session management via Genesis session headers
    - Supports both direct JSON and base64-encoded payloads
"""
import json
import base64
import logging
import asyncio
from typing import Dict, Any, AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
from dotenv import load_dotenv

# Import the Zscaler MCP Server
from zscaler_mcp.server import ZscalerMCPServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Zscaler MCP Genesis Wrapper",
    description="AWS Genesis wrapper for Zscaler MCP Server",
    version="1.0.0"
)

# Create instance of Zscaler MCP server
logger.info("Initializing Zscaler MCP Server instance")
mcp_server = ZscalerMCPServer()


@app.get("/health")
def health() -> Dict[str, str]:
    """
    Health check endpoint required by AWS ECS.

    Returns:
        Dict[str, str]: Health status response with OK status and message
    """
    return {"status": "ok", "message": "Zscaler MCP Server is running"}


async def generate_streaming_response(
    response_data: Dict[str, Any],
    session_id: str
) -> AsyncGenerator[str, None]:
    """
    Generate streaming HTTP response in NDJSON format for Genesis.

    Genesis expects streaming responses with start/data/end signals in NDJSON format.
    Each signal is a separate JSON object on its own line, allowing Genesis to
    process the response incrementally.

    Args:
        response_data (Dict[str, Any]): The response data to stream
        session_id (str): Genesis session ID for tracking

    Yields:
        str: NDJSON formatted lines (JSON object + newline)
    """
    current_time = asyncio.get_event_loop().time()

    # Start signal - indicates beginning of response
    yield json.dumps({
        "type": "start",
        "session_id": session_id,
        "timestamp": current_time
    }) + "\n"

    # Data signal - contains the actual response payload
    yield json.dumps({
        "type": "data",
        "session_id": session_id,
        "data": response_data,
        "timestamp": current_time,
    }) + "\n"

    # End signal - indicates completion of response
    yield json.dumps({
        "type": "end",
        "session_id": session_id,
        "timestamp": current_time
    }) + "\n"


@app.post("/mcp/")
async def mcp_endpoint(request: Request) -> StreamingResponse:
    """
    Genesis MCP integration endpoint.

    Main endpoint for Genesis to invoke MCP tools. Handles Genesis-specific request
    format, extracts tool information, calls the appropriate Zscaler MCP tool, and
    returns results in Genesis-compatible streaming NDJSON format.

    Request Format:
        - Direct JSON: {"name": "tool_name", "arguments": {...}}
        - Base64 encoded: {"payload": "base64_encoded_json"}

    Response Format:
        - Streaming NDJSON with start/data/end signals
        - Each line is a separate JSON object
        - Genesis session ID maintained throughout

    Args:
        request (Request): FastAPI request object containing tool invocation data

    Returns:
        StreamingResponse: NDJSON streaming response for Genesis runtime
    """
    endpoint_logger = logging.getLogger("mcp_endpoint")

    try:
        # Extract Genesis session ID from headers (handle both case variations)
        headers = dict(request.headers)
        session_id = (
            headers.get("x-amzn-genesis-session-id") or
            headers.get("X-Amzn-Genesis-Session-Id", "default-session")
        )

        endpoint_logger.info(f"Processing Genesis MCP request with session ID: {session_id}")

        # Parse request body - handle both direct JSON and base64-encoded payloads
        body_bytes = await request.body()
        try:
            req_json = json.loads(body_bytes.decode("utf-8"))

            if "payload" in req_json:
                # Handle base64-encoded payload (some Genesis configurations use this)
                payload_bytes = base64.b64decode(req_json["payload"])
                payload = json.loads(payload_bytes.decode("utf-8"))
                endpoint_logger.debug("Decoded base64 payload")
            else:
                # Direct JSON payload
                payload = req_json
                endpoint_logger.debug("Using direct JSON payload")

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            # Fallback for malformed JSON - treat as raw content
            endpoint_logger.warning(f"Failed to parse JSON payload: {e}")
            payload = {"content": body_bytes.decode("utf-8")}

        endpoint_logger.debug(f"Parsed payload: {payload}")

        # Extract tool information from payload based on method
        method = payload.get("method", "")
        if method == "tools/call":
            # For tools/call: {"method": "tools/call", "params": {"name": "tool_name", "arguments": {...}}}
            tool_name = payload.get("params", {}).get("name")
            arguments = payload.get("params", {}).get("arguments", {})
        elif method == "tools/list":
            # For tools/list: {"method": "tools/list", "params": {"_meta": {...}}}
            tool_name = "tools/list"
            arguments = payload.get("params", {}).get("_meta", {})
        else:
            # Fallback for other formats
            tool_name = payload.get("name") or payload.get("tool", {}).get("name")
            arguments = payload.get("arguments") or payload.get("tool", {}).get("parameters", {})

        # Validate required tool information
        if not tool_name:
            endpoint_logger.warning("Missing tool name in request")
            result = {"status": "error", "error": "Missing tool name in request"}
        else:
            # Dispatch tool call to Zscaler MCP server
            endpoint_logger.info(f"Calling Zscaler MCP tool: {tool_name}")
            result = await call_zscaler_tool(tool_name, arguments)

        # Prepare Genesis response data
        response_data = {
            "body": "Tool invocation complete",
            "genesis_session_id": session_id,
            "request_body": payload,
            "result": result,
        }

        endpoint_logger.debug(f"Sending response for session {session_id}")

        # Return streaming NDJSON response
        return StreamingResponse(
            generate_streaming_response(response_data, session_id),
            media_type="application/x-ndjson",
            headers={
                "X-Amzn-Genesis-Session-Id": session_id,
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Broad exception catch is intentional here as the final error boundary
        # to ensure we always return a proper HTTP response to Genesis
        endpoint_logger.error(f"Unexpected error in MCP endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )


async def call_zscaler_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a tool on the Zscaler MCP server using FastMCP's call_tool mechanism.

    This function handles the interface between Genesis requests and the Zscaler MCP server.
    It uses FastMCP's internal call_tool method which respects the MCP protocol and
    returns structured responses that we can process for Genesis.

    Based on debugging, call_tool returns a tuple:
    - Item 0: List of TextContent objects (MCP protocol format)
    - Item 1: Dictionary with clean JSON data (what we want for Genesis)

    Args:
        tool_name (str): Name of the Zscaler MCP tool to invoke
        arguments (Dict[str, Any]): Arguments to pass to the tool

    Returns:
        Dict[str, Any]: Structured response with status, tool name, and results
            - success: {"status": "success", "tool": tool_name, "result": [json_data]}
            - error: {"status": "error", "tool": tool_name, "error": error_message}
    """
    tool_logger = logging.getLogger("call_zscaler_tool")

    try:
        tool_logger.info(f"Invoking Zscaler MCP tool: {tool_name} with args: {arguments}")

        # Use FastMCP's internal call_tool method - respects MCP protocol
        result = await mcp_server.server.call_tool(tool_name, arguments)

        tool_logger.debug(f"Raw call_tool result type: {type(result)}")

        # Handle the tuple format returned by call_tool
        if isinstance(result, tuple) and len(result) == 2:
            _, clean_data = result  # First item is TextContent list, we only need clean_data
            tool_logger.debug(f"Extracted clean data from tuple: {clean_data}")

            # Return the clean data directly - this is the JSON we want
            return {
                "status": "success",
                "tool": tool_name,
                "result": [json.dumps(clean_data, indent=2)]
            }

        # Fallback for non-tuple results (defensive programming)
        if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
            tool_logger.debug("Processing iterable result format")
            processed_result = []

            for item in result:
                if hasattr(item, 'text'):
                    # TextContent object - extract text
                    processed_result.append(item.text)
                elif isinstance(item, dict):
                    # Dictionary - convert to JSON
                    processed_result.append(json.dumps(item, indent=2))
                else:
                    # Other types - convert to string
                    processed_result.append(str(item))

            return {
                "status": "success",
                "tool": tool_name,
                "result": processed_result
            }

        # Handle single result objects
        tool_logger.debug("Processing single result object")
        if hasattr(result, 'text'):
            result_data = [result.text]
        elif isinstance(result, dict):
            result_data = [json.dumps(result, indent=2)]
        else:
            result_data = [str(result)]

        return {
            "status": "success",
            "tool": tool_name,
            "result": result_data
        }

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Broad exception catch is intentional here to handle any possible
        # error during tool execution and return structured error to Genesis
        tool_logger.error(f"Error calling Zscaler MCP tool {tool_name}: {e}", exc_info=True)
        return {
            "status": "error",
            "tool": tool_name,
            "error": str(e)
        }


@app.get("/")
def root() -> Dict[str, Any]:
    """
    Root endpoint providing service information.

    Returns basic information about the Zscaler MCP Genesis Wrapper service,
    including available endpoints and service metadata.

    Returns:
        Dict[str, Any]: Service information including version and endpoints
    """
    return {
        "message": "Zscaler MCP Genesis Wrapper",
        "version": "1.0.0",
        "description": "AWS Genesis wrapper for Zscaler MCP Server",
        "endpoints": {
            "health": "/health",
            "mcp": "/mcp"
        },
    }


if __name__ == "__main__":
    logger.info("Starting Zscaler MCP Genesis Wrapper server")
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
