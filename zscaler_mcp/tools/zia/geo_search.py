from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_geo_search_tool(
    action: Annotated[
        Literal["geo_by_coordinates", "geo_by_ip", "city_prefix_search"],
        Field(
            description="Choose one of: geo_by_coordinates, geo_by_ip, city_prefix_search"
        ),
    ],
    latitude: Annotated[
        Optional[float], Field(description="Required if action is geo_by_coordinates")
    ] = None,
    longitude: Annotated[
        Optional[float], Field(description="Required if action is geo_by_coordinates")
    ] = None,
    ip: Annotated[
        Optional[str], Field(description="Required if action is geo_by_ip")
    ] = None,
    prefix: Annotated[
        Optional[str], Field(description="Required if action is city_prefix_search")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict], str]:
    """
    Performs geographical lookup actions using the ZIA Locations API.

    Supported actions:
    - geo_by_coordinates: Retrieve region or city data from given latitude and longitude.
    - geo_by_ip: Retrieve region or city data for a given IP address.
    - city_prefix_search: Search cities matching a given name prefix.

    Parameters:
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
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    if action == "geo_by_coordinates":
        if latitude is None or longitude is None:
            raise ValueError("Both latitude and longitude must be provided.")
        result, _, err = client.zia.locations.list_region_geo_coordinates(
            latitude, longitude
        )
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
        results, _, err = client.zia.locations.list_cities_by_name(
            query_params={"prefix": prefix}
        )
        if err:
            raise Exception(f"City prefix search failed: {err}")
        return [r.as_dict() for r in results or []]

    else:
        raise ValueError(
            "Invalid action. Must be one of: geo_by_coordinates, geo_by_ip, city_prefix_search"
        )
