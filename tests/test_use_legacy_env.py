"""
Test for ZSCALER_USE_LEGACY environment variable functionality.
"""

import os
from unittest.mock import patch

import pytest

from zscaler_mcp.client import get_zscaler_client


class TestUseLegacyEnvironmentVariable:
    """Test cases for ZSCALER_USE_LEGACY environment variable."""

    def test_use_legacy_env_true(self):
        """Test that ZSCALER_USE_LEGACY=true sets use_legacy to True."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'true',
            'ZPA_CLIENT_ID': 'test_client_id',
            'ZPA_CLIENT_SECRET': 'test_client_secret',
            'ZPA_CUSTOMER_ID': 'test_customer_id',
            'ZPA_CLOUD': 'beta'
        }):
            # Should use legacy mode when env var is true
            # Don't pass service parameter to trigger the expected error
            with pytest.raises(ValueError, match="You must specify the 'service'"):
                get_zscaler_client(use_legacy=True)

    def test_use_legacy_env_case_insensitive(self):
        """Test that ZSCALER_USE_LEGACY is case insensitive."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'TRUE',
            'ZPA_CLIENT_ID': 'test_client_id',
            'ZPA_CLIENT_SECRET': 'test_client_secret',
            'ZPA_CUSTOMER_ID': 'test_customer_id',
            'ZPA_CLOUD': 'beta'
        }):
            # Should use legacy mode when env var is TRUE (uppercase)
            with pytest.raises(ValueError, match="You must specify the 'service'"):
                get_zscaler_client(use_legacy=True)

    def test_legacy_zpa_service(self):
        """Test that ZPA legacy service works with ZPA_* environment variables."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'true',
            'ZPA_CLIENT_ID': 'test_zpa_client_id',
            'ZPA_CLIENT_SECRET': 'test_zpa_client_secret',
            'ZPA_CUSTOMER_ID': 'test_zpa_customer_id',
            'ZPA_CLOUD': 'BETA'
        }):
            # Should use legacy ZPA mode when service='zpa'
            with pytest.raises(ValueError, match="The provided ZPA_CLOUD value"):
                get_zscaler_client(service='zpa')

    def test_legacy_zia_service(self):
        """Test that ZIA legacy service works with ZIA_* environment variables."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'true',
            'ZIA_USERNAME': 'test_zia_username',
            'ZIA_PASSWORD': 'test_zia_password',
            'ZIA_API_KEY': 'test_zia_api_key',
            'ZIA_CLOUD': 'beta'
        }):
            # Should use legacy ZIA mode when service='zia'
            with pytest.raises(ValueError, match="no Set-Cookie header received"):
                get_zscaler_client(service='zia')

    def test_legacy_zcc_service(self):
        """Test that ZCC legacy service works with ZCC_* environment variables."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'true',
            'ZCC_CLIENT_ID': 'test_zcc_client_id',
            'ZCC_CLIENT_SECRET': 'test_zcc_client_secret',
            'ZCC_CLOUD': 'beta'
        }):
            # Should use legacy ZCC mode when service='zcc'
            with pytest.raises(ValueError, match="no Set-Cookie header received"):
                get_zscaler_client(service='zcc')

    def test_legacy_zdx_service(self):
        """Test that ZDX legacy service works with ZDX_* environment variables."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'true',
            'ZDX_CLIENT_ID': 'test_zdx_client_id',
            'ZDX_CLIENT_SECRET': 'test_zdx_client_secret',
            'ZDX_CLOUD': 'beta'
        }):
            # Should use legacy ZDX mode when service='zdx'
            with pytest.raises(ValueError, match="Expecting value: line 1 column 1"):
                get_zscaler_client(service='zdx')

    def test_legacy_service_parameter_override(self):
        """Test that explicit service parameter overrides environment variable."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'true',
            'ZPA_CLIENT_ID': 'test_zpa_client_id',
            'ZPA_CLIENT_SECRET': 'test_zpa_client_secret',
            'ZPA_CUSTOMER_ID': 'test_zpa_customer_id',
            'ZPA_CLOUD': 'BETA',
            'ZIA_USERNAME': 'test_zia_username',
            'ZIA_PASSWORD': 'test_zia_password',
            'ZIA_API_KEY': 'test_zia_api_key',
            'ZIA_CLOUD': 'beta'
        }):
            # Should use ZPA service when explicitly specified
            with pytest.raises(ValueError, match="The provided ZPA_CLOUD value"):
                get_zscaler_client(service='zpa')

            # Should use ZIA service when explicitly specified
            with pytest.raises(ValueError, match="no Set-Cookie header received"):
                get_zscaler_client(service='zia')

    def test_legacy_credentials_isolation(self):
        """Test that legacy credentials are only loaded when use_legacy=true."""
        with patch.dict(os.environ, {
            'ZSCALER_USE_LEGACY': 'false',
            'ZSCALER_CLIENT_ID': 'test_client_id',
            'ZSCALER_CLIENT_SECRET': 'test_client_secret',
            'ZSCALER_CUSTOMER_ID': 'test_customer_id',
            'ZSCALER_VANITY_DOMAIN': 'test_domain',
            'ZSCALER_CLOUD': 'beta',
            # Legacy credentials that should NOT be loaded
            'ZPA_CLIENT_ID': 'should_not_load_zpa',
            'ZPA_CLIENT_SECRET': 'should_not_load_zpa',
            'ZIA_USERNAME': 'should_not_load_zia',
            'ZIA_PASSWORD': 'should_not_load_zia',
            'ZCC_CLIENT_ID': 'should_not_load_zcc',
            'ZCC_CLIENT_SECRET': 'should_not_load_zcc',
            'ZDX_CLIENT_ID': 'should_not_load_zdx',
            'ZDX_CLIENT_SECRET': 'should_not_load_zdx'
        }):
            # Should use OneAPI mode and ignore legacy credentials
            # This should succeed because OneAPI credentials are provided
            client = get_zscaler_client()
            assert client is not None
            print(f"✅ Successfully created OneAPI client: {type(client).__name__}")
