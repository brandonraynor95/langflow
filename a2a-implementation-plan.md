# A2A Implementation Plan

Detailed, ordered implementation plan for the A2A design in [`a2a-design.md`](./a2a-design.md).

Each phase is independently testable. Complete one before starting the next.

---

## Codebase Reference

Key files and patterns to follow during implementation:

| Purpose | File | Key function/class |
|---|---|---|
| Route registration | `src/backend/base/langflow/api/router.py` | `router_v1.include_router()` |
| MCP route pattern | `src/backend/base/langflow/api/v1/mcp.py` | SSE transport, tool listing |
| Agentic route pattern | `src/backend/base/langflow/agentic/api/router.py` | `@router.post("/execute/{flow_name}")` |
| Flow execution | `src/backend/base/langflow/processing/process.py` | `run_graph_internal()` |
| Run endpoint pattern | `src/backend/base/langflow/api/v1/endpoints.py` | `simplified_run_flow()` (line 546+) |
| Agent tool injection | `src/lfx/src/lfx/base/agents/agent.py` | `LCToolsAgentComponent._get_tools()` |
| Component toolkit | `src/lfx/src/lfx/base/tools/component_tool.py` | `ComponentToolkit` |
| Event streaming | `src/lfx/src/lfx/events/event_manager.py` | `EventManager` |
| Auth dependency | `src/backend/base/langflow/services/auth/utils.py` | `api_key_security()` |
| DB models pattern | `src/backend/base/langflow/services/database/models/flow/model.py` | `Flow(SQLModel)` |
| Alembic migrations | `src/backend/base/langflow/alembic/versions/` | `upgrade()`/`downgrade()` |
| App lifespan | `src/backend/base/langflow/main.py` | `create_app()`, `get_lifespan()` |

---

## Phase 1: AgentCard Generation & Discovery

**Goal:** A Langflow flow can publish a discoverable AgentCard at a well-known URL.

### 1.1 Create the A2A module structure

Create the new module:

```
src/backend/base/langflow/api/a2a/
├── __init__.py
├── router.py
├── config.py
├── agent_card.py
├── task_manager.py        (stub)
├── flow_adapter.py        (stub)
├── streaming.py           (stub)
└── request_input_tool.py  (stub)
```

Stub files contain empty classes/functions with docstrings and `pass` / `raise NotImplementedError`. This establishes the module shape early.

### 1.2 Flow A2A metadata fields

**File:** `src/backend/base/langflow/services/database/models/flow/model.py`

Add fields to the Flow model:

```python
a2a_enabled: bool = Field(default=False)
a2a_name: str | None = Field(default=None)
a2a_description: str | None = Field(default=None)
a2a_agent_slug: str | None = Field(default=None, index=True)
a2a_input_mode: str = Field(default="chat")
a2a_output_mode: str = Field(default="text")
```

Create Alembic migration: `make alembic-revision message="Add A2A metadata fields to flow table"`

**Validation rules:**
- Only flows with Chat Input + Agent/LLM + Chat Output are eligible
- `a2a_agent_slug` must be unique per owner scope
- Slug format: lowercase alphanumeric + hyphens, 3-64 chars

### 1.3 AgentCard generation

**File:** `src/backend/base/langflow/api/a2a/agent_card.py`

- Function: `generate_agent_card(flow: Flow, base_url: str) -> AgentCard`
- Uses `a2a-sdk` types (`AgentCard`, `AgentSkill`, `AgentCapabilities`, etc.)
- Maps `flow.a2a_name` (or `flow.name`) → agent name
- Maps `flow.a2a_description` (or `flow.description`) → agent description
- Derives skill from flow input/output schema
- Sets capabilities: `streaming=True`, `pushNotifications=False`, `stateTransitionHistory=False`
- Populates `securitySchemes` with bearer token

### 1.4 Router with AgentCard endpoints

**File:** `src/backend/base/langflow/api/a2a/router.py`

Public A2A endpoints:
- `GET /a2a/{agent_slug}/.well-known/agent-card.json` — Public AgentCard (no auth)
- `GET /a2a/{agent_slug}/v1/card` — Auth-gated extended card

Internal admin endpoints:
- `PUT /api/v1/flows/{flow_id}/a2a-config` — Enable/configure A2A (requires auth)
- `GET /api/v1/flows/{flow_id}/a2a-config` — Read A2A config (requires auth)

