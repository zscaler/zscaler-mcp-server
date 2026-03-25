"""Tests for disabled_tools support in tool_helpers."""

import unittest
from unittest.mock import MagicMock

from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools


def _make_tools(*names):
    """Build tool definition dicts for testing."""
    return [
        {"func": MagicMock(name=n), "name": n, "description": f"desc-{n}"}
        for n in names
    ]


class TestRegisterReadToolsDisabled(unittest.TestCase):
    """Test disabled_tools filtering in register_read_tools."""

    def setUp(self):
        self.server = MagicMock()

    def test_no_disabled_tools_registers_all(self):
        tools = _make_tools("zcc_list_devices", "zpa_list_apps")
        count = register_read_tools(self.server, tools)
        self.assertEqual(count, 2)
        self.assertEqual(self.server.add_tool.call_count, 2)

    def test_exact_name_excluded(self):
        tools = _make_tools("zcc_devices_csv_exporter", "zcc_list_devices")
        count = register_read_tools(
            self.server, tools, disabled_tools={"zcc_devices_csv_exporter"}
        )
        self.assertEqual(count, 1)
        registered_name = self.server.add_tool.call_args[1]["name"]
        self.assertEqual(registered_name, "zcc_list_devices")

    def test_wildcard_excludes_matching(self):
        tools = _make_tools("zcc_list_devices", "zcc_export_data", "zpa_list_apps")
        count = register_read_tools(self.server, tools, disabled_tools={"zcc_*"})
        self.assertEqual(count, 1)
        registered_name = self.server.add_tool.call_args[1]["name"]
        self.assertEqual(registered_name, "zpa_list_apps")

    def test_multiple_patterns(self):
        tools = _make_tools("zcc_a", "zdx_b", "zpa_c", "zia_d")
        count = register_read_tools(
            self.server, tools, disabled_tools={"zcc_*", "zdx_*"}
        )
        self.assertEqual(count, 2)
        registered_names = [
            call[1]["name"] for call in self.server.add_tool.call_args_list
        ]
        self.assertEqual(sorted(registered_names), ["zia_d", "zpa_c"])

    def test_disabled_tools_applied_after_enabled_tools(self):
        tools = _make_tools("zpa_a", "zpa_b", "zia_c")
        count = register_read_tools(
            self.server,
            tools,
            enabled_tools={"zpa_a", "zpa_b"},
            disabled_tools={"zpa_b"},
        )
        self.assertEqual(count, 1)
        registered_name = self.server.add_tool.call_args[1]["name"]
        self.assertEqual(registered_name, "zpa_a")

    def test_disabled_all_results_in_zero(self):
        tools = _make_tools("zcc_a", "zcc_b")
        count = register_read_tools(self.server, tools, disabled_tools={"zcc_*"})
        self.assertEqual(count, 0)
        self.server.add_tool.assert_not_called()

    def test_non_matching_pattern_excludes_nothing(self):
        tools = _make_tools("zpa_a", "zpa_b")
        count = register_read_tools(self.server, tools, disabled_tools={"zzz_*"})
        self.assertEqual(count, 2)


class TestRegisterWriteToolsDisabled(unittest.TestCase):
    """Test disabled_tools filtering in register_write_tools."""

    def setUp(self):
        self.server = MagicMock()

    def test_exact_name_excluded(self):
        tools = _make_tools("zpa_create_seg", "zpa_delete_seg")
        count = register_write_tools(
            self.server,
            tools,
            enable_write_tools=True,
            write_tools={"zpa_*"},
            disabled_tools={"zpa_delete_seg"},
        )
        self.assertEqual(count, 1)
        registered_name = self.server.add_tool.call_args[1]["name"]
        self.assertEqual(registered_name, "zpa_create_seg")

    def test_wildcard_excludes_matching(self):
        tools = _make_tools("zcc_create_a", "zpa_create_b")
        count = register_write_tools(
            self.server,
            tools,
            enable_write_tools=True,
            write_tools={"*"},
            disabled_tools={"zcc_*"},
        )
        self.assertEqual(count, 1)
        registered_name = self.server.add_tool.call_args[1]["name"]
        self.assertEqual(registered_name, "zpa_create_b")

    def test_disabled_applied_before_allowlist_check(self):
        """Disabled tools are skipped before the write allowlist is checked."""
        tools = _make_tools("zpa_create_seg")
        count = register_write_tools(
            self.server,
            tools,
            enable_write_tools=True,
            write_tools={"zpa_*"},
            disabled_tools={"zpa_create_seg"},
        )
        self.assertEqual(count, 0)
        self.server.add_tool.assert_not_called()

    def test_write_disabled_still_skips_all(self):
        tools = _make_tools("zpa_create_seg")
        count = register_write_tools(
            self.server,
            tools,
            enable_write_tools=False,
            disabled_tools={"zpa_create_seg"},
        )
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
