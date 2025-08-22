import json
import os
from googleapiclient.discovery import build

# Load configuration
CONFIG_FILE = "config.json"
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

YOUTUBE_API_KEY = config["google_api_key"]
NICHES_FILE = "niches_keywords.json"  # Your provided JSON file
OUTPUT_FILE = "youtube_videos_scored.json"

# Load niches and keywords
with open(NICHES_FILE, "r") as f:
    niches = json.load(f)

# YouTube API client
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Video scoring function
def video_score(AVD, VL, VA_weeks):
    APV = (AVD / VL) * 100
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

# Helper: get video stats
def get_video_data(video_id):
    try:
        res = youtube.videos().list(
            part="contentDetails,statistics,snippet",
            id=video_id
        ).execute()
        item = res["items"][0]
        vl = parse_duration(item["contentDetails"]["duration"])
        va_weeks = (os.popen("date +%s").read())  # placeholder: use publishedAt
        avd = float(item["statistics"].get("averageViewDuration", 0)) / 60.0  # min
        return vl, avd, va_weeks
    except Exception:
        return None, None, None

# Duration parser (ISO 8601)
import isodate
def parse_duration(duration):
    try:
        return isodate.parse_duration(duration).total_seconds() / 60.0
    except Exception:
        return 0

# Search videos per niche & keyword
result_data = {}
for niche, keywords in niches.items():
    niche_videos = []
    for keyword in keywords:
        search_res = youtube.search().list(
            q=keyword,
            type="video",
            videoLicense="creativeCommon",
            part="id",
            maxResults=5
        ).execute()
        for item in search_res.get("items", []):
            vid = item["id"]["videoId"]
            vl, avd, va_weeks = get_video_data(vid)
            if vl and avd and va_weeks:
                score = video_score(avd, vl, va_weeks)
                if score >= 0.8:
                    niche_videos.append({"video_id": vid, "score": round(score, 3)})
    # Sort by score descending
    result_data[niche] = sorted(niche_videos, key=lambda x: x["score"], reverse=True)

# Save JSON
with open(OUTPUT_FILE, "w") as f:
    json.dump(result_data, f, indent=4)

print(f"JSON file '{OUTPUT_FILE}' created successfully.")
