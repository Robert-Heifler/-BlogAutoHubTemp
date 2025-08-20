import os
import sys
import logging
import requests
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from youtube_transcript_api import YouTubeTranscriptApi
from apscheduler.schedulers.background import BackgroundScheduler
import time

# ----------------- Logging Setup -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ----------------- Required Environment Variables -----------------
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

# ----------------- Niches and ClickBank URLs -----------------
NICHE_CLICKBANK_MAP = {
    "Weight Loss": "https://www.clickbank.net/weightloss",
    "Pelvic Health": "https://www.clickbank.net/pelvichealth",
    "Joint Relief": "https://www.clickbank.net/jointrelief",
    "Liver Detox": "https://www.clickbank.net/liverdetox",
    "Side Hustles": "https://www.clickbank.net/sidehustle",
    "Respiratory Health": "https://www.clickbank.net/respiratory"
}

# ----------------- Helper Functions -----------------

def validate_env():
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        logging.error(f"Missing required environment variables: {missing}")
        sys.exit(1)
    logging.info("All required environment variables are present.")

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
        return service
    except Exception as e:
        logging.error(f"Blogger verification failed: {e}")
        sys.exit(1)

def verify_youtube_api():
    test_url = f"https://www.googleapis.com/youtube/v3/channels?part=id&id=UC_x5XG1OV2P6uZZ5FSM9Ttw&key={os.environ['YOUTUBE_API_KEY']}"
    try:
        resp = requests.get(test_url)
        resp.raise_for_status()
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

def get_youtube_videos(niche, min_length=200):
    # Placeholder search logic: replace with actual YouTube API search
    logging.info(f"Searching YouTube for niche '{niche}' with min transcript length {min_length}")
    # Returns a list of video_ids
    return ["dQw4w9WgXcQ"]  # Example placeholder

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        words = " ".join([t["text"] for t in transcript])
        if len(words.split()) < int(os.environ["MIN_BLOG_LENGTH"]):
            logging.info(f"Transcript too short for video {video_id}, skipping")
            return None
        logging.info(f"Transcript fetched and validated for video {video_id}")
        return transcript
    except Exception as e:
        logging.warning(f"Failed to get transcript for video {video_id}: {e}")
        return None

def generate_content(transcript, video_title, video_date, niche):
    prompt = f"""
    Create a unique SEO-friendly blog post from this transcript:
    Transcript: {transcript}
    Video Title: {video_title}
    Video Date: {video_date}
    Niche: {niche}
    Include a soft CTA linking to {NICHE_CLICKBANK_MAP[niche]}.
    Ensure content is in English and at least {os.environ['MIN_BLOG_LENGTH']} words.
    """
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    data = {"prompt": prompt, "max_tokens": 2000, "temperature": 0.7}
    try:
        resp = requests.post("https://openrouter.ai/api/v1/completions", json=data, headers=headers, timeout=15)
        resp.raise_for_status()
        content = resp.json().get("choices")[0]["text"]
        logging.info("Content generated successfully")
        return content
    except Exception as e:
        logging.error(f"Content generation failed: {e}")
        return None

def post_to_blogger(service, title, content):
    try:
        body = {"title": title, "content": content}
        post = service.posts().insert(blogId=os.environ["BLOGGER_ID"], body=body).execute()
        logging.info(f"Post published successfully: {post['url']}")
    except Exception as e:
        logging.error(f"Failed to post to Blogger: {e}")

# ----------------- Main Workflow -----------------

def run_worker(niche):
    service = verify_blogger_credentials()
    videos = get_youtube_videos(niche)
    for vid in videos:
        transcript_data = get_transcript(vid)
        if not transcript_data:
            continue
        transcript_text = " ".join([t["text"] for t in transcript_data])
        content = generate_content(transcript_text, f"Video {vid}", datetime.now().strftime("%Y-%m-%d"), niche)
        if content:
            post_to_blogger(service, f"{niche} Update - {datetime.now().strftime('%Y-%m-%d')}", content)
            break

# ----------------- Scheduler -----------------

def schedule_posts():
    scheduler = BackgroundScheduler()
    # Schedule 2 posts each on Tue, Wed, Thu at 09:00 and 15:00
    days = ["tue", "wed", "thu"]
    hours = [9, 15]
    for day in days:
        for hour in hours:
            scheduler.add_job(lambda: run_worker(os.environ["NICHE_DEFAULT"]), day_of_week=day, hour=hour)
    scheduler.start()
    logging.info("Scheduled posts initialized")

# ----------------- Immediate Test Post -----------------

def immediate_test_post():
    logging.info("Triggering immediate test post")
    run_worker(os.environ["NICHE_DEFAULT"])

# ----------------- Main -----------------

def main():
    logging.info("Starting Worker service...")
    validate_env()
    verify_youtube_api()
    verify_openrouter_key()
    schedule_posts()
    immediate_test_post()  # Runs once immediately after deploy
    logging.info("Worker main workflow initialized and scheduler running")

    # Keep service alive for scheduler
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down worker service")

if __name__ == "__main__":
    main()


