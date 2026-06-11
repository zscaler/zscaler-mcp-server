"""Process lifecycle management for the Zscaler MCP Server.

Implements the CLI subcommands ``zscaler-mcp reload`` /
``zscaler-mcp restart`` / ``zscaler-mcp status`` / ``zscaler-mcp stop``
that work identically whether the server is running natively as a
Python process or inside a container (via ``docker exec
zscaler-mcp-server zscaler-mcp <subcommand>``).

The pattern follows the standard Unix daemon contract:

* On startup the running server writes a PID file containing its PID,
  start time, port, transport, and the ``.env`` path it loaded from.
* The CLI subcommands read the PID file and signal the running process:

  - ``reload`` (SIGHUP) — soft reload: re-read ``.env`` (with ``override=True``),
    drop the lazy SDK client cache, drop the entitlement-bearer cache.
    MCP sessions survive; the listening socket is preserved.
  - ``restart`` (SIGUSR2) — hard restart: re-read ``.env`` into the parent's
    ``os.environ`` then ``os.execvp`` the same Python interpreter with the
    original argv. Same PID (Docker doesn't notice), fresh memory, fresh env
    values. Sessions die; clients reconnect. We deliberately use SIGUSR2 (not
    SIGTERM) so that ``docker stop`` / ``systemctl stop`` / Ctrl+C continue to
    behave normally — they send SIGTERM/SIGINT which we leave un-handled (i.e.
    the FastMCP/uvicorn-default clean shutdown).
  - ``stop`` (SIGTERM) — clean shutdown, no respawn. Same signal Docker uses,
    so the running server doesn't need a special handler at all.
  - ``status`` — print PID, uptime, port, dotenv path, transport.
  - ``update`` — check GitHub Releases (PyPI fallback) for a newer version
    and report it. With ``--apply``, pip-upgrade the package in place and
    SIGUSR2-restart the running server — pip/venv installs only; inside a
    container it refuses and prints the image-pull recipe instead.

* On clean exit the server removes its PID file (atexit-registered).

The PID file location is, in order of priority:

1. ``$ZSCALER_MCP_PID_FILE`` if set
2. ``/var/run/zscaler-mcp.pid`` if the directory is writable (typical
   inside containers running as root or a user with write access there)
3. ``/tmp/zscaler-mcp.pid`` (universally writable fallback)
4. ``~/.zscaler-mcp/server.pid`` if even ``/tmp`` is not writable

Multiple instances on the same host: override
``ZSCALER_MCP_PID_FILE=/tmp/zscaler-mcp-8001.pid`` per instance.

Cross-platform: Unix-only. SIGHUP doesn't exist on Windows; the
``reload``/``restart``/``stop`` subcommands fall back to a clear error
message there. Container deployments are unaffected (Linux). Native
Windows operators can still use ``zscaler-mcp status`` to inspect the
PID file without signaling.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# PID file location
# ============================================================================

PID_FILE_ENV = "ZSCALER_MCP_PID_FILE"


def _writable_dir(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK)


def default_pid_file_path() -> Path:
    """Resolve the default PID file path for this host.

    Priority: ``$ZSCALER_MCP_PID_FILE`` > ``/var/run`` > ``/tmp`` >
    ``~/.zscaler-mcp/``. The chosen directory is created on demand for
    the home-dir fallback only — the others must already exist.
    """
    override = os.environ.get(PID_FILE_ENV, "").strip()
    if override:
        return Path(override).expanduser()

    candidates: List[Path] = [
        Path("/var/run"),
        Path("/tmp"),
    ]
    for d in candidates:
        if _writable_dir(d):
            return d / "zscaler-mcp.pid"

    home_dir = Path.home() / ".zscaler-mcp"
    home_dir.mkdir(parents=True, exist_ok=True)
    return home_dir / "server.pid"


# ============================================================================
# PID file payload
# ============================================================================


@dataclass
class LifecycleState:
    """Serialized PID-file contents.

    We persist enough metadata to (a) identify the running process,
    (b) reload the same ``.env`` source on SIGHUP, and (c) re-exec the
    same Python entrypoint on SIGTERM-restart.
    """

    pid: int
    started_at: float
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    dotenv_path: Optional[str] = None
    argv: List[str] = field(default_factory=list)
    python_executable: str = sys.executable
    version: str = "unknown"

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "LifecycleState":
        data = json.loads(text)
        return cls(**data)


def write_pid_file(state: LifecycleState, path: Optional[Path] = None) -> Path:
    """Atomically write ``state`` to the PID file."""
    target = path or default_pid_file_path()
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(state.to_json())
    os.replace(tmp, target)
    logger.debug("Wrote PID file: %s (pid=%d)", target, state.pid)
    return target


def read_pid_file(path: Optional[Path] = None) -> Optional[LifecycleState]:
    """Read the PID file; return ``None`` if absent or unparsable."""
    target = path or default_pid_file_path()
    if not target.exists():
        return None
    try:
        return LifecycleState.from_json(target.read_text())
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("PID file %s is unparsable (%s) — ignoring", target, exc)
        return None


def remove_pid_file(path: Optional[Path] = None) -> None:
    """Remove the PID file if present. Best-effort, never raises."""
    target = path or default_pid_file_path()
    try:
        target.unlink(missing_ok=True)
        logger.debug("Removed PID file: %s", target)
    except OSError as exc:
        logger.debug("Could not remove PID file %s: %s", target, exc)


def is_process_alive(pid: int) -> bool:
    """Probe a PID with signal 0 — true if the process exists and we can signal it."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission. Treat as alive for
        # status purposes — the user will see a clearer error if they try
        # to actually signal it.
        return True
    return True


