import google_auth
from googleapiclient.discovery import build

def svc():
    return build(
        "blogger", "v3",
        credentials=google_auth.creds(["https://www.googleapis.com/auth/blogger"]),
        cache_discovery=False
    )