Register in `src/backend/base/langflow/api/router.py` following the lazy-loaded agentic router pattern.

### 1.5 Instance-level toggle

Add `LANGFLOW_A2A_ENABLED` env var to settings. When `false`, the A2A router returns 404 for all routes.

### 1.6 `a2a-sdk` dependency

Add `a2a-sdk` to `src/backend/base/pyproject.toml` dependencies. Pin to latest stable version.

### 1.7 Tests

**Unit tests** (`src/backend/tests/unit/api/a2a/test_agent_card.py`):
- AgentCard generated from flow metadata has correct structure
- AgentCard validates against A2A JSON schema (use `a2a-sdk` validation)
- Missing flow description → sensible default
- Flow with complex inputs → skill schema reflects them

**Unit tests** (`src/backend/tests/unit/api/a2a/test_config.py`):
- Config CRUD: create, read, update
- Default config values
- Slug uniqueness validation
- Eligibility validation (reject non-agent flows)

**Integration tests** (`src/backend/tests/integration/api/a2a/test_discovery.py`):
- `GET /.well-known/agent-card.json` for an enabled flow → 200 with valid AgentCard
- `GET /.well-known/agent-card.json` for a disabled flow → 404
- `GET /.well-known/agent-card.json` when `LANGFLOW_A2A_ENABLED=false` → 404
- `PUT /a2a-config` without auth → 401
- `PUT /a2a-config` with auth → 200, config persisted

### Phase 1 exit criteria

- [ ] A flow with `a2a_enabled=True` serves a valid AgentCard at the well-known URL
- [ ] A flow with `a2a_enabled=False` returns 404
- [ ] Instance toggle works
- [ ] Config CRUD works with auth
- [ ] Slug uniqueness enforced
- [ ] Flow eligibility validated
- [ ] All tests pass

---

## Phase 2: Synchronous Message Handling (`message:send`)

**Goal:** An external agent can send a message and get a response (blocking).

### 2.1 Flow adapter — inbound translation

**File:** `src/backend/base/langflow/api/a2a/flow_adapter.py`

- Function: `async def translate_inbound(message: Message, flow: Flow) -> FlowInputs`
- Extracts `text` parts → `input_value`
- Extracts `data` parts → tweaks dict
- Maps `contextId` → `session_id` (HMAC: `hmac.new(flow_secret, context_id.encode(), 'sha256').hexdigest()[:16]`, prefixed with `a2a-`)
- Returns inputs compatible with `run_graph_internal()`

### 2.2 Flow adapter — outbound translation

- Function: `async def translate_outbound(run_outputs: list[RunOutputs]) -> list[Artifact]`
- Text output → `Artifact` with `TextPart`
- Structured output → `Artifact` with `DataPart`
- File output → `Artifact` with `FilePart` (URL pointing to Langflow file endpoint)

### 2.3 Task manager — basic lifecycle

**File:** `src/backend/base/langflow/api/a2a/task_manager.py`

DB model: `A2ATask` (as defined in design doc).

Create Alembic migration: `make alembic-revision message="Add A2A task table"`

Core methods:
- `create_task(flow_id, context_id, task_id?) -> A2ATask`
- `update_state(task_id, state, artifacts?, error?)`
- `get_task(task_id) -> A2ATask`
- `list_tasks(context_id?) -> list[A2ATask]`
- `handle_retry(task_id) -> A2ATask | None` — returns cached result if completed

### 2.4 Synchronous endpoint

**File:** `src/backend/base/langflow/api/a2a/router.py`

`POST /a2a/{agent_slug}/v1/message:send`

Implementation flow:
1. Resolve `agent_slug` → flow
2. Validate auth via `Depends(api_key_security)`
3. Check flow A2A config is enabled
4. Check idempotent retry (same `taskId` → return cached result)
5. Create `A2ATask` (SUBMITTED)
6. Translate inbound message via `flow_adapter`
7. Update task → WORKING
8. Call `run_graph_internal()` (following `simplified_run_flow` pattern)
9. Translate outbound results via `flow_adapter`
10. Update task → COMPLETED with artifacts
11. Return A2A Task response
12. On error: update task → FAILED, return error

### 2.5 Task endpoints

- `GET /a2a/{agent_slug}/v1/tasks/{task_id}` — Poll task state (requires auth)
- `GET /a2a/{agent_slug}/v1/tasks` — List tasks, filterable by `contextId` (requires auth)
- `POST /a2a/{agent_slug}/v1/tasks/{task_id}:cancel` — Request cancellation (requires auth)

