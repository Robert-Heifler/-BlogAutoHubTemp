import os
import re
import time
import logging
import requests
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, VideoUnavailable
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# -----------------------
# Logging configuration
# -----------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# -----------------------
# Environment variables
# -----------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BLOGGER_BLOG_ID = os.getenv("BLOGGER_BLOG_ID")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
PORT = int(os.getenv("PORT", 5000))

required_env_vars = [
    OPENROUTER_API_KEY, BLOGGER_BLOG_ID, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
]
if any(var is None for var in required_env_vars):
    raise EnvironmentError("Missing required environment variables. Please check Render config.")

# -----------------------
# Constants
# -----------------------
CHUNK_SIZE = 2000  # characters per chunk for OpenRouter
MAX_RETRIES = 3
BACKOFF_FACTOR = 2

# -----------------------
# Helper Functions
# -----------------------
def fetch_transcript(video_id):
    """Fetch YouTube transcript, return None if unavailable."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'].strip() for entry in transcript])
        return transcript_text
    except (TranscriptsDisabled, VideoUnavailable):
        logging.error(f"Transcript unavailable for video {video_id}.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching transcript for {video_id}: {e}")
        return None

def chunk_text(text, max_chars=CHUNK_SIZE):
    """Split text into chunks at sentence boundaries."""
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += " " + sentence if current_chunk else sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def call_openrouter_api(prompt):
    """Call OpenRouter API with retries and timeout."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "anthropic/claude-3-sonnet",
        "messages": [{"role": "user", "content": prompt}]
    }
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
            response.raise_for_status()
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                return content
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                sleep_time = BACKOFF_FACTOR ** attempt
                logging.warning(f"Rate limited by OpenRouter. Backing off {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            logging.error(f"OpenRouter HTTPError: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"OpenRouter RequestException: {e}")
            time.sleep(BACKOFF_FACTOR ** attempt)
    logging.error("Failed to get response from OpenRouter after retries.")
    return None

def get_blogger_service():
    """Authenticate and return Blogger API service."""
    creds = Credentials.from_authorized_user_info(info={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN
    })
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("blogger", "v3", credentials=creds)

def publish_post(title, content):
    """Publish content to Blogger."""
    try:
        service = get_blogger_service()
        post_body = {
            "kind": "blogger#post",
            "blog": {"id": BLOGGER_BLOG_ID},
            "title": title,
            "content": content
        }
        published_post = service.posts().insert(blogId=BLOGGER_BLOG_ID, body=post_body).execute()
        logging.info(f"Post published: {published_post.get('url')}")
        return published_post.get("url")
    except HttpError as e:
        logging.error(f"Blogger API error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error publishing post: {e}")
        return None

def get_youtube_video_title(video_id):
    """Optional: fetch video title using YouTube Data API."""
    # Placeholder: You can add YouTube API integration here
    return "Generated Blog Post"

def generate_blog_html(video_id, content, title):
    """Generate HTML content with video above the fold."""
    embed_code = f"""
    <div style='text-align:center; margin-bottom:20px;'>
        <iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}?rel=0" frameborder="0" allowfullscreen></iframe>
    </div>
    """
    html_content = f"<h2>{title}</h2>{embed_code}<div>{content}</div>"
    return html_content

# -----------------------
# API Endpoints
# -----------------------
@app.route("/generate", methods=["POST"])
def generate_blog():
    """Generate and publish a blog post from YouTube video transcript."""
    data = request.json
    video_id = data.get("video_id")
    if not video_id or not re.match(r"^[\w-]{11}$", video_id):
        return jsonify({"error": "Invalid or missing video_id"}), 400

    transcript = fetch_transcript(video_id)
    if not transcript:
        return jsonify({"error": "Transcript not available"}), 500

    chunks = chunk_text(transcript)
    blog_content = ""
    for chunk in chunks:
        prompt = f"Rewrite the following transcript into a detailed blog article. Make it long-form, SEO-driven, and engaging with headings, subheadings, and natural CTAs. Minimum length: 1200 words.\n\nTranscript:\n\n{chunk}"
        chunk_content = call_openrouter_api(prompt)
        if not chunk_content:
            return jsonify({"error": "OpenRouter API failed for one of the chunks"}), 500
        blog_content += chunk_content

    title = get_youtube_video_title(video_id)
    html_content = generate_blog_html(video_id, blog_content, title)
    post_url = publish_post(title, html_content)
    if post_url:
        return jsonify({"url": post_url}), 200
    return jsonify({"error": "Failed to publish post"}), 500

@app.route("/diagnostics", methods=["GET"])
def diagnostics():
    """Localhost-only diagnostics."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({
        "env_vars_set": all(required_env_vars),
        "status": "OK"
    }), 200

# -----------------------
# Run Server
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
