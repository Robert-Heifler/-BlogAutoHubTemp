import google_auth
from googleapiclient.discovery import build

def svc():
    return build(
        "youtube", "v3",
        credentials=google_auth.creds(["https://www.googleapis.com/auth/youtube.readonly"]),
        cache_discovery=False
    )
