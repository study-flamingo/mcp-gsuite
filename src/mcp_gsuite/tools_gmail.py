from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    BlobResourceContents,
)
from . import gmail
import json
from .server import mcp
from .auth_utils import require_auth
import base64
from typing import Optional
from pydantic import AnyUrl


def decode_base64_data(file_data):
    standard_base64_data = file_data.replace("-", "+").replace("_", "/")
    missing_padding = len(standard_base64_data) % 4
    if missing_padding:
        standard_base64_data += "=" * (4 - missing_padding)
    return base64.b64decode(standard_base64_data, validate=True)


@mcp.tool(name="query_gmail_emails")
@require_auth
def query_gmail_emails(
    __user_id__: str, query: Optional[str] = None, max_results: int = 100
) -> str:
    """Query Gmail emails based on an optional search query.
    Returns emails in reverse chronological order (newest first).
    Returns metadata such as subject and also a short summary of the content.
    """
    gmail_service = gmail.GmailService(user_id=__user_id__)
    emails = gmail_service.query_emails(query=query, max_results=max_results)
    return json.dumps(emails, indent=2)


@mcp.tool(name="get_gmail_email")
@require_auth
def get_gmail_email(__user_id__: str, email_id: str) -> str:
    """Retrieves a complete Gmail email message by its ID, including the full message body and attachment IDs."""
    gmail_service = gmail.GmailService(user_id=__user_id__)
    email, attachments = gmail_service.get_email_by_id_with_attachments(email_id)

    if email is None:
        return f"Failed to retrieve email with ID: {email_id}"

    email["attachments"] = attachments
    return json.dumps(email, indent=2)


@mcp.tool(name="bulk_get_gmail_emails")
@require_auth
def bulk_get_gmail_emails(__user_id__: str, email_ids: list[str]) -> str:
    """Retrieves multiple Gmail email messages by their IDs in a single request, including the full message bodies and attachment IDs."""
    gmail_service = gmail.GmailService(user_id=__user_id__)

    results = []
    for email_id in email_ids:
        email, attachments = gmail_service.get_email_by_id_with_attachments(email_id)
        if email is not None:
            email["attachments"] = attachments
            results.append(email)

    if not results:
        return "Failed to retrieve any emails from the provided IDs"

    return json.dumps(results, indent=2)


@mcp.tool(name="create_gmail_draft")
@require_auth
def create_gmail_draft(
    __user_id__: str, to: str, subject: str, body: str, cc: Optional[list[str]] = None
) -> str:
    """Creates a draft email message from scratch in Gmail with specified recipient, subject, body, and optional CC recipients.

    Do NOT use this tool when you want to draft or send a REPLY to an existing message. This tool does NOT include any previous message content. Use the reply_gmail_email tool
    with send=False instead."
    """
    gmail_service = gmail.GmailService(user_id=__user_id__)
    draft = gmail_service.create_draft(to=to, subject=subject, body=body, cc=cc)

    if draft is None:
        return "Failed to create draft email"

    return json.dumps(draft, indent=2)


@mcp.tool(name="delete_gmail_draft")
@require_auth
def delete_gmail_draft(__user_id__: str, draft_id: str) -> str:
    """Deletes a Gmail draft message by its ID. This action cannot be undone."""
    gmail_service = gmail.GmailService(user_id=__user_id__)
    success = gmail_service.delete_draft(draft_id)

    return (
        "Successfully deleted draft"
        if success
        else f"Failed to delete draft with ID: {draft_id}"
    )


@mcp.tool(name="reply_gmail_email")
@require_auth
def reply_gmail_email(
    __user_id__: str,
    original_message_id: str,
    reply_body: str,
    send: bool = False,
    cc: Optional[list[str]] = None,
) -> str:
    """Creates a reply to an existing Gmail email message and either sends it or saves as draft.

    Use this tool if you want to draft a reply. Use the 'cc' argument if you want to perform a "reply all".
    """
    gmail_service = gmail.GmailService(user_id=__user_id__)

    # First get the original message to extract necessary information
    original_message, _ = gmail_service.get_email_by_id_with_attachments(
        original_message_id
    )
    if original_message is None:
        return f"Failed to retrieve original message with ID: {original_message_id}"

    # Create and send/draft the reply
    result = gmail_service.create_reply(
        original_message=original_message,
        reply_body=reply_body,
        send=send,
        cc=cc,
    )

    if result is None:
        return f"Failed to {'send' if send else 'draft'} reply email"

    return json.dumps(result, indent=2)


@mcp.tool(name="get_gmail_attachment")
@require_auth
def get_gmail_attachment(
    __user_id__: str,
    message_id: str,
    attachment_id: str,
    mime_type: str,
    filename: str,
    save_to_disk: Optional[str] = None,
) -> str | EmbeddedResource:
    """Retrieves a Gmail attachment by its ID."""
    gmail_service = gmail.GmailService(user_id=__user_id__)
    attachment_data = gmail_service.get_attachment(message_id, attachment_id)

    if attachment_data is None:
        return f"Failed to retrieve attachment with ID: {attachment_id} from message: {message_id}"

    file_data = attachment_data["data"]
    attachment_url = f"attachment://gmail/{message_id}/{attachment_id}/{filename}"
    if save_to_disk:
        decoded_data = decode_base64_data(file_data)
        with open(save_to_disk, "wb") as f:
            f.write(decoded_data)
        return f"Attachment saved to disk: {save_to_disk}"
    return EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            blob=file_data,
            uri=AnyUrl(attachment_url),
            mimeType=mime_type,
        ),
    )


@mcp.tool(name="bulk_save_gmail_attachments")
@require_auth
def bulk_save_gmail_attachments(
    __user_id__: str, attachments: list[dict]
) -> list[TextContent]:
    """Saves multiple Gmail attachments to disk by their message IDs and attachment IDs in a single request."""
    gmail_service = gmail.GmailService(user_id=__user_id__)
    results = []

    for attachment_info in attachments:
        # get attachment data from message_id and part_id
        message, email_attachments = gmail_service.get_email_by_id_with_attachments(
            attachment_info["message_id"]
        )
        if message is None:
            results.append(
                TextContent(
                    type="text",
                    text=f"Failed to retrieve message with ID: {attachment_info['message_id']}",
                )
            )
            continue
        # get attachment_id from part_id
        attachment_id = email_attachments[attachment_info["part_id"]]["attachmentId"]
        attachment_data = gmail_service.get_attachment(
            attachment_info["message_id"], attachment_id
        )
        if attachment_data is None:
            results.append(
                TextContent(
                    type="text",
                    text=f"Failed to retrieve attachment with ID: {attachment_id} from message: {attachment_info['message_id']}",
                )
            )
            continue

        file_data = attachment_data["data"]
        try:
            decoded_data = decode_base64_data(file_data)
            with open(attachment_info["save_path"], "wb") as f:
                f.write(decoded_data)
            results.append(
                TextContent(
                    type="text",
                    text=f"Attachment saved to: {attachment_info['save_path']}",
                )
            )
        except Exception as e:
            results.append(
                TextContent(
                    type="text",
                    text=f"Failed to save attachment to {attachment_info['save_path']}: {str(e)}",
                )
            )
            continue

    return results
