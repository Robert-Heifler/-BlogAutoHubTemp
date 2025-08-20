import os
import time
import threading
import logging
from flask import Flask

import requests
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
import openai

# --- Logging setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Flask app to keep Render alive ---
app = Flask(__name__)

@app.route("/")
def health():
    return "Service running", 200

# --- Environment variables ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BLOG_ID = os.getenv("BLOG_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# --- Blogger posting ---
def post_to_blogger(title: str, content: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/blogger"])
    service = build("blogger", "v3", credentials=creds)

    post = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    result = service.posts().insert(blogId=BLOG_ID, body=post, isDraft=False).execute()
    logging.info(f"Posted to Blogger: {result['url']}")
    return result['url']

# --- YouTube search + transcript ---
def find_videos(query="weight loss tips", max_results=3):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    search = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        videoLicense="creativeCommon",
        maxResults=max_results
    ).execute()
    return [
        {
            "id": item["id"]["videoId"],
            "title": item["snippet"]["title"]
        }
        for item in search.get("items", [])
    ]

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        logging.warning(f"No transcript for {video_id}: {e}")
        return None

# --- AI summarization ---
def summarize_with_ai(transcript, video_title):
    prompt = f"""
    Create a detailed, SEO-optimized blog post based on the following transcript.
    The blog should include:
    - An engaging title
    - A clear introduction
    - 3–5 structured sections
    - A conclusion
    - Natural inclusion of keywords
    - Embed code for the YouTube video titled: {video_title}

    Transcript:
    {transcript}
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}]
    }
    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# --- Main worker loop ---
def run_job():
    logging.info("Job started")
    videos = find_videos()
    for video in videos:
        transcript = get_transcript(video["id"])
        if not transcript:
            continue
        content = summarize_with_ai(transcript, video["title"])
        embed = f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video["id"]}" frameborder="0" allowfullscreen></iframe>'
        post_to_blogger(video["title"], embed + "<br><br>" + content)
    logging.info("Job finished")

def scheduler():
    while True:
        now = datetime.utcnow()
        # Example: post only on Tue/Wed/Thu at 15:00 UTC
        if now.weekday() in [1, 2, 3] and now.hour == 15 and now.minute == 0:
            run_job()
            time.sleep(60)
        time.sleep(20)

# --- Background thread ---
def start_scheduler():
    t = threading.Thread(target=scheduler, daemon=True)
    t.start()

if __name__ == "__main__":
    start_scheduler()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

