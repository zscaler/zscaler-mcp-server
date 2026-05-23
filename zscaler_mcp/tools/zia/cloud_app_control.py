"""ZIA Cloud App Control MCP Tools.

Cloud App Control (CAC) lets ZIA enforce *granular* controls over cloud
applications — not just allow/block, but action-level decisions like
``BLOCK_FILE_UPLOAD``, ``ALLOW_AI_ML_WEB_USE``, or
``DENY_WEBMAIL_SEND``. Every CAC rule is scoped to a single
**rule type** (a.k.a. category / ``app_class``), and the granular
action vocabulary is *surfaced* at the **category** level — the
discovery endpoint accepts a representative app from a category and
returns the category-wide action list.

**However, the create endpoint validates each ``(rule_type,
application, action)`` tuple individually.** Two apps in the same
category can each accept a slightly different subset of the
category's action enums. Combining multiple apps into a single
rule's ``cloud_applications`` list with a shared ``actions`` list
frequently fails with::

    {"code": "INVALID_INPUT_ARGUMENT",
     "message": "Invalid action provided for selected applications"}

The error is total — the entire create is rejected, not just the
incompatible app. There is no read-only call that enumerates per-app
action validity, so the only safe pattern when the admin's request
targets multiple apps is to **create one rule per cloud
application** (one ``zia_create_cloud_app_control_rule`` call per
canonical enum), each with the minimal action subset the admin
actually asked for. See
``skills/zia/create-cloud-app-control-rule/SKILL.md`` →
"Multi-app handling".

Tools in this module:
    - :func:`zia_list_cloud_app_control_actions` — discover the
      granular action vocabulary available for a cloud application's
      category (read-only, used as a pre-step for rule authoring).
    - :func:`zia_list_cloud_app_control_rules` — list existing CAC
      rules for a given rule type (read-only).
    - :func:`zia_get_cloud_app_control_rule` — fetch one CAC rule by
      ``rule_type`` and ``rule_id`` (read-only).
    - :func:`zia_create_cloud_app_control_rule` — author a new CAC
      rule (write).
    - :func:`zia_update_cloud_app_control_rule` — modify a CAC rule
      (write); silent backfill of ``name`` from the existing rule
      because the underlying ZIA endpoint is a PUT.
    - :func:`zia_delete_cloud_app_control_rule` — destructive,
      requires HMAC confirmation token (write).

Authoring workflow ("create a rule that blocks uploads on Dropbox"):
    1. ``zia_list_cloud_app_policy(search="Dropbox",
       query="[*].{app: app, name: appName, parent: parent}")`` ->
       returns the canonical enum (``DROPBOX``) and its parent
       category (``FILE_SHARE``). Always use the ``app`` field
       (canonical enum), never ``appName`` (display name).
    2. ``zia_list_cloud_app_control_actions(cloud_app="DROPBOX")`` ->
       returns ``category="FILE_SHARE"`` and the category's action
       vocabulary. Per-app action validity is not enumerated here —
       the create call is the only authoritative validator (see
       below).
    3. ``zia_list_cloud_app_control_rules(rule_type="FILE_SHARE",
       query="[?enabled].{id, name, order, actions,
       cloud_applications}")`` -> pull the existing policy table
       once and run the four safety checks below.
    4. ``zia_create_cloud_app_control_rule(rule_type="FILE_SHARE",
       name="Block Dropbox upload", cloud_applications=["DROPBOX"],
       actions=["BLOCK_FILE_SHARE_UPLOAD"], order=<from step 3>,
       ...)`` -> creates the rule.

Authoring workflow when the admin names multiple apps ("block file
uploads on Dropbox, Google Drive, and OneDrive for Finance"):
    Loop steps 1, 2, and 4 once per app — one
    ``zia_create_cloud_app_control_rule`` invocation per app, each
    with ``cloud_applications=[<single canonical enum>]``. Step 3
    runs once for the whole batch (the safety checks reuse the same
    policy-table snapshot). Activation runs once at the end.

Rule order and policy evaluation:
    The CAC policy table for each ``rule_type`` is evaluated
    top-to-bottom, **first-match-wins**. ``order`` is 1-based —
    ``order=1`` is the top, evaluated first. A more general rule
    placed above a more specific rule will **shadow** the
    specific one (the specific rule never fires). The tool
    defaults ``order=1`` when omitted, but agents must pass
    ``order`` explicitly whenever the tenant already has CAC
    rules of the same ``rule_type`` — never rely on the default.

Safety checks before every create (and any update that changes
``actions``, ``cloud_applications``, or ``order``):
    Adding a rule without reviewing the existing table is the
    most common source of silently-shadowed rules and accidental
    duplicates. The agent is expected to run these four checks
    against the result of a single
    ``zia_list_cloud_app_control_rules(rule_type=...)`` call
    before invoking ``create`` / ``update``:

    a. **Specificity.** The rule must target a specific cloud
       application (or a small same-category set) AND at least
       one other scoping dimension (users / groups / departments
       / locations / devices / time window / device trust /
       user-agent type), unless the admin explicitly asked for
       a tenant-wide policy.
    b. **Shadowing.** No existing enabled rule above the
       proposed ``order`` position may match the same traffic
       the new rule is meant to govern — otherwise the new rule
       never fires.
    c. **Duplicate purpose.** If an existing enabled rule
       already performs the requested action against the same
       apps and scoping, ``update`` that rule instead of
       creating a parallel one.
    d. **Deny supersedes Allow.** A ``BLOCK_*`` / ``DENY_*``
       rule must sit above every overlapping ``ALLOW_*`` rule
       that could match the same traffic. Compute the lowest
       matching Allow ``order`` and place the new Deny strictly
       below it (i.e. a smaller ``order`` value — 1-based, so
       smaller = closer to the top). The Deny itself must also
       be specific per check (a).

    If any check fails, surface it to the admin and confirm
    intent before proceeding. See
    ``skills/zia/create-cloud-app-control-rule/SKILL.md`` Step 6
    for the full walk-through.

The CAC API is unusual within the ZIA rule families:
    - The endpoint *requires* ``rule_type`` (the category) on every
      list/get/create/update/delete call. Unlike most ZIA rule
      tools, you can't fetch by ``rule_id`` alone.
    - The SDK exposes the apps under the kwarg ``applications`` (not
      ``cloud_applications`` like other rule families). The MCP tool
      surfaces it as ``cloud_applications`` for consistency and maps
      to the SDK kwarg internally — friendly names go through the
      same auto-resolver.

Related tools:
    - ``zia_list_cloud_app_policy`` — policy-engine catalog (look up
      canonical app names and their parent categories).
    - ``zia_list_shadow_it_apps`` — analytics catalog (numeric IDs,
      different surface — do not confuse with the policy catalog).
"""

