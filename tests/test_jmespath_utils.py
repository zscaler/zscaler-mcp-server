"""Tests for JMESPath client-side filtering utility."""

import unittest

from zscaler_mcp.common.jmespath_utils import apply_jmespath


class TestApplyJmespath(unittest.TestCase):
    """Test cases for the apply_jmespath function."""

    def setUp(self):
        self.sample_data = [
            {"name": "zia_list_users", "description": "List ZIA users", "service": "zia", "type": "read"},
            {"name": "zia_create_user", "description": "Create a ZIA user", "service": "zia", "type": "write"},
            {"name": "zpa_list_apps", "description": "List ZPA application segments", "service": "zpa", "type": "read"},
            {"name": "zcc_list_devices", "description": "List ZCC devices", "service": "zcc", "type": "read"},
            {"name": "zdx_get_score", "description": "Get ZDX score for an app", "service": "zdx", "type": "read"},
        ]

    def test_none_expression_returns_data_unchanged(self):
        result = apply_jmespath(self.sample_data, None)
        self.assertEqual(result, self.sample_data)

    def test_empty_string_expression_returns_data_unchanged(self):
        result = apply_jmespath(self.sample_data, "")
        self.assertEqual(result, self.sample_data)

    def test_filter_by_service(self):
        result = apply_jmespath(self.sample_data, "[?service == 'zia']")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(item["service"] == "zia" for item in result))

    def test_filter_by_type(self):
        result = apply_jmespath(self.sample_data, "[?type == 'write']")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "zia_create_user")

    def test_contains_filter(self):
        result = apply_jmespath(self.sample_data, "[?contains(name, 'list')]")
        self.assertEqual(len(result), 3)

    def test_projection_returns_list(self):
        result = apply_jmespath(self.sample_data, "[*].name")
        self.assertEqual(len(result), 5)
        self.assertIn("zia_list_users", result)

    def test_no_matches_returns_empty_list(self):
        result = apply_jmespath(self.sample_data, "[?service == 'nonexistent']")
        self.assertEqual(result, [])

    def test_scalar_result_wrapped_in_list(self):
        result = apply_jmespath(self.sample_data, "length(@)")
        self.assertEqual(result, [5])

    def test_invalid_expression_returns_error(self):
        result = apply_jmespath(self.sample_data, "[???invalid")
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIn("Invalid JMESPath expression", result[0]["error"])

    def test_combined_filters(self):
        result = apply_jmespath(self.sample_data, "[?service == 'zia' && type == 'read']")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "zia_list_users")

    def test_dict_input(self):
        data = {"name": "test", "items": [1, 2, 3]}
        result = apply_jmespath(data, "items")
        self.assertEqual(result, [1, 2, 3])

    def test_dict_input_scalar(self):
        data = {"name": "test", "count": 42}
        result = apply_jmespath(data, "name")
        self.assertEqual(result, ["test"])

    def test_null_result_from_expression(self):
        data = {"name": "test"}
        result = apply_jmespath(data, "nonexistent_key")
        self.assertEqual(result, [])

    def test_nested_field_filter(self):
        data = [
            {"name": "user1", "dept": {"name": "Engineering"}},
            {"name": "user2", "dept": {"name": "Sales"}},
            {"name": "user3", "dept": {"name": "Engineering"}},
        ]
        result = apply_jmespath(data, "[?dept.name == 'Engineering']")
        self.assertEqual(len(result), 2)

    def test_starts_with_function(self):
        result = apply_jmespath(self.sample_data, "[?starts_with(name, 'zia_')]")
        self.assertEqual(len(result), 2)

    def test_pipe_expression(self):
        result = apply_jmespath(self.sample_data, "[?type == 'read'] | length(@)")
        self.assertEqual(result, [4])

    def test_empty_list_input(self):
        result = apply_jmespath([], "[?name == 'test']")
        self.assertEqual(result, [])

    def test_multiselect_projection(self):
        result = apply_jmespath(self.sample_data, "[*].{tool: name, svc: service}")
        self.assertEqual(len(result), 5)
        self.assertIn("tool", result[0])
        self.assertIn("svc", result[0])


class TestListToolsReturnTypeContract(unittest.TestCase):
    """Regression: list tools that pipe through apply_jmespath MUST declare
    their return type as ``Any``, not ``List[dict]`` / ``List[str]``.

    Why: JMESPath expressions like ``length(@)`` produce scalar results that
    apply_jmespath wraps as ``[19]`` — a list of int. A strict ``List[dict]``
    annotation causes the MCP/Pydantic output validator to reject the
    response, forcing the AI agent to narrate around the validation error
    and exposing implementation details (JMESPath, validators) to the user.
    """

    import typing as _typing

    def _assert_returns_any(self, fn):
        rt = self._typing.get_type_hints(fn).get("return")
        self.assertIs(
            rt,
            self._typing.Any,
            f"{fn.__module__}.{fn.__name__} return type is {rt!r}; "
            "tools that call apply_jmespath must declare `-> Any` so "
            "JMESPath scalar results (e.g. length(@) -> [19]) are not "
            "rejected by the MCP output validator.",
        )

    def test_zia_list_cloud_firewall_dns_rules_returns_any(self):
        from zscaler_mcp.tools.zia.cloud_firewall_dns_rules import (
            zia_list_cloud_firewall_dns_rules,
        )
        self._assert_returns_any(zia_list_cloud_firewall_dns_rules)

    def test_zia_list_cloud_firewall_ips_rules_returns_any(self):
        from zscaler_mcp.tools.zia.cloud_firewall_ips_rules import (
            zia_list_cloud_firewall_ips_rules,
        )
        self._assert_returns_any(zia_list_cloud_firewall_ips_rules)

    def test_zia_list_file_type_control_rules_returns_any(self):
        from zscaler_mcp.tools.zia.file_type_control_rules import (
            zia_list_file_type_control_rules,
        )
        self._assert_returns_any(zia_list_file_type_control_rules)

    def test_zia_list_file_type_categories_returns_any(self):
        from zscaler_mcp.tools.zia.file_type_control_rules import (
            zia_list_file_type_categories,
        )
        self._assert_returns_any(zia_list_file_type_categories)

    def test_zia_list_sandbox_rules_returns_any(self):
        from zscaler_mcp.tools.zia.sandbox_rules import zia_list_sandbox_rules
        self._assert_returns_any(zia_list_sandbox_rules)


if __name__ == "__main__":
    unittest.main()
