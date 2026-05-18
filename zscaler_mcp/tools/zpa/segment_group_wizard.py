"""ZPA Segment Group Wizard — interactive embedded MCP-UI tool.

Implements the **MCP Apps** standard
(<https://modelcontextprotocol.io/docs/extensions/apps.md>, spec
version ``2026-01-26``) for an interactive segment-group create wizard
that renders inline in MCP-Apps-capable hosts (Cursor, Claude, ChatGPT
Apps, Goose, VS Code Copilot).

The wizard pattern uses **two** MCP primitives, intentionally
decoupled:

1. **A tool with a UI pointer in its descriptor.** This module's
   :func:`zpa_segment_group_wizard` is registered with
   ``meta={"ui": {"resourceUri": "ui://zscaler/zpa/segment-group-wizard/v1"}}``.
   When the model calls the tool, the host sees the pointer and knows
   "this tool ships a UI".
2. **A resource at the ``ui://...`` URI.** The host fetches it via
   ``resources/read``. We register the HTML bundle via FastMCP at the
   same URI; the body is the wizard HTML produced by
   :func:`get_wizard_html_resource`.

The tool function itself **does not** return the HTML inline (that's
the legacy mcp-ui "embedded UIResource" pattern, which today's
spec-compliant hosts — including Cursor — do not render). Instead it
returns structured text that the model can narrate, plus a pointer the
host already has from the descriptor.

When the admin clicks "Create segment group" inside the iframe, the
    wizard ``postMessage``\\s a ``tools/call`` for
:func:`zscaler_mcp.tools.zpa.segment_groups.zpa_create_segment_group`
back to the host. The host translates that into a real MCP tool call
that still enforces the existing safety rails (``--write-tools``
allowlist, HMAC confirmation, audit logging, etc.).

See the rollout notes and known gaps in
``local_dev/interactive-mcp-server/README.md``.
"""

from importlib.resources import files
from typing import Annotated, List

from mcp.types import TextContent
from pydantic import Field

# ---------------------------------------------------------------------------
# Canonical URI for the wizard resource. Bump the trailing version segment
# (``/v1`` -> ``/v2``) on any breaking change to the HTML schema or the
# postMessage protocol — hosts cache resources by URI.
# ---------------------------------------------------------------------------
WIZARD_RESOURCE_URI = "ui://zscaler/zpa/segment-group-wizard/v1"

# ---------------------------------------------------------------------------
# MCP Apps descriptor metadata. Attached to the tool registration so the
# host can preload the UI before / during the tool call.
# ---------------------------------------------------------------------------
WIZARD_TOOL_META: dict = {
    "ui": {
        "resourceUri": WIZARD_RESOURCE_URI,
    }
}

# Loaded once at import time so each tool call (and each resource fetch)
# doesn't hit disk.
_WIZARD_HTML = (files(__package__) / "wizards" / "segment_group.html").read_text(
    encoding="utf-8"
)


def get_wizard_html_resource() -> str:
    """Return the wizard HTML bundle.

    Registered as a FastMCP resource at :data:`WIZARD_RESOURCE_URI`
    (``ui://zscaler/zpa/segment-group-wizard/v1``) by
    :class:`zscaler_mcp.services.ZPAService`. Hosts call
    ``resources/read`` on that URI to obtain this body and mount it in
    a sandboxed iframe.
    """
    return _WIZARD_HTML


def zpa_segment_group_wizard(
    name: Annotated[
        str | None,
        Field(
            description=(
                "Optional pre-fill for the wizard's 'Group name' field. "
                "Use when the admin's request already names the group "
                "(e.g. 'open the segment-group wizard for Production "
                "Web Apps')."
            )
        ),
    ] = None,
    description: Annotated[
        str | None,
        Field(
            description=(
                "Optional pre-fill for the wizard's 'Description' field."
            )
        ),
    ] = None,
    enabled: Annotated[
        bool,
        Field(
            description=(
                "Pre-select the wizard's 'Enabled' toggle. Defaults to "
                "True — set to False only if the admin explicitly wants "
                "the group to land disabled."
            )
        ),
    ] = True,
    microtenant_id: Annotated[
        str | None,
        Field(
            description=(
                "Optional pre-fill for the wizard's microtenant field. "
                "Leave unset for the parent tenant."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[TextContent]:
    """Open an interactive wizard to create a ZPA segment group.

    The tool advertises a UI via ``_meta.ui.resourceUri`` (set at tool
    registration time, see
    :class:`zscaler_mcp.services.ZPAService`). MCP-Apps-capable hosts
    (Cursor, Claude, ChatGPT Apps, Goose, VS Code Copilot) fetch the
    wizard HTML at that URI and mount it in a sandboxed iframe under
    the tool-call disclosure.

    The tool itself is **read-only**: it does not call any Zscaler API.
    The create only happens if the admin clicks "Create segment group"
    inside the wizard, which posts a ``tools/call`` for
    :func:`zpa_create_segment_group` back through the host — and that
    write tool still has to be enabled and allowlisted on the server.

    On hosts that don't render MCP Apps UIs (stdio CLIs, AgentCore,
    Bedrock, raw HTTP clients) the admin just sees the text summary
    and the model should fall back to calling
    ``zpa_create_segment_group(...)`` directly.

    Args:
        name: Optional initial value for the group's name field.
        description: Optional initial value for the description.
        enabled: Initial state of the Enabled toggle (default True).
        microtenant_id: Optional initial value for the microtenant
            field.
        service: SDK service identifier (default ``"zpa"``).

    Returns:
        A list with one :class:`~mcp.types.TextContent` summarising what
        the wizard was opened with. The actual UI is delivered via the
        ``_meta.ui.resourceUri`` pointer on the tool descriptor — not
        via this return value — so non-rendering hosts still get a
        useful textual response.
    """
    initial = {
        "name": name or "",
        "description": description or "",
        "enabled": bool(enabled),
        "microtenant_id": microtenant_id or "",
    }

    summary_parts: list[str] = ["Opened the ZPA Segment Group wizard."]
    if name:
        summary_parts.append(f"Pre-filled name: '{name}'.")
    if description:
        truncated = description if len(description) <= 60 else description[:57] + "..."
        summary_parts.append(f"Pre-filled description: '{truncated}'.")
    if enabled is False:
        summary_parts.append("Pre-set to disabled.")
    if microtenant_id:
        summary_parts.append(f"Pre-filled microtenant: '{microtenant_id}'.")

    summary_parts.append(
        "Hosts that support MCP Apps (Cursor, Claude, ChatGPT Apps, "
        f"Goose, VS Code Copilot) will mount the wizard at "
        f"{WIZARD_RESOURCE_URI} in a sandboxed iframe. The admin "
        "submits the form to trigger zpa_create_segment_group. On "
        "non-rendering hosts, call zpa_create_segment_group(...) "
        "directly with these initial values: " + repr(initial)
    )

    return [TextContent(type="text", text=" ".join(summary_parts))]


__all__ = [
    "WIZARD_RESOURCE_URI",
    "WIZARD_TOOL_META",
    "get_wizard_html_resource",
    "zpa_segment_group_wizard",
]
