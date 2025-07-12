import pytest
import pytest_asyncio
from typing import Any
from fastmcp import FastMCP, Client
from unittest.mock import MagicMock, patch
import json
import os

# Import the tools directly
from mcp_gsuite import tools_gmail
from mcp_gsuite import calendar_tools
from mcp.types import EmbeddedResource, BlobResourceContents, TextContent
from pydantic import AnyUrl

# Import the actual mcp instance
from mcp_gsuite.server import mcp as actual_mcp_server

@pytest_asyncio.fixture
async def mcp_server():
    """FastMCP fixture for testing"""
    yield actual_mcp_server

@pytest_asyncio.fixture
async def mcp_client(mcp_server):
    async with Client(mcp_server) as client:
        yield client

# New fixture for mocking GmailService
@pytest.fixture
def mock_gmail_service():
    with patch('mcp_gsuite.gmail.GmailService') as mock_service_class:
        mock_instance = MagicMock()
        mock_service_class.return_value = mock_instance
        yield mock_instance

# New fixture for mocking CalendarService
@pytest.fixture
def mock_calendar_service():
    with patch('mcp_gsuite.calendar.CalendarService') as mock_service_class:
        mock_instance = MagicMock()
        mock_service_class.return_value = mock_instance
        yield mock_instance

# Mock setup_oauth2 to prevent FileNotFoundError during tests
@pytest.fixture(autouse=True)
def mock_setup_oauth2():
    with patch('mcp_gsuite.auth_utils.setup_oauth2') as mock_setup:
        mock_setup.return_value = None # Or a dummy value if needed
        yield mock_setup

# Test for decode_base64_data
def test_decode_base64_data():
    # Standard base64
    encoded_data = "SGVsbG8gV29ybGQh" # "Hello World!"
    decoded = tools_gmail.decode_base64_data(encoded_data)
    assert decoded == b"Hello World!"

    # URL-safe base64
    encoded_data_url_safe = "SGVsbG8gV29ybGQh-_==" # "Hello World!" with some url safe chars
    decoded_url_safe = tools_gmail.decode_base64_data(encoded_data_url_safe)
    assert decoded_url_safe == b"Hello World!\xfb" # Corrected assertion based on actual decoding

    # With padding
    encoded_data_padding = "Zm9vYmFy" # "foobar"
    decoded_padding = tools_gmail.decode_base64_data(encoded_data_padding)
    assert decoded_padding == b"foobar"

    # No padding
    encoded_data_no_padding = "Zm9vYmFyMg" # "foobar2"
    decoded_no_padding = tools_gmail.decode_base64_data(encoded_data_no_padding)
    assert decoded_no_padding == b"foobar2"

    # Invalid base64
    with pytest.raises(Exception):
        tools_gmail.decode_base64_data("invalid-base64!")

# Tests for Gmail Tools
@pytest.mark.asyncio
async def test_query_gmail_emails(mock_gmail_service, mcp_client):
    user_id = "test_user"
    mock_gmail_service.query_emails.return_value = [{"id": "1", "snippet": "Test email"}]
    result_obj = await mcp_client.call_tool("query_gmail_emails", {"__user_id__": user_id, "query": "test", "max_results": 10})
    mock_gmail_service.query_emails.assert_called_once_with(query="test", max_results=10)
    assert json.loads(result_obj[0].text) == [{"id": "1", "snippet": "Test email"}]

