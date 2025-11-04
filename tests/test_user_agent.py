"""
Tests for the User-Agent functionality.
"""

import platform
import sys
import unittest

from zscaler_mcp.utils.utils import get_combined_user_agent


class TestUserAgent(unittest.TestCase):
    """Test cases for User-Agent generation."""

    def test_user_agent_format_without_comment(self):
        """Test the user agent format without comment."""
        user_agent = get_combined_user_agent()
        
        # Verify format components
        parts = user_agent.split()
        self.assertEqual(len(parts), 3, f"Expected 3 parts, got {len(parts)}: {parts}")
        
        # Check format of each part
        self.assertTrue(parts[0].startswith("zscaler-mcp-server/"), 
                       f"Invalid server part: {parts[0]}")
        self.assertTrue(parts[1].startswith("python/"), 
                       f"Invalid python part: {parts[1]}")
        
        # Check OS/arch format
        os_arch = parts[2].split("/")
        self.assertEqual(len(os_arch), 2, f"Invalid OS/arch format: {parts[2]}")
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        self.assertEqual(os_arch[0], system, f"Expected OS {system}, got {os_arch[0]}")
        self.assertEqual(os_arch[1], machine, f"Expected arch {machine}, got {os_arch[1]}")

    def test_user_agent_format_with_comment(self):
        """Test the user agent format with comment."""
        comment = "Claude Desktop 1.2024.10.23"
        user_agent = get_combined_user_agent(comment)
        
        # Verify the comment is appended
        self.assertTrue(user_agent.endswith(comment), 
                       f"Comment not found in user agent: {user_agent}")
        
        # Verify base format is still correct
        base_parts = user_agent.replace(f" {comment}", "").split()
        self.assertEqual(len(base_parts), 3, f"Expected 3 base parts, got {len(base_parts)}")

    def test_user_agent_contains_expected_components(self):
        """Test that the format matches the expected pattern."""
        # Get Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        user_agent = get_combined_user_agent()
        
        # Should contain these components
        self.assertIn(f"python/{python_version}", user_agent, 
                     f"Python version not found in: {user_agent}")
        self.assertIn(f"{system}/{machine}", user_agent, 
                     f"OS/arch not found in: {user_agent}")
        self.assertIn("zscaler-mcp-server/", user_agent, 
                     f"Server name not found in: {user_agent}")

    def test_user_agent_with_empty_comment(self):
        """Test that empty comment doesn't add extra whitespace."""
        user_agent_no_comment = get_combined_user_agent()
        user_agent_empty_comment = get_combined_user_agent("")
        
        # Both should be identical
        self.assertEqual(user_agent_no_comment, user_agent_empty_comment)

    def test_user_agent_with_none_comment(self):
        """Test that None comment doesn't add extra whitespace."""
        user_agent_no_comment = get_combined_user_agent()
        user_agent_none_comment = get_combined_user_agent(None)
        
        # Both should be identical
        self.assertEqual(user_agent_no_comment, user_agent_none_comment)

    def test_user_agent_format_matches_specification(self):
        """Test that the format matches: zscaler-mcp-server/VERSION python/VERSION os/arch"""
        user_agent = get_combined_user_agent()
        
        # Split into parts
        parts = user_agent.split()
        
        # Verify each part has the expected format (key/value)
        for part in parts:
            self.assertIn("/", part, f"Part {part} should contain '/'")
            key, value = part.split("/", 1)
            self.assertTrue(key, f"Key should not be empty in {part}")
            self.assertTrue(value, f"Value should not be empty in {part}")

    def test_user_agent_comment_with_special_characters(self):
        """Test that comment with various characters is handled correctly."""
        comments = [
            "Claude Desktop 1.2024.10.23",
            "AI-Agent/v1.0",
            "MyApp (Build 123)",
            "Test_Agent-2.0.0",
        ]
        
        for comment in comments:
            user_agent = get_combined_user_agent(comment)
            self.assertTrue(user_agent.endswith(comment),
                          f"Comment '{comment}' not properly appended: {user_agent}")


if __name__ == "__main__":
    unittest.main()

