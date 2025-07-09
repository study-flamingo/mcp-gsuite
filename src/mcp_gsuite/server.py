from . import gauth
from .logs import logger

from .mcp import mcp
# Import tools after mcp definition to register them with the decorator
from . import tools_gmail
from . import tools_calendar

async def init():
    accounts = gauth.get_account_info()
    for account in accounts:
        creds = gauth.get_stored_credentials(user_id=account.email)
        if creds:
            logger.info(f"Found credentials for: {account.email}")

    await mcp.run_async(transport="stdio")