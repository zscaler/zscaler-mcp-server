"""
Unit tests for EASM (External Attack Surface Management) tools.

Covers: findings, lookalike_domains, organizations.
"""

from unittest.mock import MagicMock, patch

import pytest


def _mock_obj(data: dict):
    obj = MagicMock()
    obj.as_dict.return_value = data
    return obj


# ============================================================================
# FINDINGS
# ============================================================================


class TestEasmFindings:

    @patch("zscaler_mcp.tools.easm.findings.get_zscaler_client")
    def test_list_findings_success(self, mock_get_client):
        from zscaler_mcp.tools.easm.findings import zeasm_list_findings

        mock_client = MagicMock()
        findings = _mock_obj({
            "findings": [
                {"id": "f1", "severity": "HIGH", "title": "Open Port 22"},
                {"id": "f2", "severity": "MEDIUM", "title": "Expired Cert"},
            ]
        })
        mock_client.zeasm.findings.list_findings.return_value = (findings, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_list_findings(org_id="org1")
        assert "findings" in result

    @patch("zscaler_mcp.tools.easm.findings.get_zscaler_client")
    def test_list_findings_with_jmespath(self, mock_get_client):
        from zscaler_mcp.tools.easm.findings import zeasm_list_findings

        mock_client = MagicMock()
        findings = _mock_obj({
            "findings": [
                {"id": "f1", "severity": "HIGH"},
                {"id": "f2", "severity": "LOW"},
            ]
        })
        mock_client.zeasm.findings.list_findings.return_value = (findings, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_list_findings(org_id="org1", query="findings[?severity == 'HIGH']")
        assert len(result) == 1

    @patch("zscaler_mcp.tools.easm.findings.get_zscaler_client")
    def test_list_findings_error(self, mock_get_client):
        from zscaler_mcp.tools.easm.findings import zeasm_list_findings

        mock_client = MagicMock()
        mock_client.zeasm.findings.list_findings.return_value = (None, None, "API Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zeasm_list_findings(org_id="org1")

    @patch("zscaler_mcp.tools.easm.findings.get_zscaler_client")
    def test_get_finding_details(self, mock_get_client):
        from zscaler_mcp.tools.easm.findings import zeasm_get_finding_details

        mock_client = MagicMock()
        finding = _mock_obj({"id": "f1", "severity": "HIGH", "title": "Open Port"})
        mock_client.zeasm.findings.get_finding_details.return_value = (finding, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_get_finding_details(org_id="org1", finding_id="f1")
        assert result["id"] == "f1"

    @patch("zscaler_mcp.tools.easm.findings.get_zscaler_client")
    def test_get_finding_evidence(self, mock_get_client):
        from zscaler_mcp.tools.easm.findings import zeasm_get_finding_evidence

        mock_client = MagicMock()
        evidence = _mock_obj({"finding_id": "f1", "evidence": ["screenshot.png"]})
        mock_client.zeasm.findings.get_finding_evidence.return_value = (evidence, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_get_finding_evidence(org_id="org1", finding_id="f1")
        assert result["finding_id"] == "f1"

    @patch("zscaler_mcp.tools.easm.findings.get_zscaler_client")
    def test_get_finding_scan_output(self, mock_get_client):
        from zscaler_mcp.tools.easm.findings import zeasm_get_finding_scan_output

        mock_client = MagicMock()
        scan = _mock_obj({"finding_id": "f1", "scan_data": {"ports": [22, 443]}})
        mock_client.zeasm.findings.get_finding_scan_output.return_value = (scan, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_get_finding_scan_output(org_id="org1", finding_id="f1")
        assert result["finding_id"] == "f1"


# ============================================================================
# LOOKALIKE DOMAINS
# ============================================================================


class TestEasmLookalikeDomains:

    @patch("zscaler_mcp.tools.easm.lookalike_domains.get_zscaler_client")
    def test_list_lookalike_domains(self, mock_get_client):
        from zscaler_mcp.tools.easm.lookalike_domains import zeasm_list_lookalike_domains

        mock_client = MagicMock()
        domains = _mock_obj({
            "domains": [
                {"raw": "zscal3r.com", "risk": "HIGH"},
                {"raw": "zscaler-login.com", "risk": "MEDIUM"},
            ]
        })
        mock_client.zeasm.lookalike_domains.list_lookalike_domains.return_value = (domains, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_list_lookalike_domains(org_id="org1")
        assert "domains" in result

    @patch("zscaler_mcp.tools.easm.lookalike_domains.get_zscaler_client")
    def test_list_lookalike_domains_with_jmespath(self, mock_get_client):
        from zscaler_mcp.tools.easm.lookalike_domains import zeasm_list_lookalike_domains

        mock_client = MagicMock()
        domains = _mock_obj({
            "domains": [
                {"raw": "zscal3r.com", "risk": "HIGH"},
                {"raw": "zscaler-login.com", "risk": "MEDIUM"},
            ]
        })
        mock_client.zeasm.lookalike_domains.list_lookalike_domains.return_value = (domains, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_list_lookalike_domains(org_id="org1", query="domains[?risk == 'HIGH']")
        assert len(result) == 1

    @patch("zscaler_mcp.tools.easm.lookalike_domains.get_zscaler_client")
    def test_get_lookalike_domain(self, mock_get_client):
        from zscaler_mcp.tools.easm.lookalike_domains import zeasm_get_lookalike_domain

        mock_client = MagicMock()
        domain = _mock_obj({"raw": "zscal3r.com", "risk": "HIGH", "created": "2024-01-01"})
        mock_client.zeasm.lookalike_domains.get_lookalike_domain.return_value = (domain, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_get_lookalike_domain(org_id="org1", lookalike_raw="zscal3r.com")
        assert result["raw"] == "zscal3r.com"

    @patch("zscaler_mcp.tools.easm.lookalike_domains.get_zscaler_client")
    def test_list_lookalike_domains_error(self, mock_get_client):
        from zscaler_mcp.tools.easm.lookalike_domains import zeasm_list_lookalike_domains

        mock_client = MagicMock()
        mock_client.zeasm.lookalike_domains.list_lookalike_domains.return_value = (None, None, "Err")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zeasm_list_lookalike_domains(org_id="org1")


# ============================================================================
# ORGANIZATIONS
# ============================================================================


class TestEasmOrganizations:

    @patch("zscaler_mcp.tools.easm.organizations.get_zscaler_client")
    def test_list_organizations(self, mock_get_client):
        from zscaler_mcp.tools.easm.organizations import zeasm_list_organizations

        mock_client = MagicMock()
        orgs = _mock_obj({
            "organizations": [
                {"id": "org1", "name": "Acme Corp"},
                {"id": "org2", "name": "Test Inc"},
            ]
        })
        mock_client.zeasm.organizations.list_organizations.return_value = (orgs, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_list_organizations()
        assert "organizations" in result

    @patch("zscaler_mcp.tools.easm.organizations.get_zscaler_client")
    def test_list_organizations_with_jmespath(self, mock_get_client):
        from zscaler_mcp.tools.easm.organizations import zeasm_list_organizations

        mock_client = MagicMock()
        orgs = _mock_obj({
            "organizations": [
                {"id": "org1", "name": "Acme Corp"},
            ]
        })
        mock_client.zeasm.organizations.list_organizations.return_value = (orgs, None, None)
        mock_get_client.return_value = mock_client

        result = zeasm_list_organizations(query="organizations[*].name")
        assert isinstance(result, list)

    @patch("zscaler_mcp.tools.easm.organizations.get_zscaler_client")
    def test_list_organizations_error(self, mock_get_client):
        from zscaler_mcp.tools.easm.organizations import zeasm_list_organizations

        mock_client = MagicMock()
        mock_client.zeasm.organizations.list_organizations.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zeasm_list_organizations()


# ============================================================================
# SERVICE REGISTRATION
# ============================================================================


class TestEASMServiceRegistration:

    def test_easm_service_exists_in_registry(self):
        from zscaler_mcp.services import get_available_services, get_service_names

        assert "zeasm" in get_service_names()
        assert "zeasm" in get_available_services()

    def test_easm_service_has_read_tools_only(self):
        from zscaler_mcp.services import ZEASMService

        service = ZEASMService(None)
        assert len(service.read_tools) > 0
        assert len(service.write_tools) == 0

    def test_all_easm_tools_have_prefix(self):
        from zscaler_mcp.services import ZEASMService

        service = ZEASMService(None)
        for tool in service.read_tools:
            name = tool["name"]
            assert "easm" in name.lower(), f"Tool {name} missing easm in name"
