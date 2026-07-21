"""Security layer — MCP client auth, transport hardening, write-confirmation,
output sanitization, and audit logging.

Carried forward from v1, faithful in behaviour. Each concern lives in its own
module; this package exposes the public surface the server wires together.
"""

from zscaler_mcp.security.audit import (
    disable_tool_call_logging,
    enable_tool_call_logging,
    is_tool_call_logging_enabled,
    refresh_tool_call_logging,
    wrap_tool,
)
from zscaler_mcp.security.auth import (
    APIKeyAuthProvider,
    AuthMiddleware,
    AuthProvider,
    JWTAuthProvider,
    ZscalerAuthProvider,
    apply_auth_middleware,
    build_oidcproxy_provider,
    fetch_oneapi_token,
    get_registered_zscaler_providers,
    resolve_fastmcp_auth,
)
from zscaler_mcp.security.elicitation import (
    check_confirmation,
    extract_confirmed_from_kwargs,
    should_skip_confirmations,
)
from zscaler_mcp.security.entitlements import (
    apply_entitlement_filter,
    decode_oneapi_token,
    extract_entitled_services,
    obtain_oneapi_token,
)
from zscaler_mcp.security.hardening import (
    HostValidationMiddleware,
    SourceIPMiddleware,
    apply_transport_hardening,
    get_allowed_hosts,
    get_allowed_source_ips,
    host_validation_disabled,
    validate_host_binding,
)
from zscaler_mcp.security.sanitize import (
    is_sanitization_enabled,
    sanitize_value,
)

__all__ = [
    # auth
    "AuthProvider",
    "APIKeyAuthProvider",
    "JWTAuthProvider",
    "ZscalerAuthProvider",
    "AuthMiddleware",
    "apply_auth_middleware",
    "resolve_fastmcp_auth",
    "build_oidcproxy_provider",
    "get_registered_zscaler_providers",
    "fetch_oneapi_token",
    # entitlement
    "apply_entitlement_filter",
    "decode_oneapi_token",
    "extract_entitled_services",
    "obtain_oneapi_token",
    # hardening
    "SourceIPMiddleware",
    "HostValidationMiddleware",
    "apply_transport_hardening",
    "get_allowed_source_ips",
    "get_allowed_hosts",
    "host_validation_disabled",
    "validate_host_binding",
    # elicitation
    "check_confirmation",
    "extract_confirmed_from_kwargs",
    "should_skip_confirmations",
    # sanitize
    "sanitize_value",
    "is_sanitization_enabled",
    # audit
    "wrap_tool",
    "enable_tool_call_logging",
    "disable_tool_call_logging",
    "is_tool_call_logging_enabled",
    "refresh_tool_call_logging",
]
