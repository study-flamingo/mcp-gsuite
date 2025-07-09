from .server import init
import asyncio

def main():
    """Main entry point for the package."""
    asyncio.run(init())

if __name__ == "__main__":
    main()
