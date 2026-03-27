# A2A Protocol Implementation Design — Langflow

Status: **Unified Design** (merged from Claude and Codex design lineages)
Target: A2A v0.3 stable, `a2a-sdk` Python package

---

## Product Thesis

MCP gives agents tools. A2A gives agents peers.

Langflow should support both. A2A should feel like collaboration — not just another API transport. Langflow's visual flow builder is a natural fit for creating agents that others consume. A2A makes that consumption standardized rather than proprietary.

**Langflow's differentiator:** Most A2A implementations expose code-defined agents. Langflow would be the first to offer visually-built agents published via A2A — build in the UI, toggle A2A on, and your flow becomes a standard agent on the network.

---

## Problem Statement

Langflow can already build local agentic workflows, but it does not have a first-class, standards-aligned way to:

- be discovered and called by external agent systems via a standard protocol,
- delegate work from one workflow to another remote workflow,
- continue a remote delegated task across turns,
- and trace those interactions as a coherent multi-step collaboration.

Without that, Langflow risks looking behind the curve as the market starts asking about agent interoperability. LangChain, CrewAI, and Microsoft Agent Framework have already shipped A2A support.

---

## Why Now

- A2A is governed by the Linux Foundation's AAIF, co-founded by OpenAI, Anthropic, Google, Microsoft, AWS, and Block.
- LangChain and CrewAI — Langflow's closest competitors — have shipped A2A. Not having it puts Langflow at a disadvantage for multi-agent use cases.
- The protocol is stabilizing (v0.3 with gRPC, signed AgentCards). Risk of it fizzling is low.
- Langflow already has the substrate needed: workflow execution, MCP exposure patterns, agentic UX surfaces, SSE streaming.

---

## Target Users

### Primary: Platform builder

A developer or team building a multi-agent system where Langflow is one component among several (LangGraph orchestrator, custom agents, third-party SaaS agents).

- Wants to publish a Langflow RAG agent so a LangGraph orchestrator can discover and delegate research tasks to it without knowing anything about Langflow's API.
- Wants streaming progress from long-running flows.
- Wants the Langflow agent to ask for clarification when a query is ambiguous.

### Secondary: Langflow power user

An existing Langflow user who builds flows and wants to make them available to teammates or external systems.

- Wants to toggle A2A on for a specific flow without modifying the flow itself.
- Wants flow's Agent component to naturally ask for clarification from callers.
- Wants to control which flows are exposed and require authentication.

### Tertiary: Agent ecosystem participant

A developer using any A2A-compatible framework who wants to leverage Langflow-built agents.

- Wants to discover a Langflow agent's capabilities via its AgentCard.
- Wants to have a multi-turn conversation using standard A2A calls.

---

## V1 Scope

### V1 delivers: A2A Server

Expose Langflow flows as A2A-compliant agents. Any A2A-compatible system can discover and interact with Langflow flows.

### V1 includes

- Expose an agent/chat flow as an A2A endpoint
- Agent Card generation and public A2A runtime endpoints
- Single-turn `message:send` (synchronous)
- SSE streaming via `message:stream`
- Multi-turn conversations via `contextId` → Langflow session mapping
- `INPUT_REQUIRED` turn-taking via auto-injected `request_input` tool
- Task retrieval, listing, and cancellation
- Per-flow A2A configuration (opt-in)
- Instance-level kill switch (`LANGFLOW_A2A_ENABLED`)
- API key authentication
- Protocol compliance with `a2a-sdk` types

### V1 does NOT include

- A2A Client component (calling remote A2A agents from a flow) — Phase 2
- Push notifications / webhooks
- gRPC or JSON-RPC bindings
- OAuth 2.0 (roadmapped)
- Frontend UI for A2A management (API-only for v1)
- Configurable I/O mapping (convention-only for v1)
- Full cross-vendor interoperability guarantees
- Arbitrary multimodal exchange

### Why server-first