# ============================================================================
# Signal handlers (installed in the running server)
# ============================================================================


def install_serve_handlers(state: LifecycleState, dotenv_path: Optional[str]) -> None:
    """Install SIGHUP (reload) and SIGUSR2 (restart) handlers in the running server.

    The handlers reference ``state`` by closure so they always re-read
    the same ``.env`` source the operator started with.

    SIGTERM and SIGINT are intentionally **not** handled here so that
    ``docker stop`` / ``systemctl stop`` / Ctrl+C keep their standard
    clean-shutdown behaviour. The ``zscaler-mcp stop`` subcommand sends
    plain SIGTERM and relies on FastMCP/uvicorn's default shutdown.

    Cross-platform: SIGHUP and SIGUSR2 are Unix-only. The corresponding
    handlers are silently skipped on Windows; native Windows operators
    must restart the supervisor (Docker, NSSM, etc.) directly.
    """

    def _reload_handler(signum: int, frame) -> None:  # noqa: ANN001 - signal API
        logger.info("[LIFECYCLE] SIGHUP received — soft reload")
        try:
            _do_soft_reload(dotenv_path)
            logger.info("[LIFECYCLE] reload complete — sessions preserved")
        except Exception as exc:  # noqa: BLE001 - signal handlers must not raise
            logger.exception("[LIFECYCLE] reload failed: %s", exc)

    def _restart_handler(signum: int, frame) -> None:  # noqa: ANN001
        logger.info("[LIFECYCLE] SIGUSR2 received — hard restart via execvp")
        try:
            # Pull fresh values into os.environ so the child inherits them.
            # The child will also re-load .env on startup (idempotent),
            # but doing it here means the new process starts with the
            # right env even before its own dotenv pass runs.
            _do_soft_reload(dotenv_path)
            remove_pid_file()
            os.execvp(state.python_executable, [state.python_executable, *state.argv])
        except Exception as exc:  # noqa: BLE001
            logger.exception("[LIFECYCLE] restart failed: %s — exiting", exc)
            os._exit(1)

    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _reload_handler)
        logger.debug("Installed SIGHUP handler (zscaler-mcp reload)")

    if hasattr(signal, "SIGUSR2"):
        signal.signal(signal.SIGUSR2, _restart_handler)
        logger.debug("Installed SIGUSR2 handler (zscaler-mcp restart)")


