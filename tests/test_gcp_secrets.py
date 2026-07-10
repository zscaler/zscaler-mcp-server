"""Tests for the GCP Secret Manager loader (cloud/gcp_secrets.py).

These cover the gate logic and the no-op path without requiring the real
``google-cloud-secret-manager`` dependency.
"""

from __future__ import annotations

import pytest

from zscaler_mcp.cloud import gcp_secrets


def test_is_enabled_default_false(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_GCP_SECRET_MANAGER", raising=False)
    assert gcp_secrets.is_enabled() is False


@pytest.mark.parametrize("truthy", ["true", "1", "yes", "TRUE", " Yes "])
def test_is_enabled_truthy(monkeypatch, truthy):
    monkeypatch.setenv("ZSCALER_MCP_GCP_SECRET_MANAGER", truthy)
    assert gcp_secrets.is_enabled() is True


def test_load_secrets_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_GCP_SECRET_MANAGER", raising=False)
    # Must return cleanly without importing google libs.
    assert gcp_secrets.load_secrets() is None


def test_load_secrets_missing_project_id_exits(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_GCP_SECRET_MANAGER", "true")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    with pytest.raises(SystemExit, match="GCP_PROJECT_ID is not set"):
        gcp_secrets.load_secrets()


def test_env_key_to_secret_id():
    assert gcp_secrets._env_key_to_secret_id("ZSCALER_CLIENT_ID") == "zscaler-client-id"
    assert gcp_secrets._env_key_to_secret_id("ZSCALER_CLIENT_SECRET") == "zscaler-client-secret"