### 2.6 Tests

**Unit tests** (`src/backend/tests/unit/api/a2a/test_flow_adapter.py`):
- Text Part → `input_value` mapping
- Data Part → tweaks mapping
- `contextId` → `session_id` deterministic HMAC mapping
- Flow text output → text Artifact
- Flow structured output → data Artifact

**Unit tests** (`src/backend/tests/unit/api/a2a/test_task_manager.py`):
- State transitions: SUBMITTED → WORKING → COMPLETED
- State transitions: SUBMITTED → WORKING → FAILED
- Idempotent retry: completed task returns cached result
- Idempotent retry: failed task allows re-execution

**Integration tests** (`src/backend/tests/integration/api/a2a/test_message_send.py`):
- Send text message → flow executes → get response with artifacts
- Send message to disabled flow → 404
- Send message without auth → 401
- Send message with `data` Part → tweaks applied correctly
- Flow that errors → TASK_STATE_FAILED response
- Same `taskId` re-sent after completion → cached result returned
- Poll `GET /tasks/{task_id}` → correct state

### Phase 2 exit criteria

- [ ] `message:send` executes a flow and returns A2A-formatted response
- [ ] Auth, visibility, and error handling work
- [ ] Idempotent retry works
- [ ] Task polling and listing work
- [ ] Cancellation sets state to CANCELED
- [ ] All tests pass

---

## Phase 3: Multi-Turn Conversations

**Goal:** Multiple messages with the same `contextId` maintain conversation history.

### 3.1 Session continuity

The `flow_adapter` already maps `contextId` → `session_id`. This phase verifies that Langflow's Agent component correctly picks up chat history across turns.

No new code may be needed — this might work out of the box from Phase 2's mapping. The key is testing.

### 3.2 Context tracking

Ensure the task manager correctly links tasks by `context_id`:
- Each turn creates a new task with a new `task_id` but the same `context_id`
- `session_id` is derived from `context_id`, not `task_id`

### 3.3 Tests

**Integration tests** (`src/backend/tests/integration/api/a2a/test_multi_turn.py`):
- Send message 1 with `contextId: "abc"` → get response
- Send message 2 with `contextId: "abc"` referencing message 1 content → agent has context
- Send message with new `contextId: "def"` → agent has no prior context
- Three-turn conversation → agent accumulates full history
- Use a simple Agent flow (with mock LLM) that echoes back conversation history to verify continuity

### Phase 3 exit criteria

- [ ] Multi-turn conversations work via `contextId`
- [ ] Chat history is preserved across turns
- [ ] Different `contextId` values are isolated
- [ ] All tests pass

---

## Phase 4: SSE Streaming (`message:stream`)

**Goal:** Clients receive real-time SSE events during flow execution.

### 4.1 Streaming bridge

**File:** `src/backend/base/langflow/api/a2a/streaming.py`

- Class: `A2AStreamBridge`
- Takes Langflow's `EventManager` events and translates them to A2A SSE events
- Uses `asyncio.Queue` as the bridge (same pattern as `endpoints.py` streaming)
- Yields `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent` as SSE `data:` lines

Event translation:
```python
async def translate_event(self, event: dict) -> A2ASSEEvent | None:
    match event["event"]:
        case "token":
            return TaskArtifactUpdateEvent(...)  # Partial text
        case "end_vertex":
            return TaskStatusUpdateEvent(state="working", message=f"Completed {vertex}")
        case "end":
            return TaskStatusUpdateEvent(state="completed")
        case "error":
            return TaskStatusUpdateEvent(state="failed", ...)
```

### 4.2 Streaming endpoint

`POST /a2a/{agent_slug}/v1/message:stream`

Returns `StreamingResponse` with `media_type="text/event-stream"`:
1. Create `asyncio.Queue`
2. Create `EventManager` feeding into queue
3. Run flow in `asyncio.create_task()` (background)
4. Yield SSE events from queue via `A2AStreamBridge`
5. On flow completion, yield final COMPLETED event
6. On client disconnect, flow still completes (results stored in task record)

### 4.3 Task subscribe endpoint

`GET /a2a/{agent_slug}/v1/tasks/{task_id}:subscribe` — SSE stream for an already-running task.

