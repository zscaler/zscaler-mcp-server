"""ZCell Anomaly Policy — agent-first v2 read tools.

Read-only surface over the Zscaler Cellular anomaly-policy family (SDK
``client.zcell.anomaly_policy``):

    * zcell_list_anomaly_policies         — one curated row per anomaly policy
    * zcell_list_anomaly_policy_logs       — enable/disable/run log for a policy
    * zcell_list_anomaly_policy_violations — ICCIDs that violated a policy
    * zcell_list_iccid_violations          — violation events for one ICCID

The anomaly-policy and violation endpoints require an epoch-seconds time window;
the shared :class:`WindowInput` ``days`` shorthand fills it server-side.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zcell._common import WindowInput, as_dicts

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListAnomalyPoliciesInput(WindowInput):
    """Inputs for listing anomaly policies (time-bounded)."""

    policy_type: Annotated[
        Optional[str],
        Field(default=None, description="Filter by policy type (e.g. GEOFENCING)."),
    ] = None
    page: Annotated[
        Optional[int], Field(default=None, ge=0, description="Page number (0-based).")
    ] = None
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


class AnomalyPolicyLogsInput(BaseModel):
    """Inputs for listing an anomaly policy's activity logs."""

    policy_id: Annotated[str, Field(description="Anomaly policy ID (string, even if numeric).")]
    page: Annotated[
        Optional[int], Field(default=None, ge=0, description="Page number (0-based).")
    ] = None
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


class AnomalyPolicyViolationsInput(WindowInput):
    """Inputs for listing the ICCIDs that violated an anomaly policy."""

    policy_id: Annotated[str, Field(description="Anomaly policy ID (string, even if numeric).")]
    page: Annotated[
        Optional[int], Field(default=None, ge=0, description="Page number (0-based).")
    ] = None
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


