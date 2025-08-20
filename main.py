# --- main.py (fixed) ---
import os
import sys
import time
import html
import random
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import requests
from flask import Flask, jsonify
from tzlocal import get_localzone
from apscheduler.schedulers.background import BackgroundScheduler
from langdetect import detect, DetectorFactory
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ----------------- Logging Setup -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

DetectorFactory.seed = 0

# ----------------- Flask app -----------------
app = Flask(__name__)

@app.route("/")
def health():
    return "BlogWorker alive ✅"

@app.route("/last")
def last_status():
    return jsonify(LAST_STATUS)

# ---------- /run-now test route ----------
@app.route("/run-now")
def run_now():
    threading.Thread(target=lambda: generate_and_post(get_env("NICHE_DEFAULT")), daemon=True).start()
    return "Triggered a test blog post! Check youtubeblog shortly."

# ----------------- Constants -----------------
REQUIRED_ENV_VARS = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
    "OPENROUTER_API_KEY",
    "YOUTUBE_API_KEY",
    "NICHE_DEFAULT",
    "MIN_BLOG_LENGTH",
]

BLOG_ID = "5732679007467998989"
BLOG_URL = "https://youtubeblog.blogspot.com/"

# ClickBank offers dictionary
CLICKBANK_OFFERS: Dict[str, Dict[str, Any]] = {
    "weight_loss": {
        "keywords": ["weight loss tips", "fat loss", "metabolism", "calorie deficit",
                     "lose weight fast", "healthy weight loss", "belly fat"],
        "offers": [
            {"name": "Ikaria Lean Belly Juice", "url": "https://hop.clickbank.net/?affiliate=YOURID&vendor=ikaria"},
            {"name": "Java Burn", "url": "https://hop.clickbank.net/?affiliate=YOURID&vendor=javaburn"}
        ],
        "soft_ctas": [
            "Curious how others are accelerating fat loss without extreme diets?",
            "Want a gentle nudge to keep today’s momentum going?",
            "Prefer a simple add-on to your current routine rather than a total overhaul?"
        ]
    },
}

AI_PROMPT_TEMPLATE = """You are an expert health content editor. Transform the following YouTube transcript into a clear, well-structured, ORIGINAL blog post for readers.
...
"""  # keep your existing AI prompt

# ----------------- Globals -----------------
LAST_STATUS = {
    "last_run": None,
    "last_result": None,
    "last_error": None,
    "last_video_id": None,
    "last_post_id": None,
}

# ----------------- Utilities -----------------
def get_env(name: str, default: Optional[str] = None) -> str:
    return os.environ.get(name, default) or ""

def validate_env() -> None:
    logging.info("Checking env visibility…")
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

def normalize_niche_key(niche_key: str) -> str:
    """Convert any incoming niche key to lowercase and replace spaces with underscores"""
    return niche_key.lower().replace('"', '').replace("'", "").replace(" ", "_")

