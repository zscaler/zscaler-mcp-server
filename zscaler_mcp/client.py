"""Zscaler SDK client factory (OneAPI).

All Zscaler products are accessed through the unified OneAPI client
(`zscaler.ZscalerClient`), authenticated against ZIdentity using a single set
of credentials:

    - ``ZSCALER_CLIENT_ID``
    - ``ZSCALER_CLIENT_SECRET`` (or ``ZSCALER_PRIVATE_KEY`` for JWT auth)
    - ``ZSCALER_VANITY_DOMAIN``
    - ``ZSCALER_CUSTOMER_ID`` (required when calling ZPA tools)
    - ``ZSCALER_CLOUD`` (optional; defaults to production)
"""

import logging
import os
import warnings

from dotenv import load_dotenv
from zscaler import ZscalerClient

from .utils.utils import get_combined_user_agent

# Suppress SyntaxWarnings emitted by the upstream zscaler SDK DLP modules.
warnings.filterwarnings("ignore", category=SyntaxWarning, module="zscaler.zia.dlp_dictionary")
warnings.filterwarnings("ignore", category=SyntaxWarning, module="zscaler.zia.dlp_engine")

logger = logging.getLogger(__name__)


def _required(value, env_name):
    """Resolve a credential value, falling back to the environment."""
    if value not in (None, ""):
        return value
    return os.getenv(env_name)


def get_zscaler_client(
    *,
    client_id: str = None,
    client_secret: str = None,
    customer_id: str = None,
    vanity_domain: str = None,
    private_key: str = None,
    cloud: str = None,
    service: str = None,
    user_agent_comment: str = None,
) -> ZscalerClient:
    """Return an authenticated OneAPI ZscalerClient.

    Args:
        client_id: OAuth client ID. Falls back to ``ZSCALER_CLIENT_ID``.
        client_secret: OAuth client secret. Falls back to ``ZSCALER_CLIENT_SECRET``.
        customer_id: Zscaler customer/tenant ID. Falls back to ``ZSCALER_CUSTOMER_ID``.
            Required only when ``service="zpa"``.
        vanity_domain: ZIdentity vanity domain. Falls back to ``ZSCALER_VANITY_DOMAIN``.
        private_key: OAuth private key for JWT-based auth (used in place of
            ``client_secret``). Falls back to ``ZSCALER_PRIVATE_KEY``.
        cloud: Zscaler cloud environment override (e.g. ``"BETA"``,
            ``"zscalertwo"``). Falls back to ``ZSCALER_CLOUD``.
        service: Optional service hint used by tool modules to signal which
            Zscaler product they are calling (``"zpa"``, ``"zia"``, ``"zdx"``,
            ``"zcc"``, ``"ztw"``, ``"zid"``, ``"zeasm"``, ``"zins"``,
            ``"zms"``). The OneAPI client itself is universal; this hint is
            only used to enforce the ZPA-specific ``customer_id`` requirement.
        user_agent_comment: Optional suffix appended to the User-Agent header
            (e.g. ``"Claude Desktop 1.2024.10.23"``). Falls back to
            ``ZSCALER_MCP_USER_AGENT_COMMENT``.

    Returns:
        An authenticated :class:`zscaler.ZscalerClient` instance.

    Raises:
        RuntimeError: when one or more required OneAPI credentials are missing.
        ValueError: when neither ``client_secret`` nor ``private_key`` is provided.
    """
    load_dotenv()

    if user_agent_comment is None:
        user_agent_comment = os.getenv("ZSCALER_MCP_USER_AGENT_COMMENT")

    client_id = _required(client_id, "ZSCALER_CLIENT_ID")
    client_secret = _required(client_secret, "ZSCALER_CLIENT_SECRET")
    customer_id = _required(customer_id, "ZSCALER_CUSTOMER_ID")
    vanity_domain = _required(vanity_domain, "ZSCALER_VANITY_DOMAIN")
    cloud = _required(cloud, "ZSCALER_CLOUD")
    private_key = _required(private_key, "ZSCALER_PRIVATE_KEY")

    auth_fields = {
        "ZSCALER_CLIENT_ID": client_id,
        "ZSCALER_VANITY_DOMAIN": vanity_domain,
    }
    if service == "zpa":
        auth_fields["ZSCALER_CUSTOMER_ID"] = customer_id

    missing = [name for name, value in auth_fields.items() if not (value and value.strip())]
    if missing:
        raise RuntimeError(
            "Zscaler SDK failed to initialize due to missing OneAPI credentials: "
            f"{missing}. Set them in the environment or .env file."
        )

    if not client_secret and not private_key:
        raise ValueError(
            "You must provide either ZSCALER_CLIENT_SECRET or ZSCALER_PRIVATE_KEY "
            "for the OneAPI client."
        )

    custom_user_agent = get_combined_user_agent(user_agent_comment)
    logger.debug("[client] OneAPI client init (service=%s, ua=%s)", service, custom_user_agent)

    config = {
        "clientId": client_id,
        "vanityDomain": vanity_domain,
        "userAgent": custom_user_agent,
    }
    if customer_id and customer_id.strip():
        config["customerId"] = customer_id
    if cloud:
        config["cloud"] = cloud
    if client_secret:
        config["clientSecret"] = client_secret
    if private_key:
        config["privateKey"] = private_key

    return ZscalerClient(config)
