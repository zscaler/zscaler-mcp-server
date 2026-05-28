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
  This handler configures the allowlist (and customJwtAuthorizer when
  required) based on McpAuthMode:

    none     → no header allowlist, no authorizer
    api-key  → allowlist X-Api-Key
    zscaler  → allowlist X-Zscaler-Client-ID, X-Zscaler-Client-Secret
    jwt      → allowlist Authorization + customJwtAuthorizer
               (Authorization is forwardable ONLY when customJwtAuthorizer
                is configured — AWS-enforced).

  For api-key and zscaler modes, the container also accepts the
  credential as an env var (see zscaler_mcp/auth.py) so the AgentCore
  Console Sandbox playground works even though it cannot attach
  custom headers from the UI.
"""

import json
import time
import urllib.parse
import urllib.request

import boto3

CONTROL = boto3.client("bedrock-agentcore-control")


def send(event, context, status, data, reason=""):
    body = json.dumps({
        "Status":             status,
        "Reason":             reason or f"See CloudWatch log {context.log_stream_name}",
        "PhysicalResourceId": data.get("RuntimeId", context.log_stream_name),
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


def build_inbound_auth_kwargs(props) -> dict:
    """Build the requestHeaderConfiguration + authorizer config for create/update.

    Returns a kwargs dict to splat into create_agent_runtime / update_agent_runtime.
    Empty dict for auth_mode='none'.

    AgentCore restrictions enforced here:
      - Authorization is allowlist-eligible ONLY when customJwtAuthorizer
        is configured (the API itself rejects the combination otherwise).
      - Headers prefixed with x-amz-/x-amzn- are restricted (except
        X-Amzn-Bedrock-AgentCore-Runtime-Custom-*); we don't use those.
      - Max 20 headers per runtime; we configure at most 2.
    """
    auth_mode = props["McpAuthMode"]
    kwargs: dict = {}

    if auth_mode == "api-key":
        kwargs["requestHeaderConfiguration"] = {
            "requestHeaderAllowlist": ["X-Api-Key"],
        }

    elif auth_mode == "zscaler":
        kwargs["requestHeaderConfiguration"] = {
            "requestHeaderAllowlist": [
                "X-Zscaler-Client-ID",
                "X-Zscaler-Client-Secret",
            ],
        }

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
            c.strip()
            for c in props.get("JwtAllowedClients", "").split(",")
            if c.strip()
        ]
        if allowed_clients:
            custom_jwt["allowedClients"] = allowed_clients

        kwargs["authorizerConfiguration"] = {"customJWTAuthorizer": custom_jwt}
        kwargs["requestHeaderConfiguration"] = {
            "requestHeaderAllowlist": ["Authorization"],
        }

    # auth_mode == 'none' falls through — no header allowlist, no authorizer.
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
        raise ValueError(
            f"NetworkMode={mode!r} is invalid. Allowed: PUBLIC, VPC."
        )

    subnets = [
        s.strip()
        for s in (props.get("VpcSubnetIds") or "").split(",")
        if s.strip()
    ]
    sgs = [
        s.strip()
        for s in (props.get("VpcSecurityGroupIds") or "").split(",")
        if s.strip()
    ]
    if not subnets:
        raise ValueError(
            "NetworkMode=VPC requires at least one subnet in VpcSubnetIds."
        )
    if not sgs:
        raise ValueError(
            "NetworkMode=VPC requires at least one security group in "
            "VpcSecurityGroupIds."
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
        "ZSCALER_SECRET_NAME":       props["SecretName"],
        "ZSCALER_MCP_WRITE_ENABLED": props["WriteToolsEnabled"],
        "ZSCALER_MCP_AUTH_MODE":     props["McpAuthMode"],
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
        env["ZSCALER_MCP_AUTH_ENABLED"]  = "true"
        env["ZSCALER_MCP_AUTH_JWKS_URI"] = props["JwtJwksUri"]
        env["ZSCALER_MCP_AUTH_ISSUER"]   = props["JwtIssuer"]
        env["ZSCALER_MCP_AUTH_AUDIENCE"] = props["JwtAudience"]
    elif props["McpAuthMode"] == "api-key":
        env["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        env["ZSCALER_MCP_AUTH_API_KEY"] = props["ApiKey"]
    elif props["McpAuthMode"] == "zscaler":
        env["ZSCALER_MCP_AUTH_ENABLED"] = "true"
    else:
        env["ZSCALER_MCP_AUTH_ENABLED"] = "false"

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
            send(event, context, "SUCCESS", {
                "RuntimeId":  runtime_id,
                "RuntimeArn": runtime_arn,
                "McpUrl":     mcp_url,
            })

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
