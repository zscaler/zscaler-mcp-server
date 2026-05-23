"""
ZPA Application Segment Privileged Remote Access Tools

Privileged Remote Access (PRA) application segments are a distinct ZPA
resource type served by the SDK API ``client.zpa.app_segments_pra``
(separate from both the regular ``client.zpa.application_segment`` and
the Browser Access ``client.zpa.app_segments_ba_v2`` resources).

A PRA segment publishes one or more **RDP** or **SSH** targets to
authorized users through Zscaler's Privileged Remote Access portal.
End users connect through their browser without a native RDP/SSH client
and without ZCC; the connection is brokered by the PRA portal and uses
PRA credentials managed separately as ``pra_credential`` and
``pra_portal`` resources.

Each PRA segment carries a ``common_apps_dto.apps_config`` block listing
one PRA app per published target, with the target's domain, port,
protocol (``RDP``/``SSH``), and — for RDP — the desired
``connection_security`` mode. The SDK auto-injects
``app_types: ["SECURE_REMOTE_ACCESS"]`` if missing.

The five tools in this module are uniformly suffixed ``_pra`` so the
agent can always tell them apart from the regular and BA application-
segment tools. Use these tools only when the admin explicitly asks for
**Privileged Remote Access** (RDP/SSH); for traditional client-routed
app segments use ``zpa_*_application_segment`` and for browser-published
web apps use ``zpa_*_application_segment_ba``.
"""

from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# Helpers (private to this module)
# =============================================================================


# `application_protocol` on a PRA app is the wire protocol of the target.
_PRA_PROTOCOLS = {"RDP", "SSH"}

# `connection_security` is RDP-only. It controls the RDP transport security
# negotiated by the PRA portal. Ignored for SSH.
_PRA_RDP_CONNECTION_SECURITY = {"ANY", "NLA", "NLA_EXT", "TLS", "VM_CONNECT", "RDP"}


def _validate_apps_config(
    apps_config: List[Dict[str, Any]],
    domain_names: Optional[List[str]],
    *,
    require_domain_in_segment: bool,
) -> None:
    """Validate the apps_config payload before sending it to the SDK.

    The ZPA PRA API rejects mismatches between an app's ``domain`` and the
    segment's ``domain_names`` with a generic error. Catching it here keeps
    the round-trip count down and returns a clear message.

    Args:
        apps_config: List of PRA app config dicts, as supplied by the caller.
        domain_names: The segment's ``domain_names``. Required on create,
            optional on update (where the existing segment's domains are
            preserved if not re-supplied).
        require_domain_in_segment: When True, every ``apps_config[].domain``
            must appear in ``domain_names``. Set False on update calls that
            don't pass ``domain_names`` (the SDK will diff against the
            existing segment).
    """
    required = ("domain", "application_port", "application_protocol", "name")
    segment_domains = set(domain_names or [])

    for i, app in enumerate(apps_config):
        if not isinstance(app, dict):
            raise ValueError(
                f"apps_config[{i}] must be a dict, got {type(app).__name__}"
            )
        missing = [k for k in required if not app.get(k)]
        if missing:
            raise ValueError(
                f"apps_config[{i}] is missing required field(s): {', '.join(missing)}. "
                f"Required: {', '.join(required)}."
            )
        protocol = app["application_protocol"]
        if protocol not in _PRA_PROTOCOLS:
            raise ValueError(
                f"apps_config[{i}].application_protocol must be one of "
                f"{sorted(_PRA_PROTOCOLS)}, got '{protocol}'."
            )
        connection_security = app.get("connection_security")
        if connection_security is not None:
            if protocol != "RDP":
                raise ValueError(
                    f"apps_config[{i}].connection_security is only valid when "
                    f"application_protocol == 'RDP'. Drop it for SSH apps."
                )
            if connection_security not in _PRA_RDP_CONNECTION_SECURITY:
                raise ValueError(
                    f"apps_config[{i}].connection_security must be one of "
                    f"{sorted(_PRA_RDP_CONNECTION_SECURITY)}, got "
                    f"'{connection_security}'."
                )
        if require_domain_in_segment and app["domain"] not in segment_domains:
            raise ValueError(
                f"apps_config[{i}].domain '{app['domain']}' is not present in "
                f"the segment's domain_names {sorted(segment_domains)}. "
                f"Every PRA app's domain must also be listed in the segment's "
                f"top-level domain_names."
            )


# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zpa_list_application_segments_pra(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring match on the PRA application segment's "
                "`name` field. Returns the full set of matches in this tenant — "
                "no fuzzy matching, no synonym expansion. An empty list means "
                "no Privileged Remote Access segment name contains this string; "
                "do not retry with split keywords or no filter."
            )
        ),
    ] = None,
    page: Annotated[Optional[int], Field(ge=1, description="Page number for pagination.")] = None,
    page_size: Annotated[Optional[int], Field(ge=1, description="Number of items per page.")] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Any:
    """List ZPA Privileged Remote Access (PRA) application segments.

    PRA segments publish RDP and SSH targets to authorized users through
    Zscaler's PRA portal — no native RDP/SSH client, no ZCC required. This
    tool is the PRA-specific counterpart of ``zpa_list_application_segments``;
    use this one only when the admin asks about Privileged Remote Access
    segments (RDP/SSH).

    Supports JMESPath client-side filtering via the ``query`` parameter.

    🔒 READ-ONLY OPERATION — Safe for autonomous agents.
    """
    client = get_zscaler_client(service=service)
    api = client.zpa.app_segments_pra

    query_params: Dict[str, Any] = {"microtenant_id": microtenant_id}
    if search:
        query_params["search"] = search
    if page is not None:
        query_params["page"] = str(page)
    if page_size is not None:
        query_params["page_size"] = str(page_size)

    segments, _, err = api.list_segments_pra(query_params=query_params)
    if err:
        raise Exception(f"Failed to list PRA application segments: {err}")

    results = [s.as_dict() for s in (segments or [])]
    return apply_jmespath(results, query)


