import logging
import warnings

from zscaler import ZscalerClient
from zscaler.oneapi_client import (
    LegacyZCCClient,
    LegacyZDXClient,
    LegacyZIAClient,
    LegacyZPAClient,
    LegacyZTWClient,
)

from .utils.utils import get_combined_user_agent

# Suppress SyntaxWarnings from the zscaler SDK DLP modules
warnings.filterwarnings("ignore", category=SyntaxWarning, module="zscaler.zia.dlp_dictionary")
warnings.filterwarnings("ignore", category=SyntaxWarning, module="zscaler.zia.dlp_engine")

logger = logging.getLogger(__name__)


def get_zscaler_client(
    client_id: str = None,
    client_secret: str = None,
    customer_id: str = None,
    vanity_domain: str = None,
    private_key: str = None,
    username: str = None,
    password: str = None,
    api_key: str = None,
    key_id: str = None,
    key_secret: str = None,
    secret_key: str = None,
    cloud: str = None,
    service: str = None,  # 'zpa' or 'zia'
    use_legacy: bool = False,
    user_agent_comment: str = None,
):
    import os

    from dotenv import load_dotenv

    load_dotenv()
    
    # Get user agent comment from environment variable if not explicitly provided
    if user_agent_comment is None:
        user_agent_comment = os.getenv("ZSCALER_MCP_USER_AGENT_COMMENT")

    # ✅ Defensive fallback logic
    client_id = (
        client_id if client_id not in [None, ""] else os.getenv("ZSCALER_CLIENT_ID")
    )
    client_secret = (
        client_secret
        if client_secret not in [None, ""]
        else os.getenv("ZSCALER_CLIENT_SECRET")
    )
    customer_id = (
        customer_id
        if customer_id not in [None, ""]
        else os.getenv("ZSCALER_CUSTOMER_ID")
    )
    vanity_domain = (
        vanity_domain
        if vanity_domain not in [None, ""]
        else os.getenv("ZSCALER_VANITY_DOMAIN")
    )
    cloud = cloud if cloud not in [None, ""] else os.getenv("ZSCALER_CLOUD")
    private_key = (
        private_key
        if private_key not in [None, ""]
        else os.getenv("ZSCALER_PRIVATE_KEY")
    )

    # ✅ Environment variable fallback for use_legacy
    # Check environment variable if use_legacy is not explicitly set to True
    if use_legacy is None or use_legacy is False:
        env_use_legacy = os.getenv("ZSCALER_USE_LEGACY", "false").lower() == "true"
        if env_use_legacy:
            use_legacy = True

    # ✅ Environment variable fallback for legacy credentials (only if in legacy mode)
    if use_legacy:
        # ZPA legacy credentials
        client_id = client_id if client_id not in [None, ""] else os.getenv("ZPA_CLIENT_ID")
        client_secret = client_secret if client_secret not in [None, ""] else os.getenv("ZPA_CLIENT_SECRET")
        customer_id = customer_id if customer_id not in [None, ""] else os.getenv("ZPA_CUSTOMER_ID")

        # ZIA legacy credentials
        username = username if username not in [None, ""] else os.getenv("ZIA_USERNAME")
        password = password if password not in [None, ""] else os.getenv("ZIA_PASSWORD")
        api_key = api_key if api_key not in [None, ""] else os.getenv("ZIA_API_KEY")

        # ZTW legacy credentials
        username = username if username not in [None, ""] else os.getenv("ZTW_USERNAME")
        password = password if password not in [None, ""] else os.getenv("ZTW_PASSWORD")
        api_key = api_key if api_key not in [None, ""] else os.getenv("ZTW_API_KEY")

        # ZCC legacy credentials
        api_key = api_key if api_key not in [None, ""] else os.getenv("ZCC_CLIENT_ID")
        secret_key = secret_key if secret_key not in [None, ""] else os.getenv("ZCC_CLIENT_ID")

        # ZDX legacy credentials
        key_id = key_id if key_id not in [None, ""] else os.getenv("ZDX_CLIENT_ID")
        key_secret = key_secret if key_secret not in [None, ""] else os.getenv("ZDX_CLIENT_SECRET")

        # Cloud environment (service-specific)
        if not cloud:
            if service == "zpa":
                cloud = os.getenv("ZPA_CLOUD")
            elif service == "zia":
                cloud = os.getenv("ZIA_CLOUD")
            elif service == "ztw":
                cloud = os.getenv("ZTW_CLOUD")
            elif service == "zdx":
                cloud = os.getenv("ZDX_CLOUD")
            elif service == "zcc":
                cloud = os.getenv("ZCC_CLOUD")

    # Debug logging (only in debug mode)
    logger.debug(f"[DEBUG] use_legacy parameter: {use_legacy}")
    logger.debug(f"[DEBUG] ZSCALER_USE_LEGACY env var: {os.getenv('ZSCALER_USE_LEGACY')}")

    # ✅ Debug logging
    logger.debug("[DEBUG] Final Auth Config:")
    logger.debug(f"  client_id: {bool(client_id)}")
    logger.debug(f"  client_secret: {bool(client_secret)}")
    logger.debug(f"  customer_id: {bool(customer_id)}")
    logger.debug(f"  vanity_domain: {bool(vanity_domain)}")
    logger.debug(f"  cloud: {cloud}")
    logger.debug(f"  use_legacy: {use_legacy}")
    logger.debug(f"  username: {bool(username)}")
    logger.debug(f"  password: {bool(password)}")
    logger.debug(f"  api_key: {bool(api_key)}")
    logger.debug(f"  key_id: {bool(key_id)}")
    logger.debug(f"  key_secret: {bool(key_secret)}")
    logger.debug(f"  secret_key: {bool(secret_key)}")

    """
    Returns an authenticated Zscaler SDK client (OneAPI or Legacy).

    Args:
        client_id (str): OAuth client ID or legacy ZPA client ID.
        client_secret (str): OAuth client secret or legacy ZPA secret.
        customer_id (str): Zscaler customer ID (used in both OneAPI and legacy ZPA).
        vanity_domain (str): Vanity domain (required only for OneAPI clients).
        private_key (str): OAuth private key for OneAPI JWT-based auth.
        username (str): Legacy ZIA username (used only by LegacyZIAClient).
        password (str): Legacy ZIA password (used only by LegacyZIAClient).
        api_key (str): Legacy ZCC AND ZIA API key (used only by LegacyZIAClient, LegacyZCCClient and LegacyZTWClient).
        secret_key (str): Legacy ZCC Secret key (used only by LegacyZCCClient).
        key_id (str): Legacy ZDX Key ID (used only by LegacyZDXClient).
        key_secret (str): Legacy ZDX Secret Key (used only by LegacyZDXClient).
        cloud (str): Zscaler cloud environment (e.g., 'BETA', 'zscalertwo').
        service (str): Required if use_legacy=True. Must be either 'zpa' or 'zia'.
        use_legacy (bool): If True, selects the appropriate legacy client (
                          LegacyZCCClient, LegacyZDXClient, LegacyZPAClient, LegacyZIAClient, LegacyZTWClient).
                          Can also be set via ZSCALER_USE_LEGACY environment variable.
        user_agent_comment (str): Optional additional information to include in the User-Agent header
                                 (e.g., "Claude Desktop 1.2024.10.23"). Can also be set via
                                 ZSCALER_MCP_USER_AGENT_COMMENT environment variable.

    Returns:
        Union[ZscalerClient, LegacyZPAClient, LegacyZIAClient]: An authenticated client instance.

    Notes:
        - If `use_legacy=True`, do **not** set or expect `vanity_domain`. It is required only for OneAPI.
        - Each legacy service requires different credential parameters:
            • LegacyZCCClient: key_id, secret_key, cloud
            • LegacyZDXClient: api_key, key_secret, cloud
            • LegacyZPAClient: client_id, client_secret, customer_id, cloud
            • LegacyZIAClient: username, password, api_key, cloud
            • LegacyZTWClient: username, password, api_key, cloud
            • LegacyZDXClient: key_id, key_secret, cloud
    """

    # Generate custom user-agent for all requests
    custom_user_agent = get_combined_user_agent(user_agent_comment)
    logger.debug(f"[DEBUG] Using custom user-agent: {custom_user_agent}")

    if use_legacy:
        if not service:
            raise ValueError(
                "You must specify the 'service' (e.g., zdx, 'zpa', 'zia', ztw) when using legacy mode."
            )

        if service == "zpa":
            if not all([client_id, client_secret, customer_id, cloud]):
                raise ValueError("Missing required credentials for LegacyZPAClient.")
            config = {
                "clientId": client_id,
                "clientSecret": client_secret,
                "customerId": customer_id,
                "cloud": cloud,
                "userAgent": custom_user_agent,
            }
            return LegacyZPAClient(config)

        elif service == "zcc":
            if not all([api_key, secret_key, cloud]):
                raise ValueError("Missing required credentials for LegacyZCCClient.")
            config = {
                "api_key": api_key,
                "secret_key": secret_key,
                "cloud": cloud,
                "userAgent": custom_user_agent,
            }
            return LegacyZCCClient(config)

        elif service == "zia":
            if not all([username, password, api_key, cloud]):
                raise ValueError("Missing required credentials for LegacyZIAClient.")
            config = {
                "username": username,
                "password": password,
                "api_key": api_key,
                "cloud": cloud,
                "userAgent": custom_user_agent,
            }
            return LegacyZIAClient(config)

        elif service == "ztw":
            if not all([username, password, api_key, cloud]):
                raise ValueError("Missing required credentials for LegacyZTWClient.")
            config = {
                "username": username,
                "password": password,
                "api_key": api_key,
                "cloud": cloud,
                "userAgent": custom_user_agent,
            }
            return LegacyZTWClient(config)

        elif service == "zdx":
            if not all([key_id, key_secret, cloud]):
                raise ValueError("Missing required credentials for LegacyZDXClient.")
            config = {
                "key_id": key_id,
                "key_secret": key_secret,
                "cloud": cloud,
                "userAgent": custom_user_agent,
            }
            return LegacyZDXClient(config)

        else:
            raise ValueError(f"Unsupported legacy service: {service}")

    # Default: OneAPI client
    # ✅ Check for required OneAPI credentials
    auth_fields = {
        "ZSCALER_CLIENT_ID": client_id,
        "ZSCALER_CLIENT_SECRET": client_secret,
        "ZSCALER_CUSTOMER_ID": customer_id,
        "ZSCALER_VANITY_DOMAIN": vanity_domain,
    }

    missing = [
        key for key, value in auth_fields.items() if not (value and value.strip())
    ]
    if missing:
        raise RuntimeError(
            f"Zscaler SDK failed to initialize due to missing configuration values: {missing}. "
            "Please ensure the MCP container has these values set in the environment or .env file."
        )

    if not client_secret and not private_key:
        raise ValueError(
            "You must provide either client_secret or private_key for OneAPI client."
        )

    config = {
        "clientId": client_id,
        "customerId": customer_id,
        "vanityDomain": vanity_domain,
        "userAgent": custom_user_agent,
    }

    if cloud:
        config["cloud"] = cloud
    if client_secret:
        config["clientSecret"] = client_secret
    if private_key:
        config["privateKey"] = private_key

    return ZscalerClient(config)
