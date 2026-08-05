---
layout: "zscaler"
page_title: "Release Notes"
description: |-
  Zscaler Integrations MCP Server Release Notes
---

# Zscaler Integrations MCP Server: Release Notes

## USAGE

Track all Zscaler Integrations MCP Server's releases. New tools, features, and bug fixes will be tracked here.

## 0.15.0 (August 4, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

- **Requires `mcp` 2.x.** A normal `uvx zscaler-mcp` or `pip install --upgrade` handles this; note the new floor if you pin dependencies yourself. Nothing else needs installing — `fastmcp` is no longer used at all.

### Breaking Changes

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **`ZSCALER_MCP_SKIP_CONFIRMATIONS` is removed.** Delete confirmation can no longer be switched off. Setting the variable now has no effect, so remove it from any environment where it lingers. To deny deletes outright, leave them out of `--write-tools` / `ZSCALER_MCP_WRITE_TOOLS`; to drive them unattended, pass the confirmation token back like any other client does.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **The `oidcproxy` auth mode no longer takes a client secret.** It is now a standard OAuth 2.0 protected resource (RFC 9728): the server publishes `/.well-known/oauth-protected-resource` naming your IdP, and clients authenticate against the IdP directly instead of through the server. `OIDCPROXY_CLIENT_SECRET` is ignored — remove it. The mode is now called `oidc`; `oidcproxy` and `oauth-proxy` still resolve. Clients can no longer self-register, so they need a client ID issued by the IdP.

### Enhancements

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Adopted the `2026-07-28` MCP revision.** Clients on older revisions continue to work unchanged — the revision is negotiated per connection, with nothing to configure on either side.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Delete confirmation now asks a person instead of the agent.** Clients that support MCP elicitation get a `delete` / `cancel` prompt answered by a human, and anything other than `delete` aborts without calling the Zscaler API. Clients without elicitation keep using the confirmation token. No configuration changes are required.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Pending confirmations are now encrypted** and bound to the specific call, the authenticated caller, and a short expiry, so an approval cannot be moved onto a different delete, spent by another user, or used once it has expired.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Confirmations are now tied to the authenticated caller in every authentication mode.** Previously this held only for `oidc`; with `jwt`, `api-key`, or `zscaler` there was no caller identity attached, so an approval was bound to the call but not to who made it. Identity now comes from the token's verified claims (`jwt`, `oidc`), the OneAPI client ID (`zscaler`), or a one-way fingerprint of the key (`api-key`). Credentials themselves are never used as the identity.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **New `ZSCALER_MCP_REQUEST_STATE_KEYS` for deployments that run more than one replica.** By default each instance protects pending confirmations with its own key, so a confirmation answered on one replica cannot be completed on another and the user is asked again. Set this to a shared key (a JSON array or comma-separated list; at least 32 bytes each — `python -c "import secrets; print(secrets.token_hex(32))"`) and any replica can complete any confirmation. **Required if you run multiple HTTP replicas with write tools enabled**; session affinity is not an alternative, because requests on the current protocol revision carry no session ID. Keys rotate without downtime: the first entry is used for new confirmations and every entry can still complete an outstanding one. The server warns at startup if it detects the risky combination.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **The tool list is now cacheable.** The server advertises its tool inventory as cacheable for five minutes, so clients and proxies skip re-fetching several hundred tool definitions on every connection.

### Bug Fixes

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **`zia_list_url_categories` can filter server-side again, and warns before it returns a large response.** `custom_only` and `type` are now sent to the API, so "list the custom URL categories" fetches only those — one call, no client-side filtering. What the API does *not* offer is any way to cap or trim the result: it does not paginate, and every category comes back with its URL, keyword and IP lists in full (`includeOnlyUrlKeywordCounts` was tested and does not replace them with counts, so it is not offered). A tenant with 5000 custom categories therefore returns 5000 complete records. Because of that the tool now asks you which categories you want before running unfiltered, and its description points the agent at a `query` projection when the answer only needs part of each record. `page` and `page_size` are gone — the endpoint does not paginate, so they were silently ignored while suggesting a large result could be paged through. For one category use `zia_get_url_category`; to find which category a URL belongs to use `zia_url_lookup`, which was the reported problem — an agent answered that by listing every category.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Audit logging now records the arguments a tool was called with.** `[TOOL CALL]` printed `args: {}` for every call regardless of what was passed, because it only inspected keyword arguments and the server passes tool inputs as a single object. Non-empty JMESPath `query` expressions are also logged now, on their own `[QUERY]` line with the row count before and after filtering, so a filter that silently matched nothing is visible in the log instead of looking like an empty result from Zscaler.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Responses containing empty lists are now up to 4x smaller.** Results were sent as compact CSV only when every field was a simple value; a single empty list (such as the empty `urls` field on many records) switched the whole response to JSON, which repeats every field name on every row. Empty fields no longer trigger that switch. Records containing real nested data are unaffected and still sent as JSON.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **A server-side fault can no longer quietly weaken a delete confirmation.** When the server could not determine whether a client supports interactive prompts, it fell back to the confirmation-token flow — the same outcome as a client that genuinely cannot be prompted, which hid the fault. An unexpected failure now refuses the delete outright and logs the fault, instead of handing back a token. A client that simply does not support prompting is unaffected and still uses the token.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Delete confirmation tokens are now genuinely single-use.** A valid token could previously be redeemed repeatedly for its full five-minute window, so one approval could authorize more than one delete. Redeemed tokens are now tracked until they expire, and reuse is rejected along with a fresh token to re-approve with.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Fixed the server version reported to clients.** `serverInfo` returned an empty value instead of the release number, so MCP Inspector and any other client that displays it showed no version.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **The delete confirmation now tells the agent to ask you first.** On clients without elicitation support — including Claude Desktop via `mcp-remote` — the previous wording read as a retry instruction, and agents would re-issue the delete in the same turn without checking with anyone. The prompt now requires an explicit yes from the user before the token is used.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Corrected 34 create/update tool descriptions that claimed a confirmation gate they never had.** Confirmation applies to deletes only, but these tools told the agent they were "gated by HMAC" — so an agent could report that the server had vetted a create it had actually executed on the first call. The descriptions now state only the `--write-tools` requirement that does apply. No behaviour change.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Every delete tool now states that it requires confirmation.** Only 13 of the 50 said so, in three different wordings, leaving an agent comparing two delete tools free to conclude they behaved differently — they never did. All 50 now carry the same sentence, and it no longer names HMAC, which was only ever one of the two confirmation paths. No behaviour change.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Fixed OAuth 2.1 auth on the EC2, ECS Fargate and EKS deployments.** Those paths sent an `OIDCPROXY_ISSUER` no version of the server has ever read, and omitted the two variables it requires, so choosing that auth mode produced a server that exited at startup. They now pass the IdP's discovery URL and this server's public URL, and no longer ask for a client secret.

### Documentation

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Documented that the confirmation-token fallback is single-process.** Its signing key is generated per process, so on a multi-replica deployment (Cloud Run, AKS, ECS, Container Apps) a retry that lands on a different replica is asked to confirm again. Run a single replica with write tools enabled if any of your clients lack elicitation support.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Rewrote the [MCP protocol guide](https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/mcp-protocol.md)** for the new revision: which features are adopted, how delete confirmation is carried on each revision, what the encrypted confirmation state guarantees, and how conformance is verified.

- [PR #93](https://github.com/zscaler/zscaler-mcp-server/pull/93) - **Corrected the security claims made for delete confirmation.** Earlier documents implied the confirmation token defeats prompt injection; it does not. It protects the window between approval and execution, while keeping write tools disabled by default and scoping `--write-tools` narrowly are the controls that contain a hijacked agent. See the [threat model](https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/mcp-protocol.md#destructive-operation-confirmation-threat-model).

## 0.14.0 (July 24, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Enhancements

- **New `--disabled-toolsets` flag (and `ZSCALER_MCP_DISABLED_TOOLSETS`).** The blocklist complement to `--toolsets`: load everything *except* the toolsets you name, instead of having to enumerate the dozens you want. Takes exact toolset ids (no wildcards) and wins over `--toolsets` when both name the same toolset. Example: `--toolsets all --disabled-toolsets zia_ssl_inspection,zia_admin`. See the [Toolsets guide](https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/toolsets.md).

- **Unknown toolset ids are now reported.** A typo in `--toolsets` previously matched nothing and started a server with **zero tools**, silently. Both `--toolsets` and `--disabled-toolsets` now log a warning naming the unrecognized id and listing the valid ones, then continue.

- **Clearer destructive-operation confirmations.** The confirmation prompt shown before a delete now names the resource being removed on 48 of the 50 delete tools — previously any tool whose identifier isn't literally `id`/`name` (e.g. ZPA's `group_id`) showed `unknown`. The prompt now falls back to the resource's `*_id` parameter. The two exceptions are the bulk URL-list deletes (`zia_delete_atp_malicious_urls`, `zia_delete_auth_exempt_urls`), which take a list of URLs rather than an identifier and still show `unknown`.

