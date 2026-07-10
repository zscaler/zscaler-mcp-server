"""Shared curated views + helpers for ZPA app connectors and service edges.

App connectors and service edges are near-identical runtime resources (both
enroll via a provisioning key, both report control-channel health), so the
public ``app_connectors.py`` and ``service_edges.py`` modules share these
curated views and shaping helpers. Registers no tools itself.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from zscaler_mcp.shaping import AgentView, pick

__all__ = [
    "ConnectorSummary",
    "ConnectorDetail",
    "OperationResult",
    "shape_summary",
    "shape_detail",
    "query_params",
]


class ConnectorSummary(AgentView):
    """Lean view — identify and health-triage a connector / service edge."""

    id: str = Field(description="Resource ID. Use this in follow-up calls.")
    name: str = Field(description="Display name.")
    enabled: Optional[bool] = Field(default=None, description="Whether the resource is enabled.")
    control_channel_status: Optional[str] = Field(
        default=None, description="Control-channel state (connectivity signal)."
    )
    runtime_os: Optional[str] = Field(default=None, description="Reported OS / platform.")
    application_start_time: Optional[str] = Field(default=None, description="Last start time.")
    group_id: Optional[str] = Field(
        default=None, description="Parent group ID (connector/edge group)."
    )


class ConnectorDetail(ConnectorSummary):
    """Full view — summary plus version, location, and provenance."""

    description: Optional[str] = Field(default=None, description="Admin description.")
    platform: Optional[str] = Field(default=None, description="Platform descriptor.")
    private_ip: Optional[str] = Field(default=None, description="Reported private IP.")
    public_ip: Optional[str] = Field(default=None, description="Reported public IP.")
    location: Optional[str] = Field(default=None, description="Geographic location.")
    enrollment_cert: Optional[str] = Field(
        default=None, description="Enrollment certificate name/id."
    )
    microtenant_id: Optional[str] = Field(default=None, description="Owning microtenant, if any.")
    created_time: Optional[str] = Field(default=None, description="Creation timestamp.")
    modified_time: Optional[str] = Field(default=None, description="Last-modified timestamp.")


class OperationResult(AgentView):
    """Result of a destructive operation (delete / bulk delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(p.title() for p in rest)


def shape_summary(raw: dict[str, Any], *, group_key: str) -> ConnectorSummary:
    return ConnectorSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=pick(raw, "enabled"),
        control_channel_status=pick(raw, "control_channel_status", "controlChannelStatus"),
        runtime_os=pick(raw, "runtime_os", "runtimeOS", "operating_system", "operatingSystem"),
        application_start_time=pick(raw, "application_start_time", "applicationStartTime"),
        group_id=_opt_str(pick(raw, group_key, _camel(group_key))),
    )


def shape_detail(raw: dict[str, Any], *, group_key: str) -> ConnectorDetail:
    enrollment = pick(raw, "enrollment_cert", "enrollmentCert")
    if isinstance(enrollment, dict):
        enrollment = enrollment.get("name") or _opt_str(enrollment.get("id"))
    return ConnectorDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=pick(raw, "enabled"),
        control_channel_status=pick(raw, "control_channel_status", "controlChannelStatus"),
        runtime_os=pick(raw, "runtime_os", "runtimeOS", "operating_system", "operatingSystem"),
        application_start_time=pick(raw, "application_start_time", "applicationStartTime"),
        group_id=_opt_str(pick(raw, group_key, _camel(group_key))),
        description=pick(raw, "description"),
        platform=pick(raw, "platform"),
        private_ip=pick(raw, "private_ip", "privateIp"),
        public_ip=pick(raw, "public_ip", "publicIp"),
        location=pick(raw, "location"),
        enrollment_cert=enrollment if isinstance(enrollment, str) else None,
        microtenant_id=pick(raw, "microtenant_id", "microtenantId"),
        created_time=pick(raw, "creation_time", "creationTime"),
        modified_time=pick(raw, "modified_time", "modifiedTime"),
    )


def query_params(*, search=None, page=None, page_size=None, microtenant_id=None) -> dict[str, Any]:
    qp: dict[str, Any] = {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    if search:
        qp["search"] = search
    if page is not None:
        qp["page"] = str(page)
    if page_size is not None:
        qp["page_size"] = str(page_size)
    return qp
