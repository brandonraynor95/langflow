from datetime import datetime, timezone
from urllib.parse import quote
from uuid import UUID

import pytest
from httpx import AsyncClient
from langflow.memory import aadd_messagetables

# Assuming you have these imports available
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.message import MessageCreate, MessageRead, MessageUpdate
from langflow.services.database.models.message.model import MessageTable
from langflow.services.database.models.user.model import User, UserRead
from langflow.services.deps import get_auth_service, session_scope
from sqlmodel import select


@pytest.fixture
async def created_message(active_user):
    async with session_scope() as session:
        # Create a flow for the user so messages can be filtered by user
        flow = Flow(name="test_flow_for_message", user_id=active_user.id, data={"nodes": [], "edges": []})
        session.add(flow)
        await session.flush()

        message = MessageCreate(text="Test message", sender="User", sender_name="User", session_id="session_id")
        messagetable = MessageTable.model_validate(message, from_attributes=True)
        messagetable.flow_id = flow.id
        messagetables = await aadd_messagetables([messagetable], session)
        return MessageRead.model_validate(messagetables[0], from_attributes=True)


@pytest.fixture
async def created_messages(session, active_user):  # noqa: ARG001
    async with session_scope() as _session:
        # Create a flow for the user so messages can be filtered by user
        flow = Flow(name="test_flow_for_messages", user_id=active_user.id, data={"nodes": [], "edges": []})
        _session.add(flow)
        await _session.flush()

        messages = [
            MessageCreate(text="Test message 1", sender="User", sender_name="User", session_id="session_id2"),
            MessageCreate(text="Test message 2", sender="User", sender_name="User", session_id="session_id2"),
            MessageCreate(text="Test message 3", sender="AI", sender_name="AI", session_id="session_id2"),
        ]
        messagetables = [MessageTable.model_validate(message, from_attributes=True) for message in messages]
        for mt in messagetables:
            mt.flow_id = flow.id
        return await aadd_messagetables(messagetables, _session)


@pytest.fixture
async def messages_with_datetime_session_id(session, active_user):  # noqa: ARG001
    """Create messages with datetime-like session IDs that contain characters requiring URL encoding."""
    datetime_session_id = "2024-01-15 10:30:45 UTC"  # Contains spaces and colons
    async with session_scope() as _session:
        # Create a flow for the user so messages can be filtered by user
        flow = Flow(name="test_flow_for_datetime_messages", user_id=active_user.id, data={"nodes": [], "edges": []})
        _session.add(flow)
        await _session.flush()

        messages = [
            MessageCreate(text="Datetime message 1", sender="User", sender_name="User", session_id=datetime_session_id),
            MessageCreate(text="Datetime message 2", sender="AI", sender_name="AI", session_id=datetime_session_id),
        ]
        messagetables = [MessageTable.model_validate(message, from_attributes=True) for message in messages]
        for mt in messagetables:
            mt.flow_id = flow.id
        created_messages = await aadd_messagetables(messagetables, _session)
        return created_messages, datetime_session_id


@pytest.mark.api_key_required
async def test_delete_messages(client: AsyncClient, created_messages, logged_in_headers):
    response = await client.request(
        "DELETE", "api/v1/monitor/messages", json=[str(msg.id) for msg in created_messages], headers=logged_in_headers
    )
    assert response.status_code == 204, response.text
    assert response.reason_phrase == "No Content"


@pytest.mark.api_key_required
async def test_update_message(client: AsyncClient, logged_in_headers, created_message):
    message_id = created_message.id
    message_update = MessageUpdate(text="Updated content")
    response = await client.put(
        f"api/v1/monitor/messages/{message_id}", json=message_update.model_dump(), headers=logged_in_headers
    )
    assert response.status_code == 200, response.text
    updated_message = MessageRead(**response.json())
    assert updated_message.text == "Updated content"