class IccidViolationsInput(WindowInput):
    """Inputs for listing the violation events for one ICCID under a policy."""

    policy_id: Annotated[str, Field(description="Anomaly policy ID (string, even if numeric).")]
    iccid: Annotated[str, Field(description="The ICCID to fetch violation events for.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class AnomalyPolicySummary(AgentView):
    """Lean view — what an agent needs to LIST and REFERENCE an anomaly policy."""

    id: Optional[str] = Field(
        default=None, description="Policy ID. Use with the *_logs / *_violations tools."
    )
    policy_name: Optional[str] = Field(default=None, description="Policy display name.")
    policy_type: Optional[str] = Field(default=None, description="Policy type (e.g. GEOFENCING).")
    enabled: Optional[bool] = Field(
        default=None, description="Whether the policy is enabled (decision-bearing)."
    )
    running_status: Optional[str] = Field(default=None, description="Runtime status of the policy.")
    created_at: Optional[Any] = Field(default=None, description="Creation timestamp.")
    enabled_at: Optional[Any] = Field(default=None, description="When the policy was last enabled.")
    sim_location_group_ids: list[Any] = Field(
        default_factory=list,
        description="SIM location group IDs the policy applies to (relational).",
    )
    violations: Optional[Any] = Field(
        default=None, description="Violation count/summary for the policy."
    )


class AnomalyPolicyLogEntry(AgentView):
    """One anomaly-policy activity log line."""

    policy_id: Optional[str] = Field(default=None, description="Policy ID the log belongs to.")
    status: Optional[str] = Field(default=None, description="Status recorded for this entry.")
    message: Optional[str] = Field(default=None, description="Human-readable log message.")
    recorded_at: Optional[Any] = Field(default=None, description="When the entry was recorded.")


class IccidViolationDetail(AgentView):
    """One violation event attributed to a specific ICCID."""

    policy_id: Optional[str] = Field(default=None, description="Policy ID the violation is under.")
    iccid: Optional[str] = Field(default=None, description="ICCID that violated the policy.")
    imsi: Optional[str] = Field(default=None, description="IMSI of the SIM.")
    event_type: Optional[str] = Field(default=None, description="Violation event type.")
    policy_type: Optional[str] = Field(
        default=None, description="Policy type at time of violation."
    )
    zone_id: Optional[Any] = Field(default=None, description="Geo-fence zone ID involved, if any.")
    timestamp: Optional[Any] = Field(default=None, description="When the violation occurred.")


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_policy(raw: dict[str, Any]) -> AnomalyPolicySummary:
    return AnomalyPolicySummary(
        id=_opt_str(pick(raw, "id")),
        policy_name=pick(raw, "policy_name", "policyName"),
        policy_type=pick(raw, "policy_type", "policyType"),
        enabled=pick(raw, "enabled"),
        running_status=pick(raw, "running_status", "runningStatus"),
        created_at=pick(raw, "created_at", "createdAt"),
        enabled_at=pick(raw, "enabled_at", "enabledAt"),
        sim_location_group_ids=pick(
            raw, "sim_location_group_ids", "simLocationGroupIds", default=[]
        )
        or [],
        violations=pick(raw, "violations"),
    )


def _shape_log(raw: dict[str, Any]) -> AnomalyPolicyLogEntry:
    return AnomalyPolicyLogEntry(
        policy_id=_opt_str(pick(raw, "policy_id", "policyId")),
        status=pick(raw, "status"),
        message=pick(raw, "message"),
        recorded_at=pick(raw, "recorded_at", "recordedAt"),
    )


def _shape_iccid_violation(raw: dict[str, Any]) -> IccidViolationDetail:
    return IccidViolationDetail(
        policy_id=_opt_str(pick(raw, "policy_id", "policyId")),
        iccid=pick(raw, "iccid"),
        imsi=pick(raw, "imsi"),
        event_type=pick(raw, "event_type", "eventType"),
        policy_type=pick(raw, "policy_type", "policyType"),
        zone_id=pick(raw, "zone_id", "zoneId"),
        timestamp=pick(raw, "timestamp"),
    )


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _query(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in pairs if value is not None}


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_anomaly_policy",
    input_model=ListAnomalyPoliciesInput,
    output_view=AnomalyPolicySummary,
    is_list=True,
)
def zcell_list_anomaly_policies(args: ListAnomalyPoliciesInput) -> list[dict[str, Any]]:
    """List Zscaler Cellular anomaly policies as curated, agent-facing views.

    Read-only. Returns one row per policy (id, name, type, enabled state, run
    status, applied SIM location groups, violation count) over a `days`
    lookback window. Use the returned `id` with the anomaly-policy logs and
    violations tools.
    """
    client = get_zscaler_client(service="zcell")

    policies, _, err = client.zcell.anomaly_policy.list_anomaly_policy(
        days=args.days,
        query_params=_query(
            ("policy_type", args.policy_type), ("page", args.page), ("size", args.size)
        ),
    )
    if err:
        raise RuntimeError(f"Failed to list anomaly policies: {err}")
    return shape_many(as_dicts(policies), _shape_policy)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_anomaly_policy",
    input_model=AnomalyPolicyLogsInput,
    output_view=AnomalyPolicyLogEntry,
    is_list=True,
)
def zcell_list_anomaly_policy_logs(args: AnomalyPolicyLogsInput) -> list[dict[str, Any]]:
    """List the activity log for one Zscaler Cellular anomaly policy.

    Read-only. Returns the enable/disable/run history (status + message +
    timestamp) for the given `policy_id`.
    """
    if not args.policy_id:
        raise ValueError("policy_id is required")

    client = get_zscaler_client(service="zcell")

    logs, _, err = client.zcell.anomaly_policy.list_anomaly_policy_logs(
        policy_id=args.policy_id, query_params=_query(("page", args.page), ("size", args.size))
    )
    if err:
        raise RuntimeError(f"Failed to list anomaly policy logs for {args.policy_id}: {err}")
    return shape_many(as_dicts(logs), _shape_log)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_anomaly_policy",
    input_model=AnomalyPolicyViolationsInput,
    output_view=AnomalyPolicySummary,
    is_list=True,
)
def zcell_list_anomaly_policy_violations(
    args: AnomalyPolicyViolationsInput,
) -> list[dict[str, Any]]:
    """List the ICCIDs that violated a Zscaler Cellular anomaly policy.

    Read-only. Returns the policy rows carrying violation data over a `days`
    lookback window. Use `zcell_list_iccid_violations` to drill into the
    per-event detail for a specific ICCID.
    """
    if not args.policy_id:
        raise ValueError("policy_id is required")

    client = get_zscaler_client(service="zcell")

    violations, _, err = client.zcell.anomaly_policy.list_anomaly_policy_violations(
        policy_id=args.policy_id,
        days=args.days,
        query_params=_query(("page", args.page), ("size", args.size)),
    )
    if err:
        raise RuntimeError(f"Failed to list anomaly policy violations for {args.policy_id}: {err}")
    return shape_many(as_dicts(violations), _shape_policy)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_anomaly_policy",
    input_model=IccidViolationsInput,
    output_view=IccidViolationDetail,
    is_list=True,
)
def zcell_list_iccid_violations(args: IccidViolationsInput) -> list[dict[str, Any]]:
    """List the anomaly-policy violation events for one ICCID.

    Read-only. Returns the individual violation events (event type, zone,
    timestamp) attributed to `iccid` under `policy_id`, over a `days` lookback
    window.
    """
    if not args.policy_id:
        raise ValueError("policy_id is required")
    if not args.iccid:
        raise ValueError("iccid is required")

    client = get_zscaler_client(service="zcell")

    events, _, err = client.zcell.anomaly_policy.get_anomaly_policy_violations(
        policy_id=args.policy_id, iccid=args.iccid, days=args.days
    )
    if err:
        raise RuntimeError(f"Failed to list violations for ICCID {args.iccid}: {err}")
    return shape_many(as_dicts(events), _shape_iccid_violation)
