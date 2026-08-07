"""The identity the server presents once a client connects.

`server/discover` (and the legacy `initialize` result) carry the title,
description, website and icon a client renders. This product already publishes
that identity in two other places — the MCP registry manifest (`server.json`)
and the MCPB bundle (`integrations/anthropic/manifest.json`) — which are
*install-time* metadata. Before this, a user browsing a directory saw a titled,
described, illustrated entry and then connected to a server that announced only
`zscaler-mcp` and a version.

These tests keep the three in step. They are deliberately loose about wording —
the point is that the fields are populated and recognisably the same product,
not that three files share a byte-identical marketing sentence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zscaler_mcp import __version__
from zscaler_mcp.server import (
    SERVER_DESCRIPTION,
    SERVER_ICON_URL,
    SERVER_TITLE,
    SERVER_WEBSITE_URL,
    build_server,
)

_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def server():
    return build_server()


class TestDiscoverMetadata:
    def test_every_presentation_field_is_populated(self, server):
        """A connected client must not see a bare program name."""
        assert server.title == SERVER_TITLE
        assert server.description == SERVER_DESCRIPTION
        assert server.website_url == SERVER_WEBSITE_URL
        assert server.icons, "no icon advertised"
        assert server.icons[0].src == SERVER_ICON_URL

    def test_version_is_the_package_version(self, server):
        """Omitting it reports an empty string, which clients display verbatim."""
        assert server.version == __version__

    def test_the_icon_is_fetchable_over_http_not_a_repo_path(self):
        """Clients resolve this URL themselves; a relative path is unusable."""
        assert SERVER_ICON_URL.startswith("https://")
        assert SERVER_ICON_URL.endswith(".png")

    def test_the_advertised_icon_exists_in_the_repository(self):
        """The URL points at `master`, so the asset has to be committed."""
        assert SERVER_ICON_URL.endswith("/assets/icon.png")
        assert (_ROOT / "assets" / "icon.png").is_file()

    def test_the_description_states_the_safety_posture(self):
        """Read-only-by-default is the single most important thing to convey."""
        lowered = SERVER_DESCRIPTION.lower()
        assert "read-only" in lowered
        assert "zscaler" in lowered


class TestIdentityMatchesTheDistributionManifests:
    """One product, one identity — whichever surface a user meets it on."""

    def test_title_matches_the_mcpb_bundle_name(self):
        manifest = json.loads((_ROOT / "integrations/anthropic/manifest.json").read_text())
        assert manifest["name"] == SERVER_TITLE, (
            "the Claude Desktop directory and a connected client would show "
            "different names for the same server"
        )

    def test_icon_points_at_the_same_asset_the_bundle_ships(self):
        manifest = json.loads((_ROOT / "integrations/anthropic/manifest.json").read_text())
        assert SERVER_ICON_URL.endswith(manifest["icon"]), (
            f"bundle ships {manifest['icon']}, discover advertises {SERVER_ICON_URL}"
        )

    def test_website_matches_the_registry_repository(self):
        registry = json.loads((_ROOT / "server.json").read_text())
        assert SERVER_WEBSITE_URL in json.dumps(registry), (
            "server.json does not reference the URL advertised on server/discover"
        )

    def test_all_three_surfaces_describe_the_same_products(self):
        """A weak but load-bearing check: the descriptions must not diverge."""
        registry = json.loads((_ROOT / "server.json").read_text())
        manifest = json.loads((_ROOT / "integrations/anthropic/manifest.json").read_text())
        for text in (SERVER_DESCRIPTION, registry["description"], manifest["description"]):
            lowered = text.lower()
            assert "zpa" in lowered and "zia" in lowered, f"not recognisably this product: {text}"