Server fills the bigger gap — Langflow can already consume external capabilities (MCP, tools, APIs) but lacks a standard way to be consumed by other agent systems. The A2A Client can test against the server we build, and ships as a natural follow-up.

---

## Product Model

Langflow presents three distinct concepts:

| Concept | Role | Mental model |
|---|---|---|
| **MCP** | Tools for an agent | "Use this tool" |
| **A2A** | Task-oriented delegation to/from agent peers | "Delegate this task" |
| **Workflow API** | Direct developer execution of flows | "Run this flow" |

This distinction must be explicit in UI copy, docs, and errors.

---

## URL Scheme

### Official A2A protocol alignment

The A2A spec (v0.3) defines flat REST paths under a single agent base URL. The `a2a-sdk` Python package's `A2ARESTFastAPIApplication` supports mounting at any prefix via the `rpc_url` parameter.

Since Langflow hosts multiple agents (one per exposed flow), each flow is mounted at its own prefix:

```
Base URL per agent: /a2a/{agent_slug}/

Agent Card:         GET  /a2a/{agent_slug}/.well-known/agent-card.json
Extended Card:      GET  /a2a/{agent_slug}/v1/card
Send message:       POST /a2a/{agent_slug}/v1/message:send
Stream message:     POST /a2a/{agent_slug}/v1/message:stream
Get task:           GET  /a2a/{agent_slug}/v1/tasks/{task_id}
List tasks:         GET  /a2a/{agent_slug}/v1/tasks
Cancel task:        POST /a2a/{agent_slug}/v1/tasks/{task_id}:cancel
Resubscribe:        GET  /a2a/{agent_slug}/v1/tasks/{task_id}:subscribe
```

### Why `agent_slug` (not `flow_id`)

- Stable, human-readable identity — renaming a flow doesn't break the URL
- Matches the A2A spec's mental model of named agents
- Unique per project/owner scope
- Consistent with how LangChain handles multi-agent hosting

### Internal admin endpoints (not part of A2A protocol)

```
PUT  /api/v1/flows/{flow_id}/a2a-config    # Enable/disable A2A for a flow
GET  /api/v1/flows/{flow_id}/a2a-config    # Read A2A config
```

---

## Architecture: Thin FastAPI Layer

A2A endpoints are added directly to Langflow's existing FastAPI app. A lightweight translation layer maps between A2A protocol objects and Langflow's flow execution engine.

### Why this approach

- Minimal new infrastructure — reuses auth, flow execution, DB, sessions
- Follows the same pattern as the existing MCP server integration
- No extra deployment process (no sidecar)
- Sufficient for team-scale concurrency

### Alternatives considered

| Approach | Verdict | Reason |
|---|---|---|
| Sidecar service | Rejected | Extra deployment complexity, duplicated auth. Overkill for team-scale. |
| Plugin system | Rejected | Langflow lacks a mature plugin system. Building one just for this is scope creep. |
| MCP-only federation | Rejected | Semantically wrong — everything becomes "just a tool." Harder to express agent identity, delegation, streaming state. |
| Deep graph-native remote execution | Rejected | Too much surface area for a first release. |

---

## Module Structure

```
src/backend/base/langflow/api/a2a/
├── __init__.py
├── router.py              # FastAPI routes (AgentCard, message:send, message:stream, tasks)
├── config.py              # A2A configuration model per flow
├── agent_card.py          # AgentCard generation from flow metadata
├── task_manager.py        # Task lifecycle (create, update, get, cancel, input_required)
├── flow_adapter.py        # Translates A2A messages <-> flow execution
├── streaming.py           # SSE streaming bridge
└── request_input_tool.py  # Auto-injected tool for INPUT_REQUIRED signaling
```

---

## Component Design

### 1. AgentCard Generation (`agent_card.py`)

Auto-generates an A2A AgentCard from Langflow flow metadata:

- `flow.a2a_name` (or `flow.name`) → agent name
- `flow.a2a_description` (or `flow.description`) → agent description
- Flow inputs/outputs → skill definition (one skill per flow)
- `supportedInterfaces` → HTTP+JSON/REST binding (v1)
- Auth section reflects configured auth mode (API key for v1)
- `capabilities.streaming = true`
- `capabilities.pushNotifications = false`
- `capabilities.extendedAgentCard = true` (auth-gated extended card)

**Capability model** (split from Codex spec):

- **Platform-level capabilities** (truthful for all endpoints): streaming, task retrieval, task cancellation
- **Flow-level behavioral suitability** (per-flow metadata): whether the backing flow is service-like or truly agentic, whether it can produce meaningful multi-turn continuation

The Agent Card is a protocol discovery document, not proof that the backing flow has autonomous reasoning. Langflow must describe endpoints honestly.

**Endpoints:**
- `GET /a2a/{agent_slug}/.well-known/agent-card.json` — Public AgentCard (basic discovery info)
- `GET /a2a/{agent_slug}/v1/card` — Auth-gated extended card with full skill/schema details

### 2. Flow Adapter (`flow_adapter.py`)

The translation layer between A2A protocol and Langflow execution.

```
A2A Message → flow_adapter → Langflow flow execution → flow_adapter → A2A Task/Artifacts
```

**Inbound (A2A → Langflow) — convention-based:**

| A2A Part type | Langflow target |
|---|---|
| `text` | Flow's primary text input (`input_value`) |
| `data` (structured JSON) | Flow tweaks |
| `url` / `raw` | File inputs (if flow accepts them) |
| `contextId` | Langflow `session_id` (enables multi-turn) |

**Outbound (Langflow → A2A):**

| Langflow output | A2A artifact |
|---|---|
| AI message (text) | `Artifact` with `text` Part |
| Structured data (JSON) | `Artifact` with `data` Part |
| File output | `Artifact` with `url` Part (pointing to Langflow file endpoint) |
| Error | `TASK_STATE_FAILED` with error message |

**Convention over configuration:** v1 uses fixed conventions for I/O mapping. No user-configurable mapping. This is a deliberate simplification — the convention is a subset of configurable mapping and can be upgraded without breaking changes.

**Multi-turn:** Same `contextId` across messages → same Langflow session → Agent component picks up chat history automatically.

**Idempotent retry:** Same `taskId` re-sent → return cached result if completed, re-execute if previously failed.

### 3. `request_input` Tool — Server-Initiated Turns (`request_input_tool.py`)

This is the mechanism that enables `INPUT_REQUIRED` — the core A2A capability where the server agent asks the client for clarification mid-task.

**How it works:** When a flow is executed via A2A and contains an Agent component, a `request_input` tool is automatically injected into the Agent's toolkit. The LLM autonomously decides when to use it — no special canvas nodes or flow modifications needed.

```python
# Auto-injected into Agent's toolkit when running behind A2A
request_input = StructuredTool(
    name="request_input",
    description="Ask the calling agent for clarification or additional information. "
                "Use this when you need more details to complete the task.",
    func=request_input_handler,
    args_schema=RequestInputSchema,  # { "question": str }
)
```

**The execution flow:**

```
1. Client sends message via A2A
2. Flow executes, Agent component runs with request_input in its toolkit
3. LLM reasons: "I need to know which environment"
4. LLM calls request_input("Which environment? I see staging and prod.")
5. flow_adapter intercepts the tool call:
   a. Emits TaskStatusUpdateEvent → INPUT_REQUIRED with the question as message
   b. Suspends the Agent's execution via asyncio.Event
6. Client sees INPUT_REQUIRED, sends follow-up message (same context + task)
7. flow_adapter receives follow-up:
   a. Resolves the asyncio.Event with the client's response
   b. Response is returned as the tool result to the Agent
8. Agent continues reasoning with the new information
9. Agent produces final answer → COMPLETED
```

