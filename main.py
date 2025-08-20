import os
import sys
import logging
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from youtube_transcript_api import YouTubeTranscriptApi

# ----------------- Logging Setup -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ----------------- Immediate Environment Check -----------------
REQUIRED_ENV_VARS = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
    "BLOGGER_ID",
    "OPENROUTER_API_KEY",
    "CLAUDE_API_KEY",
    "YOUTUBE_API_KEY",
    "NICHE_DEFAULT",
    "MIN_BLOG_LENGTH"
]

logging.info("Checking which required environment variables are visible at runtime...")
for var in REQUIRED_ENV_VARS:
    if var in os.environ:
        logging.info(f"{var} is visible ✅")
    else:
        logging.warning(f"{var} is MISSING ❌")

# ----------------- Environment Validation -----------------
def validate_env():
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        logging.error(f"Missing required environment variables: {missing}")
        sys.exit(1)
    logging.info("All required environment variables are present.")

# ----------------- Credential Verification -----------------
def verify_blogger_credentials():
    try:
        creds = Credentials(
            token=None,
            refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
            client_id=os.environ["GOOGLE_CLIENT_ID"],
            client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
            token_uri="https://oauth2.googleapis.com/token"
        )
        service = build("blogger", "v3", credentials=creds)
        service.blogs().get(blogId=os.environ["BLOGGER_ID"]).execute()
        logging.info("Google Blogger credentials verified successfully.")
    except Exception as e:
        logging.error(f"Blogger verification failed: {e}")
        sys.exit(1)

def verify_youtube_api():
    test_url = f"https://www.googleapis.com/youtube/v3/channels?part=id&id=UC_x5XG1OV2P6uZZ5FSM9Ttw&key={os.environ['YOUTUBE_API_KEY']}"
    try:
        resp = requests.get(test_url)
        if resp.status_code != 200:
            raise Exception(f"Status code {resp.status_code}")
        logging.info("YouTube API key verified successfully.")
    except Exception as e:
        logging.error(f"YouTube API verification failed: {e}")
        sys.exit(1)

def verify_openrouter_key():
    test_url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    try:
        resp = requests.get(test_url, headers=headers, timeout=10)
        resp.raise_for_status()
        logging.info("OpenRouter API key verified successfully.")
    except Exception as e:
        logging.error(f"OpenRouter API verification failed: {e}")
        sys.exit(1)

# ----------------- Main Execution -----------------
def main():
    logging.info("Starting Worker service...")

    # 1. Validate environment variables
    validate_env()

    # 2. Verify all API credentials
    verify_blogger_credentials()
    verify_youtube_api()
    verify_openrouter_key()

    logging.info("All pre-flight checks passed. Proceeding to main workflow...")

    # ----------------- Main Workflow Placeholder -----------------
    # Place your YouTube transcript retrieval, AI content spin,
    # soft CTA insertion, scheduling logic, etc. here

    logging.info("Worker main workflow completed successfully.")

if __name__ == "__main__":
    main()


