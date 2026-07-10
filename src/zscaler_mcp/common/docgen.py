"""Documentation generator (v2, registry-driven).

Walks the live tool inventory — the self-declared :class:`ToolSpec` records in
:data:`zscaler_mcp.registry.REGISTRY` — and rewrites the auto-generated regions
of hand-edited Markdown files in place. Narrative sections of those files
(introductions, examples, how-tos) are left untouched; only the regions between
matching marker comments are replaced.

This is the v2 port of v1's ``zscaler_mcp/common/docgen.py``. The behaviour and
public surface are identical; the only difference is the inventory source. v1
instantiated every service class and read its ``read_tools`` / ``write_tools``
dicts; v2 reads the decorator-populated registry, so a tool appears in the docs
for exactly the same reason it appears in the server — there is no second list.

Markers look like::

    <!-- generated:start <region-name> -->
    ...auto-rewritten content...
    <!-- generated:end <region-name> -->

Two top-level entry points:

* :func:`generate_docs` — rewrites the targets in place.
* :func:`check_docs` — does the same render but compares against the files on
  disk, returning a list of stale targets without modifying anything.

Both share the same inventory walk and the same renderer, so a clean
``check_docs`` mathematically guarantees a no-op ``generate_docs`` and vice
versa.

Public surface:
    * :func:`build_inventory`
    * :func:`render_region`
    * :func:`generate_docs`
    * :func:`check_docs`
    * :data:`TARGETS` — list of (path, region, renderer) tuples that ship today.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from zscaler_mcp.common import mcpb

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

# src/zscaler_mcp/common/docgen.py → repo root is four parents up
# (common → zscaler_mcp → src → <repo root>).
REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Inventory model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolEntry:
    """A single registered tool in the inventory."""

    name: str
    description: str
    service: str  # 'zia', 'zpa', 'zcell', ...
    toolset: str  # 'zia_url_filtering', 'zcell_sim_handling', ...
    is_write: bool


@dataclass
class Inventory:
    """Snapshot of every tool the server can expose.

    Built once via :func:`build_inventory`; the renderers walk this structure
    rather than re-introspecting the registry per region.
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


def build_inventory() -> Inventory:
    """Walk the live registry and assemble a flat tool inventory.

    Discovery is idempotent (the decorator rejects duplicates and re-imports
    are no-ops), so calling this repeatedly is safe. No SDK client is needed —
    the registry is populated purely from the ``@tool`` decorators at import
    time.
    """
    from zscaler_mcp.registry import REGISTRY, discover_tools

    discover_tools()

    inv = Inventory()
    for spec in REGISTRY:
        inv.tools.append(
            ToolEntry(
                name=spec.name,
                description=(spec.description or "").strip(),
                service=spec.service,
                toolset=spec.toolset,
                is_write=spec.is_write,
            )
        )
    return inv


# ---------------------------------------------------------------------------
# Service metadata
# ---------------------------------------------------------------------------

# Stable render order. Any service present in the inventory but absent here is
# appended alphabetically after these, so a new service still renders (just not
# in a curated slot) even before this map is updated.
_SERVICE_ORDER = [
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
    "meta",
]


def _ordered_services(present: "set[str] | Dict[str, object]") -> List[str]:
    """Return services in curated order, then any extras alphabetically."""
    present_set = set(present)
    ordered = [s for s in _SERVICE_ORDER if s in present_set]
    extras = sorted(present_set - set(_SERVICE_ORDER))
    return ordered + extras


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
        "zcell": "ZCell — Cellular",
        "meta": "Meta (always loaded)",
    }.get(service, service.upper())


def _service_anchor(service: str) -> str:
    """Anchor slug for the per-service heading.

    Mirrors ``github-slugger`` (GitHub + Docusaurus): lowercase, drop
    punctuation that isn't a space or hyphen, then turn each remaining space
    into a single hyphen — without collapsing runs of spaces first (an em-dash
    surrounded by spaces becomes a double-dash).
    """
    name = _service_display_name(service).lower()
    out: List[str] = []
    for ch in name:
        if ch.isalnum() or ch in (" ", "-"):
            out.append(ch)
    slug = "".join(out).strip()
    return slug.replace(" ", "-").strip("-")


def _kind_label(t: ToolEntry) -> str:
    return "Write" if t.is_write else "Read-only"


# ---------------------------------------------------------------------------
# Renderers — one per region name
# ---------------------------------------------------------------------------


def _render_supported_tools_region(inv: Inventory) -> str:
    """Body for the supported-tools.md auto-region.

    Layout (per service): heading → one-line summary → table
    (Tool | Toolset | Type | Description). Services rendered in a stable order.
    """
    by_svc = inv.by_service()
    order = _ordered_services(by_svc)

    lines: List[str] = []

    lines.append("## Table of Contents")
    lines.append("")
    for svc in order:
        lines.append(f"- [{_service_display_name(svc)}](#{_service_anchor(svc)})")
    lines.append("")

    for svc in order:
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


