import os
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

_DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/blogger",
    "https://www.googleapis.com/auth/gmail.send",
]

def creds(scopes=_DEFAULT_SCOPES):
    creds = Credentials(
        None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=scopes,
    )
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds

