"""Tests for the AWS Secrets Manager loader (cloud/aws_secrets.py).

None of these require ``boto3``. The credential-publishing half is driven
through a stubbed :func:`_fetch_secret_string`, and the one test that does
exercise the import goes through the *absence* of boto3, which is the state of
a default (no ``[aws]`` extra) install and therefore the state a user hits when
they set ``ZSCALER_SECRET_NAME`` without installing the extra.
"""

from __future__ import annotations

import io
import json
import logging
import os

import pytest

from zscaler_mcp.cloud import aws_secrets

# Every variable the loader is willing to write.
_MANAGED = aws_secrets.CREDENTIAL_KEYS + ("ZSCALER_SECRET_NAME", "AWS_REGION", "AWS_DEFAULT_REGION")


@pytest.fixture(autouse=True)
def _clean_env():
    """Isolate these tests from the process environment in both directions.

    Cleared going in, so a developer's real ``.env`` cannot make an assertion
    pass for the wrong reason. Restored coming out, because the whole point of
    the loader is that it writes ``os.environ`` directly — ``monkeypatch`` does
    not see those writes and would leave them behind for every later test in the
    session. A leaked ``ZSCALER_MCP_REQUEST_STATE_KEYS`` in particular fails
    server construction repo-wide, which is a confusing way to learn this.
    """
    saved = {key: os.environ.get(key) for key in _MANAGED}
    for key in _MANAGED:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _stub_secret(monkeypatch, payload, *, secret_name="zscaler/mcp/credentials"):
    """Point the loader at ``payload`` without touching AWS."""
    monkeypatch.setenv("ZSCALER_SECRET_NAME", secret_name)
    body = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(aws_secrets, "_fetch_secret_string", lambda _id: body)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


class TestGate:
    def test_disabled_without_a_secret_name(self):
        assert aws_secrets.is_enabled() is False

    def test_enabled_by_the_secret_name_alone(self, monkeypatch):
        """Presence of ZSCALER_SECRET_NAME IS the gate — there is no boolean.

        The AgentCore CloudFormation in ``integrations/aws/`` has always set
        exactly this one variable to mean "fetch my credentials from Secrets
        Manager", so requiring a second flag would silently break every existing
        deployment.
        """
        monkeypatch.setenv("ZSCALER_SECRET_NAME", "zscaler/mcp/credentials")
        assert aws_secrets.is_enabled() is True

    def test_whitespace_is_not_a_secret_name(self, monkeypatch):
        monkeypatch.setenv("ZSCALER_SECRET_NAME", "   ")
        assert aws_secrets.is_enabled() is False

    def test_load_is_a_noop_when_disabled(self):
        # Must return without importing boto3 — the common stdio/local case.
        assert aws_secrets.load_secrets() is None


# ---------------------------------------------------------------------------
# Region resolution
# ---------------------------------------------------------------------------


class TestRegion:
    def test_prefers_aws_region(self, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "eu-west-2")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        assert aws_secrets._region() == "eu-west-2"

    def test_falls_back_to_aws_default_region(self, monkeypatch):
        monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-2")
        assert aws_secrets._region() == "ap-southeast-2"

    def test_unset_defers_to_boto3(self):
        """No hardcoded default.

        The fork defaulted to ``us-east-1``, which silently queried the wrong
        region for every deployment outside it. ``None`` lets boto3 resolve from
        the container credential chain, which AgentCore and ECS populate.
        """
        assert aws_secrets._region() is None


# ---------------------------------------------------------------------------
# Publishing credentials
# ---------------------------------------------------------------------------


class TestPublishing:
    def test_credentials_reach_the_environment(self, monkeypatch):
        _stub_secret(
            monkeypatch,
            {
                "ZSCALER_CLIENT_ID": "client-1",
                "ZSCALER_CLIENT_SECRET": "shh",
                "ZSCALER_VANITY_DOMAIN": "acme",
                "ZSCALER_CUSTOMER_ID": "123456",
            },
        )
        aws_secrets.load_secrets()

        assert os.environ["ZSCALER_CLIENT_ID"] == "client-1"
        assert os.environ["ZSCALER_CLIENT_SECRET"] == "shh"
        assert os.environ["ZSCALER_VANITY_DOMAIN"] == "acme"
        assert os.environ["ZSCALER_CUSTOMER_ID"] == "123456"

    def test_the_secret_overrides_the_container_environment(self, monkeypatch):
        """Rotating the secret has to beat a stale value in the task definition.

        Deployments commonly carry a placeholder in the container env and the
        real credential in the secret; if the environment won, rotation would
        have no effect and the failure would look like a Zscaler-side problem.
        """
        monkeypatch.setenv("ZSCALER_CLIENT_ID", "stale")
        monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "stale")
        _stub_secret(monkeypatch, {"ZSCALER_CLIENT_ID": "fresh", "ZSCALER_CLIENT_SECRET": "fresh"})
        aws_secrets.load_secrets()

        assert os.environ["ZSCALER_CLIENT_ID"] == "fresh"

    def test_non_string_values_are_coerced(self, monkeypatch):
        """Secrets authored in the console frequently hold a bare JSON number."""
        _stub_secret(
            monkeypatch,
            {
                "ZSCALER_CLIENT_ID": "c",
                "ZSCALER_CLIENT_SECRET": "s",
                "ZSCALER_CUSTOMER_ID": 123456,
            },
        )
        aws_secrets.load_secrets()

        assert os.environ["ZSCALER_CUSTOMER_ID"] == "123456"

    def test_null_values_are_skipped_rather_than_stringified(self, monkeypatch):
        """A JSON null must not become the literal string "None"."""
        _stub_secret(
            monkeypatch,
            {"ZSCALER_CLIENT_ID": "c", "ZSCALER_CLIENT_SECRET": "s", "ZSCALER_CLOUD": None},
        )
        aws_secrets.load_secrets()

        assert "ZSCALER_CLOUD" not in os.environ


