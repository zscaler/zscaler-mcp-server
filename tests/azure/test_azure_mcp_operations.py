"""
Tests for integrations/azure/azure_mcp_operations.py — Azure deployment script.

Covers: .env parsing, credential resolution, CLI parser, state management,
VM setup script generation, client config helpers, and prompt helpers.
All tests run offline without Azure credentials by mocking subprocess / SDK calls.
"""

import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the integrations/azure directory to sys.path so we can import the module
AZURE_DIR = Path(__file__).resolve().parent.parent.parent / "integrations" / "azure"
sys.path.insert(0, str(AZURE_DIR))

import azure_mcp_operations as ops


# ---------------------------------------------------------------------------
# .env parsing
# ---------------------------------------------------------------------------


class TestLoadEnv(unittest.TestCase):
    """Tests for load_env() — .env file parser."""

    def test_basic_key_value(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("FOO=bar\nBAZ=qux\n")
            f.flush()
            env = ops.load_env(Path(f.name))
        self.assertEqual(env, {"FOO": "bar", "BAZ": "qux"})
        os.unlink(f.name)

    def test_quoted_values_stripped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('SINGLE=\'hello\'\nDOUBLE="world"\n')
            f.flush()
            env = ops.load_env(Path(f.name))
        self.assertEqual(env["SINGLE"], "hello")
        self.assertEqual(env["DOUBLE"], "world")
        os.unlink(f.name)

    def test_comments_and_blank_lines_skipped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# comment\n\nKEY=val\n  # indented comment\n")
            f.flush()
            env = ops.load_env(Path(f.name))
        self.assertEqual(env, {"KEY": "val"})
        os.unlink(f.name)

    def test_lines_without_equals_skipped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("NOEQUALS\nGOOD=value\n")
            f.flush()
            env = ops.load_env(Path(f.name))
        self.assertEqual(env, {"GOOD": "value"})
        os.unlink(f.name)

    def test_nonexistent_file(self):
        env = ops.load_env(Path("/tmp/does-not-exist-12345.env"))
        self.assertEqual(env, {})

    def test_value_with_equals_sign(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("URL=https://host?a=1&b=2\n")
            f.flush()
            env = ops.load_env(Path(f.name))
        self.assertEqual(env["URL"], "https://host?a=1&b=2")
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------


class TestResolve(unittest.TestCase):
    """Tests for resolve() — first-non-empty-wins credential lookup."""

    def test_from_env_dict(self):
        env = {"ZSCALER_CLIENT_ID": "from-env"}
        result = ops.resolve(env, "ZSCALER_CLIENT_ID")
        self.assertEqual(result, "from-env")

    def test_fallback_to_second_key(self):
        env = {"FALLBACK_KEY": "found"}
        result = ops.resolve(env, "PRIMARY_KEY", "FALLBACK_KEY")
        self.assertEqual(result, "found")

    @patch.dict(os.environ, {"OS_ENV_KEY": "from-os"})
    def test_fallback_to_os_environ(self):
        result = ops.resolve({}, "OS_ENV_KEY")
        self.assertEqual(result, "from-os")

    def test_returns_empty_when_nothing_found(self):
        result = ops.resolve({}, "MISSING_KEY_1", "MISSING_KEY_2")
        self.assertEqual(result, "")

    def test_skips_whitespace_only_values(self):
        env = {"KEY1": "  ", "KEY2": "actual"}
        result = ops.resolve(env, "KEY1", "KEY2")
        self.assertEqual(result, "actual")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


class TestBuildParser(unittest.TestCase):
    """Tests for build_parser() — CLI argument parsing."""

    def test_deploy_command(self):
        parser = ops.build_parser()
        args = parser.parse_args(["deploy"])
        self.assertEqual(args.operation, "deploy")

    def test_destroy_with_flags(self):
        parser = ops.build_parser()
        args = parser.parse_args(["destroy", "--yes", "--resource-group", "my-rg"])
        self.assertEqual(args.operation, "destroy")
        self.assertTrue(args.yes)
        self.assertEqual(args.resource_group, "my-rg")

    def test_agent_chat_with_message(self):
        parser = ops.build_parser()
        args = parser.parse_args(["agent_chat", "-m", "hello world"])
        self.assertEqual(args.operation, "agent_chat")
        self.assertEqual(args.message, "hello world")

    def test_all_operations_registered(self):
        expected = {
            "deploy", "destroy", "status", "logs", "ssh",
            "agent_create", "agent_status", "agent_chat", "agent_destroy",
        }
        self.assertEqual(set(ops.OPERATIONS.keys()), expected)

    def test_no_operation_shows_help(self):
        parser = ops.build_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.operation)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


class TestStateManagement(unittest.TestCase):
    """Tests for _save_state / _load_state / _clear_state."""

    def setUp(self):
        self._orig = ops.STATE_FILE
        self._tmpdir = tempfile.mkdtemp()
        ops.STATE_FILE = Path(self._tmpdir) / ".test-state.json"

    def tearDown(self):
        if ops.STATE_FILE.exists():
            ops.STATE_FILE.unlink()
        os.rmdir(self._tmpdir)
        ops.STATE_FILE = self._orig

    def test_save_and_load(self):
        data = {"mcp_url": "https://example.com/mcp", "auth_mode": "api-key"}
        ops._save_state(data)
        loaded = ops._load_state()
        self.assertEqual(loaded, data)

    def test_load_when_no_file(self):
        loaded = ops._load_state()
        self.assertEqual(loaded, {})

    def test_clear_state(self):
        ops._save_state({"key": "value"})
        self.assertTrue(ops.STATE_FILE.exists())
        ops._clear_state()
        self.assertFalse(ops.STATE_FILE.exists())

    def test_clear_state_when_no_file(self):
        ops._clear_state()  # Should not raise

    def test_load_corrupted_json(self):
        ops.STATE_FILE.write_text("not valid json {{{", encoding="utf-8")
        loaded = ops._load_state()
        self.assertEqual(loaded, {})


# ---------------------------------------------------------------------------
# VM setup script generation
# ---------------------------------------------------------------------------


class TestGenerateVMSetupScript(unittest.TestCase):
    """Tests for _generate_vm_setup_script()."""

    def _generate(self, **kwargs):
        defaults = {
            "mcp_port": "8000",
            "zscaler_client_id": "cid",
            "zscaler_client_secret": "csecret",
            "zscaler_vanity_domain": "test.zscaler.com",
            "zscaler_customer_id": "custid",
            "zscaler_cloud": "production",
            "auth_mode": "none",
        }
        defaults.update(kwargs)
        return ops._generate_vm_setup_script(**defaults)

    def test_basic_none_auth(self):
        script = self._generate()
        self.assertIn("ZSCALER_CLIENT_ID=", script)
        self.assertIn("ZSCALER_MCP_AUTH_ENABLED=\"false\"", script)
        self.assertIn("zscaler-mcp", script)
        self.assertIn("#!/bin/bash", script)

    def test_oidcproxy_auth(self):
        script = self._generate(
            auth_mode="oidcproxy",
            oidc_domain="login.microsoftonline.com/tenant/v2.0",
            oidc_client_id="oidc-cid",
            oidc_client_secret="oidc-secret",
            oidc_audience="my-audience",
            vm_public_ip="1.2.3.4",
        )
        self.assertIn("OIDCPROXY_CONFIG_URL=", script)
        self.assertIn("login.microsoftonline.com/tenant/v2.0", script)
        self.assertIn("OIDCPROXY_CLIENT_ID=", script)
        self.assertIn("python -c", script)

    def test_jwt_auth(self):
        script = self._generate(
            auth_mode="jwt",
            jwks_uri="https://idp/.well-known/jwks.json",
            jwt_issuer="https://idp/",
            jwt_audience="my-api",
        )
        self.assertIn("ZSCALER_MCP_AUTH_MODE=\"jwt\"", script)
        self.assertIn("ZSCALER_MCP_AUTH_JWKS_URI=", script)

    def test_api_key_auth(self):
        script = self._generate(auth_mode="api-key", api_key="test-key-123")
        self.assertIn("ZSCALER_MCP_AUTH_MODE=\"api-key\"", script)
        self.assertIn("ZSCALER_MCP_AUTH_API_KEY=", script)

    def test_zscaler_auth(self):
        script = self._generate(auth_mode="zscaler")
        self.assertIn("ZSCALER_MCP_AUTH_MODE=\"zscaler\"", script)

    def test_write_tools_included(self):
        script = self._generate(write_enabled="true", write_tools="zpa_*,zia_*")
        self.assertIn("ZSCALER_MCP_WRITE_ENABLED=", script)
        self.assertIn("ZSCALER_MCP_WRITE_TOOLS=", script)

    def test_disabled_tools_and_services(self):
        script = self._generate(disabled_tools="zcc_*", disabled_services="zdx")
        self.assertIn("ZSCALER_MCP_DISABLED_TOOLS=", script)
        self.assertIn("ZSCALER_MCP_DISABLED_SERVICES=", script)


# ---------------------------------------------------------------------------
# Config path helpers
# ---------------------------------------------------------------------------


class TestConfigPaths(unittest.TestCase):
    """Tests for Claude Desktop / Cursor config path resolution."""

    @patch.object(ops, "SYSTEM", "Darwin")
    def test_claude_config_macos(self):
        path = ops._claude_config_path()
        self.assertIn("Claude", str(path))
        self.assertTrue(str(path).endswith("claude_desktop_config.json"))

    @patch.object(ops, "SYSTEM", "Darwin")
    def test_cursor_config_macos(self):
        path = ops._cursor_config_path()
        self.assertIn(".cursor", str(path))
        self.assertTrue(str(path).endswith("mcp.json"))


# ---------------------------------------------------------------------------
# upsert_json_config
# ---------------------------------------------------------------------------


class TestUpsertJsonConfig(unittest.TestCase):
    """Tests for upsert_json_config()."""

    def test_creates_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "config.json"
            ops.upsert_json_config(
                path, lambda c: c.update({"mcpServers": {"test": True}})
            )
            data = json.loads(path.read_text())
            self.assertTrue(data["mcpServers"]["test"])

    def test_merges_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            path.write_text(json.dumps({"existing": True}))
            ops.upsert_json_config(path, lambda c: c.update({"new_key": "val"}))
            data = json.loads(path.read_text())
            self.assertTrue(data["existing"])
            self.assertEqual(data["new_key"], "val")


# ---------------------------------------------------------------------------
# run_az / run_cmd
# ---------------------------------------------------------------------------


class TestRunAz(unittest.TestCase):
    """Tests for run_az() — Azure CLI subprocess wrapper."""

    @patch("subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = ops.run_az(["account", "show"], capture=True)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "az")
        self.assertEqual(cmd[1], "account")

    @patch("subprocess.run")
    def test_failure_exits(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="auth failed"
        )
        with self.assertRaises(SystemExit):
            ops.run_az(["login"], capture=True, check=True)

    @patch("subprocess.run")
    def test_check_false_no_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
        result = ops.run_az(["bad-cmd"], capture=True, check=False)
        self.assertEqual(result.returncode, 1)


# ---------------------------------------------------------------------------
# Integration: OPERATIONS map completeness
# ---------------------------------------------------------------------------


class TestOperationsMap(unittest.TestCase):
    """Verify the OPERATIONS dispatch map is complete and callable."""

    def test_all_values_are_callable(self):
        for name, fn in ops.OPERATIONS.items():
            self.assertTrue(callable(fn), f"{name} is not callable")

    def test_foundry_operations_present(self):
        foundry_ops = {"agent_create", "agent_status", "agent_chat", "agent_destroy"}
        self.assertTrue(foundry_ops.issubset(set(ops.OPERATIONS.keys())))

    def test_infra_operations_present(self):
        infra_ops = {"deploy", "destroy", "status", "logs", "ssh"}
        self.assertTrue(infra_ops.issubset(set(ops.OPERATIONS.keys())))


if __name__ == "__main__":
    unittest.main()
