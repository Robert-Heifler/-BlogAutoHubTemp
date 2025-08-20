import os
import time
import logging
from datetime import datetime
import requests
import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import schedule

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Environment variables
required_env_vars = [
    'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REFRESH_TOKEN',
    'BLOGGER_ID', 'OPENROUTER_API_KEY', 'CLAUDE_API_KEY',
    'YOUTUBE_API_KEY', 'NICHE_DEFAULT', 'MIN_BLOG_LENGTH'
]

env = {}
missing_vars = []

for var in required_env_vars:
    value = os.getenv(var)
    if not value:
        missing_vars.append(var)
    env[var] = value

if missing_vars:
    logging.error(f"Missing required environment variables: {missing_vars}")
    raise EnvironmentError(f"Missing required environment variables: {missing_vars}")

# Spin-up logic to prevent sleeping
def spin_up_service():
    logging.info("Spinning up service to prevent sleep mode...")
    # Dummy GET request to self or keepalive endpoint
    try:
        requests.get("https://your-service-url.com/keepalive", timeout=5)
    except Exception:
        pass
    time.sleep(3)  # wait a few seconds for full wake-up

spin_up_service()

# Initialize Google Blogger API
creds = Credentials(
    token=None,
    refresh_token=env['GOOGLE_REFRESH_TOKEN'],
    client_id=env['GOOGLE_CLIENT_ID'],
    client_secret=env['GOOGLE_CLIENT_SECRET'],
    token_uri='https://oauth2.googleapis.com/token'
)
blogger_service = build('blogger', 'v3', credentials=creds)

# AI prompt function for Claude via OpenRouter
def get_ai_blog_content(prompt):
    logging.info("Generating blog content with AI...")
    headers = {"Authorization": f"Bearer {env['CLAUDE_API_KEY']}"}
    payload = {"prompt": prompt, "model": "claude-3-haiku", "max_tokens": 1000}
    response = requests.post("https://api.openrouter.ai/v1/completions", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['completion']

# YouTube video search function
def search_youtube_videos(query, max_results=3):
    logging.info(f"Searching YouTube for videos matching: {query}")
    url = f"https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'key': env['YOUTUBE_API_KEY'],
        'maxResults': max_results
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    items = response.json().get('items', [])
    video_urls = [f"https://www.youtube.com/watch?v={item['id']['videoId']}" for item in items]
    return video_urls

# Blog creation function
def create_blog_post(title, content):
    logging.info(f"Creating blog post: {title}")
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    post = blogger_service.posts().insert(blogId=env['BLOGGER_ID'], body=body).execute()
    logging.info(f"Post created with ID: {post['id']}")
    return post['id']

# Full blog workflow
def run_blog_workflow():
    niche = env['NICHE_DEFAULT']
    prompt = f"Write a high-quality, {env['MIN_BLOG_LENGTH']}-word blog post about {niche} including actionable tips."
    blog_content = get_ai_blog_content(prompt)
    video_links = search_youtube_videos(niche)
    # Append videos to blog content
    for url in video_links:
        blog_content += f"<br><br>Watch this video: <a href='{url}'>{url}</a>"
    create_blog_post(f"{niche} Insights - {datetime.now().strftime('%Y-%m-%d')}", blog_content)

# Immediate run for test/manual blog post
run_blog_workflow()

# Schedule for future daily runs
schedule.every().day.at("09:00").do(run_blog_workflow)
while True:
    schedule.run_pending()
    time.sleep(60)