def blogger_service():
    creds = Credentials(
        token=None,
        refresh_token=get_env("GOOGLE_REFRESH_TOKEN"),
        client_id=get_env("GOOGLE_CLIENT_ID"),
        client_secret=get_env("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build("blogger", "v3", credentials=creds, cache_discovery=False)

def youtube_service():
    return build("youtube", "v3", developerKey=get_env("YOUTUBE_API_KEY"), cache_discovery=False)

def openrouter_chat(model: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=get_env("OPENROUTER_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return resp.choices[0].message.content

def self_ping_loop(port: int):
    url = f"http://0.0.0.0:{port}/"
    while True:
        try:
            requests.get(url, timeout=5)
        except Exception:
            pass
        time.sleep(600)

# ----------------- YouTube & Transcript -----------------
def search_yt_videos(niche_key: str, max_results: int = 15) -> List[Dict[str, Any]]:
    yt = youtube_service()
    keywords = CLICKBANK_OFFERS[niche_key]["keywords"]
    query = random.choice(keywords)
    req = yt.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results,
        order="relevance",
        safeSearch="moderate",
        videoDuration="medium",
        publishedAfter=(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()
    )
    res = req.execute()
    return res.get("items", [])

def fetch_video_details(video_id: str) -> Dict[str, Any]:
    yt = youtube_service()
    res = yt.videos().list(part="snippet,contentDetails,statistics", id=video_id).execute()
    if not res.get("items"):
        raise ValueError("No video details found")
    return res["items"][0]

def try_get_transcript_en(video_id: str) -> Optional[str]:
    try:
        tracks = YouTubeTranscriptApi.list_transcripts(video_id)
        for lang_code in ["en", "en-US", "en-GB"]:
            if tracks.find_transcript([lang_code]):
                s = tracks.find_transcript([lang_code]).fetch()
                return " ".join([t["text"] for t in s if t.get("text")])
        for tr in tracks:
            if tr.language_code.startswith("en"):
                s = tr.fetch()
                return " ".join([t["text"] for t in s if t.get("text")])
        return None
    except Exception:
        return None

def is_english(text: str) -> bool:
    try:
        return detect(text) == "en"
    except Exception:
        return False

# ----------------- Content Generation -----------------
def build_prompt(niche_key: str, transcript: str, video_meta: Dict[str, Any]) -> str:
    niche = CLICKBANK_OFFERS[niche_key]
    offers_html = "\n".join([f"- {o['name']}: {o['url']}" for o in niche["offers"]])
    soft_ctas_txt = "\n".join([f"- {c}" for c in niche["soft_ctas"]])
    snippet = video_meta["snippet"]
    video_title = snippet["title"]
    channel_title = snippet["channelTitle"]
    published_at = snippet["publishedAt"][:10]
    return AI_PROMPT_TEMPLATE.format(
        niche_name=niche_key.replace("_", " ").title(),
        video_title=video_title,
        channel_title=channel_title,
        video_published_date=published_at,
        soft_ctas=soft_ctas_txt,
        offers=offers_html,
        transcript=transcript
    )

def generate_post_html(niche_key: str, transcript: str, video_meta: Dict[str, Any]) -> str:
    model = "anthropic/claude-3.5-sonnet"
    prompt = build_prompt(niche_key, transcript, video_meta)
    return openrouter_chat(model, prompt)

def build_post_title(niche_key: str, video_meta: Dict[str, Any]) -> str:
    return f"{video_meta['snippet']['title']} — Key Insights & Takeaways ({niche_key.replace('_',' ').title()})"

def yt_embed_html(video_id: str) -> str:
    return f"""
<div style="margin: 16px 0;">
  <iframe width="560" height="315"
    src="https://www.youtube.com/embed/{html.escape(video_id)}"
    title="YouTube video player" frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowfullscreen></iframe>
</div>
"""

def qualify_transcript(t: str, min_words: int) -> bool:
    if not t or not is_english(t):
        return False
    return len(t.split()) >= max(200, min_words // 2)

# ----------------- Blogger Posting -----------------
def post_to_blogger(title: str, html_content: str) -> str:
    service = blogger_service()
    body = {"kind": "blogger#post", "title": title, "content": html_content}
    res = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=False).execute()
    return res.get("id", "")

# ----------------- Orchestrator -----------------
def find_qualified_video(niche_key: str, max_pages: int = 3) -> Dict[str, Any]:
    niche_key = normalize_niche_key(niche_key)
    min_blog_len = int(get_env("MIN_BLOG_LENGTH", "800"))
    for _ in range(max_pages):
        candidates = search_yt_videos(niche_key)
        for item in candidates:
            vid = item["id"]["videoId"]
            details = fetch_video_details(vid)
            transcript = try_get_transcript_en(vid)
            if not qualify_transcript(transcript, min_blog_len):
                continue
            return {"video_id": vid, "meta": details, "transcript": transcript}
        time.sleep(2)
    raise RuntimeError("No qualified videos found")

def generate_and_post(niche_key: Optional[str] = None) -> None:
    LAST_STATUS.update({"last_run": datetime.now().isoformat(), "last_result": None, "last_error": None})
    try:
        niche = normalize_niche_key(niche_key or get_env("NICHE_DEFAULT"))
        v = find_qualified_video(niche)
        vid, meta, transcript = v["video_id"], v["meta"], v["transcript"]
        html_body = generate_post_html(niche, transcript, meta)
        title = build_post_title(niche, meta)
        embed = yt_embed_html(vid)
        snippet = meta["snippet"]
        header_info = f"<p><em>Source video:</em> <strong>{html.escape(snippet['title'])}</strong> by {html.escape(snippet['channelTitle'])} — Published on <strong>{html.escape(snippet['publishedAt'][:10])}</strong></p>"
        final_html = f"{header_info}{embed}{html_body}"
        post_id = post_to_blogger(title, final_html)
        LAST_STATUS.update({"last_result": "posted", "last_video_id": vid, "last_post_id": post_id})
        logging.info("✅ Posted to Blogger. Post ID: %s (video %s)", post_id, vid)
    except Exception as e:
        LAST_STATUS.update({"last_result": "error", "last_error": str(e)})
        logging.error("❌ generate_and_post failed: %s", e, exc_info=True)

# ----------------- Scheduling -----------------
def schedule_jobs(sched: BackgroundScheduler):
    tz = get_localzone()
    for dow in ["tue", "wed", "thu"]:
        sched.add_job(lambda: generate_and_post(get_env("NICHE_DEFAULT")), "cron", day_of_week=dow, hour=10, minute=5, timezone=tz, id=f"{dow}-am")
        sched.add_job(lambda: generate_and_post(get_env("NICHE_DEFAULT")), "cron", day_of_week=dow, hour=14, minute=35, timezone=tz, id=f"{dow}-pm")
    logging.info("Scheduler initialized for Tue/Wed/Thu at 10:05 and 14:35.")

# ----------------- Boot & Run -----------------
def boot_sequence(port: int):
    validate_env()
    scheduler = BackgroundScheduler()
    schedule_jobs(scheduler)
    scheduler.start()
    logging.info("Starting Flask app on port %s", port)
    threading.Thread(target=self_ping_loop, args=(port,), daemon=True).start()
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    boot_sequence(PORT)
