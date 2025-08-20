import os
import json
import logging
from datetime import datetime, timedelta, timezone
import requests
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# =====================
# Environment Validation
# =====================
REQUIRED_ENV = ["GITHUB_TOKEN", "GITHUB_REPO", "NICHE_DEFAULT"]
missing = [e for e in REQUIRED_ENV if not os.getenv(e)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {missing}")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
NICHE_DEFAULT = os.getenv("NICHE_DEFAULT")

# =====================
# Logging
# =====================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# =====================
# GitHub Persistence
# =====================
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/previously_used_youtube_videos.json"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def load_previous_videos():
    try:
        resp = requests.get(GITHUB_API_URL, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        content = requests.utils.unquote(resp.json()["content"])
        previous_videos = json.loads(content)
        logging.info("Previously used videos loaded from GitHub.")
        return previous_videos
    except Exception as e:
        logging.warning(f"Could not load previously used videos from GitHub. Starting fresh. Error: {e}")
        return {"videos": []}

def save_previous_videos(videos):
    try:
        # Fetch SHA for update
        resp = requests.get(GITHUB_API_URL, headers=HEADERS)
        resp.raise_for_status()
        sha = resp.json()["sha"]
        payload = {
            "message": f"Update used videos {datetime.now().isoformat()}",
            "content": json.dumps(videos, indent=2).encode("utf-8").hex(),
            "sha": sha
        }
        put_resp = requests.put(GITHUB_API_URL, headers=HEADERS, json=payload)
        put_resp.raise_for_status()
        logging.info("Previously used videos updated on GitHub.")
    except Exception as e:
        logging.error(f"Failed to update previously used videos on GitHub: {e}")

previously_used_videos = load_previous_videos()

# =====================
# Niche Key Normalization
# =====================
def normalize_niche_key(niche_key):
    return (niche_key or NICHE_DEFAULT).strip().lower().replace(" ", "_")

# =====================
# Placeholder for ClickBank offers
# =====================
CLICKBANK_OFFERS = {
    "weight_loss": {"keywords": ["weight loss", "diet", "fat loss"]},
    "pelvic_health": {"keywords": ["pelvic floor", "kegel"]},
    "joint_relief": {"keywords": ["joint pain", "arthritis"]},
    "liver_detox": {"keywords": ["liver cleanse", "detox"]},
    "side_hustles": {"keywords": ["side hustle", "make money online"]},
    "respiratory_health": {"keywords": ["lung health", "respiratory support"]},
}

# =====================
# YouTube Search Stub
# =====================
def search_yt_videos(niche_key):
    niche_normalized = normalize_niche_key(niche_key)
    if niche_normalized not in CLICKBANK_OFFERS:
        logging.error(f"Niche key '{niche_key}' normalized to '{niche_normalized}' not found in ClickBank offers.")
        return []
    keywords = CLICKBANK_OFFERS[niche_normalized]["keywords"]
    # Placeholder: Replace with real YouTube API search
    logging.info(f"Searching YouTube for niche '{niche_normalized}' with keywords: {keywords}")
    return [{"id": "video1"}, {"id": "video2"}]

def find_qualified_video(niche_key):
    candidates = search_yt_videos(niche_key)
    for video in candidates:
        if video["id"] not in previously_used_videos["videos"]:
            previously_used_videos["videos"].append(video["id"])
            save_previous_videos(previously_used_videos)
            return video
    logging.warning(f"No new videos found for niche '{niche_key}'")
    return None

# =====================
# Placeholder: Generate & Post
# =====================
def generate_and_post(niche):
    video = find_qualified_video(niche)
    if not video:
        logging.error(f"❌ generate_and_post failed: '{niche}'")
        return
    logging.info(f"Posting video {video['id']} for niche '{niche}'")
    # Add blog post creation and publishing logic here

# =====================
# Scheduler Setup
# =====================
app = Flask(__name__)
scheduler = BackgroundScheduler()

def schedule_jobs():
    niches = ["Weight Loss", "Pelvic Health", "Joint Relief", "Liver Detox", "Side Hustles", "Respiratory Health"]
    for niche in niches:
        scheduler.add_job(lambda n=niche: generate_and_post(n), 'cron', day_of_week='tue,wed,thu', hour=10, minute=5)
        scheduler.add_job(lambda n=niche: generate_and_post(n), 'cron', day_of_week='tue,wed,thu', hour=14, minute=35)
    scheduler.start()
    logging.info("Scheduler started for Tue/Wed/Thu at 10:05 and 14:35.")

schedule_jobs()

# =====================
# Flask Routes
# =====================
@app.route('/')
def index():
    return "Blog Auto Hub Worker is running!"

@app.route('/run-now')
def run_now():
    generate_and_post(NICHE_DEFAULT)
    return "Run-now executed."

# =====================
# Main
# =====================
if __name__ == "__main__":
    logging.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=10000)
