"""
Unit tests for ZPA (Zscaler Private Access) tools.

Covers: app_segments, segment_groups, server_groups, app_connector_groups,
app_connectors, application_servers, ba_certificate, service_edge_groups,
provisioning_key, pra_portal, pra_credential, access policy rules,
forwarding rules, timeout rules, isolation rules, app protection rules,
and getter/manager tools.
"""

from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_client():
    """Create a mock Zscaler client with ZPA API stubs."""
    client = MagicMock()
    client.zpa.application_segment = MagicMock()
    client.zpa.segment_groups = MagicMock()
    client.zpa.server_groups = MagicMock()
    client.zpa.app_connector_groups = MagicMock()
    client.zpa.app_connectors = MagicMock()
    client.zpa.servers = MagicMock()
    client.zpa.certificates = MagicMock()
    client.zpa.service_edge_group = MagicMock()
    client.zpa.provisioning = MagicMock()
    client.zpa.pra_portal = MagicMock()
    client.zpa.pra_credential = MagicMock()
    client.zpa.policies = MagicMock()
    client.zpa.posture_profiles = MagicMock()
    client.zpa.trusted_networks = MagicMock()
    client.zpa.idp = MagicMock()
    client.zpa.saml_attributes = MagicMock()
    client.zpa.scim_attributes = MagicMock()
    client.zpa.scim_groups = MagicMock()
    client.zpa.app_segment_by_type = MagicMock()
    client.zpa.enrollment_certificates = MagicMock()
    client.zpa.cbi_profile = MagicMock()
    client.zpa.app_protection = MagicMock()
    return client


def _mock_obj(data: dict):
    """Create a mock SDK object with as_dict()."""
    obj = MagicMock()
    obj.as_dict.return_value = data
    return obj


# ============================================================================
# APPLICATION SEGMENTS
# ============================================================================


