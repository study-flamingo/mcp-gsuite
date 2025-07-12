"""Instantiates the MCP server and registers all tools."""
from fastmcp.server import FastMCP
from .logs import logger
from . import gauth
from .gmail_tools import register_gmail_tools
from .calendar_tools import register_calendar_tools

accounts = gauth.get_account_info()
for account in accounts:
    creds = gauth.get_stored_credentials(user_id=account.email)
    if creds:
        logger.info(f"🗝️  Found credentials for: {account.email}")

mcp = FastMCP("gsuite-mcp")
register_gmail_tools(mcp)
register_calendar_tools(mcp)

# TODO: Implement drive access
# from .tools_drive import register_drive_tools
# register_drive_tools(mcp)

async def init():
    await mcp.run_async(transport="stdio")