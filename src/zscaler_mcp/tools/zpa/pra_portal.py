from zscaler_mcp.sdk.zscaler_client import get_zscaler_client
from zscaler_mcp import app
from typing import Annotated, Union, List
from pydantic import Field


@app.tool(
    name="zpa_pra_portals",
    description="Tool for managing ZPA Privileged Remote Access (PRA) Portals.",
)
def pra_portal_manager(
    action: Annotated[
        str,
        Field(description="Action to perform: 'create', 'read', 'update', or 'delete'.")
    ],
    portal_id: Annotated[
        str,
        Field(description="Portal ID for read, update, or delete operations.")
    ] = None,
    name: Annotated[
        str,
        Field(description="Name of the PRA portal.")
    ] = None,
    description: Annotated[
        str,
        Field(description="Description of the PRA portal.")
    ] = None,
    enabled: Annotated[
        bool,
        Field(description="Whether the portal is enabled.")
    ] = True,
    domain: Annotated[
        str,
        Field(description="Domain for the portal (required for create/update).")
    ] = None,
    certificate_id: Annotated[
        str,
        Field(description="Certificate ID (required when creating or updating a portal).")
    ] = None,
    user_notification: Annotated[
        str,
        Field(description="User notification message for the portal.")
    ] = None,
    user_notification_enabled: Annotated[
        bool,
        Field(description="Whether user notifications are enabled.")
    ] = None,
    microtenant_id: Annotated[
        str,
        Field(description="Microtenant ID for scoping operations.")
    ] = None,
    query_params: Annotated[
        dict,
        Field(description="Optional query parameters for filtering results.")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zpa",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing ZPA Privileged Remote Access (PRA) Portals.

    Supported actions:
    - create: Requires name, domain, certificate_id.
    - read: Fetch all or one portal by portal_id.
    - update: Requires portal_id and mutable fields.
    - delete: Requires portal_id.

    Args:
        action (str): One of 'create', 'read', 'update', 'delete'.
        certificate_id (str): Required when creating or updating a portal.
        domain (str): Required for creating or updating.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_portal

    if action == "create":
        if not all([name, domain]):
            raise ValueError("Both 'name' and 'domain' are required for portal creation")

        # Attempt to resolve certificate ID by name if not directly provided
        if not certificate_id:
            certs, _, err = client.zpa.certificates.list_issued_certificates(query_params={"search": name})
            if err:
                raise Exception(f"Failed to resolve certificate: {err}")
            if not certs:
                raise ValueError(f"No certificate found matching name: {name}")
            certificate_id = certs[0].id
            raise ValueError("name, domain, and certificate_id are required for portal creation")

        payload = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "domain": domain,
            "certificate_id": certificate_id,
            "user_notification": user_notification,
            "user_notification_enabled": user_notification_enabled,
        }

        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        created, _, err = api.add_portal(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if portal_id:
            result, _, err = api.get_portal(portal_id, query_params={"microtenant_id": microtenant_id})
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            qp = query_params or {}
            if microtenant_id:
                qp["microtenant_id"] = microtenant_id
            portals, _, err = api.list_portals(query_params=qp)
            if err:
                raise Exception(f"List failed: {err}")
            return [p.as_dict() for p in portals]

    elif action == "update":
        if not portal_id:
            raise ValueError("portal_id is required for update")

        update_fields = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "domain": domain,
            "certificate_id": certificate_id,
            "user_notification": user_notification,
            "user_notification_enabled": user_notification_enabled,
        }
        if microtenant_id:
            update_fields["microtenant_id"] = microtenant_id

        updated, _, err = api.update_portal(portal_id, **update_fields)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not portal_id:
            raise ValueError("portal_id is required for delete")

        _, _, err = api.delete_portal(portal_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted PRA portal {portal_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
