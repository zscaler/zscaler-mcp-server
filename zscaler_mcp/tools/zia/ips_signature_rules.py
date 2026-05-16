"""ZIA Custom IPS Signature Rules MCP Tools.

This module wraps every CRUD operation backed by the SDK's
``zscaler.zia.ips_signature_rules.IPSSignatureRulesAPI``. The five
tools registered here let an admin inventory, fetch, author, modify,
and remove **custom** Snort/Suricata-style IPS signature rules on the
ZIA tenant — distinct from the *Cloud Firewall IPS rules* family
(``zia_*_cloud_firewall_ips_rule``) which gates IPS enforcement on
firewall-matched traffic. The two surfaces are complementary: a
signature describes *what* to detect, a Cloud Firewall IPS rule
controls *when* to enforce.

Tools registered here:

* ``zia_list_ips_signature_rules`` — paginated list of every custom
  IPS signature rule on the tenant. Supports JMESPath client-side
  filtering via the ``query`` parameter.
* ``zia_get_ips_signature_rule`` — fetch one signature rule by ID.
* ``zia_create_ips_signature_rule`` — author a new custom signature.
  ``rule_text`` is required and is **server-side validated** by the
  SDK against the dynamic-validation endpoint *before* the create
  request is issued; a syntactic / semantic / duplicate-``sid`` issue
  surfaces as a ``ValueError`` instead of a half-baked rule on the
  tenant.
* ``zia_update_ips_signature_rule`` — modify an existing signature.
  Update is a **PUT-replace** under the hood, so this tool silently
  backfills the load-bearing fields ``name`` and ``rule_text`` from
  the existing record when the caller omits them — same pattern as
  the rule-family update tools (`zia_update_cloud_firewall_ips_rule`,
  `zia_update_ssl_inspection_rule`, etc.). Server-side validation is
  *not* re-run on update because the existing-``sid`` check would
  flag every legitimate edit as a duplicate of itself; if you change
  ``rule_text``, validate it manually first via the SDK or the ZIA
  Admin Portal.
* ``zia_delete_ips_signature_rule`` — destructive; HMAC
  double-confirmation gate.

All write operations are **staged** until ``zia_activate_configuration``
is called, like every other ZIA write.

These tools live in the ``zia_cloud_firewall`` toolset alongside the
Cloud Firewall IPS policy-rule family so admins working on intrusion
prevention have both surfaces loaded together.
"""

