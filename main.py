import os
import sys
import logging
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time

# ----------------- Logging Setup -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ----------------- Environment Variables -----------------
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

def validate_env():
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        logging.error(f"Missing required environment variables: {missing}")
        sys.exit(1)
    logging.info("All required environment variables are present.")

# ----------------- API Verification -----------------
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

# ----------------- ClickBank Niche Links -----------------
NICHE_LINKS = {
    "Weight Loss": "https://www.clickbank.net/affiliate1",
    "Pelvic Health": "https://www.clickbank.net/affiliate2",
    "Joint Relief": "https://www.clickbank.net/affiliate3",
    "Liver Detox": "https://www.clickbank.net/affiliate4",
    "Side Hustles": "https://www.clickbank.net/affiliate5",
    "Respiratory Health": "https://www.clickbank.net/affiliate6"
}

# ----------------- YouTube Video Selection -----------------
def find_valid_video(niche):
    # Placeholder: logic to search YouTube videos based on niche keywords
    # Retry until we find one that meets requirements (English, length)
    search_keywords = niche
    # Example: YouTube API search here
    # For now, return a dummy video ID
    return "dQw4w9WgXcQ"  # Replace with real search logic

def is_transcript_valid(video_id, min_length):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t["text"] for t in transcript_list])
        if len(text.split()) < min_length:
            return False, None
        # Basic English check (could use langdetect if desired)
        if not all(ord(c) < 128 or c in "\n.,!?'" for c in text):
            return False, None
        return True, text
    except Exception as e:
        logging.warning(f"Transcript invalid for {video_id}: {e}")
        return False, None

# ----------------- Content Generation -----------------
def generate_blog_content(transcript, video_id, niche):
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    payload = {
        "prompt": f"Generate a blog post in English using this transcript: {transcript}\nInclude the niche affiliate link: {NICHE_LINKS[niche]}\nMention video publish date and title.\n",
        "model": "claude-instant-v1",
        "max_tokens": 1500
    }
    response = requests.post("https://openrouter.ai/api/v1/completions", json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    content = data.get("completion", "")
    return content

# ----------------- Post to Blogger -----------------
def post_to_blogger(title, content):
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token"
    )
    service = build("blogger", "v3", credentials=creds)
    post_body = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    blog_id = os.environ["BLOGGER_ID"]
    service.posts().insert(blogId=blog_id, body=post_body).execute()
    logging.info(f"Posted to Blogger: {title}")

# ----------------- Worker Workflow -----------------
def worker_task(niche):
    min_length = int(os.environ.get("MIN_BLOG_LENGTH", 300))
    while True:
        video_id = find_valid_video(niche)
        valid, transcript = is_transcript_valid(video_id, min_length)
        if valid:
            logging.info(f"Selected valid video {video_id} for niche {niche}")
            # Add video publish date and title
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            publish_date = datetime.now().strftime("%B %d, %Y")
            title = f"{niche} Update ({publish_date})"
            content = generate_blog_content(transcript, video_id, niche)
            post_to_blogger(title, content)
            break
        else:
            logging.info(f"Video {video_id} invalid. Searching again...")

# ----------------- Scheduler Setup -----------------
def schedule_posts():
    scheduler = BackgroundScheduler()
    # Tuesday: 2 posts
    scheduler.add_job(lambda: worker_task("Weight Loss"), 'cron', day_of_week='tue', hour=8, minute=0)
    scheduler.add_job(lambda: worker_task("Pelvic Health"), 'cron', day_of_week='tue', hour=12, minute=0)
    # Wednesday: 2 posts
    scheduler.add_job(lambda: worker_task("Joint Relief"), 'cron', day_of_week='wed', hour=8, minute=0)
    scheduler.add_job(lambda: worker_task("Liver Detox"), 'cron', day_of_week='wed', hour=12, minute=0)
    # Thursday: 2 posts
    scheduler.add_job(lambda: worker_task("Side Hustles"), 'cron', day_of_week='thu', hour=8, minute=0)
    scheduler.add_job(lambda: worker_task("Respiratory Health"), 'cron', day_of_week='thu', hour=12, minute=0)
    scheduler.start()
    logging.info("Scheduler started with weekly posting times.")

# ----------------- Main Execution -----------------
def main():
    logging.info("Starting Worker service...")

    validate_env()
    verify_blogger_credentials()
    verify_youtube_api()
    verify_openrouter_key()

    logging.info("All pre-flight checks passed. Proceeding to main workflow...")
    schedule_posts()

    try:
        while True:
            time.sleep(30)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Worker shutting down.")

if __name__ == "__main__":
    main()