@pytest.mark.api_key_required
async def test_update_message_not_found(client: AsyncClient, logged_in_headers):
    non_existent_id = UUID("00000000-0000-0000-0000-000000000000")
    message_update = MessageUpdate(text="Updated content")
    response = await client.put(
        f"api/v1/monitor/messages/{non_existent_id}", json=message_update.model_dump(), headers=logged_in_headers
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Message not found"


@pytest.mark.api_key_required
async def test_delete_messages_session(client: AsyncClient, created_messages, logged_in_headers):
    session_id = "session_id2"
    response = await client.delete(f"api/v1/monitor/messages/session/{session_id}", headers=logged_in_headers)
    assert response.status_code == 204
    assert response.reason_phrase == "No Content"

    assert len(created_messages) == 3
    response = await client.get("api/v1/monitor/messages", headers=logged_in_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


# Successfully update session ID for all messages with the old session ID
@pytest.mark.usefixtures("session")
async def test_successfully_update_session_id(client, logged_in_headers, created_messages):
    old_session_id = "session_id2"
    new_session_id = "new_session_id"

    response = await client.patch(
        f"api/v1/monitor/messages/session/{old_session_id}",
        params={"new_session_id": new_session_id},
        headers=logged_in_headers,
    )

    assert response.status_code == 200, response.text
    updated_messages = response.json()
    assert len(updated_messages) == len(created_messages)
    for message in updated_messages:
        assert message["session_id"] == new_session_id

    response = await client.get(
        "api/v1/monitor/messages", headers=logged_in_headers, params={"session_id": new_session_id}
    )
    assert response.status_code == 200
    assert len(response.json()) == len(created_messages)
    messages = response.json()
    for message in messages:
        assert message["session_id"] == new_session_id
        response_timestamp = message["timestamp"]
        timestamp = datetime.strptime(response_timestamp, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
        assert timestamp_str == response_timestamp

    # Check if the messages ordered by timestamp are in the correct order
    # User, User, AI
    assert messages[0]["sender"] == "User"
    assert messages[1]["sender"] == "User"
    assert messages[2]["sender"] == "AI"


# No messages found with the given session ID
@pytest.mark.usefixtures("session")
async def test_no_messages_found_with_given_session_id(client, logged_in_headers):
    old_session_id = "non_existent_session_id"
    new_session_id = "new_session_id"

    response = await client.patch(
        f"/messages/session/{old_session_id}", params={"new_session_id": new_session_id}, headers=logged_in_headers
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Not Found"


# Test for URL-encoded datetime session ID
@pytest.mark.api_key_required
async def test_get_messages_with_url_encoded_datetime_session_id(
    client: AsyncClient, messages_with_datetime_session_id, logged_in_headers
):
    """Test that URL-encoded datetime session IDs are properly decoded and matched."""
    _created_messages, datetime_session_id = messages_with_datetime_session_id

    # URL encode the datetime session ID (spaces become %20, colons become %3A)
    encoded_session_id = quote(datetime_session_id)

    # Test with URL-encoded session ID
    response = await client.get(
        "api/v1/monitor/messages", params={"session_id": encoded_session_id}, headers=logged_in_headers
    )

    assert response.status_code == 200, response.text
    messages = response.json()
    assert len(messages) == 2

    # Verify all messages have the correct (decoded) session ID
    for message in messages:
        assert message["session_id"] == datetime_session_id

    # Verify message content
    assert messages[0]["text"] == "Datetime message 1"
    assert messages[1]["text"] == "Datetime message 2"


@pytest.mark.api_key_required
async def test_get_messages_with_non_encoded_datetime_session_id(
    client: AsyncClient, messages_with_datetime_session_id, logged_in_headers
):
    """Test that non-URL-encoded datetime session IDs also work correctly."""
    _created_messages, datetime_session_id = messages_with_datetime_session_id

    # Test with non-encoded session ID (should still work due to unquote being safe for non-encoded strings)
    response = await client.get(
        "api/v1/monitor/messages", params={"session_id": datetime_session_id}, headers=logged_in_headers
    )

    assert response.status_code == 200, response.text
    messages = response.json()
    assert len(messages) == 2

    # Verify all messages have the correct session ID
    for message in messages:
        assert message["session_id"] == datetime_session_id


@pytest.mark.api_key_required
async def test_get_messages_with_various_encoded_characters(client: AsyncClient, logged_in_headers, active_user):
    """Test various URL-encoded characters in session IDs."""
    # Create a session ID with various special characters
    special_session_id = "test+session:2024@domain.com"

    async with session_scope() as session:
        # Create a flow for the user so messages can be filtered by user
        flow = Flow(name="test_flow_for_special_chars", user_id=active_user.id, data={"nodes": [], "edges": []})
        session.add(flow)
        await session.flush()

        message = MessageCreate(
            text="Special chars message", sender="User", sender_name="User", session_id=special_session_id
        )
        messagetable = MessageTable.model_validate(message, from_attributes=True)
        messagetable.flow_id = flow.id
        await aadd_messagetables([messagetable], session)

    # URL encode the session ID
    encoded_session_id = quote(special_session_id)

    # Test with URL-encoded session ID
    response = await client.get(
        "api/v1/monitor/messages", params={"session_id": encoded_session_id}, headers=logged_in_headers
    )

    assert response.status_code == 200, response.text
    messages = response.json()
    assert len(messages) == 1
    assert messages[0]["session_id"] == special_session_id
    assert messages[0]["text"] == "Special chars message"


@pytest.mark.api_key_required
async def test_get_messages_empty_result_with_encoded_nonexistent_session(client: AsyncClient, logged_in_headers):
    """Test that URL-encoded non-existent session IDs return empty results."""
    nonexistent_session_id = "2024-12-31 23:59:59 UTC"
    encoded_session_id = quote(nonexistent_session_id)

    response = await client.get(
        "api/v1/monitor/messages", params={"session_id": encoded_session_id}, headers=logged_in_headers
    )

    assert response.status_code == 200, response.text
    messages = response.json()
    assert len(messages) == 0


# ---------------------------------------------------------------------------
# Ownership tests for DELETE /monitor/messages and /monitor/messages/session
# ---------------------------------------------------------------------------


@pytest.fixture
async def other_user(client):  # noqa: ARG001
    async with session_scope() as session:
        user = User(
            username="other_owner_user",
            password=get_auth_service().get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False,
        )
        stmt = select(User).where(User.username == user.username)
        if existing := (await session.exec(stmt)).first():
            user = existing
        else:
            session.add(user)
            await session.flush()
            await session.refresh(user)
        user = UserRead.model_validate(user, from_attributes=True)
    yield user
    try:
        async with session_scope() as session:
            db_user = await session.get(User, user.id)
            if db_user:
                await session.delete(db_user)
    except Exception:
        pass


@pytest.fixture
async def other_user_headers(client, other_user):
    login_data = {"username": other_user.username, "password": "testpassword"}
    response = await client.post("api/v1/login", data=login_data)
    assert response.status_code == 200
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def messages_owned_by_other_user(other_user):
    async with session_scope() as session:
        flow = Flow(
            name="other_owner_flow",
            user_id=other_user.id,
            data={"nodes": [], "edges": []},
        )
        session.add(flow)
        await session.flush()

        messages = [
            MessageCreate(text="Other user msg 1", sender="User", sender_name="User", session_id="other_session"),
            MessageCreate(text="Other user msg 2", sender="AI", sender_name="AI", session_id="other_session"),
        ]
        messagetables = [MessageTable.model_validate(m, from_attributes=True) for m in messages]
        for mt in messagetables:
            mt.flow_id = flow.id
        return await aadd_messagetables(messagetables, session)


@pytest.mark.api_key_required
async def test_delete_messages_cannot_delete_other_users_messages(
    client: AsyncClient,
    messages_owned_by_other_user,
    logged_in_headers,
    other_user_headers,
):
    """DELETE /monitor/messages returns 403 when requesting to delete messages not owned by the requester."""
    other_ids = [str(msg.id) for msg in messages_owned_by_other_user]

    # user A tries to delete user B's messages — must return 403
    response = await client.request("DELETE", "api/v1/monitor/messages", json=other_ids, headers=logged_in_headers)
    assert response.status_code == 403

    # user B's messages must still exist
    response = await client.get("api/v1/monitor/messages", headers=other_user_headers)
    assert response.status_code == 200
    remaining_ids = {msg["id"] for msg in response.json()}
    assert all(msg_id in remaining_ids for msg_id in other_ids)


@pytest.mark.api_key_required
async def test_delete_messages_returns_403_for_mixed_ownership(
    client: AsyncClient,
    created_messages,
    messages_owned_by_other_user,
    logged_in_headers,
    other_user_headers,
):
    """DELETE /monitor/messages returns 403 when the request includes IDs not owned by the requester."""
    own_ids = [str(msg.id) for msg in created_messages]
    other_ids = [str(msg.id) for msg in messages_owned_by_other_user]

    # Send a mixed list — own + other user's — must return 403 and delete nothing
    response = await client.request(
        "DELETE", "api/v1/monitor/messages", json=own_ids + other_ids, headers=logged_in_headers
    )
    assert response.status_code == 403

    # Own messages must remain intact
    response = await client.get("api/v1/monitor/messages", headers=logged_in_headers)
    assert response.status_code == 200
    remaining_ids = {msg["id"] for msg in response.json()}
    assert all(msg_id in remaining_ids for msg_id in own_ids)

    # Other user's messages must also remain intact
    response = await client.get("api/v1/monitor/messages", headers=other_user_headers)
    assert response.status_code == 200
    remaining_ids = {msg["id"] for msg in response.json()}
    assert all(msg_id in remaining_ids for msg_id in other_ids)


@pytest.mark.api_key_required
async def test_delete_messages_session_cannot_delete_other_users_session(
    client: AsyncClient,
    messages_owned_by_other_user,
    logged_in_headers,
    other_user_headers,
):
    """DELETE /monitor/messages/session/{id} returns 403 when the session belongs to another user."""
    session_id = "other_session"

    # user A tries to wipe user B's session — must return 403
    response = await client.delete(f"api/v1/monitor/messages/session/{session_id}", headers=logged_in_headers)
    assert response.status_code == 403

    # user B's messages in that session must remain
    response = await client.get(
        "api/v1/monitor/messages", params={"session_id": session_id}, headers=other_user_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == len(messages_owned_by_other_user)
