#!/usr/bin/env python3
"""Call the MCP server on Bedrock AgentCore, from a terminal.

The Console playground cannot do this: it submits a bare JSON-RPC body and has
no UI for request headers, so it can neither select the 2026-07-28 revision nor
echo the ``Mcp-Session-Id`` the handshake revisions depend on. Both are header
mechanics, so any real test has to come from a client that can set headers.

Usage:
    python3 invoke_mcp.py --list-tools
    python3 invoke_mcp.py --call zia_list_ssl_inspection_rules
    python3 invoke_mcp.py --call zia_list_ssl_inspection_rules --args '{"page_size": 5}'
    python3 invoke_mcp.py --legacy --list-tools     # handshake revision instead

The runtime ARN is read from .aws-deploy-state.json unless --arn is given.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import boto3

PROTOCOL_VERSION = "2026-07-28"
LEGACY_VERSION = "2025-11-25"
STATE_FILE = Path(__file__).with_name(".aws-deploy-state.json")

META = {
    "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "invoke_mcp", "version": "1"},
}
EVENT = "before-sign.bedrock-agentcore.InvokeAgentRuntime"

# tools/call mirrors params.name into Mcp-Name; prompts/get and resources/read
# mirror their own key. Anything else sends no name header.
NAME_KEYS = {"tools/call": "name", "prompts/get": "name", "resources/read": "uri"}


def resolve_arn(explicit: str | None) -> str:
    if explicit:
        return explicit
    if not STATE_FILE.exists():
        sys.exit(f"No {STATE_FILE.name}; pass --arn explicitly.")
    state = json.loads(STATE_FILE.read_text())
    region = state.get("region", "us-east-1")
    prefix = state.get("resource_prefix", "zscaler-mcp").replace("-", "")
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    for rt in control.list_agent_runtimes().get("agentRuntimes", []):
        if rt["agentRuntimeName"].startswith(prefix):
            return rt["agentRuntimeArn"]
    sys.exit("No matching agent runtime found; pass --arn explicitly.")


def decode(response) -> str:
    return b"".join(response.get("response", [])).decode("utf-8").strip()


def unwrap(raw: str) -> dict:
    """Return the JSON-RPC object, whether it arrived raw or as an SSE frame."""
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return json.loads(raw)


class Client:
    """Speaks either MCP revision over InvokeAgentRuntime."""

    def __init__(self, arn: str, region: str, legacy: bool = False):
        self.arn = arn
        self.legacy = legacy
        self.session_id: str | None = None
        self.client = boto3.client("bedrock-agentcore", region_name=region)
        self._rpc_id = 0

    def _post(self, body: dict, protocol_version: str, headers: dict) -> str:
        """Send one JSON-RPC message.

        InvokeAgentRuntime models Accept, Mcp-Protocol-Version and
        Mcp-Session-Id as first-class API parameters, so those are passed
        directly. Mcp-Method and Mcp-Name have no parameter and must be
        attached as raw headers, which is why they need to be in the runtime's
        requestHeaderAllowlist to survive the trip.
        """
        kwargs = {
            "agentRuntimeArn": self.arn,
            "payload": json.dumps(body).encode(),
            "contentType": "application/json",
            # The MCP streamable-http endpoint requires both; offering only
            # application/json gets a 406 before the body is ever read.
            "accept": "application/json, text/event-stream",
            "mcpProtocolVersion": protocol_version,
        }
        if self.session_id:
            kwargs["mcpSessionId"] = self.session_id

        def add(request, **_):
            for key, value in headers.items():
                request.headers.add_header(key, value)

        handler = self.client.meta.events.register_first(EVENT, add) if headers else None
        try:
            response = self.client.invoke_agent_runtime(**kwargs)
        finally:
            if handler is not None:
                self.client.meta.events.unregister(EVENT, handler)

        # The session id is only issued on the handshake path, and only by
        # initialize; capture it so later calls in this session can echo it.
        for key, value in response.get("ResponseMetadata", {}).get("HTTPHeaders", {}).items():
            if key.lower() == "mcp-session-id":
                self.session_id = value
        return decode(response)

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def call(self, method: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        headers: dict[str, str] = {}
        if not self.legacy:
            # The envelope replaces the handshake: it carries the protocol
            # version and client capabilities on every single request.
            params["_meta"] = META
            headers["Mcp-Method"] = method
            name_key = NAME_KEYS.get(method)
            if name_key and params.get(name_key):
                headers["Mcp-Name"] = params[name_key]

        version = LEGACY_VERSION if self.legacy else PROTOCOL_VERSION
        body = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        return unwrap(self._post(body, version, headers))

    def notify(self, method: str) -> None:
        self._post({"jsonrpc": "2.0", "method": method}, LEGACY_VERSION, {})

    def handshake(self) -> dict:
        """Run initialize + initialized. Only the legacy revision needs this."""
        result = self.call(
            "initialize",
            {
                "protocolVersion": LEGACY_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "invoke_mcp", "version": "1"},
            },
        )
        self.notify("notifications/initialized")
        return result


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--arn", help="Agent runtime ARN (default: from .aws-deploy-state.json)")
    ap.add_argument("--region", default=None)
    ap.add_argument(
        "--legacy", action="store_true", help=f"Use the {LEGACY_VERSION} handshake revision"
    )
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--call", metavar="TOOL", help="Tool name to invoke")
    ap.add_argument("--args", default="{}", help="Tool arguments as a JSON object")
    ap.add_argument("--raw", action="store_true", help="Print the full JSON-RPC response")
    args = ap.parse_args()

    region = args.region or (
        json.loads(STATE_FILE.read_text()).get("region", "us-east-1")
        if STATE_FILE.exists()
        else "us-east-1"
    )
    arn = resolve_arn(args.arn)
    revision = LEGACY_VERSION if args.legacy else PROTOCOL_VERSION
    print(f"runtime  : {arn}")
    print(f"revision : {revision}\n")

    client = Client(arn, region, legacy=args.legacy)
    if args.legacy:
        info = client.handshake().get("result", {}).get("serverInfo", {})
        print(
            f"handshake: {info.get('name')} {info.get('version')}  (session {client.session_id})\n"
        )

    if args.list_tools:
        response = client.call("tools/list", {})
        if args.raw:
            print(json.dumps(response, indent=2))
            return
        if "error" in response:
            sys.exit(f"ERROR {response['error'].get('code')}: {response['error'].get('message')}")
        tools = response.get("result", {}).get("tools", [])
        print(f"{len(tools)} tools")
        for tool in tools:
            print(f"  - {tool['name']}")
        return

    if args.call:
        response = client.call(
            "tools/call", {"name": args.call, "arguments": json.loads(args.args)}
        )
        if args.raw:
            print(json.dumps(response, indent=2))
            return
        if "error" in response:
            sys.exit(f"ERROR {response['error'].get('code')}: {response['error'].get('message')}")
        for block in response.get("result", {}).get("content", []):
            print(block.get("text", block))
        return

    ap.error("Pass --list-tools or --call TOOL")


if __name__ == "__main__":
    main()
