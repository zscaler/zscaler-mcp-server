"""
Tests for client.py - Zscaler SDK client factory.

Covers: OneAPI client creation, all legacy service clients (ZPA, ZIA, ZCC, ZDX, ZTW),
env var fallbacks, use_legacy auto-detection, credential validation, cloud resolution,
user-agent handling, and error paths.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from zscaler_mcp.client import get_zscaler_client


# Suppress SDK import noise during tests
@patch("dotenv.load_dotenv")
class TestGetZscalerClientOneAPI(unittest.TestCase):
    """Tests for the default OneAPI client path."""

    @patch("zscaler_mcp.client.ZscalerClient")
    def test_oneapi_with_client_secret(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client(
            client_id="cid",
            client_secret="csecret",
            vanity_domain="example.zscaler.com",
        )
        mock_client_cls.assert_called_once()
        config = mock_client_cls.call_args[0][0]
        self.assertEqual(config["clientId"], "cid")
        self.assertEqual(config["clientSecret"], "csecret")
        self.assertEqual(config["vanityDomain"], "example.zscaler.com")
        self.assertNotIn("privateKey", config)

    @patch("zscaler_mcp.client.ZscalerClient")
    def test_oneapi_with_private_key(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client(
            client_id="cid",
            client_secret="csecret",
            private_key="pk123",
            vanity_domain="example.zscaler.com",
        )
        config = mock_client_cls.call_args[0][0]
        self.assertEqual(config["privateKey"], "pk123")
        self.assertEqual(config["clientSecret"], "csecret")

    @patch("zscaler_mcp.client.ZscalerClient")
    def test_oneapi_with_customer_id_and_cloud(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client(
            client_id="cid",
            client_secret="csecret",
            customer_id="custid",
            vanity_domain="example.zscaler.com",
            cloud="beta",
        )
        config = mock_client_cls.call_args[0][0]
        self.assertEqual(config["customerId"], "custid")
        self.assertEqual(config["cloud"], "beta")

    @patch("zscaler_mcp.client.ZscalerClient")
    def test_oneapi_zpa_requires_customer_id(self, mock_client_cls, _dotenv):
        with self.assertRaises(RuntimeError) as ctx:
            get_zscaler_client(
                client_id="cid",
                client_secret="csecret",
                vanity_domain="example.zscaler.com",
                service="zpa",
            )
        self.assertIn("ZSCALER_CUSTOMER_ID", str(ctx.exception))

    def test_oneapi_missing_client_id_raises(self, _dotenv):
        with self.assertRaises(RuntimeError) as ctx:
            get_zscaler_client(
                client_secret="csecret",
                vanity_domain="example.zscaler.com",
            )
        self.assertIn("ZSCALER_CLIENT_ID", str(ctx.exception))

    def test_oneapi_missing_vanity_domain_raises(self, _dotenv):
        with self.assertRaises(RuntimeError) as ctx:
            get_zscaler_client(
                client_id="cid",
                client_secret="csecret",
            )
        self.assertIn("ZSCALER_VANITY_DOMAIN", str(ctx.exception))

    def test_oneapi_missing_both_secret_and_key_raises(self, _dotenv):
        with self.assertRaises(RuntimeError):
            get_zscaler_client(
                client_id="cid",
                vanity_domain="example.zscaler.com",
            )

    @patch("zscaler_mcp.client.ZscalerClient")
    def test_oneapi_no_customer_id_omitted(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client(
            client_id="cid",
            client_secret="csecret",
            vanity_domain="example.zscaler.com",
        )
        config = mock_client_cls.call_args[0][0]
        self.assertNotIn("customerId", config)

    @patch("zscaler_mcp.client.ZscalerClient")
    def test_oneapi_no_cloud_omitted(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client(
            client_id="cid",
            client_secret="csecret",
            vanity_domain="example.zscaler.com",
        )
        config = mock_client_cls.call_args[0][0]
        self.assertNotIn("cloud", config)


@patch("dotenv.load_dotenv")
class TestGetZscalerClientLegacyZPA(unittest.TestCase):
    """Tests for Legacy ZPA client path."""

    @patch("zscaler_mcp.client.LegacyZPAClient")
    def test_legacy_zpa_success(self, mock_zpa, _dotenv):
        mock_zpa.return_value = MagicMock()
        get_zscaler_client(
            client_id="cid",
            client_secret="csecret",
            customer_id="custid",
            cloud="PRODUCTION",
            service="zpa",
            use_legacy=True,
        )
        mock_zpa.assert_called_once()
        config = mock_zpa.call_args[0][0]
        self.assertEqual(config["clientId"], "cid")
        self.assertEqual(config["clientSecret"], "csecret")
        self.assertEqual(config["customerId"], "custid")
        self.assertEqual(config["cloud"], "PRODUCTION")

    def test_legacy_zpa_missing_creds_raises(self, _dotenv):
        with self.assertRaises(ValueError) as ctx:
            get_zscaler_client(
                client_id="cid",
                service="zpa",
                use_legacy=True,
            )
        self.assertIn("LegacyZPAClient", str(ctx.exception))


@patch("dotenv.load_dotenv")
class TestGetZscalerClientLegacyZIA(unittest.TestCase):
    """Tests for Legacy ZIA client path."""

    @patch("zscaler_mcp.client.LegacyZIAClient")
    def test_legacy_zia_success(self, mock_zia, _dotenv):
        mock_zia.return_value = MagicMock()
        get_zscaler_client(
            username="user@zia.com",
            password="pass",
            api_key="apikey",
            cloud="zscalertwo",
            service="zia",
            use_legacy=True,
        )
        mock_zia.assert_called_once()
        config = mock_zia.call_args[0][0]
        self.assertEqual(config["username"], "user@zia.com")
        self.assertEqual(config["password"], "pass")
        self.assertEqual(config["api_key"], "apikey")

    def test_legacy_zia_missing_creds_raises(self, _dotenv):
        with self.assertRaises(ValueError) as ctx:
            get_zscaler_client(
                username="user@zia.com",
                service="zia",
                use_legacy=True,
            )
        self.assertIn("LegacyZIAClient", str(ctx.exception))


@patch("dotenv.load_dotenv")
class TestGetZscalerClientLegacyZCC(unittest.TestCase):
    """Tests for Legacy ZCC client path."""

    @patch("zscaler_mcp.client.LegacyZCCClient")
    @patch.dict(os.environ, {"ZCC_CLIENT_ID": "zcc_key", "ZCC_CLIENT_SECRET": "zcc_secret"})
    def test_legacy_zcc_success(self, mock_zcc, _dotenv):
        mock_zcc.return_value = MagicMock()
        get_zscaler_client(
            cloud="PRODUCTION",
            service="zcc",
            use_legacy=True,
        )
        mock_zcc.assert_called_once()
        config = mock_zcc.call_args[0][0]
        self.assertEqual(config["api_key"], "zcc_key")
        self.assertEqual(config["secret_key"], "zcc_secret")

    def test_legacy_zcc_missing_creds_raises(self, _dotenv):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                get_zscaler_client(
                    service="zcc",
                    use_legacy=True,
                )
            self.assertIn("LegacyZCCClient", str(ctx.exception))


@patch("dotenv.load_dotenv")
class TestGetZscalerClientLegacyZTW(unittest.TestCase):
    """Tests for Legacy ZTW client path."""

    @patch("zscaler_mcp.client.LegacyZTWClient")
    def test_legacy_ztw_success(self, mock_ztw, _dotenv):
        mock_ztw.return_value = MagicMock()
        get_zscaler_client(
            username="user@ztw.com",
            password="pass",
            api_key="apikey",
            cloud="zscalerone",
            service="ztw",
            use_legacy=True,
        )
        mock_ztw.assert_called_once()
        config = mock_ztw.call_args[0][0]
        self.assertEqual(config["username"], "user@ztw.com")

    def test_legacy_ztw_missing_creds_raises(self, _dotenv):
        with self.assertRaises(ValueError) as ctx:
            get_zscaler_client(
                username="user",
                service="ztw",
                use_legacy=True,
            )
        self.assertIn("LegacyZTWClient", str(ctx.exception))


@patch("dotenv.load_dotenv")
class TestGetZscalerClientLegacyZDX(unittest.TestCase):
    """Tests for Legacy ZDX client path."""

    @patch("zscaler_mcp.client.LegacyZDXClient")
    def test_legacy_zdx_success(self, mock_zdx, _dotenv):
        mock_zdx.return_value = MagicMock()
        get_zscaler_client(
            key_id="kid",
            key_secret="ksecret",
            cloud="PRODUCTION",
            service="zdx",
            use_legacy=True,
        )
        mock_zdx.assert_called_once()
        config = mock_zdx.call_args[0][0]
        self.assertEqual(config["key_id"], "kid")
        self.assertEqual(config["key_secret"], "ksecret")

    def test_legacy_zdx_missing_creds_raises(self, _dotenv):
        with self.assertRaises(ValueError) as ctx:
            get_zscaler_client(
                key_id="kid",
                service="zdx",
                use_legacy=True,
            )
        self.assertIn("LegacyZDXClient", str(ctx.exception))


@patch("dotenv.load_dotenv")
class TestGetZscalerClientLegacyErrors(unittest.TestCase):
    """Tests for legacy mode error paths."""

    def test_legacy_no_service_raises(self, _dotenv):
        with self.assertRaises(ValueError) as ctx:
            get_zscaler_client(use_legacy=True)
        self.assertIn("service", str(ctx.exception))

    def test_legacy_unsupported_service_raises(self, _dotenv):
        with self.assertRaises(ValueError) as ctx:
            get_zscaler_client(
                service="nonexistent",
                use_legacy=True,
            )
        self.assertIn("Unsupported legacy service", str(ctx.exception))


@patch("dotenv.load_dotenv")
class TestEnvVarFallbacks(unittest.TestCase):
    """Tests for environment variable fallback logic."""

    @patch("zscaler_mcp.client.ZscalerClient")
    @patch.dict(
        os.environ,
        {
            "ZSCALER_CLIENT_ID": "env_cid",
            "ZSCALER_CLIENT_SECRET": "env_csecret",
            "ZSCALER_VANITY_DOMAIN": "env.zscaler.com",
            "ZSCALER_CLOUD": "beta",
        },
        clear=True,
    )
    def test_falls_back_to_env_vars(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client()
        config = mock_client_cls.call_args[0][0]
        self.assertEqual(config["clientId"], "env_cid")
        self.assertEqual(config["clientSecret"], "env_csecret")
        self.assertEqual(config["vanityDomain"], "env.zscaler.com")
        self.assertEqual(config["cloud"], "beta")

    @patch("zscaler_mcp.client.ZscalerClient")
    @patch.dict(
        os.environ,
        {
            "ZSCALER_CLIENT_ID": "env_cid",
            "ZSCALER_CLIENT_SECRET": "env_csecret",
            "ZSCALER_VANITY_DOMAIN": "env.zscaler.com",
            "ZSCALER_MCP_USER_AGENT_COMMENT": "TestAgent/1.0",
        },
        clear=True,
    )
    def test_user_agent_from_env(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client()
        config = mock_client_cls.call_args[0][0]
        self.assertIn("userAgent", config)

    @patch("zscaler_mcp.client.ZscalerClient")
    @patch.dict(
        os.environ,
        {
            "ZSCALER_CLIENT_ID": "env_cid",
            "ZSCALER_CLIENT_SECRET": "env_csecret",
            "ZSCALER_VANITY_DOMAIN": "env.zscaler.com",
        },
        clear=True,
    )
    def test_explicit_params_override_env(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client(
            client_id="override_cid",
            client_secret="override_csecret",
            vanity_domain="override.zscaler.com",
        )
        config = mock_client_cls.call_args[0][0]
        self.assertEqual(config["clientId"], "override_cid")
        self.assertEqual(config["clientSecret"], "override_csecret")
        self.assertEqual(config["vanityDomain"], "override.zscaler.com")


@patch("dotenv.load_dotenv")
class TestUseLegacyAutoDetection(unittest.TestCase):
    """Tests for ZSCALER_USE_LEGACY env var auto-detection."""

    @patch("zscaler_mcp.client.LegacyZPAClient")
    @patch.dict(
        os.environ,
        {
            "ZSCALER_USE_LEGACY": "true",
            "ZPA_CLIENT_ID": "zpa_cid",
            "ZPA_CLIENT_SECRET": "zpa_csecret",
            "ZPA_CUSTOMER_ID": "zpa_custid",
            "ZPA_CLOUD": "PRODUCTION",
        },
        clear=True,
    )
    def test_use_legacy_from_env_var(self, mock_zpa, _dotenv):
        mock_zpa.return_value = MagicMock()
        get_zscaler_client(service="zpa")
        mock_zpa.assert_called_once()

    @patch("zscaler_mcp.client.ZscalerClient")
    @patch.dict(
        os.environ,
        {
            "ZSCALER_USE_LEGACY": "false",
            "ZSCALER_CLIENT_ID": "cid",
            "ZSCALER_CLIENT_SECRET": "csecret",
            "ZSCALER_VANITY_DOMAIN": "v.zscaler.com",
        },
        clear=True,
    )
    def test_use_legacy_false_uses_oneapi(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client()
        mock_client_cls.assert_called_once()


@patch("dotenv.load_dotenv")
class TestLegacyCloudResolution(unittest.TestCase):
    """Tests for service-specific cloud env var resolution in legacy mode."""

    @patch("zscaler_mcp.client.LegacyZPAClient")
    @patch.dict(
        os.environ,
        {"ZPA_CLOUD": "ZPA_CLOUD_VAL"},
        clear=True,
    )
    def test_zpa_cloud_from_env(self, mock_zpa, _dotenv):
        mock_zpa.return_value = MagicMock()
        get_zscaler_client(
            client_id="cid",
            client_secret="csecret",
            customer_id="custid",
            service="zpa",
            use_legacy=True,
        )
        config = mock_zpa.call_args[0][0]
        self.assertEqual(config["cloud"], "ZPA_CLOUD_VAL")

    @patch("zscaler_mcp.client.LegacyZIAClient")
    @patch.dict(
        os.environ,
        {"ZIA_CLOUD": "ZIA_CLOUD_VAL"},
        clear=True,
    )
    def test_zia_cloud_from_env(self, mock_zia, _dotenv):
        mock_zia.return_value = MagicMock()
        get_zscaler_client(
            username="user",
            password="pass",
            api_key="key",
            service="zia",
            use_legacy=True,
        )
        config = mock_zia.call_args[0][0]
        self.assertEqual(config["cloud"], "ZIA_CLOUD_VAL")

    @patch("zscaler_mcp.client.LegacyZTWClient")
    @patch.dict(
        os.environ,
        {"ZTW_CLOUD": "ZTW_CLOUD_VAL"},
        clear=True,
    )
    def test_ztw_cloud_from_env(self, mock_ztw, _dotenv):
        mock_ztw.return_value = MagicMock()
        get_zscaler_client(
            username="user",
            password="pass",
            api_key="key",
            service="ztw",
            use_legacy=True,
        )
        config = mock_ztw.call_args[0][0]
        self.assertEqual(config["cloud"], "ZTW_CLOUD_VAL")

    @patch("zscaler_mcp.client.LegacyZDXClient")
    @patch.dict(
        os.environ,
        {"ZDX_CLOUD": "ZDX_CLOUD_VAL"},
        clear=True,
    )
    def test_zdx_cloud_from_env(self, mock_zdx, _dotenv):
        mock_zdx.return_value = MagicMock()
        get_zscaler_client(
            key_id="kid",
            key_secret="ksecret",
            service="zdx",
            use_legacy=True,
        )
        config = mock_zdx.call_args[0][0]
        self.assertEqual(config["cloud"], "ZDX_CLOUD_VAL")

    @patch("zscaler_mcp.client.LegacyZCCClient")
    @patch.dict(
        os.environ,
        {"ZCC_CLOUD": "ZCC_CLOUD_VAL", "ZCC_CLIENT_ID": "zcc_key", "ZCC_CLIENT_SECRET": "zcc_sec"},
        clear=True,
    )
    def test_zcc_cloud_from_env(self, mock_zcc, _dotenv):
        mock_zcc.return_value = MagicMock()
        get_zscaler_client(
            service="zcc",
            use_legacy=True,
        )
        config = mock_zcc.call_args[0][0]
        self.assertEqual(config["cloud"], "ZCC_CLOUD_VAL")


@patch("dotenv.load_dotenv")
class TestLegacyCredentialFallbacks(unittest.TestCase):
    """Tests for legacy credential env var fallbacks."""

    @patch("zscaler_mcp.client.LegacyZPAClient")
    @patch.dict(
        os.environ,
        {
            "ZPA_CLIENT_ID": "env_zpa_cid",
            "ZPA_CLIENT_SECRET": "env_zpa_csec",
            "ZPA_CUSTOMER_ID": "env_zpa_custid",
            "ZPA_CLOUD": "PRODUCTION",
        },
        clear=True,
    )
    def test_zpa_creds_from_env(self, mock_zpa, _dotenv):
        mock_zpa.return_value = MagicMock()
        get_zscaler_client(service="zpa", use_legacy=True)
        config = mock_zpa.call_args[0][0]
        self.assertEqual(config["clientId"], "env_zpa_cid")
        self.assertEqual(config["clientSecret"], "env_zpa_csec")
        self.assertEqual(config["customerId"], "env_zpa_custid")

    @patch("zscaler_mcp.client.LegacyZIAClient")
    @patch.dict(
        os.environ,
        {
            "ZIA_USERNAME": "env_zia_user",
            "ZIA_PASSWORD": "env_zia_pass",
            "ZIA_API_KEY": "env_zia_key",
            "ZIA_CLOUD": "zscalertwo",
        },
        clear=True,
    )
    def test_zia_creds_from_env(self, mock_zia, _dotenv):
        mock_zia.return_value = MagicMock()
        get_zscaler_client(service="zia", use_legacy=True)
        config = mock_zia.call_args[0][0]
        self.assertEqual(config["username"], "env_zia_user")
        self.assertEqual(config["password"], "env_zia_pass")
        self.assertEqual(config["api_key"], "env_zia_key")

    @patch("zscaler_mcp.client.LegacyZDXClient")
    @patch.dict(
        os.environ,
        {
            "ZDX_CLIENT_ID": "env_zdx_kid",
            "ZDX_CLIENT_SECRET": "env_zdx_ksec",
            "ZDX_CLOUD": "PRODUCTION",
        },
        clear=True,
    )
    def test_zdx_creds_from_env(self, mock_zdx, _dotenv):
        mock_zdx.return_value = MagicMock()
        get_zscaler_client(service="zdx", use_legacy=True)
        config = mock_zdx.call_args[0][0]
        self.assertEqual(config["key_id"], "env_zdx_kid")
        self.assertEqual(config["key_secret"], "env_zdx_ksec")


@patch("dotenv.load_dotenv")
class TestPrivateKeyPath(unittest.TestCase):
    """Tests for private_key env var fallback."""

    @patch("zscaler_mcp.client.ZscalerClient")
    @patch.dict(
        os.environ,
        {
            "ZSCALER_CLIENT_ID": "cid",
            "ZSCALER_CLIENT_SECRET": "csecret",
            "ZSCALER_PRIVATE_KEY": "env_pk",
            "ZSCALER_VANITY_DOMAIN": "v.zscaler.com",
        },
        clear=True,
    )
    def test_private_key_from_env(self, mock_client_cls, _dotenv):
        mock_client_cls.return_value = MagicMock()
        get_zscaler_client()
        config = mock_client_cls.call_args[0][0]
        self.assertEqual(config["privateKey"], "env_pk")


if __name__ == "__main__":
    unittest.main()