def _do_soft_reload(dotenv_path: Optional[str]) -> None:
    """Re-read ``.env`` and refresh env-driven runtime toggles.

    The Zscaler SDK client is created lazily on every tool call (no
    module-level cache), so once new credentials land in ``os.environ``
    the next tool call already picks them up. The auth-middleware token
    cache is keyed by credential hash, so credential changes naturally
    miss the old entries and re-validate against the new values.

    What this function actually does:

    * Re-loads the operator's ``.env`` file with ``override=True`` so
      stale values get replaced.
    * Re-applies env-driven toggles that are read once at startup
      (currently: ``ZSCALER_MCP_LOG_TOOL_CALLS``).

    Importing here keeps the lifecycle module free of an upfront
    dependency on the rest of the package, so the CLI subcommands
    themselves don't pay the import cost.
    """
    if not dotenv_path:
        logger.info(
            "[LIFECYCLE] no dotenv path recorded at startup — skipping .env "
            "reload (env vars are inherited from the existing process "
            "environment unchanged)"
        )
    elif not os.path.isfile(dotenv_path):
        logger.warning(
            "[LIFECYCLE] dotenv path %s does not exist — skipping .env "
            "reload. To enable live reload in a container, bind-mount the "
            "host .env at /app/.env (e.g. -v $(pwd)/.env:/app/.env:ro).",
            dotenv_path,
        )
    else:
        try:
            from dotenv import load_dotenv

            loaded = load_dotenv(dotenv_path, override=True)
            logger.info("[LIFECYCLE] re-loaded .env from %s (loaded=%s)", dotenv_path, loaded)
        except ImportError:
            logger.warning("[LIFECYCLE] python-dotenv not available — skipping .env reload")

    try:
        from zscaler_mcp.common.tool_helpers import refresh_tool_call_logging

        refresh_tool_call_logging()
    except ImportError:
        pass


# ============================================================================
# CLI subcommands
# ============================================================================


_SUBCOMMAND_HELP = "Process-lifecycle management. Run with no subcommand to launch the server."


def register_subparsers(parser: argparse.ArgumentParser) -> None:
    """Add ``reload`` / ``restart`` / ``status`` / ``stop`` subparsers.

    Designed to coexist with the existing top-level argparse surface:
    the subcommand is captured in ``args.command`` (None when the user
    runs the bare ``zscaler-mcp`` for the serve path).

    Implementation note: we use ``add_subparsers(required=False)`` so
    the existing default behaviour (no subcommand → start the server)
    is preserved. Backward compatible with every prior CLI invocation.
    """
    subparsers = parser.add_subparsers(
        dest="command",
        title="subcommands",
        description=_SUBCOMMAND_HELP,
        metavar="{reload,restart,status,stop,update}",
    )

    subparsers.add_parser(
        "reload",
        help=(
            "Send SIGHUP to the running server: re-read .env and re-apply "
            "env-driven runtime toggles (e.g. ZSCALER_MCP_LOG_TOOL_CALLS). "
            "MCP sessions and the listening socket survive. The Zscaler "
            "SDK has no module-level cache; new credentials in .env take "
            "effect on the next tool call."
        ),
    )
    subparsers.add_parser(
        "restart",
        help=(
            "Send SIGUSR2 to the running server: it re-reads .env, then "
            "execvp's a fresh Python interpreter with the same argv. Same "
            "PID, fresh memory, fresh module imports, fresh env. Sessions "
            "die — clients reconnect. Use this for credential rotation or "
            "any startup-only config change (toolset selection, write-tool "
            "allowlist, etc.)."
        ),
    )
    subparsers.add_parser(
        "status",
        help=(
            "Print PID, uptime, transport, port, and .env path of the "
            "running server (or report none running)."
        ),
    )
    subparsers.add_parser(
        "stop",
        help=(
            "Send SIGTERM to the running server for a clean shutdown "
            "without respawn. SIGTERM is intentionally not handled by the "
            "server, so this falls through to the FastMCP/uvicorn default "
            "and matches `docker stop` behaviour. Use 'restart' to keep "
            "the service running with fresh config."
        ),
    )
    update_parser = subparsers.add_parser(
        "update",
        help=(
            "Check GitHub Releases (PyPI fallback) for a newer version and "
            "report installed vs latest. With --apply, pip-upgrade the "
            "package in place and restart the running server (SIGUSR2) — "
            "supported for plain pip/venv installs only. Inside a "
            "container --apply refuses and prints the image-pull recipe "
            "instead: the image is the source of truth there, and an "
            "in-place change would be silently lost on the next recreate."
        ),
    )
    update_parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help=(
            "Apply the update: pip install --upgrade into the running "
            "server's environment (or this CLI's environment when no "
            "server is running), verify the install, then SIGUSR2-restart "
            "the server so the new version loads. Without this flag, "
            "'update' only checks and reports."
        ),
    )