@pytest.mark.asyncio
async def test_get_gmail_email(mock_gmail_service, mcp_client):
    user_id = "test_user"
    email_id = "email_123"
    mock_email_data = {"id": email_id, "subject": "Test Subject", "attachments": []}
    mock_attachments = [{"attachmentId": "att1", "filename": "file.txt"}]
    mock_gmail_service.get_email_by_id_with_attachments.return_value = (mock_email_data, mock_attachments)

    result_obj = await mcp_client.call_tool("get_gmail_email", {"__user_id__": user_id, "email_id": email_id})
    mock_gmail_service.get_email_by_id_with_attachments.assert_called_once_with(email_id)
    expected_email = mock_email_data.copy()
    expected_email["attachments"] = mock_attachments
    assert json.loads(result_obj[0].text) == expected_email

    # Test email not found
    mock_gmail_service.get_email_by_id_with_attachments.return_value = (None, [])
    result_obj_not_found = await mcp_client.call_tool("get_gmail_email", {"__user_id__": user_id, "email_id": "non_existent"})
    assert result_obj_not_found[0].text == "Failed to retrieve email with ID: non_existent"

@pytest.mark.asyncio
async def test_bulk_get_gmail_emails(mock_gmail_service, mcp_client):
    user_id = "test_user"
    email_ids = ["email_1", "email_2", "email_3"]
    mock_email_data_1 = {"id": "email_1", "subject": "Sub 1"}
    mock_email_data_2 = {"id": "email_2", "subject": "Sub 2"}
    mock_attachments_1 = [{"attachmentId": "att_a"}]
    mock_attachments_2 = [{"attachmentId": "att_b"}]

    # Simulate one email found, one not found, one found
    mock_gmail_service.get_email_by_id_with_attachments.side_effect = [
        (mock_email_data_1, mock_attachments_1),
        (None, []),
        (mock_email_data_2, mock_attachments_2),
    ]

    results_obj = await mcp_client.call_tool("bulk_get_gmail_emails", {"__user_id__": user_id, "email_ids": email_ids})

    assert mock_gmail_service.get_email_by_id_with_attachments.call_count == 3
    loaded_results = json.loads(results_obj[0].text)
    assert len(loaded_results) == 2
    assert loaded_results[0]["id"] == "email_1"
    assert loaded_results[1]["id"] == "email_2"
    assert loaded_results[0]["attachments"] == mock_attachments_1
    assert loaded_results[1]["attachments"] == mock_attachments_2

    # Test no emails found
    mock_gmail_service.get_email_by_id_with_attachments.side_effect = [(None, []), (None, [])]
    result_obj_none_found = await mcp_client.call_tool("bulk_get_gmail_emails", {"__user_id__": user_id, "email_ids": ["e1", "e2"]})
    assert result_obj_none_found[0].text == "Failed to retrieve any emails from the provided IDs"

@pytest.mark.asyncio
async def test_create_gmail_draft(mock_gmail_service, mcp_client):
    user_id = "test_user"
    to = "recipient@example.com"
    subject = "Test Draft"
    body = "This is a test draft."
    mock_draft = {"id": "draft_123", "subject": subject}
    mock_gmail_service.create_draft.return_value = mock_draft

    result_obj = await mcp_client.call_tool("create_gmail_draft", {"__user_id__": user_id, "to": to, "subject": subject, "body": body})
    mock_gmail_service.create_draft.assert_called_once_with(to=to, subject=subject, body=body, cc=None)
    assert json.loads(result_obj[0].text) == mock_draft

    # Test with CC
    cc = ["cc1@example.com", "cc2@example.com"]
    mock_gmail_service.create_draft.reset_mock()
    mock_gmail_service.create_draft.return_value = {"id": "draft_456", "subject": subject}
    result_obj_cc = await mcp_client.call_tool("create_gmail_draft", {"__user_id__": user_id, "to": to, "subject": subject, "body": body, "cc": cc})
    mock_gmail_service.create_draft.assert_called_once_with(to=to, subject=subject, body=body, cc=cc)
    assert json.loads(result_obj_cc[0].text)["id"] == "draft_456"

    # Test failure
    mock_gmail_service.create_draft.return_value = None
    result_obj_fail = await mcp_client.call_tool("create_gmail_draft", {"__user_id__": user_id, "to": to, "subject": subject, "body": body})
    assert result_obj_fail[0].text == "Failed to create draft email"

