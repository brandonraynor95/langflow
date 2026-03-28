#!/usr/bin/env python3
"""A2A client script for testing Langflow's A2A server.

Sends messages to a Langflow A2A agent and handles multi-turn
conversations including INPUT_REQUIRED (agent asks for clarification).

Usage:
    # Interactive mode — chat with the agent
    python test-a2a-client.py --slug my-agent

    # Single message
    python test-a2a-client.py --slug my-agent --message "Deploy my app"

    # Streaming mode
    python test-a2a-client.py --slug my-agent --stream

    # Custom Langflow URL
    python test-a2a-client.py --slug my-agent --url http://localhost:7860

Setup:
    1. Start Langflow: uv run langflow run
    2. Build a flow with ChatInput → Agent → ChatOutput
    3. Configure the Agent's LLM (OpenAI, etc.)
    4. Enable A2A on the flow via the UI (A2A Agents tab) or API:
       curl -X PUT http://localhost:7860/api/v1/flows/<id>/a2a-config \\
         -H "Authorization: Bearer <token>" \\
         -H "Content-Type: application/json" \\
         -d '{"a2a_enabled": true, "a2a_agent_slug": "my-agent"}'
    5. Run this script

To test INPUT_REQUIRED specifically:
    Set the Agent's system message to something like:
    "Before performing any action, always ask the user to confirm
    by using the request_input tool. Ask what environment they want."
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

import httpx


def get_token(base_url: str, username: str, password: str) -> str | None:
    """Login and get a bearer token."""
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]
    except Exception as e:
        print(f"  Login failed: {e}")
    return None


def discover_agent(base_url: str, slug: str) -> dict | None:
    """Fetch the AgentCard (no auth needed)."""
    resp = httpx.get(
        f"{base_url}/a2a/{slug}/.well-known/agent-card.json",
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    print(f"  Agent not found: {resp.status_code} {resp.text}")
    return None


def send_message(
    base_url: str,
    slug: str,
    text: str,
    headers: dict,
    context_id: str,
    task_id: str | None = None,
) -> dict:
    """Send a message via POST /message:send."""
    payload: dict = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "contextId": context_id,
        },
    }
    if task_id:
        payload["taskId"] = task_id

    resp = httpx.post(
        f"{base_url}/a2a/{slug}/v1/message:send",
        json=payload,
        headers=headers,
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"  Error: {resp.status_code} {resp.text}")
        return {"status": {"state": "failed"}}
    return resp.json()


def send_message_stream(
    base_url: str,
    slug: str,
    text: str,
    headers: dict,
    context_id: str,
) -> dict | None:
    """Send a message via POST /message:stream and print events."""
    payload = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "contextId": context_id,
        },
    }

    last_task = None
    with httpx.stream(
        "POST",
        f"{base_url}/a2a/{slug}/v1/message:stream",
        json=payload,
        headers=headers,
        timeout=120,
    ) as resp:
        if resp.status_code != 200:
            print(f"  Error: {resp.status_code}")
            return None

        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            kind = event.get("kind", "")

            if kind == "status-update":
                state = event["status"]["state"]
                msg = ""
                status_msg = event.get("status", {}).get("message", {})
                if status_msg:
                    parts = status_msg.get("parts", [])
                    msg = " ".join(p.get("text", "") for p in parts)
                print(f"  [{state}] {msg}")
                last_task = event

            elif kind == "artifact-update":
                artifact = event.get("artifact", {})
                for part in artifact.get("parts", []):
                    if part.get("kind") == "text":
                        print(part["text"], end="", flush=True)
                print()

    return last_task


def get_artifact_text(task: dict) -> str:
    """Extract text from a task's artifacts."""
    texts = []
    for artifact in task.get("artifacts", []):
        for part in artifact.get("parts", []):
            if part.get("kind") == "text":
                texts.append(part["text"])
    return "\n".join(texts)


def get_status_message(task: dict) -> str:
    """Extract the status message from a task."""
    msg = task.get("status", {}).get("message", {})
    if not msg:
        return ""
    parts = msg.get("parts", [])
    return " ".join(p.get("text", "") for p in parts)