def dispatch(command: str, args: Optional[argparse.Namespace] = None) -> int:
    """Run a lifecycle subcommand. Returns the process exit code.

    ``args`` carries subcommand-specific flags (currently only
    ``update --apply``); the signal-based subcommands ignore it.
    """
    if command == "reload":
        return cmd_reload()
    if command == "restart":
        return cmd_restart()
    if command == "status":
        return cmd_status()
    if command == "stop":
        return cmd_stop()
    if command == "update":
        return cmd_update(apply=bool(getattr(args, "apply", False)))
    print(f"unknown lifecycle subcommand: {command}", file=sys.stderr)
    return 2


# ----------------------------------------------------------------------------
# Subcommand implementations
# ----------------------------------------------------------------------------


def _signal_unsupported_on_windows() -> int:
    print(
        "ERROR: zscaler-mcp reload/restart/stop are Unix-only "
        "(Windows lacks the required signals). Use 'zscaler-mcp status' "
        "to inspect the PID file, or restart your supervisor (Docker, "
        "systemd, etc.) directly.",
        file=sys.stderr,
    )
    return 2


def _no_running_server(path: Path) -> int:
    print(f"No running zscaler-mcp server found (PID file {path} missing).")
    return 1


def _stale_pid_file(path: Path, pid: int) -> int:
    print(
        f"PID file {path} references pid {pid}, but no such process exists. "
        f"The server likely crashed or was killed; removing the stale file.",
        file=sys.stderr,
    )
    remove_pid_file(path)
    return 1


def _default_dotenv_candidates() -> list[Path]:
    """Paths the server searches for ``.env`` at startup.

    Mirrors ``zscaler_mcp.server._resolve_dotenv_path`` so the lifecycle
    classifier can predict what the FRESH execvp'd process will load.
    Order matters — same priority as the server uses.
    """
    pkg_dir = Path(__file__).resolve().parent
    project_root = pkg_dir.parent
    return [project_root / ".env", Path.cwd() / ".env"]


