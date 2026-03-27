"""SSE streaming bridge between Langflow events and A2A SSE format.

Translates Langflow EventManager events into A2A-compliant SSE events:
- "token"      → TaskArtifactUpdateEvent (partial text, append=True)
- "end_vertex" → TaskStatusUpdateEvent (state=working, progress)
- "end"        → TaskStatusUpdateEvent (state=completed, final=True)
- "error"      → TaskStatusUpdateEvent (state=failed)

The bridge sits between the Langflow execution engine and the SSE
StreamingResponse. It reads Langflow events from the EventManager queue
and puts translated A2A events onto its output queue.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone


class A2AStreamBridge:
    """Translates Langflow streaming events to A2A SSE events.

    Usage:
        bridge = A2AStreamBridge(task_id="...", context_id="...")

        # Feed Langflow events in (from EventManager queue)
        await bridge.process_langflow_event(raw_event_str)

        # Consume A2A events out (for StreamingResponse)
        event = await bridge.output_queue.get()
    """

    def __init__(self, task_id: str, context_id: str):
        self.task_id = task_id
        self.context_id = context_id
        self.output_queue: asyncio.Queue = asyncio.Queue()

    async def process_langflow_event(self, raw_event: str) -> None:
        """Process a raw Langflow event string and emit A2A SSE events.

        Args:
            raw_event: JSON string from EventManager, format:
                       '{"event": "token", "data": {...}}\\n\\n'
        """
        try:
            parsed = json.loads(raw_event.strip())
        except (json.JSONDecodeError, TypeError):
            return

        event_type = parsed.get("event", "")
        data = parsed.get("data", {})

        if event_type == "token":
            await self._handle_token(data)
        elif event_type == "end":
            await self._handle_end(data)
        elif event_type == "error":
            await self._handle_error(data)
        elif event_type == "end_vertex":
            await self._handle_end_vertex(data)
        # Other events (build_start, build_end, etc.) are silently ignored

    async def finish(self) -> None:
        """Signal the end of the stream with a None sentinel."""
        await self.output_queue.put(None)

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    async def _handle_token(self, data: dict) -> None:
        """Translate a token event to a TaskArtifactUpdateEvent."""
        chunk = data.get("chunk", "")
        if not chunk:
            return

        event = {
            "kind": "artifact-update",
            "taskId": self.task_id,
            "contextId": self.context_id,
            "artifact": {
                "artifactId": f"stream-{self.task_id}",
                "name": "response",
                "parts": [{"kind": "text", "text": chunk}],
            },
            "append": True,
            "lastChunk": False,
        }
        await self.output_queue.put(event)

    async def _handle_end(self, data: dict) -> None:
        """Translate an end event to a completed TaskStatusUpdateEvent."""
        event = {
            "kind": "status-update",
            "taskId": self.task_id,
            "contextId": self.context_id,
            "status": {
                "state": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "final": True,
        }
        await self.output_queue.put(event)

    async def _handle_error(self, data: dict) -> None:
        """Translate an error event to a failed TaskStatusUpdateEvent."""
        error_msg = data.get("error", "Unknown error") if isinstance(data, dict) else str(data)

        event = {
            "kind": "status-update",
            "taskId": self.task_id,
            "contextId": self.context_id,
            "status": {
                "state": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": str(error_msg)}],
                },
            },
            "final": True,
        }
        await self.output_queue.put(event)

    async def _handle_end_vertex(self, data: dict) -> None:
        """Translate an end_vertex event to a working TaskStatusUpdateEvent."""
        vertex_info = data.get("build_data", "step")

        event = {
            "kind": "status-update",
            "taskId": self.task_id,
            "contextId": self.context_id,
            "status": {
                "state": "working",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": f"Completed {vertex_info}"}],
                },
            },
            "final": False,
        }
        await self.output_queue.put(event)
