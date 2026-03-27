"""Translates between A2A protocol objects and Langflow flow execution.

Inbound: A2A Message parts -> flow inputs (input_value, tweaks, session_id).
Outbound: flow run outputs -> A2A Artifacts.
"""

from __future__ import annotations


async def translate_inbound(message: dict, flow_data: dict) -> dict:
    """Translate an A2A Message into Langflow flow inputs."""
    raise NotImplementedError


async def translate_outbound(run_outputs: list) -> list:
    """Translate Langflow run outputs into A2A Artifacts."""
    raise NotImplementedError
