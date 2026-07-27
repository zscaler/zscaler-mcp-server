"""ZMS nonces — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/nonces.py``:

    zms_list_nonces, zms_get_nonce

``list_nonces`` returns a connection ``{nodes, page_info}``; ``get_nonce`` returns
one nonce keyed by ``eyez_id``. Requires ZSCALER_CUSTOMER_ID.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, shape_many
from zscaler_mcp.tools.zms._common import nodes_of, require_customer_id

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListNoncesInput(BaseModel):
    """Inputs for listing ZMS enrollment nonces."""

    page: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    search: Annotated[Optional[str], Field(default=None, description="Search filter.")] = None
    sort: Annotated[Optional[str], Field(default=None, description="Sort field.")] = None
    sort_dir: Annotated[
        Optional[str], Field(default=None, description="Sort direction: ASC or DESC.")
    ] = None


class GetNonceInput(BaseModel):
    """Inputs for getting one ZMS nonce."""

    eyez_id: Annotated[str, Field(description="Nonce eyez_id (the canonical identifier).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class NonceDetail(AgentView):
    """Full nonce payload — kept nested (may carry sensitive enrollment data)."""

    eyez_id: Optional[str] = Field(default=None, description="Nonce eyez_id (echoed).")
    data: dict = Field(default_factory=dict, description="Full nonce payload.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListNoncesInput,
    is_list=True,
)
def zms_list_nonces(args: ListNoncesInput) -> list[dict[str, Any]]:
    """List ZMS enrollment nonces.

    Read-only. Returns one row per nonce (eyez_id, name, status, expiry).
    Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page": args.page,
        "page_size": args.page_size,
    }
    if args.search is not None:
        kwargs["search"] = args.search
    if args.sort is not None:
        kwargs["sort"] = args.sort
    if args.sort_dir is not None:
        kwargs["sort_dir"] = args.sort_dir
    result, _, err = client.zms.nonces.list_nonces(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS nonces: {err}")
    return shape_many(nodes_of(result))


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=GetNonceInput,
    output_view=NonceDetail,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zms_get_nonce(args: GetNonceInput) -> dict[str, Any]:
    """Get one ZMS nonce.

    Read-only. Keyed by `eyez_id`. The payload may carry sensitive enrollment
    data — handle accordingly. Requires ZSCALER_CUSTOMER_ID.
    """
    if not args.eyez_id:
        raise ValueError("eyez_id is required")
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    result, _, err = client.zms.nonces.get_nonce(customer_id=customer_id, eyez_id=args.eyez_id)
    if err:
        raise RuntimeError(f"Failed to get ZMS nonce {args.eyez_id}: {err}")
    return NonceDetail(
        eyez_id=args.eyez_id, data=result if isinstance(result, dict) else {}
    ).model_dump()