def run_conversation(
    base_url: str,
    slug: str,
    headers: dict,
    initial_message: str | None,
    stream: bool,
):
    """Run an interactive conversation with an A2A agent."""
    context_id = str(uuid.uuid4())
    print(f"\n  Context: {context_id}")
    print(f"  Type 'quit' to exit.\n")

    # Get first message
    if initial_message:
        user_input = initial_message
    else:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() == "quit":
            return

    while True:
        # Send message
        if stream:
            task = send_message_stream(
                base_url, slug, user_input, headers, context_id
            )
            if not task:
                break
        else:
            print("  Thinking...")
            task = send_message(
                base_url, slug, user_input, headers, context_id
            )

        state = task.get("status", {}).get("state", "unknown")
        task_id = task.get("taskId") or task.get("id")

        if state == "completed":
            if not stream:
                text = get_artifact_text(task)
                print(f"\nAgent: {text}\n")
            else:
                print()

        elif state == "input-required":
            # The agent is asking for clarification!
            question = get_status_message(task)
            print(f"\nAgent needs input: {question}\n")

            user_input = input("You (follow-up): ").strip()
            if not user_input or user_input.lower() == "quit":
                break

            # Send follow-up to the SAME task
            print("  Sending follow-up...")
            task = send_message(
                base_url, slug, user_input, headers,
                context_id, task_id=task_id,
            )
            state = task.get("status", {}).get("state", "unknown")

            if state == "completed":
                text = get_artifact_text(task)
                print(f"\nAgent: {text}\n")
            elif state == "input-required":
                # Agent asked again — loop back
                continue
            else:
                print(f"\n  Task state: {state}")
                msg = get_status_message(task)
                if msg:
                    print(f"  Message: {msg}")
                break

        elif state == "failed":
            msg = get_status_message(task)
            print(f"\n  Failed: {msg}\n")
            break

        else:
            print(f"\n  Unexpected state: {state}")
            break

        # Next turn
        if not initial_message:
            user_input = input("You: ").strip()
            if not user_input or user_input.lower() == "quit":
                break
        else:
            break  # Single message mode


def main():
    parser = argparse.ArgumentParser(
        description="A2A client for testing Langflow agents"
    )
    parser.add_argument(
        "--slug", required=True, help="Agent slug (e.g. 'my-agent')"
    )
    parser.add_argument(
        "--url", default="http://localhost:7860", help="Langflow base URL"
    )
    parser.add_argument(
        "--message", "-m", help="Send a single message (non-interactive)"
    )
    parser.add_argument(
        "--stream", "-s", action="store_true", help="Use SSE streaming"
    )
    parser.add_argument("--username", default="langflow", help="Login username")
    parser.add_argument("--password", default="langflow", help="Login password")
    parser.add_argument(
        "--discover-only", action="store_true", help="Just fetch and print the AgentCard"
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    # Step 1: Discover
    print(f"\n--- Discovering agent '{args.slug}' ---")
    card = discover_agent(base_url, args.slug)
    if not card:
        sys.exit(1)

    print(f"  Name: {card['name']}")
    print(f"  Description: {card.get('description', 'N/A')}")
    print(f"  Skills: {len(card.get('skills', []))}")
    print(f"  Streaming: {card.get('capabilities', {}).get('streaming', False)}")

    if args.discover_only:
        print(f"\n  Full card:")
        print(json.dumps(card, indent=2))
        return

    # Step 2: Login
    print(f"\n--- Logging in ---")
    token = get_token(base_url, args.username, args.password)
    if not token:
        print("  Failed to login. Check credentials.")
        sys.exit(1)
    print(f"  OK (token: {token[:20]}...)")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Step 3: Conversation
    mode = "streaming" if args.stream else "synchronous"
    print(f"\n--- Starting {mode} conversation ---")
    run_conversation(
        base_url, args.slug, headers, args.message, args.stream
    )


if __name__ == "__main__":
    main()