def _classify_env_source(state: LifecycleState) -> tuple[str, str]:
    """Classify the env source the next reload/restart will actually act on.

    Returns ``(label, advice)``:

    * ``label`` is a short tag for status output. Five values:

      - ``"live"`` / ``"live (bind-mounted)"`` — recorded path exists and
        will be re-read on reload/restart. (``live (bind-mounted)`` if the
        path is under ``/app/``, the canonical container WORKDIR.)
      - ``"fresh-discovery"`` — recorded path is missing/empty, but a
        ``.env`` exists in one of the default search locations. The
        execvp'd child will discover and load it. Common after a one-off
        ``docker cp ./.env <container>:/app/.env``.
      - ``"missing"`` — recorded path doesn't exist AND no default-path
        ``.env`` exists either. Restart is a pure memory-reset.
      - ``"none"`` — no ``.env`` was loaded at startup AND no default-path
        ``.env`` exists now. Same memory-reset semantics.

    * ``advice`` is a human-readable line tailored to ``reload`` / ``restart``
      messages so the user understands what will and won't change.

    Why the classifier exists: env vars in a running container's PID 1 are
    immutable from outside the container — there's no Unix API for one
    process to mutate another's environment. The only ways to actually
    change them are:

    1. Bind-mount a ``.env`` so PID 1 can re-read it on reload (best
       long-term workflow).
    2. ``docker cp ./.env <container>:/app/.env`` to inject the file as
       a one-shot, then ``restart`` (the fresh process re-discovers it).
    3. ``docker rm -f`` + ``docker run`` (forces Docker to re-read the
       host's ``.env`` at run-time and bake fresh values into ``Config.Env``).

    Without one of those, ``restart`` is essentially a memory reset — same
    env, fresh interpreter — which is rarely what the user wants. The
    classifier surfaces this so the CLI tells the truth.
    """
    dotenv = state.dotenv_path

    if dotenv and os.path.isfile(dotenv):
        label = "live (bind-mounted)" if dotenv.startswith("/app/") else "live"
        return (
            label,
            f"the server will re-read {dotenv} (override=True) before "
            f"re-execing. Live edits to that file will be picked up.",
        )

    # Recorded path is None or missing. Check if the fresh process will
    # discover a .env via the default search paths — this covers the
    # `docker cp ./.env <container>:/app/.env` workflow without requiring
    # the operator to set --dotenv-path or restart the container.
    discovered = next(
        (p for p in _default_dotenv_candidates() if p.is_file()),
        None,
    )
    if discovered is not None:
        location = str(discovered)
        label = (
            "fresh-discovery (bind-mounted)" if location.startswith("/app/") else "fresh-discovery"
        )
        return (
            label,
            f"no .env was tracked at startup, but a .env file is now "
            f"present at {location}. The fresh process (after restart) "
            f"will discover and load it. SIGHUP reload alone will NOT "
            f"pick it up — use restart.",
        )

    if dotenv:
        return (
            "missing",
            f"the .env path recorded in the PID file ({dotenv}) does not "
            f"exist, and no .env was found in the default search paths "
            f"either. The new process will inherit the same os.environ; "
            f"reload/restart will NOT pick up new values. Three fixes: "
            f"(a) `docker cp ./.env <container>:{dotenv}` + `restart`, "
            f"(b) recreate the container with `-v <host-path>/.env:{dotenv}:ro` "
            f"for ongoing edits, or (c) `docker rm -f` + `docker run` to "
            f"force Docker to re-read the host .env into Config.Env.",
        )

    return (
        "none",
        "no .env was loaded at startup, and no .env is present in the "
        "default search paths either. Env vars come from the process "
        "environment only (e.g. docker --env-file at boot, Secrets "
        "Manager, or `docker run -e KEY=VALUE`). The new process will "
        "inherit the same os.environ; reload/restart will NOT pick up "
        "new values. Three fixes: (a) `docker cp ./.env <container>:/app/.env` "
        "+ `restart`, (b) recreate with a bind-mount for ongoing edits, "
        "or (c) `docker rm -f` + `docker run --env-file` to bake new "
        "values into Config.Env.",
    )


def cmd_reload() -> int:
    """``zscaler-mcp reload`` — SIGHUP the running server."""
    if not hasattr(signal, "SIGHUP"):
        return _signal_unsupported_on_windows()

    path = default_pid_file_path()
    state = read_pid_file(path)
    if state is None:
        return _no_running_server(path)
    if not is_process_alive(state.pid):
        return _stale_pid_file(path, state.pid)

    try:
        os.kill(state.pid, signal.SIGHUP)
    except PermissionError:
        print(
            f"ERROR: not permitted to signal pid {state.pid}. "
            f"Run as the same user that started the server, or use sudo.",
            file=sys.stderr,
        )
        return 1
    except ProcessLookupError:
        return _stale_pid_file(path, state.pid)

    label, advice = _classify_env_source(state)
    print(f"Sent SIGHUP to zscaler-mcp (pid={state.pid}). MCP sessions preserved.")
    print(f"  env source : {label}")
    print(f"  effect     : {advice}")
    print("  also       : ZSCALER_MCP_LOG_TOOL_CALLS is re-applied from the current environment.")
    return 0


def cmd_restart() -> int:
    """``zscaler-mcp restart`` — SIGUSR2-trigger an in-place execvp."""
    if not hasattr(signal, "SIGUSR2"):
        return _signal_unsupported_on_windows()

    path = default_pid_file_path()
    state = read_pid_file(path)
    if state is None:
        return _no_running_server(path)
    if not is_process_alive(state.pid):
        return _stale_pid_file(path, state.pid)

    try:
        os.kill(state.pid, signal.SIGUSR2)
    except PermissionError:
        print(
            f"ERROR: not permitted to signal pid {state.pid}. "
            f"Run as the same user that started the server, or use sudo.",
            file=sys.stderr,
        )
        return 1
    except ProcessLookupError:
        return _stale_pid_file(path, state.pid)

    label, advice = _classify_env_source(state)
    print(
        f"Sent SIGUSR2 to zscaler-mcp (pid={state.pid}). The server will "
        f"re-exec itself in place (same PID, fresh interpreter)."
    )
    print(f"  env source : {label}")
    print(f"  effect     : {advice}")
    return 0


def cmd_stop() -> int:
    """``zscaler-mcp stop`` — clean shutdown via SIGTERM.

    The running server has no SIGTERM handler installed (deliberately —
    so ``docker stop`` and ``systemctl stop`` keep working), which means
    SIGTERM falls through to the FastMCP/uvicorn default: clean shutdown,
    no respawn.
    """
    path = default_pid_file_path()
    state = read_pid_file(path)
    if state is None:
        return _no_running_server(path)
    if not is_process_alive(state.pid):
        return _stale_pid_file(path, state.pid)

    try:
        os.kill(state.pid, signal.SIGTERM)
    except (PermissionError, ProcessLookupError) as exc:
        print(f"ERROR: could not signal pid {state.pid}: {exc}", file=sys.stderr)
        return 1

    print(f"Sent SIGTERM to zscaler-mcp (pid={state.pid}). Will not respawn.")
    return 0


def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def cmd_status() -> int:
    """``zscaler-mcp status`` — pretty-print PID-file state."""
    path = default_pid_file_path()
    state = read_pid_file(path)
    if state is None:
        print(f"No zscaler-mcp server PID file found at {path}.")
        return 1

    alive = is_process_alive(state.pid)
    uptime = time.time() - state.started_at if alive else 0

    env_label, env_advice = _classify_env_source(state)

    print("zscaler-mcp lifecycle status")
    print("=" * 40)
    print(f"  pid file          : {path}")
    print(f"  pid               : {state.pid}")
    print(f"  alive             : {'yes' if alive else 'NO (stale PID file)'}")
    if alive:
        print(f"  uptime            : {_format_uptime(uptime)}")
    print(f"  version           : {state.version}")
    print(f"  transport         : {state.transport}")
    if state.transport != "stdio":
        print(f"  bind              : {state.host}:{state.port}")
    print(f"  dotenv path       : {state.dotenv_path or '(none)'}")
    print(f"  env source        : {env_label}")
    print(f"  reload/restart    : {env_advice}")
    print(f"  python executable : {state.python_executable}")
    print(f"  argv              : {' '.join(state.argv) if state.argv else '(none)'}")
    return 0 if alive else 1


# ============================================================================
# `update` subcommand — version check + on-demand in-place upgrade
# ============================================================================

PYPI_PACKAGE = "zscaler-mcp"
GITHUB_RELEASES_LATEST_URL = (
    "https://api.github.com/repos/zscaler/zscaler-mcp-server/releases/latest"
)
PYPI_JSON_URL = f"https://pypi.org/pypi/{PYPI_PACKAGE}/json"
PYPI_PROJECT_URL = f"https://pypi.org/project/{PYPI_PACKAGE}/"
_HTTP_TIMEOUT_SECONDS = 5


