from fastmcp import FastMCP
from . import gauth
from .logs import logger
from .auth_utils import require_auth

mcp = FastMCP("mcp-gsuite")

# Import tools to register them with the decorator
from . import tools_gmail
from . import tools_calendar


async def init():
    accounts = gauth.get_account_info()
    for account in accounts:
        creds = gauth.get_stored_credentials(user_id=account.email)
        if creds:
            logger.info(f"Found credentials for: {account.email}")

    await mcp.run_async(transport="stdio")