# youtube_video_selector.py
# Fully automated YouTube video selector with scoring, JSON output for met/near-threshold videos.

import os
import json
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from isodate import parse_duration

# ==========================
# Configuration
# ==========================
API_KEY = os.getenv("YOUTUBE_API_KEY")  # Must be set in environment
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MAX_RESULTS = 10
THRESHOLD = 0.8
NEAR_THRESHOLD = THRESHOLD * 0.9  # 10% below threshold

# ==========================
# Niches and Keywords
# ==========================
niches = {
    "Weight Loss": ["weight loss tips", "fat burning workout", "healthy diet"],
    "Fitness": ["home workout", "HIIT training", "strength training"],
    # Add more niches and keywords as needed
}

# ==========================
# Helper Functions
# ==========================
def get_youtube_client():
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY is not set in environment")
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)

def iso8601_duration_to_minutes(duration_str):
    try:
        return parse_duration(duration_str).total_seconds() / 60
    except Exception:
        return 0

def compute_video_age_weeks(published_at):
    try:
        published_dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        delta = datetime.utcnow() - published_dt
        return delta.days / 7
    except Exception:
        return 0

def video_score(AVD, VL, VA_weeks):
    APV = (AVD / VL) * 100 if VL > 0 else 0
    EngagementScore = max(0, (APV - 60) / 40)
    LengthScore = 0
    if 9 <= VL <= 17:
        LengthScore = 1 - (abs(VL - 12) / 5) * 0.3
    AgeScore = 0
    if 6 <= VA_weeks <= 78:
        AgeScore = 1
    elif VA_weeks > 78:
        AgeScore = 0.5
    FinalScore = (0.5 * EngagementScore) + (0.3 * LengthScore) + (0.2 * AgeScore)
    return FinalScore

# ==========================
# YouTube API Functions
# ==========================
def search_videos(keyword, max_results=MAX_RESULTS):
    youtube = get_youtube_client()
    try:
        request = youtube.search().list(
            q=keyword,
            type="video",
            videoLicense="creativeCommon",
            part="id,snippet",
            maxResults=max_results,
            order="viewCount",
            safeSearch="moderate"
        )
        response = request.execute()
    except HttpError as e:
        print(f"Search error for '{keyword}': {e}")
        return []

    videos = []
    for item in response.get("items", []):
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "published_at": item["snippet"]["publishedAt"]
        })
    return videos

def get_video_details(video_ids):
    youtube = get_youtube_client()
    try:
        request = youtube.videos().list(
            part="contentDetails,statistics,snippet",
            id=",".join(video_ids)
        )
        response = request.execute()
    except HttpError as e:
        print(f"Details error: {e}")
        return {}

    details = {}
    for item in response.get("items", []):
        vid = item["id"]
        try:
            VL = iso8601_duration_to_minutes(item["contentDetails"]["duration"])
            AVD = VL * 0.7  # Proxy for average view duration
            VA_weeks = compute_video_age_weeks(item["snippet"]["publishedAt"])
            details[vid] = {"VL": VL, "AVD": AVD, "VA_weeks": VA_weeks}
        except Exception:
            continue
    return details

# ==========================
# Main Ranking & Selection
# ==========================
def select_top_video(keyword):
    videos = search_videos(keyword)
    if not videos:
        return []
    video_ids = [v["video_id"] for v in videos]
    details = get_video_details(video_ids)
    ranked = []
    for v in videos:
        vid = v["video_id"]
        if vid not in details:
            continue
        VL = details[vid]["VL"]
        AVD = details[vid]["AVD"]
        VA_weeks = details[vid]["VA_weeks"]
        score = video_score(AVD, VL, VA_weeks)
        v.update({"VL": VL, "AVD": AVD, "VA_weeks": VA_weeks, "final_score": score})
        ranked.append(v)
    return ranked

# ==========================
# Run Across All Niches/Keywords
# ==========================
def run_all_keywords():
    all_results = []
    for niche, keywords in niches.items():
        for kw in keywords:
            print(f"Processing keyword: {kw} in niche: {niche}")
            videos = select_top_video(kw)
            for v in videos:
                v["keyword"] = kw
                v["niche"] = niche
                all_results.append(v)

    videos_met_criteria = [v for v in all_results if v["final_score"] >= THRESHOLD]
    videos_close = [v for v in all_results if NEAR_THRESHOLD <= v["final_score"] < THRESHOLD]

    with open("videos_met_criteria.json", "w") as f:
        json.dump(videos_met_criteria, f, indent=2)
    with open("videos_close.json", "w") as f:
        json.dump(videos_close, f, indent=2)

    print(f"Videos meeting criteria: {len(videos_met_criteria)}")
    print(f"Videos close to threshold: {len(videos_close)}")

# ==========================
# Main
# ==========================
if __name__ == "__main__":
    run_all_keywords()
