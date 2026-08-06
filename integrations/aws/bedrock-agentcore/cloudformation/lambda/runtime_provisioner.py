"""AgentCore Runtime CloudFormation custom-resource handler.

Invoked by the CFN custom resource defined in runtime.yaml. Creates,
updates, and deletes the Bedrock AgentCore Runtime via boto3 since
there is no native AWS::BedrockAgentCore::Runtime CloudFormation type
yet (as of this writing).

Plane split (this is a real footgun):
  - bedrock-agentcore-control  →  CRUD on Runtime, Gateway, Endpoint, etc.
  - bedrock-agentcore          →  data-plane invoke ops only
                                  (InvokeAgentRuntime, InvokeBrowser, ...)

Identifier model:
  - agentRuntimeName  →  human-friendly, supplied at Create time only
  - agentRuntimeId    →  AWS-generated ID used by Get/Update/Delete
                         (looked up via ListAgentRuntimes + filter on name)

Header forwarding per auth mode:
  AgentCore's invoke-agent-runtime API only forwards headers that
  appear in the runtime's requestHeaderAllowlist (max 20 entries).
  See https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-header-allowlist.html
  Every mode allowlists the MCP protocol headers (MCP-Protocol-Version,
  Mcp-Method, Mcp-Name, Mcp-Session-Id) — they are what keep both the
  2026-07-28 stateless revision and the older handshake revisions
  callable, see MCP_ROUTING_HEADERS. On top of that, per McpAuthMode:

    none     → routing headers only, no authorizer
    api-key  → + X-Api-Key
    zscaler  → + X-Zscaler-Client-ID, X-Zscaler-Client-Secret
    jwt      → + Authorization, + customJwtAuthorizer
               (Authorization is forwardable ONLY when customJwtAuthorizer
                is configured — AWS-enforced).

  For api-key and zscaler modes, the container also accepts a request
  that carries no credential at all, using its own — which is what makes
  the AgentCore Console Sandbox playground usable even though it cannot
  attach custom headers from the UI. That behaviour is off by default and
  is enabled here, and only here, by ZSCALER_MCP_TRUST_PLATFORM_AUTH
  (see zscaler_mcp/security/auth.py::platform_auth_trusted).
"""

import json
import time
import urllib.parse
import urllib.request

import boto3

CONTROL = boto3.client("bedrock-agentcore-control")


