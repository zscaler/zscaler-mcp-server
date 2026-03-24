"""
Tests for security features in zscaler_mcp.server and zscaler_mcp.common.logging.

Covers:
    - Host validation defaults (_get_transport_security)
    - Runtime host guard (_validate_host_config)
    - TLS/HTTPS configuration (_get_tls_config)
    - Security posture banner (_log_security_posture)
    - Plaintext .env advisory (_check_env_file_security)
    - Consolidated log_security_warning (common/logging.py)
"""

import logging
import os
import tempfile
from unittest.mock import patch

import pytest

from zscaler_mcp.common.logging import log_security_warning
from zscaler_mcp.server import (
    _check_env_file_security,
    _enforce_https_policy,
    _get_allowed_source_ips,
    _get_tls_config,
    _get_transport_security,
    _ip_matches,
    _is_http_allowed,
    _log_security_posture,
    _validate_host_config,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HOST_VAL_ENVS = [
    "ZSCALER_MCP_DISABLE_HOST_VALIDATION",
    "ZSCALER_MCP_ALLOWED_HOSTS",
    "ZSCALER_MCP_TLS_CERTFILE",
    "ZSCALER_MCP_TLS_KEYFILE",
]

_TLS_ENVS = [
    "ZSCALER_MCP_TLS_CERTFILE",
    "ZSCALER_MCP_TLS_KEYFILE",
    "ZSCALER_MCP_TLS_KEYFILE_PASSWORD",
    "ZSCALER_MCP_TLS_CA_CERTS",
]

_POSTURE_ENVS = [
    "ZSCALER_MCP_AUTH_ENABLED",
    "ZSCALER_MCP_AUTH_MODE",
    "ZSCALER_MCP_AUTH_JWKS_URI",
    "ZSCALER_MCP_AUTH_API_KEY",
    "ZSCALER_VANITY_DOMAIN",
    "ZSCALER_MCP_DISABLE_HOST_VALIDATION",
    "ZSCALER_MCP_ALLOWED_HOSTS",
    "ZSCALER_MCP_SKIP_CONFIRMATIONS",
    "ZSCALER_MCP_TLS_CERTFILE",
    "ZSCALER_MCP_TLS_KEYFILE",
    "ZSCALER_MCP_ALLOW_HTTP",
    "ZSCALER_MCP_ALLOWED_SOURCE_IPS",
]

_HTTPS_POLICY_ENVS = [
    "ZSCALER_MCP_ALLOW_HTTP",
    "ZSCALER_MCP_TLS_CERTFILE",
    "ZSCALER_MCP_TLS_KEYFILE",
]
_SRC_IP_ENVS = ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"]


def _clean_env(keys):
    """Remove environment variables for a clean test state."""
    for k in keys:
        os.environ.pop(k, None)


# ---------------------------------------------------------------------------
# log_security_warning (common/logging.py)
# ---------------------------------------------------------------------------


class TestLogSecurityWarning:
    def test_logs_warning_banner(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
            log_security_warning("Test Title", ["Detail line 1", "Detail line 2"])
        assert "SECURITY WARNING: Test Title" in caplog.text
        assert "Detail line 1" in caplog.text
        assert "Detail line 2" in caplog.text

    def test_logs_separator_lines(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
            log_security_warning("X", ["y"])
        assert "=" * 72 in caplog.text

    def test_empty_details_list(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
            log_security_warning("No Details", [])
        assert "SECURITY WARNING: No Details" in caplog.text


# ---------------------------------------------------------------------------
# _get_transport_security — Host Validation
# ---------------------------------------------------------------------------


class TestGetTransportSecurity:
    def setup_method(self):
        _clean_env(_HOST_VAL_ENVS)

    def teardown_method(self):
        _clean_env(_HOST_VAL_ENVS)

    def test_localhost_returns_none(self):
        result = _get_transport_security(host="127.0.0.1")
        assert result is None

    def test_localhost_no_host_returns_none(self):
        result = _get_transport_security()
        assert result is None

    def test_zero_bind_without_config_raises(self):
        with pytest.raises(SystemExit, match="Cannot bind to 0.0.0.0"):
            _get_transport_security(host="0.0.0.0")

    def test_zero_bind_with_allowed_hosts(self):
        os.environ["ZSCALER_MCP_ALLOWED_HOSTS"] = "example.com:*,localhost:*"
        result = _get_transport_security(host="0.0.0.0")
        assert result is not None
        assert result.allowed_hosts == ["example.com:*", "localhost:*"]

    def test_allowed_hosts_origins_http(self):
        os.environ["ZSCALER_MCP_ALLOWED_HOSTS"] = "app.example.com:8000"
        result = _get_transport_security(host="0.0.0.0")
        assert result is not None
        assert "http://app.example.com:8000" in result.allowed_origins

    def test_allowed_hosts_origins_https_with_tls(self):
        certfile = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        keyfile = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            certfile.write(b"cert")
            certfile.close()
            keyfile.write(b"key")
            keyfile.close()
            os.environ["ZSCALER_MCP_TLS_CERTFILE"] = certfile.name
            os.environ["ZSCALER_MCP_TLS_KEYFILE"] = keyfile.name
            os.environ["ZSCALER_MCP_ALLOWED_HOSTS"] = "app.example.com:443"
            result = _get_transport_security(host="0.0.0.0")
            assert result is not None
            assert "https://app.example.com:443" in result.allowed_origins
        finally:
            os.unlink(certfile.name)
            os.unlink(keyfile.name)

    def test_explicit_disable_returns_dns_rebinding_off(self):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "true"
        result = _get_transport_security(host="0.0.0.0")
        assert result is not None
        assert result.enable_dns_rebinding_protection is False

    def test_explicit_disable_accepts_1(self):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "1"
        result = _get_transport_security(host="0.0.0.0")
        assert result is not None
        assert result.enable_dns_rebinding_protection is False

    def test_explicit_disable_accepts_yes(self):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "yes"
        result = _get_transport_security(host="0.0.0.0")
        assert result is not None
        assert result.enable_dns_rebinding_protection is False

    def test_disable_logs_security_warning(self, caplog):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "true"
        with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
            _get_transport_security(host="0.0.0.0")
        assert "SECURITY WARNING" in caplog.text
        assert "Host Header Validation" in caplog.text

    def test_dns_rebinding_enabled_with_allowlist(self):
        os.environ["ZSCALER_MCP_ALLOWED_HOSTS"] = "myhost:8000"
        result = _get_transport_security(host="0.0.0.0")
        assert result.enable_dns_rebinding_protection is True

    def test_allowed_hosts_comma_separated(self):
        os.environ["ZSCALER_MCP_ALLOWED_HOSTS"] = "a.com:*, b.com:*, c.com:8080"
        result = _get_transport_security(host="0.0.0.0")
        assert len(result.allowed_hosts) == 3
        assert "a.com:*" in result.allowed_hosts
        assert "b.com:*" in result.allowed_hosts


# ---------------------------------------------------------------------------
# _validate_host_config — Runtime Guard
# ---------------------------------------------------------------------------


class TestValidateHostConfig:
    def setup_method(self):
        _clean_env(_HOST_VAL_ENVS)

    def teardown_method(self):
        _clean_env(_HOST_VAL_ENVS)

    def test_localhost_passes(self):
        _validate_host_config("127.0.0.1")

    def test_other_ip_passes(self):
        _validate_host_config("10.0.0.1")

    def test_zero_bind_no_config_raises(self):
        with pytest.raises(SystemExit, match="Cannot bind to 0.0.0.0"):
            _validate_host_config("0.0.0.0")

    def test_zero_bind_with_allowed_hosts_passes(self):
        os.environ["ZSCALER_MCP_ALLOWED_HOSTS"] = "example.com:*"
        _validate_host_config("0.0.0.0")

    def test_zero_bind_with_disable_passes(self):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "true"
        _validate_host_config("0.0.0.0")

    def test_zero_bind_with_disable_1_passes(self):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "1"
        _validate_host_config("0.0.0.0")

    def test_zero_bind_with_disable_yes_passes(self):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "yes"
        _validate_host_config("0.0.0.0")


# ---------------------------------------------------------------------------
# _get_tls_config
# ---------------------------------------------------------------------------


class TestGetTlsConfig:
    def setup_method(self):
        _clean_env(_TLS_ENVS)

    def teardown_method(self):
        _clean_env(_TLS_ENVS)

    def test_no_env_returns_empty(self):
        assert _get_tls_config() == {}

    def test_both_files_returns_config(self):
        cert = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        key = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            cert.write(b"cert-data")
            cert.close()
            key.write(b"key-data")
            key.close()
            os.environ["ZSCALER_MCP_TLS_CERTFILE"] = cert.name
            os.environ["ZSCALER_MCP_TLS_KEYFILE"] = key.name
            result = _get_tls_config()
            assert result["ssl_certfile"] == cert.name
            assert result["ssl_keyfile"] == key.name
        finally:
            os.unlink(cert.name)
            os.unlink(key.name)

    def test_only_cert_raises(self):
        cert = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            cert.write(b"cert")
            cert.close()
            os.environ["ZSCALER_MCP_TLS_CERTFILE"] = cert.name
            with pytest.raises(SystemExit, match="Incomplete TLS"):
                _get_tls_config()
        finally:
            os.unlink(cert.name)

    def test_only_key_raises(self):
        key = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            key.write(b"key")
            key.close()
            os.environ["ZSCALER_MCP_TLS_KEYFILE"] = key.name
            with pytest.raises(SystemExit, match="Incomplete TLS"):
                _get_tls_config()
        finally:
            os.unlink(key.name)

    def test_cert_file_not_found_raises(self):
        os.environ["ZSCALER_MCP_TLS_CERTFILE"] = "/nonexistent/cert.pem"
        os.environ["ZSCALER_MCP_TLS_KEYFILE"] = "/nonexistent/key.pem"
        with pytest.raises(SystemExit, match="certificate file not found"):
            _get_tls_config()

    def test_key_file_not_found_raises(self):
        cert = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            cert.write(b"cert")
            cert.close()
            os.environ["ZSCALER_MCP_TLS_CERTFILE"] = cert.name
            os.environ["ZSCALER_MCP_TLS_KEYFILE"] = "/nonexistent/key.pem"
            with pytest.raises(SystemExit, match="key file not found"):
                _get_tls_config()
        finally:
            os.unlink(cert.name)

    def test_optional_password(self):
        cert = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        key = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            cert.write(b"cert")
            cert.close()
            key.write(b"key")
            key.close()
            os.environ["ZSCALER_MCP_TLS_CERTFILE"] = cert.name
            os.environ["ZSCALER_MCP_TLS_KEYFILE"] = key.name
            os.environ["ZSCALER_MCP_TLS_KEYFILE_PASSWORD"] = "s3cret"
            result = _get_tls_config()
            assert result["ssl_keyfile_password"] == "s3cret"
        finally:
            os.unlink(cert.name)
            os.unlink(key.name)

    def test_optional_ca_certs(self):
        cert = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        key = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        ca = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            cert.write(b"cert")
            cert.close()
            key.write(b"key")
            key.close()
            ca.write(b"ca")
            ca.close()
            os.environ["ZSCALER_MCP_TLS_CERTFILE"] = cert.name
            os.environ["ZSCALER_MCP_TLS_KEYFILE"] = key.name
            os.environ["ZSCALER_MCP_TLS_CA_CERTS"] = ca.name
            result = _get_tls_config()
            assert result["ssl_ca_certs"] == ca.name
        finally:
            os.unlink(cert.name)
            os.unlink(key.name)
            os.unlink(ca.name)

    def test_ca_certs_not_found_raises(self):
        cert = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        key = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        try:
            cert.write(b"cert")
            cert.close()
            key.write(b"key")
            key.close()
            os.environ["ZSCALER_MCP_TLS_CERTFILE"] = cert.name
            os.environ["ZSCALER_MCP_TLS_KEYFILE"] = key.name
            os.environ["ZSCALER_MCP_TLS_CA_CERTS"] = "/nonexistent/ca.pem"
            with pytest.raises(SystemExit, match="CA certificate file not found"):
                _get_tls_config()
        finally:
            os.unlink(cert.name)
            os.unlink(key.name)

    def test_whitespace_values_treated_as_empty(self):
        os.environ["ZSCALER_MCP_TLS_CERTFILE"] = "   "
        os.environ["ZSCALER_MCP_TLS_KEYFILE"] = "   "
        assert _get_tls_config() == {}


# ---------------------------------------------------------------------------
# _log_security_posture
# ---------------------------------------------------------------------------


class TestLogSecurityPosture:
    def setup_method(self):
        _clean_env(_POSTURE_ENVS)

    def teardown_method(self):
        _clean_env(_POSTURE_ENVS)

    def test_http_no_tls(self, caplog):
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "http://127.0.0.1:8000" in caplog.text
        assert "DISABLED (plaintext)" in caplog.text

    def test_https_with_tls(self, caplog):
        tls = {"ssl_certfile": "/path/cert.pem", "ssl_keyfile": "/path/key.pem"}
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "https", "0.0.0.0", 443, tls)
        assert "https://0.0.0.0:443" in caplog.text
        assert "ENABLED (encrypted)" in caplog.text

    def test_mutual_tls_indicated(self, caplog):
        tls = {
            "ssl_certfile": "/c.pem",
            "ssl_keyfile": "/k.pem",
            "ssl_ca_certs": "/ca.pem",
        }
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "https", "0.0.0.0", 443, tls)
        assert "Mutual TLS:   Yes" in caplog.text

    def test_no_mutual_tls(self, caplog):
        tls = {"ssl_certfile": "/c.pem", "ssl_keyfile": "/k.pem"}
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "https", "0.0.0.0", 443, tls)
        assert "Mutual TLS:   No" in caplog.text

    def test_auth_disabled(self, caplog):
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "false"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "Authentication: DISABLED" in caplog.text

    def test_auth_jwt_auto_detected(self, caplog):
        os.environ["ZSCALER_MCP_AUTH_JWKS_URI"] = "https://idp.example.com/keys"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "jwt (auto-detected)" in caplog.text

    def test_auth_api_key_auto_detected(self, caplog):
        os.environ["ZSCALER_MCP_AUTH_API_KEY"] = "sk-test"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "api-key (auto-detected)" in caplog.text

    def test_auth_zscaler_auto_detected(self, caplog):
        os.environ["ZSCALER_VANITY_DOMAIN"] = "acme"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "zscaler (auto-detected)" in caplog.text

    def test_auth_explicit_mode(self, caplog):
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "jwt"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "Mode:         jwt" in caplog.text

    def test_host_validation_disabled(self, caplog):
        os.environ["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "true"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "Host Validation:DISABLED" in caplog.text or "DISABLED" in caplog.text

    def test_host_validation_allowlist(self, caplog):
        os.environ["ZSCALER_MCP_ALLOWED_HOSTS"] = "myapp.com:*"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "0.0.0.0", 8000, {})
        assert "myapp.com:*" in caplog.text

    def test_host_validation_localhost_only(self, caplog):
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "localhost only" in caplog.text

    def test_confirmations_enabled(self, caplog):
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "HMAC-bound tokens" in caplog.text

    def test_confirmations_disabled(self, caplog):
        os.environ["ZSCALER_MCP_SKIP_CONFIRMATIONS"] = "true"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "DISABLED (skip)" in caplog.text

    def test_banner_separators(self, caplog):
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "=" * 72 in caplog.text
        assert "ZSCALER MCP SERVER" in caplog.text


# ---------------------------------------------------------------------------
# _check_env_file_security
# ---------------------------------------------------------------------------


class TestCheckEnvFileSecurity:
    def test_no_env_file_no_warning(self, caplog, tmp_path):
        with patch("zscaler_mcp.server.os.getcwd", return_value=str(tmp_path)):
            with patch("zscaler_mcp.server.os.path.dirname") as mock_dirname:
                mock_dirname.return_value = str(tmp_path / "nonexistent")
                with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
                    _check_env_file_security()
        assert "SECURITY WARNING" not in caplog.text

    def test_env_with_secrets_warns(self, caplog, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ZSCALER_CLIENT_SECRET=mysecret\nOTHER=value\n")
        with patch("zscaler_mcp.server.os.getcwd", return_value=str(tmp_path)):
            with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
                _check_env_file_security()
        assert "SECURITY WARNING" in caplog.text
        assert "ZSCALER_CLIENT_SECRET" in caplog.text

    def test_env_with_api_key_warns(self, caplog, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ZSCALER_MCP_AUTH_API_KEY=sk-test\n")
        with patch("zscaler_mcp.server.os.getcwd", return_value=str(tmp_path)):
            with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
                _check_env_file_security()
        assert "SECURITY WARNING" in caplog.text
        assert "ZSCALER_MCP_AUTH_API_KEY" in caplog.text

    def test_env_with_private_key_warns(self, caplog, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ZSCALER_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n")
        with patch("zscaler_mcp.server.os.getcwd", return_value=str(tmp_path)):
            with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
                _check_env_file_security()
        assert "SECURITY WARNING" in caplog.text

    def test_env_with_commented_secret_no_warning(self, caplog, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# ZSCALER_CLIENT_SECRET=commented_out\n")
        fake_pkg = tmp_path / "pkg"
        fake_pkg.mkdir()
        with (
            patch("zscaler_mcp.server.os.getcwd", return_value=str(tmp_path)),
            patch("zscaler_mcp.server.os.path.abspath", return_value=str(fake_pkg / "server.py")),
        ):
            with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
                _check_env_file_security()
        assert "ZSCALER_CLIENT_SECRET" not in caplog.text

    def test_env_without_secrets_no_warning(self, caplog, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ZSCALER_MCP_TRANSPORT=streamable-http\nZSCALER_CLOUD=beta\n")
        fake_pkg = tmp_path / "pkg"
        fake_pkg.mkdir()
        with (
            patch("zscaler_mcp.server.os.getcwd", return_value=str(tmp_path)),
            patch("zscaler_mcp.server.os.path.abspath", return_value=str(fake_pkg / "server.py")),
        ):
            with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
                _check_env_file_security()
        assert "SECURITY WARNING" not in caplog.text

    def test_advisory_mentions_alternatives(self, caplog, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ZSCALER_CLIENT_SECRET=x\n")
        with patch("zscaler_mcp.server.os.getcwd", return_value=str(tmp_path)):
            with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security"):
                _check_env_file_security()
        assert (
            "Docker" in caplog.text
            or "Kubernetes" in caplog.text
            or "Secrets Manager" in caplog.text
        )


# ---------------------------------------------------------------------------
# HTTPS Policy — _is_http_allowed / _enforce_https_policy
# ---------------------------------------------------------------------------


class TestIsHttpAllowed:
    def setup_method(self):
        _clean_env(_HTTPS_POLICY_ENVS)

    def teardown_method(self):
        _clean_env(_HTTPS_POLICY_ENVS)

    def test_default_is_false(self):
        assert _is_http_allowed() is False

    def test_true(self):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = "true"
        assert _is_http_allowed() is True

    def test_1(self):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = "1"
        assert _is_http_allowed() is True

    def test_yes(self):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = "yes"
        assert _is_http_allowed() is True

    def test_false(self):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = "false"
        assert _is_http_allowed() is False

    def test_empty_is_false(self):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = ""
        assert _is_http_allowed() is False

    def test_whitespace_is_false(self):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = "   "
        assert _is_http_allowed() is False


class TestEnforceHttpsPolicy:
    def setup_method(self):
        _clean_env(_HTTPS_POLICY_ENVS)

    def teardown_method(self):
        _clean_env(_HTTPS_POLICY_ENVS)

    def test_localhost_always_allowed(self):
        _enforce_https_policy("127.0.0.1", 8000, {})

    def test_localhost_ipv6_allowed(self):
        _enforce_https_policy("::1", 8000, {})

    def test_localhost_name_allowed(self):
        _enforce_https_policy("localhost", 8000, {})

    def test_tls_present_always_allowed(self):
        _enforce_https_policy("0.0.0.0", 8000, {"ssl_certfile": "/c.pem"})

    def test_non_localhost_no_tls_blocked(self):
        with pytest.raises(SystemExit, match="HTTPS is required"):
            _enforce_https_policy("0.0.0.0", 8000, {})

    def test_non_localhost_no_tls_specific_ip_blocked(self):
        with pytest.raises(SystemExit, match="HTTPS is required"):
            _enforce_https_policy("10.0.0.5", 8000, {})

    def test_allow_http_bypasses(self):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = "true"
        _enforce_https_policy("0.0.0.0", 8000, {})

    def test_error_message_contains_instructions(self):
        with pytest.raises(SystemExit, match="ZSCALER_MCP_TLS_CERTFILE"):
            _enforce_https_policy("0.0.0.0", 8000, {})


# ---------------------------------------------------------------------------
# Source IP ACL — _get_allowed_source_ips / _ip_matches
# ---------------------------------------------------------------------------


class TestGetAllowedSourceIps:
    def setup_method(self):
        _clean_env(_SRC_IP_ENVS)

    def teardown_method(self):
        _clean_env(_SRC_IP_ENVS)

    def test_unset_returns_none(self):
        assert _get_allowed_source_ips() is None

    def test_empty_returns_none(self):
        os.environ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"] = ""
        assert _get_allowed_source_ips() is None

    def test_whitespace_returns_none(self):
        os.environ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"] = "   "
        assert _get_allowed_source_ips() is None

    def test_single_ip(self):
        os.environ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"] = "10.0.0.5"
        assert _get_allowed_source_ips() == ["10.0.0.5"]

    def test_multiple_ips(self):
        os.environ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"] = "10.0.0.5, 192.168.1.0/24, 172.16.0.0/12"
        result = _get_allowed_source_ips()
        assert len(result) == 3
        assert "10.0.0.5" in result
        assert "192.168.1.0/24" in result

    def test_wildcard(self):
        os.environ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"] = "0.0.0.0/0"
        result = _get_allowed_source_ips()
        assert result == ["0.0.0.0/0"]


class TestIpMatches:
    def test_exact_match(self):
        assert _ip_matches("10.0.0.5", ["10.0.0.5"]) is True

    def test_exact_no_match(self):
        assert _ip_matches("10.0.0.6", ["10.0.0.5"]) is False

    def test_cidr_match(self):
        assert _ip_matches("192.168.1.50", ["192.168.1.0/24"]) is True

    def test_cidr_no_match(self):
        assert _ip_matches("192.168.2.50", ["192.168.1.0/24"]) is False

    def test_wildcard_star(self):
        assert _ip_matches("1.2.3.4", ["*"]) is True

    def test_wildcard_cidr_all(self):
        assert _ip_matches("1.2.3.4", ["0.0.0.0/0"]) is True

    def test_multiple_entries(self):
        allowed = ["10.0.0.0/8", "172.16.0.0/12"]
        assert _ip_matches("10.5.5.5", allowed) is True
        assert _ip_matches("172.20.1.1", allowed) is True
        assert _ip_matches("192.168.1.1", allowed) is False

    def test_invalid_client_ip(self):
        assert _ip_matches("not-an-ip", ["10.0.0.0/8"]) is False

    def test_ipv6_match(self):
        assert _ip_matches("::1", ["::1"]) is True

    def test_ipv6_no_match(self):
        assert _ip_matches("::1", ["::2"]) is False

    def test_empty_list(self):
        assert _ip_matches("10.0.0.1", []) is False

    def test_invalid_cidr_skipped(self):
        assert _ip_matches("10.0.0.1", ["not-valid", "10.0.0.1"]) is True


# ---------------------------------------------------------------------------
# Security Posture Banner — HTTP Policy & Source IP fields
# ---------------------------------------------------------------------------


class TestLogSecurityPostureNewFields:
    def setup_method(self):
        _clean_env(_POSTURE_ENVS)

    def teardown_method(self):
        _clean_env(_POSTURE_ENVS)

    def test_http_policy_blocked_default(self, caplog):
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "0.0.0.0", 8000, {})
        assert "HTTP Policy:    BLOCKED (default)" in caplog.text

    def test_http_policy_allowed_explicit(self, caplog):
        os.environ["ZSCALER_MCP_ALLOW_HTTP"] = "true"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "0.0.0.0", 8000, {})
        assert "ALLOWED (explicit opt-in)" in caplog.text

    def test_http_policy_localhost(self, caplog):
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "ALLOWED (localhost)" in caplog.text

    def test_http_policy_tls_active(self, caplog):
        tls = {"ssl_certfile": "/c.pem", "ssl_keyfile": "/k.pem"}
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "https", "0.0.0.0", 443, tls)
        assert "N/A (TLS active)" in caplog.text

    def test_source_ip_disabled(self, caplog):
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "defer to firewall" in caplog.text

    def test_source_ip_with_allowlist(self, caplog):
        os.environ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"] = "10.0.0.0/8,172.16.0.5"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "10.0.0.0/8" in caplog.text
        assert "172.16.0.5" in caplog.text

    def test_source_ip_allow_all(self, caplog):
        os.environ["ZSCALER_MCP_ALLOWED_SOURCE_IPS"] = "0.0.0.0/0"
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.server"):
            _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        assert "ALLOW ALL" in caplog.text