- **Tool behavior hints for MCP clients.** Every tool now advertises standard MCP annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`) derived from its action. Supported clients use these to decide when to surface a confirmation — read tools run freely, while create/update/delete are flagged as writes (delete and PUT-replace updates as destructive).

- **MCP protocol posture hardened.** The MCP SDK dependencies are now capped to their current major versions (`mcp<2`, `fastmcp<4`) so a routine install cannot silently jump onto the in-progress next protocol revision before it is validated. The server is also verified against the official MCP conformance suite in CI against the published `2025-11-25` protocol.

### Bug Fixes

- **Read tools no longer drop attributes — every field the Zscaler API returns is now included** ([#88](https://github.com/zscaler/zscaler-mcp-server/issues/88)). Since v0.13.0, read tools projected each resource down to a fixed subset of fields, so any attribute outside that subset silently disappeared. The most visible case was `zcc_list_devices` dropping `policy_name` (along with most enrollment and telemetry fields), which made per-device policy assignment impossible to determine through the server — but the same trimming affected resources across every service.

  Read tools now return the **complete record**, exactly as the Zscaler API provides it. The server no longer declares an output schema enumerating a resource's attributes either, so a field Zscaler adds in future reaches you with **no server upgrade required**. (Create and update tools still document every settable input field, exactly as the Zscaler SDK does.)

  Two follow-on changes come with this:

  - The `detail='summary'|'full'` parameter on the ZCC and ZPA list/get tools is **removed**. It existed only to opt out of the trimming, and with the full record always returned it no longer selected anything. Note it is rejected rather than ignored — passing it returns an `Unexpected keyword argument` validation error — so drop it from any saved script, workflow, or agent prompt.
  - Field names in responses are now exactly what the Zscaler API returns (for example `policyName`, `registrationState`), rather than a server-invented spelling. This covers the 243 read tools that return a resource record. The remaining 11 return a container the server itself builds — the ZPA LSS metadata catalogs, the ZMS status / nonce / TOTP envelopes, `zdx_get_analysis`, and `ztw_get_discovery_settings` — which keep their own field names and carry the API payload intact inside.

- **Restored: JMESPath client-side filtering on list tools.** The optional `query` parameter (originally added in [PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45)) was lost during the internal rewrite and is back on **164** collection-returning tools. Pass a [JMESPath](https://jmespath.org/) expression to filter or project results before they reach the agent — `[*].{user: user, policy: policyName}`, `` [?enabled==`true`] ``, or `length(@)`. Omit it to get the full records. Together with `--toolsets`, this is the supported way to keep responses small: the caller chooses what to drop, instead of the server guessing.

## 0.13.4 (July 23, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Bug Fixes

- **Fixed listing ZIA SSL Inspection rules.** `zia_list_ssl_inspection_rules` (and `zia_get_ssl_inspection_rule`) failed with a validation error because the SSL Inspection API returns each rule's `action` as a nested object (e.g. `{"type": "DO_NOT_DECRYPT", ...}`) rather than the plain enum string used by the other ZIA rule families. The rule views now normalize that object to its action `type`, so the tools return results correctly. The list tool also no longer advertises a `search` parameter — the SSL Inspection API returns a flat list with no server-side search or pagination.

## 0.13.3 (July 21, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Enhancements

- **Dependency refresh.** All Python dependencies were upgraded to their latest compatible releases (including the latest `zscaler-sdk-python` and `fastmcp`). `zscaler-sdk-python` stays unpinned so new installs always resolve the newest SDK. No configuration changes are required.

## 0.13.2 (July 21, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Bug Fixes

- **Restored in-process TLS for HTTP transports.** The `streamable-http` / `sse` transports can once again terminate HTTPS directly in the server. Set `ZSCALER_MCP_TLS_CERTFILE` and `ZSCALER_MCP_TLS_KEYFILE` (optionally `ZSCALER_MCP_TLS_KEYFILE_PASSWORD` for an encrypted key, and `ZSCALER_MCP_TLS_CA_CERTS` for mutual-TLS client validation). When TLS is configured the server listens over `https://` and the non-localhost plaintext guard is satisfied without `ZSCALER_MCP_ALLOW_HTTP`.

- **Restored Host header validation (DNS-rebinding protection).** Set `ZSCALER_MCP_ALLOWED_HOSTS` (e.g. `your-host:*,localhost:*`) to reject requests whose `Host` header is not on the allowlist. Binding to `0.0.0.0` now refuses to start unless an allowlist is provided or validation is explicitly disabled via `ZSCALER_MCP_DISABLE_HOST_VALIDATION=true`.

- **Restored `--enable-write-tools` flag.** The master switch for write operations (create / update / delete) is available again as a CLI flag (env: `ZSCALER_MCP_WRITE_ENABLED`). It is off by default; combine with `--write-tools` to narrow the allowlist to specific tool patterns.

## 0.13.0 (July 10, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### New Services

- **New service: Zscaler Cellular (ZCell) — 20 read-only tools.** The server now supports Zscaler Cellular, exposing SIM inventory, usage analytics, anomaly policies, audit logs, and network/session events. ZCell requires **one additional credential**: your Zscaler Cellular customer ID, supplied via the `ZCELL_CUSTOMER_ID` environment variable (or the `zcellCustomerId` config key). This is separate from `ZSCALER_CUSTOMER_ID` (which ZPA uses) — set both if you use ZPA and ZCell together. All other OneAPI credentials (`ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET` / `ZSCALER_PRIVATE_KEY`, `ZSCALER_VANITY_DOMAIN`) are shared. Tools, grouped by toolset:
  - **SIM inventory** (`zcell_sim_handling`): `zcell_list_sims`, `zcell_get_sim_details`
  - **SIM analytics** (`zcell_sim_analytics`): `zcell_list_sim_analytics_summary`, `zcell_list_sim_analytics_map`, `zcell_list_sim_usage_by_sim`, `zcell_list_sim_usage_by_day`, `zcell_list_sim_usage_by_country`
  - **SIM location groups** (`zcell_sim_location_groups`): `zcell_list_sim_location_groups`, `zcell_get_sim_location_group`
  - **Anomaly policies** (`zcell_anomaly_policy`): `zcell_list_anomaly_policies`, `zcell_list_anomaly_policy_logs`, `zcell_list_anomaly_policy_violations`, `zcell_list_iccid_violations`
  - **Customer profile** (`zcell_customer_data_handling`): `zcell_get_customer_data_handling`
  - **Regions** (`zcell_customer_region_handling`): `zcell_list_regions`, `zcell_list_region_operational_status`
  - **Audit logs** (`zcell_audit_data_handling`): `zcell_list_audit_customers_search`, `zcell_list_audit_metadata`
  - **Network events** (`zcell_network_events`): `zcell_list_network_events`
  - **SIM tags** (`zcell_tag_handling`): `zcell_list_tags`

  Time-bounded ZCell queries (analytics, audit search, network events, anomaly logs) accept a `days` lookback shorthand (e.g. `days=7`). ZCell is read-only.

### Enhancements

- **Guided prompts (MCP Prompts).** The server now ships parameterized, server-side prompt playbooks that walk an AI agent through common multi-step investigations. MCP clients that support prompts (Claude Desktop, Cursor, etc.) surface these as slash-command-style starting points. Launch prompts include ZDX troubleshooting playbooks and ZCell workflows (`zcell_investigate_sim`, `zcell_audit_data_usage`, `zcell_review_anomaly_policies`).

- **Restored CLI convenience flags.** `--version` / `-v` prints the server version and exits; `--list-tools` prints every registered tool (name, action, one-line description), honouring `--services` / `--disabled-services`; `--generate-auth-token [basic|bearer]` prints ready-to-paste MCP client config snippets from your `ZSCALER_CLIENT_ID` / `ZSCALER_CLIENT_SECRET`.

- **Service-level selection flags.** `--services` / `-s` (env: `ZSCALER_MCP_SERVICES`) enables only the listed services; `--disabled-services` (env: `ZSCALER_MCP_DISABLED_SERVICES`) removes entire services (e.g. `--services zcell,zpa`).

- **User-Agent customization.** `--user-agent-comment` (env: `ZSCALER_MCP_USER_AGENT_COMMENT`) appends a comment to the outbound User-Agent the server sends to Zscaler APIs.

- **Process lifecycle management.** `zscaler-mcp status` / `reload` / `restart` / `stop` / `update` subcommands let operators inspect and control a running server without recreating it. `--dotenv-path` / `ZSCALER_MCP_DOTENV_PATH` points at an explicit `.env`; `--pid-file` / `ZSCALER_MCP_PID_FILE` overrides the PID-file location for multiple instances.

## 0.12.7 (June 10, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Bug Fixes

