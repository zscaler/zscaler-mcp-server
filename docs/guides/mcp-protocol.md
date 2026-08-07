# MCP Protocol Posture & Conformance

This server implements the **Model Context Protocol (MCP)**. This guide documents
which protocol revision it speaks, how it advertises tool behaviour to clients,
how destructive operations are gated, and how conformance is verified.

## Protocol baseline

| | |
| --- | --- |
| **Revision negotiated** | `2026-07-28` (stateless core) |
| **Runtime SDK** | `mcp` 2.x (`>=2.0.0,<3`) |
| **Older clients** | Supported — the SDK negotiates down per connection |

Version negotiation is the SDK's job, per connection. A client that speaks
`2025-11-25` or `2025-06-18` still works; it simply gets the older transport for
features the newer revision reshaped. There is **no server-side feature flag** for
the revision, and deliberately so: a flag would mean shipping two code paths and
asking operators to reason about a protocol detail their client already negotiates
correctly.

Three features of the `2026-07-28` revision are adopted:

| Feature | SEP | What it does here |
| --- | --- | --- |
| Stateless input requests | SEP-2322 | Delete confirmations reach a human without a server-to-client back-channel |
| Request-state protection | SEP-2322 | Seals the `requestState` that carries a pending confirmation |
| Cacheable responses | SEP-2549 | Lets clients cache the (immutable) tool inventory |

## Dependency contract

```toml
"mcp[cli]>=2.0.0,<3",
```

The **floor** is 2.0.0 because that is where the revision lands. All three features
above are constructor-level arguments to `MCPServer`, so a 1.x resolution does not
degrade gracefully — it raises at startup.

The **cap** below 3.0.0 is deliberate. The next major is a landmine a routine
`uv sync` should not walk into silently; lifting it should be a reviewed act.

**`fastmcp` is not a dependency at all** — not a base one, not an extra, and no
auth mode asks an operator to install it. `mcp` 2.x ships its own high-level server
(`MCPServer`) with the ASGI app factories this server wraps.

The one thing that used to need it was the OAuth 2.1 auth mode, which was built on
`fastmcp`'s `OIDCProxy`. That mode is now implemented natively: the server declares
itself an OAuth 2.0 protected resource per
[RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html) using `AuthSettings` +
`token_verifier`, both already in `mcp` 2.x. It publishes
`/.well-known/oauth-protected-resource` naming the IdP and verifies presented
tokens against the IdP's JWKS — reusing the same signature, issuer, audience and
expiry checks as the `jwt` mode, so the two cannot drift.

Rewriting it this way removed a dependency that was still a prerelease *and* pinned
a prerelease transitively (`fastmcp-slim`). Resolving that would have required a
blanket `prerelease = "allow"`, which — because `uv lock` resolves every extra —
would have governed the whole lockfile, including the automated SDK-upgrade job.
It also removed the client secret: verifying a signature needs the IdP's public
keys, not a credential of ours.

The trade-off is that clients can no longer self-register via Dynamic Client
Registration; each needs a client ID from the IdP.

Enforced by `tests/test_dependency_caps.py`, which fails the build if the floor
drops, the cap is weakened, `fastmcp` is re-declared anywhere, or any module starts
asking an operator to install something.

## Tool annotations