class TestZpaAppSegments:

    @patch("zscaler_mcp.tools.zpa.app_segments.get_zscaler_client")
    def test_list_application_segments(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_segments import zpa_list_application_segments

        segs = [_mock_obj({"id": f"seg{i}", "name": f"App {i}"}) for i in range(3)]
        mock_client.zpa.application_segment.list_segments.return_value = (segs, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_application_segments()
        assert len(result) == 3
        assert result[0]["name"] == "App 0"

    @patch("zscaler_mcp.tools.zpa.app_segments.get_zscaler_client")
    def test_list_application_segments_with_search(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_segments import zpa_list_application_segments

        mock_client.zpa.application_segment.list_segments.return_value = ([], None, None)
        mock_get_client.return_value = mock_client

        zpa_list_application_segments(search="web", page=1, page_size=10)
        call_kwargs = mock_client.zpa.application_segment.list_segments.call_args[1]
        assert call_kwargs["query_params"]["search"] == "web"

    @patch("zscaler_mcp.tools.zpa.app_segments.get_zscaler_client")
    def test_list_application_segments_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_segments import zpa_list_application_segments

        mock_client.zpa.application_segment.list_segments.return_value = (None, None, "API Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_application_segments()

    @patch("zscaler_mcp.tools.zpa.app_segments.get_zscaler_client")
    def test_get_application_segment(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_segments import zpa_get_application_segment

        seg = _mock_obj({"id": "seg1", "name": "WebApp"})
        mock_client.zpa.application_segment.get_segment.return_value = (seg, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_application_segment(segment_id="seg1")
        assert result["id"] == "seg1"

    @patch("zscaler_mcp.tools.zpa.app_segments.get_zscaler_client")
    def test_get_application_segment_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_segments import zpa_get_application_segment

        mock_client.zpa.application_segment.get_segment.return_value = (None, None, "Not Found")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_get_application_segment(segment_id="bad")

    @patch("zscaler_mcp.tools.zpa.app_segments.get_zscaler_client")
    def test_create_application_segment(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_segments import zpa_create_application_segment

        created = _mock_obj({"id": "new1", "name": "NewApp"})
        mock_client.zpa.application_segment.add_segment.return_value = (created, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_create_application_segment(
            name="NewApp", segment_group_id="sg1", domain_names=["app.example.com"],
            tcp_port_ranges=["443", "443"],
        )
        assert result["id"] == "new1"


# ============================================================================
# SEGMENT GROUPS
# ============================================================================


class TestZpaSegmentGroups:

    @patch("zscaler_mcp.tools.zpa.segment_groups.get_zscaler_client")
    def test_list_segment_groups(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.segment_groups import zpa_list_segment_groups

        groups = [_mock_obj({"id": f"g{i}", "name": f"Group {i}"}) for i in range(2)]
        mock_client.zpa.segment_groups.list_groups.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_segment_groups()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.segment_groups.get_zscaler_client")
    def test_get_segment_group(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.segment_groups import zpa_get_segment_group

        group = _mock_obj({"id": "g1", "name": "Main"})
        mock_client.zpa.segment_groups.get_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_segment_group(group_id="g1")
        assert result["name"] == "Main"

    @patch("zscaler_mcp.tools.zpa.segment_groups.get_zscaler_client")
    def test_create_segment_group(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.segment_groups import zpa_create_segment_group

        created = _mock_obj({"id": "g2", "name": "NewGroup"})
        mock_client.zpa.segment_groups.add_group.return_value = (created, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_create_segment_group(name="NewGroup")
        assert result["id"] == "g2"

    @patch("zscaler_mcp.tools.zpa.segment_groups.get_zscaler_client")
    def test_list_segment_groups_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.segment_groups import zpa_list_segment_groups

        mock_client.zpa.segment_groups.list_groups.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_segment_groups()


# ============================================================================
# SERVER GROUPS
# ============================================================================


class TestZpaServerGroups:

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_list_server_groups(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.server_groups import zpa_list_server_groups

        groups = [_mock_obj({"id": f"sg{i}", "name": f"SG {i}"}) for i in range(2)]
        mock_client.zpa.server_groups.list_groups.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_server_groups()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_get_server_group(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.server_groups import zpa_get_server_group

        group = _mock_obj({"id": "sg1", "name": "Prod Servers"})
        mock_client.zpa.server_groups.get_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_server_group(group_id="sg1")
        assert result["name"] == "Prod Servers"

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_create_server_group(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.server_groups import zpa_create_server_group

        created = _mock_obj({"id": "sg2", "name": "NewSG"})
        mock_client.zpa.server_groups.add_group.return_value = (created, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_create_server_group(name="NewSG", app_connector_group_ids=["acg1"])
        assert result["id"] == "sg2"
        kwargs = mock_client.zpa.server_groups.add_group.call_args.kwargs
        assert kwargs["dynamic_discovery"] is True
        assert kwargs["app_connector_group_ids"] == ["acg1"]
        assert "server_ids" not in kwargs

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_create_server_group_rejects_empty_connector_groups(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.server_groups import zpa_create_server_group

        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="app_connector_group_ids is required"):
            zpa_create_server_group(name="NewSG", app_connector_group_ids=[])

        mock_client.zpa.server_groups.add_group.assert_not_called()

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_create_server_group_dynamic_discovery_false_requires_server_ids(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.server_groups import zpa_create_server_group

        mock_get_client.return_value = mock_client

        with pytest.raises(
            ValueError, match="dynamic_discovery=False requires server_ids"
        ):
            zpa_create_server_group(
                name="StaticSG",
                app_connector_group_ids=["acg1"],
                dynamic_discovery=False,
            )

        mock_client.zpa.server_groups.add_group.assert_not_called()

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_create_server_group_dynamic_discovery_false_with_server_ids_succeeds(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.server_groups import zpa_create_server_group

        mock_client.zpa.server_groups.add_group.return_value = (
            _mock_obj({"id": "sg-static", "name": "StaticSG"}),
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        zpa_create_server_group(
            name="StaticSG",
            app_connector_group_ids=["acg1"],
            dynamic_discovery=False,
            server_ids=["srv-1", "srv-2"],
        )

        kwargs = mock_client.zpa.server_groups.add_group.call_args.kwargs
        assert kwargs["dynamic_discovery"] is False
        assert kwargs["server_ids"] == ["srv-1", "srv-2"]

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_update_server_group_partial_does_not_clobber_lists(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.server_groups import zpa_update_server_group

        mock_client.zpa.server_groups.update_group.return_value = (
            _mock_obj({"id": "sg9"}),
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        zpa_update_server_group(group_id="sg9", description="renamed")

        kwargs = mock_client.zpa.server_groups.update_group.call_args.kwargs
        assert kwargs == {"description": "renamed"}
        assert "app_connector_group_ids" not in kwargs
        assert "server_ids" not in kwargs
        assert "dynamic_discovery" not in kwargs

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_update_server_group_rejects_empty_connector_groups(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.server_groups import zpa_update_server_group

        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="cannot be set to an empty list"):
            zpa_update_server_group(group_id="sg9", app_connector_group_ids=[])

        mock_client.zpa.server_groups.update_group.assert_not_called()

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_update_server_group_dyn_disc_false_with_no_existing_servers_raises(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.server_groups import zpa_update_server_group

        existing = _mock_obj({"id": "sg9", "servers": []})
        existing.servers = []
        mock_client.zpa.server_groups.get_group.return_value = (existing, None, None)
        mock_get_client.return_value = mock_client

        with pytest.raises(
            ValueError, match="dynamic_discovery=False requires server_ids"
        ):
            zpa_update_server_group(group_id="sg9", dynamic_discovery=False)

        mock_client.zpa.server_groups.update_group.assert_not_called()

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_update_server_group_dyn_disc_false_when_existing_has_servers_succeeds(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.server_groups import zpa_update_server_group

        existing = _mock_obj({"id": "sg9", "servers": [{"id": "srv-1"}]})
        existing.servers = [{"id": "srv-1"}]
        mock_client.zpa.server_groups.get_group.return_value = (existing, None, None)
        mock_client.zpa.server_groups.update_group.return_value = (
            _mock_obj({"id": "sg9"}),
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        zpa_update_server_group(group_id="sg9", dynamic_discovery=False)

        kwargs = mock_client.zpa.server_groups.update_group.call_args.kwargs
        assert kwargs["dynamic_discovery"] is False
        assert "server_ids" not in kwargs

    @patch("zscaler_mcp.tools.zpa.server_groups.get_zscaler_client")
    def test_list_server_groups_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.server_groups import zpa_list_server_groups

        mock_client.zpa.server_groups.list_groups.return_value = (None, None, "Failed")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_server_groups()


# ============================================================================
# APP CONNECTOR GROUPS
# ============================================================================


class TestZpaAppConnectorGroups:

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_list_app_connector_groups(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_list_app_connector_groups

        groups = [_mock_obj({"id": f"acg{i}", "name": f"ACG {i}"}) for i in range(2)]
        mock_client.zpa.app_connector_groups.list_connector_groups.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_app_connector_groups()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_get_app_connector_group(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_get_app_connector_group

        group = _mock_obj({"id": "acg1", "name": "US-West"})
        mock_client.zpa.app_connector_groups.get_connector_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_app_connector_group(group_id="acg1")
        assert result["name"] == "US-West"

    @staticmethod
    def _cert(cert_id: str, name: str):
        """Return a mock SDK enrollment-cert object with .id and .name set as real attrs."""
        cert = MagicMock()
        cert.id = cert_id
        cert.name = name
        return cert

    def _arm_default_cert_lookup(self, mock_client, cert_id: str = "ent-cert-default"):
        """Make the 'Connector' enrollment cert resolve to ``cert_id``."""
        cert = self._cert(cert_id, "Connector")
        mock_client.zpa.enrollment_certificates.list_enrolment.return_value = (
            [cert],
            None,
            None,
        )

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_create_app_connector_group_auto_resolves_default_cert(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_create_app_connector_group

        self._arm_default_cert_lookup(mock_client, cert_id="ent-cert-default")
        created = _mock_obj({"id": "acg2", "name": "EU-Central"})
        mock_client.zpa.app_connector_groups.add_connector_group.return_value = (
            created,
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        result = zpa_create_app_connector_group(
            name="EU-Central", latitude="48.85", longitude="2.35", location="Paris"
        )

        mock_client.zpa.enrollment_certificates.list_enrolment.assert_called_once_with(
            query_params={"search": "Connector"}
        )
        kwargs = mock_client.zpa.app_connector_groups.add_connector_group.call_args.kwargs
        assert kwargs["enrollment_cert_id"] == "ent-cert-default"
        assert result["id"] == "acg2"

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_create_app_connector_group_with_explicit_cert_id_skips_lookup(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_create_app_connector_group

        created = _mock_obj({"id": "acg3", "name": "APAC"})
        mock_client.zpa.app_connector_groups.add_connector_group.return_value = (
            created,
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        zpa_create_app_connector_group(name="APAC", enrollment_cert_id="explicit-id-9")

        mock_client.zpa.enrollment_certificates.list_enrolment.assert_not_called()
        kwargs = mock_client.zpa.app_connector_groups.add_connector_group.call_args.kwargs
        assert kwargs["enrollment_cert_id"] == "explicit-id-9"

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_create_app_connector_group_with_custom_cert_name(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_create_app_connector_group

        custom = self._cert("svc-edge-cert-77", "Service Edge")
        mock_client.zpa.enrollment_certificates.list_enrolment.return_value = (
            [custom],
            None,
            None,
        )
        mock_client.zpa.app_connector_groups.add_connector_group.return_value = (
            _mock_obj({"id": "acg4", "name": "Edge-Group"}),
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        zpa_create_app_connector_group(
            name="Edge-Group", enrollment_cert_name="Service Edge"
        )

        mock_client.zpa.enrollment_certificates.list_enrolment.assert_called_once_with(
            query_params={"search": "Service Edge"}
        )
        kwargs = mock_client.zpa.app_connector_groups.add_connector_group.call_args.kwargs
        assert kwargs["enrollment_cert_id"] == "svc-edge-cert-77"

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_create_app_connector_group_cert_not_found_raises(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_create_app_connector_group

        mock_client.zpa.enrollment_certificates.list_enrolment.return_value = (
            [],
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="Enrollment certificate 'Connector' not found"):
            zpa_create_app_connector_group(name="No-Cert-Group")

        mock_client.zpa.app_connector_groups.add_connector_group.assert_not_called()

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_update_app_connector_group_preserves_cert_when_not_specified(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_update_app_connector_group

        updated = _mock_obj({"id": "acg9", "name": "Renamed"})
        mock_client.zpa.app_connector_groups.update_connector_group.return_value = (
            updated,
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        zpa_update_app_connector_group(group_id="acg9", name="Renamed")

        mock_client.zpa.enrollment_certificates.list_enrolment.assert_not_called()
        _args, kwargs = mock_client.zpa.app_connector_groups.update_connector_group.call_args
        assert "enrollment_cert_id" not in kwargs

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_update_app_connector_group_resolves_when_name_provided(
        self, mock_get_client, mock_client
    ):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_update_app_connector_group

        self._arm_default_cert_lookup(mock_client, cert_id="rotated-cert-1")
        mock_client.zpa.app_connector_groups.update_connector_group.return_value = (
            _mock_obj({"id": "acg9"}),
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        zpa_update_app_connector_group(
            group_id="acg9", enrollment_cert_name="Connector"
        )

        _args, kwargs = mock_client.zpa.app_connector_groups.update_connector_group.call_args
        assert kwargs["enrollment_cert_id"] == "rotated-cert-1"

    @patch("zscaler_mcp.tools.zpa.app_connector_groups.get_zscaler_client")
    def test_list_app_connector_groups_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_connector_groups import zpa_list_app_connector_groups

        mock_client.zpa.app_connector_groups.list_connector_groups.return_value = (None, None, "Err")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_app_connector_groups()


# ============================================================================
# APP CONNECTORS
# ============================================================================


class TestZpaAppConnectors:

    @patch("zscaler_mcp.tools.zpa.app_connectors.get_zscaler_client")
    def test_list_app_connectors(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_connectors import zpa_list_app_connectors

        connectors = [_mock_obj({"id": f"c{i}", "name": f"Connector {i}"}) for i in range(3)]
        mock_client.zpa.app_connectors.list_connectors.return_value = (connectors, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_app_connectors()
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zpa.app_connectors.get_zscaler_client")
    def test_get_app_connector(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_connectors import zpa_get_app_connector

        conn = _mock_obj({"id": "c1", "name": "DC-Connector"})
        mock_client.zpa.app_connectors.get_connector.return_value = (conn, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_app_connector(connector_id="c1")
        assert result["name"] == "DC-Connector"

    @patch("zscaler_mcp.tools.zpa.app_connectors.get_zscaler_client")
    def test_list_app_connectors_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.app_connectors import zpa_list_app_connectors

        mock_client.zpa.app_connectors.list_connectors.return_value = (None, None, "Failed")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_app_connectors()


# ============================================================================
# APPLICATION SERVERS
# ============================================================================


class TestZpaApplicationServers:

    @patch("zscaler_mcp.tools.zpa.application_servers.get_zscaler_client")
    def test_list_application_servers(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.application_servers import zpa_list_application_servers

        servers = [_mock_obj({"id": f"s{i}", "name": f"Server {i}"}) for i in range(2)]
        mock_client.zpa.servers.list_servers.return_value = (servers, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_application_servers()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.application_servers.get_zscaler_client")
    def test_get_application_server(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.application_servers import zpa_get_application_server

        srv = _mock_obj({"id": "s1", "name": "Backend"})
        mock_client.zpa.servers.get_server.return_value = (srv, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_application_server(server_id="s1")
        assert result["name"] == "Backend"

    @patch("zscaler_mcp.tools.zpa.application_servers.get_zscaler_client")
    def test_create_application_server(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.application_servers import zpa_create_application_server

        created = _mock_obj({"id": "s2", "name": "NewServer"})
        mock_client.zpa.servers.add_server.return_value = (created, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_create_application_server(name="NewServer", address="10.0.0.1")
        assert result["id"] == "s2"

    @patch("zscaler_mcp.tools.zpa.application_servers.get_zscaler_client")
    def test_list_application_servers_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.application_servers import zpa_list_application_servers

        mock_client.zpa.servers.list_servers.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_application_servers()


# ============================================================================
# BA CERTIFICATES
# ============================================================================


class TestZpaBaCertificates:

    @patch("zscaler_mcp.tools.zpa.ba_certificate.get_zscaler_client")
    def test_list_ba_certificates(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.ba_certificate import zpa_list_ba_certificates

        certs = [_mock_obj({"id": f"cert{i}", "name": f"Cert {i}"}) for i in range(2)]
        mock_client.zpa.certificates.list_issued_certificates.return_value = (certs, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_ba_certificates()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.ba_certificate.get_zscaler_client")
    def test_get_ba_certificate(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.ba_certificate import zpa_get_ba_certificate

        cert = _mock_obj({"id": "cert1", "name": "WildCard"})
        mock_client.zpa.certificates.get_certificate.return_value = (cert, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_ba_certificate(certificate_id="cert1")
        assert result["name"] == "WildCard"

    @patch("zscaler_mcp.tools.zpa.ba_certificate.get_zscaler_client")
    def test_list_ba_certificates_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.ba_certificate import zpa_list_ba_certificates

        mock_client.zpa.certificates.list_issued_certificates.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_ba_certificates()


# ============================================================================
# SERVICE EDGE GROUPS
# ============================================================================


class TestZpaServiceEdgeGroups:

    @patch("zscaler_mcp.tools.zpa.service_edge_groups.get_zscaler_client")
    def test_list_service_edge_groups(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.service_edge_groups import zpa_list_service_edge_groups

        groups = [_mock_obj({"id": f"seg{i}", "name": f"SE {i}"}) for i in range(2)]
        mock_client.zpa.service_edge_group.list_service_edge_groups.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_service_edge_groups()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.service_edge_groups.get_zscaler_client")
    def test_get_service_edge_group(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.service_edge_groups import zpa_get_service_edge_group

        group = _mock_obj({"id": "seg1", "name": "US Edge"})
        mock_client.zpa.service_edge_group.get_service_edge_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_service_edge_group(group_id="seg1")
        assert result["name"] == "US Edge"

    @patch("zscaler_mcp.tools.zpa.service_edge_groups.get_zscaler_client")
    def test_list_service_edge_groups_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.service_edge_groups import zpa_list_service_edge_groups

        mock_client.zpa.service_edge_group.list_service_edge_groups.return_value = (None, None, "Err")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_service_edge_groups()


# ============================================================================
# PROVISIONING KEYS
# ============================================================================


class TestZpaProvisioningKeys:

    @patch("zscaler_mcp.tools.zpa.provisioning_key.get_zscaler_client")
    def test_list_provisioning_keys(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.provisioning_key import zpa_list_provisioning_keys

        keys = [_mock_obj({"id": f"k{i}", "name": f"Key {i}"}) for i in range(2)]
        mock_client.zpa.provisioning.list_provisioning_keys.return_value = (keys, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_provisioning_keys(key_type="connector")
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.provisioning_key.get_zscaler_client")
    def test_get_provisioning_key(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.provisioning_key import zpa_get_provisioning_key

        key = _mock_obj({"id": "k1", "name": "ProdKey"})
        mock_client.zpa.provisioning.get_provisioning_key.return_value = (key, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_provisioning_key(key_id="k1", key_type="connector")
        assert result["name"] == "ProdKey"

    @patch("zscaler_mcp.tools.zpa.provisioning_key.get_zscaler_client")
    def test_list_provisioning_keys_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.provisioning_key import zpa_list_provisioning_keys

        mock_client.zpa.provisioning.list_provisioning_keys.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_provisioning_keys(key_type="connector")


# ============================================================================
# PRA PORTALS
# ============================================================================


class TestZpaPraPortals:

    @patch("zscaler_mcp.tools.zpa.pra_portal.get_zscaler_client")
    def test_list_pra_portals(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.pra_portal import zpa_list_pra_portals

        portals = [_mock_obj({"id": f"p{i}", "name": f"Portal {i}"}) for i in range(2)]
        mock_client.zpa.pra_portal.list_portals.return_value = (portals, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_pra_portals()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.pra_portal.get_zscaler_client")
    def test_get_pra_portal(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.pra_portal import zpa_get_pra_portal

        portal = _mock_obj({"id": "p1", "name": "Admin Portal"})
        mock_client.zpa.pra_portal.get_portal.return_value = (portal, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_pra_portal(portal_id="p1")
        assert result["name"] == "Admin Portal"

    @patch("zscaler_mcp.tools.zpa.pra_portal.get_zscaler_client")
    def test_list_pra_portals_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.pra_portal import zpa_list_pra_portals

        mock_client.zpa.pra_portal.list_portals.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_pra_portals()


# ============================================================================
# PRA CREDENTIALS
# ============================================================================


class TestZpaPraCredentials:

    @patch("zscaler_mcp.tools.zpa.pra_credential.get_zscaler_client")
    def test_list_pra_credentials(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.pra_credential import zpa_list_pra_credentials

        creds = [_mock_obj({"id": f"cred{i}", "name": f"Cred {i}"}) for i in range(2)]
        mock_client.zpa.pra_credential.list_credentials.return_value = (creds, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_pra_credentials()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.pra_credential.get_zscaler_client")
    def test_get_pra_credential(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.pra_credential import zpa_get_pra_credential

        cred = _mock_obj({"id": "cred1", "name": "SSHKey"})
        mock_client.zpa.pra_credential.get_credential.return_value = (cred, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_pra_credential(credential_id="cred1")
        assert result["name"] == "SSHKey"

    @patch("zscaler_mcp.tools.zpa.pra_credential.get_zscaler_client")
    def test_list_pra_credentials_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.pra_credential import zpa_list_pra_credentials

        mock_client.zpa.pra_credential.list_credentials.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_pra_credentials()


# ============================================================================
# ACCESS POLICY RULES
# ============================================================================


class TestZpaAccessPolicyRules:

    @patch("zscaler_mcp.tools.zpa.access_policy_rules.get_zscaler_client")
    def test_list_access_policy_rules(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_policy_rules import zpa_list_access_policy_rules

        rules = [_mock_obj({"id": f"r{i}", "name": f"Rule {i}"}) for i in range(3)]
        mock_client.zpa.policies.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_access_policy_rules()
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zpa.access_policy_rules.get_zscaler_client")
    def test_get_access_policy_rule(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_policy_rules import zpa_get_access_policy_rule

        rule = _mock_obj({"id": "r1", "name": "AllowAll"})
        mock_client.zpa.policies.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_access_policy_rule(rule_id="r1")
        assert result["name"] == "AllowAll"

    @patch("zscaler_mcp.tools.zpa.access_policy_rules.get_zscaler_client")
    def test_list_access_policy_rules_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_policy_rules import zpa_list_access_policy_rules

        mock_client.zpa.policies.list_rules.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_access_policy_rules()


# ============================================================================
# FORWARDING POLICY RULES
# ============================================================================


class TestZpaForwardingPolicyRules:

    @patch("zscaler_mcp.tools.zpa.access_forwarding_rules.get_zscaler_client")
    def test_list_forwarding_policy_rules(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_forwarding_rules import zpa_list_forwarding_policy_rules

        rules = [_mock_obj({"id": f"fr{i}", "name": f"FwdRule {i}"}) for i in range(2)]
        mock_client.zpa.policies.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_forwarding_policy_rules()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.access_forwarding_rules.get_zscaler_client")
    def test_get_forwarding_policy_rule(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_forwarding_rules import zpa_get_forwarding_policy_rule

        rule = _mock_obj({"id": "fr1", "name": "DirectFwd"})
        mock_client.zpa.policies.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_forwarding_policy_rule(rule_id="fr1")
        assert result["name"] == "DirectFwd"

    @patch("zscaler_mcp.tools.zpa.access_forwarding_rules.get_zscaler_client")
    def test_list_forwarding_policy_rules_error(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_forwarding_rules import zpa_list_forwarding_policy_rules

        mock_client.zpa.policies.list_rules.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zpa_list_forwarding_policy_rules()


# ============================================================================
# TIMEOUT POLICY RULES
# ============================================================================


class TestZpaTimeoutPolicyRules:

    @patch("zscaler_mcp.tools.zpa.access_timeout_rules.get_zscaler_client")
    def test_list_timeout_policy_rules(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_timeout_rules import zpa_list_timeout_policy_rules

        rules = [_mock_obj({"id": f"tr{i}", "name": f"Timeout {i}"}) for i in range(2)]
        mock_client.zpa.policies.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_timeout_policy_rules()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.access_timeout_rules.get_zscaler_client")
    def test_get_timeout_policy_rule(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_timeout_rules import zpa_get_timeout_policy_rule

        rule = _mock_obj({"id": "tr1", "name": "IdleTimeout"})
        mock_client.zpa.policies.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_timeout_policy_rule(rule_id="tr1")
        assert result["name"] == "IdleTimeout"


# ============================================================================
# ISOLATION POLICY RULES
# ============================================================================


class TestZpaIsolationPolicyRules:

    @patch("zscaler_mcp.tools.zpa.access_isolation_rules.get_zscaler_client")
    def test_list_isolation_policy_rules(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_isolation_rules import zpa_list_isolation_policy_rules

        rules = [_mock_obj({"id": f"ir{i}", "name": f"Iso {i}"}) for i in range(2)]
        mock_client.zpa.policies.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_isolation_policy_rules()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.access_isolation_rules.get_zscaler_client")
    def test_get_isolation_policy_rule(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_isolation_rules import zpa_get_isolation_policy_rule

        rule = _mock_obj({"id": "ir1", "name": "IsoRule"})
        mock_client.zpa.policies.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_isolation_policy_rule(rule_id="ir1")
        assert result["name"] == "IsoRule"


# ============================================================================
# APP PROTECTION RULES
# ============================================================================


class TestZpaAppProtectionRules:

    @patch("zscaler_mcp.tools.zpa.access_app_protection_rules.get_zscaler_client")
    def test_list_app_protection_rules(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_app_protection_rules import zpa_list_app_protection_rules

        rules = [_mock_obj({"id": f"apr{i}", "name": f"APR {i}"}) for i in range(2)]
        mock_client.zpa.policies.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_list_app_protection_rules()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.access_app_protection_rules.get_zscaler_client")
    def test_get_app_protection_rule(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.access_app_protection_rules import zpa_get_app_protection_rule

        rule = _mock_obj({"id": "apr1", "name": "WAFRule"})
        mock_client.zpa.policies.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zpa_get_app_protection_rule(rule_id="apr1")
        assert result["name"] == "WAFRule"


# ============================================================================
# GETTER / MANAGER TOOLS
# ============================================================================


class TestZpaPostureProfiles:

    @patch("zscaler_mcp.tools.zpa.get_posture_profiles.get_zscaler_client")
    def test_list_posture_profiles(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_posture_profiles import posture_profile_manager

        profiles = [_mock_obj({"id": f"pp{i}", "name": f"Profile {i}"}) for i in range(2)]
        mock_client.zpa.posture_profiles.list_posture_profiles.return_value = (profiles, None, None)
        mock_get_client.return_value = mock_client

        result = posture_profile_manager(action="read")
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.get_posture_profiles.get_zscaler_client")
    def test_get_posture_profile_by_id(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_posture_profiles import posture_profile_manager

        profile = _mock_obj({"id": "pp1", "name": "CrowdStrike"})
        mock_client.zpa.posture_profiles.get_profile.return_value = (profile, None, None)
        mock_get_client.return_value = mock_client

        result = posture_profile_manager(action="read", profile_id="pp1")
        assert result["name"] == "CrowdStrike"

    @patch("zscaler_mcp.tools.zpa.get_posture_profiles.get_zscaler_client")
    def test_unsupported_action_raises(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_posture_profiles import posture_profile_manager

        mock_get_client.return_value = mock_client
        with pytest.raises(ValueError):
            posture_profile_manager(action="delete")


class TestZpaTrustedNetworks:

    @patch("zscaler_mcp.tools.zpa.get_trusted_networks.get_zscaler_client")
    def test_list_trusted_networks(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_trusted_networks import trusted_network_manager

        networks = [_mock_obj({"id": f"tn{i}", "name": f"Net {i}"}) for i in range(2)]
        mock_client.zpa.trusted_networks.list_trusted_networks.return_value = (networks, None, None)
        mock_get_client.return_value = mock_client

        result = trusted_network_manager(action="read")
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.get_trusted_networks.get_zscaler_client")
    def test_unsupported_action_raises(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_trusted_networks import trusted_network_manager

        mock_get_client.return_value = mock_client
        with pytest.raises(ValueError):
            trusted_network_manager(action="create")


class TestZpaEnrollmentCertificates:

    @patch("zscaler_mcp.tools.zpa.get_enrollment_certificate.get_zscaler_client")
    def test_list_enrollment_certificates(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_enrollment_certificate import enrollment_certificate_manager

        certs = [_mock_obj({"id": f"ec{i}", "name": f"Cert {i}"}) for i in range(3)]
        mock_client.zpa.enrollment_certificates.list_enrolment.return_value = (certs, None, None)
        mock_get_client.return_value = mock_client

        result = enrollment_certificate_manager(action="read")
        assert len(result) == 3


class TestZpaSegmentsByType:

    @patch("zscaler_mcp.tools.zpa.get_segments_by_type.get_zscaler_client")
    def test_get_segments_by_type(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_segments_by_type import app_segments_by_type_manager

        segs = [_mock_obj({"id": "s1", "name": "BrowserAccess"})]
        mock_client.zpa.app_segment_by_type.get_segments_by_type.return_value = (segs, None, None)
        mock_get_client.return_value = mock_client

        result = app_segments_by_type_manager(application_type="BROWSER_ACCESS")
        assert len(result) == 1


class TestZpaIsolationProfiles:

    @patch("zscaler_mcp.tools.zpa.get_isolation_profile.get_zscaler_client")
    def test_list_isolation_profiles(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_isolation_profile import isolation_profile_manager

        profiles = [_mock_obj({"id": "ip1", "name": "Default"}), _mock_obj({"id": "ip2", "name": "Custom"})]
        mock_client.zpa.cbi_profile.list_cbi_profiles.return_value = (profiles, None, None)
        mock_get_client.return_value = mock_client

        result = isolation_profile_manager(action="read")
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zpa.get_isolation_profile.get_zscaler_client")
    def test_unsupported_action_raises(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_isolation_profile import isolation_profile_manager

        mock_get_client.return_value = mock_client
        with pytest.raises(ValueError):
            isolation_profile_manager(action="write")


class TestZpaAppProtectionProfiles:

    @patch("zscaler_mcp.tools.zpa.get_app_protection_profile.get_zscaler_client")
    def test_list_app_protection_profiles(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_app_protection_profile import app_protection_profile_manager

        profiles = [_mock_obj({"id": "app1", "name": "WAF Profile"})]
        mock_client.zpa.app_protection.list_profiles.return_value = (profiles, None, None)
        mock_get_client.return_value = mock_client

        result = app_protection_profile_manager(action="read")
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zpa.get_app_protection_profile.get_zscaler_client")
    def test_get_app_protection_profile_by_name(self, mock_get_client, mock_client):
        from zscaler_mcp.tools.zpa.get_app_protection_profile import app_protection_profile_manager

        profiles = [_mock_obj({"id": "app1", "name": "WAF Profile"})]
        mock_client.zpa.app_protection.list_profiles.return_value = (profiles, None, None)
        mock_get_client.return_value = mock_client

        result = app_protection_profile_manager(action="read", name="WAF Profile")
        assert result["name"] == "WAF Profile"


# ============================================================================
# SERVICE REGISTRATION
# ============================================================================


class TestZPAServiceRegistration:

    def test_zpa_service_exists_in_registry(self):
        from zscaler_mcp.services import get_available_services, get_service_names

        assert "zpa" in get_service_names()
        assert "zpa" in get_available_services()

    def test_zpa_service_has_tools(self):
        from zscaler_mcp.services import ZPAService

        service = ZPAService(None)
        assert len(service.read_tools) > 0

    def test_all_zpa_tools_have_naming_convention(self):
        from zscaler_mcp.services import ZPAService

        service = ZPAService(None)
        for tool in service.read_tools:
            name = tool["name"]
            assert "zpa" in name.lower(), f"Tool {name} missing zpa in name"
        for tool in service.write_tools:
            name = tool["name"]
            assert "zpa" in name.lower(), f"Tool {name} missing zpa in name"
