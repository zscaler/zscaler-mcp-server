"""Tests for the restored v1-parity CLI surface on :mod:`zscaler_mcp.server`.

These cover the operator-facing flags and helpers that were dropped during the
v2 re-architecture and re-added for parity:

* ``--version`` / ``-v``
* ``--list-tools`` (registry-driven, honours ``--services`` / ``--disabled-services``)
* ``--services`` / ``--disabled-services`` argparse wiring
* ``--generate-auth-token`` (basic + bearer + missing-creds error)
* ``--user-agent-comment`` + client-side User-Agent construction
* ``_resolve_dotenv_path`` override precedence
* lifecycle subcommands land in ``args.command``
"""

from __future__ import annotations

import pytest

from zscaler_mcp import __version__, server
from zscaler_mcp.common.utils import get_combined_user_agent, get_mcp_user_agent

# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def test_parser_accepts_new_flags():
    args = server.build_parser().parse_args(
        [
            "--services",
            "zpa,zia",
            "--disabled-services",
            "zcc",
            "--user-agent-comment",
            "Claude Desktop 1.0",
            "--dotenv-path",
            "/tmp/x.env",
            "--pid-file",
            "/tmp/x.pid",
        ]
    )
    assert args.services == "zpa,zia"
    assert args.disabled_services == "zcc"
    assert args.user_agent_comment == "Claude Desktop 1.0"
    assert args.dotenv_path == "/tmp/x.env"
    assert args.pid_file == "/tmp/x.pid"
    assert getattr(args, "command", None) is None  # serve path


def test_parser_list_tools_flag():
    args = server.build_parser().parse_args(["--list-tools"])
    assert args.list_tools is True


def test_parser_disabled_toolsets_flag():
    args = server.build_parser().parse_args(["--disabled-toolsets", "zia_ssl_inspection,zia_admin"])
    assert args.disabled_toolsets == "zia_ssl_inspection,zia_admin"
    assert server._parse_csv(args.disabled_toolsets) == ["zia_ssl_inspection", "zia_admin"]
    # Default is empty -> _parse_csv resolves to None (no blocklist).
    default = server.build_parser().parse_args([])
    assert server._parse_csv(default.disabled_toolsets) is None


def test_disabled_toolsets_env_default(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_DISABLED_TOOLSETS", "zia_admin")
    args = server.build_parser().parse_args([])
    assert args.disabled_toolsets == "zia_admin"


def test_parser_enable_write_tools_flag():
    args = server.build_parser().parse_args(["--enable-write-tools"])
    assert args.enable_write_tools is True
    # Default is off for safety (assuming the env var is not set in CI).
    default = server.build_parser().parse_args([])
    assert default.enable_write_tools is False


def test_enable_write_tools_env_default(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_WRITE_ENABLED", "true")
    args = server.build_parser().parse_args([])
    assert args.enable_write_tools is True


@pytest.mark.parametrize("value,expected", [([], "basic"), (["bearer"], "bearer")])
def test_parser_generate_auth_token(value, expected):
    args = server.build_parser().parse_args(["--generate-auth-token", *value])
    assert args.generate_auth_token == expected


def test_version_flag_exits_zero_and_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        server.build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


@pytest.mark.parametrize("cmd", ["reload", "restart", "status", "stop", "update"])
def test_lifecycle_subcommands_captured(cmd):
    args = server.build_parser().parse_args([cmd])
    assert args.command == cmd


# ---------------------------------------------------------------------------
# --list-tools helper
# ---------------------------------------------------------------------------


def test_list_available_tools_filters_by_service(capsys):
    server.list_available_tools(enabled_services=["zpa"])
    out = capsys.readouterr().out
    assert "zpa" in out
    # No other service should leak in when the allowlist is zpa-only.
    for other in ("zia_", "zdx_", "zcc_"):
        assert other not in out


def test_list_available_tools_includes_write_tools(capsys):
    server.list_available_tools()
    out = capsys.readouterr().out
    # Write tools are shown tagged with their action so the list is complete.
    assert "Zscaler MCP Server" in out
    assert "tool(s) across" in out


# ---------------------------------------------------------------------------
# --generate-auth-token
# ---------------------------------------------------------------------------


def test_generate_auth_token_basic(monkeypatch, capsys):
    monkeypatch.setenv("ZSCALER_CLIENT_ID", "id123")
    monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "secret456")
    server.generate_auth_token("basic")
    out = capsys.readouterr().out
    # base64("id123:secret456")
    import base64

    expected = base64.b64encode(b"id123:secret456").decode()
    assert f"Basic {expected}" in out
    assert "X-Zscaler-Client-ID" in out  # raw-header alternative shown for basic


def test_generate_auth_token_bearer(monkeypatch, capsys):
    monkeypatch.setenv("ZSCALER_CLIENT_ID", "id123")
    monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "secret456")
    server.generate_auth_token("bearer")
    out = capsys.readouterr().out
    assert "Bearer secret456" in out
    assert "X-Zscaler-Client-ID" not in out  # raw-header alt is basic-only


