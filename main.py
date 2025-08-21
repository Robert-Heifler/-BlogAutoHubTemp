import os
import json
import logging
import random
from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# ------------------- CONFIG -------------------
SCOPES = ['https://www.googleapis.com/auth/blogger']
KEYWORDS_FILE = 'keywords.json'  # Your JSON with niche-keywords
TOKEN_FILE = 'token.json'
BLOG_ID = os.environ.get('BLOG_ID')  # Optional: default blog ID
# --------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

# ------------------- LOAD KEYWORDS -------------------
def load_keywords():
    if not os.path.exists(KEYWORDS_FILE):
        logger.error(f"Keywords file '{KEYWORDS_FILE}' not found.")
        return {}
    with open(KEYWORDS_FILE, 'r') as f:
        return json.load(f)

keywords_data = load_keywords()

# ------------------- GOOGLE SERVICE -------------------
def get_blogger_service():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.error("Google client ID or secret missing in environment variables.")
        raise Exception("Missing Google OAuth credentials.")

    flow_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config(flow_config, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token_file:
            token_file.write(creds.to_json())

    service = build('blogger', 'v3', credentials=creds)
    return service

# ------------------- BLOG POST FUNCTION -------------------
def create_blog_post(niche):
    if niche not in keywords_data or not keywords_data[niche]:
        logger.error(f"No keywords found for niche '{niche}'")
        return None

    keyword = random.choice(keywords_data[niche])
    logger.info(f"Using keyword '{keyword}' for niche '{niche}'")

    service = get_blogger_service()

    blog_id = BLOG_ID or request.args.get('blog_id')
    if not blog_id:
        # Fetch user's blogs and pick first one
        blogs_list = service.blogs().listByUser(userId='self').execute()
        if not blogs_list.get('items'):
            logger.error("No blogs found for this user.")
            return None
        blog_id = blogs_list['items'][0]['id']
        logger.info(f"No blog ID specified. Using first blog: {blog_id}")

    post_title = f"{keyword.capitalize()} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    post_content = f"<h1>{post_title}</h1><p>This is an automated post about {keyword}.</p>"

    try:
        post = service.posts().insert(blogId=blog_id, body={
            "kind": "blogger#post",
            "title": post_title,
            "content": post_content
        }).execute()
        logger.info(f"Post created successfully!")
        logger.info(f"Blog ID: {blog_id}")
        logger.info(f"Post Title: {post.get('title')}")
        logger.info(f"Post URL: {post.get('url')}")
        return post
    except Exception as e:
        logger.exception("Failed to create blog post.")
        return None

# ------------------- SCHEDULE JOBS -------------------
def schedule_jobs():
    for niche in keywords_data.keys():
        scheduler.add_job(lambda n=niche: create_blog_post(n), 'interval', minutes=60)
    logger.info("Scheduled jobs for all niches.")

# ------------------- FLASK ROUTES -------------------
@app.route('/')
def index():
    return "Blog Worker is running."

@app.route('/run-now')
def run_now():
    niche = request.args.get('niche')
    if not niche:
        return jsonify({"error": "Please specify a niche"}), 400
    post = create_blog_post(niche)
    if post:
        return jsonify({"status": "success", "post_url": post.get('url')})
    return jsonify({"status": "failed"}), 500

# ------------------- MAIN -------------------
if __name__ == "__main__":
    schedule_jobs()
    logger.info("Scheduler started")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
