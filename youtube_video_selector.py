# youtube_video_selector.py
# Fetches, scores, and ranks Creative Commons YouTube videos with pagination and robust handling.

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from datetime import datetime, timezone
import re
from typing import List, Dict, Optional

# ==========================
# Configuration
# ==========================
API_KEY = os.getenv("YOUTUBE_API_KEY")
MAX_RESULTS = 10

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY environment variable is not set.")

# ==========================
# YouTube Client
# ==========================
def get_youtube_client():
    return build("youtube", "v3", developerKey=API_KEY)

# ==========================
# Helper Functions
# ==========================
def iso8601_duration_to_minutes(duration: str) -> Optional[float]:
    """Convert ISO 8601 duration (PT#H#M#S) to minutes."""
    try:
        hours = minutes = seconds = 0
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            h, m, s = match.groups()
            hours = int(h) if h else 0
            minutes = int(m) if m else 0
            seconds = int(s) if s else 0
        return hours * 60 + minutes + seconds / 60
    except Exception as e:
        print(f"Failed to parse duration '{duration}': {e}")
        return None

def compute_video_age_weeks(published_at: str) -> float:
    try:
        published_dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        delta_days = (datetime.now(timezone.utc) - published_dt.replace(tzinfo=timezone.utc)).days
        return delta_days / 7
    except Exception:
        return 52.0  # fallback 1 year

def video_score(AVD: float, VL: float, VA_weeks: float) -> float:
    """
    Bob Heifler formula.
    Note: AVD is currently a proxy (70% of VL), so EngagementScore may be biased upward.
    """
    APV = (AVD / VL) * 100
    EngagementScore = max(0, (APV - 60) / 40)
    LengthScore = 0 if VL < 9 or VL > 17 else max(0, 1 - (abs(VL - 12) / 5) * 0.3)
    AgeScore = 0 if VA_weeks < 6 else 1 if VA_weeks <= 78 else 0.5
    return (0.5 * EngagementScore) + (0.3 * LengthScore) + (0.2 * AgeScore)

# ==========================
# Video Retrieval
# ==========================
def search_videos(keyword: str, max_results: int = MAX_RESULTS) -> List[Dict]:
    youtube = get_youtube_client()
    videos = []
    next_page_token = None

    while len(videos) < max_results:
        try:
            request = youtube.search().list(
                q=keyword,
                type="video",
                videoLicense="creativeCommon",
                part="id,snippet",
                maxResults=min(50, max_results - len(videos)),  # API max per page is 50
                order="viewCount",
                safeSearch="moderate",
                pageToken=next_page_token
            )
            response = request.execute()
        except HttpError as e:
            print(f"Search error: {e}")
            break

        items = response.get("items", [])
        if not items:
            break

        for item in items:
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "published_at": item["snippet"]["publishedAt"]
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    if len(videos) < max_results:
        print(f"Warning: Only {len(videos)} videos found for keyword '{keyword}'.")

    return videos

def get_video_details(video_ids: List[str]) -> Dict[str, Dict]:
    youtube = get_youtube_client()
    details = {}
    try:
        request = youtube.videos().list(
            part="contentDetails,statistics,snippet",
            id=",".join(video_ids)
        )
        response = request.execute()
    except HttpError as e:
        print(f"Details error: {e}")
        return details

    for item in response.get("items", []):
        vid = item["id"]
        VL = iso8601_duration_to_minutes(item["contentDetails"]["duration"])
        if VL is None:
            continue  # skip invalid durations

        # Proxy for AVD; replace with Analytics API for real data
        AVD = VL * 0.7

        VA_weeks = compute_video_age_weeks(item["snippet"]["publishedAt"])

        # Store statistics for optional future dynamic scoring
        stats = item.get("statistics", {})
        view_count = int(stats.get("viewCount", 0))
        like_count = int(stats.get("likeCount", 0))

        details[vid] = {
            "VL": VL,
            "AVD": AVD,
            "VA_weeks": VA_weeks,
            "view_count": view_count,
            "like_count": like_count
        }
    return details

# ==========================
# Ranking & Filtering
# ==========================
def rank_videos(videos: List[Dict]) -> List[Dict]:
    if not videos:
        return []

    video_ids = [v["video_id"] for v in videos]
    details = get_video_details(video_ids)

    filtered = []
    for v in videos:
        vid = v["video_id"]
        if vid not in details:
            continue
        d = details[vid]
        score = video_score(d["AVD"], d["VL"], d["VA_weeks"])
        if score >= 0.8 and 6 <= d["VA_weeks"] <= 78 and 9 <= d["VL"] <= 17:
            v.update({
                "VL": d["VL"],
                "AVD": d["AVD"],
                "VA_weeks": d["VA_weeks"],
                "view_count": d["view_count"],
                "like_count": d["like_count"],
                "final_score": score
            })
            filtered.append(v)

    return sorted(filtered, key=lambda x: x["final_score"], reverse=True)

# ==========================
# Top Video Selector
# ==========================
def select_top_video(keyword: str) -> Optional[Dict]:
    videos = search_videos(keyword)
    ranked = rank_videos(videos)
    return ranked[0] if ranked else None

# ==========================
# Example Usage
# ==========================
if __name__ == "__main__":
    keyword = "weight loss"
    top_video = select_top_video(keyword)
    if top_video:
        print("Top Video:")
        for k, v in top_video.items():
            print(f"{k}: {v}")
    else:
        print("No video met the 0.8+ FinalScore criteria.")
