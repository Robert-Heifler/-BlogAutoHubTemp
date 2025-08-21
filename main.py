import os
import json
import logging
import random
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from youtube_transcript_api import YouTubeTranscriptApi

# Setup logging
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Scheduler
scheduler = BackgroundScheduler()

# File paths
KEYWORDS_FILE = "keywords.jason"
USED_INDEX_FILE = "used_keyword_index.json"

# Load keywords
if os.path.exists(KEYWORDS_FILE):
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        try:
            KEYWORDS_DATA = json.load(f)
        except Exception as e:
            logging.error(f"Failed to parse {KEYWORDS_FILE}: {e}")
            KEYWORDS_DATA = {}
else:
    logging.error(f"{KEYWORDS_FILE} not found!")
    KEYWORDS_DATA = {}

# Load used keyword indexes to rotate sequentially
if os.path.exists(USED_INDEX_FILE):
    with open(USED_INDEX_FILE, "r", encoding="utf-8") as f:
        try:
            USED_INDEX = json.load(f)
        except Exception as e:
            logging.error(f"Failed to parse {USED_INDEX_FILE}: {e}")
            USED_INDEX = {}
else:
    USED_INDEX = {}

# Function to get next keyword sequentially for a niche
def get_next_keyword(niche):
    keywords = KEYWORDS_DATA.get(niche, [])
    if not keywords:
        logging.error(f"No keywords found for niche '{niche}'")
        return None
    index = USED_INDEX.get(niche, 0)
    keyword = keywords[index % len(keywords)]
    USED_INDEX[niche] = (index + 1) % len(keywords)
    # Save back updated index
    with open(USED_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(USED_INDEX, f, indent=2)
    return keyword

# Example function: find YouTube videos and create blog post
def create_blog_post(niche):
    keyword = get_next_keyword(niche)
    if not keyword:
        logging.error(f"No keyword available for niche {niche}. Skipping post creation.")
        return

    logging.info(f"Using keyword '{keyword}' for niche '{niche}'")

    # Your YouTube search and transcript workflow goes here
    # (Pseudo code for integration; adapt as needed)
    # videos = search_youtube(keyword)
    # transcript = YouTubeTranscriptApi.get_transcript(videos[0]['id'])
    # blog_content = generate_blog_content(transcript, keyword)
    # post_to_blogger(blog_content, niche)

# Scheduler jobs
def schedule_jobs():
    # Example: Tue/Wed/Thu at 10:05 and 14:35
    scheduler.add_job(lambda: create_blog_post("Weight Loss"), 'cron', day_of_week='1-3', hour=10, minute=5)
    scheduler.add_job(lambda: create_blog_post("Weight Loss"), 'cron', day_of_week='1-3', hour=14, minute=35)
    # Add other niches similarly
    scheduler.start()
    logging.info("Scheduler started")

# Flask routes
@app.route("/")
def home():
    return "Blog Worker Running"

@app.route("/run-now")
def run_now():
    niche = request.args.get("niche", "Weight Loss")
    create_blog_post(niche)
    return f"Triggered blog post creation for niche '{niche}'"

# Main
if __name__ == "__main__":
    schedule_jobs()
    app.run(host="0.0.0.0", port=10000)