**Key design points:**

- **No canvas changes:** The tool is invisible on the canvas. It's injected at runtime only when the flow is invoked via A2A.
- **Agent autonomy:** The LLM decides when to ask for input, just like it decides when to use any other tool.
- **Async suspension:** The flow execution coroutine `await`s an `asyncio.Event` while waiting for the client's response. Holds the execution context in memory but requires no serialization or engine changes.
- **Timeout:** Configurable (default 5 minutes). On timeout, the tool returns an error message to the Agent, which must either proceed with best-effort or fail.
- **Multiple rounds:** The Agent can call `request_input` multiple times within a single task.
- **Limitation:** Only works for flows that contain an Agent component (LLM-backed). Non-agent DAG flows cannot ask for input.

### 4. Task Manager (`task_manager.py`)

Tracks A2A task state in the database.

**New DB model: `A2ATask`**

| Field | Type | Description |
|---|---|---|
| `task_id` | UUID (PK) | A2A task identifier |
| `context_id` | UUID | Groups related tasks into a conversation |
| `flow_id` | UUID (FK) | Which flow is executing |
| `session_id` | str | Langflow session (derived from `context_id`) |
| `state` | enum | `SUBMITTED`, `WORKING`, `INPUT_REQUIRED`, `COMPLETED`, `FAILED`, `CANCELED` |
| `artifacts` | JSON | Collected output artifacts |
| `metadata` | JSON | A2A task metadata |
| `error` | str (nullable) | Error message if failed |
| `created_at` | datetime | Task creation time |
| `updated_at` | datetime | Last state change |

**State transitions:**

```
message received             →  SUBMITTED
flow execution starts        →  WORKING
agent calls request_input    →  INPUT_REQUIRED (awaiting client response)
client responds              →  WORKING (resumed)
flow completes               →  COMPLETED (with artifacts)
flow errors                  →  FAILED (with error + partial artifacts if any)
input timeout                →  FAILED (agent could not continue without input)
cancel requested             →  CANCELED (best-effort)
```

**Cleanup:** Tasks older than configurable TTL (default 24h) are pruned automatically. Active tasks (WORKING, INPUT_REQUIRED) not pruned even if old. Configurable via `LANGFLOW_A2A_TASK_TTL`.

**Cancellation:** Best-effort for v1. Sets state to `CANCELED`. If task is in `INPUT_REQUIRED`, resolves the event with an error.

### 5. SSE Streaming (`streaming.py`)

Primary interaction mode. Bridges Langflow's callback/event system to A2A SSE format.

**Event mapping:**

| Langflow event | A2A SSE event |
|---|---|
| Flow execution started | `TaskStatusUpdateEvent` → `WORKING` |
| Token streamed from LLM | `TaskArtifactUpdateEvent` with partial text (append) |
| Vertex completed | `TaskStatusUpdateEvent` with progress message |
| Agent calls `request_input` | `TaskStatusUpdateEvent` → `INPUT_REQUIRED` with question as message |
| Client responds to input request | `TaskStatusUpdateEvent` → `WORKING` (resumed) |
| Flow completed | Final `TaskArtifactUpdateEvent` + `TaskStatusUpdateEvent` → `COMPLETED` |
| Flow errored | `TaskStatusUpdateEvent` → `FAILED` with error |

**Connection handling:**
- Client disconnect mid-stream → flow still completes, results cached in task record
- Client can reconnect via `GET /tasks/{task_id}` or `GET /tasks/{task_id}:subscribe`
- Task state updated in DB regardless of listener presence

### 6. Flow A2A Config (`config.py`)

**DB model (extends Flow):**

Add fields to the Flow model:

| Field | Type | Default | Description |
|---|---|---|---|
| `a2a_enabled` | bool | `False` | Whether this flow is exposed via A2A |
| `a2a_name` | str | None | Public agent name (falls back to `flow.name`) |
| `a2a_description` | str | None | Public agent description (falls back to `flow.description`) |
| `a2a_agent_slug` | str | None | URL slug (unique per owner scope) |
| `a2a_input_mode` | str | `"chat"` | Input contract mode |
| `a2a_output_mode` | str | `"text"` | Output contract mode |

**Why on Flow model (not separate table):**
- MCP exposure already follows a flow-level metadata pattern
- V1 exposure is local and flow-specific
- Minimizes new joins for the authoring UI

**Validation rules:**
- Only flows with Chat Input + Agent/LLM + Chat Output are eligible for V1 A2A exposure
- `a2a_agent_slug` must be unique per project/owner scope
- Renaming a flow does not affect `a2a_agent_slug`

---

## Conversation Model & Turn-Taking

### How turns work in v1

**Turn-taking is bidirectional.** The client agent initiates by sending a message. The Langflow agent can either respond with a final answer, or ask for clarification via `INPUT_REQUIRED`.

**Multi-turn conversations via `contextId`:**

```
CLIENT AGENT                                LANGFLOW AGENT

Turn 1:
  POST /message:send
  contextId: "ctx-abc"
  "What vulnerabilities exist in our auth?"
                                ──────────►  Flow executes with input_value
                                             Agent queries vector store
                                ◄──────────
  Task COMPLETED
  Artifact: "I found 3 potential issues..."

Turn 2:
  POST /message:send
  contextId: "ctx-abc"  (same context!)
  "Elaborate on issue #2"
                                ──────────►  Same session → chat history
                                             includes Turn 1 context
                                ◄──────────
  Task COMPLETED
  Artifact: "The /token endpoint..."
```

**The mechanics:**

1. `contextId` is the conversation thread identifier.
2. `contextId` → `session_id`: deterministic mapping with HMAC salt for non-guessability.
3. Chat history: Langflow's Agent component persists chat history per session.
4. Each turn is a separate Task with its own lifecycle. The `contextId` links them logically.
5. No shared state beyond chat history — each turn is an independent flow execution.

### Server-initiated turns (`INPUT_REQUIRED`)

```
CLIENT AGENT                                LANGFLOW AGENT

  POST /message:stream
  "Deploy my app to production"
                                ──────────►  Agent reasons about request
                                             Agent calls request_input(
                                               "Which environment?")
                                ◄──────────
  TaskStatusUpdateEvent:
    state: INPUT_REQUIRED
    message: "Which environment?"

  POST /message:send (same context + task)
  "prod-us"
                                ──────────►  asyncio.Event resolved
                                             Agent continues reasoning
                                ◄──────────
  Task COMPLETED
  Artifact: "Deployed to prod-us successfully"
```

### What v1 does not support

- Push notifications / webhooks (requires SSRF prevention, URL allowlisting — v2)
- gRPC binding
- Keeping one infinite duplex stream open across all turns

---

## Authentication & Visibility

**Three layers of control:**

1. **Instance-level** — `LANGFLOW_A2A_ENABLED=true/false`. Kill switch for the entire A2A subsystem. When off, all A2A routes return 404.

2. **Flow-level** — `a2a_enabled` flag on the flow. Opt-in per flow. Default is `false`.

3. **Auth-level** — Valid Langflow API key required via `Authorization: Bearer <key>` header.

**Public vs. extended AgentCard:** Public card (no auth) contains basic discovery info. Extended card (auth required) contains full skill definitions and input/output schemas.

**Session ID non-guessability:** `contextId` → `session_id` mapping uses HMAC with per-flow secret salt to prevent a malicious client from guessing another client's session ID.

---

## Error Model

**Public A2A runtime errors:** A2A-compatible HTTP error envelope with machine-usable reason values and task/agent identifiers when available.

**User-visible error messages:**
- "Remote A2A agent unavailable"
- "Remote A2A authentication failed"
- "Remote A2A response format unsupported"
- "A2A task timed out waiting for input"

