# MCP Protocol Posture & Conformance

This server implements the **Model Context Protocol (MCP)**. This guide documents
which protocol version it targets, how it advertises tool behaviour to clients,
how conformance is verified, and how the next protocol revision will be adopted.

## Protocol baseline

| | |
| --- | --- |
| **Published baseline served** | `2025-11-25` |
| **Runtime SDKs** | `mcp` 1.x (`>=1.23.0,<2`), `fastmcp` 3.x (`>=2.13.0,<4`) |
| **Next spec (staged, not yet adopted)** | `2026-07-28` (stateless core) |

The server speaks the current published MCP specification and is verified against
it in CI (see [Conformance](#conformance)). The next revision, `2026-07-28`, is a
stateless-core rewrite; adopting it is a deliberate, staged migration described in
[Migration to 2026-07-28](#migration-to-2026-07-28) — **not** an automatic
consequence of a dependency bump.

## SDK version caps

`pyproject.toml` pins **upper bounds** on the two MCP SDKs:

```toml
"mcp[cli]>=1.23.0,<2",
"fastmcp>=2.13.0,<4",
```

These caps are deliberate, not lazy pinning. The `2026-07-28` specification ships
in `mcp` 2.x and `fastmcp` 4.x — a breaking rewrite (new `CallToolResult` /
`InputRequiredResult` return types, `ServerRunner`, native multi-round-trip
elicitation) that also cascades prerelease foundations underneath it (an alpha
Pydantic line, the `fastmcp` → `fastmcp-slim` package split). A routine
`uvx zscaler-mcp` or `uv sync` must not silently jump onto that stack the day the
majors reach GA.

Lifting a cap is a reviewed change done **in lockstep** with the migration work,
never on its own. The caps are enforced by `tests/test_dependency_caps.py`, which
fails the build if either bound is dropped or weakened.

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
> `--write-tools` allowlist, and deletes require HMAC confirmation.

Implementation: the semantics live on `ToolSpec` (`read_only` / `destructive` /
`idempotent`, in `src/zscaler_mcp/registry/spec.py`); `_tool_annotations()` in
`src/zscaler_mcp/registry/fastmcp_bridge.py` renders them into the MCP wire type.

## Conformance

The server is validated against the **official** MCP conformance suite,
[`@modelcontextprotocol/conformance`](https://github.com/modelcontextprotocol/conformance),
in **server mode** — the runner connects to a live instance as an MCP client and
asserts protocol behaviour.

### Running it locally

```bash
make conformance
```

This boots the server over streamable-http, points the pinned runner at it for
the published `2025-11-25` baseline, and gates on the committed baseline file.
Requires `node`/`npx` on your `PATH`. CI runs the identical flow in
`.github/workflows/mcp-conformance.yml`.

Key choices (following the [official server guide](https://qaskills.sh/blog/mcp-official-conformance-suite-server-guide-2026)):

- The runner version is **pinned** (`@0.1.16`) — an unpinned `latest` could change
  what "conformant" means between runs.
- We target the **published** `2025-11-25` baseline, never `draft`. A conformance
  *claim* must not shift silently when new spec work lands.
- The server needs **no Zscaler credentials** to be tested: the SDK client is
  created lazily on the first tool call, so `initialize` / `tools/list` / the
  `tools/call` envelope are all exercisable against an uncredentialed boot.

### Expected-failures baseline

The suite's `active` set includes scenarios that don't apply to a production
server. `.github/conformance-baseline.yml` lists these known-inapplicable
scenarios so CI gates on regressions while tolerating them. Every entry fails for
one of two legitimate reasons:

1. **Missing reference test fixtures** — scenarios like `tools-call-image` or
   `prompts-get-simple` require the reference "everything" server's synthetic
   fixtures (a tool that returns an image; a prompt literally named
   `test_simple_prompt`). A real server doesn't ship those.
2. **Capabilities we intentionally don't advertise** — resources, completions,
   and server-initiated elicitation.

Everything that *does* apply passes: `server-initialize`, `ping`,
`logging-set-level`, `tools-list`, `tools-call-simple-text`, `tools-call-error`,
`server-sse-multiple-streams`, `resources-list`, `prompts-list`,
`dns-rebinding-protection`.

The runner's exit-code contract keeps the baseline honest:

| Scenario result | In baseline? | Outcome |
| --------------- | ------------ | ------- |
| Fails | Yes | pass (expected) |
| Fails | No  | **fail** — new regression |
| Passes | Yes | **fail** — stale entry, remove it |
| Passes | No  | pass |

So adding a capability (or a fixture) forces a baseline update in the same PR — it
can't silently rot.

## Destructive-operation confirmation: threat model

Destructive tools (`action == delete`) are gated by a two-step, HMAC-signed
confirmation (`src/zscaler_mcp/security/elicitation.py`). It is easy to overstate
what this buys you, so this section is deliberately blunt about the guarantees
and — more importantly — the **non-guarantees**. Read it before assuming the
confirmation "stops prompt injection."

### The flow

1. The agent calls a delete tool **without** a `confirmation_token`.
2. The server returns a plain-text `DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED`
   message carrying an HMAC token bound to `tool_name + canonical(params) + expiry`.
3. The agent retries with the **same** params plus `kwargs={"confirmation_token": "..."}`.
4. The server recomputes the HMAC. Match → execute. Mismatch/expiry → reject.

### What the HMAC token *does* guarantee

The token is an **integrity primitive**, not a human gate. Its real job is to
defend the window *between approval and execution*:

| Threat | Plain boolean (`confirmed=true`) | HMAC token |
| --- | --- | --- |
| Approve delete of **X**, execute delete of **X** | ✅ works | ✅ works (token bound to X) |
| Approve delete of **X**, params flipped to **Y** before execution (TOCTOU / confused deputy) | ❌ boolean still passes for Y | ✅ **rejected** — HMAC bound to X |
| Agent self-authorizes with no server round-trip | ❌ agent just sets the bool | ✅ impossible — needs a server-issued token |
| Replay an old approval later | ❌ boolean never expires | ✅ rejected after TTL (default 300 s) |
| Horizontal scale-out (any instance validates) | n/a | ✅ stateless — the signing secret is per-process, no shared session store |

So the guarantees are: **anti-tamper, anti-forgery, anti-replay, stateless.** These
are genuine and worth keeping.

### What it does **NOT** guarantee (the important part)

**The HMAC token cannot stop a hijacked or misbehaving agent that both requests
*and* redeems the token for the same parameters.** From the server's vantage
point, that sequence is byte-for-byte identical to a legitimate approved delete —
the token is just a string the agent is holding, and the agent can echo it back
to itself in the *same turn*. This is not hypothetical: in observed traces the
model reasons *"this is an internal confirmation check that's already been
validated, so I can proceed"* and completes the whole dance autonomously.

Concretely, the confirmation does **not** protect against:

- **Prompt injection that drives an unwanted delete end-to-end.** If injected
  content hijacks the model into calling delete, the same hijacked model receives
  the token and redeems it. HMAC only catches *parameter substitution after
  approval*, not an attacker who controls both calls.
- **A model that skips asking the human.** Nothing in the protocol forces the
  agent to surface the confirmation message to a person before redeeming. A
  well-behaved model asks; a compromised one need not.
- **Social-engineering the human.** If the human approves because the agent framed
  a malicious delete as benign, the token faithfully authorizes it.

### What actually provides the human gate today

The confirmation token is **layer 3** of a defense-in-depth stack. The load-bearing
protections are the first two:

1. **Write tools are OFF by default (`--enable-write-tools` / `--write-tools`
   allowlist).** This is the #1 control. If a delete tool is never registered,
   there is nothing for injection to hijack. Ship read-only unless a write surface
   is explicitly, narrowly enabled.
2. **A human reading the confirmation in chat and replying.** This is the actual
   human-in-the-loop today — but it lives in the *client's* rendering plus the
   operator's attention, **not** in the protocol. It is advisory, not enforced.
3. **The HMAC token** — hardens (2) against tamper/replay/forgery, but does not
   create a human decision where the agent declines to ask for one.

> **Do not treat the HMAC confirmation as the anti-prompt-injection control.** It
> is a TOCTOU/replay defense underneath the two controls above. The single
> strongest lever you have is keeping write tools disabled.

### Why native elicitation (`2026-07-28`) is the real fix

The gap above is structural: any confirmation the *agent* mediates can be
completed by the agent. **Native MCP elicitation** closes it by moving the decision
**out of the model's control** — the *client* (Claude Desktop, Cursor, …) renders
a human-facing prompt and **a person clicks**. The model cannot fabricate that
click, cannot echo it back to itself, and cannot be injected into producing it.

There are two forms, and only one is SDK-gated:

- **Client-initiated elicitation (`ctx.elicit`) — available on today's baseline.**
  `fastmcp` (3.x) exposes `Context.elicit(...)` and `mcp` (1.x) carries the
  `ElicitRequest`/`ElicitResult`/`ElicitationCapability` primitives. The server can,
  mid-tool-call, ask a capable client to prompt the human. This is implementable now
  and does **not** require the `2026-07-28` bump. It requires the client to advertise
  the elicitation capability, so the HMAC token remains as the **fallback** for
  clients that don't (and as the integrity layer either way).
- **Stateless elicitation (`InputRequiredResult` + `requestState`) — SDK-gated.**
  The `2026-07-28` reworking returns an "input required" result the client answers on
  a fresh request, so any server instance can handle the retry (the scale-out form).
  This needs `mcp` 2.x / `fastmcp` 4.x. HMAC does not disappear — it demotes to the
  signature over the opaque `requestState`, preserving statelessness and tamper/replay
  resistance.

In both forms the *human* decision moves to where injection can't reach it; the
difference is only *how* the round-trip is carried. The staged migration is
described next.

## Migration to 2026-07-28

The `2026-07-28` spec is a stateless-core revision. This server is already
well-positioned for it (no sessions, lazy per-call client, HMAC-based
confirmation), but the Python SDKs that carry it (`mcp` 2.x / `fastmcp` 4.x) must
reach GA first. The plan:

- **Now (published baseline):** the SDK caps, tool annotations, and conformance
  suite above — all shipped against `2025-11-25`, no breaking bump.
- **Staged (gated on `mcp` 2.x / `fastmcp` 4.x GA):** bump the SDKs; adapt the
  bridge to the new `CallToolResult` / `InputRequiredResult` return types; rework
  destructive confirmation from the agent-visible HMAC token to **native
  elicitation** (an `InputRequiredResult` carrying an HMAC-signed `requestState`);
  re-run the conformance suite at `2026-07-28`. Version negotiation is handled by
  the SDK per connection (`mode='auto'`), so old clients keep working — no
  server-side feature flag.
- **Not planned:** session/Redis infrastructure (already stateless), header-based
  routing, and the MCP Apps/Tasks extensions.

### Note on confirmation and prompt injection

See [Destructive-operation confirmation: threat model](#destructive-operation-confirmation-threat-model)
for the full analysis of what today's HMAC token does and does not protect
against. In short: under `2026-07-28`, the agent-visible token is replaced by
**native elicitation** (an `InputRequiredResult` a compliant client renders as a
human-facing prompt), moving the yes/no decision *out of the potentially hijacked
model's loop*. HMAC survives as the signature over the elicitation's opaque
`requestState` — statelessness and tamper/replay resistance preserved, human
decision relocated to where injection can't reach it.
