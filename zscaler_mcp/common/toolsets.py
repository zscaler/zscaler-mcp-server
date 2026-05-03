"""Toolset registry — logical groupings of related tools.

A *toolset* is a small piece of metadata that every tool is tagged with. It
plays the same role as GitHub's MCP server toolsets: it lets users (and
clients) load only the slice of tools they actually need, instead of all
~280+ tools the server can expose.

Why toolsets exist
------------------
1. **Context reduction.** Loading all Zscaler MCP tools into an agent's
   context window is wasteful and confuses tool selection. Toolsets let a
   client request "only ZIA URL filtering + ZPA app segments" and get ~25
   tools instead of ~280.
2. **Per-toolset agent guidance.** Each toolset can contribute a paragraph
   of system instructions that is composed into the MCP ``instructions``
   field at startup — delivered to the agent only when the matching tools
   are loaded. This replaces the unreliable "agent will read CLAUDE.md"
   pattern.
3. **Foundation for header- / URL-driven configuration.** Once tools are
   tagged, an HTTP client can switch toolset profiles per request via
   ``X-MCP-Toolsets`` or ``/mcp/x/{toolsets}`` URL paths.
4. **Foundation for dynamic discovery.** The ``zscaler_list_toolsets`` /
   ``zscaler_get_toolset_tools`` / ``zscaler_enable_toolset`` meta-tools
   let the agent enable additional toolsets at runtime.

This module exposes:

* :class:`ToolsetMetadata`  — the metadata object every tool is tagged with.
* :class:`ToolsetCatalog`   — the registry of all known toolsets.
* :data:`TOOLSETS`          — the canonical instance of the catalog used
  across the codebase.

Naming convention
-----------------
Toolset IDs follow ``{service}_{group}`` (snake_case), or just the bare
service name when a service has only one toolset, e.g.::

    zia_url_filtering        zia_cloud_firewall      zia_ssl_inspection
    zpa_app_segments         zpa_policy              zpa_connectors
    zdx_devices              zdx_alerts              zdx_deep_traces
    zcc                      ztw                     zid

Special keywords accepted by callers (resolved during selection, never
stored as IDs):

* ``"default"`` — expand to every toolset whose ``default`` flag is True.
* ``"all"``     — expand to every registered toolset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

__all__ = [
    "ToolsetMetadata",
    "ToolsetCatalog",
    "TOOLSETS",
    "META_TOOLSET_ID",
    "resolve_toolset_selection",
    "toolset_for_tool",
]


# ---------------------------------------------------------------------------
# Special, always-on toolset for the server's own meta-tools
# (zscaler_check_connectivity, zscaler_get_available_services,
# zscaler_list_toolsets, zscaler_get_toolset_tools,
# zscaler_enable_toolset). These are never filtered by toolset
# selection — the agent always needs them.
# ---------------------------------------------------------------------------
META_TOOLSET_ID = "meta"


@dataclass(frozen=True)
class ToolsetMetadata:
    """Metadata that every tool is tagged with.

    Attributes:
        id: Unique snake_case identifier (``zia_url_filtering``,
            ``zpa_app_segments``, ``meta``). Used in CLI flags, env vars,
            HTTP headers, URL paths, and dynamic discovery.
        service: Owning service code (``zia``, ``zpa``, ``zdx``, ``zcc``,
            ``ztw``, ``zid``, ``zeasm``, ``zins``, ``zms``, or
            ``"meta"`` for cross-service tools). Used by token-entitlement
            filtering (a token without ZIA entitlement skips every tool
            whose toolset's ``service`` is ``"zia"``).
        description: Short human-readable summary, surfaced via
            ``zscaler_list_toolsets`` and the documentation generator.
        default: When True, included in the ``"default"`` keyword
            expansion (i.e. loaded when the user passes no ``--toolsets``).
        instructions: Optional callable that returns a string snippet to
            append to the server's ``instructions`` field at startup. The
            callable receives the :class:`ToolsetCatalog` so it can check
            whether sibling toolsets are also enabled and adjust guidance
            accordingly (mirrors GitHub's
            ``InstructionsFunc(*Inventory) string`` pattern). Snippets
            should be short (1–4 sentences) and focused on the
            "guardrail" guidance the agent must always remember when
            using these tools (e.g. "ZIA needs activation after writes",
            "rule_type is required on every cloud-app-control CRUD call").
    """

    id: str
    service: str
    description: str
    default: bool = False
    instructions: Optional[Callable[["ToolsetCatalog"], str]] = None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


@dataclass
class ToolsetCatalog:
    """Registry of every known toolset.

    The catalog is a flat dict keyed by toolset id. It is populated at
    import time by :data:`TOOLSETS`; tests may construct ad-hoc catalogs
    via :meth:`from_iter` for isolated coverage.
    """

    _by_id: Dict[str, ToolsetMetadata] = field(default_factory=dict)

    # ---- mutation -------------------------------------------------------

    def register(self, metadata: ToolsetMetadata) -> ToolsetMetadata:
        """Register a toolset. Raises ``ValueError`` on duplicate id."""
        if metadata.id in self._by_id:
            raise ValueError(f"Duplicate toolset id: {metadata.id!r}")
        self._by_id[metadata.id] = metadata
        return metadata

    @classmethod
    def from_iter(cls, items: Iterable[ToolsetMetadata]) -> "ToolsetCatalog":
        cat = cls()
        for item in items:
            cat.register(item)
        return cat

    # ---- access ---------------------------------------------------------

    def get(self, toolset_id: str) -> Optional[ToolsetMetadata]:
        return self._by_id.get(toolset_id)

    def has(self, toolset_id: str) -> bool:
        return toolset_id in self._by_id

    def all_ids(self) -> List[str]:
        """Sorted list of every registered toolset id."""
        return sorted(self._by_id)

    def default_ids(self) -> List[str]:
        """Sorted list of toolset ids whose ``default`` flag is True."""
        return sorted(t.id for t in self._by_id.values() if t.default)

    def for_service(self, service: str) -> List[ToolsetMetadata]:
        """Every toolset belonging to a given service code."""
        return sorted(
            (t for t in self._by_id.values() if t.service == service),
            key=lambda t: t.id,
        )

    def values(self) -> List[ToolsetMetadata]:
        return list(self._by_id.values())

    # ---- selection helper used by the registration pipeline ------------

    def resolve(
        self,
        requested: Optional[Iterable[str]],
    ) -> Tuple[Set[str], List[str]]:
        """Resolve a requested selection into a concrete set of toolset ids.

        ``requested`` may include the special keywords ``"default"`` and
        ``"all"``. Whitespace-only entries are dropped. Unknown ids are
        returned in the second element of the tuple so the caller can
        warn the user (matching GitHub's ``unrecognizedToolsets``
        pattern — they're surfaced as warnings, not fatal errors).

        Selection rules:
        * ``requested is None``       → expand "default".
        * ``requested == []``         → empty set (useful when running in
          dynamic-discovery mode where toolsets are enabled at runtime).
        * ``"all"`` anywhere in input → every registered toolset id.
        * ``"default"`` anywhere      → expanded in place to default ids.
        """

        if requested is None:
            return set(self.default_ids()), []

        cleaned: List[str] = []
        for raw in requested:
            if raw is None:
                continue
            trimmed = raw.strip()
            if trimmed:
                cleaned.append(trimmed)

        if not cleaned:
            return set(), []

        if any(item == "all" for item in cleaned):
            return set(self.all_ids()), []

        selected: Set[str] = set()
        unknown: List[str] = []
        for item in cleaned:
            if item == "default":
                selected.update(self.default_ids())
            elif self.has(item):
                selected.add(item)
            else:
                unknown.append(item)

        # The meta toolset is always selected — its tools are core
        # infrastructure (connectivity check, discovery) and must never be
        # filtered out even when the user picks a narrow toolset list.
        if self.has(META_TOOLSET_ID):
            selected.add(META_TOOLSET_ID)

        return selected, unknown


# ---------------------------------------------------------------------------
# Standalone helper used by callers that just want to resolve a string
# (e.g. from a CLI arg or HTTP header) against the canonical catalog.
# ---------------------------------------------------------------------------


def resolve_toolset_selection(
    requested: Optional[Iterable[str]],
    catalog: Optional[ToolsetCatalog] = None,
) -> Tuple[Set[str], List[str]]:
    """Convenience wrapper around :meth:`ToolsetCatalog.resolve`."""
    return (catalog or TOOLSETS).resolve(requested)


# ===========================================================================
# Per-toolset instruction snippets
# ===========================================================================
#
# These are short paragraphs that get composed into the MCP server's
# ``instructions`` field at startup, *only when the toolset is enabled*.
# Each snippet is a function so it can inspect sibling toolsets and adjust
# guidance, mirroring GitHub's ``InstructionsFunc(inv *Inventory) string``
# pattern.
#
# Style guide:
#   • 1–4 sentences max, focused on guardrails the agent must always
#     remember when using these tools.
#   • Reference tool names verbatim.
#   • No service-overview prose — that goes in the toolset description.

# ---- ZIA -------------------------------------------------------------------

def _zia_umbrella_instructions(_: ToolsetCatalog) -> str:
    return (
        "ZIA writes are staged until activation. After any successful "
        "zia_create_*/zia_update_*/zia_delete_*, call "
        "zia_activate_configuration. Forgetting this is the #1 reason "
        "users say 'my change didn't work'."
    )


def _zia_cloud_app_control_instructions(_: ToolsetCatalog) -> str:
    return (
        "Cloud App Control rules: rule_type is required on every "
        "zia_create/update/delete_cloud_app_control_rule. Discover it via "
        "zia_list_cloud_app_policy — the app's `parent` field is the "
        "rule_type. Then call zia_list_cloud_app_control_actions to get "
        "the valid `actions` enum for that category."
    )


def _zia_cloud_firewall_dns_instructions(_: ToolsetCatalog) -> str:
    return (
        "DNS rules' `applications` field accepts the same canonical "
        "ZIA cloud-app names as `cloud_applications` on other rule "
        "types — friendly display names are auto-resolved via the "
        "internal cloud-app catalog before the API call."
    )


def _zia_url_categories_instructions(_: ToolsetCatalog) -> str:
    return (
        "URL categories: predefined categories cannot be deleted and "
        "cannot be created. To add or remove URLs from a predefined "
        "category, use zia_update_url_category_predefined with the "
        "ADD_TO_LIST / REMOVE_FROM_LIST configured_name. Use "
        "zia_create_url_category only for custom categories."
    )


def _zia_policy_rules_instructions(_: ToolsetCatalog) -> str:
    return (
        "Every ZIA rule resource enforces a 1-based `order` (defaults to "
        "1, top of the list) and a `rank` (defaults to 7). All "
        "zia_update_*_rule tools are PUT-replace under the hood and "
        "silently backfill required identifiers (name, order, etc.) "
        "from the existing rule when omitted."
    )


# ---- ZPA -------------------------------------------------------------------

def _zpa_umbrella_instructions(catalog: ToolsetCatalog) -> str:
    chain = (
        "Application onboarding dependency chain: app connector group → "
        "server group → segment group → application segment → access "
        "policy rule. Skipping a step causes cryptic 400 errors."
    )
    if catalog.has("zpa_policy"):
        chain += (
            " New policy rules are appended at the end by default; "
            "policy is evaluated top-to-bottom, so order matters."
        )
    return chain


# ---- ZDX -------------------------------------------------------------------

def _zdx_umbrella_instructions(_: ToolsetCatalog) -> str:
    return (
        "ZDX is read-only except for deep traces and analyses. The "
        "`since` parameter on every ZDX query tool is in HOURS, not a "
        "timestamp. Default is 2 hours. Always ask the user for scope "
        "(location, department, geo) before running broad queries on "
        "large tenants."
    )


# ---- ZMS -------------------------------------------------------------------

def _zms_umbrella_instructions(_: ToolsetCatalog) -> str:
    return (
        "ZMS uses GraphQL and is read-only. Every query is scoped by "
        "ZSCALER_CUSTOMER_ID (resolved automatically from env). Tag "
        "hierarchy is namespace → key → value — discover top-down."
    )


# ===========================================================================
# Canonical catalog
# ===========================================================================
#
# Defaults policy: the "default" set is intentionally narrower than "all"
# (mirrors GitHub's ~40-tool default). It loads the toolsets a brand-new
# user is most likely to want first, so the out-of-box context cost is
# low. Users can opt into more via --toolsets, X-MCP-Toolsets, or the
# /mcp/x/{toolsets} URL path.

TOOLSETS = ToolsetCatalog()


# ---- Always-on cross-service meta tools ------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id=META_TOOLSET_ID,
    service="meta",
    description=(
        "Cross-service meta-tools (connectivity check, service discovery, "
        "tool search, toolset discovery). Always loaded — never filtered."
    ),
    default=True,
))


# ---- ZIA toolsets ----------------------------------------------------------
#
# ZIA is the largest service. We split it into ~10 sub-toolsets along the
# same boundaries the API itself uses (see CLAUDE.md "ZIA Policy-Rule
# Tool Family" table).

TOOLSETS.register(ToolsetMetadata(
    id="zia_admin",
    service="zia",
    description=(
        "ZIA tenant administration: activation, admin users/roles, "
        "auth settings, audit/intermediate-CA configuration."
    ),
    default=True,
    instructions=_zia_umbrella_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_locations",
    service="zia",
    description=(
        "ZIA location and sub-location management, location groups, "
        "VPN credentials, static IPs, GRE tunnels."
    ),
    default=True,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_url_filtering",
    service="zia",
    description=(
        "ZIA URL Filtering policy rules (zia_*_url_filtering_rule)."
    ),
    default=True,
    instructions=_zia_policy_rules_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_url_categories",
    service="zia",
    description=(
        "ZIA URL category catalog (custom + predefined). Includes the "
        "predefined-category mutation tools."
    ),
    default=True,
    instructions=_zia_url_categories_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_cloud_firewall",
    service="zia",
    description=(
        "ZIA Cloud Firewall rules (filtering, DNS, IPS), network "
        "services, network application groups, IP source/destination "
        "groups."
    ),
    default=True,
    instructions=_zia_cloud_firewall_dns_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_ssl_inspection",
    service="zia",
    description="ZIA SSL Inspection policy rules.",
    default=False,
    instructions=_zia_policy_rules_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_dlp",
    service="zia",
    description=(
        "ZIA Web DLP rules, DLP dictionaries, DLP engines, DLP "
        "notification templates, ICAP servers."
    ),
    default=False,
    instructions=_zia_policy_rules_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_file_type_control",
    service="zia",
    description=(
        "ZIA File Type Control rules and file type categories."
    ),
    default=False,
    instructions=_zia_policy_rules_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_sandbox",
    service="zia",
    description=(
        "ZIA Sandbox policy rules and sandbox report/quota inspection."
    ),
    default=False,
    instructions=_zia_policy_rules_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_cloud_app_control",
    service="zia",
    description=(
        "ZIA Cloud App Control policy rules + cloud-app catalog browsers."
    ),
    default=False,
    instructions=_zia_cloud_app_control_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_shadow_it",
    service="zia",
    description=(
        "ZIA Shadow IT analytics: cloud application catalog, custom "
        "tags, bulk sanctioning."
    ),
    default=False,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_users",
    service="zia",
    description=(
        "ZIA users, user groups, departments, device groups, devices."
    ),
    default=True,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_workload_groups",
    service="zia",
    description="ZIA workload groups (used as a rule operand).",
    default=False,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_time_intervals",
    service="zia",
    description=(
        "Reusable time-interval objects referenced by all ZIA rule "
        "types via the `time_windows` field."
    ),
    default=False,
))

TOOLSETS.register(ToolsetMetadata(
    id="zia_misc",
    service="zia",
    description=(
        "Miscellaneous ZIA resources that don't fit the above buckets "
        "(rule labels, forwarding rules, FTP control, etc.)."
    ),
    default=False,
))


# ---- ZPA toolsets ----------------------------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id="zpa_app_segments",
    service="zpa",
    description=(
        "ZPA application segments (incl. PRA, browser-access, inspection "
        "variants), segment groups, server groups."
    ),
    default=True,
    instructions=_zpa_umbrella_instructions,
))

TOOLSETS.register(ToolsetMetadata(
    id="zpa_policy",
    service="zpa",
    description=(
        "ZPA policy rules: access, app-protection, forwarding, "
        "isolation, timeout, capabilities, conditional access, "
        "client/credential/console."
    ),
    default=True,
))

TOOLSETS.register(ToolsetMetadata(
    id="zpa_connectors",
    service="zpa",
    description=(
        "ZPA app connector groups, app connectors, service edges, "
        "service edge groups, provisioning keys."
    ),
    default=True,
))

TOOLSETS.register(ToolsetMetadata(
    id="zpa_idp",
    service="zpa",
    description=(
        "ZPA identity providers, SAML attributes, SCIM attributes, "
        "SCIM groups, posture profiles, trusted networks, "
        "machine groups, isolation profiles, customer version profiles."
    ),
    default=False,
))

TOOLSETS.register(ToolsetMetadata(
    id="zpa_microtenants",
    service="zpa",
    description="ZPA microtenants and microtenant scope management.",
    default=False,
))

TOOLSETS.register(ToolsetMetadata(
    id="zpa_misc",
    service="zpa",
    description=(
        "Other ZPA resources: certificates, pra (privileged remote "
        "access) consoles/credentials/portals/approvals, application "
        "servers, enrollment certificates."
    ),
    default=False,
))


# ---- ZDX toolset(s) --------------------------------------------------------
#
# ZDX is naturally smaller and read-only; we keep it as a single
# default-on toolset rather than fragmenting.

TOOLSETS.register(ToolsetMetadata(
    id="zdx",
    service="zdx",
    description=(
        "Zscaler Digital Experience: device, application, and alert "
        "querying plus deep-trace/analysis lifecycle (read-only "
        "except for deep-trace start/stop and analysis start/stop)."
    ),
    default=True,
    instructions=_zdx_umbrella_instructions,
))


# ---- ZCC toolset -----------------------------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id="zcc",
    service="zcc",
    description=(
        "Zscaler Client Connector: enrolled-device inventory, trusted "
        "networks, forwarding profiles."
    ),
    default=True,
))


# ---- ZTW toolset -----------------------------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id="ztw",
    service="ztw",
    description=(
        "Zscaler Workload Segmentation administration."
    ),
    default=False,
))


# ---- ZIdentity toolset -----------------------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id="zid",
    service="zid",
    description=(
        "ZIdentity user, group, role, and entitlement administration."
    ),
    default=False,
))


# ---- ZEASM toolset ---------------------------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id="zeasm",
    service="zeasm",
    description=(
        "Zscaler External Attack Surface Management: assets, findings, "
        "discovery."
    ),
    default=False,
))


# ---- ZInsights toolset -----------------------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id="zins",
    service="zins",
    description=(
        "Z-Insights queries: network and security log analytics."
    ),
    default=False,
))


# ---- ZMS toolset -----------------------------------------------------------

TOOLSETS.register(ToolsetMetadata(
    id="zms",
    service="zms",
    description=(
        "Zscaler Microsegmentation (GraphQL, read-only): agents, "
        "resources, policy rules, app zones, tags."
    ),
    default=False,
    instructions=_zms_umbrella_instructions,
))


# ===========================================================================
# Tool-name → toolset id mapping
# ===========================================================================
#
# This is the single source of truth for which toolset every tool belongs
# to. Rather than annotate every tool dict in services.py, we keep the
# mapping centralized here so that:
#
#   * Adding a new tool means adding ONE line to either the explicit
#     overrides dict or — if it follows our naming convention — relying on
#     the prefix-based fallback.
#   * The whole catalog can be audited in one place.
#   * Renaming or splitting a toolset is a one-file change.
#
# Resolution order for a given tool name:
#   1. Explicit override in _TOOL_TOOLSET_OVERRIDES (exact match).
#   2. First matching prefix in _TOOLSET_PREFIX_RULES (in declaration
#      order — so most-specific prefixes must be listed FIRST).
#   3. Bare service-name fallback (zcc → "zcc", ztw → "ztw", etc.).
#   4. META_TOOLSET_ID for the small set of cross-service meta tools.
#   5. ValueError — fail loudly so unmapped tools can't slip into
#     production with the wrong (or no) toolset.

# Tool names that are special cases or don't follow the conventional
# {service}_{verb}_{resource} shape (legacy ZIA names, meta tools, etc.).
_TOOL_TOOLSET_OVERRIDES: Dict[str, str] = {
    # ---- Cross-service meta tools (always loaded) ----------------------
    "zscaler_check_connectivity": META_TOOLSET_ID,
    "zscaler_get_available_services": META_TOOLSET_ID,
    "zscaler_list_toolsets": META_TOOLSET_ID,
    "zscaler_get_toolset_tools": META_TOOLSET_ID,
    "zscaler_enable_toolset": META_TOOLSET_ID,

    # ---- Legacy ZIA tool names (no zia_ prefix) ------------------------
    "get_zia_users": "zia_users",
    "get_zia_user_groups": "zia_users",
    "get_zia_user_departments": "zia_users",
    "get_zia_dlp_dictionaries": "zia_dlp",
    "get_zia_dlp_engines": "zia_dlp",

    # ---- ZIA: tools whose names don't include the toolset boundary ----
    "zia_geo_search": "zia_locations",
    "zia_url_lookup": "zia_url_categories",
    "zia_activate_configuration": "zia_admin",
    "zia_get_activation_status": "zia_admin",
    "zia_list_devices": "zia_users",
    "zia_list_devices_lite": "zia_users",
    "zia_list_device_groups": "zia_users",

    # ZIA: shadow-IT (separate from cloud-app-control catalog)
    "zia_list_shadow_it_apps": "zia_shadow_it",
    "zia_list_shadow_it_custom_tags": "zia_shadow_it",
    "zia_bulk_update_shadow_it_apps": "zia_shadow_it",

    # ZIA: cloud-application policy catalog (used by SSL/DLP/FTC/CAC
    # rules) — surface under the cloud-app-control toolset since that's
    # the tool family it primarily supports.
    "zia_list_cloud_app_policy": "zia_cloud_app_control",
    "zia_list_cloud_app_ssl_policy": "zia_cloud_app_control",
    "zia_list_cloud_app_control_actions": "zia_cloud_app_control",

    # ZIA: ATP malicious URLs and auth-exempt URLs
    "zia_list_atp_malicious_urls": "zia_url_categories",
    "zia_add_atp_malicious_urls": "zia_url_categories",
    "zia_delete_atp_malicious_urls": "zia_url_categories",
    "zia_list_auth_exempt_urls": "zia_url_categories",
    "zia_add_auth_exempt_urls": "zia_url_categories",
    "zia_delete_auth_exempt_urls": "zia_url_categories",

    # ZIA: rule labels are a generic resource shared across all rule
    # families — pin them under the umbrella admin toolset so they're
    # always available alongside the rules that reference them.
    "zia_list_rule_labels": "zia_admin",
    "zia_get_rule_label": "zia_admin",
    "zia_create_rule_label": "zia_admin",
    "zia_update_rule_label": "zia_admin",
    "zia_delete_rule_label": "zia_admin",

    # ZIA: workload groups (cross-rule operand)
    "zia_list_workload_groups": "zia_workload_groups",
    "zia_get_workload_group": "zia_workload_groups",

    # ZIA: time intervals (cross-rule scheduling object)
    "zia_list_time_intervals": "zia_time_intervals",
    "zia_get_time_interval": "zia_time_intervals",
    "zia_create_time_interval": "zia_time_intervals",
    "zia_update_time_interval": "zia_time_intervals",
    "zia_delete_time_interval": "zia_time_intervals",

    # ZIA: sandbox info tools (read-only quota/report) live alongside
    # sandbox rules so a user enabling zia_sandbox gets both.
    "zia_get_sandbox_quota": "zia_sandbox",
    "zia_get_sandbox_report": "zia_sandbox",
    "zia_get_sandbox_behavioral_analysis": "zia_sandbox",
    "zia_get_sandbox_file_hash_count": "zia_sandbox",

    # ---- ZPA: pra (privileged remote access) ---------------------------
    "zpa_list_pra_credentials": "zpa_misc",
    "zpa_get_pra_credential": "zpa_misc",
    "zpa_create_pra_credential": "zpa_misc",
    "zpa_update_pra_credential": "zpa_misc",
    "zpa_delete_pra_credential": "zpa_misc",
    "zpa_list_pra_portals": "zpa_misc",
    "zpa_get_pra_portal": "zpa_misc",
    "zpa_create_pra_portal": "zpa_misc",
    "zpa_update_pra_portal": "zpa_misc",
    "zpa_delete_pra_portal": "zpa_misc",

    # ZPA: certificates and application servers (under misc)
    "zpa_list_ba_certificates": "zpa_misc",
    "zpa_get_ba_certificate": "zpa_misc",
    "zpa_create_ba_certificate": "zpa_misc",
    "zpa_delete_ba_certificate": "zpa_misc",
    "zpa_list_application_servers": "zpa_misc",
    "zpa_get_application_server": "zpa_misc",
    "zpa_create_application_server": "zpa_misc",
    "zpa_update_application_server": "zpa_misc",
    "zpa_delete_application_server": "zpa_misc",

    # ZPA: idp-adjacent reads (under zpa_idp)
    "get_zpa_isolation_profile": "zpa_idp",
    "get_zpa_posture_profile": "zpa_idp",
    "get_zpa_saml_attribute": "zpa_idp",
    "get_zpa_scim_attribute": "zpa_idp",
    "get_zpa_scim_group": "zpa_idp",
    "get_zpa_trusted_network": "zpa_idp",
    "get_zpa_app_protection_profile": "zpa_misc",
    "get_zpa_enrollment_certificate": "zpa_connectors",
    "get_zpa_app_segments_by_type": "zpa_app_segments",

    # ---- ZTW IP groups -------------------------------------------------
    # All ztw_* tools collapse into a single ztw toolset.
}


# Prefix rules — first match wins. List MORE-SPECIFIC patterns FIRST.
# A predicate is a callable taking a tool name and returning bool.
_TOOLSET_PREFIX_RULES: List[Tuple[Callable[[str], bool], str]] = [
    # ===================================================================
    # ZIA — order matters; check the most-specific patterns first
    # ===================================================================

    # Cloud App Control rules + the actions discovery tool
    (lambda n: "_cloud_app_control_" in n, "zia_cloud_app_control"),

    # Cloud Firewall family — must come before generic "cloud_firewall"
    (lambda n: "_cloud_firewall_dns_" in n, "zia_cloud_firewall"),
    (lambda n: "_cloud_firewall_ips_" in n, "zia_cloud_firewall"),
    (lambda n: "_cloud_firewall_" in n,     "zia_cloud_firewall"),

    # File Type Control
    (lambda n: "_file_type_control_" in n,  "zia_file_type_control"),
    (lambda n: "_file_type_categories" in n, "zia_file_type_control"),

    # SSL Inspection
    (lambda n: "_ssl_inspection_" in n,     "zia_ssl_inspection"),

    # Web DLP
    (lambda n: "_web_dlp_" in n,            "zia_dlp"),

    # Sandbox rules (sandbox info tools handled in overrides)
    (lambda n: "_sandbox_rule" in n,        "zia_sandbox"),

    # URL filtering
    (lambda n: "_url_filtering_" in n,      "zia_url_filtering"),

    # URL categories (predefined + custom + ADD/REMOVE URLs)
    (lambda n: "_url_categor" in n or n.endswith("_urls_to_category") or n.endswith("_urls_from_category"),
     "zia_url_categories"),

    # Locations / GRE / VPN credentials / static IPs
    (lambda n: "_location" in n,            "zia_locations"),
    (lambda n: "_gre_" in n or "_gre_tunnel" in n, "zia_locations"),
    (lambda n: "_vpn_credential" in n,      "zia_locations"),
    (lambda n: "_static_ip" in n,           "zia_locations"),

    # Network services / app groups / svc groups / ip src/dst groups
    (lambda n: "_network_app" in n or "_network_service" in n
              or "_network_svc_" in n,      "zia_cloud_firewall"),
    (lambda n: "_ip_destination_group" in n or "_ip_source_group" in n,
                                            "zia_cloud_firewall"),

    # ===================================================================
    # ZPA — order matters
    # ===================================================================

    # Policy rule families — all map to zpa_policy
    (lambda n: "_access_policy_rule" in n,     "zpa_policy"),
    (lambda n: "_app_protection_rule" in n,    "zpa_policy"),
    (lambda n: "_forwarding_policy_rule" in n, "zpa_policy"),
    (lambda n: "_isolation_policy_rule" in n,  "zpa_policy"),
    (lambda n: "_timeout_policy_rule" in n,    "zpa_policy"),

    # Connector & service-edge family
    (lambda n: "_app_connector" in n,          "zpa_connectors"),
    (lambda n: "_service_edge" in n,           "zpa_connectors"),
    (lambda n: "_provisioning_key" in n,       "zpa_connectors"),

    # App segments + segment groups + server groups
    (lambda n: "_application_segment" in n,    "zpa_app_segments"),
    (lambda n: "_segment_group" in n,          "zpa_app_segments"),
    (lambda n: "_server_group" in n,           "zpa_app_segments"),

    # ===================================================================
    # ZTW — collapse into a single toolset
    # ===================================================================
    (lambda n: n.startswith("ztw_"),           "ztw"),
]


def toolset_for_tool(tool_name: str) -> str:
    """Return the toolset id that owns ``tool_name``.

    Resolution order:
        1. Explicit override (``_TOOL_TOOLSET_OVERRIDES``).
        2. First matching prefix rule (``_TOOLSET_PREFIX_RULES``).
        3. Bare service prefix fallback (``zcc_*`` → ``zcc``, etc.).

    Raises:
        KeyError: if the tool name can't be mapped. This is intentional —
            an unmapped tool is a bug we want to catch at registration
            time, not a thing we want to silently dump into a default
            bucket.
    """
    if tool_name in _TOOL_TOOLSET_OVERRIDES:
        return _TOOL_TOOLSET_OVERRIDES[tool_name]

    for predicate, toolset_id in _TOOLSET_PREFIX_RULES:
        if predicate(tool_name):
            return toolset_id

    # Bare service-name fallback: zcc_*, zdx_*, zid_*, zeasm_*,
    # zins_*, zms_*, ztw_* all collapse into a single toolset per service
    # (toolset id == service code).
    for prefix in ("zcc_", "zdx_", "zid_", "zeasm_", "zins_", "zms_"):
        if tool_name.startswith(prefix):
            tsid = prefix.rstrip("_")
            if TOOLSETS.has(tsid):
                return tsid

    # Generic ZIA fallback for tools not caught by a more specific rule.
    if tool_name.startswith("zia_") or tool_name.startswith("get_zia_"):
        return "zia_misc"

    # Generic ZPA fallback.
    if tool_name.startswith("zpa_") or tool_name.startswith("get_zpa_"):
        return "zpa_misc"

    raise KeyError(
        f"No toolset mapping for tool {tool_name!r}. "
        "Add an entry to _TOOL_TOOLSET_OVERRIDES or a rule to "
        "_TOOLSET_PREFIX_RULES in zscaler_mcp/common/toolsets.py."
    )
