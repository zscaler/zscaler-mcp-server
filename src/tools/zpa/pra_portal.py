from src.sdk.zscaler_client import get_zscaler_client
from typing import Union

def pra_portal_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    portal_id: str = None,
    name: str = None,
    description: str = None,
    enabled: bool = True,
    domain: str = None,
    certificate_id: str = None,
    user_notification: str = None,
    user_notification_enabled: bool = None,
    microtenant_id: str = None,
    query_params: dict = None,
) -> Union[dict, list[dict], str]:
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
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )
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