class TestAllowlist:
    def test_unrecognised_keys_never_reach_the_environment(self, monkeypatch):
        """The fork injected every key it found.

        That turned a typo — or a hostile edit of the secret — into an arbitrary
        environment variable in the server process, which is a far larger blast
        radius than "my credential didn't load".
        """
        _stub_secret(
            monkeypatch,
            {
                "ZSCALER_CLIENT_ID": "c",
                "ZSCALER_CLIENT_SECRET": "s",
                "PATH": "/attacker/bin",
                "LD_PRELOAD": "/tmp/evil.so",
            },
        )
        original_path = os.environ.get("PATH")
        aws_secrets.load_secrets()

        assert os.environ.get("PATH") == original_path
        assert "LD_PRELOAD" not in os.environ

    def test_ignored_keys_are_named_in_a_warning(self, monkeypatch, caplog):
        """A misspelled key and an absent one are otherwise indistinguishable.

        The symptom lands minutes later as an authentication failure, so the
        loader has to say which key it dropped.
        """
        _stub_secret(
            monkeypatch,
            {
                "ZSCALER_CLIENT_ID": "c",
                "ZSCALER_CLIENT_SECRET": "s",
                "ZSCALER_VANITY_DOMAINN": "typo",
            },
        )
        with caplog.at_level("WARNING"):
            aws_secrets.load_secrets()
        assert "ZSCALER_VANITY_DOMAINN" in caplog.text

    def test_the_mcp_auth_key_and_state_ring_are_loadable(self, monkeypatch):
        """AWS deployments have nowhere else to put these.

        On AgentCore the container environment is the deployment manifest, so
        the MCP client-auth key and the SEP-2322 key ring belong in the same
        secret as the OneAPI credentials.
        """
        ring = f"{'a' * 64},{'b' * 64}"
        _stub_secret(
            monkeypatch,
            {
                "ZSCALER_CLIENT_ID": "c",
                "ZSCALER_CLIENT_SECRET": "s",
                "ZSCALER_MCP_AUTH_API_KEY": "sk-abc",
                "ZSCALER_MCP_REQUEST_STATE_KEYS": ring,
            },
        )
        aws_secrets.load_secrets()

        assert os.environ["ZSCALER_MCP_AUTH_API_KEY"] == "sk-abc"
        assert os.environ["ZSCALER_MCP_REQUEST_STATE_KEYS"] == ring


class TestSecretValuesAreNotLogged:
    def test_secret_material_never_appears_in_the_log(self, monkeypatch, caplog):
        _stub_secret(
            monkeypatch,
            {
                "ZSCALER_CLIENT_ID": "client-1",
                "ZSCALER_CLIENT_SECRET": "super-secret-value",
                "ZSCALER_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----",
                "ZSCALER_MCP_AUTH_API_KEY": "sk-do-not-log",
            },
        )
        with caplog.at_level("DEBUG"):
            aws_secrets.load_secrets()
        assert "super-secret-value" not in caplog.text
        assert "BEGIN PRIVATE KEY" not in caplog.text
        assert "sk-do-not-log" not in caplog.text


# ---------------------------------------------------------------------------
# Failing closed
# ---------------------------------------------------------------------------


