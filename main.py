import os
import json
import logging
from datetime import datetime
import requests
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# =====================
# Environment Variables
# =====================
REQUIRED_ENV = ["GITHUB_TOKEN", "GITHUB_REPO", "NICHE_DEFAULT", "YOUTUBE_API_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "BLOGGER_BLOG_ID"]
missing = [e for e in REQUIRED_ENV if not os.getenv(e)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {missing}")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
NICHE_DEFAULT = os.getenv("NICHE_DEFAULT")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
BLOGGER_BLOG_ID = os.getenv("BLOGGER_BLOG_ID")

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
        return json.loads(content)
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
# Niche Configuration
# =====================
CLICKBANK_OFFERS = {
    "weight_loss": {"keywords": ["weight loss", "diet", "fat loss"]},
    "pelvic_health": {"keywords": ["pelvic floor", "kegel"]},
    "joint_relief": {"keywords": ["joint pain", "arthritis"]},
    "liver_detox": {"keywords": ["liver cleanse", "detox"]},
    "side_hustles": {"keywords": ["side hustle", "make money online"]},
    "respiratory_health": {"keywords": ["lung health", "respiratory support"]},
}

def normalize_niche_key(niche_key):
    return (niche_key or NICHE_DEFAULT).strip().lower().replace(" ", "_")

# =====================
# YouTube API Search
# =====================
from googleapiclient.discovery import build

yt_service = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def search_youtube_video(niche_key):
    niche_normalized = normalize_niche_key(niche_key)
    keywords = CLICKBANK_OFFERS.get(niche_normalized, {}).get('keywords', [])
    if not keywords:
        logging.error(f"No keywords found for niche {niche_key}")
        return None
    query = ' '.join(keywords)
    request = yt_service.search().list(part='id', type='video', q=query, videoLicense='creativeCommon', maxResults=5)
    response = request.execute()
    for item in response.get('items', []):
        vid_id = item['id']['videoId']
        if vid_id not in previously_used_videos['videos']:
            previously_used_videos['videos'].append(vid_id)
            save_previous_videos(previously_used_videos)
            return vid_id
    logging.warning(f"No new Creative Commons videos found for niche '{niche_key}'")
    return None

# =====================
# AI Blog Generation
# =====================
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_blog_content(transcript, niche_key):
    prompt = f"Create a detailed, engaging blog post for niche '{niche_key}' using the following transcript: {transcript}" 
    response = openai.Completion.create(model="text-davinci-003", prompt=prompt, max_tokens=1500)
    return response.choices[0].text

# =====================
# Blogger Posting
# =====================
def post_to_blogger(title, content):
    creds = Credentials.from_authorized_user_info({
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET')
    })
    service = build('blogger', 'v3', credentials=creds)
    body = {
        'kind': 'blogger#post',
        'title': title,
        'content': content
    }
    post = service.posts().insert(blogId=BLOGGER_BLOG_ID, body=body).execute()
    return f"https://{service._baseUrl}/blog/{BLOGGER_BLOG_ID}/posts/{post['id']}"

# =====================
# Generate & Post
# =====================
def generate_and_post(niche_key):
    video_id = search_youtube_video(niche_key)
    if not video_id:
        return None
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    transcript_text = ' '.join([t['text'] for t in transcript_list])
    blog_content = generate_blog_content(transcript_text, niche_key)
    blog_url = post_to_blogger(f"{niche_key} Insights - {datetime.now().strftime('%Y-%m-%d')}", blog_content)
    logging.info(f"Blog post created at {blog_url}")
    return blog_url

# =====================
# Flask + Scheduler
# =====================
app = Flask(__name__)
scheduler = BackgroundScheduler()

def schedule_jobs():
    niches = list(CLICKBANK_OFFERS.keys())
    for niche in niches:
        scheduler.add_job(lambda n=niche: generate_and_post(n), 'cron', day_of_week='tue,wed,thu', hour=10, minute=5)
        scheduler.add_job(lambda n=niche: generate_and_post(n), 'cron', day_of_week='tue,wed,thu', hour=14, minute=35)
    scheduler.start()
    logging.info("Scheduler started for Tue/Wed/Thu at 10:05 and 14:35.")

schedule_jobs()

@app.route('/')
def index():
    return "Blog Auto Hub Worker is running!"

@app.route('/run-now')
def run_now():
    blog_url = generate_and_post(NICHE_DEFAULT)
    if blog_url:
        return jsonify({'message': 'Blog post generated', 'status': 'success', 'url': blog_url})
    else:
        return jsonify({'message': 'No blog post generated', 'status': 'fail'})

# =====================
# Main
# =====================
if __name__ == '__main__':
    logging.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=10000)
