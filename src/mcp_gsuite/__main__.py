"""Main entry point for the package."""

from .server import init
from .logs import logger
import asyncio

def main():
    """Main entry point for the package."""
    try:
        asyncio.run(init())
    except Exception as e:
        logger.critical(str(e.with_traceback))

if __name__ == "__main__":
    main()