Implementation: task manager maintains a registry of active `asyncio.Queue`s per task. Subscribe creates a new consumer for the same queue.

### 4.4 Tests

**Integration tests** (`src/backend/tests/integration/api/a2a/test_streaming.py`):
- Connect to `message:stream` → receive WORKING event → receive artifact events → receive COMPLETED event
- Verify SSE event format matches A2A spec
- Token streaming → partial text artifacts arrive incrementally
- Client disconnect mid-stream → task still completes (verify via `GET /tasks/{id}`)
- Subscribe to existing task → receive remaining events
- Stream a flow that errors → receive FAILED event

### Phase 4 exit criteria

- [ ] SSE streaming works end-to-end
- [ ] Events are correctly formatted per A2A spec
- [ ] Client disconnect is handled gracefully
- [ ] Task subscribe works for reconnection
- [ ] All tests pass

---

## Phase 5: `request_input` Tool & `INPUT_REQUIRED`

**Goal:** The Langflow agent can ask the calling agent for clarification mid-execution.

This is the most complex phase. It introduces a new execution pattern: mid-flow suspension.

### 5.1 The `request_input` tool

**File:** `src/backend/base/langflow/api/a2a/request_input_tool.py`

```python
class RequestInputSchema(BaseModel):
    question: str = Field(description="The question to ask the calling agent")

def create_request_input_tool(task_id: str, task_manager: TaskManager) -> StructuredTool:
    """Create a request_input tool bound to a specific A2A task."""

    event = asyncio.Event()
    response_holder = {}  # Mutable container for the response

    async def request_input_handler(question: str) -> str:
        # 1. Signal INPUT_REQUIRED via task manager
        task_manager.request_input(task_id, question)

        # 2. Await client response (with timeout)
        try:
            await asyncio.wait_for(event.wait(), timeout=300)
        except asyncio.TimeoutError:
            raise ToolException("Client did not respond within timeout")

        # 3. Return client's response as tool result
        return response_holder["response"]

    return StructuredTool(
        name="request_input",
        description="Ask the calling agent for clarification or additional information.",
        coroutine=request_input_handler,
        args_schema=RequestInputSchema,
    )

def resolve_input(event: asyncio.Event, response_holder: dict, response: str):
    """Called by flow_adapter when client sends follow-up message."""
    response_holder["response"] = response
    event.set()
```

### 5.2 Tool injection into Agent component

Inject the `request_input` tool when executing a flow via A2A.

**Key integration point:** `LCToolsAgentComponent._get_tools()` in `src/lfx/src/lfx/base/agents/agent.py`

**Approach: Inject via execution context.** Add a hook in the Agent component that checks if the current execution is A2A-originated (via a flag in the session/context). If so, auto-add `request_input` to the toolkit.

```python
# In LCToolsAgentComponent._get_tools() or build_agent()
if self._is_a2a_execution():
    from langflow.api.a2a.request_input_tool import create_request_input_tool
    tools.append(create_request_input_tool(
        task_id=self._get_a2a_task_id(),
        task_manager=self._get_a2a_task_manager(),
    ))
```

The A2A execution context (task_id, task_manager reference) is passed through the session/graph metadata, set by the flow_adapter before execution begins.

### 5.3 Task manager — INPUT_REQUIRED state

Add to `task_manager.py`:
- `request_input(task_id, question)` — sets state to `INPUT_REQUIRED`, stores the question, stores `asyncio.Event` reference
- `resolve_input(task_id, response)` — resolves the event, sets state back to WORKING
- Active input requests tracked in-memory: `dict[task_id, (event, response_holder)]`

### 5.4 Follow-up message handling

When a client sends a message to a task in `INPUT_REQUIRED` state:

`POST /a2a/{agent_slug}/v1/message:send` — router checks if the referenced task is in `INPUT_REQUIRED`:
- If yes: extract text, call `task_manager.resolve_input(task_id, text)`, return acknowledgment
- If no: treat as a new turn (Phase 3 multi-turn path)

### 5.5 Streaming integration

When `request_input` is called:
1. `A2AStreamBridge` emits `TaskStatusUpdateEvent` → `input-required` with the question as message
2. Stream stays open (SSE connection held)
3. When client responds and flow resumes, bridge emits `TaskStatusUpdateEvent` → `working`
4. Flow continues, more events follow
5. Eventually `completed`

### 5.6 Timeout handling

Default: 5 minutes. Configurable via `LANGFLOW_A2A_INPUT_TIMEOUT`.

