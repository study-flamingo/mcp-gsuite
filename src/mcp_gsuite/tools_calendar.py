from mcp.types import (
    Tool,
    TextContent,
)
from . import calendar
import json
from .auth_utils import require_auth
from .mcp import mcp

@mcp.tool(name="list_calendars")
@require_auth
def list_calendars(__user_id__: str) -> str:
    """Lists all calendars accessible by the user.
    Call it before any other tool whenever the user specifies a particular agenda (Family, Holidays, etc.).
    """
    calendar_service = calendar.CalendarService(user_id=__user_id__)
    calendars = calendar_service.list_calendars()
    return json.dumps(calendars, indent=2)


@mcp.tool(name="get_calendar_events")
@require_auth
def get_calendar_events(
    __user_id__: str,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 250,
    show_deleted: bool = False,
    calendar_id: str = "primary",
) -> str:
    """Retrieves calendar events from the user's Google Calendar within a specified time range."""
    calendar_service = calendar.CalendarService(user_id=__user_id__)
    events = calendar_service.get_events(
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
        show_deleted=show_deleted,
        calendar_id=calendar_id,
    )
    return json.dumps(events, indent=2)


@mcp.tool(name="create_calendar_event")
@require_auth
def create_calendar_event(
    __user_id__: str,
    summary: str,
    start_time: str,
    end_time: str,
    location: str | None = None,
    description: str | None = None,
    attendees: list[str] | None = None,
    send_notifications: bool = True,
    timezone: str | None = None,
    calendar_id: str = "primary",
) -> str:
    """Creates a new event in a specified Google Calendar of the specified user."""
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
        calendar_id=calendar_id,
    )
    return json.dumps(event, indent=2)


@mcp.tool(name="delete_calendar_event")
@require_auth
def delete_calendar_event(
    __user_id__: str,
    event_id: str,
    send_notifications: bool = True,
    calendar_id: str = "primary",
) -> str:
    """Deletes an event from the user's Google Calendar by its event ID."""
    calendar_service = calendar.CalendarService(user_id=__user_id__)
    success = calendar_service.delete_event(
        event_id=event_id,
        send_notifications=send_notifications,
        calendar_id=calendar_id,
    )
    return json.dumps(
        {
            "success": success,
            "message": "Event successfully deleted" if success else "Failed to delete event",
        },
        indent=2,
    )