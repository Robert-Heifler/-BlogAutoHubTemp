import os
import re
import sys
import time
import logging
import random
import argparse
import requests
import schedule
from datetime import datetime
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, VideoUnavailable
from langdetect import detect
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build as g_build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# -----------------------
# Logging configuration
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)

# -----------------------
# Environment variables
# -----------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BLOGGER_BLOG_ID = os.getenv("BLOGGER_BLOG_ID")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
PORT = int(os.getenv("PORT", 5000))

required_env_vars = [
    OPENROUTER_API_KEY, BLOGGER_BLOG_ID, GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, YOUTUBE_API_KEY
]
if any(var is None for var in required_env_vars):
    raise EnvironmentError("Missing required environment variables. Please check Render config.")

# -----------------------
# Constants
# -----------------------
CHUNK_SIZE = 2000
MAX_RETRIES = 3
BACKOFF_FACTOR = 2
MIN_BLOG_WORDS = 250
DEFAULT_NICHES = ["weight loss", "pelvic health", "joint relief", "liver detox", "respiratory health"]

# -----------------------
# Helper Functions
# -----------------------
def wait_for_network(max_wait=60):
    url = "https://www.google.com"
    start = time.time()
    while True:
        try:
            requests.get(url, timeout=5)
            logger.info("Network connectivity verified.")
            return
        except Exception as e:
            elapsed = int(time.time() - start)
            if elapsed > max_wait:
                logger.warning(f"Network unavailable after {max_wait}s. Proceeding anyway.")
                return
            logger.info(f"Network not ready yet ({e}). Retrying in 5s...")
            time.sleep(5)

def fetch_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'].strip() for entry in transcript_list])
        if not is_english(text) or len(text) < 200:
            logger.warning(f"Transcript invalid or too short for video {video_id}.")
            return None
        return text
    except (TranscriptsDisabled, VideoUnavailable):
        logger.error(f"Transcript unavailable for video {video_id}.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching transcript for {video_id}: {e}")
        return None

def is_english(text):
    try:
        lang = detect(text)
        if lang == "en":
            return True
    except:
        pass
    # fallback heuristic
    english_words = ["the","and","is","of","to","in","for","with","on","as"]
    word_count = len(text.split())
    matches = sum(1 for w in text.lower().split() if w in english_words)
    return word_count > 20 and (matches / word_count) > 0.05

def chunk_text(text, max_chars=CHUNK_SIZE):
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += " " + sentence if current_chunk else sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def call_openrouter_api(prompt):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "anthropic/claude-3-sonnet", "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
            r.raise_for_status()
            resp_json = r.json()
            raw_content = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            if isinstance(raw_content, list):
                raw_content = " ".join([c.get("text","") for c in raw_content if c.get("text")])
            if raw_content:
                return raw_content
            else:
                logger.error(f"OpenRouter returned empty content. Raw response: {resp_json}")
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter request error: {e}")
            time.sleep(BACKOFF_FACTOR ** attempt)
    return None