Every tool advertises MCP [`ToolAnnotations`](https://modelcontextprotocol.io/)
behavioural hints. A client uses them to decide how to present a tool — most
importantly, whether to surface a **human-facing confirmation** before running a
destructive one.

The hints are **derived from the tool's single action verb**, never declared by
hand, so they can never drift from what the tool actually does:

| action   | `readOnlyHint` | `destructiveHint`      | `idempotentHint` | `openWorldHint` |
| -------- | -------------- | ---------------------- | ---------------- | --------------- |
| `read`   | `true`         | *(unset)*              | *(unset)*        | `false`         |
| `create` | `false`        | `false`                | `false`          | `false`         |
| `update` | `false`        | `true` (PUT-replace)   | `true`           | `false`         |
| `delete` | `false`        | `true`                 | `true`           | `false`         |

Notes:

- `update` is marked **destructive** because ZIA policy-rule updates (and several
  other resources) are PUT-replace — a full overwrite that can drop omitted
  fields. It is **idempotent** because the same payload converges to the same
  state. `delete` is destructive and idempotent (deleting twice converges to
  "absent"). `create` is neither — each call appends a new resource.
- `openWorldHint` is `false` for every tool: they all operate against a single,
  closed system (the configured Zscaler tenant), never an open-ended external
  world (contrast a web-search tool).
- Write-only hints are left **unset** (not `false`) on read-only tools, per the
  MCP spec, since they are meaningless there.

> **Annotations are hints, not a security boundary.** They are advisory metadata
> for clients. The authoritative controls remain server-side and are enforced
> regardless of any hint: reads are always safe, writes require the
> `--write-tools` allowlist, and deletes require a human confirmation.

Implementation: the semantics live on `ToolSpec` (`read_only` / `destructive` /
`idempotent`, in `src/zscaler_mcp/registry/spec.py`); `_tool_annotations()` in
`src/zscaler_mcp/registry/fastmcp_bridge.py` renders them into the MCP wire type.
The wire field names are camelCase (shown above); the Python attributes on
`ToolAnnotations` are snake_case.

## Cacheable tool inventory (SEP-2549)

`tools/list` carries a cache hint: `ttl_ms` 300 000, `scope` `"public"`. A client
or proxy may cache the listing instead of re-fetching ~280 entries per connection.

Both halves of that hint are claims about this server's behaviour, and both hold
for the same reason: **the inventory is fixed once registration finishes.** Every
filter — toolset selection, the write allowlist, the entitlement downscope — is
resolved at startup, and there is no runtime registration path, so the listing a
client receives cannot change while the connection lives. `scope: "public"` follows
from the same fact: the listing depends on this server's configuration, not on the
caller, so sharing a cached copy across authorization contexts leaks nothing.

**Adding a tool that enables toolsets at runtime would make this hint a lie.**
`tests/test_protocol_2026_07_28.py` asserts the listing is idempotent, so that
change fails a test rather than silently serving stale inventories.

No other method is hinted. Anything reflecting tenant state must not be cached.

## Client-controlled log level (older revisions only)

`logging/setLevel` is implemented, so a client on `2025-06-18` or `2025-11-25` can
turn diagnostics on against a server it did not launch.

**It does nothing on `2026-07-28`.** SEP-2577 deprecated the logging capability and
that revision drops the method from its surface: the SDK rejects it during request
validation, before handler lookup, so the handler is unreachable there regardless
of what the server registers. That is by design, not a gap — clients on the new
revision use OpenTelemetry instead, which the SDK emits natively. The handler stays
because it costs nothing, serves every older client, and is what keeps the
`logging-set-level` conformance scenario passing.

The level applies to the `zscaler_mcp` logger tree **only**. Raising the root
logger would drag in `httpx`, `uvicorn` and the Zscaler SDK's own request logging,
which at `debug` prints credential-bearing headers. A client asking for verbose MCP
logs is not asking for that.

MCP defines eight severities to Python's five; `notice` maps to `INFO`, and
`alert` / `emergency` both pin to `CRITICAL`.

## HTTP session mode

"Stateless" means two unrelated things in MCP, and conflating them causes real
confusion. This server has always been stateless in the sense that matters for
security review: no tenant state survives a tool call, the Zscaler SDK client is
built per call, and the confirmation-signing secret is per process. None of that
is affected by anything in this section.

Separately, the streamable-http transport can either issue an `Mcp-Session-Id` to
clients that perform the `initialize` handshake, or treat every request as
self-contained. This server keeps the session, **unconditionally** — there is no
flag and no environment variable, because only one of the two settings keeps a
human in the delete confirmation loop:

```bash
zscaler-mcp --transport streamable-http   # sessions on for handshake clients
```

| | this server | had sessions been dropped |
|---|---|---|
| `Mcp-Session-Id` issued on `initialize` | yes | no |
| `2026-07-28` client (no handshake, no session id) | connects | connects |
| **Delete confirmation for a pre-`2026-07-28` client** | **a human is asked** | **token the agent can redeem itself** |
| Delete confirmation for a `2026-07-28` client | a human is asked | a human is asked |
| Requires sticky load balancing | for handshake clients | no |

The second row is the one that is widely misunderstood, so it is worth stating
plainly: a `2026-07-28` request is served in **both** modes. The SDK routes any
request whose `mcp-protocol-version` is not a handshake revision to its modern
entry point *before* the session logic runs, so that revision never touches
session machinery and sessions cost it nothing.

The third row is why the setting is not a preference. A pre-`2026-07-28` client
declares its `elicitation` capability once, during `initialize`, and the
**session is what remembers it**. Without a session the server sees no
capabilities at all, cannot ask, and falls back to the token — and the token can
be redeemed by the agent in the same turn it was issued, so nothing guarantees a
person ever approved the delete. That is a safety regression, and the price of
avoiding it is session affinity for handshake clients.

**How a delete gets confirmed is decided per call**, by
`elicitation_available()` in `src/zscaler_mcp/security/elicitation.py`, from the
capabilities the client advertised:

- **No `elicitation` capability** — the [HMAC confirmation token](#the-hmac-fallback-the-flow),
  an ordinary two-step tool-result exchange. Needs no back-channel.
- **Capability on `2026-07-28`** — the prompt is returned in-band as an
  `InputRequiredResult` and answered on a follow-up call. Also needs no
  back-channel; capabilities arrive per request in `_meta`.
- **Capability on an older revision** — the prompt is *pushed* as a
  server-initiated request over the session, and the call waits for the answer.

No combination lets a delete through unconfirmed, and none blocks one for a
reason the client cannot act on.

**Claude Desktop takes the first path**, because `mcp-remote` does not advertise
the `elicitation` capability. So does any other client that omits it — check your
own by looking for this line in the server log on the first delete:

```text
Client did not advertise the 'elicitation' capability — falling back to the HMAC
confirmation token, which cannot enforce a human decision
```

On that path **the prompt's wording is the only thing asking a human**, so it is
written as an instruction to the agent — show the warning, wait for a reply,
treat the original request as *not* being consent, retry only on an explicit yes.
Expect the agent's own tool-permission dialog ("Allow / Deny") to appear as well;
that is the client authorizing the *tool*, not a person approving the *deletion*,
and the two are easy to mistake for each other.

This remains advisory: a model can ignore the instruction, and one has. The
controls that do not depend on the model are write-tools-off-by-default and a
narrow `--write-tools` allowlist. If a human decision must be guaranteed for
every delete, use a client that supports elicitation.

> **Do not add a reachability check here.** A previous version of
> `elicitation_available()` tried to confirm the client could receive a pushed
> prompt by reading `ctx.connection.has_standalone_channel`. `Context` has no
> such attribute, so every pre-`2026-07-28` caller raised `AttributeError` into
> the defensive `except` and was silently downgraded to the token — the exact
> regression this section warns about, shipped by the code meant to prevent it.
> Capabilities already encode reachability, for the reason given above.

Running multiple replicas has a separate constraint: the confirmation secret is
per process, so a token issued by one replica will not verify on another. See
[the fallback is single-process](#known-limitation-the-fallback-is-single-process).

`sse` is session-oriented by construction and is unaffected.

## Destructive-operation confirmation: threat model

Destructive tools (`action == delete`) are gated by
`src/zscaler_mcp/security/elicitation.py`, which resolves **per call** between two
paths:

| | Path | Used when | Who decides |
| --- | --- | --- | --- |
| **Primary** | **Native elicitation (SEP-2322)** | The client advertises the `elicitation` capability *and* can be reached | A **human**, in a client-rendered prompt |
| Fallback | HMAC confirmation token | Client without the capability, or one whose prompt can't be delivered | The **agent**, echoing a server-issued token |

Elicitation has been an **optional** client capability since `2025-06-18`, which is
why the fallback still exists: a client that does not implement it cannot be asked,
and the server has to do *something* other than delete unattended.

Nothing else in the pipeline changes — the `--write-tools` allowlist still gates
whether a delete tool exists at all. **Neither path can be switched off:** the
server ships no flag or environment variable that skips confirmation, since a
delete against a live tenant is irreversible. To deny deletes outright, leave them
out of the write allowlist.

This section is deliberately blunt about what each path does and does not buy you.

### Native elicitation: the flow

A delete tool declares a **resolved parameter** the caller cannot supply. The
framework fills it before the tool body runs:

1. The agent calls a delete tool. No token, no approval argument — there is no
   approval field in the tool's `inputSchema` for it to fill.
2. The server's resolver asks the client to confirm, naming the resource and
   offering the choices `delete` / `cancel`.
3. On `2026-07-28` this is an `InputRequiredResult`: the call returns, the client
   prompts a human, and the client **retries** with the answer plus an opaque
   `requestState`. On older revisions the same question goes over the mid-call
   `elicitation/create` request instead. Same question, different carrier.
4. The answer arrives as a protocol field. `delete` → the tool body runs. Anything
   else → "NOT performed", and the SDK is never called.

**Why this is the real fix.** The approval is not part of the model's output. There
is no argument for a hijacked model to author, no token for it to echo back to
itself, and a failed round trip fails **closed** — the resolver runs *before* the
tool body, so an unanswered or timed-out confirmation cannot reach the SDK.

The honest limits: trust moves from the model to the **client software** (a
non-compliant client could fabricate an answer — a real boundary, just a much
better placed one), and social-engineering the human still works. Neither is
fixable server-side.

### Request-state protection

`requestState` is the blob a client echoes back on the retry, and it records
which question the server asked. That makes it caller-controlled input bearing on
whether a destructive operation was authorized, so it is sealed by the SDK's
`RequestStateSecurity`: AES-256-GCM, plus expiry, request binding and principal
binding. A confirmation answered on one call cannot be lifted onto a different
call or spent by a different principal, and it stops being valid once it expires.

**It is not single-use, unlike the HMAC fallback below.** The state pins the
question, not the answer — the decision itself rides in `inputResponses` on every
round — so re-sending an identical approved call inside the state's lifetime runs
it again. Because the state is bound to the exact arguments and the authenticated
caller, a repeat can only be the same delete of the same resource by the same
caller, which finds it already gone. Making one approval good for exactly one
execution is a property SEP-2322 does not currently offer; the sealed value that
would key such a ledger is unsealed by the SDK before any server code sees it.

The key is **random and per-process** (`RequestStateSecurity.ephemeral()`), which
has two consequences worth stating plainly:

- A restart invalidates any in-flight confirmation. The client asks again — the
  correct outcome, since the operator never approved anything in the new process.
- Behind a load balancer, a retry landing on a different replica will not decrypt.
  Sticky sessions fix it. A shared key would too, but that means an
  operator-supplied secret, and this deployment shape does not warrant adding one
  to the configuration surface.

This is the same single-process boundary the HMAC fallback has always had, now
enforced with an authenticated cipher instead of a bare MAC.

### The HMAC fallback: the flow

1. The agent calls a delete tool **without** a `confirmation_token`.
2. The server returns a plain-text `DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED`
   message carrying an HMAC token bound to `tool_name + canonical(params) + expiry`
   plus a per-issue nonce.
3. The agent retries with the **same** params plus `kwargs={"confirmation_token": "..."}`.
4. The server recomputes the HMAC. Match → execute. Mismatch/expiry/reuse → reject.

### What the HMAC token *does* guarantee

The token is an **integrity primitive**, not a human gate. Its real job is to
defend the window *between approval and execution*:

| Threat | Plain boolean (`confirmed=true`) | HMAC token |
| --- | --- | --- |
| Approve delete of **X**, execute delete of **X** | ✅ works | ✅ works (token bound to X) |
| Approve delete of **X**, params flipped to **Y** before execution (TOCTOU / confused deputy) | ❌ boolean still passes for Y | ✅ **rejected** — HMAC bound to X |
| Agent self-authorizes with no server round-trip | ❌ agent just sets the bool | ✅ impossible — needs a server-issued token |
| Replay an old approval later | ❌ boolean never expires | ✅ rejected after TTL (default 300 s) |
| Redeem the same approval twice | ❌ boolean is reusable | ✅ rejected — single-use ledger |
| Horizontal scale-out (any instance validates) | n/a | ❌ **single-process only** — see below (the primary path scales with a shared key ring) |

So the guarantees are: **anti-tamper, anti-forgery, anti-replay, single-use** —
within one process.

### Known limitation: the fallback is single-process

The HMAC key and the single-use ledger both live in process memory. A token minted
by one process is therefore not valid on another, nor after a restart. Behind a
load balancer with more than one replica (Cloud Run, AKS, ECS, Container Apps), a
confirmation retry that lands on a different replica is rejected as a parameter
mismatch — the operator sees "token does not match the submitted parameters" for a
perfectly valid approval.

**Scope check before you worry about this.** The limitation applies *only* to the
fallback path, i.e. to clients that do not implement elicitation. It is also not
worth fixing with a bespoke shared-secret env var: that would duplicate — with a
weaker, sign-only primitive we would then carry forever — what the protocol already
defines in `RequestStateSecurity`. Multi-replica operators should confirm their
clients advertise the capability; if any do not, run a single replica while write
tools are enabled.

### The primary path has its own key-regime requirement

The elicitation path does **not** inherit the fallback's process-memory ledger, but
its sealed `requestState` still has to be decryptable by whichever replica receives
the retry. With `ZSCALER_MCP_REQUEST_STATE_KEYS` unset the SDK's `ephemeral()` key
is per-process, so the same cross-replica failure applies — it just fails closed at
the AEAD boundary instead of as a parameter mismatch.

**Sticky sessions are not a workaround on `2026-07-28`.** The server does still
issue an `Mcp-Session-Id`, but only to *handshake-era* clients. The SDK routes a
modern request to `handle_modern_request` **before** any session handling, and that
handler never sets a session id: a `2026-07-28` request is a self-contained POST.
There is therefore no MCP session for a load balancer to pin on, and any affinity
would have to come from infrastructure-level cookie or source-IP stickiness, which
is not a protocol guarantee.

Set `ZSCALER_MCP_REQUEST_STATE_KEYS` to a shared ring (first key seals, all keys
unseal) for any multi-replica HTTP deployment with write tools enabled. The server
logs a warning at startup if that combination is detected without one.

A second fallback-only limitation: tokens are **not bound to the calling
principal**, so any authenticated caller holding one can redeem it. The protocol's
`authenticated_principal` binding closes that on the primary path. Relevant only
for multi-user HTTP deployments.

### What the fallback does **NOT** guarantee (the important part)

Everything below describes the **HMAC fallback path only**. It is exactly the gap
native elicitation closes, which is why the fallback is a fallback.

**The HMAC token cannot stop a hijacked or misbehaving agent that both requests
*and* redeems the token for the same parameters.** From the server's vantage
point, that sequence is byte-for-byte identical to a legitimate approved delete —
the token is just a string the agent is holding, and the agent can echo it back
to itself in the *same turn*. This is not hypothetical: in observed traces the
model reasons *"this is an internal confirmation check that's already been
validated, so I can proceed"* and completes the whole dance autonomously.

Concretely, the fallback does **not** protect against:

- **Prompt injection that drives an unwanted delete end-to-end.** If injected
  content hijacks the model into calling delete, the same hijacked model receives
  the token and redeems it. HMAC only catches *parameter substitution after
  approval*, not an attacker who controls both calls.
- **A model that skips asking the human.** Nothing forces the agent to surface the
  confirmation message to a person before redeeming.
- **Social-engineering the human.** If the human approves because the agent framed
  a malicious delete as benign, the token faithfully authorizes it.

### The defense-in-depth stack

1. **Write tools are OFF by default (`--enable-write-tools` / `--write-tools`
   allowlist).** Still the #1 control. If a delete tool is never registered, there
   is nothing for injection to hijack. Ship read-only unless a write surface is
   explicitly, narrowly enabled. Native elicitation does not change this.
2. **Native elicitation** — a real human gate for capable clients, enforced by the
   protocol rather than by convention.
3. **The HMAC token** — for callers that cannot be prompted. Hardens the exchange
   against tamper, replay and reuse, but does not create a human decision where the
   agent declines to ask for one.

> Layer 2 is what makes the human gate enforceable. Layer 3 is a TOCTOU/replay
> defense, not an anti-injection control — so on a deployment whose clients lack
> elicitation support, keeping the write surface narrow remains the strongest lever.

## Conformance

The server is validated against the **official** MCP conformance suite,
[`@modelcontextprotocol/conformance`](https://github.com/modelcontextprotocol/conformance),
in **server mode** — the runner connects to a live instance as an MCP client and
asserts protocol behaviour.

Two targets exist, for different jobs:

| Target | Revision | Runner | Gates CI? |
| --- | --- | --- | --- |
| `make conformance` | `2025-11-25` (published) | `@0.1.16` (stable, pinned) | **Yes** |
| `make conformance-next` | `2026-07-28` | `@0.2.0-alpha.10` (prerelease) | No |

CI gates on the **published** revision with a **pinned stable** runner. An alpha
runner can add, rename or reinterpret scenarios between builds, which would turn
upstream churn into red builds here — so `conformance-next` is the maintainer's
deliberate check on the revision this server actually negotiates, not a gate. Fold
it into the gate once the 0.2.x runner reaches GA.

Both require `node`/`npx` on your `PATH`. CI runs the stable flow in
`.github/workflows/mcp-conformance.yml`.

The server needs **no Zscaler credentials** to be tested: the SDK client is created
lazily on the first tool call, so `initialize` / `tools/list` / the `tools/call`
envelope are all exercisable against an uncredentialed boot.

### Expected-failures baselines

The suite's `active` set includes scenarios that don't apply to a production
server. `.github/conformance-baseline.yml` (and `-next.yml`) list these
known-inapplicable scenarios so CI gates on regressions while tolerating them.
Every entry fails for one of two legitimate reasons:

1. **Missing reference test fixtures** — scenarios like `tools-call-image` or
   `prompts-get-simple` require the reference "everything" server's synthetic
   fixtures (a tool that returns an image; a prompt literally named
   `test_simple_prompt`). A real server doesn't ship those. The elicitation
   scenarios are in this category too: they need a fixture tool that elicits
   unconditionally, whereas this server elicits on **delete** tools, which are off
   unless `--enable-write-tools` is passed.
2. **Capabilities we intentionally don't advertise** — resources and completions.

Everything that *does* apply passes: `server-initialize`, `ping`,
`logging-set-level`, `tools-list`, `tools-call-simple-text`, `tools-call-error`,
`server-sse-multiple-streams`, `resources-list`, `prompts-list`,
`dns-rebinding-protection`.

The runner's exit-code contract keeps the baselines honest:

| Scenario result | In baseline? | Outcome |
| --------------- | ------------ | ------- |
| Fails | Yes | pass (expected) |
| Fails | No  | **fail** — new regression |
| Passes | Yes | **fail** — stale entry, remove it |
| Passes | No  | pass |

So adding a capability (or a fixture) forces a baseline update in the same PR — it
can't silently rot.

### Where the real behaviour is tested

Conformance covers the protocol envelope; it cannot exercise this server's
confirmation flow, because that lives on delete tools the runner has no fixture
for. `tests/test_protocol_2026_07_28.py` covers it end-to-end over the in-memory
transport, including the assertion that matters most: that the confirmation travels
over the **stateless input-request loop**, not a back-channel.

That distinction is not academic. The mid-call form kept passing in isolation while
being unreachable over the negotiated revision, because the stateless core removed
the back-channel it depended on. A unit test could not tell the difference; only a
real round trip can.

## Not planned

- **Session / Redis infrastructure.** Nothing worth persisting exists between
  calls — no tenant state, a lazy per-call SDK client. See
  [HTTP session mode](#http-session-mode) for the transport-level session,
  which is a separate question.
- **Header-based routing** (`X-MCP-Toolsets`) and URL-path toolset shortcuts. Both
  need per-request server construction.
- **MCP Apps / Tasks extensions.** No use case here yet.
