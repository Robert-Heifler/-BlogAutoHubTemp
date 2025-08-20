import os
import time
import logging
from datetime import datetime
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
import openai
from youtube_transcript_api import YouTubeTranscriptApi
from apscheduler.schedulers.background import BackgroundScheduler

# ---------------------- Logging Setup ----------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# ---------------------- Environment Variables ----------------------
BLOGGER_ID = os.environ.get('BLOGGER_ID')
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
MIN_BLOG_LENGTH = os.environ.get('MIN_BLOG_LENGTH')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REFRESH_TOKEN = os.environ.get('GOOGLE_REFRESH_TOKEN')
NICHE_DEFAULT = os.environ.get('NICHE_DEFAULT')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

REQUIRED_VARS = ['BLOGGER_ID','CLAUDE_API_KEY','YOUTUBE_API_KEY','MIN_BLOG_LENGTH']

missing_vars = [var for var in REQUIRED_VARS if not os.environ.get(var)]
if missing_vars:
    logging.error(f"Missing required environment variables: {missing_vars}")
    exit(1)

# ---------------------- Spin-up Logic ----------------------
def spin_up_service():
    logging.info("Checking if AI service is awake...")
    awake = False
    # This simulates a check to ensure AI/cloud service is active
    for _ in range(5):
        try:
            # Replace with actual API ping if needed
            resp = requests.get('https://api.openrouter.ai/v1/ping', headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'}, timeout=5)
            if resp.status_code == 200:
                awake = True
                break
        except Exception as e:
            logging.warning(f"Spin-up check failed, retrying: {e}")
        time.sleep(3)
    if not awake:
        logging.error("Failed to wake AI service.")
        exit(1)
    logging.info("AI service awake ✅")

# ---------------------- YouTube Video Retrieval ----------------------
def search_youtube_videos(query, max_results=3):
    logging.info(f"Searching YouTube for: {query}")
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(q=query, part='snippet', maxResults=max_results, type='video', videoLicense='creativeCommon', order='viewCount')
    response = request.execute()
    videos = []
    for item in response.get('items', []):
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        videos.append({'id': video_id, 'title': title})
    logging.info(f"Found videos: {videos}")
    return videos

# ---------------------- Transcript Retrieval ----------------------
def get_transcript(video_id):
    logging.info(f"Fetching transcript for video {video_id}")
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([t['text'] for t in transcript_list])
        return transcript
    except Exception as e:
        logging.warning(f"Failed to fetch transcript: {e}")
        return ''

# ---------------------- AI Blog Generation ----------------------
def generate_blog_post(prompt_text):
    logging.info("Generating blog post using Claude/OpenRouter...")
    headers = {'Authorization': f'Bearer {CLAUDE_API_KEY}', 'Content-Type': 'application/json'}
    data = {'prompt': prompt_text, 'max_tokens': 2000}
    resp = requests.post('https://api.openrouter.ai/v1/completions', headers=headers, json=data)
    if resp.status_code != 200:
        logging.error(f"AI generation failed: {resp.text}")
        return ''
    result = resp.json()
    blog_content = result.get('completion', '')
    return blog_content

# ---------------------- Blogger Posting ----------------------
def publish_to_blogger(title, content):
    logging.info(f"Publishing post: {title}")
    creds = Credentials(None, refresh_token=GOOGLE_REFRESH_TOKEN, client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET, token_uri='https://oauth2.googleapis.com/token')
    try:
        service = build('blogger', 'v3', credentials=creds)
        body = {'kind': 'blogger#post', 'blog': {'id': BLOGGER_ID}, 'title': title, 'content': content}
        post = service.posts().insert(blogId=BLOGGER_ID, body=body, isDraft=False).execute()
        logging.info(f"Post published successfully: {post['id']}")
    except HttpError as e:
        logging.error(f"Blogger API error: {e}")

# ---------------------- Main Workflow ----------------------
def run_post_creation():
    spin_up_service()
    videos = search_youtube_videos(NICHE_DEFAULT, max_results=2)
    if not videos:
        logging.error("No suitable YouTube videos found.")
        return

    for video in videos:
        transcript = get_transcript(video['id'])
        if len(transcript) < int(MIN_BLOG_LENGTH):
            logging.warning(f"Transcript too short, skipping video {video['id']}")
            continue
        prompt = f"Create a complete SEO-optimized blog post based on this transcript: {transcript}. Include a soft CTA."
        blog_content = generate_blog_post(prompt)
        if blog_content:
            publish_to_blogger(video['title'], blog_content)

# ---------------------- Scheduler ----------------------
scheduler = BackgroundScheduler()
scheduler.add_job(run_post_creation, 'cron', day_of_week='mon-fri', hour=6, minute=0)
scheduler.start()

# ---------------------- Immediate Test Run ----------------------
if __name__ == '__main__':
    logging.info("Starting immediate test run...")
    run_post_creation()
    while True:
        time.sleep(60)  # Keep scheduler alive