class TestFailsClosed:
    """Every failure stops the server.

    Starting without credentials defers the error to the first tool call, where
    it reaches the agent as an opaque Zscaler API error rather than as the
    deployment problem it is.
    """

    def test_missing_boto3_names_the_extra(self, monkeypatch):
        monkeypatch.setenv("ZSCALER_SECRET_NAME", "zscaler/mcp/credentials")
        with pytest.raises(SystemExit, match=r"zscaler-mcp\[aws\]"):
            aws_secrets.load_secrets()

    def test_a_non_json_secret_is_fatal(self, monkeypatch):
        _stub_secret(monkeypatch, "not json at all")
        with pytest.raises(SystemExit, match="not valid JSON"):
            aws_secrets.load_secrets()

    def test_a_json_array_is_fatal(self, monkeypatch):
        _stub_secret(monkeypatch, ["ZSCALER_CLIENT_ID"])
        with pytest.raises(SystemExit, match="not an object"):
            aws_secrets.load_secrets()

    def test_missing_required_credentials_are_fatal(self, monkeypatch):
        _stub_secret(monkeypatch, {"ZSCALER_VANITY_DOMAIN": "acme"})
        with pytest.raises(SystemExit, match="ZSCALER_CLIENT_ID"):
            aws_secrets.load_secrets()

    def test_a_private_key_satisfies_the_client_secret_requirement(self, monkeypatch):
        """JWT-based OneAPI auth has no client secret to offer."""
        _stub_secret(
            monkeypatch,
            {"ZSCALER_CLIENT_ID": "c", "ZSCALER_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----"},
        )
        aws_secrets.load_secrets()  # must not raise

    def test_credentials_already_in_the_environment_satisfy_the_check(self, monkeypatch):
        """A secret holding only non-credential settings is legitimate."""
        monkeypatch.setenv("ZSCALER_CLIENT_ID", "from-task-definition")
        monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "from-task-definition")
        _stub_secret(monkeypatch, {"ZSCALER_VANITY_DOMAIN": "acme"})
        aws_secrets.load_secrets()  # must not raise


# ---------------------------------------------------------------------------
# Dispatch from the cloud package
# ---------------------------------------------------------------------------


class TestCloudDispatch:
    def test_load_secrets_runs_the_aws_loader(self, monkeypatch):
        """`server.main()` calls `cloud.load_secrets()` once, not each provider.

        Before consolidation that entry point dispatched only to GCP, so a
        deployment from this repo's own AgentCore CloudFormation set
        ZSCALER_SECRET_NAME and nothing ever read it.
        """
        from zscaler_mcp import cloud

        _stub_secret(monkeypatch, {"ZSCALER_CLIENT_ID": "c", "ZSCALER_CLIENT_SECRET": "s"})
        cloud.load_secrets()

        assert os.environ["ZSCALER_CLIENT_ID"] == "c"

    def test_is_enabled_covers_every_provider(self, monkeypatch):
        from zscaler_mcp import cloud

        monkeypatch.delenv("ZSCALER_MCP_GCP_SECRET_MANAGER", raising=False)
        assert cloud.is_enabled() is False
        monkeypatch.setenv("ZSCALER_SECRET_NAME", "zscaler/mcp/credentials")
        assert cloud.is_enabled() is True


class TestLoaderOutputIsVisible:
    """The loaders run before ``configure_logging()`` and must still be heard.

    ``main()`` calls ``load_secrets()`` ahead of ``parse_args()`` because a secret
    can carry the variables the CLI reads for its own defaults. Without the
    bootstrap handler that ordering silently discards every line the loader
    emits — which is exactly what a real AgentCore container did: credentials
    loaded fine, and the startup log said nothing about where they came from.
    """

    def test_a_handlerless_root_still_gets_the_output(self, monkeypatch, capsys):
        from zscaler_mcp import cloud

        root = logging.getLogger()
        saved_handlers, saved_level = root.handlers[:], root.level
        root.handlers = []
        root.setLevel(logging.WARNING)
        try:
            _stub_secret(monkeypatch, {"ZSCALER_CLIENT_ID": "c", "ZSCALER_CLIENT_SECRET": "s"})
            cloud.load_secrets()
            # stderr, not stdout: the transport is still unknown here, and a
            # stdout handler would corrupt the JSON-RPC stream under stdio.
            assert "AWS Secrets Manager" in capsys.readouterr().err
        finally:
            root.handlers, root.level = saved_handlers, saved_level

    def test_the_bare_root_is_restored_for_configure_logging(self, monkeypatch):
        """basicConfig() no-ops if a handler is left behind, pinning stderr for
        the whole process and overriding the transport-appropriate choice."""
        from zscaler_mcp import cloud

        root = logging.getLogger()
        saved_handlers, saved_level = root.handlers[:], root.level
        root.handlers = []
        root.setLevel(logging.WARNING)
        try:
            _stub_secret(monkeypatch, {"ZSCALER_CLIENT_ID": "c", "ZSCALER_CLIENT_SECRET": "s"})
            cloud.load_secrets()
            assert root.handlers == []
            assert root.level == logging.WARNING
        finally:
            root.handlers, root.level = saved_handlers, saved_level

    def test_an_existing_logging_setup_is_left_alone(self, monkeypatch):
        from zscaler_mcp import cloud

        root = logging.getLogger()
        saved_handlers, saved_level = root.handlers[:], root.level
        existing = logging.StreamHandler(io.StringIO())
        root.handlers = [existing]
        try:
            _stub_secret(monkeypatch, {"ZSCALER_CLIENT_ID": "c", "ZSCALER_CLIENT_SECRET": "s"})
            cloud.load_secrets()
            assert root.handlers == [existing]
        finally:
            root.handlers, root.level = saved_handlers, saved_level