On timeout:
- `asyncio.TimeoutError` caught in `request_input_handler`
- Raises `ToolException` — Agent LLM receives error as tool result
- Agent can either continue without the info or give up
- Task state determined by agent's final output

### 5.7 Tests

**Unit tests** (`src/backend/tests/unit/api/a2a/test_request_input.py`):
- `request_input` tool creation and schema validation
- `asyncio.Event` flow: create tool → call handler (suspends) → resolve → handler returns response
- Timeout: call handler → don't resolve → verify `ToolException` after timeout
- Multiple calls: first resolves, second resolves independently

**Integration tests** (`src/backend/tests/integration/api/a2a/test_input_required.py`):
- Agent flow calls `request_input` → SSE emits `INPUT_REQUIRED` → client sends follow-up → agent continues → COMPLETED
- Agent calls `request_input` twice → two `INPUT_REQUIRED` rounds → both resolved → COMPLETED
- Agent calls `request_input` → client doesn't respond → timeout → task FAILED
- Non-agent flow (pure DAG) → `request_input` tool not injected → flow runs normally

### Phase 5 exit criteria

- [ ] `request_input` tool auto-injected for A2A executions
- [ ] Agent LLM can autonomously call `request_input`
- [ ] `INPUT_REQUIRED` SSE event emitted correctly
- [ ] Client follow-up resolves the suspended execution
- [ ] Multiple INPUT_REQUIRED rounds work
- [ ] Timeout produces graceful failure
- [ ] Non-agent flows unaffected
- [ ] All tests pass

### Phase 5 audit: gaps identified during implementation (2026-03-27)

The following gaps were identified during Phase 5 implementation review.
The low-level mechanics (asyncio.Event suspension, task manager state
transitions, follow-up routing) are implemented and tested, but wiring
into the actual execution path is incomplete.

**Gap 1: Tool not injected into Agent component**

The `create_request_input_tool()` function exists and works, but nothing
calls it during flow execution. The plan calls for modifying
`LCToolsAgentComponent._get_tools()` to detect A2A execution context and
inject the tool. This requires:
- Passing A2A execution context (task_id, task_manager ref) through the
  graph metadata / session context
- A hook in the Agent component to check for A2A context and add the tool
- The context must be set by the router before calling `simple_run_flow()`

**Gap 2: INPUT_REQUIRED incompatible with synchronous message:send**

The `message:send` endpoint awaits `_execute_flow()` which awaits
`simple_run_flow()`. If the Agent calls `request_input` during execution,
the entire chain is blocked — the HTTP response never returns, so the
client never sees INPUT_REQUIRED and can't send a follow-up.

INPUT_REQUIRED only works with `message:stream` where the SSE connection
stays open and can emit INPUT_REQUIRED while the flow is suspended.

Resolution options:
- A: Only support INPUT_REQUIRED via `message:stream` (natural fit)
- B: Make `message:send` return early with WORKING/INPUT_REQUIRED state,
  client then polls or uses streaming
- C: Run flow in background task for message:send, return task immediately

**Gap 3: Streaming endpoint doesn't wire INPUT_REQUIRED events**

The `message:stream` endpoint executes the flow in a background task but
uses a simple try/complete/fail pattern. It doesn't wire the stream bridge
to emit INPUT_REQUIRED events when the tool is called, or WORKING events
when the input is resolved.

**Gap 4: Integration tests simulate INPUT_REQUIRED manually**

The integration tests set task state to INPUT_REQUIRED by directly poking
`_task_manager` rather than testing actual flow execution triggering the
tool. This was necessary because of Gap 1 (tool not injected), but means
the full end-to-end path is untested.

**Resolution plan:**
- Fix Gap 1: Pass A2A context through graph metadata, inject tool
- Fix Gap 2: Adopt Option A — INPUT_REQUIRED only via message:stream
- Fix Gap 3: Wire stream bridge to receive INPUT_REQUIRED events from tool
- Fix Gap 4: Add end-to-end test with mock LLM that calls request_input

---

## Phase 6: Auth, Visibility & Hardening

**Goal:** Production-ready auth and security controls.

### 6.1 Auth enforcement

All A2A endpoints (except public AgentCard) require `Depends(api_key_security)`.

Verify:
- Public AgentCard (`/.well-known/agent-card.json`) — no auth required
- Extended card (`/v1/card`) — auth required
- `message:send`, `message:stream` — auth required
- Task endpoints — auth required
- Config management — auth required