def zpa_get_application_segment_pra(
    segment_id: Annotated[str, Field(description="ID of the PRA application segment to retrieve.")],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA Privileged Remote Access (PRA) application segment by ID.

    Returns the full record, including the ``common_apps_dto.apps_config``
    block that lists each published PRA app (one per RDP/SSH target) with
    its domain, port, protocol, and connection_security (RDP only).

    🔒 READ-ONLY OPERATION — Safe for autonomous agents.
    """
    if not segment_id:
        raise ValueError("segment_id is required")

    client = get_zscaler_client(service=service)
    api = client.zpa.app_segments_pra

    segment, _, err = api.get_segment_pra(
        segment_id, query_params={"microtenant_id": microtenant_id}
    )
    if err:
        raise Exception(f"Failed to get PRA application segment {segment_id}: {err}")

    return segment.as_dict()


# =============================================================================
# WRITE OPERATIONS (require --enable-write-tools)
# =============================================================================


def zpa_create_application_segment_pra(
    name: Annotated[
        str, Field(description="Name of the Privileged Remote Access (PRA) application segment.")
    ],
    segment_group_id: Annotated[str, Field(description="ID of the segment group.")],
    domain_names: Annotated[
        List[str],
        Field(
            description=(
                "Domain names (or IP addresses) of the RDP/SSH targets published "
                "by this PRA segment. Every domain that appears in `apps_config` "
                "MUST also be listed here."
            )
        ),
    ],
    apps_config: Annotated[
        List[Dict[str, Any]],
        Field(
            description=(
                "List of PRA app configurations — one per published RDP/SSH "
                "target. Each entry is a dict with REQUIRED keys: `domain`, "
                "`application_port` (string, e.g. \"3389\" for RDP, \"22\" for "
                "SSH), `application_protocol` (\"RDP\" or \"SSH\"), and `name` "
                "(per-app friendly name). Optional keys: `enabled`, "
                "`connection_security` (RDP only — one of \"ANY\", \"NLA\", "
                "\"NLA_EXT\", \"TLS\", \"VM_CONNECT\", \"RDP\"). The SDK auto-"
                "injects `app_types: [\"SECURE_REMOTE_ACCESS\"]` if missing. "
                "This list is wrapped into the API's `common_apps_dto.apps_config` "
                "block."
            )
        ),
    ],
    server_group_ids: Annotated[
        List[str],
        Field(description="List of server group IDs the PRA segment routes through."),
    ],
    description: Annotated[
        Optional[str], Field(description="Description of the PRA segment.")
    ] = None,
    enabled: Annotated[bool, Field(description="Whether the segment is enabled.")] = True,
    tcp_port_range: Annotated[
        Optional[List[Dict[str, str]]],
        Field(
            description=(
                "TCP port ranges in structured form, e.g. "
                "[{\"from\": \"3389\", \"to\": \"3389\"}]. RDP normally uses 3389, "
                "SSH normally uses 22."
            )
        ),
    ] = None,
    udp_port_range: Annotated[
        Optional[List[Dict[str, str]]],
        Field(description="UDP port ranges in structured form (RDP can also use UDP 3389)."),
    ] = None,
    tcp_port_ranges: Annotated[
        Optional[List[str]],
        Field(description="Legacy TCP port ranges as a flat list of from/to pairs, e.g. [\"3389\", \"3389\"]."),
    ] = None,
    udp_port_ranges: Annotated[
        Optional[List[str]],
        Field(description="Legacy UDP port ranges as a flat list of from/to pairs."),
    ] = None,
    bypass_type: Annotated[
        Optional[Literal["ALWAYS", "NEVER", "ON_NET"]],
        Field(description="Bypass type for the segment."),
    ] = None,
    health_check_type: Annotated[
        Optional[Literal["DEFAULT", "NONE"]],
        Field(description="Health check type."),
    ] = None,
    health_reporting: Annotated[
        Optional[Literal["NONE", "ON_ACCESS", "CONTINUOUS"]],
        Field(description="Health reporting mode."),
    ] = None,
    is_cname_enabled: Annotated[
        Optional[bool], Field(description="Whether CNAMEs are enabled for the segment.")
    ] = None,
    passive_health_enabled: Annotated[
        Optional[bool], Field(description="Whether passive health checks are enabled.")
    ] = None,
    icmp_access_type: Annotated[
        Optional[Literal["NONE", "PING", "PING_TRACEROUTING"]],
        Field(
            description=(
                "Controls whether the PRA segment responds to ICMP. `NONE` "
                "disables ICMP, `PING` allows ping, `PING_TRACEROUTING` allows "
                "ping plus traceroute. Defaults to `NONE` server-side when omitted."
            )
        ),
    ] = None,
    double_encrypt: Annotated[
        Optional[bool],
        Field(description="Enable double encryption for the segment."),
    ] = None,
    config_space: Annotated[
        Optional[Literal["DEFAULT", "SIEM"]],
        Field(description="Configuration space for the segment."),
    ] = None,
    ip_anchored: Annotated[
        Optional[bool], Field(description="Whether the segment is IP-anchored.")
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA Privileged Remote Access (PRA) application segment.

    PRA segments publish RDP and SSH targets to authorized users through
    Zscaler's PRA portal. The end user connects through a browser — no
    native RDP/SSH client, no ZCC. PRA credentials and the PRA portal are
    managed as separate ZPA resources (``pra_credential``, ``pra_portal``)
    and bound to the user via PRA credential policies, NOT on the app
    segment itself.

    This tool is the PRA-specific counterpart of
    ``zpa_create_application_segment``; use this one only when the admin
    explicitly asks for **Privileged Remote Access** (RDP/SSH).

    Required inputs:

    - ``name``, ``segment_group_id``, ``domain_names``, ``server_group_ids``
    - ``apps_config`` — one entry per RDP/SSH target with `domain`,
      `application_port`, `application_protocol` (`RDP`/`SSH`), and `name`.
      For RDP, also supply `connection_security` (e.g. `ANY` or `NLA`).
    - At least one of `tcp_port_range` / `tcp_port_ranges` /
      `udp_port_range` / `udp_port_ranges`. RDP normally uses TCP+UDP
      3389; SSH normally uses TCP 22.

    The tool validates that every ``apps_config[].domain`` appears in
    ``domain_names`` and rejects mismatches before the API round-trip. It
    also rejects `connection_security` on SSH apps and unknown values.

    ⚠️  WRITE OPERATION — Requires --enable-write-tools flag.

    Examples:
        Create an RDP PRA segment:

        >>> segment = zpa_create_application_segment_pra(
        ...     name="DC1 RDP Jumpboxes",
        ...     segment_group_id="72058304855089379",
        ...     domain_names=["rdp01.acme.com", "rdp02.acme.com"],
        ...     server_group_ids=["72058304855090128"],
        ...     tcp_port_range=[{"from": "3389", "to": "3389"}],
        ...     udp_port_range=[{"from": "3389", "to": "3389"}],
        ...     apps_config=[
        ...         {
        ...             "name": "rdp01",
        ...             "domain": "rdp01.acme.com",
        ...             "application_port": "3389",
        ...             "application_protocol": "RDP",
        ...             "connection_security": "ANY",
        ...             "enabled": True,
        ...         },
        ...         {
        ...             "name": "rdp02",
        ...             "domain": "rdp02.acme.com",
        ...             "application_port": "3389",
        ...             "application_protocol": "RDP",
        ...             "connection_security": "ANY",
        ...             "enabled": True,
        ...         },
        ...     ],
        ... )

        Create an SSH PRA segment:

        >>> segment = zpa_create_application_segment_pra(
        ...     name="Linux Bastions",
        ...     segment_group_id="72058304855089379",
        ...     domain_names=["bastion.acme.com"],
        ...     server_group_ids=["72058304855090128"],
        ...     tcp_port_range=[{"from": "22", "to": "22"}],
        ...     apps_config=[
        ...         {
        ...             "name": "bastion",
        ...             "domain": "bastion.acme.com",
        ...             "application_port": "22",
        ...             "application_protocol": "SSH",
        ...             "enabled": True,
        ...         },
        ...     ],
        ... )
    """
    if not name:
        raise ValueError("name is required")
    if not segment_group_id:
        raise ValueError("segment_group_id is required")
    if not domain_names:
        raise ValueError("domain_names is required for PRA segments")
    if not server_group_ids:
        raise ValueError("server_group_ids is required")
    if not apps_config:
        raise ValueError(
            "apps_config is required — at least one PRA app must be supplied "
            "(one entry per RDP/SSH target)."
        )

    if (tcp_port_range and tcp_port_ranges) or (udp_port_range and udp_port_ranges):
        raise ValueError(
            "Use either structured port ranges (tcp_port_range/udp_port_range) "
            "or flat string ranges (tcp_port_ranges/udp_port_ranges), not both."
        )
    if not any([tcp_port_range, udp_port_range, tcp_port_ranges, udp_port_ranges]):
        raise ValueError("At least one port configuration must be provided (TCP or UDP).")

    _validate_apps_config(apps_config, domain_names, require_domain_in_segment=True)

    client = get_zscaler_client(service=service)
    api = client.zpa.app_segments_pra

    body: Dict[str, Any] = {
        "name": name,
        "description": description,
        "enabled": enabled,
        "domain_names": domain_names,
        "segment_group_id": segment_group_id,
        "server_group_ids": server_group_ids,
        "bypass_type": bypass_type,
        "health_check_type": health_check_type,
        "health_reporting": health_reporting,
        "is_cname_enabled": is_cname_enabled,
        "passive_health_enabled": passive_health_enabled,
        "icmp_access_type": icmp_access_type,
        "double_encrypt": double_encrypt,
        "config_space": config_space,
        "ip_anchored": ip_anchored,
        "common_apps_dto": {"apps_config": apps_config},
    }

    if tcp_port_range:
        body["tcp_port_range"] = tcp_port_range
    elif tcp_port_ranges:
        body["tcp_port_ranges"] = tcp_port_ranges
    if udp_port_range:
        body["udp_port_range"] = udp_port_range
    elif udp_port_ranges:
        body["udp_port_ranges"] = udp_port_ranges

    if microtenant_id:
        body["microtenant_id"] = microtenant_id

    created, _, err = api.add_segment_pra(**body)
    if err:
        raise Exception(f"Failed to create PRA application segment: {err}")

    return created.as_dict()


def zpa_update_application_segment_pra(
    segment_id: Annotated[str, Field(description="ID of the PRA segment to update.")],
    name: Annotated[Optional[str], Field(description="Name of the PRA application segment.")] = None,
    segment_group_id: Annotated[
        Optional[str], Field(description="ID of the segment group.")
    ] = None,
    domain_names: Annotated[
        Optional[List[str]],
        Field(
            description=(
                "Domain names (or IPs) published by this PRA segment. If "
                "supplied, every domain in `apps_config` must appear here. If "
                "omitted on update, the existing segment's domains are preserved "
                "by the SDK."
            )
        ),
    ] = None,
    apps_config: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(
            description=(
                "Updated list of PRA app configurations. The SDK diffs this "
                "against the current segment by `domain`: existing apps with a "
                "matching domain keep their `pra_app_id`, new entries are "
                "created (`pra_app_id` left blank), and PRA apps whose domain "
                "is no longer listed are added to `deleted_pra_apps` and "
                "removed. Each entry requires `domain`, `application_port`, "
                "`application_protocol` (RDP/SSH), and `name`. RDP entries may "
                "include `connection_security`. Omit this parameter to leave "
                "the published apps unchanged."
            )
        ),
    ] = None,
    description: Annotated[Optional[str], Field(description="Description of the PRA segment.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the segment is enabled.")] = None,
    server_group_ids: Annotated[
        Optional[List[str]], Field(description="List of server group IDs.")
    ] = None,
    tcp_port_range: Annotated[
        Optional[List[Dict[str, str]]], Field(description="TCP port ranges in structured form.")
    ] = None,
    udp_port_range: Annotated[
        Optional[List[Dict[str, str]]], Field(description="UDP port ranges in structured form.")
    ] = None,
    tcp_port_ranges: Annotated[
        Optional[List[str]], Field(description="Legacy TCP port ranges as a flat list.")
    ] = None,
    udp_port_ranges: Annotated[
        Optional[List[str]], Field(description="Legacy UDP port ranges as a flat list.")
    ] = None,
    bypass_type: Annotated[
        Optional[Literal["ALWAYS", "NEVER", "ON_NET"]], Field(description="Bypass type.")
    ] = None,
    health_check_type: Annotated[
        Optional[Literal["DEFAULT", "NONE"]], Field(description="Health check type.")
    ] = None,
    health_reporting: Annotated[
        Optional[Literal["NONE", "ON_ACCESS", "CONTINUOUS"]],
        Field(description="Health reporting mode."),
    ] = None,
    is_cname_enabled: Annotated[
        Optional[bool], Field(description="Whether CNAMEs are enabled.")
    ] = None,
    passive_health_enabled: Annotated[
        Optional[bool], Field(description="Whether passive health checks are enabled.")
    ] = None,
    icmp_access_type: Annotated[
        Optional[Literal["NONE", "PING", "PING_TRACEROUTING"]],
        Field(description="ICMP access type for the PRA segment."),
    ] = None,
    double_encrypt: Annotated[
        Optional[bool], Field(description="Enable double encryption.")
    ] = None,
    config_space: Annotated[
        Optional[Literal["DEFAULT", "SIEM"]], Field(description="Configuration space.")
    ] = None,
    ip_anchored: Annotated[
        Optional[bool], Field(description="Whether the segment is IP-anchored.")
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA Privileged Remote Access (PRA) application segment.

    The SDK's update path performs a PUT (full replace) under the hood and
    auto-diffs the supplied ``apps_config`` against the segment's current
    PRA apps:

    - Apps with a matching ``domain`` keep their existing ``pra_app_id``.
    - New ``apps_config`` entries become new PRA apps (``pra_app_id`` blank).
    - PRA apps whose domain is no longer present in ``apps_config`` are
      added to ``deleted_pra_apps`` and removed.

    Omit ``apps_config`` entirely to leave the published PRA apps unchanged.

    This tool is the PRA-specific counterpart of
    ``zpa_update_application_segment``; use this one only when the admin
    explicitly asks for **Privileged Remote Access** (RDP/SSH).

    ⚠️  WRITE OPERATION — Requires --enable-write-tools flag.
    """
    if not segment_id:
        raise ValueError("segment_id is required for update")

    if (tcp_port_range and tcp_port_ranges) or (udp_port_range and udp_port_ranges):
        raise ValueError(
            "Use either structured port ranges (tcp_port_range/udp_port_range) "
            "or flat string ranges (tcp_port_ranges/udp_port_ranges), not both."
        )

    if apps_config is not None:
        # On update, only enforce the domain ↔ domain_names link when the
        # caller is also re-supplying domain_names. Otherwise the SDK uses
        # the existing segment's domains, which we don't have here.
        _validate_apps_config(
            apps_config,
            domain_names,
            require_domain_in_segment=domain_names is not None,
        )

    client = get_zscaler_client(service=service)
    api = client.zpa.app_segments_pra

    body: Dict[str, Any] = {
        "name": name,
        "description": description,
        "enabled": enabled,
        "domain_names": domain_names,
        "segment_group_id": segment_group_id,
        "server_group_ids": server_group_ids,
        "bypass_type": bypass_type,
        "health_check_type": health_check_type,
        "health_reporting": health_reporting,
        "is_cname_enabled": is_cname_enabled,
        "passive_health_enabled": passive_health_enabled,
        "icmp_access_type": icmp_access_type,
        "double_encrypt": double_encrypt,
        "config_space": config_space,
        "ip_anchored": ip_anchored,
    }

    if apps_config is not None:
        body["common_apps_dto"] = {"apps_config": apps_config}

    if tcp_port_range:
        body["tcp_port_range"] = tcp_port_range
    elif tcp_port_ranges:
        body["tcp_port_ranges"] = tcp_port_ranges
    if udp_port_range:
        body["udp_port_range"] = udp_port_range
    elif udp_port_ranges:
        body["udp_port_ranges"] = udp_port_ranges

    if microtenant_id:
        body["microtenant_id"] = microtenant_id

    updated, _, err = api.update_segment_pra(segment_id, **body)
    if err:
        raise Exception(f"Failed to update PRA application segment {segment_id}: {err}")

    return updated.as_dict()


def zpa_delete_application_segment_pra(
    segment_id: Annotated[str, Field(description="ID of the PRA segment to delete.")],
    force_delete: Annotated[
        bool,
        Field(
            description=(
                "If True, also detaches the PRA segment from its segment group "
                "as part of deletion. Use only when the admin has confirmed "
                "this side effect."
            )
        ),
    ] = False,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}",
) -> str:
    """Delete a ZPA Privileged Remote Access (PRA) application segment.

    🚨 DESTRUCTIVE OPERATION — Requires double confirmation.
    This action cannot be undone.

    This tool is the PRA-specific counterpart of
    ``zpa_delete_application_segment``; use this one only when the admin
    explicitly asks to delete a **Privileged Remote Access** (RDP/SSH)
    segment. Deleting the segment does NOT delete the related
    ``pra_credential`` or ``pra_portal`` resources — those have their own
    lifecycle.
    """
    from zscaler_mcp.common.elicitation import (
        check_confirmation,
        extract_confirmed_from_kwargs,
    )

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zpa_delete_application_segment_pra",
        confirmed,
        {"segment_id": segment_id, "force_delete": str(force_delete)},
    )
    if confirmation_check:
        return confirmation_check

    if not segment_id:
        raise ValueError("segment_id is required for delete")

    client = get_zscaler_client(service=service)
    api = client.zpa.app_segments_pra

    _, _, err = api.delete_segment_pra(
        segment_id,
        force_delete=force_delete,
        microtenant_id=microtenant_id,
    )
    if err:
        raise Exception(f"Failed to delete PRA application segment {segment_id}: {err}")

    return f"Successfully deleted PRA application segment {segment_id}"
