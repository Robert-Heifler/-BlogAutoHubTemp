import os
from google.oauth2.service_account import Credentials

_DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/blogger",
    "https://www.googleapis.com/auth/gmail.send",
]

def creds(scopes=_DEFAULT_SCOPES):
    key = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "service_account.json")
    return Credentials.from_service_account_file(key, scopes=scopes)