from typing import Annotated, Any, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_ips_signature_rules(
    page: Annotated[
        Optional[int], Field(description="Page offset for pagination (1-based).")
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Number of records per page (default = ZIA tenant default)."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering / projection of "
                "the returned signature list (e.g. \"[?contains(name, 'Suricata')]\" "
                "or \"[*].{id: id, name: name, sid: rule_text}\")."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """List every custom IPS signature rule on the ZIA tenant.

    Read-only. Returns a list of dicts; each dict carries the rule's
    metadata (``id``, ``name``, ``description``) and the raw
    ``rule_text`` (Snort / Suricata-style ``alert ... (sid:N; rev:N;)``).

    Pagination is forwarded to the SDK via the ``page`` / ``page_size``
    query parameters. Supports JMESPath client-side filtering via the
    ``query`` parameter.
    """
    client = get_zscaler_client(service=service)

    query_params = {}
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size

    rules, _, err = client.zia.ips_signature_rules.list_ips_signature_rules(
        query_params=query_params or None
    )
    if err:
        raise Exception(f"Failed to list IPS signature rules: {err}")

    results = [r.as_dict() for r in (rules or [])]
    return apply_jmespath(results, query)


def zia_get_ips_signature_rule(
    rule_id: Annotated[
        Union[int, str],
        Field(description="The unique ID of the IPS signature rule to retrieve."),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Fetch a single custom IPS signature rule by ID.

    Returns a dict with ``id``, ``name``, ``description``, and the raw
    ``rule_text`` Snort / Suricata signature.
    """
    client = get_zscaler_client(service=service)

    rule, _, err = client.zia.ips_signature_rules.get_ips_signature_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve IPS signature rule {rule_id}: {err}")
    return rule.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zia_create_ips_signature_rule(
    name: Annotated[
        str,
        Field(
            description=(
                "Human-readable name for the signature rule (max 31 chars). "
                "Visible in the ZIA Admin Portal under Policy → Cloud IPS "
                "Control → Custom Signatures."
            )
        ),
    ],
    rule_text: Annotated[
        str,
        Field(
            description=(
                "The Snort / Suricata-style signature body. Must include a "
                "unique `sid:` (signature ID) and a `rev:` (revision). "
                "Example: 'alert http any any -> any any "
                "(msg:\"HTTP /admin\"; content:\"/admin\"; http_uri; nocase; "
                "sid:1000010; rev:1;)'. The SDK pre-flight-validates this "
                "against the ZIA dynamic-validation endpoint *before* "
                "submitting the create — syntactic, semantic, or duplicate-"
                "`sid` errors are returned as ValueError without creating a "
                "stub rule on the tenant."
            )
        ),
    ],
    description: Annotated[
        Optional[str],
        Field(description="Optional admin-facing description / change-log note."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Create a new custom IPS signature rule on the tenant.

    ``rule_text`` is server-side-validated by the SDK before the
    create request is issued; if validation fails the tool raises and
    no rule is created. Successful creates are **staged** until
    ``zia_activate_configuration`` is called.
    """
    payload = {"name": name, "rule_text": rule_text}
    if description is not None:
        payload["description"] = description

    client = get_zscaler_client(service=service)

    rule, _, err = client.zia.ips_signature_rules.add_ips_signature_rule(**payload)
    if err:
        raise Exception(f"Failed to create IPS signature rule: {err}")
    return rule.as_dict()


def zia_update_ips_signature_rule(
    rule_id: Annotated[
        Union[int, str],
        Field(description="The unique ID of the IPS signature rule to update."),
    ],
    name: Annotated[
        Optional[str], Field(description="Updated rule name (max 31 chars).")
    ] = None,
    rule_text: Annotated[
        Optional[str],
        Field(
            description=(
                "Updated Snort / Suricata-style signature body. Server-side "
                "validation is NOT re-run on update because the existing-`sid` "
                "check would flag every legitimate edit as a duplicate of "
                "itself; validate the new rule text manually before calling."
            )
        ),
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Updated admin-facing description.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Update an existing custom IPS signature rule.

    The IPS signature update endpoint is **PUT-replace** — any field
    omitted from the payload is reset on the API side. To make partial
    updates safe this tool silently backfills the load-bearing fields
    ``name`` and ``rule_text`` from the existing record when the caller
    does not supply them (mirrors the convention used by the ZIA
    rule-family update tools). Successful updates are **staged** until
    ``zia_activate_configuration`` is called.
    """
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if rule_text is not None:
        payload["rule_text"] = rule_text
    if description is not None:
        payload["description"] = description

    client = get_zscaler_client(service=service)

    if "name" not in payload or "rule_text" not in payload:
        existing, _, fetch_err = client.zia.ips_signature_rules.get_ips_signature_rule(rule_id)
        if fetch_err:
            raise Exception(
                f"Failed to fetch IPS signature rule {rule_id} for "
                f"required-field backfill: {fetch_err}"
            )
        existing_dict = existing.as_dict()
        payload.setdefault("name", existing_dict.get("name"))
        payload.setdefault("rule_text", existing_dict.get("rule_text"))

    rule, _, err = client.zia.ips_signature_rules.update_ips_signature_rule(
        rule_id, **payload
    )
    if err:
        raise Exception(f"Failed to update IPS signature rule {rule_id}: {err}")
    return rule.as_dict()


def zia_delete_ips_signature_rule(
    rule_id: Annotated[
        Union[int, str],
        Field(description="The unique ID of the IPS signature rule to delete."),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """Delete a custom IPS signature rule by ID.

    🚨 DESTRUCTIVE — requires HMAC double-confirmation. The change is
    **staged** until ``zia_activate_configuration`` is called.
    """
    from zscaler_mcp.common.elicitation import (
        check_confirmation,
        extract_confirmed_from_kwargs,
    )

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zia_delete_ips_signature_rule", confirmed, {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check

    client = get_zscaler_client(service=service)

    _, _, err = client.zia.ips_signature_rules.delete_ips_signature_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete IPS signature rule {rule_id}: {err}")
    return f"IPS signature rule {rule_id} deleted successfully."
