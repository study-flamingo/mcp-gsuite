from .__main__ import main
from .server import app

if __name__ == "__main__":
    """Alternate entry point for the package."""
    main()

__all__ = [
    "app"
]