def send(event, context, status, data, reason=""):
    body = json.dumps(
        {
            "Status": status,
            "Reason": reason or f"See CloudWatch log {context.log_stream_name}",
            "PhysicalResourceId": data.get("RuntimeId", context.log_stream_name),
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
            "Data": data,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        event["ResponseURL"],
        data=body,
        method="PUT",
        headers={"Content-Type": "", "Content-Length": str(len(body))},
    )
    with urllib.request.urlopen(req) as resp:
        resp.read()


def find_runtime_by_name(name: str) -> dict | None:
    """Walk ListAgentRuntimes and return the runtime summary whose name matches."""
    paginator_kwargs = {"maxResults": 100}
    while True:
        resp = CONTROL.list_agent_runtimes(**paginator_kwargs)
        for rt in resp.get("agentRuntimes", []):
            if rt.get("agentRuntimeName") == name:
                return rt
        token = resp.get("nextToken")
        if not token:
            return None
        paginator_kwargs["nextToken"] = token


def wait_for_status(runtime_id: str, target_status: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        rt = CONTROL.get_agent_runtime(agentRuntimeId=runtime_id)
        status = rt.get("status", "UNKNOWN")
        print(f"  status={status}")
        if status == target_status:
            return rt
        if status in ("CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED"):
            raise RuntimeError(f"Runtime entered terminal failure state: {status}")
        time.sleep(10)
    raise TimeoutError(f"Runtime did not reach {target_status} within {timeout}s")


# Routing headers for MCP revision 2026-07-28. The SDK selects the modern
# stateless handler purely on the MCP-Protocol-Version *header*
# (streamable_http_manager._handle_request); body content is never consulted.
# The classifier then requires Mcp-Method to equal the body's method, and
# Mcp-Name to equal the named param for tools/call, prompts/get and
# resources/read (mcp.shared.inbound.classify_inbound_request).
#
# InvokeAgentRuntime drops every header not named here, so omitting them does
# not degrade 2026-07-28 to something slower — it makes the revision
# unreachable, silently, for every client. Requests fall back to the
# initialize handshake, which needs an Mcp-Session-Id echoed on each
# subsequent call, and AgentCore gives each call a fresh microVM.
#
# Mcp-Session-Id is allowlisted so it is at least not *also* stripped, but note
# that the handshake revisions still cannot complete a session on AgentCore: the
# platform manages MCP sessions itself and hands the client a session id of its
# own rather than the one the container issued, so the client has nothing valid
# to echo and the next call 404s. Verified end-to-end — initialize returned
# f7ebe538-ba3c-... while the container logged 5c8e958dfea4... . No allowlist
# entry can undo that substitution; AgentCore is a 2026-07-28 target, and the
# ALB-fronted ECS / EC2 / EKS deployments serve both revisions unaffected.
#
# Allowlisted in all four auth modes, including 'none': protocol routing is
# orthogonal to who the caller is.
MCP_ROUTING_HEADERS = [
    "MCP-Protocol-Version",
    "Mcp-Method",
    "Mcp-Name",
    "Mcp-Session-Id",
]


def build_inbound_auth_kwargs(props) -> dict:
    """Build the requestHeaderConfiguration + authorizer config for create/update.

    Returns a kwargs dict to splat into create_agent_runtime / update_agent_runtime.

    AgentCore restrictions enforced here:
      - Authorization is allowlist-eligible ONLY when customJwtAuthorizer
        is configured (the API itself rejects the combination otherwise).
      - Headers prefixed with x-amz-/x-amzn- are restricted (except
        X-Amzn-Bedrock-AgentCore-Runtime-Custom-*); we don't use those.
      - Max 20 headers per runtime; we configure at most 6.
    """
    auth_mode = props["McpAuthMode"]
    kwargs: dict = {}
    allowlist = list(MCP_ROUTING_HEADERS)

    if auth_mode == "api-key":
        allowlist.append("X-Api-Key")

    elif auth_mode == "zscaler":
        allowlist += ["X-Zscaler-Client-ID", "X-Zscaler-Client-Secret"]

    elif auth_mode == "jwt":
        discovery_url = props.get("JwtDiscoveryUrl") or _derive_discovery_url(
            props.get("JwtIssuer", "")
        )
        if not discovery_url:
            raise ValueError(
                "jwt auth mode requires JwtDiscoveryUrl (or JwtIssuer from which it can "
                "be derived as <issuer>/.well-known/openid-configuration)."
            )
        custom_jwt: dict = {
            "discoveryUrl": discovery_url,
            "allowedAudience": [
                a.strip()
                for a in props.get("JwtAudience", "zscaler-mcp-server").split(",")
                if a.strip()
            ],
        }
        allowed_clients = [
            c.strip() for c in props.get("JwtAllowedClients", "").split(",") if c.strip()
        ]
        if allowed_clients:
            custom_jwt["allowedClients"] = allowed_clients

        kwargs["authorizerConfiguration"] = {"customJWTAuthorizer": custom_jwt}
        allowlist.append("Authorization")

    # auth_mode == 'none' falls through with the routing headers only.
    kwargs["requestHeaderConfiguration"] = {"requestHeaderAllowlist": allowlist}
    return kwargs


def build_network_configuration(props) -> dict:
    """Build ``networkConfiguration`` for create/update_agent_runtime.

    PUBLIC mode (default) returns the simple AgentCore-managed network
    shape. VPC mode wires ENIs into customer-owned subnets/SGs per
    SEP-VPC support (https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html).

    Raises ``ValueError`` if VPC mode is requested without at least one
    subnet AND at least one security group — AgentCore's
    ``CreateAgentRuntime`` rejects either missing, so we fail fast here
    with a clear message rather than letting the API surface it as a
    generic 400.
    """
    mode = (props.get("NetworkMode") or "PUBLIC").strip().upper()
    if mode == "PUBLIC":
        return {"networkMode": "PUBLIC"}
    if mode != "VPC":
        raise ValueError(f"NetworkMode={mode!r} is invalid. Allowed: PUBLIC, VPC.")

    subnets = [s.strip() for s in (props.get("VpcSubnetIds") or "").split(",") if s.strip()]
    sgs = [s.strip() for s in (props.get("VpcSecurityGroupIds") or "").split(",") if s.strip()]
    if not subnets:
        raise ValueError("NetworkMode=VPC requires at least one subnet in VpcSubnetIds.")
    if not sgs:
        raise ValueError(
            "NetworkMode=VPC requires at least one security group in VpcSecurityGroupIds."
        )
    return {
        "networkMode": "VPC",
        "networkModeConfig": {
            "subnets": subnets,
            "securityGroups": sgs,
        },
    }


def _derive_discovery_url(issuer: str) -> str:
    """OIDC discovery URL = <issuer>/.well-known/openid-configuration.

    Normalises a trailing slash on the issuer so we don't emit a double slash.
    """
    issuer = (issuer or "").strip()
    if not issuer:
        return ""
    return f"{issuer.rstrip('/')}/.well-known/openid-configuration"


def build_runtime_mcp_url(runtime_arn: str, qualifier: str = "DEFAULT") -> str:
    """Build the AgentCore Runtime MCP invocation URL from the runtime ARN.

    AgentCore's GetAgentRuntime response does NOT contain the invocation URL —
    it has to be assembled from the ARN. The data-plane format is:

      https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<encoded-arn>/invocations?qualifier=<qualifier>

    where <encoded-arn> is the full runtime ARN with every `:` and `/`
    percent-encoded (urllib.parse.quote with safe=""). The default qualifier
    "DEFAULT" points at the latest deployed version; named endpoints use
    their endpoint name.

    Returns "" if the ARN is empty or malformed (caller should surface this
    as a deployment failure — Gateway target creation will reject "").
    """
    arn = (runtime_arn or "").strip()
    if not arn.startswith("arn:") or ":" not in arn:
        return ""
    # ARN shape: arn:aws:bedrock-agentcore:<region>:<account>:runtime/<name>
    parts = arn.split(":", 5)
    if len(parts) < 6:
        return ""
    region = parts[3]
    if not region:
        return ""
    encoded_arn = urllib.parse.quote(arn, safe="")
    return (
        f"https://bedrock-agentcore.{region}.amazonaws.com"
        f"/runtimes/{encoded_arn}/invocations?qualifier={qualifier}"
    )


def build_env(props):
    env = {
        "ZSCALER_SECRET_NAME": props["SecretName"],
        "ZSCALER_MCP_WRITE_ENABLED": props["WriteToolsEnabled"],
        "ZSCALER_MCP_AUTH_MODE": props["McpAuthMode"],
        # AgentCore's ContainerConfiguration accepts ONLY containerUri — there is
        # no command or args override — so the stock image's entrypoint has to be
        # steered entirely from here. The published image defaults to stdio on
        # 127.0.0.1, which AgentCore cannot reach; these three make it serve the
        # MCP protocol contract (POST 0.0.0.0:8000/mcp).
        #
        # This is what lets the AgentCore path run the SAME multi-arch image as
        # Docker Hub, instead of a separate build whose only difference was a
        # baked-in CMD.
        "ZSCALER_MCP_TRANSPORT": "streamable-http",
        "ZSCALER_MCP_HOST": "0.0.0.0",
        "ZSCALER_MCP_PORT": "8000",
    }
    if props["WriteToolsAllowlist"]:
        env["ZSCALER_MCP_WRITE_TOOLS"] = props["WriteToolsAllowlist"]
    if props["DisabledTools"]:
        env["ZSCALER_MCP_DISABLED_TOOLS"] = props["DisabledTools"]
    if props["DisabledServices"]:
        env["ZSCALER_MCP_DISABLED_SERVICES"] = props["DisabledServices"]
    if props["EnableToolCallLogging"] == "true":
        env["ZSCALER_MCP_LOG_TOOL_CALLS"] = "true"

    if props["McpAuthMode"] == "jwt":
        env["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        env["ZSCALER_MCP_AUTH_JWKS_URI"] = props["JwtJwksUri"]
        env["ZSCALER_MCP_AUTH_ISSUER"] = props["JwtIssuer"]
        env["ZSCALER_MCP_AUTH_AUDIENCE"] = props["JwtAudience"]
    elif props["McpAuthMode"] == "api-key":
        env["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        env["ZSCALER_MCP_AUTH_API_KEY"] = props["ApiKey"]
    elif props["McpAuthMode"] == "zscaler":
        env["ZSCALER_MCP_AUTH_ENABLED"] = "true"
    else:
        env["ZSCALER_MCP_AUTH_ENABLED"] = "false"

    if props["McpAuthMode"] in ("api-key", "zscaler"):
        # Let a request that carries no credential through, using the container's
        # own. Not a knob: on AgentCore Runtime it is unconditionally true that
        # the platform authenticated the caller first (IAM
        # bedrock-agentcore:InvokeAgentRuntime, or the customJwtAuthorizer) and
        # equally true that the caller often CANNOT present one —
        # InvokeAgentRuntime forwards only headers named in
        # requestHeaderAllowlist, and the Console Sandbox playground has no UI to
        # set a header at all.
        #
        # It is set ONLY here, for exactly this reason. Never set it on the
        # ECS / EC2 / EKS templates, where the container is reachable directly.
        env["ZSCALER_MCP_TRUST_PLATFORM_AUTH"] = "true"

    # Deliberately NOT set here: ZSCALER_MCP_REQUEST_STATE_KEYS. A shared key
    # ring is required for delete confirmations to survive across the ephemeral
    # microVMs AgentCore runs, but it is key material — putting it in
    # environmentVariables would print it in the CloudFormation template and the
    # AgentCore console. Add it to the Secrets Manager secret instead; the AWS
    # loader (cloud/aws_secrets.py) allowlists that key and publishes it before
    # the server reads it. The server warns at startup if write tools are on
    # without one.
    #
    # Also deliberately NOT set: ZSCALER_MCP_ALLOWED_SOURCE_IPS. The ACL reads
    # the ASGI peer address, which behind AgentCore's proxy is the proxy — so an
    # allowlist there is meaningless at best and locks out every caller at worst.

    # AgentCore terminates TLS upstream
    env["ZSCALER_MCP_ALLOW_HTTP"] = "true"
    # AgentCore Runtime is the sole ingress to the container. It validates
    # the request (CUSTOM_JWT authorizer, header allowlist) and forwards an
    # internal Host header that is not predictable for an explicit allowlist.
    # The container-level host validation would add no security on top of
    # AgentCore's own auth + routing, so we disable it here.
    env["ZSCALER_MCP_DISABLE_HOST_VALIDATION"] = "true"
    return env


def handler(event, context):
    print(f"Event: {json.dumps(event)[:1000]}")
    try:
        request_type = event["RequestType"]
        props = event["ResourceProperties"]
        runtime_name = props["RuntimeName"]

        if request_type in ("Create", "Update"):
            env = build_env(props)
            auth_kwargs = build_inbound_auth_kwargs(props)
            if auth_kwargs:
                print(f"Inbound auth kwargs: {json.dumps(auth_kwargs)}")
            network_config = build_network_configuration(props)
            print(f"Network configuration: {json.dumps(network_config)}")
            existing = find_runtime_by_name(runtime_name)

            if existing:
                runtime_id = existing["agentRuntimeId"]
                print(f"Updating existing runtime: name={runtime_name} id={runtime_id}")
                CONTROL.update_agent_runtime(
                    agentRuntimeId=runtime_id,
                    agentRuntimeArtifact={
                        "containerConfiguration": {"containerUri": props["ImageUri"]},
                    },
                    roleArn=props["ExecutionRoleArn"],
                    networkConfiguration=network_config,
                    protocolConfiguration={"serverProtocol": "MCP"},
                    environmentVariables=env,
                    **auth_kwargs,
                )
            else:
                print(f"Creating runtime: {runtime_name}")
                resp = CONTROL.create_agent_runtime(
                    agentRuntimeName=runtime_name,
                    agentRuntimeArtifact={
                        "containerConfiguration": {"containerUri": props["ImageUri"]},
                    },
                    roleArn=props["ExecutionRoleArn"],
                    networkConfiguration=network_config,
                    protocolConfiguration={"serverProtocol": "MCP"},
                    environmentVariables=env,
                    **auth_kwargs,
                )
                runtime_id = resp["agentRuntimeId"]
                print(f"Created runtime: id={runtime_id}")

            rt = wait_for_status(runtime_id, "READY")
            runtime_arn = rt["agentRuntimeArn"]
            mcp_url = build_runtime_mcp_url(runtime_arn)
            if not mcp_url:
                raise RuntimeError(
                    f"Could not derive MCP URL from runtime ARN: {runtime_arn!r}. "
                    "Expected shape arn:aws:bedrock-agentcore:<region>:<account>:runtime/<name>."
                )
            print(f"Runtime MCP URL: {mcp_url}")
            send(
                event,
                context,
                "SUCCESS",
                {
                    "RuntimeId": runtime_id,
                    "RuntimeArn": runtime_arn,
                    "McpUrl": mcp_url,
                },
            )

        elif request_type == "Delete":
            existing = find_runtime_by_name(runtime_name)
            if existing:
                runtime_id = existing["agentRuntimeId"]
                try:
                    CONTROL.delete_agent_runtime(agentRuntimeId=runtime_id)
                    print(f"Deleted runtime: name={runtime_name} id={runtime_id}")
                except CONTROL.exceptions.ResourceNotFoundException:
                    print(f"Runtime already gone: {runtime_name}")
            else:
                print(f"No runtime named {runtime_name} found — nothing to delete.")
            send(event, context, "SUCCESS", {"RuntimeId": runtime_name})

    except Exception as exc:
        print(f"FAILED: {exc}")
        send(event, context, "FAILED", {}, reason=str(exc))
