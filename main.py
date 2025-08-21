import os
import json
import random
import logging
from datetime import datetime
from flask import Flask, request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler

# -----------------------------
# CONFIGURATION
# -----------------------------
SCOPES = ['https://www.googleapis.com/auth/blogger']
BLOG_ID = os.getenv('BLOG_ID')  # Ensure this is set in environment
KEYWORDS_FILE = 'keywords.jason'  # Your keywords file
SCHEDULE_TIMES = [("Tue", "10:05"), ("Wed", "10:05"), ("Thu", "10:05")]

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

# -----------------------------
# LOAD KEYWORDS
# -----------------------------
def load_keywords():
    if not os.path.exists(KEYWORDS_FILE):
        logging.error(f"Keywords file not found: {KEYWORDS_FILE}")
        return {}
    with open(KEYWORDS_FILE, 'r') as f:
        return json.load(f)

keywords_data = load_keywords()

# -----------------------------
# GOOGLE API AUTH
# -----------------------------
def get_blogger_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('blogger', 'v3', credentials=creds)
    return service

service = get_blogger_service()

# -----------------------------
# LOG ALL BLOGS
# -----------------------------
def log_all_blogs():
    try:
        blogs = service.blogs().listByUser(userId='self').execute()
        logging.info("Blogs available to this account:")
        for b in blogs.get('items', []):
            logging.info(f" - ID: {b['id']} | Name: {b['name']} | URL: {b['url']}")
    except Exception as e:
        logging.error(f"Error fetching blogs list: {e}")

log_all_blogs()

# -----------------------------
# POST CREATION
# -----------------------------
def create_blog_post(niche):
    if niche not in keywords_data or not keywords_data[niche]:
        logging.error(f"No keywords found for niche '{niche}'")
        return
    keyword = random.choice(keywords_data[niche])
    logging.info(f"Using keyword '{keyword}' for niche '{niche}'")

    post_title = f"{keyword.title()} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    post_content = f"<p>Automated post content for keyword: {keyword}</p>"

    post = {
        'kind': 'blogger#post',
        'title': post_title,
        'content': post_content
    }

    try:
        # Log blog info before posting
        blog_info = service.blogs().get(blogId=BLOG_ID).execute()
        logging.info(f"Attempting to post to blog:")
        logging.info(f" - Blog ID: {BLOG_ID}")
        logging.info(f" - Blog title: {blog_info.get('name')}")
        logging.info(f" - Blog URL: {blog_info.get('url')}")

        # Insert post
        result = service.posts().insert(blogId=BLOG_ID, body=post).execute()
        logging.info(f"Post published successfully! URL: {result.get('url')}")

    except Exception as e:
        logging.error(f"Error posting to Blogger: {e}")

# -----------------------------
# SCHEDULER
# -----------------------------
def schedule_jobs():
    for day, time_str in SCHEDULE_TIMES:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(lambda: create_blog_post("Weight Loss"), 'cron', day_of_week=day.lower()[:3], hour=hour, minute=minute)
    logging.info(f"Scheduler started for {SCHEDULE_TIMES}")

schedule_jobs()

# -----------------------------
# FLASK ENDPOINTS
# -----------------------------
@app.route('/')
def home():
    return "Blog Worker is running"

@app.route('/run-now')
def run_now():
    niche = request.args.get('niche', 'Weight Loss')
    create_blog_post(niche)
    return f"Triggered post creation for niche: {niche}"

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == '__main__':
    logging.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
