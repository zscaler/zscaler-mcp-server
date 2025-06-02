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

from zscaler import ZscalerClient

def get_zscaler_client(
    client_id: str,
    customer_id: str,
    vanity_domain: str,
    client_secret: str = None,
    private_key: str = None,
    cloud: str = None,
) -> ZscalerClient:
    """
    Returns an authenticated ZscalerClient using either clientSecret or privateKey.

    Args:
        client_id (str): OAuth Client ID.
        customer_id (str): Zscaler Customer ID.
        vanity_domain (str): Tenant's vanity domain (e.g., 'mytenant').
        client_secret (str, optional): OAuth client secret for authentication.
        private_key (str, optional): OAuth private key for JWT-based auth.
        cloud (str, optional): Zscaler cloud environment (e.g., 'beta'). Optional.

    Returns:
        ZscalerClient: An authenticated SDK client instance.
    """
    if not client_secret and not private_key:
        raise ValueError("You must provide either client_secret or private_key.")

    if client_secret and private_key:
        raise ValueError("You must provide only one of client_secret or private_key, not both.")

    config = {
        "clientId": client_id,
        "vanityDomain": vanity_domain,
        "customerId": customer_id,
    }

    if cloud:
        config["cloud"] = cloud
    if client_secret:
        config["clientSecret"] = client_secret
    if private_key:
        config["privateKey"] = private_key

    return ZscalerClient(config)
