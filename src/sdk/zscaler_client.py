# from zscaler import ZscalerClient

# def get_zscaler_client(
#     client_id: str,
#     customer_id: str,
#     vanity_domain: str,
#     client_secret: str = None,
#     private_key: str = None,
#     cloud: str = None,
# ) -> ZscalerClient:
#     """
#     Returns an authenticated ZscalerClient using either clientSecret or privateKey.

#     Args:
#         client_id (str): OAuth Client ID.
#         customer_id (str): Zscaler Customer ID.
#         vanity_domain (str): Tenant's vanity domain (e.g., 'mytenant').
#         client_secret (str, optional): OAuth client secret for authentication.
#         private_key (str, optional): OAuth private key for JWT-based auth.
#         cloud (str, optional): Zscaler cloud environment (e.g., 'beta'). Optional.

#     Returns:
#         ZscalerClient: An authenticated SDK client instance.
#     """
#     if not client_secret and not private_key:
#         raise ValueError("You must provide either client_secret or private_key.")

#     if client_secret and private_key:
#         raise ValueError("You must provide only one of client_secret or private_key, not both.")

#     config = {
#         "clientId": client_id,
#         "vanityDomain": vanity_domain,
#         "customerId": customer_id,
#     }

#     if cloud:
#         config["cloud"] = cloud
#     if client_secret:
#         config["clientSecret"] = client_secret
#     if private_key:
#         config["privateKey"] = private_key

#     return ZscalerClient(config)

# src/sdk/zpa_client.py

from zscaler import ZscalerClient
from zscaler.oneapi_client import (
            LegacyZPAClient,
            LegacyZIAClient,
            LegacyZDXClient
    )


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
    cloud: str = None,
    service: str = None,  # 'zpa' or 'zia'
    use_legacy: bool = False,
):
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
        api_key (str): Legacy ZIA API key (used only by LegacyZIAClient).
        cloud (str): Zscaler cloud environment (e.g., 'BETA', 'zscalertwo').
        service (str): Required if use_legacy=True. Must be either 'zpa' or 'zia'.
        use_legacy (bool): If True, selects the appropriate legacy client (LegacyZPAClient or LegacyZIAClient).

    Returns:
        Union[ZscalerClient, LegacyZPAClient, LegacyZIAClient]: An authenticated client instance.

    Notes:
        - If `use_legacy=True`, do **not** set or expect `vanity_domain`. It is required only for OneAPI.
        - Each legacy service requires different credential parameters:
            • LegacyZPAClient: client_id, client_secret, customer_id, cloud
            • LegacyZIAClient: username, password, api_key, cloud
            • LegacyZDXClient: key_id, key_secret, cloud
    """

    if use_legacy:
        if not service:
            raise ValueError("You must specify the 'service' (e.g., zdx, 'zpa', 'zia') when using legacy mode.")

        if service == "zpa":
            if not all([client_id, client_secret, customer_id, cloud]):
                raise ValueError("Missing required credentials for LegacyZPAClient.")
            config = {
                "clientId": client_id,
                "clientSecret": client_secret,
                "customerId": customer_id,
                "cloud": cloud,
            }
            return LegacyZPAClient(config)

        elif service == "zia":
            if not all([username, password, api_key, cloud]):
                raise ValueError("Missing required credentials for LegacyZIAClient.")
            config = {
                "username": username,
                "password": password,
                "api_key": api_key,
                "cloud": cloud,
            }
            return LegacyZIAClient(config)

        elif service == "zdx":
            if not all([key_id, key_secret]):
                raise ValueError("Missing required credentials for LegacyZDXClient.")
            config = {
                "key_id": key_id,
                "key_secret": key_secret,
                # "cloud": cloud,
            }
            return LegacyZDXClient(config)

        else:
            raise ValueError(f"Unsupported legacy service: {service}")

    # Default: OneAPI client
    if not client_secret and not private_key:
        raise ValueError("You must provide either client_secret or private_key for OneAPI client.")

    config = {
        "clientId": client_id,
        "customerId": customer_id,
        "vanityDomain": vanity_domain,
    }

    if cloud:
        config["cloud"] = cloud
    if client_secret:
        config["clientSecret"] = client_secret
    if private_key:
        config["privateKey"] = private_key

    return ZscalerClient(config)
