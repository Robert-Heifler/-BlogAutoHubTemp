import base64, google_auth
from email.mime.text import MIMEText
from googleapiclient.discovery import build

def svc():
    return build(
        "gmail", "v1",
        credentials=google_auth.creds(["https://www.googleapis.com/auth/gmail.send"]),
        cache_discovery=False
    )

def send_html(to_addr: str, subject: str, html: str):
    msg = MIMEText(html, "html")
    msg["to"], msg["subject"] = to_addr, subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc().users().messages().send(userId="me", body={"raw": raw}).execute()
