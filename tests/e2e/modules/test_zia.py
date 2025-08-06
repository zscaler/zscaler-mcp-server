"""
E2E tests for the ZIA module.
"""

import json
import unittest

import pytest

from tests.e2e.utils.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
class TestZIAModuleE2E(BaseE2ETest):
    """
    End-to-end test suite for the Zscaler MCP Server ZIA Module.
    """



    def test_get_cloud_applications(self):
        """Verify the agent can retrieve cloud applications."""

        async def test_logic():
            fixtures = [
                {
                    "operation": "cloud_applications",
                    "validator": lambda kwargs: True,
                    "response": {
                        "status_code": 200,
                        "body": {
                            "applications": [
                                {
                                    "id": "app-001",
                                    "name": "Salesforce",
                                    "category": "Business",
                                    "risk_level": "Low",
                                    "status": "Active"
                                },
                                {
                                    "id": "app-002", 
                                    "name": "Slack",
                                    "category": "Communication",
                                    "risk_level": "Medium",
                                    "status": "Active"
                                },
                                {
                                    "id": "app-003",
                                    "name": "GitHub",
                                    "category": "Development",
                                    "risk_level": "Medium",
                                    "status": "Active"
                                }
                            ]
                        }
                    },
                },
            ]

            self._mock_api_instance.cloud_applications.side_effect = (
                self._create_mock_api_side_effect(fixtures)
            )

            prompt = "List all cloud applications and their risk levels"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            self.assertGreaterEqual(len(tools), 1, "Expected at least 1 tool call")
            
            # Check that the result contains information about cloud applications
            result_lower = result.lower()
            self.assertTrue(
                "salesforce" in result_lower or "slack" in result_lower or "github" in result_lower,
                f"Expected cloud application names in result: {result}"
            )

        self.run_test_with_retries(
            "test_get_cloud_applications",
            test_logic,
            assertions,
        )

    def test_get_url_categories(self):
        """Verify the agent can retrieve URL categories."""

        async def test_logic():
            fixtures = [
                {
                    "operation": "url_categories",
                    "validator": lambda kwargs: True,
                    "response": {
                        "status_code": 200,
                        "body": {
                            "categories": [
                                {
                                    "id": "cat-001",
                                    "name": "Social Media",
                                    "description": "Social networking sites",
                                    "status": "Active"
                                },
                                {
                                    "id": "cat-002",
                                    "name": "News",
                                    "description": "News and media websites",
                                    "status": "Active"
                                },
                                {
                                    "id": "cat-003",
                                    "name": "Shopping",
                                    "description": "E-commerce websites",
                                    "status": "Active"
                                }
                            ]
                        }
                    },
                },
            ]

            self._mock_api_instance.url_categories.side_effect = (
                self._create_mock_api_side_effect(fixtures)
            )

            prompt = "Show me the URL categories and their descriptions"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            self.assertGreaterEqual(len(tools), 1, "Expected at least 1 tool call")
            
            # Check that the result contains information about URL categories
            result_lower = result.lower()
            self.assertTrue(
                "social media" in result_lower or "news" in result_lower or "shopping" in result_lower,
                f"Expected URL category names in result: {result}"
            )

        self.run_test_with_retries(
            "test_get_url_categories",
            test_logic,
            assertions,
        )

    def test_get_static_ips(self):
        """Verify the agent can retrieve static IPs."""

        async def test_logic():
            fixtures = [
                {
                    "operation": "static_ips",
                    "validator": lambda kwargs: True,
                    "response": {
                        "status_code": 200,
                        "body": {
                            "static_ips": [
                                {
                                    "id": "ip-001",
                                    "ip_address": "192.168.1.100",
                                    "description": "Web server",
                                    "status": "Active"
                                },
                                {
                                    "id": "ip-002",
                                    "ip_address": "10.0.0.50",
                                    "description": "Database server",
                                    "status": "Active"
                                }
                            ]
                        }
                    },
                },
            ]

            self._mock_api_instance.static_ips.side_effect = (
                self._create_mock_api_side_effect(fixtures)
            )

            prompt = "List all static IPs and their descriptions"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            self.assertGreaterEqual(len(tools), 1, "Expected at least 1 tool call")
            
            # Check that the result contains information about static IPs
            result_lower = result.lower()
            self.assertTrue(
                "192.168.1.100" in result_lower or "10.0.0.50" in result_lower,
                f"Expected static IP addresses in result: {result}"
            )

        self.run_test_with_retries(
            "test_get_static_ips",
            test_logic,
            assertions,
        )


if __name__ == "__main__":
    unittest.main() 