def _render_service_summary_region(inv: Inventory) -> str:
    """Compact per-service totals table for README.md."""
    counts = inv.service_counts()
    counts.pop("meta", None)

    rows = sorted(counts.items(), key=lambda kv: (-kv[1]["total"], kv[0]))
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
        "zcell": "Zscaler Cellular — SIM inventory, usage analytics & anomaly policies",
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
        "zcell": "**ZCell**",
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


def _render_toolset_catalog_region(inv: Inventory) -> str:
    """Toolset catalog tables for docs/guides/toolsets.md.

    v2 toolsets are self-declared strings on each :class:`ToolSpec` — there is
    no separate metadata catalog carrying human descriptions / default flags
    (that lived in v1's ``common/toolsets.py``). So the catalog is rendered
    purely from the registry: one table per owning service listing each
    toolset id, its tool count, and its member tools. The per-tool
    descriptions live in the supported-tools reference; this region is the
    id → members index.
    """
    by_ts = inv.by_toolset()

    # Map each toolset to its owning service (every member shares a service).
    toolset_service: Dict[str, str] = {}
    for tsid, members in by_ts.items():
        toolset_service[tsid] = members[0].service if members else "meta"

    by_service: Dict[str, List[str]] = {}
    for tsid, svc in toolset_service.items():
        by_service.setdefault(svc, []).append(tsid)

    lines: List[str] = []
    for svc in _ordered_services(by_service):
        ids = by_service.get(svc)
        if not ids:
            continue
        lines.append(f"### {_service_display_name(svc)}")
        lines.append("")
        lines.append("| Toolset | Tools | Members |")
        lines.append("|---|---|---|")
        for tsid in sorted(ids):
            members = by_ts.get(tsid, [])
            member_list = ", ".join(f"`{t.name}`" for t in members) or "_(none)_"
            lines.append(f"| `{tsid}` | {len(members)} | {member_list} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Region registry
# ---------------------------------------------------------------------------

# (target file path relative to repo root, region name | None, renderer)
#
# When ``region`` is a string, the renderer's output replaces the body between
# matching ``<!-- generated:start <region> -->`` / end markers in a hand-edited
# Markdown file. When ``region`` is ``None``, the renderer output IS the entire
# file content (whole-file target). The MCPB manifest is the one whole-file
# target: it's pure generated JSON with no hand-edited prose to preserve
# (``mcpb`` is imported at the top of the module).
TARGETS: List[Tuple[str, Optional[str], Callable[[Inventory], str]]] = [
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
    (
        mcpb.MANIFEST_RELATIVE_PATH,
        None,
        mcpb.render_manifest_json,
    ),
]


# ---------------------------------------------------------------------------
# Marker-based file rewriter
# ---------------------------------------------------------------------------


def _escape_md_cell(text: str) -> str:
    """Escape characters that break Markdown table cells (pipes + newlines)."""
    if not text:
        return ""
    return text.replace("\r\n", " ").replace("\n", " ").replace("|", "\\|").strip()


def _rewrite_region(content: str, region: str, body: str) -> str:
    """Replace the contents between the ``start``/``end`` markers for ``region``.

    Raises ``ValueError`` if the markers are missing, unbalanced, or duplicated.
    The body is sandwiched between the markers with one blank line on each side.
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
            return fn(inv)
    raise KeyError(f"Unknown region: {region}")


def _compute_updated_content(
    path: Path,
    region: Optional[str],
    renderer: Callable[[Inventory], str],
    inv: Inventory,
) -> Tuple[str, str]:
    """Return ``(original, updated)`` for a single target.

    * ``region`` set — Markdown region rewrite; the file must exist and contain
      the matching marker pair.
    * ``region`` is ``None`` — whole-file replacement; a missing file yields an
      empty ``original`` so the first generation triggers a write.
    """
    body = renderer(inv)
    if region is not None:
        original = path.read_text(encoding="utf-8")
        updated = _rewrite_region(original, region, body)
        return original, updated

    original = path.read_text(encoding="utf-8") if path.exists() else ""
    return original, body


def generate_docs(
    repo_root: Optional[Path] = None,
    inv: Optional[Inventory] = None,
) -> List[Path]:
    """Rewrite every target region in place.

    Returns the list of files that were modified. Files already up to date are
    skipped silently (idempotent: a second run with no source changes writes
    nothing).
    """
    root = (repo_root or REPO_ROOT).resolve()
    inv = inv or build_inventory()
    written: List[Path] = []

    for relpath, region, fn in TARGETS:
        path = root / relpath
        original, updated = _compute_updated_content(path, region, fn, inv)
        if updated != original:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(updated, encoding="utf-8")
            written.append(path)
    return written


def check_docs(
    repo_root: Optional[Path] = None,
    inv: Optional[Inventory] = None,
) -> List[Path]:
    """Return the target files that :func:`generate_docs` would modify, without
    touching them.

    Empty list → docs are in sync with the live inventory. Non-empty → stale;
    CI should treat that as a build failure.
    """
    root = (repo_root or REPO_ROOT).resolve()
    inv = inv or build_inventory()
    stale: List[Path] = []

    for relpath, region, fn in TARGETS:
        path = root / relpath
        original, updated = _compute_updated_content(path, region, fn, inv)
        if updated != original:
            stale.append(path)
    return stale
