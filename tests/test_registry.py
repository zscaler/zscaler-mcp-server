"""
Tests for the service registry.
"""

import unittest
from unittest.mock import MagicMock

from zscaler_mcp import services
from zscaler_mcp.services import BaseService


class TestRegistry(unittest.TestCase):
    """Test cases for the service registry."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Store the original AVAILABLE_SERVICES dictionary
        self.original_services = services._AVAILABLE_SERVICES.copy()  # pylint: disable=protected-access

    def tearDown(self):
        """Clean up after each test method."""
        # Restore the original AVAILABLE_SERVICES dictionary
        services._AVAILABLE_SERVICES = self.original_services.copy()  # pylint: disable=protected-access

    def test_get_service_names(self):
        """Test that get_service_names returns the correct list of service names."""
        # Call get_service_names
        service_names = services.get_service_names()

        # Verify that the returned list contains all the expected service names
        expected_services = {"zcc", "zdx", "zpa", "zia", "zidentity", "ztw"}
        self.assertEqual(set(service_names), expected_services)
        self.assertEqual(len(service_names), 6)

    def test_get_available_services(self):
        """Test that get_available_services returns the correct dictionary of services."""
        # Call get_available_services
        available_services = services.get_available_services()

        # Verify that all expected services are present
        expected_services = {"zcc", "zdx", "zpa", "zia", "zidentity", "ztw"}
        self.assertEqual(set(available_services.keys()), expected_services)

        # Verify that all services are subclasses of BaseService
        for service_class in available_services.values():
            self.assertTrue(issubclass(service_class, BaseService))

    def test_service_registry_content(self):
        """Test that the service registry contains the expected services."""
        # Get the available services
        available_services = services.get_available_services()

        # Verify that all expected services are present
        expected_services = {
            "zcc": services.ZCCService,
            "zdx": services.ZDXService,
            "zpa": services.ZPAService,
            "zia": services.ZIAService,
            "zidentity": services.ZIdentityService,
        }

        for service_name, service_class in expected_services.items():
            self.assertIn(service_name, available_services)
            self.assertEqual(available_services[service_name], service_class)

    def test_service_inheritance(self):
        """Test that all services inherit from BaseService."""
        available_services = services.get_available_services()

        for service_name, service_class in available_services.items():
            self.assertTrue(
                issubclass(service_class, BaseService),
                f"Service {service_name} does not inherit from BaseService"
            )

    def test_service_instantiation(self):
        """Test that all services can be instantiated with a client."""
        available_services = services.get_available_services()
        mock_client = MagicMock()

        for service_name, service_class in available_services.items():
            try:
                # Create an instance of the service
                service_instance = service_class(mock_client)
                self.assertIsInstance(service_instance, BaseService)
                self.assertEqual(service_instance.zscaler_client, mock_client)
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.fail(f"Failed to instantiate {service_name}: {e}")

    def test_service_tools_registration(self):
        """Test that all services have tools and can register them."""
        available_services = services.get_available_services()
        mock_client = MagicMock()
        mock_server = MagicMock()

        for service_name, service_class in available_services.items():
            try:
                # Create an instance of the service
                service_instance = service_class(mock_client)

                # Verify that the service has tools (read or write)
                self.assertIsInstance(service_instance.tools, list)  # Deprecated but kept for compatibility
                self.assertIsInstance(service_instance.read_tools, list)
                self.assertIsInstance(service_instance.write_tools, list)
                # Services should have at least read tools
                self.assertGreater(len(service_instance.read_tools) + len(service_instance.write_tools), 0)

                # Verify that register_tools method exists and can be called
                self.assertTrue(hasattr(service_instance, 'register_tools'))
                service_instance.register_tools(mock_server)

            except Exception as e:  # pylint: disable=broad-exception-caught
                self.fail(f"Failed to test tools registration for {service_name}: {e}")

    def test_service_names_consistency(self):
        """Test that get_service_names and get_available_services return consistent data."""
        service_names = services.get_service_names()
        available_services = services.get_available_services()

        # Verify that both methods return the same set of service names
        self.assertEqual(set(service_names), set(available_services.keys()))

    def test_service_registry_immutability(self):
        """Test that get_available_services returns a copy, not the original dictionary."""
        # Get the available services
        available_services = services.get_available_services()

        # Modify the returned dictionary
        available_services["test_service"] = MagicMock()

        # Get the services again
        available_services_2 = services.get_available_services()

        # Verify that the original registry was not modified
        self.assertNotIn("test_service", available_services_2)
        self.assertEqual(len(available_services_2), 6)  # Should still have 6 services


if __name__ == "__main__":
    unittest.main()
