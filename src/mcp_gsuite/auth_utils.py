import subprocess
import sys
import threading
from functools import wraps
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

USER_ID_ARG = "__user_id__"
from . import gauth
from .logs import logger


class OauthListener(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/code":
            self.send_response(404)
            self.end_headers()
            return

        query = parse_qs(url.query)
        if "code" not in query:
            self.send_response(400)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write("Auth successful! You can close the tab!".encode("utf-8"))
        self.wfile.flush()

        storage = {}
        creds = gauth.get_credentials(authorization_code=query["code"][0], state=storage)

        t = threading.Thread(target=self.server.shutdown)
        t.daemon = True
        t.start()


def start_auth_flow(user_id: str):
    auth_url = gauth.get_authorization_url(user_id, state={})
    if sys.platform == "darwin" or sys.platform.startswith("linux"):
        subprocess.Popen(["open", auth_url])
    else:
        import webbrowser

        webbrowser.open(auth_url)

    # start server for code callback
    server_address = ("", 4100)
    server = HTTPServer(server_address, OauthListener)
    server.serve_forever()


def setup_oauth2(user_id: str):
    accounts = gauth.get_account_info()
    if len(accounts) == 0:
        raise RuntimeError("No accounts specified in .gauth.json")
    if user_id not in [a.email for a in accounts]:
        raise RuntimeError(f"Account for email: {user_id} not specified in .gauth.json")

    credentials = gauth.get_stored_credentials(user_id=user_id)
    if not credentials:
        start_auth_flow(user_id=user_id)
    else:
        if credentials.access_token_expired:
            logger.error("credentials expired. try refresh")

        # this call refreshes access token
        gauth.get_user_info(credentials=credentials)
        gauth.store_credentials(credentials=credentials, user_id=user_id)


def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = kwargs.get(USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {USER_ID_ARG}")
        setup_oauth2(user_id=user_id)
        return func(*args, **kwargs)

    return wrapper