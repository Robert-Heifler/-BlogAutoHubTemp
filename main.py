import os
import sys
import logging
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from langdetect import detect
import schedule
import time
from flask import Flask

# ------------------- Logging Setup -------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ------------------- Required Environment Variables -------------------
REQUIRED_ENV = {
    "GOOGLE_CLIENT_ID": str,
    "GOOGLE_CLIENT_SECRET": str,
    "GOOGLE_REFRESH_TOKEN": str,
    "BLOGGER_ID": str,
    "OPENROUTER_API_KEY": str,
    "CLAUDE_API_KEY": str,
    "YOUTUBE_API_KEY": str,
    "NICHE_DEFAULT": str,
    "MIN_BLOG_LENGTH": int
}

missing_vars = []
env_values = {}

for var, var_type in REQUIRED_ENV.items():
    value = os.getenv(var)
    if value is None:
        missing_vars.append(var)
    else:
        try:
            env_values[var] = var_type(value)
        except ValueError:
            missing_vars.append(f"{var} (wrong type)")

if missing_vars:
    logging.error(f"Missing or invalid environment variables: {missing_vars}")
    raise EnvironmentError("Please set all required environment variables correctly before starting.")

# ------------------- API Verification -------------------

def verify_google_credentials():
    try:
        creds = Credentials(
            token=None,
            refresh_token=env_values["GOOGLE_REFRESH_TOKEN"],
            client_id=env_values["GOOGLE_CLIENT_ID"],
            client_secret=env_values["GOOGLE_CLIENT_SECRET"],
            token_uri="https://oauth2.googleapis.com/token"
        )
        service = build('blogger', 'v3', credentials=creds)
        _ = service.blogs().get(blogId=env_values["BLOGGER_ID"]).execute()
        logging.info("Google Blogger credentials verified successfully.")
    except Exception as e:
        logging.error(f"Google Blogger API verification failed: {e}")
        raise

def verify_youtube_key():
    test_url = f"https://www.googleapis.com/youtube/v3/videos?part=id&id=dQw4w9WgXcQ&key={env_values['YOUTUBE_API_KEY']}"
    resp = requests.get(test_url)
    if resp.status_code != 200:
        logging.error(f"YouTube API key verification failed: {resp.text}")
        raise EnvironmentError("Invalid YouTube API key")
    logging.info("YouTube API key verified successfully.")

def verify_openrouter_key():
    test_url = "https://api.openrouter.ai/v1/models"
    headers = {"Authorization": f"Bearer {env_values['OPENROUTER_API_KEY']}"}
    resp = requests.get(test_url, headers=headers)
    if resp.status_code != 200:
        logging.error(f"OpenRouter API key verification failed: {resp.text}")
        raise EnvironmentError("Invalid OpenRouter API key")
    logging.info("OpenRouter API key verified successfully.")

def verify_claude_key():
    test_url = "https://api.openrouter.ai/v1/models"
    headers = {"Authorization": f"Bearer {env_values['CLAUDE_API_KEY']}"}
    resp = requests.get(test_url, headers=headers)
    if resp.status_code != 200:
        logging.error(f"Claude API key verification failed: {resp.text}")
        raise EnvironmentError("Invalid Claude API key")
    logging.info("Claude API key verified successfully.")

# Run all verifications
verify_google_credentials()
verify_youtube_key()
verify_openrouter_key()
verify_claude_key()

# ------------------- Main Logic -------------------

MIN_BLOG_LENGTH = env_values["MIN_BLOG_LENGTH"]
NICHE_DEFAULT = env_values["NICHE_DEFAULT"]

def fetch_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        logging.error(f"Transcript retrieval failed for video {video_id}: {e}")
        return None

def detect_language(text):
    try:
        return detect(text)
    except Exception as e:
        logging.warning(f"Language detection failed: {e}")
        return "unknown"

def generate_blog_content(transcript):
    # Replace this with your AI content generation using OpenRouter/Claude
    # Placeholder: simply returns transcript trimmed/padded to MIN_BLOG_LENGTH
    content = transcript[:MIN_BLOG_LENGTH]
    if len(content) < MIN_BLOG_LENGTH:
        content += " " * (MIN_BLOG_LENGTH - len(content))
    return content

def post_to_blogger(title, content):
    creds = Credentials(
        token=None,
        refresh_token=env_values["GOOGLE_REFRESH_TOKEN"],
        client_id=env_values["GOOGLE_CLIENT_ID"],
        client_secret=env_values["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token"
    )
    service = build('blogger', 'v3', credentials=creds)
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    result = service.posts().insert(blogId=env_values["BLOGGER_ID"], body=body).execute()
    logging.info(f"Blog posted successfully: {result.get('url')}")

# ------------------- Scheduler for Worker -------------------
def worker_task():
    logging.info("Worker task started.")
    # Example video ID for testing
    video_id = "dQw4w9WgXcQ"
    transcript = fetch_youtube_transcript(video_id)
    if transcript and len(transcript) >= MIN_BLOG_LENGTH:
        content = generate_blog_content(transcript)
        post_to_blogger("Automated Blog Post", content)
    logging.info("Worker task finished.")

# ------------------- Service Start -------------------
IS_WEB_SERVICE = "PORT" in os.environ

if IS_WEB_SERVICE:
    app = Flask(__name__)

    @app.route("/health")
    def health():
        return "OK", 200

    @app.route("/")
    def index():
        return "Blog automation service running", 200

    port = int(os.getenv("PORT", 5000))
    logging.info(f"Starting Web Service on port {port}")
    app.run(host="0.0.0.0", port=port)
else:
    logging.info("Starting Worker Service")
    schedule.every(30).minutes.do(worker_task)
    while True:
        schedule.run_pending()
        time.sleep(5)