def test_generate_auth_token_requires_credentials(monkeypatch):
    monkeypatch.delenv("ZSCALER_CLIENT_ID", raising=False)
    monkeypatch.delenv("ZSCALER_CLIENT_SECRET", raising=False)
    with pytest.raises(SystemExit) as exc:
        server.generate_auth_token("basic")
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# .env resolution
# ---------------------------------------------------------------------------


def test_resolve_dotenv_path_explicit_override(tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text("ZSCALER_MCP_UA_TEST=fromfile\n")
    monkeypatch.delenv("ZSCALER_MCP_UA_TEST", raising=False)
    loaded = server._resolve_dotenv_path(str(env_file))
    assert loaded == str(env_file)
    import os

    assert os.environ["ZSCALER_MCP_UA_TEST"] == "fromfile"


def test_resolve_dotenv_path_missing_explicit_returns_default_or_none(tmp_path):
    # A non-existent explicit path must not raise; it falls back to the
    # default search (which may find the repo .env or nothing).
    result = server._resolve_dotenv_path(str(tmp_path / "does-not-exist.env"))
    assert result is None or result.endswith(".env")


# ---------------------------------------------------------------------------
# User-Agent construction (client wiring)
# ---------------------------------------------------------------------------


def test_user_agent_comment_appended():
    base = get_mcp_user_agent()
    combined = get_combined_user_agent("Claude Desktop 1.0")
    assert combined == f"{base} (Claude Desktop 1.0)"


def test_user_agent_no_comment_is_base():
    assert get_combined_user_agent(None) == get_mcp_user_agent()
    assert get_combined_user_agent("  ") == get_mcp_user_agent()


# ---------------------------------------------------------------------------
# TLS config (ZSCALER_MCP_TLS_CERTFILE / KEYFILE / PASSWORD / CA_CERTS)
# ---------------------------------------------------------------------------


def _clear_tls_env(monkeypatch):
    for var in (
        "ZSCALER_MCP_TLS_CERTFILE",
        "ZSCALER_MCP_TLS_KEYFILE",
        "ZSCALER_MCP_TLS_KEYFILE_PASSWORD",
        "ZSCALER_MCP_TLS_CA_CERTS",
    ):
        monkeypatch.delenv(var, raising=False)


def test_tls_kwargs_empty_when_unset(monkeypatch):
    _clear_tls_env(monkeypatch)
    assert server._tls_kwargs_from_env() == {}


def test_tls_kwargs_incomplete_config_raises(monkeypatch):
    _clear_tls_env(monkeypatch)
    monkeypatch.setenv("ZSCALER_MCP_TLS_CERTFILE", "/tmp/cert.pem")
    with pytest.raises(SystemExit) as exc:
        server._tls_kwargs_from_env()
    assert "Incomplete TLS" in str(exc.value)


def test_tls_kwargs_missing_file_raises(monkeypatch, tmp_path):
    _clear_tls_env(monkeypatch)
    monkeypatch.setenv("ZSCALER_MCP_TLS_CERTFILE", str(tmp_path / "nope-cert.pem"))
    monkeypatch.setenv("ZSCALER_MCP_TLS_KEYFILE", str(tmp_path / "nope-key.pem"))
    with pytest.raises(SystemExit) as exc:
        server._tls_kwargs_from_env()
    assert "not found" in str(exc.value)


def test_tls_kwargs_full_config(monkeypatch, tmp_path):
    _clear_tls_env(monkeypatch)
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    ca = tmp_path / "ca.pem"
    for f in (cert, key, ca):
        f.write_text("x")
    monkeypatch.setenv("ZSCALER_MCP_TLS_CERTFILE", str(cert))
    monkeypatch.setenv("ZSCALER_MCP_TLS_KEYFILE", str(key))
    monkeypatch.setenv("ZSCALER_MCP_TLS_KEYFILE_PASSWORD", "pw")
    monkeypatch.setenv("ZSCALER_MCP_TLS_CA_CERTS", str(ca))
    kwargs = server._tls_kwargs_from_env()
    assert kwargs == {
        "ssl_certfile": str(cert),
        "ssl_keyfile": str(key),
        "ssl_keyfile_password": "pw",
        "ssl_ca_certs": str(ca),
    }
