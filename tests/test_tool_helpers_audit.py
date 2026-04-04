"""Tests for audit logging, sanitization, and result summarization in tool_helpers."""

import unittest
from unittest.mock import MagicMock, patch

from zscaler_mcp.common.tool_helpers import (
    _sanitize_args,
    _summarize_result,
    _wrap_with_audit,
    enable_tool_call_logging,
    register_read_tools,
    register_write_tools,
)


class TestSanitizeArgs(unittest.TestCase):
    """Test sensitive parameter redaction."""

    def test_redacts_password(self):
        result = _sanitize_args({"password": "hunter2", "name": "test"})
        self.assertEqual(result["password"], "***REDACTED***")
        self.assertEqual(result["name"], "test")

    def test_redacts_secret(self):
        result = _sanitize_args({"client_secret": "abc123"})
        self.assertEqual(result["client_secret"], "***REDACTED***")

    def test_redacts_token(self):
        result = _sanitize_args({"confirmation_token": "tok_xyz"})
        self.assertEqual(result["confirmation_token"], "***REDACTED***")

    def test_redacts_api_key(self):
        result = _sanitize_args({"api_key": "key_123"})
        self.assertEqual(result["api_key"], "***REDACTED***")

    def test_redacts_key_substring_match(self):
        result = _sanitize_args({"my_secret_value": "s3cret"})
        self.assertEqual(result["my_secret_value"], "***REDACTED***")

    def test_skips_none_values(self):
        result = _sanitize_args({"name": "test", "optional": None})
        self.assertNotIn("optional", result)
        self.assertEqual(result["name"], "test")

    def test_preserves_normal_params(self):
        result = _sanitize_args({"name": "fw_rule", "page": 1, "page_size": 50})
        self.assertEqual(result, {"name": "fw_rule", "page": 1, "page_size": 50})

    def test_empty_dict(self):
        self.assertEqual(_sanitize_args({}), {})

    def test_private_key_redacted(self):
        result = _sanitize_args({"private_key": "-----BEGIN RSA"})
        self.assertEqual(result["private_key"], "***REDACTED***")


class TestSummarizeResult(unittest.TestCase):
    """Test compact result summaries for audit logging."""

    def test_list_with_items(self):
        self.assertEqual(_summarize_result([1, 2, 3]), "3 items")

    def test_empty_list(self):
        self.assertEqual(_summarize_result([]), "0 items")

    def test_single_dict_with_error(self):
        result = [{"error": "something went wrong with the API call"}]
        summary = _summarize_result(result)
        self.assertTrue(summary.startswith("error:"))

    def test_single_dict_with_nodes(self):
        result = [{"nodes": [{"id": 1}, {"id": 2}, {"id": 3}]}]
        self.assertEqual(_summarize_result(result), "3 nodes")

    def test_single_dict_no_data_status(self):
        result = [{"status": "no_data"}]
        self.assertEqual(_summarize_result(result), "no data")

    def test_dict_with_error(self):
        result = {"error": "auth failed"}
        summary = _summarize_result(result)
        self.assertTrue(summary.startswith("error:"))

    def test_dict_with_keys(self):
        result = {"a": 1, "b": 2, "c": 3}
        self.assertEqual(_summarize_result(result), "dict (3 keys)")

    def test_non_dict_non_list(self):
        self.assertEqual(_summarize_result("hello"), "str")

    def test_error_truncation(self):
        long_error = "x" * 200
        result = [{"error": long_error}]
        summary = _summarize_result(result)
        self.assertLessEqual(len(summary), 130)


