"""Tests for :mod:`zscaler_mcp.lifecycle`.

The lifecycle module is the foundation of the
``zscaler-mcp reload/restart/status/stop`` CLI subcommands. Coverage:

* PID-file round-trip + atomic write
* Default PID-file resolution priority (``$ZSCALER_MCP_PID_FILE`` >
  ``/var/run`` > ``/tmp`` > ``~/.zscaler-mcp``)
* ``is_process_alive`` semantics
* Each subcommand against (a) no PID file, (b) stale PID file, (c) live
  PID belonging to this very process — verifying we both signal and
  parse-print correctly without needing a separate server subprocess
* The serve-side soft-reload helper actually re-reads ``.env`` and
  re-applies ``ZSCALER_MCP_LOG_TOOL_CALLS``
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

import pytest

from zscaler_mcp import lifecycle
from zscaler_mcp.common import tool_helpers

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pid_file(tmp_path, monkeypatch):
    """Point ``ZSCALER_MCP_PID_FILE`` at a temp file for the test."""
    p = tmp_path / "zscaler-mcp.pid"
    monkeypatch.setenv("ZSCALER_MCP_PID_FILE", str(p))
    return p


@pytest.fixture
def no_default_dotenv(monkeypatch):
    """Force ``_default_dotenv_candidates()`` to return an empty list.

    Without this, the classifier sees the repo's own ``.env`` (this test
    file lives inside the project root that has a ``.env``) and routes
    through the "fresh-discovery" branch instead of "missing" / "none".
    Tests that explicitly want to assert "missing" or "none" use this
    fixture; tests that want to exercise "fresh-discovery" use the
    sibling fixture ``with_default_dotenv`` below.
    """
    monkeypatch.setattr(
        "zscaler_mcp.lifecycle._default_dotenv_candidates",
        lambda: [],
    )


@pytest.fixture
def with_default_dotenv(tmp_path, monkeypatch):
    """Place a real .env in one of the default search slots.

    Yields the path of the planted file so tests can reference it in
    assertions.
    """
    planted = tmp_path / "default.env"
    planted.write_text("PLANTED=1\n")
    monkeypatch.setattr(
        "zscaler_mcp.lifecycle._default_dotenv_candidates",
        lambda: [planted],
    )
    return planted


def _make_state(pid: int = 1, **overrides) -> lifecycle.LifecycleState:
    defaults = dict(
        pid=pid,
        started_at=time.time(),
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        dotenv_path="/app/.env",
        argv=[sys.executable, "-m", "zscaler_mcp.server", "--transport", "streamable-http"],
        python_executable=sys.executable,
        version="test",
    )
    defaults.update(overrides)
    return lifecycle.LifecycleState(**defaults)


# ---------------------------------------------------------------------------
# PID-file path resolution
# ---------------------------------------------------------------------------


class TestDefaultPidFilePath:
    def test_explicit_env_override_wins(self, tmp_path, monkeypatch):
        target = tmp_path / "custom.pid"
        monkeypatch.setenv("ZSCALER_MCP_PID_FILE", str(target))
        assert lifecycle.default_pid_file_path() == target

    def test_falls_back_to_writable_dir(self, monkeypatch):
        monkeypatch.delenv("ZSCALER_MCP_PID_FILE", raising=False)
        # Both /var/run (typical macOS = not writable) and /tmp exist;
        # whichever is writable should win, but we only assert the file
        # name, not the directory.
        path = lifecycle.default_pid_file_path()
        assert path.name in ("zscaler-mcp.pid", "server.pid")


# ---------------------------------------------------------------------------
# PID-file round-trip
# ---------------------------------------------------------------------------


class TestPidFileRoundTrip:
    def test_write_then_read_yields_equal_state(self, pid_file):
        state = _make_state(pid=12345)
        lifecycle.write_pid_file(state, pid_file)

        assert pid_file.exists()
        loaded = lifecycle.read_pid_file(pid_file)
        assert loaded is not None
        assert loaded.pid == 12345
        assert loaded.transport == "streamable-http"
        assert loaded.dotenv_path == "/app/.env"
        assert loaded.argv == state.argv

    def test_read_returns_none_when_absent(self, pid_file):
        assert lifecycle.read_pid_file(pid_file) is None

    def test_read_returns_none_for_garbage(self, pid_file):
        pid_file.write_text("{not json")
        assert lifecycle.read_pid_file(pid_file) is None

    def test_remove_is_idempotent(self, pid_file):
        lifecycle.remove_pid_file(pid_file)  # no-op when missing
        state = _make_state(pid=1)
        lifecycle.write_pid_file(state, pid_file)
        lifecycle.remove_pid_file(pid_file)
        lifecycle.remove_pid_file(pid_file)
        assert not pid_file.exists()


# ---------------------------------------------------------------------------
# Process-alive probe
# ---------------------------------------------------------------------------


class TestIsProcessAlive:
    def test_self_is_alive(self):
        assert lifecycle.is_process_alive(os.getpid()) is True

    def test_invalid_pid(self):
        assert lifecycle.is_process_alive(0) is False
        assert lifecycle.is_process_alive(-1) is False

    def test_stale_pid_returns_false(self):
        # PID 999_999_999 is essentially guaranteed not to exist on Unix.
        assert lifecycle.is_process_alive(999_999_999) is False


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------


class TestCmdStatus:
    def test_no_pid_file(self, pid_file, capsys):
        rc = lifecycle.cmd_status()
        out = capsys.readouterr().out
        assert rc == 1
        assert "No zscaler-mcp server PID file" in out

    def test_stale_pid_file_marked_dead(self, pid_file, capsys):
        # PID 999_999_999: not alive.
        state = _make_state(pid=999_999_999)
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_status()
        out = capsys.readouterr().out
        assert rc == 1
        assert "stale PID file" in out or "NO" in out

    def test_live_pid_renders_full_status(self, pid_file, capsys):
        state = _make_state(pid=os.getpid(), transport="streamable-http", port=8765)
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_status()
        out = capsys.readouterr().out
        assert rc == 0
        assert "alive" in out and "yes" in out
        assert str(os.getpid()) in out
        assert "127.0.0.1:8765" in out
        assert "/app/.env" in out
        assert "env source" in out  # classifier label is surfaced

    def test_status_flags_missing_dotenv(self, pid_file, no_default_dotenv, capsys):
        # Simulates the common --env-file-only docker case: dotenv_path
        # was recorded at startup but the file isn't actually present
        # inside the container.
        state = _make_state(pid=os.getpid(), dotenv_path="/app/.env")
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_status()
        out = capsys.readouterr().out
        assert rc == 0
        assert "missing" in out
        assert "docker cp" in out  # workflow C surfaced in the advice

    def test_status_flags_no_dotenv(self, pid_file, no_default_dotenv, capsys):
        # Simulates AgentCore / pure --env-file deployments where no
        # .env was loaded at all.
        state = _make_state(pid=os.getpid(), dotenv_path=None)
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_status()
        out = capsys.readouterr().out
        assert rc == 0
        assert "env source        : none" in out
        assert "docker cp" in out

    def test_status_flags_live_dotenv(self, pid_file, tmp_path, capsys):
        # Real bind-mounted .env case: the path exists and points to a
        # readable file.
        env_file = tmp_path / ".env"
        env_file.write_text("ZSCALER_CLIENT_ID=demo\n")
        state = _make_state(pid=os.getpid(), dotenv_path=str(env_file))
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_status()
        out = capsys.readouterr().out
        assert rc == 0
        assert "live" in out
        assert "re-read" in out

    def test_status_flags_fresh_discovery(self, pid_file, with_default_dotenv, capsys):
        # Simulates the docker cp workflow: PID file says no .env was
        # tracked at startup, but a .env now exists in a default search
        # path. The classifier should tell the user that restart will
        # pick it up.
        state = _make_state(pid=os.getpid(), dotenv_path=None)
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_status()
        out = capsys.readouterr().out
        assert rc == 0
        assert "fresh-discovery" in out
        assert "use restart" in out


# ---------------------------------------------------------------------------
# Subcommand: reload / restart / stop (no-pid-file path is the safest
# self-contained assertion; signaling tests use a real subprocess below).
# ---------------------------------------------------------------------------


class TestSubcommandsAgainstMissingPidFile:
    def test_reload_no_pid_file(self, pid_file, capsys):
        rc = lifecycle.cmd_reload()
        out = capsys.readouterr().out
        assert rc == 1
        assert "No running zscaler-mcp server" in out

    def test_restart_no_pid_file(self, pid_file, capsys):
        rc = lifecycle.cmd_restart()
        out = capsys.readouterr().out
        assert rc == 1
        assert "No running zscaler-mcp server" in out

    def test_stop_no_pid_file(self, pid_file, capsys):
        rc = lifecycle.cmd_stop()
        out = capsys.readouterr().out
        assert rc == 1
        assert "No running zscaler-mcp server" in out


class TestSubcommandsAgainstStalePidFile:
    def test_reload_stale_pid_cleans_up(self, pid_file, capsys):
        lifecycle.write_pid_file(_make_state(pid=999_999_999), pid_file)
        rc = lifecycle.cmd_reload()
        assert rc == 1
        assert not pid_file.exists()  # stale file removed

    def test_restart_stale_pid_cleans_up(self, pid_file):
        lifecycle.write_pid_file(_make_state(pid=999_999_999), pid_file)
        rc = lifecycle.cmd_restart()
        assert rc == 1
        assert not pid_file.exists()

    def test_stop_stale_pid_cleans_up(self, pid_file):
        lifecycle.write_pid_file(_make_state(pid=999_999_999), pid_file)
        rc = lifecycle.cmd_stop()
        assert rc == 1
        assert not pid_file.exists()


# ---------------------------------------------------------------------------
# In-process signal-handler smoke tests
#
# Rather than spawning a subprocess (slow + flaky on CI), we install the
# handlers in *this* process, raise the signals via os.kill(getpid(), …),
# and assert side effects (env var refresh, log emission).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not hasattr(signal, "SIGHUP"), reason="SIGHUP unavailable")
class TestSighupReloadRefreshesEnv:
    def test_sighup_reloads_dotenv_and_audit_toggle(self, tmp_path, monkeypatch):
        # Start with audit logging OFF.
        monkeypatch.delenv("ZSCALER_MCP_LOG_TOOL_CALLS", raising=False)
        tool_helpers.disable_tool_call_logging()
        assert tool_helpers.is_tool_call_logging_enabled() is False

        # .env enables audit logging — reload should pick it up.
        env_file = tmp_path / ".env"
        env_file.write_text("ZSCALER_MCP_LOG_TOOL_CALLS=true\n")

        state = _make_state(pid=os.getpid(), dotenv_path=str(env_file))

        # Install handlers, then send SIGHUP to ourselves.
        prev = signal.getsignal(signal.SIGHUP)
        try:
            lifecycle.install_serve_handlers(state, str(env_file))
            os.kill(os.getpid(), signal.SIGHUP)
            # Give the signal handler a moment to land.
            time.sleep(0.1)

            assert os.environ.get("ZSCALER_MCP_LOG_TOOL_CALLS") == "true"
            assert tool_helpers.is_tool_call_logging_enabled() is True
        finally:
            signal.signal(signal.SIGHUP, prev)
            tool_helpers.disable_tool_call_logging()


# ---------------------------------------------------------------------------
# tool_helpers refresh helper (independent of signals)
# ---------------------------------------------------------------------------


class TestRefreshToolCallLogging:
    def test_enables_when_env_true(self, monkeypatch):
        tool_helpers.disable_tool_call_logging()
        monkeypatch.setenv("ZSCALER_MCP_LOG_TOOL_CALLS", "true")
        tool_helpers.refresh_tool_call_logging()
        assert tool_helpers.is_tool_call_logging_enabled() is True
        tool_helpers.disable_tool_call_logging()

    def test_disables_when_env_false(self, monkeypatch):
        tool_helpers.enable_tool_call_logging()
        monkeypatch.setenv("ZSCALER_MCP_LOG_TOOL_CALLS", "false")
        tool_helpers.refresh_tool_call_logging()
        assert tool_helpers.is_tool_call_logging_enabled() is False

    def test_idempotent(self, monkeypatch):
        monkeypatch.delenv("ZSCALER_MCP_LOG_TOOL_CALLS", raising=False)
        tool_helpers.disable_tool_call_logging()
        tool_helpers.refresh_tool_call_logging()
        tool_helpers.refresh_tool_call_logging()
        assert tool_helpers.is_tool_call_logging_enabled() is False


# ---------------------------------------------------------------------------
# argparse integration: subparsers register without breaking parse
# ---------------------------------------------------------------------------


class TestArgparseSubparsers:
    def test_register_subparsers_does_not_break_default_parse(self):
        import argparse

        parser = argparse.ArgumentParser()
        # Add a few "real" args to mimic the server parser surface.
        parser.add_argument("--transport", default="stdio")
        lifecycle.register_subparsers(parser)

        # Default (no subcommand) → command is None.
        args = parser.parse_args([])
        assert args.command is None
        assert args.transport == "stdio"

        # Each subcommand parses cleanly.
        for cmd in ("reload", "restart", "status", "stop", "update"):
            args = parser.parse_args([cmd])
            assert args.command == cmd

    def test_update_apply_flag(self):
        import argparse

        parser = argparse.ArgumentParser()
        lifecycle.register_subparsers(parser)

        args = parser.parse_args(["update"])
        assert args.apply is False

        args = parser.parse_args(["update", "--apply"])
        assert args.apply is True

    def test_dispatch_unknown_returns_2(self, capsys):
        rc = lifecycle.dispatch("bogus")
        err = capsys.readouterr().err
        assert rc == 2
        assert "unknown lifecycle subcommand" in err


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------


class TestClassifyEnvSource:
    """The classifier is what makes reload/restart messages honest.

    These tests pin every branch so a future refactor doesn't reintroduce
    the misleading "will re-read .env" message in the no-bind-mount case.
    """

    def test_no_dotenv_no_default_returns_none_label(self, no_default_dotenv):
        state = _make_state(pid=1, dotenv_path=None)
        label, advice = lifecycle._classify_env_source(state)
        assert label == "none"
        assert "no .env was loaded" in advice
        assert "will NOT pick up" in advice
        assert "docker cp" in advice

    def test_missing_dotenv_returns_missing_label(self, tmp_path, no_default_dotenv):
        ghost = tmp_path / "does-not-exist.env"
        state = _make_state(pid=1, dotenv_path=str(ghost))
        label, advice = lifecycle._classify_env_source(state)
        assert label == "missing"
        assert "does not exist" in advice
        assert "docker cp" in advice
        assert "will NOT pick up" in advice

    def test_existing_dotenv_returns_live_label(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\n")
        state = _make_state(pid=1, dotenv_path=str(env_file))
        label, advice = lifecycle._classify_env_source(state)
        assert label == "live"
        assert "re-read" in advice
        assert "Live edits" in advice

    def test_app_dotenv_marks_bind_mount(self, monkeypatch):
        # Inside a container the canonical path is /app/.env; the
        # classifier surfaces that as "live (bind-mounted)" so admins
        # know the host edits are live.
        state = _make_state(pid=1, dotenv_path="/app/.env")
        monkeypatch.setattr(
            "zscaler_mcp.lifecycle.os.path.isfile",
            lambda p: p == "/app/.env",
        )
        label, _ = lifecycle._classify_env_source(state)
        assert label == "live (bind-mounted)"

    def test_fresh_discovery_when_default_path_exists(self, with_default_dotenv):
        # PID file says no .env was tracked, but a .env exists in a
        # default search slot (e.g. after `docker cp ./.env <ctr>:/app/.env`).
        # The fresh execvp'd child will discover it; classifier must say so.
        state = _make_state(pid=1, dotenv_path=None)
        label, advice = lifecycle._classify_env_source(state)
        assert label == "fresh-discovery"
        assert str(with_default_dotenv) in advice
        assert "after restart" in advice
        assert "SIGHUP reload alone will NOT" in advice

    def test_fresh_discovery_supersedes_missing_recorded_path(self, tmp_path, with_default_dotenv):
        # PID file recorded a path that no longer exists, but a default-
        # path .env was placed since then. Restart-then-discover beats
        # the stale "missing" message.
        ghost = tmp_path / "ghost.env"
        state = _make_state(pid=1, dotenv_path=str(ghost))
        label, _ = lifecycle._classify_env_source(state)
        assert label == "fresh-discovery"

    def test_fresh_discovery_app_path_marks_bind_mount(self, monkeypatch):
        planted = Path("/app/.env")
        monkeypatch.setattr(
            "zscaler_mcp.lifecycle._default_dotenv_candidates",
            lambda: [planted],
        )
        monkeypatch.setattr(
            "zscaler_mcp.lifecycle.Path.is_file",
            lambda self: str(self) == "/app/.env",
        )
        state = _make_state(pid=1, dotenv_path=None)
        label, _ = lifecycle._classify_env_source(state)
        assert label == "fresh-discovery (bind-mounted)"


@pytest.fixture
def signal_noop():
    """Install no-op handlers for SIGHUP and SIGUSR2.

    The reload/restart tests below call ``cmd_reload()`` / ``cmd_restart()``
    which signal ``os.getpid()`` to verify the messaging — without this
    fixture the default kernel action for SIGUSR2 is "terminate", which
    would kill the pytest process (exit 159 = 128+31).
    """
    prev = {}
    for sig_name in ("SIGHUP", "SIGUSR2"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            prev[sig] = signal.signal(sig, lambda *_: None)
    yield
    for sig, handler in prev.items():
        signal.signal(sig, handler)


class TestReloadRestartMessaging:
    """Regression: reload/restart output must reflect the env source.

    Prevents the "will re-read .env" lie in the docker --env-file-only case.
    """

    def test_restart_message_mentions_missing_when_dotenv_absent(
        self, pid_file, no_default_dotenv, signal_noop, capsys
    ):
        state = _make_state(pid=os.getpid(), dotenv_path="/app/.env")
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_restart()
        out = capsys.readouterr().out
        assert rc == 0
        assert "env source : missing" in out
        assert "docker cp" in out

    def test_reload_message_mentions_none_when_no_dotenv(
        self, pid_file, no_default_dotenv, signal_noop, capsys
    ):
        state = _make_state(pid=os.getpid(), dotenv_path=None)
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_reload()
        out = capsys.readouterr().out
        assert rc == 0
        assert "env source : none" in out

    def test_reload_message_mentions_live_when_dotenv_exists(
        self, pid_file, tmp_path, signal_noop, capsys
    ):
        env_file = tmp_path / ".env"
        env_file.write_text("X=1\n")
        state = _make_state(pid=os.getpid(), dotenv_path=str(env_file))
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_reload()
        out = capsys.readouterr().out
        assert rc == 0
        assert "env source : live" in out

    def test_restart_message_mentions_fresh_discovery_after_docker_cp(
        self, pid_file, with_default_dotenv, signal_noop, capsys
    ):
        # Operator did `docker cp ./.env <ctr>:/app/.env`; PID file was
        # written when no .env existed (dotenv_path=None). Restart must
        # tell them the new process will discover the freshly-injected file.
        state = _make_state(pid=os.getpid(), dotenv_path=None)
        lifecycle.write_pid_file(state, pid_file)
        rc = lifecycle.cmd_restart()
        out = capsys.readouterr().out
        assert rc == 0
        assert "fresh-discovery" in out
        assert str(with_default_dotenv) in out


class TestSoftReloadMissingDotenv:
    """The soft-reload helper should log honestly, not silently no-op."""

    def test_logs_warning_when_dotenv_path_does_not_exist(self, tmp_path, caplog):
        ghost = tmp_path / "nope.env"
        with caplog.at_level("WARNING", logger="zscaler_mcp.lifecycle"):
            lifecycle._do_soft_reload(str(ghost))
        assert any("does not exist" in r.getMessage() for r in caplog.records)

    def test_logs_info_when_no_dotenv_path(self, caplog):
        with caplog.at_level("INFO", logger="zscaler_mcp.lifecycle"):
            lifecycle._do_soft_reload(None)
        assert any("no dotenv path recorded" in r.getMessage() for r in caplog.records)


class TestFormatUptime:
    @pytest.mark.parametrize(
        "seconds,expected_substring",
        [
            (5, "5s"),
            (65, "1m 5s"),
            (3725, "1h 2m 5s"),
            (90061, "1d 1h 1m"),
        ],
    )
    def test_renders_human_friendly(self, seconds, expected_substring):
        assert expected_substring in lifecycle._format_uptime(seconds)


# ---------------------------------------------------------------------------
# `update` subcommand — version check + on-demand upgrade
# ---------------------------------------------------------------------------


class TestVersionTuple:
    @pytest.mark.parametrize(
        "newer,older",
        [
            ("0.13.0", "0.12.6"),
            ("0.12.10", "0.12.9"),
            ("1.0.0", "0.99.99"),
            ("0.13.0", "0.13"),
        ],
    )
    def test_ordering(self, newer, older):
        assert lifecycle._version_tuple(newer) > lifecycle._version_tuple(older)

    def test_equal(self):
        assert lifecycle._version_tuple("0.12.6") == lifecycle._version_tuple("0.12.6")

    def test_non_numeric_components_never_raise(self):
        assert lifecycle._version_tuple("3rc1.x.2") == (3, 0, 2)
        assert lifecycle._version_tuple("") == (0,)


class TestFetchLatestVersion:
    def test_github_primary(self, monkeypatch):
        monkeypatch.setattr(
            lifecycle,
            "_http_get_json",
            lambda url: {
                "tag_name": "v0.13.0",
                "html_url": "https://github.com/zscaler/zscaler-mcp-server/releases/tag/v0.13.0",
            },
        )
        version, url = lifecycle._fetch_latest_version()
        assert version == "0.13.0"
        assert "releases/tag/v0.13.0" in url

    def test_pypi_fallback_when_github_fails(self, monkeypatch):
        def fake_get(url):
            if "api.github.com" in url:
                raise OSError("rate limited")
            return {"info": {"version": "0.13.0"}}

        monkeypatch.setattr(lifecycle, "_http_get_json", fake_get)
        version, url = lifecycle._fetch_latest_version()
        assert version == "0.13.0"
        assert url == lifecycle.PYPI_PROJECT_URL

    def test_none_when_both_fail(self, monkeypatch):
        def fake_get(url):
            raise OSError("no egress")

        monkeypatch.setattr(lifecycle, "_http_get_json", fake_get)
        assert lifecycle._fetch_latest_version() is None


class TestRunningInContainer:
    def test_dockerenv_marker(self, tmp_path):
        marker = tmp_path / ".dockerenv"
        marker.touch()
        assert lifecycle._running_in_container(dockerenv=marker, cgroup=tmp_path / "absent")

    def test_cgroup_marker(self, tmp_path):
        cgroup = tmp_path / "cgroup"
        cgroup.write_text("12:memory:/docker/abc123\n")
        assert lifecycle._running_in_container(dockerenv=tmp_path / "absent", cgroup=cgroup)

    def test_kubepods_marker(self, tmp_path):
        cgroup = tmp_path / "cgroup"
        cgroup.write_text("0::/kubepods.slice/kubepods-pod\n")
        assert lifecycle._running_in_container(dockerenv=tmp_path / "absent", cgroup=cgroup)

    def test_plain_host(self, tmp_path):
        cgroup = tmp_path / "cgroup"
        cgroup.write_text("0::/init.scope\n")
        assert not lifecycle._running_in_container(dockerenv=tmp_path / "absent", cgroup=cgroup)

    def test_no_cgroup_file(self, tmp_path):
        assert not lifecycle._running_in_container(
            dockerenv=tmp_path / "absent", cgroup=tmp_path / "also-absent"
        )


@pytest.fixture
def update_check(monkeypatch):
    """Pin the version check to installed=0.12.6, latest=0.13.0."""
    monkeypatch.setattr(lifecycle, "_current_version", lambda: "0.12.6")
    monkeypatch.setattr(
        lifecycle,
        "_fetch_latest_version",
        lambda: ("0.13.0", "https://example.invalid/v0.13.0"),
    )


class TestCmdUpdateCheckOnly:
    def test_up_to_date(self, monkeypatch, capsys):
        monkeypatch.setattr(lifecycle, "_current_version", lambda: "0.13.0")
        monkeypatch.setattr(
            lifecycle,
            "_fetch_latest_version",
            lambda: ("0.13.0", "https://example.invalid/v0.13.0"),
        )
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: "venv")
        rc = lifecycle.cmd_update(apply=False)
        out = capsys.readouterr().out
        assert rc == 0
        assert "Already up to date." in out

    def test_update_available_reports_hint(self, update_check, monkeypatch, capsys):
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: "venv")
        rc = lifecycle.cmd_update(apply=False)
        out = capsys.readouterr().out
        assert rc == 0
        assert "Update available: 0.12.6 -> 0.13.0" in out
        assert "--apply" in out

    def test_container_hint_points_at_image_pull(self, update_check, monkeypatch, capsys):
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: "container")
        rc = lifecycle.cmd_update(apply=False)
        out = capsys.readouterr().out
        assert rc == 0
        assert "docker pull zscaler/zscaler-mcp-server:0.13.0" in out

    def test_check_failure_returns_1(self, monkeypatch, capsys):
        monkeypatch.setattr(lifecycle, "_current_version", lambda: "0.12.6")
        monkeypatch.setattr(lifecycle, "_fetch_latest_version", lambda: None)
        rc = lifecycle.cmd_update(apply=False)
        err = capsys.readouterr().err
        assert rc == 1
        assert "could not reach GitHub or PyPI" in err


class TestCmdUpdateApply:
    @pytest.mark.parametrize("channel", ["container", "uvx", "editable"])
    def test_refuses_unsupported_channels(self, update_check, monkeypatch, capsys, channel):
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: channel)

        def boom(*args, **kwargs):
            raise AssertionError("subprocess must not run for refused channels")

        monkeypatch.setattr(lifecycle.subprocess, "run", boom)
        rc = lifecycle.cmd_update(apply=True)
        err = capsys.readouterr().err
        assert rc == 2
        assert f"'{channel}'" in err

    def test_apply_no_running_server(self, update_check, monkeypatch, pid_file, capsys):
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: "venv")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)

            class Result:
                returncode = 0
                stderr = ""
                # The verify subprocess prints the freshly-installed version.
                stdout = "0.13.0\n"

            return Result()

        monkeypatch.setattr(lifecycle.subprocess, "run", fake_run)
        rc = lifecycle.cmd_update(apply=True)
        out = capsys.readouterr().out

        assert rc == 0
        # First call: the pip upgrade, pinned to the resolved latest.
        assert calls[0][1:] == ["-m", "pip", "install", "--upgrade", "zscaler-mcp==0.13.0"]
        # Second call: fresh-interpreter verification.
        assert calls[1][1] == "-c"
        assert "Upgraded to 0.13.0." in out
        assert "No running server found" in out

    def test_apply_pip_failure_prints_rollback(self, update_check, monkeypatch, pid_file, capsys):
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: "venv")

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 1
                stderr = "ERROR: No matching distribution found"
                stdout = ""

            return Result()

        monkeypatch.setattr(lifecycle.subprocess, "run", fake_run)
        rc = lifecycle.cmd_update(apply=True)
        err = capsys.readouterr().err
        assert rc == 1
        assert "pip upgrade failed" in err
        assert "zscaler-mcp==0.12.6" in err  # rollback pin

    def test_apply_verify_mismatch_fails(self, update_check, monkeypatch, pid_file, capsys):
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: "venv")

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stderr = ""
                stdout = "0.12.6\n"  # verify still sees the old version

            return Result()

        monkeypatch.setattr(lifecycle.subprocess, "run", fake_run)
        rc = lifecycle.cmd_update(apply=True)
        err = capsys.readouterr().err
        assert rc == 1
        assert "verification failed" in err

    @pytest.mark.skipif(not hasattr(signal, "SIGUSR2"), reason="SIGUSR2 is Unix-only")
    def test_apply_restarts_running_server(self, update_check, monkeypatch, pid_file, capsys):
        monkeypatch.setattr(lifecycle, "_detect_install_channel", lambda: "venv")

        # A live "server": this very process, with a no-op SIGUSR2 handler
        # installed so the kill() doesn't terminate pytest.
        received = []
        previous = signal.signal(signal.SIGUSR2, lambda s, f: received.append(s))
        try:
            state = lifecycle.LifecycleState(
                pid=os.getpid(),
                started_at=time.time(),
                python_executable=sys.executable,
            )
            lifecycle.write_pid_file(state, pid_file)

            def fake_run(cmd, **kwargs):
                # The upgrade must target the running server's interpreter.
                assert cmd[0] == sys.executable

                class Result:
                    returncode = 0
                    stderr = ""
                    stdout = "0.13.0\n"

                return Result()

            monkeypatch.setattr(lifecycle.subprocess, "run", fake_run)
            rc = lifecycle.cmd_update(apply=True)
            out = capsys.readouterr().out

            assert rc == 0
            assert received == [signal.SIGUSR2]
            assert "Sent SIGUSR2" in out
        finally:
            signal.signal(signal.SIGUSR2, previous)

    def test_dispatch_routes_update_with_apply(self, monkeypatch):
        import argparse

        seen = {}

        def fake_cmd_update(apply=False):
            seen["apply"] = apply
            return 0

        monkeypatch.setattr(lifecycle, "cmd_update", fake_cmd_update)
        args = argparse.Namespace(apply=True)
        assert lifecycle.dispatch("update", args) == 0
        assert seen == {"apply": True}
