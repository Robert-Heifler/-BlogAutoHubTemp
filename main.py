import os
import json
import logging
from dotenv import load_dotenv
import google_auth  # fixed import here
import requests
from flask import Flask
import threading  # run automation in background

# Load environment and set up logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
BLOGGER_POST_URL = "https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/"

# Set up Flask app for health check
app = Flask(__name__)


@app.route('/health')
def health():
    return 'OK', 200

def load_blog_config():
    config_json = os.getenv("BLOG_CONFIG_JSON")
    if not config_json:
        logging.error("BLOG_CONFIG_JSON env variable missing.")
        return None
    try:
        return json.loads(config_json)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON: {e}")
        return None

def search_youtube_videos(keywords, max_results=3):
    headers = google_auth.get_auth_header()
    query = " ".join(keywords)
    params = {
        "part": "snippet",
        "maxResults": max_results,
        "q": query,
        "type": "video",
        "order": "relevance"
    }
    response = requests.get(YOUTUBE_SEARCH_URL, headers=headers, params=params)
    if response.ok:
        return response.json().get("items", [])
    else:
        logging.error(f"YouTube search failed: {response.text}")
        return []

def create_blog_post_title(template, video_title):
    return template.replace("{video}", video_title)

def create_blog_post_content(video_snippet, cta_html):
    return f"<p>{video_snippet}</p>\n{cta_html}"

def post_to_blogger(blog_id, title, content):
    headers = google_auth.get_auth_header()
    headers["Content-Type"] = "application/json"
    body = {
        "kind": "blogger#post",
        "blog": {"id": blog_id},
        "title": title,
        "content": content
    }
    url = BLOGGER_POST_URL.format(blog_id=blog_id)
    response = requests.post(url, headers=headers, json=body)
    if response.ok:
        return response.json()
    else:
        logging.error(f"Failed to post to Blogger: {response.text}")
        return None

def automation_main():
    logging.info("🔁 Starting automation run")
    blog_config = load_blog_config()
    if blog_config is None:
        logging.error("❌ Blog config load failed.")
        return

    for blog_id, details in blog_config.items():
        blog_name = details.get("blog_name", "Unknown Blog")
        keywords = details.get("keywords", [])
        title_template = details.get("title_template", "{video}")
        cta_html = details.get("cta_html", "")

        logging.info(f"🔍 Searching YouTube for blog '{blog_name}' using: {keywords}")
        videos = search_youtube_videos(keywords)
        if not videos:
            logging.warning(f"⚠️ No videos found for '{blog_name}'. Skipping.")
            continue

        for video in videos:
            snippet = video.get("snippet", {})
            video_title = snippet.get("title", "No Title")
            video_description = snippet.get("description", "")

            post_title = create_blog_post_title(title_template, video_title)
            post_content = create_blog_post_content(video_description, cta_html)

            result = post_to_blogger(blog_id, post_title, post_content)
            if result:
                logging.info(f"✅ Posted to '{blog_name}': {post_title}")
            else:
                logging.error(f"❌ Failed to post video '{video_title}'.")

    logging.info("🏁 Automation run completed.")


@app.route('/env-check')
def env_check():
    def mask(val):
        if not val:
            return "MISSING"
        return f"{val[:4]}...{val[-4:]} (len={len(val)})"

    return {
        "GOOGLE_CLIENT_ID": mask(os.getenv("GOOGLE_CLIENT_ID")),
        "GOOGLE_CLIENT_SECRET": mask(os.getenv("GOOGLE_CLIENT_SECRET")),
        "GOOGLE_REFRESH_TOKEN": mask(os.getenv("GOOGLE_REFRESH_TOKEN")),
        "BLOG_CONFIG_JSON": "SET" if os.getenv("BLOG_CONFIG_JSON") else "MISSING"
    }



if __name__ == "__main__":
    threading.Thread(target=automation_main).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
