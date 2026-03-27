"""Translates between A2A protocol objects and Langflow flow execution.

Inbound: A2A Message parts → flow inputs (input_value, tweaks, session_id).
Outbound: flow run outputs → A2A Artifacts.

The adapter uses convention-based mapping for v1:
- Text parts → input_value (concatenated)
- Data parts → tweaks (merged)
- contextId → session_id (HMAC-based for non-guessability)
"""

from __future__ import annotations

import hashlib
import hmac
import uuid


async def translate_inbound(
    message: dict,
    flow_secret: str,
) -> dict:
    """Translate an A2A Message into Langflow flow execution inputs.

    Args:
        message: The A2A message dict (contains role, parts, contextId).
        flow_secret: Per-flow secret used to HMAC the contextId into
                     a non-guessable session_id.

    Returns:
        A dict with keys matching SimplifiedAPIRequest fields:
        - input_value: str
        - input_type: str ("chat")
        - output_type: str ("chat")
        - tweaks: dict | None
        - session_id: str
    """
    parts = message.get("parts", [])

    # Extract text parts — concatenate into input_value
    text_parts = []
    for part in parts:
        if part.get("kind") == "text":
            text_parts.append(part.get("text", ""))
    input_value = "".join(text_parts)

    # Extract data parts — merge into tweaks
    tweaks = None
    for part in parts:
        if part.get("kind") == "data":
            if tweaks is None:
                tweaks = {}
            tweaks.update(part.get("data", {}))

    # Map contextId → session_id via HMAC
    context_id = message.get("contextId")
    if context_id:
        session_id = _context_id_to_session_id(context_id, flow_secret)
    else:
        # No contextId → generate a unique session (single-turn)
        session_id = f"a2a-{uuid.uuid4().hex[:16]}"

    return {
        "input_value": input_value,
        "input_type": "chat",
        "output_type": "chat",
        "tweaks": tweaks,
        "session_id": session_id,
    }


async def translate_outbound(run_outputs: list) -> list:
    """Translate Langflow run outputs into A2A Artifacts.

    Args:
        run_outputs: List of RunOutputs-like dicts from flow execution.
                     Each contains {inputs: dict, outputs: list[ResultData]}.

    Returns:
        List of A2A Artifact dicts, each with parts (text or data).
    """
    artifacts = []

    for i, run_output in enumerate(run_outputs):
        # run_output can be a dict or an object with .outputs attribute
        if hasattr(run_output, "outputs"):
            output_list = run_output.outputs or []
        else:
            output_list = run_output.get("outputs", [])

        for result in output_list:
            artifact = _result_to_artifact(result, index=i)
            if artifact:
                artifacts.append(artifact)

    return artifacts


def _context_id_to_session_id(context_id: str, flow_secret: str) -> str:
    """Map a contextId to a non-guessable session_id using HMAC.

    The HMAC ensures:
    - Same contextId + same secret = same session (deterministic)
    - Different secrets = different sessions (cross-flow isolation)
    - Cannot reverse-engineer contextId from session_id
    """
    mac = hmac.new(
        flow_secret.encode(),
        context_id.encode(),
        hashlib.sha256,
    )
    return f"a2a-{mac.hexdigest()[:16]}"


def _result_to_artifact(result, index: int = 0) -> dict | None:
    """Convert a single ResultData into an A2A Artifact."""
    # Handle both dict and object access patterns
    if hasattr(result, "results"):
        results = result.results
    else:
        results = result.get("results", {}) if isinstance(result, dict) else {}

    if not results:
        return None

    parts = []

    # Check for text message output
    if isinstance(results, dict):
        message = results.get("message")
        if isinstance(message, dict) and "text" in message:
            parts.append({
                "kind": "text",
                "text": message["text"],
            })
        elif isinstance(message, str):
            parts.append({
                "kind": "text",
                "text": message,
            })

        # Check for structured data output
        data = results.get("data")
        if isinstance(data, dict):
            parts.append({
                "kind": "data",
                "data": data,
            })

    if not parts:
        # Fallback: serialize the entire result as data
        parts.append({
            "kind": "data",
            "data": results if isinstance(results, dict) else {"result": str(results)},
        })

    return {
        "artifactId": f"artifact-{index}",
        "name": f"output-{index}",
        "parts": parts,
    }
