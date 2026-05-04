"""Documentation generator.

Walks the live tool inventory and rewrites the auto-generated regions of
hand-edited Markdown files in place. Narrative sections of those files
(introductions, examples, how-tos) are left untouched; only the regions
between matching marker comments are replaced.

Markers look like::

    <!-- generated:start <region-name> -->
    ...auto-rewritten content...
    <!-- generated:end <region-name> -->

Two top-level entry points:

* :func:`generate_docs` — rewrites the targets in place.
* :func:`check_docs` — does the same render but compares against the
  files on disk, returning a list of stale targets without modifying
  anything.

Both share the same inventory walk and the same renderer, so a clean
``check_docs`` mathematically guarantees a no-op
``generate_docs`` and vice versa.

Public surface:
    * :func:`build_inventory`
    * :func:`render_region`
    * :func:`generate_docs`
    * :func:`check_docs`
    * :data:`TARGETS` — list of (path, region) tuples that ship today.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from zscaler_mcp.common.toolsets import (
    META_TOOLSET_ID,
    TOOLSETS,
    ToolsetCatalog,
    toolset_for_tool,
)

__all__ = [
    "ToolEntry",
    "Inventory",
    "build_inventory",
    "render_region",
    "generate_docs",
    "check_docs",
    "TARGETS",
    "MARKER_START",
    "MARKER_END",
    "REPO_ROOT",
]


# ---------------------------------------------------------------------------
# Marker conventions
# ---------------------------------------------------------------------------

MARKER_START = "<!-- generated:start {region} -->"
MARKER_END = "<!-- generated:end {region} -->"


# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------

# zscaler_mcp/common/docgen.py → repo root is two parents up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Inventory model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolEntry:
    """A single registered tool in the inventory."""

    name: str
    description: str
    service: str  # 'zia', 'zpa', ...
    toolset: str  # 'zia_url_filtering', 'meta', ...
    is_write: bool


@dataclass
class Inventory:
    """Snapshot of every tool the server can expose.

    Built once via :func:`build_inventory`; the renderers walk this
    structure rather than re-introspecting the services per region.
    """

    tools: List[ToolEntry] = field(default_factory=list)

    # ---- queries -----------------------------------------------------------

    def by_service(self) -> Dict[str, List[ToolEntry]]:
        """All tools grouped by service code (sorted by tool name)."""
        out: Dict[str, List[ToolEntry]] = {}
        for t in self.tools:
            out.setdefault(t.service, []).append(t)
        for v in out.values():
            v.sort(key=lambda x: x.name)
        return out

    def by_toolset(self) -> Dict[str, List[ToolEntry]]:
        out: Dict[str, List[ToolEntry]] = {}
        for t in self.tools:
            out.setdefault(t.toolset, []).append(t)
        for v in out.values():
            v.sort(key=lambda x: x.name)
        return out

    def service_counts(self) -> Dict[str, Dict[str, int]]:
        """Per-service counts: {'zia': {'read': 80, 'write': 26, 'total': 106}}."""
        out: Dict[str, Dict[str, int]] = {}
        for svc, tools in self.by_service().items():
            reads = sum(1 for t in tools if not t.is_write)
            writes = sum(1 for t in tools if t.is_write)
            out[svc] = {"read": reads, "write": writes, "total": reads + writes}
        return out


# ---------------------------------------------------------------------------
# Inventory build
# ---------------------------------------------------------------------------


# The 'meta' toolset's tools are added directly in server.py rather than
# through a service class. We pin them here so the generator sees them
# even though no service owns them. Keep in sync with the registrations
# in ``ZscalerMCPServer._register_tools``.
_META_TOOLS: List[Tuple[str, str]] = [
    (
        "zscaler_check_connectivity",
        "Check connectivity to the Zscaler API.",
    ),
    (
        "zscaler_get_available_services",
        (
            "Service-level overview of what is loaded in this session: "
            "which Zscaler services are callable, which are present but "
            "have zero callable tools because the OneAPI credentials are "
            "not entitled to them, and which were excluded by configuration."
        ),
    ),
    (
        "zscaler_list_toolsets",
        (
            "Primary tool-discovery entry point. Lists every toolset "
            "with description, default flag, currently-enabled status, "
            "and per-row availability metadata. Supports name / "
            "description / service substring filters."
        ),
    ),
    (
        "zscaler_get_toolset_tools",
        (
            "Drills into a toolset to enumerate its tools and per-tool "
            "availability. Use after zscaler_list_toolsets has identified "
            "the relevant toolset."
        ),
    ),
    (
        "zscaler_enable_toolset",
        (
            "Activates a registered-but-not-loaded toolset for the rest "
            "of the session. Refuses with status 'not_entitled' if the "
            "OneAPI credentials cannot access the underlying product."
        ),
    ),
]


def build_inventory() -> Inventory:
    """Walk every service and assemble a flat tool inventory.

    Service classes are instantiated with ``zscaler_client=None`` —
    that's enough for inventory enumeration; the SDK client is only
    needed at call time. Mirrors the pattern already used by
    ``parse_args`` in ``server.py`` for argument validation.
    """
    from zscaler_mcp import services as services_mod

    inv = Inventory()

    for tool_name, description in _META_TOOLS:
        inv.tools.append(
            ToolEntry(
                name=tool_name,
                description=description,
                service="meta",
                toolset=META_TOOLSET_ID,
                is_write=False,
            )
        )

    for service_code, service_class in services_mod.get_available_services().items():
        instance = service_class(None)
        for entry in getattr(instance, "read_tools", []):
            inv.tools.append(
                ToolEntry(
                    name=entry["name"],
                    description=entry.get("description", "").strip(),
                    service=service_code,
                    toolset=_safe_toolset_for(entry["name"]),
                    is_write=False,
                )
            )
        for entry in getattr(instance, "write_tools", []):
            inv.tools.append(
                ToolEntry(
                    name=entry["name"],
                    description=entry.get("description", "").strip(),
                    service=service_code,
                    toolset=_safe_toolset_for(entry["name"]),
                    is_write=True,
                )
            )

    return inv


def _safe_toolset_for(tool_name: str) -> str:
    """Resolve a tool's toolset, falling back to the meta sentinel.

    An unmapped tool would normally raise — but for the doc generator
    we'd rather emit *something* than fail the whole render. Tests
    against ``test_every_registered_tool_resolves`` will catch real
    drift before it ever reaches here.
    """
    try:
        return toolset_for_tool(tool_name)
    except KeyError:
        return META_TOOLSET_ID


# ---------------------------------------------------------------------------
# Renderers — one per region name
# ---------------------------------------------------------------------------


def _service_display_name(service: str) -> str:
    return {
        "zia": "ZIA — Internet Access",
        "zpa": "ZPA — Private Access",
        "zdx": "ZDX — Digital Experience",
        "zcc": "ZCC — Client Connector",
        "ztw": "ZTW — Workload Segmentation",
        "zid": "ZIdentity",
        "zeasm": "EASM — External Attack Surface Management",
        "zins": "Z-Insights",
        "zms": "ZMS — Microsegmentation",
        "meta": "Meta (always loaded)",
    }.get(service, service.upper())


def _service_anchor(service: str) -> str:
    """GitHub-style anchor slug for the per-service heading.

    GitHub auto-generates anchors by lowercasing, dropping punctuation
    that isn't a hyphen, and collapsing whitespace runs to a single
    hyphen. This mirrors that algorithm closely enough for our
    auto-generated TOCs to land on the right anchor.
    """
    name = _service_display_name(service).lower()
    out: List[str] = []
    for ch in name:
        if ch.isalnum() or ch in (" ", "-"):
            out.append(ch)
    slug = "".join(out).strip()
    while "  " in slug:
        slug = slug.replace("  ", " ")
    return slug.replace(" ", "-").strip("-")


def _kind_label(t: ToolEntry) -> str:
    return "Write" if t.is_write else "Read-only"


def _render_supported_tools_region(inv: Inventory, _catalog: ToolsetCatalog) -> str:
    """Body for the supported-tools.md auto-region.

    Layout (per service): heading → one-line summary → table
    (Tool | Toolset | Type | Description). Services rendered in a
    stable order; the meta toolset is rendered last.
    """
    service_order = [
        "zia",
        "zpa",
        "zdx",
        "zcc",
        "ztw",
        "zid",
        "zeasm",
        "zins",
        "zms",
        "meta",
    ]
    by_svc = inv.by_service()

    lines: List[str] = []

    lines.append("## Table of Contents")
    lines.append("")
    for svc in service_order:
        if svc not in by_svc:
            continue
        lines.append(f"- [{_service_display_name(svc)}](#{_service_anchor(svc)})")
    lines.append("")

    for svc in service_order:
        tools = by_svc.get(svc)
        if not tools:
            continue
        reads = [t for t in tools if not t.is_write]
        writes = [t for t in tools if t.is_write]
        lines.append("---")
        lines.append("")
        lines.append(f"## {_service_display_name(svc)}")
        lines.append("")
        if writes:
            lines.append(f"{len(reads)} read-only tools, {len(writes)} write tools.")
        else:
            lines.append(f"All {len(tools)} tools are read-only.")
        lines.append("")
        lines.append("| Tool | Toolset | Type | Description |")
        lines.append("|------|---------|------|-------------|")
        for t in sorted(tools, key=lambda x: (x.is_write, x.name)):
            desc = _escape_md_cell(t.description)
            lines.append(f"| `{t.name}` | `{t.toolset}` | {_kind_label(t)} | {desc} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_service_summary_region(inv: Inventory, _catalog: ToolsetCatalog) -> str:
    """Compact per-service totals table for README.md."""
    counts = inv.service_counts()
    counts.pop("meta", None)

    rows = sorted(counts.items(), key=lambda kv: -kv[1]["total"])
    total_tools = sum(c["total"] for c in counts.values())

    lines = [
        f"The Zscaler Integrations MCP Server provides **{total_tools} tools** for all major Zscaler services:",
        "",
        "| Service | Description | Tools |",
        "|---------|-------------|-------|",
    ]

    descriptions = {
        "zia": "Zscaler Internet Access — Security policies",
        "zpa": "Zscaler Private Access — Application access",
        "zdx": "Zscaler Digital Experience — Monitoring & analytics",
        "zms": "Zscaler Microsegmentation — Agents, resources, policies",
        "ztw": "Zscaler Workload Segmentation",
        "zins": "Z-Insights analytics — Web traffic, cyber incidents, shadow IT",
        "zid": "ZIdentity — Identity & access management",
        "zeasm": "External Attack Surface Management",
        "zcc": "Zscaler Client Connector — Device management",
    }
    bold_name = {
        "zia": "**ZIA**",
        "zpa": "**ZPA**",
        "zdx": "**ZDX**",
        "zms": "**ZMS**",
        "ztw": "**ZTW**",
        "zins": "**Z-Insights**",
        "zid": "**ZIdentity**",
        "zeasm": "**EASM**",
        "zcc": "**ZCC**",
    }

    for svc, c in rows:
        if c["write"]:
            kind = f"{c['total']} read/write"
        else:
            kind = f"{c['total']} read-only"
        lines.append(
            f"| {bold_name.get(svc, svc.upper())} | {descriptions.get(svc, '')} | {kind} |"
        )

    return "\n".join(lines) + "\n"


def _render_toolset_catalog_region(inv: Inventory, catalog: ToolsetCatalog) -> str:
    """Toolset catalog tables for docs/guides/toolsets.md.

    One small table per service section. Replaces the hand-maintained
    catalog block. Drives off ``catalog`` for metadata (description,
    default-flag) and ``inv`` for tool counts per toolset.
    """
    by_ts = inv.by_toolset()

    def tool_count(tsid: str) -> int:
        return len(by_ts.get(tsid, []))

    # Group toolsets by owning service.
    by_service: Dict[str, List[str]] = {}
    for tsid in catalog.all_ids():
        meta = catalog.get(tsid)
        if meta is None:  # pragma: no cover - defensive
            continue
        by_service.setdefault(meta.service, []).append(tsid)

    lines: List[str] = []

    if META_TOOLSET_ID in by_service:
        lines.append("### Always-on")
        lines.append("")
        lines.append("| Id | Tools | Purpose |")
        lines.append("|---|---|---|")
        for tsid in sorted(by_service[META_TOOLSET_ID]):
            meta = catalog.get(tsid)
            members = ", ".join(f"`{t.name}`" for t in by_ts.get(tsid, []))
            lines.append(
                f"| `{tsid}` | {members or '_(none)_'} | {_escape_md_cell(meta.description)} |"
            )
        lines.append("")

    service_order = [
        "zia",
        "zpa",
        "zdx",
        "zcc",
        "ztw",
        "zid",
        "zeasm",
        "zins",
        "zms",
    ]

    for svc in service_order:
        ids = by_service.get(svc)
        if not ids:
            continue
        lines.append(f"### {_service_display_name(svc)}")
        lines.append("")
        lines.append("| Id | Default | Tools | Coverage |")
        lines.append("|---|---|---|---|")
        for tsid in sorted(ids):
            meta = catalog.get(tsid)
            default_flag = "yes" if meta.default else "no"
            count = tool_count(tsid)
            lines.append(
                f"| `{tsid}` | {default_flag} | {count} | {_escape_md_cell(meta.description)} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Region registry
# ---------------------------------------------------------------------------


# (target file path relative to repo root, region name, renderer)
TARGETS: List[Tuple[str, str, Callable[[Inventory, ToolsetCatalog], str]]] = [
    (
        "docs/guides/supported-tools.md",
        "tools",
        _render_supported_tools_region,
    ),
    (
        "README.md",
        "service-summary",
        _render_service_summary_region,
    ),
    (
        "docs/guides/toolsets.md",
        "toolset-catalog",
        _render_toolset_catalog_region,
    ),
]


# ---------------------------------------------------------------------------
# Marker-based file rewriter
# ---------------------------------------------------------------------------


def _escape_md_cell(text: str) -> str:
    """Escape characters that break Markdown table cells.

    Pipes and newlines must go; everything else is fair game.
    """
    if not text:
        return ""
    return text.replace("\r\n", " ").replace("\n", " ").replace("|", "\\|").strip()


def _rewrite_region(content: str, region: str, body: str) -> str:
    """Replace the contents of ``<!-- generated:start <region> -->``...
    ``<!-- generated:end <region> -->`` in ``content``.

    Raises ``ValueError`` if the matching markers are missing or
    unbalanced. The body is sandwiched between the markers with one
    blank line on each side for readability.
    """
    start = MARKER_START.format(region=region)
    end = MARKER_END.format(region=region)

    s_idx = content.find(start)
    e_idx = content.find(end)
    if s_idx < 0:
        raise ValueError(f"Missing start marker for region '{region}': expected '{start}'")
    if e_idx < 0:
        raise ValueError(f"Missing end marker for region '{region}': expected '{end}'")
    if e_idx < s_idx:
        raise ValueError(f"End marker for region '{region}' precedes start marker")
    if content.count(start) > 1 or content.count(end) > 1:
        raise ValueError(f"Region '{region}' appears more than once in the file")

    before = content[: s_idx + len(start)]
    after = content[e_idx:]
    body = body.rstrip() + "\n"
    return f"{before}\n\n{body}\n{after}"


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def render_region(region: str, inv: Optional[Inventory] = None) -> str:
    """Render a single region body by name (used by tests)."""
    inv = inv or build_inventory()
    for _, name, fn in TARGETS:
        if name == region:
            return fn(inv, TOOLSETS)
    raise KeyError(f"Unknown region: {region}")


def generate_docs(
    repo_root: Optional[Path] = None,
    inv: Optional[Inventory] = None,
) -> List[Path]:
    """Rewrite every target region in place.

    Returns the list of files that were modified. Files whose content
    was already up to date are skipped silently (idempotent behaviour:
    running the generator twice with no source changes results in no
    file writes the second time).
    """
    root = (repo_root or REPO_ROOT).resolve()
    inv = inv or build_inventory()
    written: List[Path] = []

    for relpath, region, fn in TARGETS:
        path = root / relpath
        original = path.read_text(encoding="utf-8")
        body = fn(inv, TOOLSETS)
        updated = _rewrite_region(original, region, body)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            written.append(path)
    return written


def check_docs(
    repo_root: Optional[Path] = None,
    inv: Optional[Inventory] = None,
) -> List[Path]:
    """Return the list of target files that would be modified by
    :func:`generate_docs` without actually touching them.

    Empty list → docs are in sync with the live inventory. Non-empty
    list → docs are stale and the generator needs to be re-run. CI
    integrations should treat a non-empty list as a build failure.
    """
    root = (repo_root or REPO_ROOT).resolve()
    inv = inv or build_inventory()
    stale: List[Path] = []

    for relpath, region, fn in TARGETS:
        path = root / relpath
        original = path.read_text(encoding="utf-8")
        body = fn(inv, TOOLSETS)
        updated = _rewrite_region(original, region, body)
        if updated != original:
            stale.append(path)
    return stale
