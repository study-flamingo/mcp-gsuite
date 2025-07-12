"""MCP Tool definitions for Google Calendar API."""
from fastmcp.server import FastMCP
from pydantic import Field
from typing import Annotated
import json
from . import gauth
from .api import calendar
from .auth_utils import require_auth

# Dynamically load user IDs from accounts.json
try:
    accounts = gauth.get_account_info()
    user_id_examples_formatted = [f"{account.email} of type: {account.account_type}. Extra info for: {account.extra_info}" for account in accounts]
    user_id_examples = [f"{account.email}" for account in accounts]
except Exception as e:
    print(f"Warning: Could not load accounts from .accounts.json: {e}. Using default examples.")
    user_id_examples = ["your.name@example.com"] # Fallback if accounts.json is not found or invalid

def register_calendar_tools(mcp: FastMCP):
    @mcp.tool(name="list_calendars")
    def list_calendars(
        __user_id__: Annotated[str, Field(description=f"The email of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
    ) -> str:
        """Lists all calendars accessible by the user.
        Call it before any other tool whenever the user specifies a particular agenda (Family, Holidays, etc.).
        """
        require_auth(__user_id__)
        calendar_service = calendar.CalendarService(user_id=__user_id__)
        calendars = calendar_service.list_calendars()
        return json.dumps(calendars, indent=2)


    @mcp.tool(name="get_calendar_events")
    def get_calendar_events(
        __user_id__: Annotated[str, Field(description=f"The email of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        __calendar_id__: Annotated[str, Field(description="Optional ID of the specific agenda for which you are executing this action.\n                          If not provided, the default calendar is being used. \n                          If not known, the specific calendar id can be retrieved with the list_calendars tool", examples=["primary"])] = "primary",
        time_min: Annotated[str | None, Field(description="Start time in RFC3339 format (e.g. 2024-12-01T00:00:00Z). Defaults to current time if not specified.")] = None,
        time_max: Annotated[str | None, Field(description="End time in RFC3339 format (e.g. 2024-12-31T23:59:59Z). Optional.")] = None,
        max_results: Annotated[int, Field(description="Maximum number of events to return (1-2500)", ge=1, le=2500)] = 25,
        show_deleted: Annotated[bool, Field(description="Whether to include deleted events")] = False,
    ) -> str:
        """Retrieves calendar events from the user's Google Calendar within a specified time range."""
        require_auth(__user_id__)
        calendar_service = calendar.CalendarService(user_id=__user_id__)
        events = calendar_service.get_events(
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            show_deleted=show_deleted,
            calendar_id=__calendar_id__,
        )
        return json.dumps(events, indent=2)


    @mcp.tool(name="create_calendar_event")
    def create_calendar_event(
        __user_id__: Annotated[str, Field(description=f"The email of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        summary: Annotated[str, Field(description="Title of the event")],
        start_time: Annotated[str, Field(description="Start time in RFC3339 format (e.g. 2024-12-01T10:00:00Z)")],
        end_time: Annotated[str, Field(description="End time in RFC3339 format (e.g. 2024-12-01T11:00:00Z)")],
        __calendar_id__: Annotated[str, Field(description="Optional ID of the specific agenda for which you are executing this action.\n                          If not provided, the default calendar is being used. \n                          If not known, the specific calendar id can be retrieved with the list_calendars tool", examples=["primary"])] = "primary",
        location: Annotated[str | None, Field(description="Location of the event (optional)")] = None,
        description: Annotated[str | None, Field(description="Description or notes for the event (optional)")] = None,
        attendees: Annotated[list[str] | None, Field(description="List of attendee email addresses (optional)")] = None,
        send_notifications: Annotated[bool, Field(description="Whether to send notifications to attendees")] = True,
        timezone: Annotated[str | None, Field(description="Timezone for the event (e.g. 'America/New_York'). Defaults to UTC if not specified.")] = None,
    ) -> str:
        """Creates a new event in a specified Google Calendar of the specified user."""
        require_auth(__user_id__)
        calendar_service = calendar.CalendarService(user_id=__user_id__)
        event = calendar_service.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            attendees=attendees or [],
            send_notifications=send_notifications,
            timezone=timezone,
            calendar_id=__calendar_id__,
        )
        return json.dumps(event, indent=2)


    @mcp.tool(name="delete_calendar_event")
    def delete_calendar_event(
        __user_id__: Annotated[str, Field(description=f"The email of the Google account for which you are executing this action. Must be one of: {', '.join(user_id_examples_formatted)}", examples=user_id_examples)],
        event_id: Annotated[str, Field(description="The ID of the calendar event to delete")],
        send_notifications: Annotated[bool, Field(description="Whether to send cancellation notifications to attendees")] = True,
        __calendar_id__: Annotated[str, Field(description="Optional ID of the specific agenda for which you are executing this action.\n                          If not provided, the default calendar is being used. \n                          If not known, the specific calendar id can be retrieved with the list_calendars tool", examples=["primary"])] = "primary",
    ) -> str:
        """Deletes an event from the user's Google Calendar by its event ID."""
        require_auth(__user_id__)
        calendar_service = calendar.CalendarService(user_id=__user_id__)
        success = calendar_service.delete_event(
            event_id=event_id,
            send_notifications=send_notifications,
            calendar_id=__calendar_id__,
        )
        return json.dumps(
            {
                "success": success,
                "message": "Event successfully deleted" if success else "Failed to delete event",
            },
            indent=2,
        )