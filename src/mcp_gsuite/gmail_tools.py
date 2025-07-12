"""MCP Tool definitions for Gmail API."""
from fastmcp.server import FastMCP
from pydantic import Field, AnyUrl
from typing import Annotated
import base64
import json
from mcp.types import (
    TextContent,
    EmbeddedResource,
    BlobResourceContents,
)
from . import gauth
from .api import gmail
from .logs import logger
from .auth_utils import require_auth

# Dynamically load user IDs from accounts.json
try:
    accounts = gauth.get_account_info()
    user_id_examples_formatted = [f"{account.email} ({account.account_type}, {account.extra_info})" for account in accounts]
    user_id_examples = [f"{account.email} ({account.account_type}, {account.extra_info})" for account in accounts]
except Exception as e:
    print(f"Warning: Could not load accounts from .accounts.json: {e}. Using default examples.")
    user_id_examples = ["your.name@example.com"] # Fallback if accounts.json is not found or invalid

def decode_base64_data(file_data):
    standard_base64_data = file_data.replace("-", "+").replace("_", "/")
    missing_padding = len(standard_base64_data) % 4
    if missing_padding:
        standard_base64_data += "=" * (4 - missing_padding)
    return base64.b64decode(standard_base64_data, validate=True)

def register_gmail_tools(mcp: FastMCP):
    @mcp.tool(name="query_gmail_emails")
    def query_gmail_emails(
        __user_id__: Annotated[str, Field(description=f"The email of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        query: Annotated[str | None, Field(description="Gmail search query (optional).", examples=["in:inbox subject:test"])] = None,
        max_results: Annotated[int, Field(description="Maximum number of emails to retrieve (1-500)", examples=[10], ge=1, le=500)] = 10
    ) -> str:
        """Query Gmail emails based on an optional search query.
        Returns emails in reverse chronological order (newest first).
        Returns metadata such as subject and also a short summary of the content.
        """
        require_auth(__user_id__)
        try:
            gmail_service = gmail.GmailService(user_id=__user_id__)
        except Exception as e:
            return f"Error initializing GmailService: {str(e)}"

        try:
            emails = gmail_service.query_emails(query=query, max_results=max_results)
        except Exception as e:
            return f"Error querying emails: {str(e)}"

        try:
            return json.dumps(emails, indent=2)
        except Exception as e:
            return f"Error parsing emails: {str(e)}"


    @mcp.tool(name="get_gmail_email")
    def get_gmail_email(
        __user_id__: Annotated[str, Field(description=f"The EMAIL of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        email_id: Annotated[str, Field(description="The ID of the Gmail message to retrieve")]
    ) -> str:
        """Retrieves a complete Gmail email message by its ID, including the full message body and attachment IDs."""
        require_auth(__user_id__)
        gmail_service = gmail.GmailService(user_id=__user_id__)
        email, attachments = gmail_service.get_email_by_id_with_attachments(email_id)

        if email is None:
            return f"Failed to retrieve email with ID: {email_id}"

        email["attachments"] = attachments
        return json.dumps(email, indent=2)


    @mcp.tool(name="create_gmail_draft")
    def create_gmail_draft(
        __user_id__: Annotated[str, Field(description=f"The EMAIL of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        to: Annotated[str, Field(description="Email address of the recipient")],
        subject: Annotated[str, Field(description="Subject line of the email")],
        body: Annotated[str, Field(description="Body content of the email")],
        cc: Annotated[list[str] | None, Field(description="Optional list of email addresses to CC")] = None
    ) -> str:
        """Creates a draft email message from scratch in Gmail with specified recipient, subject, body, and optional CC recipients.

        Do NOT use this tool when you want to draft or send a REPLY to an existing message. This tool does NOT include any previous message content. Use the reply_gmail_email tool
        with send=False instead."
        """
        require_auth(__user_id__)
        gmail_service = gmail.GmailService(user_id=__user_id__)
        draft = gmail_service.create_draft(to=to, subject=subject, body=body, cc=cc)

        if draft is None:
            return "Failed to create draft email"

        return json.dumps(draft, indent=2)


    @mcp.tool(name="delete_gmail_draft")
    def delete_gmail_draft(
        __user_id__: Annotated[str, Field(description=f"The EMAIL of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        draft_id: Annotated[str, Field(description="The ID of the draft to delete")]
    ) -> str:
        """Deletes a Gmail draft message by its ID. This action cannot be undone."""
        require_auth(__user_id__)
        gmail_service = gmail.GmailService(user_id=__user_id__)
        success = gmail_service.delete_draft(draft_id)

        return (
            "Successfully deleted draft"
            if success
            else f"Failed to delete draft with ID: {draft_id}"
        )


    @mcp.tool(name="reply_gmail_email")
    def reply_gmail_email(
        __user_id__: Annotated[str, Field(description=f"The EMAIL of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        original_message_id: Annotated[str, Field(description="The ID of the Gmail message to reply to")],
        reply_body: Annotated[str, Field(description="The body content of your reply message")],
        send: Annotated[bool, Field(description="If true, sends the reply immediately. If false, saves as draft.", default=False)],
        cc: Annotated[list[str] | None, Field(description="Optional list of email addresses to CC on the reply")] = None,
    ) -> str:
        """Creates a reply to an existing Gmail email message and either sends it or saves as draft.

        Use this tool if you want to draft a reply. Use the 'cc' argument if you want to perform a "reply all".
        """
        require_auth(__user_id__)
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
    def get_gmail_attachment(
        __user_id__: Annotated[str, Field(description=f"The EMAIL of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        message_id: Annotated[str, Field(description="The ID of the Gmail message containing the attachment")],
        attachment_id: Annotated[str, Field(description="The ID of the attachment to retrieve")],
        mime_type: Annotated[str, Field(description="The MIME type of the attachment")],
        filename: Annotated[str, Field(description="The filename of the attachment")],
        save_to_disk: Annotated[str | None, Field(description="The fullpath to save the attachment to disk. If not provided, the attachment is returned as a resource.")] = None,
    ) -> str | EmbeddedResource:
        """Retrieves a Gmail attachment by its ID."""
        require_auth(__user_id__)
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


    @mcp.tool(name="bulk_get_gmail_emails")
    def bulk_get_gmail_emails(
        __user_id__: Annotated[str, Field(description=f"The EMAIL of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        email_ids: Annotated[list[str], Field(description="List of Gmail message IDs to retrieve")]
    ) -> str:
        """Retrieves multiple Gmail email messages by their IDs in a single request, including the full message bodies and attachment IDs."""
        require_auth(__user_id__)
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


    @mcp.tool(name="bulk_save_gmail_attachments")
    def bulk_save_gmail_attachments(
        __user_id__: Annotated[str, Field(description=f"The EMAIL of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        attachments: Annotated[list[dict], Field(description="A list of dictionaries, each containing 'message_id', 'part_id', and 'save_path' for attachments to save.")]
    ) -> list[TextContent]:
        """Saves multiple Gmail attachments to disk by their message IDs and attachment IDs in a single request."""
        require_auth(__user_id__)
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