from typing import Annotated, Any, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.common.zia_helpers import (
    APP_CLASS_FIELD_DESCRIPTION,
    ORDER_FIELD_DESCRIPTION,
    RANK_FIELD_DESCRIPTION,
    apply_default_order,
    apply_default_rank,
    canonical_app_class_for_parent,
    list_apps_in_category,
    lookup_cloud_app_entry,
    resolve_cloud_applications,
    validate_app_class,
    validate_order,
    validate_rank,
)
from zscaler_mcp.utils.utils import parse_list

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

# Bound the "representative app" walk so we don't pound the API when a
# whole category genuinely has no granular actions defined.
_MAX_CATEGORY_PROBE_APPS = 8

# Hard ZIA limit on the Cloud App Control rule ``name`` field. Enforced
# client-side so callers get a clear validation error instead of the
# generic ``INVALID_INPUT_ARGUMENT`` round-trip the API otherwise
# returns.
_CAC_NAME_MAX_LENGTH = 31


def _validate_cac_rule_name(name: Optional[str]) -> None:
    """Reject Cloud App Control rule names that exceed ZIA's 31-char hard limit.

    ZIA rejects longer names with::

        {"code": "INVALID_INPUT_ARGUMENT",
         "message": "Name exceeds the max length 31 characters"}

    Catching it client-side saves a round trip and gives the caller a
    field-specific error message instead of the API's generic one.
    ``None`` is accepted so update calls that intentionally omit
    ``name`` (relying on silent backfill) pass through unchanged.
    """
    if name is None:
        return
    if len(name) > _CAC_NAME_MAX_LENGTH:
        raise ValueError(
            f"Cloud App Control rule name must be {_CAC_NAME_MAX_LENGTH} "
            f"characters or fewer (got {len(name)}: {name!r}). ZIA "
            f"rejects longer names with INVALID_INPUT_ARGUMENT: "
            f"'Name exceeds the max length 31 characters'. Abbreviate "
            f"the verb (e.g. 'Block' -> 'Blk', 'Allow' -> 'Allw', "
            f"'Isolate' -> 'Iso') before truncating the app name."
        )


def _probe_actions(
    cloudappcontrol,
    *,
    rule_type: str,
    candidates: list[str],
) -> tuple[list[str], Optional[str]]:
    """Try ``list_available_actions(rule_type, [app])`` until one yields actions.

    Returns ``(actions, surfacing_app)`` where ``surfacing_app`` is the
    canonical enum that finally produced a non-empty action set, or
    ``None`` if every probe came back empty.
    """
    for app in candidates:
        actions, _, err = cloudappcontrol.list_available_actions(
            rule_type=rule_type, cloud_apps=[app]
        )
        if err:
            continue
        if actions:
            return list(actions), app
    return [], None


