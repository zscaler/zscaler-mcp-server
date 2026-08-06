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
    build_oidc_auth_kwargs,
    fetch_oneapi_token,
    get_registered_zscaler_providers,
    platform_auth_trusted,
    resolve_oidc_auth,
)
from zscaler_mcp.security.elicitation import (
    CAPABILITY_CHECK_FAILED,
    TOKEN_FALLBACK,
    CapabilityCheckFailed,
    DeleteConfirmation,
    build_confirmation_request,
    check_confirmation,
    elicitation_available,
    extract_confirmed_from_kwargs,
    gate_destructive_operation,
    interpret_confirmation,
    is_capability_check_failure,
    is_token_fallback,
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
    "resolve_oidc_auth",
    "build_oidc_auth_kwargs",
    "get_registered_zscaler_providers",
    "fetch_oneapi_token",
    "platform_auth_trusted",
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
    "DeleteConfirmation",
    "CAPABILITY_CHECK_FAILED",
    "TOKEN_FALLBACK",
    "CapabilityCheckFailed",
    "build_confirmation_request",
    "interpret_confirmation",
    "is_token_fallback",
    "elicitation_available",
    "is_capability_check_failure",
    "extract_confirmed_from_kwargs",
    "gate_destructive_operation",
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
