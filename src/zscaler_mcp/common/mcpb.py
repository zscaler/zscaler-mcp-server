"""MCPB (MCP Bundle) manifest builder — v2, registry-driven.

Anthropic's Claude Desktop Directory installs local MCP servers as
``.mcpb`` files — zip archives containing a ``manifest.json`` plus the
server's source. The full spec lives at
https://github.com/anthropics/mcpb/blob/main/MANIFEST.md.

This module is the **single source of truth** for that manifest. Every
field the catalog needs is either:

* **Static** — owned by :data:`_STATIC_TEMPLATE` below. Author, homepage,
  ``user_config`` schema, compatibility matrix, server invocation.
  Hand-edit these when Anthropic bumps the spec, when we add a new
  ``user_config`` knob, or when we drop a Python version. None of these
  change per release.
* **Dynamic** — derived from the live tool inventory and
  :data:`zscaler_mcp.__version__`. The ``tools`` array and ``version``
  field. These change on every release and must never be hand-edited.

This is the v2 port of v1's ``zscaler_mcp/common/mcpb.py``. Two things
changed with the re-architecture:

1. **Inventory source.** v1 read every service class's ``read_tools`` /
   ``write_tools`` dicts; v2 reads the decorator-populated registry via
   :func:`zscaler_mcp.common.docgen.build_inventory`. The ``by_service``
   duck-type contract is unchanged, so :func:`build_manifest` is agnostic.
2. **``src/`` layout.** The package now lives at ``src/zscaler_mcp`` (the
   hatchling wheel maps it to the importable ``zscaler_mcp``). ``uv run``
   installs the project from ``pyproject.toml`` at the bundle root, so the
   server is importable at runtime; ``PYTHONPATH`` points at
   ``${__dirname}/src`` as a belt-and-suspenders fallback, and
   ``entry_point`` references ``src/zscaler_mcp/server.py``.

The MCPB CLI (``mcpb pack``) requires the manifest at the *root* of the
directory it packs, alongside ``src/``, ``pyproject.toml`` and
``assets/icon.png``. We keep the committed copy under
``integrations/anthropic/`` (so the repo root stays uncluttered) and the
build flow (``scripts/build_mcpb.py``) copies it to the repo root only at
pack time — the root copy is never committed. The ``icon`` and
``entry_point`` paths in the manifest are therefore relative to the repo
root (the pack root), not to ``integrations/anthropic/``.

Architectural decisions encoded here (originally raised by Bryan
Thompson from Anthropic in PR #30):

1. **``server.type = "uv"``** instead of ``"python"`` with
   ``pip --target``. ``pip --target`` embeds platform-locked compiled
   wheels (``cryptography``, ``pydantic-core``, ``orjson`` ship
   ``.so`` / ``.pyd``), producing an OS-and-arch-locked bundle that
   silently fails on the other platforms. ``uv run`` defers wheel
   selection to install time, so the bundle stays source-only and
   cross-platform.

2. **MCPB spec version 0.4** (the current shipping spec).

3. **Env-var names match what ``server.py`` actually reads.** The v2
   server exposes toolsets (``ZSCALER_MCP_TOOLSETS``) rather than the v1
   ``ZSCALER_MCP_TOOLS`` allowlist, so the manifest maps
   ``user_config.toolsets`` → ``ZSCALER_MCP_TOOLSETS``. Any env var that
   ``server.py`` doesn't consume would be silently ignored by Claude
   Desktop's UI toggles (the exact bug PR #30 fixed), so
   ``tests/test_mcpb.py`` greps ``server.py`` to keep the two in lock-step.

Public surface:
    * :func:`build_manifest` — full manifest dict.
    * :func:`render_manifest_json` — same, serialised to pretty-printed
      JSON (the docgen renderer signature ``(Inventory) -> str``).
    * :data:`MANIFEST_RELATIVE_PATH` — canonical path under REPO_ROOT.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from zscaler_mcp import __version__

__all__ = [
    "MANIFEST_RELATIVE_PATH",
    "build_manifest",
    "render_manifest_json",
]


# ---------------------------------------------------------------------------
# Output location
# ---------------------------------------------------------------------------

# Canonical committed location of the generated manifest, relative to the
# repo root. The MCPB CLI (`npx @anthropic-ai/mcpb@latest pack`) expects
# the manifest at the *pack root* (repo root) — the build/CI flow copies
# this file there at pack time (see scripts/build_mcpb.py). Keeping the
# committed copy under integrations/anthropic/ keeps the repo root clean
# and groups it with the other platform-integration assets.
MANIFEST_RELATIVE_PATH = "integrations/anthropic/manifest.json"


# ---------------------------------------------------------------------------
# Static metadata template
# ---------------------------------------------------------------------------

# Everything that doesn't change per release lives here. Keys are merged
# verbatim into the final manifest; the ``version`` and ``tools`` fields
# are injected by :func:`build_manifest`.
_STATIC_TEMPLATE: Dict[str, Any] = {
    "manifest_version": "0.4",
    "name": "Zscaler MCP Server",
    "description": (
        "Zscaler MCP Server — AI-powered management of the Zscaler Zero Trust "
        "Exchange across ZIA, ZPA, ZDX, ZCC, ZTW, ZIdentity, EASM, Z-Insights, "
        "ZMS, and ZCell via the Model Context Protocol."
    ),
    "long_description": (
        "Zscaler MCP Server is a Model Context Protocol (MCP) server for "
        "managing Zscaler products with LLMs (Claude, ChatGPT, Gemini, "
        "etc.). It exposes hundreds of tools across the Zscaler services. "
        "Read-only operations are available by default; create / update / "
        "delete tools require explicit allowlisting via the 'Enable Write "
        "Tools' and 'Write Tools Allowlist' settings below, and destructive "
        "operations additionally require an in-session HMAC confirmation "
        "token."
    ),
    "author": {
        "name": "Zscaler, Inc.",
        "email": "devrel@zscaler.com",
        "url": "https://github.com/zscaler",
    },
    "homepage": "https://www.zscaler.com",
    "documentation": "https://zscaler.github.io/zscaler-mcp-server/",
    "support": "https://help.zscaler.com/contact-support",
    # The icon lives under ``assets/`` (not at the bundle root) to keep
    # the top-level layout clean. ``.mcpbignore`` ignores ``assets/``
    # wholesale but un-ignores this one file via ``!assets/icon.png``
    # so it still gets packed.
    "icon": "assets/icon.png",
    "privacy_policies": [
        "https://www.zscaler.com/privacy-policy",
    ],
    "server": {
        "type": "uv",
        # Package lives under src/ in v2 (hatchling maps src/zscaler_mcp →
        # importable zscaler_mcp). Claude Desktop displays this in the
        # directory listing; it doesn't actually invoke it (the mcp_config
        # block below is what runs).
        "entry_point": "src/zscaler_mcp/server.py",
        "mcp_config": {
            "command": "uv",
            # `uv run` reads pyproject.toml at the bundle root, resolves the
            # right wheels for the user's platform, installs the project into
            # a uv-managed venv, then executes the inner `python -m`.
            "args": [
                "run",
                "python",
                "-m",
                "zscaler_mcp.server",
            ],
            "env": {
                # v2 src/ layout: the package is under src/, so add it to the
                # path as a fallback (uv also installs the project from
                # pyproject.toml, which is the primary import path).
                "PYTHONPATH": "${__dirname}/src",
                # Zscaler API auth — OneAPI credentials (read by the SDK).
                "ZSCALER_CLIENT_ID": "${user_config.client_id}",
                "ZSCALER_CLIENT_SECRET": "${user_config.client_secret}",
                "ZSCALER_CUSTOMER_ID": "${user_config.customer_id}",
                # ZCell (Zscaler Cellular) requires a separate customer ID —
                # distinct from ZSCALER_CUSTOMER_ID (used by ZPA).
                "ZCELL_CUSTOMER_ID": "${user_config.zcell_customer_id}",
                "ZSCALER_VANITY_DOMAIN": "${user_config.vanity_domain}",
                "ZSCALER_CLOUD": "${user_config.cloud}",
                # Server behaviour toggles. Names below MUST match the ones
                # `zscaler_mcp/server.py` actually reads — tests/test_mcpb.py
                # greps server.py to catch drift (the historical silent-ignore
                # bug from PR #30).
                "ZSCALER_MCP_SERVICES": "${user_config.enabled_services}",
                "ZSCALER_MCP_TOOLSETS": "${user_config.toolsets}",
                "ZSCALER_MCP_DEBUG": "${user_config.debug_mode}",
                "ZSCALER_MCP_WRITE_ENABLED": "${user_config.enable_write_tools}",
                "ZSCALER_MCP_WRITE_TOOLS": "${user_config.write_tools}",
                "ZSCALER_MCP_USER_AGENT_COMMENT": "${user_config.user_agent_comment}",
            },
        },
    },
    # NOTE: `tools` is injected by build_manifest() from the live
    # inventory; it must NOT appear in this static template.
    "compatibility": {
        "platforms": ["darwin", "win32", "linux"],
        "runtimes": {
            # Track the floor declared in pyproject.toml::requires-python.
            "python": ">=3.10",
        },
    },
    "user_config": {
        "enabled_services": {
            "type": "string",
            "title": "Enabled Services",
            "description": (
                "Comma-separated list of Zscaler services to enable. "
                "Available: zia, zpa, zdx, zcc, ztw, zid, zeasm, zins, zms, "
                "zcell. Default: every service the OneAPI credentials are "
                "entitled to."
            ),
            "required": False,
            "sensitive": False,
            "default": "zia,zpa,zdx,zcc,ztw,zid,zeasm,zins,zms,zcell",
        },
        "toolsets": {
            "type": "string",
            "title": "Enabled Toolsets",
            "description": (
                "Comma-separated list of toolset ids to enable (e.g. "
                "'zia_url_filtering,zpa_app_segments'). Special values: "
                "'default' for the curated default-on subset, 'all' for every "
                "toolset. Leave empty to load every toolset for the enabled "
                "services."
            ),
            "required": False,
            "sensitive": False,
            "default": "",
        },
        "debug_mode": {
            "type": "boolean",
            "title": "Enable Debug Mode",
            "description": (
                "Enable debug logging for troubleshooting. Logs all MCP "
                "operations and outbound API interactions to the Claude "
                "Desktop developer console."
            ),
            "required": False,
            "sensitive": False,
            "default": False,
        },
        "enable_write_tools": {
            "type": "boolean",
            "title": "Enable Write Tools",
            "description": (
                "Enable tools that CREATE, UPDATE, or DELETE Zscaler "
                "resources. Read-only tools (list / get) remain available "
                "regardless of this setting. Off by default."
            ),
            "required": False,
            "sensitive": False,
            "default": False,
        },
        "write_tools": {
            "type": "string",
            "title": "Write Tools Allowlist (MANDATORY when writes are enabled)",
            "description": (
                "Comma-separated allowlist of write tools. Supports fnmatch "
                "wildcards (e.g. 'zpa_create_*,zia_update_*'). Required "
                "when 'Enable Write Tools' is on — an empty allowlist "
                "registers zero write tools even with the toggle enabled."
            ),
            "required": False,
            "sensitive": False,
            "default": "",
        },
        "user_agent_comment": {
            "type": "string",
            "title": "Custom User Agent",
            "description": (
                "Optional comment appended to the SDK's outgoing "
                "User-Agent header. Useful for tagging requests when a "
                "single tenant has multiple deployments."
            ),
            "required": False,
            "sensitive": False,
        },
        "client_id": {
            "type": "string",
            "title": "ZSCALER_CLIENT_ID",
            "description": "OneAPI client ID from the ZIdentity console.",
            "required": False,
            "sensitive": True,
        },
        "client_secret": {
            "type": "string",
            "title": "ZSCALER_CLIENT_SECRET",
            "description": "OneAPI client secret from the ZIdentity console.",
            "required": False,
            "sensitive": True,
        },
        "customer_id": {
            "type": "string",
            "title": "ZSCALER_CUSTOMER_ID",
            "description": (
                "Zscaler customer/tenant ID. Required for ZPA tools; optional for other services."
            ),
            "required": False,
            "sensitive": False,
        },
        "zcell_customer_id": {
            "type": "string",
            "title": "ZCELL_CUSTOMER_ID",
            "description": (
                "Zscaler Cellular customer ID. Required for ZCell tools. "
                "Separate from ZSCALER_CUSTOMER_ID (used by ZPA)."
            ),
            "required": False,
            "sensitive": False,
        },
        "vanity_domain": {
            "type": "string",
            "title": "ZSCALER_VANITY_DOMAIN",
            "description": "ZIdentity vanity domain (e.g. 'acme').",
            "required": False,
            "sensitive": False,
        },
        "cloud": {
            "type": "string",
            "title": "ZSCALER_CLOUD",
            "description": (
                "Optional Zscaler cloud override (e.g. 'BETA', "
                "'zscalertwo'). Leave as 'production' for the standard cloud."
            ),
            "required": False,
            "sensitive": False,
            "default": "production",
        },
    },
    "license": "MIT",
    "repository": {
        "type": "git",
        "url": "https://github.com/zscaler/zscaler-mcp-server",
    },
}


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------


def _first_sentence(text: str) -> str:
    """Trim a long description down to its first sentence.

    Tool descriptions can run to a paragraph (auto-resolver footnotes, SDK
    quirks, etc.). The MCPB directory only shows a one-liner per tool, so we
    collapse each description to its first sentence — falling back to the full
    text if no sentence break is found within a reasonable window.
    """
    text = (text or "").strip()
    if not text:
        return ""

    period_idx = text.find(". ")
    if period_idx == -1:
        cleaned = text.rstrip()
        if not cleaned.endswith("."):
            cleaned += "."
    else:
        cleaned = text[: period_idx + 1]

    if len(cleaned) > 280:
        cleaned = cleaned[:277].rstrip() + "..."

    return cleaned


def _tool_entries_from_inventory(inventory: Any) -> List[Dict[str, str]]:
    """Convert an :class:`Inventory` into the MCPB ``tools`` array.

    Two ordering invariants for diff stability:

    1. **Service-grouped** — tools are ordered by service code first (meta,
       zia, zpa, …) to match the catalog UI's grouping.
    2. **Alphabetical within a service.**

    ``inventory`` is duck-typed (``.by_service() -> {svc: [entry, ...]}`` with
    ``entry.name`` / ``entry.description``) to avoid importing docgen here.
    """
    service_order = [
        "meta",
        "zia",
        "zpa",
        "zdx",
        "zcc",
        "ztw",
        "zid",
        "zeasm",
        "zins",
        "zms",
        "zcell",
    ]

    grouped = inventory.by_service()
    entries: List[Dict[str, str]] = []

    for svc in service_order:
        for tool in sorted(grouped.get(svc, []), key=lambda t: t.name):
            entries.append(
                {
                    "name": tool.name,
                    "description": _first_sentence(tool.description),
                }
            )

    # Defensive: surface any service code we didn't anticipate (a future
    # product) so its tools still ship, after the canonical block.
    seen = set(service_order)
    for svc in sorted(grouped.keys()):
        if svc in seen:
            continue
        for tool in sorted(grouped[svc], key=lambda t: t.name):
            entries.append(
                {
                    "name": tool.name,
                    "description": _first_sentence(tool.description),
                }
            )

    return entries


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def build_manifest(inventory: Any) -> Dict[str, Any]:
    """Assemble the full MCPB manifest dict.

    ``inventory`` is the :class:`zscaler_mcp.common.docgen.Inventory` produced
    by :func:`zscaler_mcp.common.docgen.build_inventory`. The type isn't
    annotated explicitly to avoid an import cycle (docgen imports this module
    for its TARGETS registration).

    The returned dict is constructed in a stable key order so the generated
    JSON has a predictable layout (tests rely on this for idempotence).
    """
    manifest: Dict[str, Any] = {}

    manifest["manifest_version"] = _STATIC_TEMPLATE["manifest_version"]
    manifest["name"] = _STATIC_TEMPLATE["name"]
    manifest["version"] = __version__
    manifest["description"] = _STATIC_TEMPLATE["description"]
    manifest["long_description"] = _STATIC_TEMPLATE["long_description"]
    manifest["author"] = _STATIC_TEMPLATE["author"]
    manifest["homepage"] = _STATIC_TEMPLATE["homepage"]
    manifest["documentation"] = _STATIC_TEMPLATE["documentation"]
    manifest["support"] = _STATIC_TEMPLATE["support"]
    manifest["icon"] = _STATIC_TEMPLATE["icon"]
    manifest["privacy_policies"] = list(_STATIC_TEMPLATE["privacy_policies"])

    manifest["server"] = _STATIC_TEMPLATE["server"]

    manifest["tools"] = _tool_entries_from_inventory(inventory)

    manifest["compatibility"] = _STATIC_TEMPLATE["compatibility"]
    manifest["user_config"] = _STATIC_TEMPLATE["user_config"]

    manifest["license"] = _STATIC_TEMPLATE["license"]
    manifest["repository"] = _STATIC_TEMPLATE["repository"]

    return manifest


def render_manifest_json(inventory: Any) -> str:
    """Docgen renderer: ``(Inventory) -> str``.

    Returns pretty-printed JSON with a trailing newline so the file is
    diff-friendly and POSIX-compliant. Matches the whole-file renderer
    contract used by :data:`zscaler_mcp.common.docgen.TARGETS`.
    """
    payload = build_manifest(inventory)
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