def zia_list_cloud_app_control_actions(
    cloud_app: Annotated[
        str,
        Field(
            description=(
                "The cloud application the user is asking about. Accepts "
                "the canonical ZIA enum (``AZURE_DEVOPS``, ``DROPBOX``, "
                "``CHATGPT_AI``) **or** a friendly display name "
                "(``'Azure DevOps'``, ``'dropbox'``, ``'chatgpt'``). "
                "The tool resolves the input to its canonical form, "
                "looks up the app's category (= rule type), and returns "
                "the granular action vocabulary the API supports for "
                "Cloud App Control rules in that category. The action "
                "vocabulary is *surfaced* at the category level — "
                "every app in a category resolves to the same "
                "returned list — but the create endpoint validates "
                "per (rule_type, application, action) tuple and can "
                "still reject a category-level action when paired "
                "with a specific app. Treat the returned list as a "
                "superset; the create call is the only authoritative "
                "validator."
            )
        ),
    ],
    rule_type: Annotated[
        Optional[str],
        Field(
            description=(
                "Optional override for the rule-type category. By default "
                "the tool infers the rule type from ``cloud_app``'s "
                "``parent`` field in the policy catalog. Only set this "
                "when you want to force a specific category (e.g. when "
                "ZIA classifies an app under one category but you want "
                "actions for a different one). Must be one of the canonical "
                "category enums (``AI_ML``, ``WEBMAIL``, ``FILE_SHARE``, "
                "``SYSTEM_AND_DEVELOPMENT``, ``STREAMING_MEDIA``, "
                "``SOCIAL_NETWORKING``, ``INSTANT_MESSAGING``, "
                "``BUSINESS_PRODUCTIVITY``, ``ENTERPRISE_COLLABORATION``, "
                "``SALES_AND_MARKETING``, ``CONSUMER``, ``HOSTING_PROVIDER``, "
                "``IT_SERVICES``, ``HUMAN_RESOURCES``, ``LEGAL``, "
                "``HEALTH_CARE``, ``FINANCE``, ``DNS_OVER_HTTPS``, "
                "``CUSTOM_CAPP``)."
            )
        ),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "Optional JMESPath expression applied to the response. "
                "Useful for projecting just the actions list "
                "(``actions``) or filtering them "
                "(``actions[?contains(@, 'BLOCK')]``)."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """List granular Cloud App Control actions for an application.

    Cloud App Control rules in ZIA enforce action-level decisions on
    cloud applications. The **action vocabulary is surfaced at the
    category level** — every app in ``SYSTEM_AND_DEVELOPMENT``
    resolves to the same returned list
    (``ALLOW_SYSTEM_DEVELOPMENT_CREATE``,
    ``BLOCK_SYSTEM_DEVELOPMENT_SHARE``, ``DEV_CONDITIONAL_ACCESS``,
    ...), every app in ``AI_ML`` resolves to its own
    (``ALLOW_AI_ML_WEB_USE``, ``DENY_AI_ML_CHAT``, ...), and so on.

    **Important caveat — per-app validity is not enumerated here.**
    The returned ``actions`` list is the category's full vocabulary,
    NOT a per-app validity list. The ZIA *create* endpoint validates
    each ``(rule_type, application, action)`` tuple individually and
    can reject a category-level action when paired with a specific
    app in that category (the error code is
    ``INVALID_INPUT_ARGUMENT`` with the message ``"Invalid action
    provided for selected applications"``). There is no read-only
    call that enumerates which actions are individually valid for a
    given app — the create call is the only authoritative
    validator. When the admin's request names multiple apps, call
    ``zia_create_cloud_app_control_rule`` once per app rather than
    combining apps in a single rule's ``cloud_applications``; see
    the module docstring and
    ``skills/zia/create-cloud-app-control-rule/SKILL.md`` →
    "Multi-app handling".

    The ZIA API quirk this tool hides: the
    ``list_available_actions(rule_type, cloud_apps)`` endpoint only
    surfaces the action list when the supplied ``cloud_apps`` contains
    a "representative" app for the category — and not every app in
    the category qualifies. Calling with ``rule_type=SYSTEM_AND_DEVELOPMENT,
    cloud_apps=[AZURE_DEVOPS]`` returns ``[]`` even though the
    category has 11 actions; calling the same endpoint with
    ``cloud_apps=[GITHUB]`` returns the full set.

    To paper over that, this tool:

    1. Resolves ``cloud_app`` to its canonical enum (the ``app``
       field in the policy catalog, e.g. ``GDRIVE`` for "Google
       Drive"). Friendly display names are resolved automatically.
    2. Looks up the app's ``parent`` field — this is the rule type to
       use (unless the caller overrides via ``rule_type``).
    3. Probes ``list_available_actions`` with the user's app first,
       then walks through other apps in the same category until one
       returns a non-empty action set (capped at
       :data:`_MAX_CATEGORY_PROBE_APPS` candidates).
    4. Returns the actions and metadata about how they were sourced.

    Args:
        cloud_app: The cloud application the user is asking about.
            Friendly names and canonical enums both work.
        rule_type: Optional override for the category. Defaults to the
            app's ``parent`` field.
        query: Optional JMESPath expression applied to the response
            dict. Useful when the caller only wants the action list:
            pass ``"actions"`` to project it.
        service: SDK service identifier (default ``"zia"``).

    Returns:
        Dict with the following keys:

        - ``cloud_app`` — the input as the caller supplied it.
        - ``resolved_app`` — the canonical ZIA enum it resolved to.
        - ``category`` — the rule type / parent category enum.
        - ``category_name`` — friendly display name of the category
          (when known).
        - ``actions`` — list of canonical action enum strings the API
          accepts on a Cloud App Control rule for this category.
        - ``actions_surfaced_via`` — the canonical app enum the API
          actually returned actions for (may differ from
          ``resolved_app`` if the user's app wasn't a representative
          for its category).
        - ``probe_attempts`` — when the user's app didn't surface the
          action list directly, the list of other apps the tool tried
          before finding a representative.

    Raises:
        ValueError: when ``cloud_app`` cannot be resolved, when it
            resolves to multiple apps, or when ``rule_type`` is
            non-empty but not a recognized category.
        Exception: when the underlying SDK call returns an error.

    Examples:
        >>> # The original failing case — should now return the full
        >>> # SYSTEM_AND_DEVELOPMENT action set even though
        >>> # AZURE_DEVOPS itself doesn't surface them.
        >>> zia_list_cloud_app_control_actions(cloud_app="AZURE_DEVOPS")
        {
            "cloud_app": "AZURE_DEVOPS",
            "resolved_app": "AZURE_DEVOPS",
            "category": "SYSTEM_AND_DEVELOPMENT",
            "category_name": "System & Development",
            "actions": [
                "ALLOW_SYSTEM_DEVELOPMENT_COMMENT",
                "ALLOW_SYSTEM_DEVELOPMENT_CREATE",
                ...,
                "DEV_CONDITIONAL_ACCESS",
            ],
            "actions_surfaced_via": "GITHUB",
            "probe_attempts": ["AZURE_DEVOPS"],
        }

        >>> # Friendly name; only the action list is needed
        >>> zia_list_cloud_app_control_actions(
        ...     cloud_app="dropbox", query="actions"
        ... )
        ['ALLOW_FILE_SHARE_VIEW', 'ALLOW_FILE_SHARE_UPLOAD', ...]
    """
    if not cloud_app or not cloud_app.strip():
        raise ValueError(
            "cloud_app is required — provide a single canonical ZIA "
            "enum (e.g. 'AZURE_DEVOPS') or a friendly display name "
            "('Azure DevOps')."
        )

    resolved_apps, _ = resolve_cloud_applications(
        [cloud_app],
        scope="policy",
        service=service,
        strict=True,
    )
    if not resolved_apps:
        raise ValueError(
            f"Could not resolve cloud_app={cloud_app!r} to a canonical "
            f"ZIA cloud-application enum. Try "
            f"zia_list_cloud_app_policy(search={cloud_app!r}) first."
        )
    if len(resolved_apps) > 1:
        raise ValueError(
            f"cloud_app={cloud_app!r} is ambiguous — matches multiple "
            f"canonical enums: {', '.join(resolved_apps)}. "
            "Re-call with the exact canonical enum you want."
        )
    resolved_app = resolved_apps[0]

    entry = lookup_cloud_app_entry(resolved_app, scope="policy", service=service)
    if not entry:
        raise ValueError(
            f"Resolved cloud_app={resolved_app!r} but its catalog entry "
            "could not be found in the ZIA policy-engine catalog. This "
            "is unexpected — try clearing the catalog cache."
        )

    if rule_type and rule_type.strip():
        category = validate_app_class(rule_type, service=service)
        category_name = ""
    else:
        # Translate catalog-vocabulary parent ('STREAMING', 'WEB_MAIL')
        # to the canonical app_class enum the policy endpoints accept
        # ('STREAMING_MEDIA', 'WEBMAIL'). Most categories map to
        # themselves; only a small known set differ.
        category = canonical_app_class_for_parent(entry.get("parent"))
        category_name = entry.get("parent_name") or ""

    if not category:
        raise ValueError(
            f"Could not determine a rule-type category for "
            f"cloud_app={resolved_app!r}. The catalog entry has no "
            f"'parent' field; pass rule_type explicitly."
        )

    client = get_zscaler_client(service=service)
    cloudappcontrol = client.zia.cloudappcontrol

    actions, _, err = cloudappcontrol.list_available_actions(
        rule_type=category, cloud_apps=[resolved_app]
    )
    # Don't raise on the first call — some apps in a category aren't
    # accepted as the "representative" even though the category is
    # valid. We treat any first-call error/empty as a signal to try
    # other apps in the same category.
    if err:
        actions = []

    surfaced_via = resolved_app if actions else None
    probe_attempts: list[str] = [resolved_app]
    first_call_error = err

    if not actions:
        category_apps = list_apps_in_category(
            category, scope="policy", service=service, limit=_MAX_CATEGORY_PROBE_APPS * 4
        )
        candidates: list[str] = []
        for e in category_apps:
            app = e.get("app") or ""
            if app and app != resolved_app and app not in candidates:
                candidates.append(app)
            if len(candidates) >= _MAX_CATEGORY_PROBE_APPS:
                break

        probed_actions, surfaced_via = _probe_actions(
            cloudappcontrol, rule_type=category, candidates=candidates
        )
        actions = probed_actions
        if surfaced_via and surfaced_via in candidates:
            probe_attempts.extend(candidates[: candidates.index(surfaced_via) + 1])
        else:
            probe_attempts.extend(candidates)

    # If we still have nothing AND the first call errored, surface
    # the original error so the caller can debug rather than getting
    # a silent empty.
    if not actions and first_call_error and surfaced_via is None:
        raise Exception(
            f"Cloud App Control list_available_actions failed for "
            f"rule_type={category!r}, cloud_app={resolved_app!r} and no "
            f"representative app in category {category!r} surfaced "
            f"actions either. Underlying error: {first_call_error}"
        )

    response = {
        "cloud_app": cloud_app,
        "resolved_app": resolved_app,
        "category": category,
        "category_name": category_name,
        "actions": actions or [],
        "actions_surfaced_via": surfaced_via,
        "probe_attempts": probe_attempts,
    }

    return apply_jmespath(response, query)


# =============================================================================
# CLOUD APP CONTROL RULES — CRUD
# =============================================================================
#
# All five tools below are scoped by ``rule_type`` (the category enum:
# ``WEBMAIL``, ``FILE_SHARE``, ``AI_ML``, ``SYSTEM_AND_DEVELOPMENT``, ...).
# This is mandated by the SDK and the underlying ZIA endpoint — there
# is no "fetch by rule_id alone" path. To discover the right rule_type
# for a given application, call ``zia_list_cloud_app_control_actions``
# first (it returns ``category`` alongside the valid action enums).
#
# The MCP layer surfaces the apps under ``cloud_applications`` for
# consistency with every other ZIA rule family; the SDK kwarg is
# ``applications`` and the tool maps between the two. Friendly names
# go through the same auto-resolver used everywhere else.


def _resolve_cloud_apps_for_cac(
    cloud_applications: Optional[Union[List[str], str]],
    *,
    service: str,
) -> tuple[Optional[List[str]], Optional[dict]]:
    """Resolve user-supplied cloud-app names to canonical ZIA enums.

    Mirrors the helper used by ``file_type_control_rules`` and
    ``ssl_inspection``. Returns ``(resolved_enums, audit)``; the audit
    is included in the response only when at least one input was
    transformed (i.e. a friendly name was rewritten).
    """
    if cloud_applications is None:
        return None, None

    parsed = parse_list(cloud_applications)
    if not parsed:
        return parsed, None

    resolved, audit = resolve_cloud_applications(
        parsed,
        scope="policy",
        service=service,
        strict=True,
    )

    transformed = False
    for original, info in audit["resolved"].items():
        enums = info["enums"]
        if info["match"] != "canonical" or [original] != enums:
            transformed = True
            break

    return resolved, (audit if transformed else None)


def _build_cac_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    actions: Optional[Union[List[str], str]] = None,
    cloud_applications: Optional[Union[List[str], str]] = None,
    device_trust_levels: Optional[Union[List[str], str]] = None,
    user_agent_types: Optional[Union[List[str], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    departments: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    devices: Optional[Union[List[int], str]] = None,
    device_groups: Optional[Union[List[int], str]] = None,
    enforce_time_validity: Optional[bool] = None,
    validity_start_time: Optional[str] = None,
    validity_end_time: Optional[str] = None,
    validity_time_zone_id: Optional[str] = None,
    size_quota: Optional[int] = None,
    time_quota: Optional[int] = None,
) -> dict:
    """Build a CAC rule payload dict for ``add_rule`` / ``update_rule``.

    Note the SDK kwarg for the apps list is ``applications`` — we
    surface it as ``cloud_applications`` at the MCP layer for
    consistency with the other rule families.
    """
    payload: dict = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if enabled is not None:
        payload["enabled"] = enabled
    if rank is not None:
        payload["rank"] = rank
    if order is not None:
        payload["order"] = order
    if enforce_time_validity is not None:
        payload["enforce_time_validity"] = enforce_time_validity
    if validity_start_time is not None:
        payload["validity_start_time"] = validity_start_time
    if validity_end_time is not None:
        payload["validity_end_time"] = validity_end_time
    if validity_time_zone_id is not None:
        payload["validity_time_zone_id"] = validity_time_zone_id
    if size_quota is not None:
        payload["size_quota"] = size_quota
    if time_quota is not None:
        payload["time_quota"] = time_quota

    list_fields: list[tuple[str, Any, str]] = [
        ("actions", actions, "actions"),
        # MCP-layer ``cloud_applications`` -> SDK ``applications``
        ("cloud_applications", cloud_applications, "applications"),
        ("device_trust_levels", device_trust_levels, "device_trust_levels"),
        ("user_agent_types", user_agent_types, "user_agent_types"),
        ("locations", locations, "locations"),
        ("location_groups", location_groups, "location_groups"),
        ("groups", groups, "groups"),
        ("departments", departments, "departments"),
        ("users", users, "users"),
        ("time_windows", time_windows, "time_windows"),
        ("labels", labels, "labels"),
        ("devices", devices, "devices"),
        ("device_groups", device_groups, "device_groups"),
    ]
    for _mcp_name, value, sdk_name in list_fields:
        if value is not None:
            payload[sdk_name] = parse_list(value)

    return payload


# -----------------------------------------------------------------------------
# READ
# -----------------------------------------------------------------------------


def zia_list_cloud_app_control_rules(
    rule_type: Annotated[
        str,
        Field(
            description=(
                "Required. The CAC rule category to list. " + APP_CLASS_FIELD_DESCRIPTION
            )
        ),
    ],
    search: Annotated[
        Optional[str],
        Field(description="Optional server-side substring filter on rule name."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """List ZIA Cloud App Control rules for a specific rule type.

    The ZIA CAC endpoint is scoped per-category; ``rule_type`` is
    required. To list rules across multiple categories, call this
    tool once per category. Use
    ``zia_list_cloud_app_control_actions(cloud_app=...)`` first if
    the user names an app and you need to discover its category.

    Args:
        rule_type: Canonical category enum (``WEBMAIL``,
            ``STREAMING_MEDIA``, ``FILE_SHARE``, ``AI_ML``, etc.).
            Catalog-vocabulary forms (``WEB_MAIL``, ``STREAMING``)
            are accepted and translated.
        search: Optional substring filter on rule name (server-side).
        query: Optional JMESPath expression applied to the response
            list.
        service: SDK service identifier (default ``"zia"``).

    Returns:
        list[dict]: Cloud App Control rules.
    """
    canonical_rule_type = validate_app_class(rule_type, service=service)
    if not canonical_rule_type:
        raise ValueError("rule_type is required.")

    client = get_zscaler_client(service=service)
    cac = client.zia.cloudappcontrol

    query_params: dict = {}
    if search:
        query_params["search"] = search

    rules, _, err = cac.list_rules(canonical_rule_type, query_params=query_params or None)
    if err:
        raise Exception(
            f"Failed to list Cloud App Control rules for rule_type={canonical_rule_type!r}: {err}"
        )
    results = [r.as_dict() for r in (rules or [])]
    return apply_jmespath(results, query)


def zia_get_cloud_app_control_rule(
    rule_type: Annotated[
        str,
        Field(
            description=(
                "Required. The category the rule belongs to. " + APP_CLASS_FIELD_DESCRIPTION
            )
        ),
    ],
    rule_id: Annotated[
        Union[int, str],
        Field(description="The ID of the Cloud App Control rule to retrieve."),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Get a specific ZIA Cloud App Control rule by ``rule_type`` and ``rule_id``.

    Both arguments are required — ``rule_id`` alone is not
    sufficient because the ZIA CAC endpoint is category-scoped. If
    you only know the app name (e.g. "Dropbox"), call
    ``zia_list_cloud_app_control_actions(cloud_app="Dropbox")`` first
    to discover the category.
    """
    canonical_rule_type = validate_app_class(rule_type, service=service)
    if not canonical_rule_type:
        raise ValueError("rule_type is required.")

    client = get_zscaler_client(service=service)
    cac = client.zia.cloudappcontrol

    rule, _, err = cac.get_rule(canonical_rule_type, rule_id)
    if err:
        raise Exception(
            f"Failed to retrieve Cloud App Control rule "
            f"rule_type={canonical_rule_type!r}, rule_id={rule_id}: {err}"
        )
    return rule.as_dict()


# -----------------------------------------------------------------------------
# WRITE — Create / Update / Delete
# -----------------------------------------------------------------------------


def zia_create_cloud_app_control_rule(
    rule_type: Annotated[
        str,
        Field(
            description=(
                "Required. The category the new rule belongs to "
                "(e.g. ``WEBMAIL``, ``FILE_SHARE``, ``AI_ML``, "
                "``SYSTEM_AND_DEVELOPMENT``). Discover via "
                "``zia_list_cloud_app_control_actions(cloud_app=...)`` "
                "if the user named an app instead. "
                + APP_CLASS_FIELD_DESCRIPTION
            )
        ),
    ],
    name: Annotated[
        str,
        Field(
            description=(
                "Rule name. **Hard ZIA limit of 31 characters** — "
                "longer names are rejected by the API with "
                "``INVALID_INPUT_ARGUMENT: 'Name exceeds the max "
                "length 31 characters'``. This tool also rejects "
                "names > 31 characters client-side before the API "
                "call so the validation error surfaces without a "
                "round trip. In multi-app loops (one rule per "
                "cloud application), make each name unique by "
                "suffixing the app's short form — abbreviate the "
                "verb (``'Blk'``, ``'Allw'``, ``'Iso'``, ``'Dny'``) "
                "before truncating the app name, and prefer plain "
                "ASCII separators (``-``) over typographic ones "
                "(``—``) when you're at the edge of the limit. "
                "Example pattern: ``'Blk upload - OneDrive'`` (21 "
                "chars), ``'Blk upload - GDrive'`` (19 chars), "
                "``'Blk upload - Dropbox'`` (20 chars)."
            )
        ),
    ],
    actions: Annotated[
        Union[List[str], str],
        Field(
            description=(
                "Required. The granular action enums the rule enforces "
                "(e.g. ``ALLOW_WEBMAIL_VIEW``, ``BLOCK_FILE_SHARE_UPLOAD``, "
                "``ISOLATE_AI_ML_WEB_USE``). The valid values vary per "
                "rule_type — call "
                "``zia_list_cloud_app_control_actions(cloud_app=...)`` to "
                "discover them for the app you're targeting. Accepts "
                "JSON string or list."
            )
        ),
    ],
    cloud_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications the rule applies to. **Should "
                "contain exactly one canonical enum per rule** — when "
                "the admin's request names multiple apps (e.g. "
                "'Dropbox, Google Drive, and OneDrive'), call this "
                "tool once per app rather than passing a multi-app "
                "list. ZIA validates each (rule_type, application, "
                "action) tuple individually and frequently rejects "
                "multi-app rules with ``INVALID_INPUT_ARGUMENT: "
                "'Invalid action provided for selected applications'`` "
                "because per-app action validity varies. Accepts "
                "canonical ZIA enums (``DROPBOX``, ``GDRIVE``, "
                "``ONEDRIVE``, ``CHATGPT_AI``) OR friendly display "
                "names (``'Dropbox'``, ``'Google Drive'``) — friendly "
                "names are auto-resolved via the policy-engine "
                "cloud-app catalog (the ``app`` field, not "
                "``appName``). Note: the SDK kwarg is "
                "``applications``; this tool surfaces it as "
                "``cloud_applications`` for consistency with other "
                "ZIA rule tools. Accepts JSON string or list."
            )
        ),
    ] = None,
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = True,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description=ORDER_FIELD_DESCRIPTION)] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Device trust levels. Values: ``ANY``, "
                "``UNKNOWN_DEVICETRUSTLEVEL``, ``LOW_TRUST``, "
                "``MEDIUM_TRUST``, ``HIGH_TRUST``. Accepts JSON string or list."
            )
        ),
    ] = None,
    user_agent_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Browser/user-agent types to scope the rule to."),
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for locations the rule applies to."),
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for user groups the rule applies to."),
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for departments the rule applies to."),
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users the rule applies to.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for rule labels.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for ZCC-managed devices."),
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for device groups.")
    ] = None,
    enforce_time_validity: Annotated[
        Optional[bool],
        Field(description="Enforce a validity window. Required for the validity_* fields to apply."),
    ] = None,
    validity_start_time: Annotated[
        Optional[str],
        Field(description="Start of the validity window. Requires enforce_time_validity=True."),
    ] = None,
    validity_end_time: Annotated[
        Optional[str],
        Field(description="End of the validity window. Requires enforce_time_validity=True."),
    ] = None,
    validity_time_zone_id: Annotated[
        Optional[str],
        Field(description="Time zone ID for the validity window. Requires enforce_time_validity=True."),
    ] = None,
    size_quota: Annotated[
        Optional[int],
        Field(description="Size quota in KB beyond which the policy applies."),
    ] = None,
    time_quota: Annotated[
        Optional[int],
        Field(description="Time quota in minutes after which the policy applies."),
    ] = None,
    resolve_cloud_apps: Annotated[
        bool,
        Field(
            description=(
                "When True (default), friendly cloud-application names are "
                "resolved to canonical ZIA enum tokens. Set False to pass "
                "values through unchanged (advanced)."
            )
        ),
    ] = True,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Create a ZIA Cloud App Control rule.

    Write operation — requires the ``--enable-write-tools`` flag.

    Workflow expectation per app: for each canonical app the admin
    named, first call ``zia_list_cloud_app_policy(search="<app
    name>", query="[*].{app: app, name: appName, parent: parent}")``
    to resolve the friendly name to its canonical enum (the ``app``
    field — e.g. ``GDRIVE`` for "Google Drive") and discover the
    parent category. Then call ``zia_list_cloud_app_control_actions(
    cloud_app=<canonical enum>)`` to confirm the ``rule_type``
    (returned as ``category``) and the action vocabulary. Then pass
    those into this tool together with the desired ``name`` and
    ``cloud_applications``.

    **One rule per cloud application.** When the admin's request
    targets multiple apps (e.g. "block uploads on Dropbox, Google
    Drive, and OneDrive for Finance"), invoke this tool **once per
    app** — not once with ``cloud_applications=["DROPBOX", "GDRIVE",
    "ONEDRIVE"]``. The ZIA *create* endpoint validates each
    ``(rule_type, application, action)`` tuple individually and a
    category-level action that's valid for one app in a category may
    be rejected when paired with a different app in the same
    category. Combined rules frequently fail with::

        {"code": "INVALID_INPUT_ARGUMENT",
         "message": "Invalid action provided for selected applications"}

    The error rejects the entire create, not just the incompatible
    app, so the safe pattern is to split: one rule per app, each
    with ``cloud_applications=[<single canonical enum>]``, reusing
    the same scoping (users / groups / locations / schedule /
    device trust) across every iteration. Rule names must be unique
    — suffix each with the app's friendly name (e.g. "Block uploads
    — Dropbox", "Block uploads — Google Drive"). See
    ``skills/zia/create-cloud-app-control-rule/SKILL.md`` →
    "Multi-app handling" for the full pattern.

    **If the create still fails with that error**, pare the
    ``actions`` list down to the minimal subset the admin actually
    asked for and retry. If a single action still fails for an app,
    the action genuinely doesn't apply to that app — confirm with
    the admin and either substitute a different action or skip
    that app from the batch and report the omission.

    Mandatory pre-flight checks before invoking this tool:

    1. ``zia_list_cloud_app_control_rules(rule_type=<category>,
       query="[?enabled].{id, name, order, actions,
       cloud_applications}")`` — pull the existing policy table
       once and reuse the result for all four checks below across
       every iteration of the multi-app loop.
    2. Validate the new rule against the four criteria documented
       in the module docstring:

       a. **Specificity** — defined app(s) plus at least one
          other scoping dimension, unless tenant-wide is the
          admin's explicit intent.
       b. **Shadowing** — no existing enabled rule above the
          chosen ``order`` may match the same traffic.
       c. **Duplicate purpose** — if an existing enabled rule
          already does the job, prefer
          ``zia_update_cloud_app_control_rule`` against it
          instead of creating a parallel rule.
       d. **Deny supersedes Allow** — a ``BLOCK_*`` / ``DENY_*``
          rule must be placed above every overlapping
          ``ALLOW_*`` rule (smaller ``order`` value).

    3. Always pass ``order`` explicitly when the tenant already
       has CAC rules of the same ``rule_type`` — derive it from
       the checks above (especially d). Never rely on the
       ``order=1`` default in a populated table.

    If any check fails, surface it to the admin and confirm
    intent before creating. Creating a rule that gets shadowed
    by an existing rule, or duplicates an existing rule's
    purpose, is almost always a configuration error.

    Returns:
        dict: The created Cloud App Control rule. If friendly
        cloud-app names were auto-resolved,
        ``_cloud_applications_resolution`` is included for audit.
    """
    canonical_rule_type = validate_app_class(rule_type, service=service)
    if not canonical_rule_type:
        raise ValueError("rule_type is required.")
    _validate_cac_rule_name(name)

    cloud_apps_audit: Optional[dict] = None
    if resolve_cloud_apps and cloud_applications is not None:
        cloud_applications, cloud_apps_audit = _resolve_cloud_apps_for_cac(
            cloud_applications, service=service
        )

    rank = apply_default_rank(rank)
    order = apply_default_order(order)
    payload = _build_cac_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        actions=actions,
        cloud_applications=cloud_applications,
        device_trust_levels=device_trust_levels,
        user_agent_types=user_agent_types,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        departments=departments,
        users=users,
        time_windows=time_windows,
        labels=labels,
        devices=devices,
        device_groups=device_groups,
        enforce_time_validity=enforce_time_validity,
        validity_start_time=validity_start_time,
        validity_end_time=validity_end_time,
        validity_time_zone_id=validity_time_zone_id,
        size_quota=size_quota,
        time_quota=time_quota,
    )

    client = get_zscaler_client(service=service)
    cac = client.zia.cloudappcontrol

    rule, _, err = cac.add_rule(canonical_rule_type, **payload)
    if err:
        raise Exception(
            f"Failed to create Cloud App Control rule "
            f"(rule_type={canonical_rule_type!r}): {err}"
        )

    result = rule.as_dict() if hasattr(rule, "as_dict") else dict(rule)
    if cloud_apps_audit:
        result["_cloud_applications_resolution"] = cloud_apps_audit
    return result


def zia_update_cloud_app_control_rule(
    rule_type: Annotated[
        str,
        Field(
            description=(
                "Required. The category the existing rule belongs to. "
                + APP_CLASS_FIELD_DESCRIPTION
            )
        ),
    ],
    rule_id: Annotated[
        Union[int, str],
        Field(description="The ID of the Cloud App Control rule to update."),
    ],
    name: Annotated[
        Optional[str],
        Field(
            description=(
                "Rule name. **Hard ZIA limit of 31 characters** when "
                "supplied — longer names are rejected by the API "
                "with ``INVALID_INPUT_ARGUMENT: 'Name exceeds the "
                "max length 31 characters'``. This tool also "
                "rejects names > 31 characters client-side. When "
                "omitted, the existing name is silently backfilled "
                "from the rule on the server (the underlying ZIA "
                "endpoint is a PUT)."
            )
        ),
    ] = None,
    actions: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Granular action enums to enforce. The valid set varies "
                "per rule_type — discover via "
                "``zia_list_cloud_app_control_actions``. Accepts JSON "
                "string or list."
            )
        ),
    ] = None,
    cloud_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications the rule applies to. Canonical enums "
                "or friendly names; friendly names are auto-resolved. "
                "Internally maps to the SDK ``applications`` kwarg."
            )
        ),
    ] = None,
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = None,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description=ORDER_FIELD_DESCRIPTION)] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Device trust levels. Accepts JSON string or list."),
    ] = None,
    user_agent_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Browser/user-agent types to scope the rule to."),
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for user groups.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for rule labels.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for ZCC-managed devices."),
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for device groups.")
    ] = None,
    enforce_time_validity: Annotated[
        Optional[bool], Field(description="Enforce a validity window for the rule.")
    ] = None,
    validity_start_time: Annotated[
        Optional[str], Field(description="Start of the validity window.")
    ] = None,
    validity_end_time: Annotated[
        Optional[str], Field(description="End of the validity window.")
    ] = None,
    validity_time_zone_id: Annotated[
        Optional[str], Field(description="Time zone ID for the validity window.")
    ] = None,
    size_quota: Annotated[Optional[int], Field(description="Size quota in KB.")] = None,
    time_quota: Annotated[Optional[int], Field(description="Time quota in minutes.")] = None,
    resolve_cloud_apps: Annotated[
        bool,
        Field(
            description=(
                "When True (default), friendly cloud-application names are "
                "resolved to canonical enums. Set False to pass values "
                "through unchanged."
            )
        ),
    ] = True,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Update a ZIA Cloud App Control rule.

    Write operation — requires the ``--enable-write-tools`` flag.

    The ZIA CAC update endpoint is a PUT (full replacement) under the
    hood, so the request must always include ``name``. To keep
    partial updates safe, this tool silently backfills ``name`` from
    the existing rule when the caller does not supply it. Other
    fields the caller omits are not backfilled — they take whatever
    the API decides (typically: kept from prior state for ID-list
    fields, reset to defaults for primitive fields).

    Pre-flight checks when the update changes ``actions``,
    ``cloud_applications``, or ``order`` — i.e. when the rule's
    matching semantics or position in the policy table change:

    1. Re-run ``zia_list_cloud_app_control_rules(rule_type=...,
       query="[?enabled].{id, name, order, actions,
       cloud_applications}")`` and apply the same four-criteria
       review documented in the module docstring (specificity,
       shadowing, duplicate purpose, Deny-above-Allow) against
       the *post-update* shape of the rule.
    2. Particular gotchas:

       - An update that switches an ``ALLOW_*`` action to
         ``BLOCK_*`` / ``DENY_*`` may require re-ordering the
         rule above other Allow rules that now overlap.
       - An update that broadens ``cloud_applications`` may
         shadow more specific rules below — review the rules
         below the updated ``order`` position.
       - An update that **adds apps to** ``cloud_applications``
         (turning a single-app rule into a multi-app rule) may
         hit ``INVALID_INPUT_ARGUMENT: "Invalid action provided
         for selected applications"`` because per-app action
         validity varies even within a single category. The safe
         pattern is to leave the rule as-is and create new
         single-app rules for the additional apps via
         ``zia_create_cloud_app_control_rule`` — see that tool's
         docstring and the "Multi-app handling" section of
         ``skills/zia/create-cloud-app-control-rule/SKILL.md``.
       - An update that narrows scoping (removes users /
         locations / etc.) may stop shadowing other rules that
         were previously unreachable — usually intentional, but
         confirm with the admin.

    Updates that only flip ``enabled``, change ``description``,
    adjust quotas, or rename the rule do not require this
    review.

    Returns:
        dict: The updated Cloud App Control rule. If friendly
        cloud-app names were auto-resolved,
        ``_cloud_applications_resolution`` is included for audit.
    """
    canonical_rule_type = validate_app_class(rule_type, service=service)
    if not canonical_rule_type:
        raise ValueError("rule_type is required.")
    _validate_cac_rule_name(name)

    cloud_apps_audit: Optional[dict] = None
    if resolve_cloud_apps and cloud_applications is not None:
        cloud_applications, cloud_apps_audit = _resolve_cloud_apps_for_cac(
            cloud_applications, service=service
        )

    if rank is not None:
        rank = validate_rank(rank)
    if order is not None:
        order = validate_order(order)

    payload = _build_cac_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        actions=actions,
        cloud_applications=cloud_applications,
        device_trust_levels=device_trust_levels,
        user_agent_types=user_agent_types,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        departments=departments,
        users=users,
        time_windows=time_windows,
        labels=labels,
        devices=devices,
        device_groups=device_groups,
        enforce_time_validity=enforce_time_validity,
        validity_start_time=validity_start_time,
        validity_end_time=validity_end_time,
        validity_time_zone_id=validity_time_zone_id,
        size_quota=size_quota,
        time_quota=time_quota,
    )

    client = get_zscaler_client(service=service)
    cac = client.zia.cloudappcontrol

    if "name" not in payload:
        existing, _, fetch_err = cac.get_rule(canonical_rule_type, rule_id)
        if fetch_err:
            raise Exception(
                f"Failed to fetch Cloud App Control rule {rule_id} "
                f"(rule_type={canonical_rule_type!r}) for required-field "
                f"backfill: {fetch_err}"
            )
        existing_dict = existing.as_dict()
        payload.setdefault("name", existing_dict.get("name"))

    rule, _, err = cac.update_rule(canonical_rule_type, rule_id, **payload)
    if err:
        raise Exception(
            f"Failed to update Cloud App Control rule "
            f"rule_type={canonical_rule_type!r}, rule_id={rule_id}: {err}"
        )

    result = rule.as_dict() if hasattr(rule, "as_dict") else dict(rule)
    if cloud_apps_audit:
        result["_cloud_applications_resolution"] = cloud_apps_audit
    return result


def zia_delete_cloud_app_control_rule(
    rule_type: Annotated[
        str,
        Field(
            description=(
                "Required. The category the rule to delete belongs to. "
                + APP_CLASS_FIELD_DESCRIPTION
            )
        ),
    ],
    rule_id: Annotated[
        Union[int, str],
        Field(description="The ID of the Cloud App Control rule to delete."),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """Delete a ZIA Cloud App Control rule by ``rule_type`` and ``rule_id``.

    🚨 DESTRUCTIVE OPERATION — requires HMAC confirmation token.
    This action cannot be undone. Like every other CAC tool, the
    ``rule_type`` is required because the underlying ZIA endpoint is
    category-scoped.

    Returns:
        str: Success message confirming deletion.
    """
    from zscaler_mcp.common.elicitation import (
        check_confirmation,
        extract_confirmed_from_kwargs,
    )

    canonical_rule_type = validate_app_class(rule_type, service=service)
    if not canonical_rule_type:
        raise ValueError("rule_type is required.")

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zia_delete_cloud_app_control_rule",
        confirmed,
        {"rule_type": canonical_rule_type, "rule_id": str(rule_id)},
    )
    if confirmation_check:
        return confirmation_check

    client = get_zscaler_client(service=service)
    cac = client.zia.cloudappcontrol

    _, _, err = cac.delete_rule(canonical_rule_type, rule_id)
    if err:
        raise Exception(
            f"Failed to delete Cloud App Control rule "
            f"rule_type={canonical_rule_type!r}, rule_id={rule_id}: {err}"
        )
    return (
        f"Cloud App Control rule {rule_id} (rule_type={canonical_rule_type}) "
        f"deleted successfully."
    )


__all__ = [
    "zia_list_cloud_app_control_actions",
    "zia_list_cloud_app_control_rules",
    "zia_get_cloud_app_control_rule",
    "zia_create_cloud_app_control_rule",
    "zia_update_cloud_app_control_rule",
    "zia_delete_cloud_app_control_rule",
]
