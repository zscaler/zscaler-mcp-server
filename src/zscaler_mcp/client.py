"""Zscaler SDK client factory.

INTENTIONALLY a near-verbatim carry-over of v1's ``zscaler_mcp/client.py``.

The whole point of the v2 design is that the way we *invoke* Zscaler APIs does
not change — the SDK still owns OneAPI/ZIdentity auth, token refresh, the ZPA
``customer_id`` quirk, pagination, and retries. v2 only changes the SHAPE of
what the agent sees (the shaping layer in ``zscaler_mcp.shaping``), which sits
strictly downstream of this factory.

If you are tempted to hand-roll HTTP here, re-read DESIGN.md §2.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_zscaler_client(*, service: str | None = None):
    """Return an authenticated OneAPI ``ZscalerClient``.

    Credentials are resolved from the environment (or a ``.env`` file):

    - ``ZSCALER_CLIENT_ID``
    - ``ZSCALER_CLIENT_SECRET`` (or ``ZSCALER_PRIVATE_KEY`` for JWT auth)
    - ``ZSCALER_VANITY_DOMAIN``
    - ``ZSCALER_CUSTOMER_ID`` (required only when ``service="zpa"``)
    - ``ZCELL_CUSTOMER_ID`` (required only when ``service="zcell"``)
    - ``ZSCALER_CLOUD`` (optional)

    Args:
        service: Optional product hint (``"zpa"``, ``"zia"``, ...). Only used to
            enforce the per-product customer-id requirements (ZPA's
            ``customer_id`` and ZCell's independent ``zcellCustomerId``); the
            OneAPI client itself is universal.
    """
    load_dotenv()

    # Imported lazily so the scaffold can be inspected / unit-tested (with the
    # SDK call mocked) on a machine that doesn't have the SDK installed yet.
    from zscaler import ZscalerClient  # noqa: PLC0415

    client_id = os.getenv("ZSCALER_CLIENT_ID")
    client_secret = os.getenv("ZSCALER_CLIENT_SECRET")
    private_key = os.getenv("ZSCALER_PRIVATE_KEY")
    vanity_domain = os.getenv("ZSCALER_VANITY_DOMAIN")
    customer_id = os.getenv("ZSCALER_CUSTOMER_ID")
    # ZCell is scoped to /customers/{id} via a DEDICATED customer id that is
    # completely independent from ZPA's customerId (README "Authenticating to
    # Zscaler Cellular"). The SDK resolves it from the `zcellCustomerId` config
    # key OR the ZCELL_CUSTOMER_ID env var; we surface both here so a missing
    # value fails fast with a clear message instead of a cryptic path error.
    zcell_customer_id = os.getenv("ZCELL_CUSTOMER_ID")
    cloud = os.getenv("ZSCALER_CLOUD")
    user_agent_comment = os.getenv("ZSCALER_MCP_USER_AGENT_COMMENT")

    required = {"ZSCALER_CLIENT_ID": client_id, "ZSCALER_VANITY_DOMAIN": vanity_domain}
    if service == "zpa":
        required["ZSCALER_CUSTOMER_ID"] = customer_id
    if service == "zcell":
        required["ZCELL_CUSTOMER_ID"] = zcell_customer_id

    missing = [name for name, value in required.items() if not (value and value.strip())]
    if missing:
        raise RuntimeError(
            "Zscaler SDK failed to initialize due to missing OneAPI credentials: "
            f"{missing}. Set them in the environment or .env file."
        )
    if not client_secret and not private_key:
        raise ValueError(
            "Provide either ZSCALER_CLIENT_SECRET or ZSCALER_PRIVATE_KEY for the OneAPI client."
        )

    from zscaler_mcp.common.utils import get_combined_user_agent  # noqa: PLC0415

    config: dict = {
        "clientId": client_id,
        "vanityDomain": vanity_domain,
        "userAgent": get_combined_user_agent(user_agent_comment),
    }
    if customer_id and customer_id.strip():
        config["customerId"] = customer_id
    if zcell_customer_id and zcell_customer_id.strip():
        config["zcellCustomerId"] = zcell_customer_id
    if cloud:
        config["cloud"] = cloud
    if client_secret:
        config["clientSecret"] = client_secret
    if private_key:
        config["privateKey"] = private_key

    logger.debug("[client] OneAPI client init (service=%s)", service)
    return ZscalerClient(config)
