from src.sdk.zscaler_client import get_zscaler_client
from typing import Union, Literal, Annotated, Optional
import json

def zia_geo_search_tool(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    username: str,
    password: str,
    api_key: str,
    action: Annotated[
        Literal["geo_by_coordinates", "geo_by_ip", "city_prefix_search"],
        "Choose one of: geo_by_coordinates, geo_by_ip, city_prefix_search"
    ],
    use_legacy: bool = False,
    service: str = "zia",
    latitude: Annotated[
        Optional[float],
        "Required if action is geo_by_coordinates"
    ] = None,
    longitude: Annotated[
        Optional[float],
        "Required if action is geo_by_coordinates"
    ] = None,
    ip: Annotated[
        Optional[str],
        "Required if action is geo_by_ip"
    ] = None,
    prefix: Annotated[
        Optional[str],
        "Required if action is city_prefix_search"
    ] = None,
) -> Union[dict, list[dict], str]:
    """
    Performs geographical lookup actions using the ZIA Locations API.

    Supported actions:
    - geo_by_coordinates: Retrieve region or city data from given latitude and longitude.
    - geo_by_ip: Retrieve region or city data for a given IP address.
    - city_prefix_search: Search cities matching a given name prefix.

    Parameters:
        cloud (str): ZIA cloud (e.g., 'beta', 'zscalerthree').
        client_id (str): OAuth2 client ID.
        client_secret (str): OAuth2 client secret.
        customer_id (str): ZIA customer ID.
        vanity_domain (str): Vanity domain (e.g., 'mycompany').
        action (str): One of 'geo_by_coordinates', 'geo_by_ip', 'city_prefix_search'.
        latitude (float, optional): Latitude for geo_by_coordinates.
        longitude (float, optional): Longitude for geo_by_coordinates.
        ip (str, optional): IP address for geo_by_ip.
        prefix (str, optional): City or region name prefix for city_prefix_search.

    Returns:
        dict or list[dict]: Region or city data from ZIA Locations API.

    Examples:
        - Retrieve coordinates from lat/lon:
            action="geo_by_coordinates", latitude=49.2827, longitude=-123.1207

        - Lookup city from IP address:
            action="geo_by_ip", ip="8.8.8.8"

        - List all cities starting with 'Vancouver':
            action="city_prefix_search", prefix="Vancouver"

    Notes:
        - If city_prefix_search returns a large number of results, ensure your prefix is specific to reduce latency.
        - The returned objects are flattened using `.as_dict()` for compatibility with JSON serialization.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        username=username,
        password=password,
        api_key=api_key,
        use_legacy=use_legacy,
        service=service,
    )

    if action == "geo_by_coordinates":
        if latitude is None or longitude is None:
            raise ValueError("Both latitude and longitude must be provided.")
        result, _, err = client.zia.locations.list_region_geo_coordinates(latitude, longitude)
        if err:
            raise Exception(f"Geo lookup by coordinates failed: {err}")
        return result.as_dict()

    elif action == "geo_by_ip":
        if not ip:
            raise ValueError("An IP address must be provided.")
        result, _, err = client.zia.locations.get_geo_by_ip(ip)
        if err:
            raise Exception(f"Geo lookup by IP failed: {err}")
        return result.as_dict()

    elif action == "city_prefix_search":
        if not prefix:
            raise ValueError("A city prefix must be provided.")
        results, _, err = client.zia.locations.list_cities_by_name(query_params={"prefix": prefix})
        if err:
            raise Exception(f"City prefix search failed: {err}")
        return [r.as_dict() for r in results or []]

    else:
        raise ValueError("Invalid action. Must be one of: geo_by_coordinates, geo_by_ip, city_prefix_search")
