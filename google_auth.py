import os
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

_DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/blogger",
    "https://www.googleapis.com/auth/gmail.send",
]

def creds(scopes=_DEFAULT_SCOPES):
    # This is your existing function to create service account creds if used elsewhere
    key = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "service_account.json")
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    return ServiceAccountCredentials.from_service_account_file(key, scopes=scopes)

def get_auth_header():
    # Use OAuth2 credentials with refresh token
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=_DEFAULT_SCOPES,
    )

    # Refresh the token
    request = google.auth.transport.requests.Request()
    creds.refresh(request)

    # Return Authorization header for API calls
    return {"Authorization": f"Bearer {creds.token}"}