def _http_get_json(url: str) -> dict:
    """GET ``url`` and parse the JSON body. Raises on any failure."""
    import urllib.request

    request = urllib.request.Request(
        url,
        headers={
            # GitHub's API rejects requests without a User-Agent.
            "User-Agent": f"zscaler-mcp/{_current_version()}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _current_version() -> str:
    """Installed version of this CLI's environment."""
    from zscaler_mcp.utils.utils import _get_package_version

    return _get_package_version()


def _fetch_latest_version() -> Optional[Tuple[str, str]]:
    """Resolve the latest released version.

    Returns ``(version, release_url)`` or ``None`` when neither source is
    reachable. GitHub Releases is primary — it is the one artifact every
    distribution channel (PyPI, Docker, MCPB) hangs off and it carries the
    release notes. PyPI JSON is the fallback.
    """
    try:
        data = _http_get_json(GITHUB_RELEASES_LATEST_URL)
        tag = str(data.get("tag_name") or "").lstrip("v")
        if tag:
            return tag, str(data.get("html_url") or PYPI_PROJECT_URL)
    except Exception as exc:  # noqa: BLE001 - network failures degrade to fallback
        logger.debug("GitHub release check failed (%s) — trying PyPI", exc)

    try:
        data = _http_get_json(PYPI_JSON_URL)
        version = str(data.get("info", {}).get("version") or "")
        if version:
            return version, PYPI_PROJECT_URL
    except Exception as exc:  # noqa: BLE001
        logger.debug("PyPI version check failed: %s", exc)

    return None


def _version_tuple(version: str) -> Tuple[int, ...]:
    """Parse ``X.Y.Z`` into a comparable int tuple.

    Releases are semantic-release generated (always plain ``X.Y.Z``), so a
    full PEP 440 parser is unnecessary. Non-numeric components degrade to
    their leading digits (``"3rc1"`` -> 3) or 0, never raise.
    """
    parts: List[int] = []
    for component in version.strip().split("."):
        digits = ""
        for ch in component:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _running_in_container(
    dockerenv: Path = Path("/.dockerenv"),
    cgroup: Path = Path("/proc/1/cgroup"),
) -> bool:
    """Detect a container runtime via /.dockerenv or PID 1's cgroup."""
    if dockerenv.exists():
        return True
    try:
        text = cgroup.read_text()
    except OSError:
        return False
    return any(marker in text for marker in ("docker", "containerd", "kubepods", "lxc"))


def _detect_install_channel() -> str:
    """Classify how this process's package was installed.

    Returns one of:

    * ``"container"`` — running inside Docker/Kubernetes. The image is the
      source of truth; in-place updates are lost on the next recreate (and
      the shipped image has no pip in its uv-built venv anyway).
    * ``"uvx"`` — running from a ``uvx`` / ``uv tool`` managed environment;
      uv owns the install and re-resolves from PyPI itself.
    * ``"editable"`` — editable install or bare source checkout; updates
      come from git, not PyPI.
    * ``"venv"`` — plain pip install inside a virtualenv (the systemd-VM
      shape). The one channel where ``--apply`` is supported.
    * ``"system"`` — plain pip install into the system interpreter. Also
      eligible for ``--apply`` (may need sudo).
    """
    if _running_in_container():
        return "container"

    if "uv" in Path(sys.prefix).parts:
        return "uvx"

    import importlib.metadata

    try:
        dist = importlib.metadata.distribution(PYPI_PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        # Importable but not pip-installed: bare source checkout.
        return "editable"
    direct_url = dist.read_text("direct_url.json")
    if direct_url:
        try:
            if json.loads(direct_url).get("dir_info", {}).get("editable"):
                return "editable"
        except (json.JSONDecodeError, AttributeError):
            pass

    return "venv" if sys.prefix != getattr(sys, "base_prefix", sys.prefix) else "system"


def _upgrade_hint(channel: str, latest: str) -> str:
    """One-line, channel-correct upgrade instruction."""
    if channel == "container":
        return (
            f"pull the new image and recreate the container: "
            f"`docker pull zscaler/zscaler-mcp-server:{latest}` (or "
            f"`helm upgrade --set image.tag={latest} ...`). In-place "
            f"updates inside a container are lost on the next recreate."
        )
    if channel == "uvx":
        return (
            "uvx re-resolves from PyPI: a fresh `uvx zscaler-mcp` session "
            "already picks up the new version (or run "
            "`uv tool upgrade zscaler-mcp` for a persistent uv tool install)."
        )
    if channel == "editable":
        return (
            "this is an editable/source install — update the checkout (`git pull`) instead of pip."
        )
    return "run `zscaler-mcp update --apply` to upgrade in place and restart."


def cmd_update(apply: bool = False) -> int:
    """``zscaler-mcp update`` — check for (and optionally apply) a new version.

    Without ``--apply``: report installed vs latest plus the channel-correct
    upgrade instruction. Exit 0 (also when already up to date), exit 1 when
    neither GitHub nor PyPI is reachable.

    With ``--apply`` (pip/venv and system installs only): pin-upgrade to the
    resolved latest version in the **running server's** interpreter
    environment (falling back to this CLI's interpreter when no server is
    running), verify the install with a fresh interpreter, then SIGUSR2 the
    running server so ``os.execvp`` re-imports the new code in place. The
    upgrade runs in this CLI process — never inside the server — so the
    server process is never asked to mutate its own loaded packages.
    """
    current = _current_version()
    fetched = _fetch_latest_version()
    if fetched is None:
        print(
            "ERROR: could not reach GitHub or PyPI to determine the latest "
            "version (no network egress, or both endpoints are down). "
            "Try again later or check https://github.com/zscaler/"
            "zscaler-mcp-server/releases manually.",
            file=sys.stderr,
        )
        return 1
    latest, release_url = fetched
    channel = _detect_install_channel()
    update_available = _version_tuple(latest) > _version_tuple(current)

    print("zscaler-mcp update check")
    print("=" * 40)
    print(f"  installed       : {current}")
    print(f"  latest          : {latest}")
    print(f"  install channel : {channel}")
    print(f"  release notes   : {release_url}")

    if not update_available:
        print("Already up to date.")
        return 0

    print(f"Update available: {current} -> {latest}")
    if not apply:
        print(f"  how to update   : {_upgrade_hint(channel, latest)}")
        return 0

    if channel in ("container", "uvx", "editable"):
        print(
            f"ERROR: --apply is not supported for the '{channel}' install "
            f"channel. {_upgrade_hint(channel, latest)}",
            file=sys.stderr,
        )
        return 2

    return _apply_update(current, latest)


def _apply_update(current: str, latest: str) -> int:
    """Pip-upgrade to ``latest``, verify, and restart the running server."""
    state = read_pid_file()
    server_alive = state is not None and is_process_alive(state.pid)

    # Upgrade the environment the *running server* executes from, not
    # necessarily the one this CLI happens to run in.
    target_python = state.python_executable if server_alive and state else sys.executable

    spec = f"{PYPI_PACKAGE}=={latest}"
    print(f"Upgrading: {target_python} -m pip install --upgrade {spec}")
    proc = subprocess.run(
        [target_python, "-m", "pip", "install", "--upgrade", spec],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
        print("ERROR: pip upgrade failed:", file=sys.stderr)
        for line in tail:
            print(f"  {line}", file=sys.stderr)
        if "No module named pip" in (proc.stderr or ""):
            print(
                "  (the target environment has no pip — it was likely "
                "created by uv. Use `uv pip install --python "
                f"{target_python} {spec}` or reinstall the venv with pip.)",
                file=sys.stderr,
            )
        print(
            f"  Roll back / pin with: {target_python} -m pip install {PYPI_PACKAGE}=={current}",
            file=sys.stderr,
        )
        return 1

    # Verify in a FRESH interpreter — this CLI's already-imported modules
    # can't see the new install, and a clean import also catches a
    # half-broken environment before we restart the server into it.
    verify = subprocess.run(
        [
            target_python,
            "-c",
            f"import importlib.metadata as m; print(m.version('{PYPI_PACKAGE}'))",
        ],
        capture_output=True,
        text=True,
    )
    installed_now = (verify.stdout or "").strip()
    if verify.returncode != 0 or installed_now != latest:
        print(
            f"ERROR: post-install verification failed (expected {latest}, "
            f"got {installed_now or 'import error'}). Roll back with: "
            f"{target_python} -m pip install {PYPI_PACKAGE}=={current}",
            file=sys.stderr,
        )
        return 1
    print(f"Upgraded to {installed_now}.")

    if not server_alive or state is None:
        print(
            "No running server found — restart your service to load the "
            "new version (e.g. `systemctl restart zscaler-mcp`)."
        )
        return 0

    if not hasattr(signal, "SIGUSR2"):
        print(
            f"Running server detected (pid={state.pid}) but in-place "
            f"restart is Unix-only — restart your supervisor to load the "
            f"new version."
        )
        return 0

    try:
        os.kill(state.pid, signal.SIGUSR2)
    except (PermissionError, ProcessLookupError) as exc:
        print(
            f"WARNING: upgraded, but could not restart pid {state.pid} "
            f"({exc}). Restart manually (e.g. `systemctl restart "
            f"zscaler-mcp` or `zscaler-mcp restart`).",
            file=sys.stderr,
        )
        return 1

    print(
        f"Sent SIGUSR2 to zscaler-mcp (pid={state.pid}) — the server is "
        f"re-execing in place and will come back on {latest}."
    )
    return 0
