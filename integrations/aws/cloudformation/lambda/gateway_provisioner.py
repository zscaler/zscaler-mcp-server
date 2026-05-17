"""AgentCore Gateway CloudFormation custom-resource handler.

Provisions and manages an Amazon Bedrock AgentCore Gateway that fronts the
Zscaler MCP Server running on AgentCore Runtime. Two operating modes:

  GatewayMode = "create"
      Create a brand-new Gateway with a CUSTOM_JWT inbound authorizer and
      register the runtime as an MCP-server target on it. Full lifecycle is
      owned by CloudFormation (delete tears down both target, gateway, and
      the AgentCore Identity OAuth2 credential provider).

  GatewayMode = "attach"
      Skip gateway creation. Register the runtime as an MCP-server target on
      a customer-owned Gateway identified by ExistingGatewayId. Lifecycle is
      target-only — delete removes our target and the credential provider we
      created, but never touches the gateway itself.

Outbound auth (Gateway → AgentCore Runtime): MCP-server targets ONLY accept
`OAUTH` credential providers — AWS explicitly rejects `JWT_PASSTHROUGH` for
this target type ("MCP server target does not support JWT_PASSTHROUGH
credential provider type"). The Lambda therefore always provisions an
AgentCore Identity OAuth2 credential provider (`CustomOauth2` vendor) from
the supplied OIDC discovery URL + client_id + client_secret, and wires it
into the target with grantType=CLIENT_CREDENTIALS (the 2LO machine-to-
machine flow). Customers who already own a credential provider can pass
its ARN via OAuthProviderArn to skip the auto-provisioning step — the
Lambda will then reuse the existing provider verbatim.

API shape references:
  - create_gateway:        bedrock-agentcore-control 2023-06-05
  - create_gateway_target: requires boto3 >= 1.40.0 for mcpServer target type
  - MCP-server target docs: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html
  - Authorizer config docs: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-create-api.html

Identifier model (mirrors runtime_provisioner):
  - Gateway/Target name → human-friendly, supplied at create time only
  - Gateway/Target id   → AWS-generated, looked up by name via list_*

CFN response contract (what the custom resource exposes via !GetAtt):
  - GatewayId      always present in create mode; passes through ExistingGatewayId in attach mode
  - GatewayArn     create mode only ("" in attach mode)
  - McpUrl         the URL downstream agents (Quick, custom clients, Bedrock Agents, etc.) call
  - TargetId       always present (the mcpServer target we created)
"""

import json
import time
import urllib.parse
import urllib.request

import boto3

CONTROL = boto3.client("bedrock-agentcore-control")


# ─────────────────────────────────────────────────────────────────────────────
# CloudFormation custom-resource response sender
# ─────────────────────────────────────────────────────────────────────────────

def send(event, context, status, data, reason=""):
    """PUT a CloudFormation custom-resource response. Tolerant to large data dicts."""
    physical_id = (
        data.get("GatewayId")
        or data.get("TargetId")
        or event.get("PhysicalResourceId")
        or context.log_stream_name
    )
    body = json.dumps({
        "Status":             status,
        "Reason":             reason or f"See CloudWatch log {context.log_stream_name}",
        "PhysicalResourceId": physical_id,
        "StackId":            event["StackId"],
        "RequestId":          event["RequestId"],
        "LogicalResourceId":  event["LogicalResourceId"],
        "Data":               data,
    }).encode("utf-8")
    req = urllib.request.Request(
        event["ResponseURL"],
        data=body,
        method="PUT",
        headers={"Content-Type": "", "Content-Length": str(len(body))},
    )
    with urllib.request.urlopen(req) as resp:
        resp.read()


# ─────────────────────────────────────────────────────────────────────────────
# Resource lookup helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_gateway_by_name(name: str) -> dict | None:
    """Walk list_gateways and return the first whose name matches."""
    kwargs = {"maxResults": 100}
    while True:
        resp = CONTROL.list_gateways(**kwargs)
        for gw in resp.get("items", []):
            if gw.get("name") == name:
                return gw
        token = resp.get("nextToken")
        if not token:
            return None
        kwargs["nextToken"] = token


def find_target_by_name(gateway_id: str, name: str) -> dict | None:
    """Walk list_gateway_targets and return the first whose name matches."""
    kwargs = {"gatewayIdentifier": gateway_id, "maxResults": 100}
    while True:
        resp = CONTROL.list_gateway_targets(**kwargs)
        for t in resp.get("items", []):
            if t.get("name") == name:
                return t
        token = resp.get("nextToken")
        if not token:
            return None
        kwargs["nextToken"] = token


# AgentCore Gateway / Target terminal failure states. The API uses both bare
# "FAILED" and (rarely, on some resource types) the CREATE_/UPDATE_/DELETE_-
# prefixed variants — accept all of them so a stuck FAILED state aborts the
# Lambda immediately instead of burning the 600s timeout.
_TERMINAL_FAILURE_STATES = ("FAILED", "CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED")


def _format_status_reasons(reasons) -> str:
    if not reasons:
        return "no reasons returned by AgentCore (check CloudWatch under /aws/bedrock-agentcore/)"
    if isinstance(reasons, (list, tuple)):
        return " | ".join(str(r) for r in reasons)
    return str(reasons)


def wait_for_gateway_status(gateway_id: str, target_status: str, timeout: int = 600) -> dict:
    """Poll get_gateway until status matches or the timeout expires."""
    deadline = time.time() + timeout
    last = None
    last_gw: dict = {}
    while time.time() < deadline:
        gw = CONTROL.get_gateway(gatewayIdentifier=gateway_id)
        last_gw = gw
        status = gw.get("status", "UNKNOWN")
        if status != last:
            print(f"  gateway status={status}")
            last = status
        if status == target_status:
            return gw
        if status in _TERMINAL_FAILURE_STATES:
            reasons = _format_status_reasons(gw.get("statusReasons"))
            raise RuntimeError(
                f"Gateway entered terminal failure state '{status}'. Reasons: {reasons}"
            )
        time.sleep(10)
    # Surface whatever GetGateway last told us so the failure log isn't a
    # bare "did not reach READY" with no context.
    reasons = _format_status_reasons(last_gw.get("statusReasons"))
    raise TimeoutError(
        f"Gateway did not reach {target_status} within {timeout}s "
        f"(last status: {last_gw.get('status', 'UNKNOWN')}; reasons: {reasons})"
    )


def wait_for_target_status(gateway_id: str, target_id: str, target_status: str, timeout: int = 600) -> dict:
    """Poll get_gateway_target until status matches or the timeout expires."""
    deadline = time.time() + timeout
    last = None
    last_target: dict = {}
    while time.time() < deadline:
        t = CONTROL.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
        last_target = t
        status = t.get("status", "UNKNOWN")
        if status != last:
            print(f"  target status={status}")
            last = status
        if status == target_status:
            return t
        if status in _TERMINAL_FAILURE_STATES:
            reasons = _format_status_reasons(t.get("statusReasons"))
            raise RuntimeError(
                f"Target entered terminal failure state '{status}'. Reasons: {reasons}"
            )
        # Pending-auth states only show up with 3LO ImplicitSync. We don't
        # use ImplicitSync (we default to SchemaUpfront), so surface these
        # loudly if they ever appear instead of looping silently.
        if status in ("CREATE_PENDING_AUTH", "UPDATE_PENDING_AUTH"):
            reasons = _format_status_reasons(t.get("statusReasons"))
            raise RuntimeError(
                f"Target stuck in {status} — this requires human OAuth consent. "
                "Either complete the consent in the AgentCore console or switch "
                "to schema-upfront mode by populating GatewayToolSchemaJson. "
                f"Reasons: {reasons}"
            )
        time.sleep(10)
    reasons = _format_status_reasons(last_target.get("statusReasons"))
    raise TimeoutError(
        f"Target did not reach {target_status} within {timeout}s "
        f"(last status: {last_target.get('status', 'UNKNOWN')}; reasons: {reasons})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Config builders
# ─────────────────────────────────────────────────────────────────────────────

def _derive_discovery_url(issuer: str) -> str:
    """OIDC discovery URL = <issuer>/.well-known/openid-configuration."""
    issuer = (issuer or "").strip()
    if not issuer:
        return ""
    if issuer.endswith("/.well-known/openid-configuration"):
        return issuer
    return f"{issuer.rstrip('/')}/.well-known/openid-configuration"


def _build_oauth_discovery_block(props: dict) -> dict:
    """Build the oauthDiscovery block for create_oauth2_credential_provider.

    Two paths, IdP-agnostic:

    1. Standard path (default): pass {"discoveryUrl": ...}. AgentCore
       Identity follows the OIDC discovery doc to find token_endpoint,
       jwks_uri, etc., and POSTs client_credentials requests in the
       canonical form: `grant_type=...&client_id=...&client_secret=...
       &scope=...`. This works out of the box for Okta, Cognito, Entra
       ID v2, Google, Keycloak, ADFS, PingFederate — anything OIDC-
       compliant whose IdP can mint tokens from `scope` alone.

    2. Escape hatch path: when TokenEndpointQuery is set, fetch the
       discovery doc, locate the real token_endpoint, then append the
       supplied query string. The result is wrapped in
       {"authorizationServerMetadata": {...}} (the field AgentCore
       Identity uses to accept a manually-specified endpoint).

       Why this exists: AgentCore's customOauth2 schema has no audience
       or resource indicator field. Some IdPs need extra parameters on
       the token request that aren't `scope`:

         - Auth0 custom APIs require `audience=<api-identifier>`
         - Entra ID v1 (legacy) requires `resource=<api-uri>`
         - RFC 8707 resource indicators on some Keycloak setups
         - Future quirks from any compliant-but-opinionated IdP

       Users supply whatever query string fits their IdP. Empty by
       default — we don't auto-detect any specific vendor.
    """
    discovery_url = (
        (props.get("InboundDiscoveryUrl") or "").strip()
        or _derive_discovery_url(props.get("InboundIssuer", ""))
    )
    if not discovery_url:
        raise ValueError(
            "Cannot build OAuth discovery block without InboundDiscoveryUrl "
            "or InboundIssuer."
        )

    token_query = (props.get("TokenEndpointQuery") or "").strip().lstrip("?&")
    if not token_query:
        return {"discoveryUrl": discovery_url}

    # Escape-hatch path — fetch discovery, splice in the extra query params.
    try:
        with urllib.request.urlopen(discovery_url, timeout=10) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise ValueError(
            f"Could not fetch OIDC discovery from {discovery_url}: {exc}. "
            "Verify the URL is reachable from this Lambda and returns a "
            "valid OIDC discovery document."
        ) from exc

    issuer = (doc.get("issuer") or "").rstrip("/")
    token_endpoint = doc.get("token_endpoint", "")
    authz_endpoint = doc.get("authorization_endpoint") or token_endpoint
    if not (issuer and token_endpoint):
        raise ValueError(
            f"OIDC discovery at {discovery_url} is missing 'issuer' or "
            f"'token_endpoint'. Got: {list(doc.keys())}"
        )

    sep = "&" if "?" in token_endpoint else "?"
    token_endpoint_with_query = f"{token_endpoint}{sep}{token_query}"

    return {
        "authorizationServerMetadata": {
            "issuer":                 issuer,
            "tokenEndpoint":          token_endpoint_with_query,
            "authorizationEndpoint":  authz_endpoint,
            "responseTypes":          ["code"],
        }
    }


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def build_authorizer_configuration(props: dict) -> dict:
    """Build the inbound CUSTOM_JWT authorizer config for create_gateway.

    Empirically verified contract (see local_dev/Bedrock_Agent_Core/
    idp-compatibility-findings.md for the test evidence):

    AgentCore Gateway's `allowedClients` matcher reads the **`client_id`
    claim** from the inbound JWT. Cognito puts `client_id` directly in M2M
    tokens; every other major OIDC IdP (Auth0, Okta, Entra ID, Keycloak,
    PingOne, Google) uses the RFC-7519-standard `azp` claim and either
    cannot inject `client_id` at all (Auth0 silently filters it from
    custom-claim APIs) or names it differently (Okta uses `cid`). When
    `allowedClients` doesn't match, the Gateway returns 403
    `insufficient_scope` rather than the more obvious `invalid_client`,
    which makes the failure indistinguishable from a real scope mismatch.

    To stay IdP-agnostic, we let the caller specify which claim carries
    the client identity via `InboundClientClaimName`:

      * `client_id` → use `allowedClients` (Cognito-native path).
      * anything else → emit a `customClaims` rule that matches that
        claim name against the OAuth client ID(s) instead. This sidesteps
        the Cognito-only behavior of `allowedClients` and works for any
        OIDC provider.

    AgentCore also requires at least one of `allowedAudience`,
    `allowedClients`, `allowedScopes`, or `customClaims` to be set.
    """
    discovery_url = (
        props.get("InboundDiscoveryUrl", "").strip()
        or _derive_discovery_url(props.get("InboundIssuer", ""))
    )
    if not discovery_url:
        raise ValueError(
            "Gateway inbound authorizer requires InboundDiscoveryUrl (or "
            "InboundIssuer from which it can be derived as "
            "<issuer>/.well-known/openid-configuration)."
        )

    custom_jwt: dict = {"discoveryUrl": discovery_url}

    allowed_clients = _split_csv(props.get("OAuthClientId", ""))
    # Default to client_id only because that's the historical CFN default;
    # the deploy script auto-detects and overrides to "azp" for Auth0 et al.
    client_claim_name = (
        props.get("InboundClientClaimName", "").strip() or "client_id"
    )
    if allowed_clients:
        if client_claim_name == "client_id":
            custom_jwt["allowedClients"] = allowed_clients
        else:
            custom_jwt["customClaims"] = [
                {
                    "inboundTokenClaimName": client_claim_name,
                    "inboundTokenClaimValueType": "STRING",
                    "authorizingClaimMatchValue": {
                        "claimMatchValue": {"matchValueString": cid},
                        "claimMatchOperator": "EQUALS",
                    },
                }
                for cid in allowed_clients
            ]

    allowed_audience = _split_csv(props.get("InboundAllowedAudience", ""))
    if allowed_audience:
        custom_jwt["allowedAudience"] = allowed_audience

    allowed_scopes = _split_csv(props.get("InboundAllowedScopes", ""))
    if allowed_scopes:
        custom_jwt["allowedScopes"] = allowed_scopes

    has_client_constraint = (
        "allowedClients" in custom_jwt or "customClaims" in custom_jwt
    )
    if not has_client_constraint and "allowedAudience" not in custom_jwt:
        raise ValueError(
            "Gateway CUSTOM_JWT authorizer requires at least one of "
            "OAuthClientId (mapped to allowedClients or customClaims) or "
            "InboundAllowedAudience."
        )

    return {"customJWTAuthorizer": custom_jwt}


def build_target_configuration(props: dict, upstream_url: str) -> dict:
    """Build the mcpServer target configuration.

    listingMode is fixed to DEFAULT — supports SchemaUpfront, 3LO outbound,
    and semantic search. DYNAMIC is intentionally not exposed (AWS docs note
    it disables both semantic search and 3LO).
    """
    mcp_server: dict = {
        "endpoint": upstream_url,
        "listingMode": "DEFAULT",
    }

    schema = (props.get("ToolSchemaJson") or "").strip()
    if schema:
        # SchemaUpfront — no interactive admin consent needed at create time,
        # and the cached schema feeds Gateway's tool catalog directly.
        try:
            json.loads(schema)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ToolSchemaJson is not valid JSON: {exc}") from exc
        mcp_server["mcpToolSchema"] = {"inlinePayload": schema}

    return {"mcp": {"mcpServer": mcp_server}}


def build_credential_provider_configurations(props: dict, provider_arn: str) -> list[dict]:
    """Build the outbound credential provider list for create_gateway_target.

    MCP-server targets only accept OAUTH (AWS rejects JWT_PASSTHROUGH at the
    API level). Caller supplies the credential-provider ARN — either one we
    just created via ensure_oauth2_credential_provider() or one the customer
    pre-created and passed in via OAuthProviderArn.

    scopes are sent ONLY when OAuthProviderScopes is explicitly set. We do
    NOT default to the audience: audiences and scopes are distinct OAuth2
    concepts, and most IdPs (Auth0, Okta strict mode, Cognito with strict
    scopes) reject the request when the client wasn't granted a scope by
    that name. The right way to bind the target API is via the IdP-side
    configuration (Auth0 tenant Default Audience, Okta audience-bound
    auth server, Cognito resource server scopes, etc.) — not by lying
    to the IdP that the audience is a scope.

    Set OAuthProviderScopes only when the upstream genuinely uses scopes
    (e.g. "okta.users.read", "https://graph.microsoft.com/.default").
    """
    if not provider_arn:
        raise ValueError(
            "MCP-server targets require an OAUTH credential provider ARN. "
            "Either supply OAuthProviderArn (use an existing provider) or "
            "OAuthClientSecret (auto-provision from the inbound IdP)."
        )
    # `scopes` is required by the boto3 schema for create_gateway_target —
    # the field must be present even if no real scopes apply. We always
    # send a list; empty when OAuthProviderScopes is unset. AgentCore
    # Identity translates non-empty values into the `scope=` parameter on
    # the upstream /token request; an empty list is forwarded as no
    # `scope` parameter, which matches OAuth2 RFC 6749 behavior and lets
    # IdPs fall back to their tenant default (e.g. Auth0 Default Audience,
    # Cognito resource-server defaults, Okta authorization-server bindings).
    oauth_cfg: dict = {
        "providerArn": provider_arn,
        "scopes": _split_csv(props.get("OAuthProviderScopes", "")),
    }
    # CLIENT_CREDENTIALS (2LO) is correct for service-to-service Gateway
    # auth. AUTHORIZATION_CODE (3LO) requires interactive user consent at
    # target-creation time, which breaks CFN-driven deploys.
    oauth_cfg["grantType"] = props.get("OAuthProviderGrantType", "CLIENT_CREDENTIALS")
    return [{
        "credentialProviderType": "OAUTH",
        "credentialProvider": {"oauthCredentialProvider": oauth_cfg},
    }]


# ─────────────────────────────────────────────────────────────────────────────
# AgentCore Identity OAuth2 credential provider lifecycle
# ─────────────────────────────────────────────────────────────────────────────

def find_oauth2_credential_provider_by_name(name: str) -> dict | None:
    """Walk list_oauth2_credential_providers and return the first whose name matches.

    AgentCore Identity caps maxResults at 20 for this API (unlike list_gateways
    and list_gateway_targets which allow 100). Passing anything higher returns
    a ValidationException.
    """
    kwargs = {"maxResults": 20}
    while True:
        resp = CONTROL.list_oauth2_credential_providers(**kwargs)
        for cp in resp.get("credentialProviders", []):
            if cp.get("name") == name:
                return cp
        token = resp.get("nextToken")
        if not token:
            return None
        kwargs["nextToken"] = token


def ensure_oauth2_credential_provider(props: dict) -> str:
    """Find-or-create the AgentCore Identity OAuth2 credential provider used
    by the Gateway target to authenticate to the upstream runtime.

    Returns the credential provider ARN.

    Skips creation entirely when OAuthProviderArn is supplied — that means
    the customer has their own provider they want us to reuse.
    """
    existing_arn = (props.get("OAuthProviderArn") or "").strip()
    if existing_arn:
        print(f"Reusing customer-supplied OAuth2 credential provider: {existing_arn}")
        return existing_arn

    name = props["CredentialProviderName"]
    client_id = (props.get("OAuthClientId") or "").strip()
    client_secret = (props.get("OAuthClientSecret") or "").strip()
    if not (client_id and client_secret):
        raise ValueError(
            "Auto-provisioning an OAuth2 credential provider requires "
            "OAuthClientId and OAuthClientSecret. Set them, or supply an "
            "existing OAuthProviderArn to reuse a pre-created provider."
        )

    existing = find_oauth2_credential_provider_by_name(name)
    if existing:
        arn = existing["credentialProviderArn"]
        print(f"OAuth2 credential provider already exists: name={name} arn={arn} — reusing")
        return arn

    oauth_discovery = _build_oauth_discovery_block(props)
    if "authorizationServerMetadata" in oauth_discovery:
        print(
            f"Creating OAuth2 credential provider: {name} "
            f"(custom tokenEndpoint: "
            f"{oauth_discovery['authorizationServerMetadata']['tokenEndpoint']})"
        )
    else:
        print(
            f"Creating OAuth2 credential provider: {name} "
            f"(discoveryUrl: {oauth_discovery['discoveryUrl']})"
        )

    resp = CONTROL.create_oauth2_credential_provider(
        name=name,
        credentialProviderVendor="CustomOauth2",
        oauth2ProviderConfigInput={
            "customOauth2ProviderConfig": {
                "oauthDiscovery": oauth_discovery,
                "clientId": client_id,
                "clientSecret": client_secret,
            }
        },
    )
    arn = resp["credentialProviderArn"]
    print(f"Created OAuth2 credential provider: arn={arn}")
    return arn


def delete_oauth2_credential_provider_best_effort(name: str) -> None:
    """Tear down the auto-provisioned credential provider on stack delete.

    Truly best-effort: any failure (list error, AWS API hiccup, missing
    permission) is logged but never raised. A delete operation that wedges
    CloudFormation because we couldn't introspect a leftover provider is
    far worse than leaving the provider orphaned for manual cleanup.
    """
    try:
        existing = find_oauth2_credential_provider_by_name(name)
    except Exception as exc:  # pragma: no cover — list call failed
        print(
            f"WARN: could not list OAuth2 credential providers while looking for "
            f"{name!r}: {exc}. Attempting blind delete."
        )
        existing = {"credentialProviderArn": "unknown"}

    if not existing:
        print(f"No OAuth2 credential provider named {name} — nothing to delete.")
        return
    try:
        CONTROL.delete_oauth2_credential_provider(name=name)
        print(f"Deleted OAuth2 credential provider: name={name}")
    except CONTROL.exceptions.ResourceNotFoundException:
        print(f"OAuth2 credential provider already gone: {name}")
    except Exception as exc:  # pragma: no cover — best-effort teardown
        print(f"WARN: could not delete OAuth2 credential provider {name}: {exc}")


def build_metadata_configuration() -> dict:
    """Per AWS MCP-target docs: allow Mcp-Session-Id through so the Gateway
    reuses MCP sessions instead of re-initializing on every tool call.
    """
    return {
        "allowedRequestHeaders": ["Mcp-Session-Id"],
        "allowedResponseHeaders": ["Mcp-Session-Id"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle ops
# ─────────────────────────────────────────────────────────────────────────────

def ensure_gateway(props: dict) -> dict:
    """Find-or-create the Gateway. Returns the gateway summary dict."""
    name = props["GatewayName"]
    existing = find_gateway_by_name(name)
    if existing:
        gateway_id = existing["gatewayId"]
        print(f"Gateway already exists: name={name} id={gateway_id} — reusing")
        return CONTROL.get_gateway(gatewayIdentifier=gateway_id)

    print(f"Creating gateway: {name}")
    create_kwargs = {
        "name": name,
        "roleArn": props["GatewayServiceRoleArn"],
        "protocolType": "MCP",
        "authorizerType": "CUSTOM_JWT",
        "authorizerConfiguration": build_authorizer_configuration(props),
        "description": "Zscaler MCP Server gateway (provisioned by CloudFormation).",
    }
    # Always enable AgentCore Gateway's semantic-tool-search feature
    # (https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using-mcp-semantic-search.html).
    # This adds the `x_amz_bedrock_agentcore_search` tool, which clients
    # call with a natural-language query to look up the most relevant
    # tool when they don't already know its exact name. AWS guarantees
    # this tool is the *first* entry returned by tools/list, so clients
    # that don't paginate (today: Claude Desktop / Claude.ai via mcp-remote,
    # which never follows nextCursor) still see it — preventing the
    # "tool not found" surprise when the catalog exceeds one page (~30
    # tools). With the Zscaler MCP Server registering 280+ tools, the
    # first-page cutoff hides most of the catalog without this on.
    #
    # NOTE: searchType is a Gateway-create-only setting; AWS rejects
    # update_gateway calls that try to flip it. To change it later you
    # destroy + recreate the Gateway (which is exactly what
    # aws_mcp_operations.py destroy + deploy does).
    mcp_cfg: dict = {"searchType": "SEMANTIC"}
    # MCP protocol versions the Gateway advertises in protocolConfiguration.
    # Accepts a single version ("2025-11-25") or a comma-separated list
    # ("2025-11-25,2025-03-26") so the Gateway can serve clients with
    # different protocol-version expectations. Notably, Amazon Quick's MCP
    # integration currently sends `MCP-Protocol-Version: 2025-03-26` on
    # service-to-service connections; a Gateway that only declares
    # `2025-11-25` rejects every Quick request with a 400 and the connector
    # registers only a placeholder action. AWS does not permit adding
    # versions to an existing Gateway (update_gateway rejects new versions
    # with ValidationException), so the multi-version set must be declared
    # at create time — exactly what this code path does.
    mcp_versions = _split_csv(props.get("GatewayMcpVersion", ""))
    if mcp_versions:
        mcp_cfg["supportedVersions"] = mcp_versions
    create_kwargs["protocolConfiguration"] = {"mcp": mcp_cfg}

    resp = CONTROL.create_gateway(**create_kwargs)
    gateway_id = resp["gatewayId"]
    print(f"Created gateway: id={gateway_id}")
    return wait_for_gateway_status(gateway_id, "READY")


def ensure_target(gateway_id: str, props: dict, oauth_provider_arn: str) -> dict:
    """Create the mcpServer target if missing; otherwise update it in place.

    Both paths build the same ``targetConfiguration`` /
    ``credentialProviderConfigurations`` payload — the only difference is
    create_gateway_target vs update_gateway_target. The update path is
    intentionally idempotent: re-running with identical inputs is a no-op
    on the AgentCore side and keeps the target available throughout
    (no CREATING → READY downtime window).
    """
    name = props["TargetName"]
    upstream_url = props["UpstreamMcpUrl"]

    target_config = build_target_configuration(props, upstream_url)
    cred_config = build_credential_provider_configurations(props, oauth_provider_arn)
    metadata_config = build_metadata_configuration()

    existing = find_target_by_name(gateway_id, name)
    if existing:
        target_id = existing["targetId"]
        print(f"Updating target: name={name} id={target_id} upstream={upstream_url}")
        CONTROL.update_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id,
            name=name,
            description="Zscaler MCP Server (AgentCore Runtime).",
            targetConfiguration=target_config,
            credentialProviderConfigurations=cred_config,
        )
    else:
        print(f"Creating target: name={name} upstream={upstream_url}")
        resp = CONTROL.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=name,
            description="Zscaler MCP Server (AgentCore Runtime).",
            targetConfiguration=target_config,
            credentialProviderConfigurations=cred_config,
            metadataConfiguration=metadata_config,
        )
        target_id = resp["targetId"]
        print(f"Created target: id={target_id}")

    return wait_for_target_status(gateway_id, target_id, "READY")


def delete_target_best_effort(gateway_id: str, name: str) -> None:
    existing = find_target_by_name(gateway_id, name)
    if not existing:
        print(f"No target named {name} on gateway {gateway_id} — nothing to delete.")
        return
    target_id = existing["targetId"]
    try:
        CONTROL.delete_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id,
        )
        print(f"Deleted target: name={name} id={target_id}")
    except CONTROL.exceptions.ResourceNotFoundException:
        print(f"Target already gone: {name}")
    except Exception as exc:  # pragma: no cover — best-effort teardown
        print(f"WARN: could not delete target {target_id}: {exc}")


def delete_gateway_best_effort(name: str) -> None:
    existing = find_gateway_by_name(name)
    if not existing:
        print(f"No gateway named {name} — nothing to delete.")
        return
    gateway_id = existing["gatewayId"]
    # AgentCore rejects DeleteGateway while targets still exist; sweep first.
    deleted_any_targets = False
    try:
        kwargs = {"gatewayIdentifier": gateway_id, "maxResults": 100}
        while True:
            resp = CONTROL.list_gateway_targets(**kwargs)
            for t in resp.get("items", []):
                tid = t["targetId"]
                tname = t.get("name", tid)
                try:
                    CONTROL.delete_gateway_target(
                        gatewayIdentifier=gateway_id, targetId=tid,
                    )
                    deleted_any_targets = True
                    print(f"Deleted orphan target on gateway: name={tname} id={tid}")
                except Exception as exc:  # pragma: no cover
                    print(f"WARN: could not delete orphan target {tid}: {exc}")
            token = resp.get("nextToken")
            if not token:
                break
            kwargs["nextToken"] = token
    except Exception as exc:  # pragma: no cover
        print(f"WARN: could not enumerate targets for gateway {gateway_id}: {exc}")

    # AgentCore's target list is eventually consistent. If we just deleted
    # any targets, poll until list_gateway_targets returns empty before
    # attempting the gateway delete, otherwise we hit
    # "Gateway has targets associated with it. Delete all targets before
    # deleting the gateway." (the gateway is left in CFN's deletion path
    # which then DELETE_FAILS the stack).
    if deleted_any_targets:
        for attempt in range(12):  # up to ~60s
            try:
                resp = CONTROL.list_gateway_targets(
                    gatewayIdentifier=gateway_id, maxResults=100,
                )
                if not resp.get("items"):
                    break
            except Exception as exc:  # pragma: no cover
                print(f"WARN: could not poll target list during teardown: {exc}")
                break
            time.sleep(5)

    try:
        CONTROL.delete_gateway(gatewayIdentifier=gateway_id)
        print(f"Deleted gateway: name={name} id={gateway_id}")
    except CONTROL.exceptions.ResourceNotFoundException:
        print(f"Gateway already gone: {name}")
    except Exception as exc:  # pragma: no cover
        print(f"WARN: could not delete gateway {gateway_id}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Custom-resource entry point
# ─────────────────────────────────────────────────────────────────────────────

def handler(event, context):
    print(f"Event: {json.dumps(event)[:1500]}")
    try:
        request_type = event["RequestType"]
        props = event["ResourceProperties"]
        mode = (props.get("GatewayMode") or "create").strip().lower()
        if mode not in ("create", "attach"):
            raise ValueError(f"Invalid GatewayMode: {mode!r} (expected 'create' or 'attach').")

        if request_type in ("Create", "Update"):
            _handle_create_or_update(event, context, mode, props)
        elif request_type == "Delete":
            _handle_delete(event, context, mode, props)

    except Exception as exc:
        print(f"FAILED: {exc}")
        send(event, context, "FAILED", {}, reason=str(exc))


def _handle_create_or_update(event, context, mode: str, props: dict) -> None:
    if mode == "create":
        gateway = ensure_gateway(props)
        gateway_id = gateway["gatewayId"]
        gateway_arn = gateway.get("gatewayArn", "")
        # AgentCore returns the MCP URL on the gateway itself.
        mcp_url = gateway.get("gatewayUrl") or gateway.get("mcpUrl") or ""
    else:  # mode == "attach"
        gateway_id = (props.get("ExistingGatewayId") or "").strip()
        if not gateway_id:
            raise ValueError(
                "GatewayMode=attach requires ExistingGatewayId. Set it to the ID "
                "of a Gateway already provisioned in this account/region."
            )
        # Validate the gateway exists + grab its URL so we can echo it back.
        gw = CONTROL.get_gateway(gatewayIdentifier=gateway_id)
        gateway_arn = gw.get("gatewayArn", "")
        mcp_url = gw.get("gatewayUrl") or gw.get("mcpUrl") or ""
        print(f"Attaching to existing gateway: id={gateway_id} url={mcp_url}")

    oauth_provider_arn = ensure_oauth2_credential_provider(props)
    target = ensure_target(gateway_id, props, oauth_provider_arn)
    target_id = target["targetId"]

    send(event, context, "SUCCESS", {
        "GatewayId":         gateway_id,
        "GatewayArn":        gateway_arn,
        "McpUrl":            mcp_url,
        "TargetId":          target_id,
        "OAuthProviderArn":  oauth_provider_arn,
        "Mode":              mode,
    })


def _handle_delete(event, context, mode: str, props: dict) -> None:
    # Always succeed on delete so a stuck stack can be torn down. Failure here
    # would block CFN forever; we'd rather leave a managed-but-orphan resource
    # behind and log loudly than wedge the stack.
    target_name = props.get("TargetName", "")
    cred_provider_name = props.get("CredentialProviderName", "")
    customer_owns_provider = bool((props.get("OAuthProviderArn") or "").strip())

    if mode == "attach":
        gateway_id = (props.get("ExistingGatewayId") or "").strip()
        if gateway_id and target_name:
            delete_target_best_effort(gateway_id, target_name)
        else:
            print("Delete (attach mode): missing ExistingGatewayId or TargetName — skipping.")
        if cred_provider_name and not customer_owns_provider:
            delete_oauth2_credential_provider_best_effort(cred_provider_name)
        send(event, context, "SUCCESS", {"Mode": "attach"})
        return

    # Create mode → cascade: target then gateway, then credential provider.
    gateway_name = props.get("GatewayName", "")
    if gateway_name:
        # delete_gateway_best_effort handles target cleanup internally.
        delete_gateway_best_effort(gateway_name)
    else:
        print("Delete (create mode): missing GatewayName — skipping.")
    if cred_provider_name and not customer_owns_provider:
        delete_oauth2_credential_provider_best_effort(cred_provider_name)
    send(event, context, "SUCCESS", {"Mode": "create"})
