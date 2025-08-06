"""
E2E tests for the ZPA module.
"""

import json
import unittest

import pytest

from tests.e2e.utils.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
class TestZPAModuleE2E(BaseE2ETest):
    """
    End-to-end test suite for the Zscaler MCP Server ZPA Module.
    """

    def test_get_app_segments(self):
        """Verify the agent can retrieve application segments."""

        async def test_logic():
            fixtures = [
                {
                    "operation": "app_segments",
                    "validator": lambda kwargs: True,
                    "response": {
                        "status_code": 200,
                        "body": {
                            "segments": [
                                {
                                    "id": "seg-001",
                                    "name": "Web Applications",
                                    "description": "Web-based applications",
                                    "status": "Active",
                                    "type": "WEB"
                                },
                                {
                                    "id": "seg-002",
                                    "name": "Database Applications",
                                    "description": "Database servers",
                                    "status": "Active",
                                    "type": "DB"
                                },
                                {
                                    "id": "seg-003",
                                    "name": "File Sharing",
                                    "description": "File sharing applications",
                                    "status": "Active",
                                    "type": "FILE"
                                }
                            ]
                        }
                    },
                },
            ]

            self._mock_api_instance.app_segments.side_effect = (
                self._create_mock_api_side_effect(fixtures)
            )

            prompt = "List all application segments and their types"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            self.assertGreaterEqual(len(tools), 1, "Expected at least 1 tool call")
            
            # Check that the result contains information about app segments
            result_lower = result.lower()
            self.assertTrue(
                "web applications" in result_lower or "database applications" in result_lower,
                f"Expected app segment names in result: {result}"
            )

        self.run_test_with_retries(
            "test_get_app_segments",
            test_logic,
            assertions,
        )

    def test_get_server_groups(self):
        """Verify the agent can retrieve server groups."""

        async def test_logic():
            fixtures = [
                {
                    "operation": "server_groups",
                    "validator": lambda kwargs: True,
                    "response": {
                        "status_code": 200,
                        "body": {
                            "server_groups": [
                                {
                                    "id": "sg-001",
                                    "name": "Production Servers",
                                    "description": "Production environment servers",
                                    "status": "Active",
                                    "server_count": 5
                                },
                                {
                                    "id": "sg-002",
                                    "name": "Development Servers",
                                    "description": "Development environment servers",
                                    "status": "Active",
                                    "server_count": 3
                                }
                            ]
                        }
                    },
                },
            ]

            self._mock_api_instance.server_groups.side_effect = (
                self._create_mock_api_side_effect(fixtures)
            )

            prompt = "Show me the server groups and their server counts"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            self.assertGreaterEqual(len(tools), 1, "Expected at least 1 tool call")
            
            # Check that the result contains information about server groups
            result_lower = result.lower()
            self.assertTrue(
                "production servers" in result_lower or "development servers" in result_lower,
                f"Expected server group names in result: {result}"
            )

        self.run_test_with_retries(
            "test_get_server_groups",
            test_logic,
            assertions,
        )

    def test_get_app_connector_groups(self):
        """Verify the agent can retrieve app connector groups."""

        async def test_logic():
            fixtures = [
                {
                    "operation": "app_connector_groups",
                    "validator": lambda kwargs: True,
                    "response": {
                        "status_code": 200,
                        "body": {
                            "app_connector_groups": [
                                {
                                    "id": "acg-001",
                                    "name": "Primary Connectors",
                                    "description": "Primary app connector group",
                                    "status": "Active",
                                    "connector_count": 2
                                },
                                {
                                    "id": "acg-002",
                                    "name": "Secondary Connectors",
                                    "description": "Secondary app connector group",
                                    "status": "Active",
                                    "connector_count": 1
                                }
                            ]
                        }
                    },
                },
            ]

            self._mock_api_instance.app_connector_groups.side_effect = (
                self._create_mock_api_side_effect(fixtures)
            )

            prompt = "List all app connector groups"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            self.assertGreaterEqual(len(tools), 1, "Expected at least 1 tool call")
            
            # Check that the result contains information about app connector groups
            result_lower = result.lower()
            self.assertTrue(
                "primary connectors" in result_lower or "secondary connectors" in result_lower,
                f"Expected app connector group names in result: {result}"
            )

        self.run_test_with_retries(
            "test_get_app_connector_groups",
            test_logic,
            assertions,
        )


if __name__ == "__main__":
    unittest.main() 