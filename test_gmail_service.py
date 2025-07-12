import sys
import os
import traceback

# Add the parent directory of mcp_gsuite to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from mcp_gsuite.api import gmail

user_id = "your.name@example.com"

try:
    print(f"Attempting to initialize GmailService for user: {user_id}")
    gmail_service = gmail.GmailService(user_id=user_id)
    print("GmailService initialized successfully.")
except Exception as e:
    print(f"Error initializing GmailService: {str(e)}")
    print(traceback.format_exc())