@pytest.mark.asyncio
async def test_delete_gmail_draft(mock_gmail_service, mcp_client):
    user_id = "test_user"
    draft_id = "draft_to_delete"

    mock_gmail_service.delete_draft.return_value = True
    result_obj_success = await mcp_client.call_tool("delete_gmail_draft", {"__user_id__": user_id, "draft_id": draft_id})
    mock_gmail_service.delete_draft.assert_called_once_with(draft_id)
    assert result_obj_success[0].text == "Successfully deleted draft"

    mock_gmail_service.delete_draft.return_value = False
    result_obj_fail = await mcp_client.call_tool("delete_gmail_draft", {"__user_id__": user_id, "draft_id": draft_id})
    assert result_obj_fail[0].text == f"Failed to delete draft with ID: {draft_id}"

@pytest.mark.asyncio
async def test_reply_gmail_email(mock_gmail_service, mcp_client):
    user_id = "test_user"
    original_message_id = "original_123"
    reply_body = "This is a reply."
    mock_original_message = {"id": original_message_id, "subject": "Original Subject", "payload": {"headers": [{"name": "From", "value": "sender@example.com"}]}}
    mock_gmail_service.get_email_by_id_with_attachments.return_value = (mock_original_message, [])

    # Test drafting a reply
    mock_gmail_service.create_reply.return_value = {"id": "reply_draft_1", "status": "draft"}
    result_obj_draft = await mcp_client.call_tool("reply_gmail_email", {"__user_id__": user_id, "original_message_id": original_message_id, "reply_body": reply_body, "send": False})
    mock_gmail_service.get_email_by_id_with_attachments.assert_called_once_with(original_message_id)
    mock_gmail_service.create_reply.assert_called_once_with(original_message=mock_original_message, reply_body=reply_body, send=False, cc=None)
    assert json.loads(result_obj_draft[0].text)["id"] == "reply_draft_1"

    # Test sending a reply with CC
    mock_gmail_service.get_email_by_id_with_attachments.reset_mock()
    mock_gmail_service.create_reply.reset_mock()
    mock_gmail_service.get_email_by_id_with_attachments.return_value = (mock_original_message, [])
    mock_gmail_service.create_reply.return_value = {"id": "reply_sent_1", "status": "sent"}
    cc_recipients = ["cc_reply@example.com"]
    result_obj_send_cc = await mcp_client.call_tool("reply_gmail_email", {"__user_id__": user_id, "original_message_id": original_message_id, "reply_body": reply_body, "send": True, "cc": cc_recipients})
    mock_gmail_service.create_reply.assert_called_once_with(original_message=mock_original_message, reply_body=reply_body, send=True, cc=cc_recipients)
    assert json.loads(result_obj_send_cc[0].text)["id"] == "reply_sent_1"

    # Test original message not found
    mock_gmail_service.get_email_by_id_with_attachments.reset_mock()
    mock_gmail_service.get_email_by_id_with_attachments.return_value = (None, [])
    result_obj_original_not_found = await mcp_client.call_tool("reply_gmail_email", {"__user_id__": user_id, "original_message_id": "non_existent", "reply_body": reply_body})
    assert result_obj_original_not_found[0].text == "Failed to retrieve original message with ID: non_existent"

    # Test create_reply failure
    mock_gmail_service.get_email_by_id_with_attachments.reset_mock()
    mock_gmail_service.create_reply.reset_mock()
    mock_gmail_service.get_email_by_id_with_attachments.return_value = (mock_original_message, [])
    mock_gmail_service.create_reply.return_value = None
    result_obj_create_reply_fail = await mcp_client.call_tool("reply_gmail_email", {"__user_id__": user_id, "original_message_id": original_message_id, "reply_body": reply_body, "send": True})
    assert result_obj_create_reply_fail[0].text == "Failed to send reply email"