def get_blogger_service():
    creds_info = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "token_uri": "https://oauth2.googleapis.com/token"
    }
    try:
        creds = Credentials.from_authorized_user_info(info=creds_info, scopes=["https://www.googleapis.com/auth/blogger"])
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        if not creds.valid:
            logger.error("Invalid Blogger credentials after refresh.")
            return None
        return g_build("blogger", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Blogger service setup failed: {e}")
        return None

def publish_post(title, content):
    service = get_blogger_service()
    if not service:
        logger.error("Blogger service not available. Cannot publish post.")
        return None
    try:
        post_body = {"kind": "blogger#post", "blog": {"id": BLOGGER_BLOG_ID}, "title": title, "content": content}
        post = service.posts().insert(blogId=BLOGGER_BLOG_ID, body=post_body).execute()
        logger.info(f"✅ Post published: {post.get('url')}")
        return post.get("url")
    except HttpError as e:
        logger.error(f"Blogger API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error publishing post: {e}")
    return None

def generate_blog_html(video_id, content, title):
    embed = f"""
    <div style='text-align:center; margin-bottom:20px;'>
        <iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}?rel=0" frameborder="0" allowfullscreen></iframe>
    </div>
    """
    return f"<h2>{title}</h2>{embed}<div>{content}</div>"

def search_youtube_video(niche, max_attempts=10):
    from googleapiclient.discovery import build as g_build
    youtube = g_build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    for attempt in range(max_attempts):
        try:
            res = youtube.search().list(
                q=niche, part="id,snippet", type="video",
                videoLicense="creativeCommon", maxResults=5
            ).execute()
            items = res.get("items", [])
            random.shuffle(items)
            for item in items:
                vid = item["id"]["videoId"]
                transcript = fetch_transcript(vid)
                if transcript:
                    return vid, transcript
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
        time.sleep(5)
    raise RuntimeError(f"No usable Creative Commons English video found for niche '{niche}' after {max_attempts} attempts.")

def run_blog_cycle(niches=None, video_id=None, transcript=None):
    niches = niches or DEFAULT_NICHES
    logger.info("=== Starting blog post creation cycle ===")
    for niche in niches:
        try:
            if not video_id or not transcript:
                video_id, transcript = search_youtube_video(niche)
            if not transcript:
                logger.warning(f"No valid transcript for niche '{niche}'. Trying next niche.")
                continue
            chunks = chunk_text(transcript)
            blog_content = ""
            for chunk in chunks:
                prompt = f"Rewrite the following transcript into a detailed SEO blog article:\n\n{chunk}"
                part = call_openrouter_api(prompt)
                if part:
                    blog_content += part + "\n\n"
                else:
                    logger.warning("OpenRouter API failed for a chunk. Skipping chunk.")
            if not blog_content or len(blog_content.split()) < MIN_BLOG_WORDS:
                logger.warning(f"Blog content too short for niche '{niche}'. Trying next niche.")
                continue
            title = f"Blog Post - {niche} - {video_id[:6]} - {datetime.now():%Y-%m-%d %H:%M}"
            html_content = generate_blog_html(video_id, blog_content, title)
            publish_post(title, html_content)
            logger.info("=== Finished blog cycle ===")
            return
        except Exception as e:
            logger.error(f"Error generating blog for niche '{niche}': {e}")
    logger.error("No successful blog post created in this cycle.")

# -----------------------
# Flask API Endpoints
# -----------------------
@app.route("/generate", methods=["POST"])
def generate_blog():
    data = request.json
    video_id = data.get("video_id")
    niche = data.get("niche")
    run_blog_cycle(niches=[niche] if niche else DEFAULT_NICHES, video_id=video_id)
    return jsonify({"status": "Triggered"}), 200

@app.route("/diagnostics", methods=["GET"])
def diagnostics():
    results = {"env_vars_set": all(required_env_vars)}
    # OpenRouter test
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}, timeout=5)
        results["openrouter_ok"] = r.status_code == 200
    except:
        results["openrouter_ok"] = False
    # Blogger test
    try:
        service = get_blogger_service()
        results["blogger_ok"] = service is not None
    except:
        results["blogger_ok"] = False
    # YouTube test
    try:
        youtube = g_build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        youtube.search().list(part="id", q="test", maxResults=1).execute()
        results["youtube_ok"] = True
    except:
        results["youtube_ok"] = False
    return jsonify(results), 200

# -----------------------
# Scheduler
# -----------------------
def schedule_jobs():
    logger.info("Initializing scheduler: 2 posts Tue/Wed/Thu")
    times = ["10:00", "15:00"]
    days = ["tuesday", "wednesday", "thursday"]
    for day in days:
        for t in times:
            getattr(schedule.every(), day).at(t).do(run_blog_cycle)

def main():
    wait_for_network()
    schedule_jobs()
    while True:
        schedule.run_pending()
        time.sleep(60)

# -----------------------
# Entrypoint
# -----------------------
if __name__ == "__main__":
    if "RENDER" in os.environ:
        app.run(host="0.0.0.0", port=PORT)
    else:
        main()
