"""Tests for the Bedrock AgentCore runtime provisioner Lambda.

The provisioner is not importable as part of the package — it is a standalone
Lambda handler shipped inside the CloudFormation assets — so it is loaded from
its path here.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PROVISIONER = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "aws"
    / "bedrock-agentcore"
    / "cloudformation"
    / "lambda"
    / "runtime_provisioner.py"
)


@pytest.fixture(scope="module")
def provisioner():
    """Load the handler with a stub boto3.

    boto3 lives behind the optional ``[aws]`` extra and the module builds a
    control-plane client at import time. Stubbing it keeps these assertions —
    which are about header configuration, not AWS calls — running everywhere
    rather than skipping wherever the extra is absent.
    """
    stub = types.ModuleType("boto3")
    stub.client = MagicMock()  # type: ignore[attr-defined]
    real_boto3 = sys.modules.get("boto3")
    sys.modules["boto3"] = stub

    spec = importlib.util.spec_from_file_location("runtime_provisioner", _PROVISIONER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["runtime_provisioner"] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop("runtime_provisioner", None)
        if real_boto3 is not None:
            sys.modules["boto3"] = real_boto3
        else:
            sys.modules.pop("boto3", None)


def _allowlist(module, props) -> list[str]:
    kwargs = module.build_inbound_auth_kwargs(props)
    return kwargs["requestHeaderConfiguration"]["requestHeaderAllowlist"]


JWT_PROPS = {
    "McpAuthMode": "jwt",
    "JwtIssuer": "https://tenant.us.auth0.com/",
    "JwtAudience": "zscaler-mcp-server",
}

ALL_MODES = [
    {"McpAuthMode": "none"},
    {"McpAuthMode": "api-key"},
    {"McpAuthMode": "zscaler"},
    JWT_PROPS,
]


class TestModernProtocolRoutingHeaders:
    """MCP 2026-07-28 is reachable only if its routing headers survive the proxy.

    InvokeAgentRuntime forwards nothing outside the allowlist, and the SDK
    routes to the modern stateless handler on the header alone, so a missing
    entry here does not slow the revision down — it removes it.
    """

    @pytest.mark.parametrize("props", ALL_MODES, ids=lambda p: p["McpAuthMode"])
    def test_every_auth_mode_forwards_the_routing_headers(self, provisioner, props):
        allowlist = {h.lower() for h in _allowlist(provisioner, props)}
        assert {"mcp-protocol-version", "mcp-method", "mcp-name"} <= allowlist

    @pytest.mark.parametrize("props", ALL_MODES, ids=lambda p: p["McpAuthMode"])
    def test_allowlist_stays_within_the_20_header_cap(self, provisioner, props):
        assert len(_allowlist(provisioner, props)) <= 20

    @pytest.mark.parametrize("props", ALL_MODES, ids=lambda p: p["McpAuthMode"])
    def test_no_restricted_amazon_prefixes(self, provisioner, props):
        for header in _allowlist(provisioner, props):
            assert not header.lower().startswith(("x-amz-", "x-amzn-"))

    def test_routing_headers_match_the_sdk_constants(self, provisioner):
        """Pin our spelling to the SDK's, so an upstream rename fails here."""
        from mcp.shared.inbound import (
            MCP_METHOD_HEADER,
            MCP_NAME_HEADER,
            MCP_PROTOCOL_VERSION_HEADER,
        )

        assert {
            MCP_PROTOCOL_VERSION_HEADER,
            MCP_METHOD_HEADER,
            MCP_NAME_HEADER,
        } <= {h.lower() for h in provisioner.MCP_ROUTING_HEADERS}

    @pytest.mark.parametrize("props", ALL_MODES, ids=lambda p: p["McpAuthMode"])
    def test_every_auth_mode_forwards_the_session_header(self, provisioner, props):
        """The handshake revision is unusable if its session id is stripped."""
        allowlist = {h.lower() for h in _allowlist(provisioner, props)}
        assert "mcp-session-id" in allowlist


class TestCredentialHeaders:
    def test_api_key_mode_forwards_the_api_key_header(self, provisioner):
        allowlist = _allowlist(provisioner, {"McpAuthMode": "api-key"})
        assert "X-Api-Key" in allowlist

    def test_zscaler_mode_forwards_both_credential_headers(self, provisioner):
        allowlist = _allowlist(provisioner, {"McpAuthMode": "zscaler"})
        assert "X-Zscaler-Client-ID" in allowlist
        assert "X-Zscaler-Client-Secret" in allowlist

    def test_jwt_mode_pairs_authorization_with_an_authorizer(self, provisioner):
        """AgentCore rejects a forwarded Authorization without customJwtAuthorizer."""
        kwargs = provisioner.build_inbound_auth_kwargs(JWT_PROPS)
        assert "Authorization" in kwargs["requestHeaderConfiguration"]["requestHeaderAllowlist"]
        assert kwargs["authorizerConfiguration"]["customJWTAuthorizer"]["discoveryUrl"] == (
            "https://tenant.us.auth0.com/.well-known/openid-configuration"
        )

    def test_none_mode_forwards_no_credential_header(self, provisioner):
        allowlist = _allowlist(provisioner, {"McpAuthMode": "none"})
        assert allowlist == provisioner.MCP_ROUTING_HEADERS
        assert "authorizerConfiguration" not in provisioner.build_inbound_auth_kwargs(
            {"McpAuthMode": "none"}
        )