@pytest.mark.asyncio
async def test_get_gmail_attachment(mock_gmail_service, tmp_path, mcp_client):
    user_id = "test_user"
    message_id = "msg_123"
    attachment_id = "att_456"
    mime_type = "text/plain"
    filename = "test.txt"
    file_content_base64 = "SGVsbG8gV29ybGQh" # "Hello World!"
    mock_gmail_service.get_attachment.return_value = {"data": file_content_base64}

    # Test returning EmbeddedResource
    result_obj_resource = await mcp_client.call_tool("get_gmail_attachment", {
        "__user_id__": user_id,
        "message_id": message_id,
        "attachment_id": attachment_id,
        "mime_type": mime_type,
        "filename": filename
    })
    mock_gmail_service.get_attachment.assert_called_once_with(message_id, attachment_id)
    assert isinstance(result_obj_resource[0], EmbeddedResource)
    assert result_obj_resource[0].type == "resource"
    assert isinstance(result_obj_resource[0].resource, BlobResourceContents)
    assert result_obj_resource[0].resource.blob == file_content_base64
    assert result_obj_resource[0].resource.mimeType == mime_type
    assert str(result_obj_resource[0].resource.uri) == f"attachment://gmail/{message_id}/{attachment_id}/{filename}"

    # Test saving to disk
    mock_gmail_service.get_attachment.reset_mock()
    save_path = tmp_path / "saved_file.txt"
    result_obj_save = await mcp_client.call_tool("get_gmail_attachment", {
        "__user_id__": user_id,
        "message_id": message_id,
        "attachment_id": attachment_id,
        "mime_type": mime_type,
        "filename": filename,
        "save_to_disk": str(save_path)
    })
    assert result_obj_save[0].text == f"Attachment saved to disk: {save_path}"
    assert save_path.read_bytes() == b"Hello World!"

    # Test attachment not found
    mock_gmail_service.get_attachment.reset_mock()
    mock_gmail_service.get_attachment.return_value = None
    result_obj_not_found = await mcp_client.call_tool("get_gmail_attachment", {
        "__user_id__": user_id,
        "message_id": message_id,
        "attachment_id": "non_existent_att",
        "mime_type": mime_type,
        "filename": filename
    })
    assert result_obj_not_found[0].text == f"Failed to retrieve attachment with ID: non_existent_att from message: {message_id}"

@pytest.mark.asyncio
async def test_bulk_save_gmail_attachments(mock_gmail_service, tmp_path, mcp_client):
    user_id = "test_user"
    attachments_info = [
        {"message_id": "msg_1", "part_id": "part_a", "save_path": str(tmp_path / "file1.txt")},
        {"message_id": "msg_2", "part_id": "part_b", "save_path": str(tmp_path / "file2.txt")},
        {"message_id": "msg_3", "part_id": "part_c", "save_path": str(tmp_path / "file3.txt")},
    ]

    # Mock return values for get_email_by_id_with_attachments and get_attachment
    mock_gmail_service.get_email_by_id_with_attachments.side_effect = [
        ({"id": "msg_1"}, {"part_a": {"attachmentId": "att_1"}}), # msg_1 found
        ({"id": "msg_2"}, {"part_b": {"attachmentId": "att_2"}}), # msg_2 found
        (None, {}), # msg_3 not found
    ]
    mock_gmail_service.get_attachment.side_effect = [
        {"data": "SGVsbG8gMQ=="}, # "Hello 1" for att_1
        {"data": "SGVsbG8gMg=="}, # "Hello 2" for att_2
    ]

    results_obj = await mcp_client.call_tool("bulk_save_gmail_attachments", {"__user_id__": user_id, "attachments": attachments_info})

    assert mock_gmail_service.get_email_by_id_with_attachments.call_count == 3
    assert len(results_obj) == 3
    assert results_obj[0].text == f"Attachment saved to: {tmp_path / 'file1.txt'}"
    assert results_obj[1].text == f"Attachment saved to: {tmp_path / 'file2.txt'}"
    assert results_obj[2].text == "Failed to retrieve message with ID: msg_3"

    assert (tmp_path / "file1.txt").read_bytes() == b"Hello 1"
    assert (tmp_path / "file2.txt").read_bytes() == b"Hello 2"
    assert not (tmp_path / "file3.txt").exists()

    # Test attachment not found for a message that was found
    mock_gmail_service.get_email_by_id_with_attachments.side_effect = [
        ({"id": "msg_4"}, {"part_d": {"attachmentId": "att_4"}}),
    ]
    mock_gmail_service.get_attachment.side_effect = [None]
    results_obj_att_not_found = await mcp_client.call_tool("bulk_save_gmail_attachments", {"__user_id__": user_id, "attachments": [{"message_id": "msg_4", "part_id": "part_d", "save_path": str(tmp_path / "file4.txt")}]})
    assert results_obj_att_not_found[0].text == "Failed to retrieve attachment with ID: att_4 from message: msg_4"