### 6.2 Rate limiting

Add basic rate limiting to A2A endpoints:
- Use `slowapi` or simple in-memory rate limiting per API key
- Default: 60 requests/minute per API key
- Configurable via `LANGFLOW_A2A_RATE_LIMIT`

### 6.3 Session ID non-guessability

Confirm the HMAC-based `contextId` → `session_id` mapping from Phase 2 is working correctly. Different API keys with same `contextId` should produce different sessions.

### 6.4 Task TTL cleanup

Add a background task (registered in app lifespan) that periodically prunes `A2ATask` records older than `LANGFLOW_A2A_TASK_TTL` (default 24h). Active tasks (WORKING, INPUT_REQUIRED) are never pruned.

### 6.5 Request size limits

Add request body size limits to A2A message endpoints. Default 1MB, configurable.

### 6.6 Tests

**Integration tests** (`src/backend/tests/integration/api/a2a/test_auth.py`):
- All protected endpoints return 401 without auth
- Valid API key → access granted
- Rate limit exceeded → 429
- Session isolation: two different API keys with same `contextId` → different sessions

**Integration tests** (`src/backend/tests/integration/api/a2a/test_cleanup.py`):
- Create tasks → wait for TTL → verify pruned
- Active tasks (WORKING, INPUT_REQUIRED) not pruned even if old

### Phase 6 exit criteria

- [ ] Auth enforced on all non-public endpoints
- [ ] Rate limiting works
- [ ] Session IDs are non-guessable
- [ ] TTL cleanup runs and prunes old tasks
- [ ] Active tasks protected from cleanup
- [ ] All tests pass

---

## Phase 7: Protocol Compliance & Polish

**Goal:** Validate full A2A spec compliance and clean up.

### 7.1 Protocol compliance tests

Use `a2a-sdk` validation to verify:
- AgentCard schema compliance
- All SSE event schemas
- Task state enum values match spec
- Message/Part/Artifact format
- Error response format

### 7.2 End-to-end smoke test

A single integration test that exercises the full lifecycle:
1. Create a flow with an Agent component
2. Enable A2A on it via config endpoint
3. Discover AgentCard at well-known URL
4. Send `message:stream`
5. Agent asks for clarification (`INPUT_REQUIRED`)
6. Respond to clarification
7. Receive final result (COMPLETED)
8. Poll task → confirms COMPLETED with artifacts
9. Send follow-up in same context → multi-turn works
10. Cancel a running task → CANCELED

### 7.3 Documentation

- Add inline docstrings to all public functions in the `a2a/` module
- Create an example/starter flow that demonstrates A2A usage
- Document environment variables and configuration options

### Phase 7 exit criteria

- [ ] All protocol compliance tests pass
- [ ] End-to-end smoke test passes
- [ ] Documentation written
- [ ] All tests pass

---

## Dependency Order

```
Phase 1: AgentCard & Discovery
    │
    ▼
Phase 2: message:send (sync)
    │
    ▼
Phase 3: Multi-turn conversations ──────► (may be trivial if Phase 2 session mapping works)
    │
    ▼
Phase 4: SSE streaming
    │
    ▼
Phase 5: request_input & INPUT_REQUIRED ──► (most complex phase)
    │
    ▼
Phase 6: Auth & hardening
    │
    ▼
Phase 7: Compliance & polish
```

Phases 1-3 build the core. Phase 4 adds streaming. Phase 5 adds the differentiating feature. Phases 6-7 harden for production.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `asyncio.Event` suspension holds memory for idle INPUT_REQUIRED tasks | Medium | Low (team-scale) | 5-min timeout, TTL cleanup, monitor memory |
| `a2a-sdk` v0.3 API changes before v1.0 stabilizes | Medium | Medium | Pin SDK version, isolate protocol types behind adapter |
| Agent LLM doesn't reliably use `request_input` tool | Medium | Medium | Good tool description, test with multiple LLM providers |
| Flow inputs too complex for convention-based mapping | Low | Low | Document limitations, configurable mapping is a clean v2 upgrade |
| Server restart kills suspended INPUT_REQUIRED flows | Medium | Low (team-scale) | Document limitation, timeout means max 5 min of lost work |
| Slug collision across users/projects | Low | Medium | Enforce uniqueness constraint at DB level with owner scope |
