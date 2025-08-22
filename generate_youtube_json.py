import json
from datetime import datetime
from googleapiclient.discovery import build
import isodate

# Config
CONFIG_FILE = "config.json"
NICHES_FILE = "niches_keywords.json"
OUTPUT_FILE = "youtube_videos_scored.json"

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

YOUTUBE_API_KEY = config["google_api_key"]

with open(NICHES_FILE, "r") as f:
    niches = json.load(f)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# FinalScore calculation
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

# Parse ISO 8601 duration
def parse_duration(duration):
    return isodate.parse_duration(duration).total_seconds() / 60.0

# Calculate age in weeks
def age_in_weeks(published_at):
    dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
    delta = datetime.utcnow() - dt
    return delta.days / 7

# Get video statistics
def get_video_data(video_id):
    res = youtube.videos().list(
        part="contentDetails,statistics,snippet",
        id=video_id
    ).execute()
    if not res["items"]:
        return None
    item = res["items"][0]
    vl = parse_duration(item["contentDetails"]["duration"])
    published_at = item["snippet"]["publishedAt"]
    VA_weeks = age_in_weeks(published_at)
    # Estimate average view duration if available; fallback to half of VL
    try:
        AVD = float(item["statistics"].get("averageViewDuration", 0)) / 60.0
        if AVD == 0:
            AVD = vl / 2
    except:
        AVD = vl / 2
    return vl, AVD, VA_weeks

result_data = {}

for niche, keywords in niches.items():
    niche_videos = []
    for keyword in keywords:
        search_res = youtube.search().list(
            q=keyword,
            type="video",
            videoLicense="creativeCommon",
            part="id",
            maxResults=5,
            order="relevance",
            videoDuration="medium"  # 4-20 min
        ).execute()
        for item in search_res.get("items", []):
            vid = item["id"]["videoId"]
            vl, avd, va_weeks = get_video_data(vid)
            if vl and avd and va_weeks:
                score = video_score(avd, vl, va_weeks)
                if score >= 0.8:
                    niche_videos.append({"video_id": vid, "score": round(score, 3)})
    result_data[niche] = sorted(niche_videos, key=lambda x: x["score"], reverse=True)

with open(OUTPUT_FILE, "w") as f:
    json.dump(result_data, f, indent=4)

print(f"Completed: {OUTPUT_FILE}")

