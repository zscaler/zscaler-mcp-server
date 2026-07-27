"""ZIA geo lookups — read-only manager.

Mirrors v1's ``geo_search.py`` exactly: a single multiplexed read tool registered
under the v1 name ``zia_geo_search`` (geo-by-coordinates, geo-by-IP, or city prefix
search, selected via ``action``). Backed by ``client.zia.locations``.

The geo records are returned exactly as the ZIA API provides them, instead
of the raw SDK dict, to keep token usage low. Single-result actions return a
single-item list.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class GeoSearchInput(BaseModel):
    """Inputs for ZIA geo lookups.

    ``action`` selects the lookup: ``geo_by_coordinates`` (needs lat/lon),
    ``geo_by_ip`` (needs ip), or ``city_prefix_search`` (needs prefix).
    """

    action: Annotated[
        Literal["geo_by_coordinates", "geo_by_ip", "city_prefix_search"],
        Field(description="Lookup to perform."),
    ]
    latitude: Annotated[
        Optional[float], Field(default=None, description="Latitude (geo_by_coordinates).")
    ] = None
    longitude: Annotated[
        Optional[float], Field(default=None, description="Longitude (geo_by_coordinates).")
    ] = None
    ip: Annotated[Optional[str], Field(default=None, description="IP address (geo_by_ip).")] = None
    prefix: Annotated[
        Optional[str], Field(default=None, description="City/region prefix (city_prefix_search).")
    ] = None


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GeoSearchInput,
    is_list=True,
)
def zia_geo_search(args: GeoSearchInput) -> list[dict[str, Any]]:
    """Resolve ZIA geo data by coordinates, by IP, or by city prefix (read-only)."""
    client = get_zscaler_client(service="zia")
    locations = client.zia.locations

    if args.action == "geo_by_coordinates":
        if args.latitude is None or args.longitude is None:
            raise ValueError("Both latitude and longitude must be provided.")
        result, _, err = locations.list_region_geo_coordinates(args.latitude, args.longitude)
        if err:
            raise RuntimeError(f"Geo lookup by coordinates failed: {err}")
        return shape_many([result.as_dict()])

    if args.action == "geo_by_ip":
        if not args.ip:
            raise ValueError("An IP address must be provided.")
        result, _, err = locations.get_geo_by_ip(args.ip)
        if err:
            raise RuntimeError(f"Geo lookup by IP failed: {err}")
        return shape_many([result.as_dict()])

    if not args.prefix:
        raise ValueError("A city prefix must be provided.")
    results, _, err = locations.list_cities_by_name(query_params={"prefix": args.prefix})
    if err:
        raise RuntimeError(f"City prefix search failed: {err}")
    return shape_many([r.as_dict() for r in (results or [])])
