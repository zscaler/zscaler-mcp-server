"""Cloud-platform credential loaders (AWS Secrets Manager, GCP Secret Manager).

Optional and opt-in: nothing here runs unless the matching environment variable
is set, and each provider's SDK is imported only once its loader is enabled — so
the dependency footprint stays light for the common stdio / local case.

``load_secrets()`` is the single entry point ``server.main()`` calls. It runs
every provider, because a deployment selects one by configuration rather than by
choosing a build: the same image serves Docker Hub, Cloud Run and Bedrock
AgentCore.
"""

import contextlib
import logging
import sys

from zscaler_mcp.cloud import aws_secrets, gcp_secrets

__all__ = ["aws_secrets", "gcp_secrets", "is_enabled", "load_secrets"]

#: Every loader, in the order they run. Providers are mutually exclusive in
#: practice; if more than one is somehow enabled, the last one wins for any key
#: they both supply.
_PROVIDERS = (aws_secrets, gcp_secrets)


def is_enabled() -> bool:
    """True when any cloud credential loader is configured."""
    return any(provider.is_enabled() for provider in _PROVIDERS)


@contextlib.contextmanager
def _bootstrap_logging():
    """Make the loaders' log output visible, then get out of the way.

    ``main()`` has to call :func:`load_secrets` *before* ``parse_args()``, because
    a secret can carry the very variables the CLI reads for its defaults
    (``ZSCALER_MCP_WRITE_ENABLED``, ``ZSCALER_MCP_AUTH_API_KEY``, …). That puts it
    ahead of ``configure_logging()``, so without this every line a loader emits
    goes to a root logger with no handler and is discarded — which was observed
    on a real AgentCore container: credentials loaded correctly and the startup
    log said nothing about where they came from, while the deployment guide told
    operators to grep for exactly those lines.

    Handled here rather than by configuring logging earlier in ``main()``, since
    at that point the transport is still unknown and a stdout handler would
    corrupt the JSON-RPC stream under stdio. ``stderr`` is safe on every
    transport. Anything already configured is left alone.
    """
    root = logging.getLogger()
    if root.handlers:
        yield
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    previous_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        yield
    finally:
        # Removed so the real configure_logging() still sees a bare root and
        # installs the transport-appropriate handler via basicConfig().
        root.removeHandler(handler)
        root.setLevel(previous_level)
        handler.close()


def load_secrets() -> None:
    """Hydrate ``os.environ`` from whichever cloud secret store is configured.

    A no-op when none is. Each loader raises ``SystemExit`` on a fatal error, so
    a misconfigured secret stops the server here rather than surfacing as an
    opaque Zscaler API error on the first tool call.
    """
    if not is_enabled():
        return

    with _bootstrap_logging():
        for provider in _PROVIDERS:
            provider.load_secrets()