# Tests for Calendar Tools
@pytest.mark.asyncio
async def test_list_calendars(mock_calendar_service, mcp_client):
    user_id = "test_user"
    mock_calendars = [{"id": "primary", "summary": "Primary Calendar"}, {"id": "holiday", "summary": "Holidays"}]
    mock_calendar_service.list_calendars.return_value = mock_calendars

    result_obj = await mcp_client.call_tool("list_calendars", {"__user_id__": user_id})
    mock_calendar_service.list_calendars.assert_called_once()
    assert json.loads(result_obj[0].text) == mock_calendars

@pytest.mark.asyncio
async def test_get_calendar_events(mock_calendar_service, mcp_client):
    user_id = "test_user"
    mock_events = [{"id": "event_1", "summary": "Meeting"}]
    mock_calendar_service.get_events.return_value = mock_events

    result_obj = await mcp_client.call_tool("get_calendar_events", {"__user_id__": user_id, "time_min": "2023-01-01T00:00:00Z", "calendar_id": "primary"})
    mock_calendar_service.get_events.assert_called_once_with(
        time_min="2023-01-01T00:00:00Z",
        time_max=None,
        max_results=250,
        show_deleted=False,
        calendar_id="primary"
    )
    assert json.loads(result_obj[0].text) == mock_events

@pytest.mark.asyncio
async def test_create_calendar_event(mock_calendar_service, mcp_client):
    user_id = "test_user"
    summary = "Test Event"
    start_time = "2023-01-01T10:00:00Z"
    end_time = "2023-01-01T11:00:00Z"
    mock_event = {"id": "new_event_1", "summary": summary}
    mock_calendar_service.create_event.return_value = mock_event

    result_obj = await mcp_client.call_tool("create_calendar_event", {
        "__user_id__": user_id,
        "summary": summary,
        "start_time": start_time,
        "end_time": end_time,
        "location": "Test Location",
        "attendees": ["attendee@example.com"]
    })
    mock_calendar_service.create_event.assert_called_once_with(
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        location="Test Location",
        description=None,
        attendees=["attendee@example.com"],
        send_notifications=True,
        timezone=None,
        calendar_id="primary"
    )
    assert json.loads(result_obj[0].text) == mock_event

@pytest.mark.asyncio
async def test_delete_calendar_event(mock_calendar_service, mcp_client):
    user_id = "test_user"
    event_id = "event_to_delete"

    mock_calendar_service.delete_event.return_value = True
    result_obj_success = await mcp_client.call_tool("delete_calendar_event", {"__user_id__": user_id, "event_id": event_id})
    mock_calendar_service.delete_event.assert_called_once_with(
        event_id=event_id,
        send_notifications=True,
        calendar_id="primary"
    )
    assert json.loads(result_obj_success[0].text) == {"success": True, "message": "Event successfully deleted"}

    mock_calendar_service.delete_event.return_value = False
    result_obj_fail = await mcp_client.call_tool("delete_calendar_event", {"__user_id__": user_id, "event_id": event_id})
    assert json.loads(result_obj_fail[0].text) == {"success": False, "message": "Failed to delete event"}