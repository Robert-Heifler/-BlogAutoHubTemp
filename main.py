import os
import json
import logging
from datetime import datetime
import requests
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler


# =====================
# Environment Validation
# =====================
REQUIRED_ENV = ["GITHUB_TOKEN", "GITHUB_REPO", "NICHE_DEFAULT", "OPENROUTER_API_KEY"]
missing = [e for e in REQUIRED_ENV if not os.getenv(e)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {missing}")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
NICHE_DEFAULT = os.getenv("NICHE_DEFAULT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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
        content = requests.utils.unquote(resp.json()["content"])
        previous_videos = json.loads(content)
        logging.info("Previously used videos loaded from GitHub.")
        return previous_videos
    except Exception as e:
        logging.warning(f"Could not load previously used videos from GitHub. Starting fresh. Error: {e}")
        return {"videos": []}

def save_previous_videos(videos):
    try:
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
# Niche Normalization
# =====================
def normalize_niche_key(niche_key):
    return (niche_key or NICHE_DEFAULT).strip().lower().replace(" ", "_")

# =====================
# ClickBank Offers Placeholder
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
    logging.info(f"Searching YouTube for niche '{niche_normalized}' with keywords: {keywords}")
    return [{"id": "video1"}, {"id": "video2"}]  # Placeholder for real YouTube API search

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
# OpenRouter AI Prompt Generation
# =====================
def generate_blog_content(video_id, niche):
    prompt = (
        f"Create a full, SEO-optimized blog post for the niche '{niche}' "
        f"based on the YouTube video ID '{video_id}'. Include title, subheadings, "
        f"bullet points, and a natural ClickBank offer placement. Use a friendly, persuasive tone."
    )
    url = "https://api.openrouter.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "claude-3-haiku",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500
    }
    try:
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logging.info(f"Generated blog content for video {video_id}")
        return content
    except Exception as e:
        logging.error(f"Failed to generate blog content: {e}")
        return None

# =====================
# Blog Post Publishing Placeholder
# =====================
def publish_blog_post(blog_content, niche):
    # Placeholder: integrate Blogger API or CMS publishing here
    blog_url = f"https://blogautohubtemp.blogspot.com/{normalize_niche_key(niche)}/{datetime.now().strftime('%Y-%m-%d')}"
    logging.info(f"Published blog post at {blog_url}")
    return blog_url

# =====================
# Generate & Post Workflow
# =====================
def generate_and_post(niche):
    video = find_qualified_video(niche)
    if not video:
        logging.error(f"❌ generate_and_post failed: '{niche}'")
        return None
    blog_content = generate_blog_content(video["id"], niche)
    if not blog_content:
        logging.error(f"❌ Blog content generation failed for '{niche}'")
        return None
    blog_url = publish_blog_post(blog_content, niche)
    return blog_url

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
    blog_url = generate_and_post(NICHE_DEFAULT)
    if blog_url:
        return jsonify({"status": "success", "blog_url": blog_url})
    else:
        return jsonify({"status": "fail", "message": "No blog post generated"})

# =====================
# Main
# =====================
if __name__ == "__main__":
    logging.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=10000)
