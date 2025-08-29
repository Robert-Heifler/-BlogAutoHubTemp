import os
print("DEBUG: Starting script execution.")
print("DEBUG: YOUTUBE_API_KEY value:", os.getenv("YOUTUBE_API_KEY"))
print("DEBUG: Running in Render service -- add a unique identifier here!")

import os
import sys

REQUIRED_ENV_VARS = ["YOUTUBE_API_KEY"]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    sys.stderr.write(f"Critical Error: Missing required environment variables: {missing_vars}\n")
    sys.exit(1)

print(f"All required environment variables are set: {REQUIRED_ENV_VARS}")




import json
import subprocess
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# Your YouTube Data API key must be set as environment variable YOUTUBE_API_KEY before running

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
if not YOUTUBE_API_KEY:
    raise Exception("Environment variable YOUTUBE_API_KEY not set. Please set it and rerun.")

# Full list of 33 video IDs as per your batches, no placeholders, no manual edits required
VIDEO_IDS = [
    "GfN_n6j07Fc",
    "5ItORcHZ7RE",
    "bXKQhBK3Z4k",
    "lqf1xtQ2zNo",
    "M-OcJpEfqV0",
    "NuULKH5pJDI",
    "9aHLmLaYQm8",
    "O_DafUjazg0",
    "TB54dZkzZOY",
    "uQOa5g9nPaw",
    "w8UY4uiVpmQ",
    "XhkfrTkqaLA",
    "Xn6K2tONHhk",
    "Xn6K2tONHhk",
    "Xn6K2tONHhk",
    "Xn6K2tONHhk",
    "XqTjSeAavjE",
    "y5w6xIoNDhM",
    "y5w6xIoNDhM",
    "yCmsZUN4r_s",
    "zWaVz9m3S_k",
    "ZX_C58IUss8",
    "_rSW3GikiKs",
    "13z9A5kuKkI",
    "3rP1xV1j44",
    "7XH6F6kL4l8",
    "95hX_OMuIpg",
    "HuAj2MvYS-g",
    "LC3Zu4puC1w",
    "M-OcJpEfqV0",
    "NuULKH5pJDI",
    "9aHLmLaYQm8",
    "bXKQhBK3Z4k"
]

OUTPUT_JSON = "video_transcripts.json"

def create_youtube_service(api_key):
    return build("youtube", "v3", developerKey=api_key)

def check_video_embeddable(youtube, video_id):
    try:
        result = youtube.videos().list(
            part="status",
            id=video_id
        ).execute()
        items = result.get("items", [])
        if not items:
            print(f"Video not found for ID: {video_id}")
            return False
        embeddable = items[0].get("status", {}).get("embeddable", False)
        return embeddable
    except Exception as e:
        print(f"Error checking embeddability for {video_id}: {e}")
        return False

def fetch_video_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript_list])
    except Exception as e:
        print(f"Transcript not available for {video_id}: {e}")
        return "Transcript not available"

def git_commit_and_push(filename):
    try:
        subprocess.run(["git", "add", filename], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-update transcripts JSON {filename}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully pushed to GitHub.")
    except subprocess.CalledProcessError as exc:
        print(f"Git operation failed: {exc}")

def main():
    youtube = create_youtube_service(YOUTUBE_API_KEY)
    data = []

    for vid in VIDEO_IDS:
        print(f"Processing video ID: {vid}")
        if check_video_embeddable(youtube, vid):
            transcript = fetch_video_transcript(vid)
        else:
            transcript = "Video not embeddable or accessible."
        data.append({
            "video_id": vid,
            "transcript": transcript
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    print(f"Saved transcript data to {OUTPUT_JSON}")
    git_commit_and_push(OUTPUT_JSON)

if __name__ == "__main__":
    main()
