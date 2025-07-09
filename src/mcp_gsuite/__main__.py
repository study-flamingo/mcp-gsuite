"""Main entry point for the package."""

from .server import init
from .logs import logger
import asyncio

def main():
    """Main entry point for the package."""
    try:
        asyncio.run(init())
    except RuntimeError as e:
        logger.critical(str(e))

if __name__ == "__main__":
    main()