- [PR #79](https://github.com/zscaler/zscaler-mcp-server/pull/79) - New `zscaler-mcp update` subcommand — version check + on-demand in-place upgrade.** `zscaler-mcp update` checks GitHub Releases (PyPI fallback) and reports installed vs. latest version, the detected install channel, and the channel-correct upgrade instruction. `zscaler-mcp update --apply` (pip/venv and system installs only) pin-upgrades the package in the running server's interpreter environment, verifies the install in a fresh interpreter (printing the exact rollback pin on failure), then SIGUSR2-restarts the server so the new version loads in place — same PID, no redeploy. Inside containers `--apply` refuses and prints the image-pull recipe instead: the image is the source of truth there. Unattended updates on a VM: put `zscaler-mcp update --apply` in a cron job or systemd timer.

- [PR #79](https://github.com/zscaler/zscaler-mcp-server/pull/79) - **Publish versioned Docker tags on every release.** The `release: published` trigger in `docker-build-push.yml` never fired (same `GITHUB_TOKEN` event suppression PR #78 fixed for the MCPB bundle), so no semver-tagged image was ever pushed — Docker Hub only had `latest`. The versioned build now runs as a `docker-image-publish` job chained off the `release` job in `release.yml`, pushing immutable + rolling tags (`X.Y.Z`, `X.Y`) so production deployments can pin versions and ecosystem tooling (Renovate, Flux, Watchtower) can track releases. `docker-build-push.yml` retains `latest`-on-master-push and gains a `workflow_dispatch` path to backfill tags for existing releases (`-f tag=v0.12.6`).

## 0.12.6 (June 4, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Bug Fixes

- [PR #78](https://github.com/zscaler/zscaler-mcp-server/pull/78) - **Attach the signed MCPB bundle automatically on every release.** The standalone `mcpb-build.yml` workflow was triggered on `release: published`, but that event never fired — GitHub deliberately suppresses workflow events raised by the built-in `GITHUB_TOKEN` that `semantic-release` uses to publish the release, so `v0.12.5` shipped without the bundle attached. The build/sign/attach step now runs as a `mcpb-bundle-attach` job chained off the `release` job in `.github/workflows/release.yml` (gated on `new_release_published`), executing in the **same workflow run** as `semantic-release` and sidestepping the token suppression entirely — the cross-platform `uv`-runtime `.mcpb`, its detached PGP signature (`.asc`), and SHA-256 checksum are now attached to the GitHub Release the moment a release is cut from `master`, with no manual step. `mcpb-build.yml` is retained as a `workflow_dispatch`-only workflow for manually re-attaching a bundle to an existing release or running a dry-run build.

## 0.12.5 (June 4, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Enhancements

- [PR #77](https://github.com/zscaler/zscaler-mcp-server/pull/77) - **Automated, signed MCPB (Claude Desktop) bundle releases.** The canonical MCPB manifest now lives at `integrations/anthropic/manifest.json` (was the repo root); `scripts/build_mcpb.py` + `make build-mcpb` produce a cross-platform, source-only `uv`-runtime bundle and validate it before packing. A new standalone workflow (`.github/workflows/mcpb-build.yml`) triggers on release publication, builds the `.mcpb`, **signs it with the project PGP key** (`GPG_PRIVATE_KEY` + `PASSPHRASE`, same as `release.yml`), and attaches the bundle, its detached signature (`.asc`), and a SHA-256 checksum to the GitHub Release.

## 0.12.4 (May 26, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Enhancements

- [PR #75](https://github.com/zscaler/zscaler-mcp-server/pull/75) - **Helm chart deployment.** Added a cluster-vendor-agnostic Helm chart under `integrations/helm-chart/` for deploying the Zscaler MCP Server to any Kubernetes cluster — EKS, GKE, AKS, OpenShift, Rancher, k3s, Talos, or `kind` / `minikube` for local dev. Ships with an interactive Python deployer (`helm_mcp_operations.py`) that mirrors the Azure / GCP scripts (`deploy`, `destroy`, `status`, `logs`, `configure`, `test`), materialises a Kubernetes `Secret` directly from your existing `.env` (no translation into `values.yaml`), and auto-configures Claude Desktop + Cursor with the right `Authorization: Basic` header. Five credential-setup paths are supported (interactive script, `kubectl create secret --from-env-file`, inline `--set`, pre-existing `Secret` for GitOps, and External Secrets Operator). Full chart reference in [`integrations/helm-chart/README.md`](https://github.com/zscaler/zscaler-mcp-server/blob/master/integrations/helm-chart/README.md) and [`docs-site/docs/deployment/helm-chart.md`](https://zscaler.github.io/zscaler-mcp-server/docs/deployment/helm-chart).

## 0.12.3 (May 22, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Enhancements

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - **Strands Agent client for AgentCore Runtime.** Added `integrations/aws/bedrock-agentcore/strands_agent_chat.py` — a self-contained interactive CLI that drives a deployed AgentCore Runtime from any laptop with AWS credentials. SigV4-signs every `InvokeAgentRuntime` call, auto-discovers the runtime from `.aws-deploy-state.json`, walks the operator through a curated Bedrock model picker (Claude Sonnet 4.6 / Opus 4.7 / Opus 4.6, Amazon Nova Pro, Llama 3.3 70B) and a tool-filter preset picker (Discovery / ZPA / ZIA / ZDX read-only / policy-investigation / custom regex / all), and drops into a chat loop with per-message stats (latency, token usage), a session summary on exit, and in-chat `help` / `status` / `tools` / `clear` / `reset` / `quit` commands. Pinned dependencies live in `integrations/aws/bedrock-agentcore/requirements.txt` (boto3, strands-agents, httpx). Companion `integrations/aws/bedrock-agentcore/.gitignore` keeps `.strands-venv/` and the local state file out of git.

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - **Reorganized `integrations/aws/` into `bedrock-agentcore/` and `harness/` subfolders.** All existing AgentCore Runtime artifacts (`aws_mcp_operations.py`, `strands_agent_chat.py`, `cloudformation/`, `env.properties`, `requirements.txt`, READMEs, `.gitignore`) now live under `integrations/aws/bedrock-agentcore/`. A sibling `integrations/aws/harness/` placeholder reserves space for the upcoming AWS-recommended AgentCore Harness deployment path. The MCP server image is unchanged — Harness consumes it as a standard `remote_mcp` tool over streamable-HTTP.

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - **MCP streamable-http handshake.** The Strands client now performs the spec-compliant MCP session handshake against the AgentCore runtime — `POST initialize` (advertising protocol version `2025-11-25`), captures the server-issued `Mcp-Session-Id` response header, fires the `notifications/initialized` notification, then echoes that header on every subsequent `tools/list` / `tools/call`. This is mandatory on the `v0.12.x+` runtime image (where `web_server.py`'s Genesis NDJSON wrapper no longer bypasses the MCP transport layer). Falls back gracefully to session-less mode against the legacy `v0.10.x` Genesis-wrapped image, so the same client works against both deployments without flags.

### Bug Fixes

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - Packaged several ZDX Skill templates for better display and parsing of the response.

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - Fixed ZIA `cloud_app_control` tools by adding further docstrings instructions for proper workflow construction.

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - **ZPA list-tool pagination types.** Re-typed `page` and `page_size` as `Annotated[Optional[int], Field(ge=1, ...)]` across all 9 ZPA list tools (`zpa_list_segment_groups`, `zpa_list_server_groups`, `zpa_list_app_connectors`, `zpa_list_app_connector_groups`, `zpa_list_service_edges`, `zpa_list_lss_configs`, `zpa_list_application_segments`, `zpa_list_application_segments_ba`, `zpa_list_application_segments_pra`). The previous `Optional[str]` declaration caused Pydantic to reject every Bedrock-driven invocation with `Input should be a valid string`, because modern Claude / Nova models naturally emit JSON integers for numeric-looking arguments. The tools now convert back to `str` at the SDK call site so the underlying API call is unchanged.

### Documentation

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - Added `docs/deployment/strands-agentcore-client.md` — full reference for the new Strands client: architecture, the two-session-id model (Bedrock affinity vs. MCP transport), prerequisites, install, the MCP handshake flow, the Bedrock model catalogue, tool filter presets, interactive flow walkthrough, chat commands, CLI flags, the `--list-tools` smoke test, and a troubleshooting table covering the `-32010` handshake error, the Anthropic use-case form, the ZPA pagination Pydantic error, missing AWS creds, and `DEBUG_MCP_WIRE` for wire-level debugging.

- [PR #69](https://github.com/zscaler/zscaler-mcp-server/pull/69) - **Migrated the documentation portal from Sphinx to Docusaurus 3**, deployed to GitHub Pages. Added new sections for Skills, published Registries (Cursor, Claude, Official MCP, Docker, GitHub), and a hand-curated sitemap.

## 0.12.2 (May 18, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Bug Fixes

- [PR #67](https://github.com/zscaler/zscaler-mcp-server/pull/67) - Fixed `get_combined_user_agent` and `get_mcp_user_agent` reporting stale hardcoded versions (e.g. `0.3.1`) on source-only runs where `importlib.metadata` can't find an installed distribution. Both helpers now fall back to `zscaler_mcp.__version__` (kept in sync with `pyproject.toml` by `scripts/set-version.sh`) instead of a baked-in literal.

- [PR #67](https://github.com/zscaler/zscaler-mcp-server/pull/67) - **AWS deploy script UX.** Step 7 (Architecture) is now always interactive with a numeric `[1] [2] [3]` prompt that matches the Azure / GCP scripts — `.env` values become the default selection rather than silently skipping the question. Added colour-coded prompts (`[recommended]` / `[experimental]` tags, step headers) and a live spinner with elapsed time during the CloudFormation stack wait. Colour and spinner auto-disable on non-TTY stdout. `docs/deployment/amazon_bedrock_agentcore.md` updated.

## 0.12.1 (May 16, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Bug Fixes

- [PR #66](https://github.com/zscaler/zscaler-mcp-server/pull/66) - Fixed `get_combined_user_agent` and `get_mcp_user_agent` reporting stale hardcoded versions (e.g. `0.3.1`) on source-only runs where `importlib.metadata` can't find an installed distribution. Both helpers now fall back to `zscaler_mcp.__version__` (kept in sync with `pyproject.toml` by `scripts/set-version.sh`) instead of a baked-in literal.

### Documentation

- [PR #66](https://github.com/zscaler/zscaler-mcp-server/pull/66) - Updated Azure and GCP integration documentation. Included links to demo videos.

## 0.12.0 (May 15, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Breaking Changes

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - Removed the `clientless_app_ids` parameter from `zpa_create_application_segment` and `zpa_update_application_segment`. The field is only meaningful for Browser Access segments and previously triggered a stray `BROWSER_ACCESS` lookup when passed against a standard segment. Browser Access workloads are now served by the dedicated `zpa_*_application_segment_ba` tools (see below); use those instead.

### Enhancements

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - **HTTP transport hardening middleware.** Added two ASGI pre-processor middlewares wired in as the outermost wrapper around every HTTP transport (streamable-http + SSE), running *before* `AuthMiddleware` and `SourceIPMiddleware`. `StripTrailingSlashMiddleware` rewrites `POST /mcp/` to `POST /mcp` so clients that can't follow a 307-on-POST (Gemini CLI, custom LangChain agents, hand-written JSON-RPC clients) work out-of-the-box. `NormalizeContentTypeMiddleware` rewrites the deprecated `Content-Type: application/json-rpc` to the spec-compliant `application/json` (preserving `; charset=...`). Both are pure pre-processors — no new dependencies, never short-circuit, compliant clients (Claude Desktop, Cursor) unaffected. Exposed via `apply_transport_hardening(app, transport)` in `zscaler_mcp/auth.py`; 20 unit tests in `tests/test_transport_hardening.py`. Mirrored to the AWS variant.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - **Auto-publish to MCP Registry.** Every push to `master` that produces a semantic-release now also pushes the freshly-bumped `server.json` to `https://registry.modelcontextprotocol.io` so downstream catalogs (GitHub MCP Registry, MCP-aware clients) reflect the new version without manual intervention. Implemented as a new `mcp-registry-publish` job in `.github/workflows/release.yml` gated on `cycjimmy/semantic-release-action`'s `new_release_published` output, checking out the new tag (`v${new_release_version}`), and authenticating via short-lived **GitHub OIDC** (`id-token: write`, scoped to this job only — no PAT, no long-lived secret). Non-fatal failure mode: if the registry push fails, PyPI and the GitHub Release have already happened and operators can fall back to the manual `mcp-publisher publish` flow documented in `integrations/github/README.md`.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - Added **ZIA Mobile Advanced Threat Settings** management tools: `zia_get_mobile_advanced_settings`, `zia_update_mobile_advanced_settings`. Backed by `zscaler.zia.mobile_threat_settings.MobileAdvancedSettingsAPI`. Tenant-wide singleton governing the *Mobile Malware Protection* policy applied to traffic from mobile clients (iOS / Android via the Zscaler Client Connector) — 8 boolean knobs for blocking apps with malicious activity, apps with known vulnerabilities, apps leaking unencrypted credentials / location / PII / device IDs, apps beaconing to known ad websites, and apps communicating with unknown remote servers. PUT-replace update contract (SDK forwards as `**kwargs`); call `zia_activate_configuration` afterwards. Lands in a new **`zia_threat_settings`** toolset (`default=True`), kept distinct from `zia_advanced_settings` / `zia_atp_policy` / `zia_atp_malware` so the mobile threat surface can be enabled / audited independently. Implementation in `zscaler_mcp/tools/zia/mobile_threat_settings.py`.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - Added **ZPA Service Edges** management tools: `zpa_list_service_edges`, `zpa_get_service_edge`, `zpa_update_service_edge`, `zpa_delete_service_edge`, `zpa_bulk_delete_service_edges`. Backed by `zscaler.zpa.service_edges.ServiceEdgeControllerAPI`. These wrap the *individual* service edge instances (the cloud-hosted broker process running on a specific host), distinct from `zpa_*_service_edge_group*` (the parent group) and `zpa_*_provisioning_key*` (the bootstrap tokens used to enroll edges into a group). The list tool returns runtime status, version, location, enrollment cert, and `serviceEdgeGroupId`; update uses the SDK's `**kwargs`-passthrough semantics (no full-replace silent backfill); single delete and `bulk_delete` are HMAC double-confirmed since each removed edge must be re-provisioned. All 5 tools land in the existing `zpa_service_edge_groups` toolset via the existing `_service_edge` prefix rule — no per-tool overrides needed. Implementation in `zscaler_mcp/tools/zpa/service_edges.py`.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - **Process lifecycle management.** New CLI subcommands `zscaler-mcp reload`, `zscaler-mcp restart`, `zscaler-mcp status`, `zscaler-mcp stop` let operators reconfigure a running server (locally or in a container) without recreating the container. The running server writes a JSON PID file at `/var/run/zscaler-mcp.pid` (with sensible fallbacks; per-instance override via `--pid-file` / `ZSCALER_MCP_PID_FILE`) and installs two signal handlers — **SIGHUP** for soft reload (re-reads `.env`, MCP sessions survive) and **SIGUSR2** for hard restart (re-reads `.env`, then `os.execvp`'s a fresh interpreter with the original argv — same PID, fresh memory, fresh env, sessions die). SIGTERM/SIGINT are deliberately left un-handled so `docker stop` / `systemctl stop` / Ctrl+C keep their standard semantics; `zscaler-mcp stop` simply sends SIGTERM. New `--dotenv-path` / `ZSCALER_MCP_DOTENV_PATH` lets operators point at an arbitrary `.env`; the resolved path is recorded in the PID file so reload/restart re-read the same source. The `scripts/setup-mcp-server.py` setup script now defaults to bind-mounting the host `.env` at `/app/.env` (with `--legacy-env-file` to opt back into the snapshot-only behaviour), so `docker exec <container> zscaler-mcp restart` picks up host-side `.env` edits without recreating the container. Implementation in `zscaler_mcp/lifecycle.py`.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - Added **ZIA Custom IPS Signature Rules** management tools: `zia_list_ips_signature_rules`, `zia_get_ips_signature_rule`, `zia_create_ips_signature_rule`, `zia_update_ips_signature_rule`, `zia_delete_ips_signature_rule`. Backed by `zscaler.zia.ips_signature_rules.IPSSignatureRulesAPI`. Snort / Suricata-style detection signatures (the "what to detect" surface) — distinct from the existing Cloud Firewall IPS *policy* rule family (the "when to enforce" surface), but loaded together in the `zia_cloud_firewall` toolset because admins working on intrusion prevention typically need both. Create inherits the SDK's pre-flight validation against the dynamic-validation endpoint (syntactic / semantic / duplicate-`sid` errors raise without leaving a stub on the tenant). Update is PUT-replace with silent backfill of `name` + `rule_text` (the load-bearing pair for this resource — IPS signatures have no `order`). Delete is HMAC double-confirmed. Implementation in `zscaler_mcp/tools/zia/ips_signature_rules.py`.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - Added **ZIA Advanced Settings** management tools: `zia_get_advanced_settings`, `zia_update_advanced_settings`. Backed by `zscaler.zia.advanced_settings.AdvancedSettingsAPI`. Wraps the tenant-wide *Administration → Advanced Settings* singleton — ~50 knobs covering authentication / Kerberos / digest bypass URLs and apps, DNS optimization on transparent proxy (IPv4 + IPv6 with include + exempt lists), Office 365 one-click, UI session timeout, surrogate IP enforcement, HTTP tunnel tracking, domain-fronting block, HTTP/2 non-browser traffic, ECS-for-all, dynamic user risk, CONNECT-host / SNI mismatch handling, and SIPA XFF header insertion. PUT-replace update contract (SDK forwards as `**kwargs`); call `zia_activate_configuration` afterwards. Lands in a new **`zia_advanced_settings`** toolset (`default=True`). Implementation in `zscaler_mcp/tools/zia/advanced_settings.py`.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - Added **ZIA Advanced Threat Protection — Malware Protection Policy** management tools: `zia_get_atp_malware_policy`, `zia_update_atp_malware_policy`, `zia_get_atp_malware_inspection`, `zia_update_atp_malware_inspection`, `zia_get_atp_malware_protocols`, `zia_update_atp_malware_protocols`, `zia_get_malware_settings`, `zia_update_malware_settings`. Backed by `zscaler.zia.malware_protection_policy.MalwareProtectionPolicyAPI`. The four tool pairs expose the tenant-wide malware singletons that sit alongside the ATP policy block: file-handling toggles (`block_unscannable_files`, `block_password_protected_archive_files`), traffic-direction inspection (`inspect_inbound`, `inspect_outbound`), protocol-level inspection (`inspect_http`, `inspect_ftp_over_http`, `inspect_ftp`), and the 16-field threat-class block (virus / trojan / worm / adware / spyware / ransomware / remote-access tool / unwanted-applications, each with a matching `*_capture` PCAP toggle). All updates are PUT-replace; `zia_update_atp_malware_protocols` re-fetches after the PUT to shield clients from a known SDK response-parsing bug. All 8 tools land in a new **`zia_atp_malware`** toolset (`default=True`). Implementation in `zscaler_mcp/tools/zia/atp_malware_protection.py`.

- [PR #65](https://github.com/zscaler/zscaler-mcp-server/pull/65) - **Housekeeping: ATP tool-module consolidation.** Merged `atp_malicious_urls.py` into `atp_settings.py` so every tool backed by `zscaler.zia.atp_policy.ATPPolicyAPI` lives in a single module (7 tools), and renamed the new malware file from `malware_protection.py` to `atp_malware_protection.py` for symmetry. No tool names, signatures, toolset assignments, or behavior changed — pure file-organization cleanup that establishes the convention **one SDK API class → one MCP module → one logical surface**.

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - Added **ZPA Browser Access (BA) application segment** management tools: `zpa_list_application_segments_ba`, `zpa_get_application_segment_ba`, `zpa_create_application_segment_ba`, `zpa_update_application_segment_ba`, `zpa_delete_application_segment_ba`. Backed by `client.zpa.app_segments_ba_v2` and uniformly suffixed `_ba` so agents can disambiguate them from the regular and PRA app-segment tools. Each BA segment carries a `common_apps_dto.apps_config` block with per-domain TLS certificate, port, and protocol (`HTTP`/`HTTPS`); the tools validate `apps_config` against the segment's `domain_names` before sending to avoid the generic ZPA error returned when domains drift. New `skills/zpa/application_segment-ba-onboard/SKILL.md` walks the full dependency chain (connector group → server group → segment group → BA TLS cert → BA segment → access policy rule).

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - Added **ZPA Privileged Remote Access (PRA) application segment** management tools: `zpa_list_application_segments_pra`, `zpa_get_application_segment_pra`, `zpa_create_application_segment_pra`, `zpa_update_application_segment_pra`, `zpa_delete_application_segment_pra`. Backed by `client.zpa.app_segments_pra` and uniformly suffixed `_pra`. Each PRA segment publishes RDP and SSH targets through the PRA portal without requiring a native client or Zscaler Client Connector; `apps_config` carries per-target domain, port, `application_protocol` (`RDP`/`SSH`), and the RDP `connection_security` mode. New `skills/zpa/application_segment-pra-onboard/SKILL.md` walks the full dependency chain including `pra_credential` and `pra_portal` provisioning.

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - Renamed the **ZPA application-onboarding skill** from `skills/zpa/onboard-application/SKILL.md` to `skills/zpa/application_segment-onboard/SKILL.md` for symmetry with the new BA / PRA onboarding skills. The three skills now form a coherent set keyed on the segment style the admin actually wants: `application_segment-onboard` (standard client-routed), `application_segment-ba-onboard` (Browser Access), `application_segment-pra-onboard` (RDP/SSH via PRA portal).

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - Added **ZCC One-Time Password (OTP) bundle** read tool: `zcc_get_device_otp`. Wraps `client.zcc.secrets.get_otp` and returns the full per-device OTP bundle — `logout_otp` (One-Time Logout Password), `exit_otp`, `uninstall_otp`, `revert_otp`, and the per-service disable OTPs (`zia_disable_otp`, `zpa_disable_otp`, `zdx_disable_otp`, `zdp_disable_otp`, `anti_tempering_disable_otp`, `deception_settings_otp`). Single SDK call serves every OTP workflow (logout, uninstall, exit, temporary service disable). New `skills/zcc/generate-logout-otp/SKILL.md` walks the typical admin flow (user identifier → device lookup → confirmation → OTP retrieval → secure delivery) and treats every returned value as a sensitive short-lived credential.

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - Added `scripts/setup-mcp-server.py` — a single interactive entry point for local Docker-based deployment of the MCP server. Prompts the admin through authentication mode (`jwt`, `zscaler`, `api-key`, `oidcproxy`, `none`), transport (`streamable-http` or `stdio`), credentials (loaded from `.env` or entered interactively), Docker image pull, container start, endpoint verification, and **auto-detection of 7 AI agents** (Claude Desktop, Claude Code, Cursor, Gemini CLI, VS Code, Windsurf, GitHub Copilot CLI) with an opt-in offer to write the matching `mcpServers` entry into each detected agent's config. Idempotent on re-run; rejects invalid combinations (e.g. `stdio` + any HTTP-bound auth mode) at the prompt. Companion `scripts/README.md` documents the flag matrix, env-file handling, agent config paths per OS, and a troubleshooting table.

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - GCP deploy operations (`integrations/google/gcp/gcp_mcp_operations.py`): `_mint_bearer_token` now supports both **Auth0-style** (JSON body, inline `client_id`/`client_secret`, audience claim) and **generic OAuth2** (form-encoded body, HTTP Basic auth, scope-based) token-minting flows. Detection is driven by the presence of a `token_scope` on the credentials dict; either flavour works against Auth0, Cognito, Entra ID, Okta, and Ping without code changes. New `_print_cloud_run_logs` helper renders `gcloud logging read` output Python-side as chronological, color-coded, single-line entries (24 h window by default) — gives a `tail`-style experience for Cloud Run troubleshooting.

- [PR #63](https://github.com/zscaler/zscaler-mcp-server/pull/63) - [Issue #61](https://github.com/zscaler/zscaler-mcp-server/issues/61) — Added **ZIA Advanced Threat Protection (ATP) policy** management tools: `zia_get_atp_settings`, `zia_update_atp_settings`, `zia_get_atp_security_exceptions`, `zia_update_atp_security_exceptions`. Backed by `zscaler.zia.atp_policy.ATPPolicyAPI`. The settings tool exposes the full ATP policy block (50+ knobs across command-and-control, malware, browser exploits, phishing, blocked countries, BitTorrent / Tor / crypto-mining, DGA domains, ad/spyware sites, and per-threat capture toggles) and the security-exceptions tool manages the tenant-wide bypass URL list. Both updates are PUT-replace; tools document the fetch-merge-write workflow and remind callers to run `zia_activate_configuration` afterwards.

- [PR #63](https://github.com/zscaler/zscaler-mcp-server/pull/63) - **ZDX toolset reorganization: 5 new dedicated toolsets** replacing the single catch-all `zdx` toolset. New toolsets (all `default=True` so the prior "everything zdx loads at startup" behaviour is preserved for `--toolsets default` and the no-selection fallback): `zdx_alerts` (active + historical alerts, single-alert get, affected devices), `zdx_locations` (administration operand catalog — locations and departments, the scope filters used by every other ZDX query via `location_id` / `department_id`), `zdx_software_inventory` (list software, get software details), `zdx_reports` (device inventory, every `zdx_application_*` tool, application users, device-level web-probe / cloudpath-probe results), and `zdx_troubleshooting` (the only ZDX surface with write tools — deep-trace + analysis lifecycle including start/stop, deep-trace events, top processes, web-probe metrics, cloudpath metrics, cloudpath topology, and health metrics). Routing uses dedicated prefix rules in `_TOOLSET_PREFIX_RULES` placed at the top of the rule list and scoped to `n.startswith("zdx_")` so they win against broader ZIA predicates (`_location`, `_device`) — a side-effect is that `zdx_list_locations` is no longer incidentally resolved to `zia_locations`. Migration: operators selecting toolsets explicitly via `--toolsets` / `ZSCALER_MCP_TOOLSETS` should replace `zdx` with the new toolset ids (or use `--toolsets default` for the full set).

- [PR #63](https://github.com/zscaler/zscaler-mcp-server/pull/63) - **Toolset reorganization: 17 new dedicated resource-family toolsets** so each Zscaler resource family lives in its own bucket instead of being absorbed into a catch-all. New ZIA toolsets: `zia_atp_policy` (all 7 tools backed by `zscaler.zia.atp_policy.ATPPolicyAPI` — the four new ATP settings/security-exception tools plus the existing `zia_*_atp_malicious_urls`), `zia_devices` (split from `zia_users`), `zia_authentication_settings` (cookie-auth exempt URLs, split from `zia_url_categories`), `zia_rule_labels` (split from `zia_admin`). New ZPA toolsets: `zpa_access_policies` (split from `zpa_policy`; the other policy-rule families remain there), `zpa_segment_groups` and `zpa_server_groups` (split from `zpa_app_segments` since both are shared operands referenced by application segments AND access policy rules), `zpa_service_edge_groups` and `zpa_provisioning_keys` (split from `zpa_connectors`), `zpa_app_connector_groups` (split from `zpa_connectors`; individual app connectors and `get_zpa_enrollment_certificate` stay there), `zpa_application_servers`, `zpa_ba_certificates`, `zpa_pra` (credentials + portals) all split from `zpa_misc`, plus `zpa_isolation`, `zpa_posture`, `zpa_trusted_networks` split from `zpa_idp`, and `zpa_app_protection` split from `zpa_misc`. Routing uses carefully ordered prefix rules (e.g. `_app_connector_group` precedes `_app_connector`, `_application_server` precedes `_application_segment`) so future tools auto-route correctly. Operators selecting toolsets explicitly via `--toolsets` may need to add the new ids; the `--toolsets default` set still includes the new toolsets that absorbed previously-default-on tools (`zia_atp_policy`, `zia_devices`, `zia_authentication_settings`, `zia_rule_labels`, `zpa_access_policies`, `zpa_segment_groups`, `zpa_server_groups`, `zpa_service_edge_groups`, `zpa_provisioning_keys`, `zpa_app_connector_groups`) so every tool that was previously default-on remains default-on.

- [PR #60](https://github.com/zscaler/zscaler-mcp-server/pull/60) - Added **ZPA Log Streaming Service (LSS)** read-only tools: `zpa_list_lss_configs`, `zpa_get_lss_config`, `zpa_list_lss_log_types`, `zpa_get_lss_log_format`, `zpa_list_lss_status_codes`, `zpa_list_lss_client_types`. Cover the configuration-only LSS surface (the API does not stream or query log content; that ships from the LSS Connector to the SIEM out-of-band). Implementation in `zscaler_mcp/tools/zpa/lss.py`.

- [PR #60](https://github.com/zscaler/zscaler-mcp-server/pull/60) - Added new ZPA skill `zpa/audit-baseline-compliance` — a fully read-only audit of a ZPA tenant against the Zscaler ZPA Baseline Recommendations v1.0 document. Inventories the tenant via `zpa_list_*`/`zpa_get_*` tools, scores ~26 configuration-only checks across 7 categories (Connectors, Server Groups, Segments, Access Policy, Forwarding Policy, Timeout Policy, LSS), and renders the result as an interactive Cursor Canvas styled like the Zscaler portal — searchable, filterable by category and severity, with per-finding evidence and remediation. Surfaces 5 "Cannot Audit" observability gaps (per-connector telemetry, app probes, LSS delivery, bandwidth, sessions) so missing telemetry APIs are tracked rather than silently skipped. Surface-aware: emits a Cursor Canvas when running in Cursor (delegates to the built-in canvas skill) and an inline structured Markdown report on Claude Code, Gemini CLI, and Copilot.

- [PR #60](https://github.com/zscaler/zscaler-mcp-server/pull/60) - Enhanced six existing ZPA skills with rationale and ordering guidance from the ZPA Baseline Recommendations v1.0 document: `zpa/application_segment-onboard` (Step 0 classification table — Standard / Sensitive / Global / Discovery / SIPA — driving correct `health_reporting` defaults per class); `zpa/create-server-group` (5-pattern selector + `dynamic_discovery` anti-patterns); `zpa/create-access-policy-rule` (8-class taxonomy from doc §A–H + per-OS posture-block gotcha); `zpa/create-forwarding-policy-rule` (allow-list mindset + canonical bypass list for Microsoft / Apple / OCSP / CRL / EDR); `zpa/create-timeout-policy-rule` (baseline auth-timeout `24h–7d` and per-class idle-timeout values); `zpa/troubleshoot-app-connector` (config-only pre-flight checks with explicit acknowledgement that ZPA does not expose runtime connector telemetry).

### Documentation

- [PR #64](https://github.com/zscaler/zscaler-mcp-server/pull/64) - `docs/deployment/amazon_bedrock_agentcore.md` — added a new **"Connecting MCP clients to the Gateway (Claude / Cursor / Inspector)"** section covering how to point any MCP-compatible client at the AgentCore Gateway's standard streamable-HTTP endpoint. Walks through bearer-token minting (Auth0 M2M example), `Authorization: Bearer <token>` wiring, and end-to-end smoke testing against the Gateway from Claude Desktop, Cursor, and the MCP Inspector. TOC updated to surface the new section.

- [PR #60](https://github.com/zscaler/zscaler-mcp-server/pull/60) - Added `local_dev/Zlive/zpa-baseline-skills-analysis.md` — a focused execution plan reflecting the read-only audit-first direction for ZPA baseline-compliance work, including the hard constraints set by the ZPA API surface (no telemetry API, configuration-only LSS, deception is a tenant feature flag, microtenant CRUD out of scope) and the explicit list of "Cannot Audit" gaps that should drive future API requests.

---
``Last updated: v0.11.0``

---

## Changelog

## 0.11.0 (May 4, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Breaking Changes

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - **Removed legacy per-service authentication.** OneAPI is now the only supported authentication mode. The `ZSCALER_USE_LEGACY` environment variable, the `use_legacy` parameter on every tool, the per-service legacy clients (`LegacyZPAClient`, `LegacyZIAClient`, `LegacyZCCClient`, `LegacyZTWClient`, `LegacyZDXClient`), and the per-service credential blocks (`ZPA_*`, `ZIA_*`, `ZCC_*`, `ZTW_*`, `ZDX_*`) have all been removed. To migrate: configure `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET` (or `ZSCALER_PRIVATE_KEY`), `ZSCALER_VANITY_DOMAIN`, and `ZSCALER_CUSTOMER_ID` (the last is required only when calling ZPA tools), and drop any `use_legacy=true` arguments from your MCP tool calls.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - **Removed the `zcc_devices_csv_exporter` tool.** Tool registration was already removed in PR #38; this release deletes the tool module, unit tests, the e2e fixture, and all remaining references in documentation. Use `zcc_list_devices` for device inventory queries.

### Enhancements

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - **Toolsets.** Tools are now grouped into 29 logical toolsets across every service. Select via `--toolsets` / `ZSCALER_MCP_TOOLSETS` (`default`, `all`, or explicit ids). Three always-on discovery meta-tools (`zscaler_list_toolsets`, `zscaler_get_toolset_tools`, `zscaler_enable_toolset`) let agents enumerate and runtime-enable additional toolsets. Per-toolset system instructions are composed into the server's `instructions` field at startup. Filter precedence: `disabled_tools` > toolset > `enabled_tools` > `write_tools`. See `docs/guides/toolsets.md`.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - **OneAPI entitlement filter.** At startup the server decodes the OneAPI bearer token and intersects active toolsets with the products the token is entitled to call, hiding tools that would only ever return `401 Unauthorized`. Non-fatal on every failure path. Opt-out via `--no-entitlement-filter` / `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true`.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - **Output sanitization.** Every tool result is passed through a three-stage sanitizer before reaching the LLM: invisible / control-character stripping (BiDi overrides, zero-width spaces, BOM), HTML / Markdown sanitization (tags + comments stripped, link/image syntax neutralised), and code-fence info-string filtering (`system`, `assistant`, `tool`, `ignore` rewritten to `text`). Defends against prompt-injection payloads embedded in Zscaler resource names / descriptions. Opt-out via `ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION=true`.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - **Tool annotations.** Read tools now carry `readOnlyHint=True`; write tools carry `destructiveHint=True`. AI-agent permission frameworks (Claude Desktop, Cursor) consume these to prompt for confirmation on destructive actions.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - **Auto-generated tool documentation.** New `--generate-docs` and `--check-docs` CLI flags (and `make generate-docs` / `make check-docs`) regenerate marker-bounded regions of `docs/guides/supported-tools.md`, `README.md`, and `docs/guides/toolsets.md` from the live tool inventory. CI runs `--check-docs` before tests to fail builds on stale docs.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - Added **ZIA Time Intervals** management tools (`zia_list_time_intervals`, `zia_get_time_interval`, `zia_create_time_interval`, `zia_update_time_interval`, `zia_delete_time_interval`). Reusable schedule objects referenced by all ZIA rule types via the `time_windows` field.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - Added **ZIA Workload Groups** read tools (`zia_list_workload_groups`, `zia_get_workload_group`).

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - Added the **ZIA Cloud App Control rule** family (`zia_list_cloud_app_control_rules`, `zia_get_cloud_app_control_rule`, `zia_create_cloud_app_control_rule`, `zia_update_cloud_app_control_rule`, `zia_delete_cloud_app_control_rule`, `zia_list_cloud_app_control_actions`). `rule_type` is required on every CRUD call. Cloud-application name auto-resolution is wired in.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - Added new ZIA skills: `create-firewall-filtering-rule`, `create-ssl-inspection-rule`, `create-url-filtering-rule`, `create-cloud-app-control-rule`, `manage-time-interval`, `look-up-rule-targets`. Renamed `resolve-cloud-app-enum` → `look-up-cloud-app-name`.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - Added new ZPA skills: `create-conditional-access-rule`, `create-session-duration-rule`. Updated `create-forwarding-policy-rule` and `create-timeout-policy-rule`.

### Bug Fixes

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - [Issue #58](https://github.com/zscaler/zscaler-mcp-server/issues/58) — `zpa_create_application_segment` and `zpa_update_application_segment` now expose 16 SDK-supported fields that were previously dropped: `icmp_access_type`, `double_encrypt`, `config_space`, `ip_anchored`, `bypass_on_reauth`, `inspect_traffic_with_zia`, `use_in_dr_mode`, `tcp_keep_alive`, `select_connector_close_to_app`, `match_style`, `adp_enabled`, `auto_app_protect_enabled`, `api_protection_enabled`, `fqdn_dns_check`, `weighted_load_balancing`, `extranet_enabled`. Enum-typed fields use `Literal` for agent-side validation; all fields default to `None` so omitting them preserves existing API values on update.

### Documentation

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - New `docs/guides/toolsets.md` covering toolset selection, filter precedence, the OneAPI entitlement filter, per-toolset system instructions, the runtime discovery tools, and contributor steps for adding a new toolset.

- [PR #59](https://github.com/zscaler/zscaler-mcp-server/pull/59) - `CLAUDE.md` and `README.md` refreshed for OneAPI-only auth and the new toolset / sanitization / entitlement-filter env vars.

## 0.10.1 (April 11, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Features

[PR #48](https://github.com/zscaler/zscaler-mcp-server/pull/48) - Aligned **Cursor Marketplace plugin** with official plugin-template standards. Fixed `category` to `developer-tools`, moved logo to `assets/`, added `marketplace.json` for validation compatibility, declared required Zscaler OneAPI env vars in `mcp.json`, and added `name` frontmatter to all 20 command files. Plugin now passes Cursor's `validate-template.mjs` checklist.

[PR #48](https://github.com/zscaler/zscaler-mcp-server/pull/48) - Added 7 **Cursor rules** (`.mdc` files) covering tool naming conventions, ZIA activation requirement, ZPA dependency chain, write operation safety, ZDX read-only conventions, ZMS GraphQL patterns, and cross-service data overlap.

## 0.8.1 (April 6, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Features

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Added **JMESPath client-side filtering** across all 88 list tools spanning 9 services (ZIA, ZPA, ZDX, ZCC, ZTW, ZID, EASM, ZINS, ZMS). Every list tool now accepts an optional `query` parameter for server-side filtering and projection of API results before they reach the AI agent.

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Added `zscaler_search_tools` meta-tool for AI agent tool discovery. Supports filtering by `service`, `name_contains`, `description_contains`, and advanced JMESPath queries against the full tool registry. Returns tool name, description, service, and type (read/write) for each match.

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Added **tool-call audit logging** via `--log-tool-calls` CLI flag or `ZSCALER_MCP_LOG_TOOL_CALLS` environment variable. Logs tool name, sanitized arguments, execution duration, and result summary for every tool invocation. Sensitive parameters (passwords, secrets, tokens) are automatically redacted.

### Enhancements

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Added **ZMS GraphQL filtering and ordering** to 6 tool domains: resources, resource groups, policy rules, app zones, app catalog, and tags. Tools now accept `filter_by` parameters (name, status, resource_type, cloud_provider, cloud_region, platform_os) and `sort_order` for server-side query refinement.

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Added 3 new ZMS guided skills: `review-tag-classification` (tag namespace hierarchy analysis), `analyze-policy-rules` (policy rule optimization and conflict detection), and `assess-workload-protection` (workload coverage and agent health assessment).

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Created centralized JMESPath utility module (`zscaler_mcp/common/jmespath_utils.py`) shared across all services, with graceful error handling for invalid expressions and consistent return normalization.

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Added `jmespath>=1.0.0` as an explicit dependency in `pyproject.toml`.

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Updated all 88 list tool descriptions in `services.py` to advertise JMESPath `query` parameter support for AI agent discoverability.

### Documentation

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Updated `CLAUDE.md` with JMESPath client-side filtering architecture, syntax reference, cross-service examples, and `zscaler_search_tools` usage patterns.

[PR #45](https://github.com/zscaler/zscaler-mcp-server/pull/45) - Updated `CLAUDE.md` with tool-call audit logging section covering CLI flag, environment variable, log format, sensitive parameter redaction, and result summarization.

## 0.7.2 (March 27, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Features

[PR #41](https://github.com/zscaler/zscaler-mcp-server/pull/41) - Added **ZMS (Zscaler Microsegmentation)** service with read-only GraphQL-backed tools: agents, agent groups, resources, resource groups, policy rules (including default rules), app zones, app catalog, nonces (provisioning keys), and tags. Requires `ZSCALER_CUSTOMER_ID` and OneAPI credentials.

[PR #41](https://github.com/zscaler/zscaler-mcp-server/pull/41) - Renamed **ZIdentity** service to **ZID** and **Z-Insights** service to **ZINS** to align with `zscaler-sdk-python` (`client.zid`, `client.zins`). Tool prefixes are now `zid_*` and `zins_*`; registry keys are `zid` and `zins`.

### Enhancements

[PR #41](https://github.com/zscaler/zscaler-mcp-server/pull/41) - Added guided **skills** for ZINS (`analyze-web-traffic`, `audit-shadow-it`, `assess-network-security`) and ZMS (`audit-microsegmentation-posture`, `troubleshoot-agent-deployment`), plus expanded ZMS skill content using the Microsegmentation API GraphQL schema reference (Query vs Mutation, managed/unmanaged/recommended resource groups, error handling).

[PR #41](https://github.com/zscaler/zscaler-mcp-server/pull/41) - **Dockerfile** (temporary dev path): optional install of a local `zscaler_sdk_python` tarball after `uv sync` to test against an unpublished SDK build; **`.dockerignore`** exception so `local_dev/zscaler_sdk_python-*.tar.gz` is included in the build context.

### Fixes

[PR #41](https://github.com/zscaler/zscaler-mcp-server/pull/41) - **CWE-345 — HMAC confirmation token replay vulnerability.** Fixed 31 delete operations across ZPA, ZIA, and ZTW that passed empty parameters (`{}`) to `check_confirmation()`, producing fungible HMAC-SHA256 tokens that could be replayed across different resources of the same type. All delete operations now bind the specific resource identifier into the HMAC payload, preventing cross-resource token replay. Added 6 regression tests including AST-based static analysis to prevent future occurrences.

[PR #41](https://github.com/zscaler/zscaler-mcp-server/pull/41) - Resolved **ruff** `I001` import-sorting issues in ZMS tool modules, `services.py` (ZMSService imports), and ZMS tests.

### Documentation

[PR #41](https://github.com/zscaler/zscaler-mcp-server/pull/41) - Updated `CLAUDE.md`, `README.md`, `docs/guides/supported-tools.md`, `codecov.yml`, Sphinx `docsrc/`, integrations, and tests for ZMS, ZID, and ZINS naming.

## 0.7.1 (March 26, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Features

[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Added `--disabled-tools` CLI flag and `ZSCALER_MCP_DISABLED_TOOLS` environment variable to exclude specific tools from registration. Supports `fnmatch` wildcard patterns (e.g., `zcc_list_*` disables all ZCC list tools).
[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Added `--disabled-services` CLI flag and `ZSCALER_MCP_DISABLED_SERVICES` environment variable to exclude entire services from loading. Accepts service names: `zcc`, `zdx`, `zia`, `zpa`, `ztw`, `zid`.
[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Combined `--disabled-tools` and `--disabled-services` for fine-grained control: disable an entire service to prevent loading, or selectively exclude individual tools while keeping the rest of the service active.

### Enhancements

[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Removed `zcc_devices_csv_exporter` tool — `zcc_list_devices` already returns equivalent data without file I/O overhead.
[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Added `verify_id_token=True` to OIDCProxy setup for cross-platform compatibility. Auth0 may return opaque access tokens that fail JWT validation on certain platforms (e.g., Windows Docker). Verifying the OIDC `id_token` instead ensures consistent behavior across macOS and Windows.
[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Added `--debug` CLI flag to `setup-oidcproxy-auth.py` for verbose token validation diagnostics (`FASTMCP_DEBUG=true`).
[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Added Step 2b to `setup-oidcproxy-auth.py` to clear stale `mcp-remote` OAuth caches and orphaned processes before server start, preventing `EADDRINUSE` and `invalid_token` errors after container restarts.

### Documentation

[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Updated README with "Excluding Services and Tools" section documenting `fnmatch` wildcard syntax and combined usage examples.
[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Updated Authentication & Deployment Guide with troubleshooting entry for persistent 401 `invalid_token` on Windows Docker.
[PR #38](https://github.com/zscaler/zscaler-mcp-server/pull/38) - Added tip about prompt specificity for large tool catalogs.

## 0.7.0 (March 25, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### 🔐 MCP Client Authentication

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added multi-mode authentication for MCP clients connecting over HTTP transports (`sse`, `streamable-http`). Authentication is disabled by default for backward compatibility and does not apply to `stdio` transport.

**Four authentication modes:**

- **`api-key`** — Simple shared secret. Client sends `Authorization: Bearer <key>`. Best for quick setup and internal environments.
- **`jwt`** — External Identity Provider via JWKS. Tokens are validated locally using the IdP's public keys. Supports Auth0, Okta, Azure AD, Keycloak, AWS Cognito, PingOne, and Google Cloud Identity.
- **`zscaler`** — Zscaler OneAPI credential validation. Client sends Basic Auth (`client_id:client_secret`) or custom headers (`X-Zscaler-Client-ID` / `X-Zscaler-Client-Secret`). Server validates against Zscaler's `/oauth2/v1/token` endpoint.
- **`auth=` parameter** — Library-level OAuth 2.1 with Dynamic Client Registration. Pass a `fastmcp.server.auth.AuthProvider` (e.g. `OIDCProxy`, `OAuthProxy`) directly to `ZscalerMCPServer(auth=...)`. Works with any OIDC-compliant IdP. Addresses [#33](https://github.com/zscaler/zscaler-mcp-server/issues/33).

**Architecture:**

- Implemented as ASGI middleware (`zscaler_mcp/auth.py`) that wraps HTTP transport apps before they reach FastMCP
- Two independent security layers: Layer 1 (MCP Client Auth) controls who can connect; Layer 2 (Zscaler API Auth) controls how the server authenticates to Zscaler APIs
- Zero overhead when authentication is disabled — middleware returns the app unchanged
- When `auth=` is provided, the server integrates the auth provider's OAuth routes and middleware directly into the HTTP app, bypassing the env-var-based auth layer

### 🌐 Network Security

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added defense-in-depth network security controls for HTTP transports:

- **HTTPS / TLS Configuration** — Optional TLS termination at the server with `ZSCALER_MCP_TLS_CERT_FILE` and `ZSCALER_MCP_TLS_KEY_FILE`
- **HTTPS Policy Enforcement** — `ZSCALER_MCP_ALLOW_HTTP=false` (default) blocks plaintext HTTP on non-localhost interfaces when TLS is not configured
- **Host Header Validation** — `ZSCALER_MCP_ALLOWED_HOSTS` restricts accepted `Host` headers to prevent DNS rebinding attacks; auto-configured for localhost
- **Source IP Access Control** — `ZSCALER_MCP_ALLOWED_SOURCE_IPS` restricts which client IPs can connect (CIDR notation supported)

### 🔌 Platform Integrations

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added native platform integrations for AI development environments:

- **Claude Code Plugin** (`.claude-plugin/`) — Plugin manifest with marketplace support, 19 guided skills, and slash commands
- **Cursor Plugin** (`.cursor-plugin/`) — Plugin manifest with 19 guided skills for Cursor IDE
- **Gemini Extension** (`gemini-extension.json`, `GEMINI.md`) — Google Gemini CLI extension with contextual tool guidance
- **Google Cloud** (`integrations/google/`) — Unified GCP deployment script (Cloud Run, GKE, Compute Engine VM) with interactive CLI menus
- **Google ADK Agent** (`integrations/google/adk/`) — Google Agent Development Kit integration for building autonomous Zscaler security agents powered by Gemini models
- **Integration documentation** (`integrations/`) — Dedicated README per platform with installation, configuration, and verification instructions

### Enhancements

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added `--generate-auth-token` CLI argument for generating authorization tokens from configured credentials

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added `--write-tools`, `--user-agent-comment`, `--list-tools`, and `--version` CLI flags

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added `ZSCALER_MCP_CONFIRMATION_TTL` environment variable for configurable confirmation window on destructive operations

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added `ZSCALER_MCP_AUTH_ALGORITHMS` environment variable for restricting JWT validation algorithms

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added `docker-run-http`, `docker-stop`, and `docker-generate-auth-token` Makefile targets for HTTP transport and authentication workflows

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Added `PyJWT[crypto]>=2.8.0` dependency for JWT token validation

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Updated `.env.example` with MCP Client Authentication and network security environment variables

### Documentation

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Created comprehensive [Authentication & Deployment Guide](docs/deployment/authentication-and-deployment.md) covering:

- Transport modes and authentication architecture
- Detailed configuration for all four authentication modes
- IdP-specific JWKS setup instructions (Auth0, Okta, Azure AD, Keycloak, AWS Cognito, PingOne, Google)
- Docker and Python library deployment examples
- Client configuration examples for Claude Desktop, Cursor, Windsurf, VS Code, and generic MCP clients
- Token generation, expiry, and refresh workflows
- Environment variable reference and troubleshooting

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Updated `README.md` with MCP Client Authentication section, network security features, and Platform Integrations reference

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Created `integrations/README.md` as central index for all platform integrations

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Created dedicated integration READMEs: `integrations/claude-code-plugin/README.md`, `integrations/cursor-plugin/README.md`, `integrations/gemini-extension/README.md`, `integrations/kiro/README.md`

[PR #37](https://github.com/zscaler/zscaler-mcp-server/pull/37) - Updated Sphinx documentation portal (`docsrc/`) with platform integrations page and release notes for v0.7.0

## 0.6.2 (February 18, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Enhancements

[PR #29](https://github.com/zscaler/zscaler-mcp-server/pull/29) - Added new ZIA tools:

- `network_apps`
- `network_services_group`
- `network_services`
- `zia_url_lookup`
- `zia_list_cloud_app_control_actions`

[PR #29](https://github.com/zscaler/zscaler-mcp-server/pull/29) - Improved search capabilities in the ZIA tool:

- `device_management`

## 0.6.1 (December 16, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Enhancements

[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - ✨ Added Z-Insights Analytics service with 16 read-only tools for Zscaler analytics via GraphQL API
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_web_traffic_by_location` - Get web traffic analytics grouped by location
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_web_traffic_no_grouping` - Get overall web traffic volume metrics
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_web_protocols` - Get web traffic by protocol (HTTP, HTTPS, SSL)
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_threat_super_categories` - Get threat super categories (malware, phishing, spyware)
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_threat_class` - Get detailed threat class breakdown
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_cyber_incidents` - Get cybersecurity incidents by category
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_cyber_incidents_by_location` - Get cybersecurity incidents grouped by location
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_cyber_incidents_daily` - Get daily cybersecurity incident trends
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_cyber_incidents_by_threat_and_app` - Get incidents correlated by threat and application
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_firewall_by_action` - Get Zero Trust Firewall traffic by action (allow/block)
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_firewall_by_location` - Get firewall traffic grouped by location
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_firewall_network_services` - Get firewall network service usage
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_casb_app_report` - Get CASB SaaS application usage report
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_shadow_it_apps` - Get discovered shadow IT applications with risk scores
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_shadow_it_summary` - Get shadow IT summary statistics and groupings
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added `zins_get_iot_device_stats` - Get IoT device statistics and classifications

### Bug Fixes

[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Fixed Z-Insights time interval defaults - changed from invalid intervals (5-day, 12-day) to valid 7 or 14-day intervals required by the API
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Fixed Z-Insights tools to return structured "no data" responses instead of throwing exceptions when API returns empty results
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Fixed Z-Insights tools to handle GraphQL errors gracefully (checking response body for errors even with HTTP 200 status)
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Fixed Z-Insights time range validation to ensure `end_time` is at least 1 day in the past for data availability
[PR #22](https://github.com/zscaler/zscaler-mcp-server/pull/22) - Added auto-adjustment logic for Z-Insights time intervals to automatically correct invalid intervals to nearest valid 7 or 14-day interval

## 0.6.0 (December 8, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Enhancements

[PR #21](https://github.com/zscaler/zscaler-mcp-server/pull/21) - ✨ Added AWS Kiro Power integration for AI-assisted Zscaler platform management within the Kiro IDE. Includes POWER.md, mcp.json, and service-specific steering files for ZPA, ZIA, ZDX, ZCC, ZTW, EASM, and ZIdentity.

## 0.5.0 (November 22, 2025)

> **⚠️ Important:** This release contains enhancements specific to **AWS Bedrock AgentCore deployments only**. These changes are maintained in a separate private AWS-specific repository and do **not** modify the core Zscaler MCP Server in this repository. Standard MCP server functionality remains unchanged.

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Enhancements

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - 🔐 AWS Bedrock AgentCore Security Enhancements

**Container-Based Secrets Manager Integration:**

- Container retrieves Zscaler API credentials from AWS Secrets Manager at runtime
- **Zero credentials exposed** in AgentCore configuration, CloudFormation templates, or deployment scripts
- Secrets encrypted at rest with AWS KMS and in transit via TLS
- Full CloudTrail audit logging for all secret access
- Backward compatible - supports both Secrets Manager and direct environment variable approaches

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - **CloudFormation Automation:**

- One-click deployment via Launch Stack button
- Automated AgentCore runtime deployment with conditional secret creation
- IAM execution roles with Secrets Manager permissions automatically configured

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Added ZEASM (External Attack Surface Management) service with 7 read-only tools: `zeasm_list_organizations`, `zeasm_list_findings`, `zeasm_get_finding_details`, `zeasm_get_finding_evidence`, `zeasm_get_finding_scan_output`, `zeasm_list_lookalike_domains`, `zeasm_get_lookalike_domain`

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Updated README.md with EASM tools documentation

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Created EASM documentation in `docsrc/tools/easm/index.rst`

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Updated `docsrc/tools/index.rst` with EASM service reference

### Bug Fixes

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed ZDX `zdx_list_alerts` calling wrong SDK method (`alerts.read` → `alerts.list_ongoing`)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed ZDX `zdx_list_alert_affected_devices` calling wrong SDK method (`alerts.read_affected_devices` → `alerts.list_affected_devices`)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed ZDX `zdx_list_application_users` calling wrong SDK method (`apps.list_users` → `apps.list_app_users`)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed ZDX `zdx_get_application_user` calling wrong SDK method and incorrect return handling (`apps.get_user` → `apps.get_app_user`)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed ZDX `zdx_list_software` calling wrong SDK method and incorrect return handling (`inventory.list_software` → `inventory.list_softwares`)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed ZDX `zdx_get_software_details` calling wrong SDK method (`inventory.get_software` → `inventory.list_software_keys`)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed ZDX `zdx_get_device_deep_trace` incorrect return handling (SDK returns list, not single object)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed syntax error in `services.py` ZIdentityService (missing `description` key in tool registration)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed EASM tools incorrect `use_legacy` parameter handling (removed invalid syntax)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Fixed `ZSCALER_CUSTOMER_ID` incorrectly required for non-ZPA services (now only required for ZPA)

[PR #20](https://github.com/zscaler/zscaler-mcp-server/pull/20) - Updated ZDX unit tests to match corrected SDK method names (42 tests)

## 0.4.0 (November 19, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Enhancements

[PR #16](https://github.com/zscaler/zscaler-mcp-server/pull/16) - Split the ZIA sandbox helper into dedicated tools (`zia_get_sandbox_quota`, `zia_get_sandbox_behavioral_analysis`, `zia_get_sandbox_file_hash_count`, `zia_get_sandbox_report`) so MCP clients can directly invoke quota/report endpoints.

[PR #16](https://github.com/zscaler/zscaler-mcp-server/pull/16) - Added ZIA SSL Inspection Rules tools (`zia_list_ssl_inspection_rules`, `zia_get_ssl_inspection_rule`, `zia_create_ssl_inspection_rule`, `zia_update_ssl_inspection_rule`, `zia_delete_ssl_inspection_rule`) for managing SSL/TLS traffic decryption and inspection policies.

[PR #16](https://github.com/zscaler/zscaler-mcp-server/pull/16) - Added ZTW workload discovery service tool (`ztw_get_discovery_settings`) for retrieving workload discovery service settings.

## 0.3.2 (November 4, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Enhancements

[PR #15](https://github.com/zscaler/zscaler-mcp-server/pull/15) - Added custom User-Agent header support with format `zscaler-mcp-server/VERSION python/VERSION os/arch`. Users can append AI agent information via `--user-agent-comment` flag or `ZSCALER_MCP_USER_AGENT_COMMENT` environment variable.

## 0.3.1 (October 28, 2025) - Tool Registration & Naming Updates

### Added

[PR #14](https://github.com/zscaler/zscaler-mcp-server/pull/14)

- **ZIA Tools**: Added missing read-only tools to services registration
  - `get_zia_dlp_dictionaries` - Manage ZIA DLP dictionaries for data loss prevention
  - `get_zia_dlp_engines` - Manage ZIA DLP engines for rule processing
  - `get_zia_user_departments` - Manage ZIA user departments for organizational structure
  - `get_zia_user_groups` - Manage ZIA user groups for access control
  - `get_zia_users` - Manage ZIA users for authentication and access control

- **ZPA Tools**: Added missing read-only tools to services registration
  - `get_zpa_app_protection_profile` - Manage ZPA App Protection Profiles (Inspection Profiles)
  - `get_zpa_enrollment_certificate` - Manage ZPA Enrollment Certificates
  - `get_zpa_isolation_profile` - Manage ZPA Cloud Browser Isolation (CBI) profiles
  - `get_zpa_posture_profile` - Manage ZPA Posture Profiles
  - `get_zpa_saml_attribute` - Manage ZPA SAML Attributes
  - `get_zpa_scim_attribute` - Manage ZPA SCIM Attributes
  - `get_zpa_scim_group` - Manage ZPA SCIM Groups
  - `get_zpa_app_segments_by_type` - Manage ZPA application segments by type
  - `get_zpa_trusted_network` - Manage ZPA Trusted Networks

### Changed

- **Tool Naming Convention**: Updated tool names to follow consistent `get_*` pattern for read-only operations
  - ZIA tools: `zia_*_manager` → `get_zia_*`
  - ZPA tools: `*_manager` → `get_zpa_*`
  - Maintains backward compatibility with existing `zia_get_*` and `zpa_get_*` patterns

### Fixed

- **Tool Registration**: Resolved missing tool registrations in `zscaler_mcp/services.py`
- **Documentation**: Updated README.md with correct tool names and comprehensive tool listings

## 0.3.0 (October 27, 2025) - Security & Confirmation Release

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### 🔐 Security Enhancements

**Multi-Layer Security Model**:

- Default read-only mode (110+ safe tools always available)
- Global `--enable-write-tools` flag required for write operations
- **Mandatory allowlist** via `--write-tools` (supports wildcards: `zpa_create_*`, `zia_delete_*`)
- Tool annotations: `readOnlyHint=True` for read operations, `destructiveHint=True` for write operations
- **Double-confirmation for DELETE operations**: Permission dialog + server-side confirmation block (33 delete tools)

**Write Tools Allowlist** (Mandatory):

- No write tools registered unless explicit allowlist provided
- Prevents accidental "allow all" scenarios
- Granular control with wildcard patterns

**DELETE Operation Protection**:

- All 33 delete operations require **double confirmation**
- First: AI agent permission dialog (`destructiveHint`)
- Second: Server-side confirmation via hidden `kwargs` parameter
- Prevents irreversible actions from being executed accidentally

### Added

- `zscaler_mcp/common/tool_helpers.py`: Registration utilities for read/write tools with annotations
- `zscaler_mcp/common/elicitation.py`: Confirmation logic for delete operations
- `--enable-write-tools` / `ZSCALER_MCP_WRITE_ENABLED`: Global write mode toggle
- `--write-tools` / `ZSCALER_MCP_WRITE_TOOLS`: Mandatory allowlist (required when write mode enabled)
- `build_mcpb.sh`: Automated packaging script with bundled Python dependencies
- Hidden `kwargs` parameter to all 33 delete functions for server-side confirmation
- `destructiveHint=True` annotation to all 93 write operations

### Changed

- MCPB packages now bundle all Python dependencies (51MB vs 499KB)
- Update operations now fetch current resource state to avoid sending `null` values to API
- Enhanced server logging with security posture information
- Updated test suite for confirmation-based delete operations (163 tests passing)

### Fixed

- Fixed `MockServer.add_tool()` missing `annotations` parameter for `--list-tools` functionality
- Fixed update operations in ZPA segment groups, server groups, app connector groups, service edge groups to handle optional fields correctly
- Fixed Pydantic validation errors in confirmation responses (return string instead of dict)
- Fixed MCPB packaging to include all required dependencies
- Removed problematic `test_use_legacy_env.py` (attempted real API calls)

### Documentation

- Updated README with comprehensive security model documentation
- Added write tools allowlist examples and usage patterns
- Documented double-confirmation flow for delete operations
- Added migration guide for users upgrading from 0.2.x

## 0.2.2 (October 6, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

[PR #11](https://github.com/zscaler/zscaler-mcp-server/pull/11) Fixed README and other documents to change the name title from "Zscaler MCP Server" to "Zscaler Integrations MCP Server"

## 0.2.1 (September 18, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

[PR #10](https://github.com/zscaler/zscaler-mcp-server/pull/10) Fixed import sorting and markdown linting issues:

- Fixed Ruff import sorting errors in `client.py`, `services.py`, and `utils.py`
- Fixed markdownlint formatting issues in `docs/guides/release-notes.md`
- Updated GitHub workflows to include linter checks in release process

## 0.2.0 (September 18, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

#### NEW ZCC MCP Tools

[PR #9](https://github.com/zscaler/zscaler-mcp-server/pull/9) Added the following new tools:

- Added `zcc_list_trusted_networks` - List existing trusted networks
- Added `zcc_list_forwarding_profiles` - List existing forwarding profiles

#### NEW ZTW MCP Tools

[PR #8](https://github.com/zscaler/zscaler-mcp-server/pull/8) Added the following new tools:

- Added `ztw_ip_destination_groups` - Manages IP Destination Groups
- Added `ztw_ip_group` - Manages IP Pool Groups
- Added `ztw_ip_source_groups` - Manages IP Source Groups
- Added `ztw_network_service_groups` - Manages Network Service Groups
- Added `ztw_list_roles` - List all existing admin roles in Zscaler Cloud & Branch Connector
- Added `ztw_list_admins` - List all existing admin users or get details for a specific admin user

#### Documentation Portal

[PR #9](https://github.com/zscaler/zscaler-mcp-server/pull/9) - New documentation portal available in [ReadTheDocs](https://zscaler-mcp-server.readthedocs.io/)

## 0.1.0 (August 15, 2025) - Initial Release

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Added

- Initial implementation for the zscaler-mcp server ([#1](https://github.com/zscaler/zscaler-mcp/issues/1))
- Support for Zscaler services: `zcc`, `zdx`, `zia`, `zpa`, `zid` ([#1](https://github.com/zscaler/zscaler-mcp/issues/1))
- Flexible per service initialization ([#1](https://github.com/zscaler/zscaler-mcp/issues/1))
- Streamable-http transport with Docker support ([#1](https://github.com/zscaler/zscaler-mcp/issues/1))
- Debug option ([#1](https://github.com/zscaler/zscaler-mcp/issues/1))
- Docker support ([#1](https://github.com/zscaler/zscaler-mcp/issues/1))
- Comprehensive end-to-end testing framework with 44+ tests
- Test runner script with multi-model testing support
- Mock API strategy for realistic testing scenarios
- ZIA tools for user management via the Python SDK:
  - `zia_user_groups`: Lists and retrieves ZIA User Groups with pagination, filtering, and sorting
  - `zia_user_departments`: Lists and retrieves ZIA User Departments with pagination, filtering, and sorting
  - `zia_users`: Lists and retrieves ZIA Users with filtering and pagination

### Changed

- Fixed import sorting and linting issues
- Simplified project structure by removing unnecessary nesting
- Updated test organization for better maintainability

### Documentation

- Updated README ZIA Features to include the new tools (`zia_user_groups`, `zia_user_departments`, `zia_users`).