---

## Production Deployment: Agent Gateway (Optional)

[Agent Gateway](https://agentgateway.dev) is an open-source reverse proxy (Rust, Linux Foundation) purpose-built for A2A and MCP traffic. It can sit in front of Langflow's A2A endpoints as an optional production hardening layer.

**What it provides:** JWT auth, rate limiting, CORS, TLS termination, OpenTelemetry, AgentCard URL rewriting, SSE pass-through, RBAC via Cedar policy engine.

**What it does NOT replace:** AgentCard generation, task state management, flow adapter logic, `request_input` mechanics, session/context management, flow execution.

**Product stance:** Langflow implements the A2A runtime and product UX itself. Agent Gateway is optional. No milestone depends on it.

---

## Upgrade Paths

### v1 → v2: A2A Client Component

Dedicated "A2A Agent" node on the canvas:
- Direct invocation mode: outputs `Message` / structured response
- Tool mode: exposes the remote agent as a tool to a Langflow `Agent`
- Manages its own `contextId` and can send multiple turns
- Surfaces `INPUT_REQUIRED` from remote agents as natural conversation flow

### v1 → v2: Configurable I/O Mapping

Add `input_mapping` and `output_mapping` fields to flow A2A config. Non-breaking. Flows without config continue using conventions.

### v1 → v2: OAuth 2.0

Add OAuth security scheme alongside API key. AgentCard advertises both. No breaking change.

### v1 → v2: Push Notifications

Webhook registration, outbound HTTP delivery with SSRF prevention.

### v1 → v2: Frontend UI

A2A registry page, "Expose as A2A Agent" controls, trace visualization with A2A spans.

---

## Testing Strategy

### Principle: Minimize mocks

Prefer real objects over mocks. Integration tests with actual flow execution, real DB writes, real HTTP calls. Mocks only at true external boundaries (e.g., LLM API calls).

### Unit tests

- AgentCard generation from flow metadata (correct fields, schema compliance)
- Flow adapter translation (A2A Parts → flow inputs, flow outputs → Artifacts)
- Task manager state transitions (all paths including INPUT_REQUIRED)
- `request_input` tool creation, asyncio.Event flow, timeout behavior
- Auth validation

### Integration tests

- Full HTTP round-trip: send A2A message → flow executes → get A2A response
- SSE streaming: connect, verify events arrive in correct order and format
- Multi-turn: two messages with same `contextId`, verify chat history continuity
- `INPUT_REQUIRED`: agent calls `request_input` → verify event → send follow-up → verify resume
- `INPUT_REQUIRED` timeout → verify FAILED
- Multiple `INPUT_REQUIRED` rounds within one task
- Idempotent retry: same `taskId` after completion → cached result
- Error paths: flow exception → `TASK_STATE_FAILED`
- Auth enforcement on all non-public endpoints

### Protocol compliance tests

- Validate AgentCard against A2A JSON schema
- Validate all SSE events against A2A event schema
- Use `a2a-sdk` built-in validation
- Run as part of CI to catch protocol drift

---

## Dependencies

- [`a2a-sdk`](https://pypi.org/project/a2a-sdk/) — Python SDK for A2A protocol serialization, validation, and types
- Langflow's existing: FastAPI, SQLAlchemy/Alembic (DB), flow execution engine, auth system, SSE/callback infrastructure

---

## Success Metrics

### Adoption (first 3 months post-launch)

| Metric | Target |
|---|---|
| Flows with A2A enabled | 100+ across all instances |
| A2A messages received | 1,000+ total |
| Multi-turn conversations | 20%+ of tasks share a `contextId` |
| `INPUT_REQUIRED` usage | 10%+ of tasks enter `INPUT_REQUIRED` |
| Unique API keys calling A2A | 50+ distinct callers |

### Quality (ongoing)

| Metric | Target |
|---|---|
| A2A task success rate | 90%+ reach `COMPLETED` |
| AgentCard schema compliance | 100% |
| Median response latency (sync) | < 2x baseline flow execution time |

---

## Rollout Plan

### Phase 1: Internal alpha (Weeks 1-2 post-implementation)

- `LANGFLOW_A2A_ENABLED` defaults to `false`
- Internal team only
- Test against A2A Inspector, Google ADK, LangChain Agent Server

### Phase 2: Closed beta (Weeks 3-4)

- Enabled per-instance for 5-10 design partners
- Gather real-world feedback

### Phase 3: Public beta (Weeks 5-6)

- `LANGFLOW_A2A_ENABLED` defaults to `true`, flows still opt-in
- Blog post, docs, changelog

### Phase 4: GA (Week 7+)

- Remove feature flag
- Full documentation, starter templates

### Rollback

Setting `LANGFLOW_A2A_ENABLED=false` immediately disables all A2A endpoints (404). No data loss.

---

## Decision Log

| # | Decision | Alternatives Considered | Why |
|---|---|---|---|
| 1 | Server first, client second | Client first, both simultaneously | Server fills the bigger gap. Client can test against own server later. |
| 2 | Per-flow AgentCards with `agent_slug` | Per-instance, flow_id in URL | Matches Langflow's mental model. Human-readable URLs. Stable identity. |
| 3 | Thin FastAPI layer | Sidecar, plugin system, MCP-only, deep graph-native | Reuses all existing infra. Simplest path. Follows MCP integration pattern. |
| 4 | SSE streaming from day one | Sync-only first | Multi-step agents need progress feedback. SSE is A2A primary mode. |
| 5 | API key auth for v1, OAuth roadmapped | OAuth from start, no auth | Ships fast with existing infra. |
| 6 | `INPUT_REQUIRED` in v1 via auto-injected `request_input` tool | Defer to v2, dedicated canvas node, heuristic detection, explicit runtime signal | Without INPUT_REQUIRED, v1 is protocol theater. Auto-injected tool is elegant: no canvas changes, agent decides autonomously. |
| 7 | Convention over configuration for I/O | Full configurable mapping | Simpler v1. Non-breaking upgrade path. |
| 8 | Protocol adapter, not agent wrapper | Wrap flows in conversational agent | Flows handle their own logic. Wrapper adds latency for no benefit. |
| 9 | A2A config fields on Flow model | Separate FlowA2AConfig table | Follows MCP pattern. Minimizes joins. |
| 10 | Separate A2ATask table | Reuse existing jobs system | A2A task lifecycle has distinct fields (context_id, artifacts, input_required state) that don't map cleanly to existing jobs. Clean separation avoids impedance mismatch. |
| 11 | URL scheme: `/a2a/{agent_slug}/v1/...` | `/a2a/flows/{flow_id}/...`, flat paths | Aligned with `a2a-sdk` `rpc_url` mechanism. Matches LangChain's approach. Human-readable. |
| 12 | `asyncio.Event` for INPUT_REQUIRED suspension | Checkpoint/serialize, re-execute from scratch | Simplest real implementation. Acceptable for team-scale. 5-min timeout prevents resource leaks. |
| 13 | Minimize mocks in tests | Heavy mocking | Real objects catch integration bugs that mocks hide. |
| 14 | Target A2A v0.3 stable | v1.0 alpha | v0.3 has stable SDK support. Clear upgrade path. |
| 15 | A2A and MCP as distinct product surfaces | Merge into one | Semantically different: tools vs peers. Merging would confuse users. |

---

## Open Questions

- Should there be a catalog endpoint at `/.well-known/agent-card.json` (root) that lists all exposed agents?
- Should the public AgentCard be fully open or require a separate "discovery key"?
- How should file-type flow inputs/outputs map to A2A `url`/`raw` Parts in practice?
- UI for managing A2A config — API-only for v1, but when does UI ship?