class TestWrapWithAudit(unittest.TestCase):
    """Test the audit logging wrapper."""

    def setUp(self):
        enable_tool_call_logging()

    def test_successful_call_returns_result(self):
        fn = MagicMock(return_value=[{"id": 1}])
        wrapped = _wrap_with_audit(fn, "test_tool")
        result = wrapped(name="test")
        self.assertEqual(result, [{"id": 1}])
        fn.assert_called_once_with(name="test")

    def test_exception_is_reraised(self):
        fn = MagicMock(side_effect=ValueError("boom"))
        wrapped = _wrap_with_audit(fn, "test_tool")
        with self.assertRaises(ValueError):
            wrapped()

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_logs_call_and_result(self, mock_logger):
        fn = MagicMock(return_value=[{"name": "rule1"}])
        wrapped = _wrap_with_audit(fn, "zia_list_rules")
        wrapped(page=1)
        calls = [c[0][0] for c in mock_logger.info.call_args_list]
        self.assertTrue(any("[TOOL CALL]" in c for c in calls))
        self.assertTrue(any("[TOOL OK]" in c for c in calls))

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_logs_error_on_exception(self, mock_logger):
        fn = MagicMock(side_effect=RuntimeError("oops"))
        wrapped = _wrap_with_audit(fn, "zia_delete_rule")
        with self.assertRaises(RuntimeError):
            wrapped()
        error_calls = [c[0][0] for c in mock_logger.error.call_args_list]
        self.assertTrue(any("[TOOL ERR]" in c for c in error_calls))

    @patch("zscaler_mcp.common.tool_helpers._log_tool_calls_enabled", False)
    def test_disabled_logging_bypasses_audit(self):
        fn = MagicMock(return_value="ok")
        wrapped = _wrap_with_audit(fn, "test_tool")
        result = wrapped()
        self.assertEqual(result, "ok")
        fn.assert_called_once()


class TestRegisterWriteToolsEdgeCases(unittest.TestCase):
    """Additional edge cases for write tool registration."""

    def setUp(self):
        self.server = MagicMock()

    def test_write_disabled_returns_zero(self):
        tools = [{"func": MagicMock(), "name": "zpa_create_app", "description": "Create app"}]
        count = register_write_tools(self.server, tools, enable_write_tools=False)
        self.assertEqual(count, 0)
        self.server.add_tool.assert_not_called()

    def test_write_enabled_no_allowlist_returns_zero(self):
        tools = [{"func": MagicMock(), "name": "zpa_create_app", "description": "Create app"}]
        count = register_write_tools(self.server, tools, enable_write_tools=True, write_tools=None)
        self.assertEqual(count, 0)
        self.server.add_tool.assert_not_called()

    def test_write_enabled_empty_allowlist_returns_zero(self):
        tools = [{"func": MagicMock(), "name": "zpa_create_app", "description": "Create app"}]
        count = register_write_tools(self.server, tools, enable_write_tools=True, write_tools=set())
        self.assertEqual(count, 0)

    def test_allowlist_wildcard_matches(self):
        tools = [
            {"func": MagicMock(), "name": "zpa_create_app", "description": "Create"},
            {"func": MagicMock(), "name": "zia_update_rule", "description": "Update"},
        ]
        count = register_write_tools(
            self.server, tools, enable_write_tools=True, write_tools={"zpa_*"}
        )
        self.assertEqual(count, 1)
        registered_name = self.server.add_tool.call_args[1]["name"]
        self.assertEqual(registered_name, "zpa_create_app")

    def test_enabled_tools_filter_with_write(self):
        tools = [
            {"func": MagicMock(), "name": "zpa_create_a", "description": "a"},
            {"func": MagicMock(), "name": "zpa_create_b", "description": "b"},
        ]
        count = register_write_tools(
            self.server, tools,
            enabled_tools={"zpa_create_a"},
            enable_write_tools=True,
            write_tools={"zpa_*"},
        )
        self.assertEqual(count, 1)
        registered_name = self.server.add_tool.call_args[1]["name"]
        self.assertEqual(registered_name, "zpa_create_a")


class TestRegisterReadToolsEdgeCases(unittest.TestCase):
    """Additional edge cases for read tool registration."""

    def setUp(self):
        self.server = MagicMock()

    def test_enabled_tools_filter(self):
        tools = [
            {"func": MagicMock(), "name": "zia_list_a", "description": "a"},
            {"func": MagicMock(), "name": "zia_list_b", "description": "b"},
            {"func": MagicMock(), "name": "zia_list_c", "description": "c"},
        ]
        count = register_read_tools(self.server, tools, enabled_tools={"zia_list_a", "zia_list_c"})
        self.assertEqual(count, 2)
        names = [c[1]["name"] for c in self.server.add_tool.call_args_list]
        self.assertIn("zia_list_a", names)
        self.assertIn("zia_list_c", names)
        self.assertNotIn("zia_list_b", names)

    def test_empty_tools_list(self):
        count = register_read_tools(self.server, [])
        self.assertEqual(count, 0)

    def test_tool_annotations_set_readonly(self):
        tools = [{"func": MagicMock(), "name": "zia_list_x", "description": "x"}]
        register_read_tools(self.server, tools)
        call_kwargs = self.server.add_tool.call_args[1]
        self.assertTrue(call_kwargs["annotations"].readOnlyHint)


if __name__ == "__main__":
    unittest.main()
