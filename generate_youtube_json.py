import os
import json
from datetime import datetime, timezone
from googleapiclient.discovery import build
import isodate

KEYWORDS_FILE = "keywords.json"
OUTPUT_FILE = "youtube_videos_scored.json"

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise RuntimeError("Missing YOUTUBE_API_KEY in environment variables")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def parse_duration(duration):
    try:
        return isodate.parse_duration(duration).total_seconds() / 60.0
    except Exception:
        return None

def age_in_weeks(published_at):
    try:
        dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.days / 7
    except Exception:
        return None

def is_video_eligible(AVD, VL, VA_weeks):
    APV = (AVD / VL) * 100 if VL else 0
    return (
        VA_weeks is not None and 6 <= VA_weeks <= 78 and
        VL is not None and 9 <= VL <= 17 and
        APV >= 60
    )

def video_score(AVD, VL, VA_weeks):
    APV = (AVD / VL) * 100 if VL else 0
    EngagementScore = max(0, (APV - 60) / 40)
    if VL is None or VL < 9 or VL > 17:
        LengthScore = 0
    else:
        LengthScore = 1 - (abs(VL - 12) / 5) * 0.3

    if VA_weeks is None or VA_weeks < 6:
        AgeScore = 0
    elif VA_weeks <= 78:
        AgeScore = 1
    else:
        AgeScore = 0.5

    FinalScore = (0.5 * EngagementScore) + (0.3 * LengthScore) + (0.2 * AgeScore)
    return FinalScore

def get_video_data(video_id):
    try:
        res = youtube.videos().list(
            part="contentDetails,statistics,snippet,status",
            id=video_id
        ).execute()
    except Exception as e:
        print(f"API error for video {video_id}: {e}")
        return None

    if not res.get("items"):
        return None

    item = res["items"][0]
    status = item.get("status", {})
    if not status.get("embeddable", False):
        return None

    vl = parse_duration(item["contentDetails"]["duration"])
    published_at = item["snippet"].get("publishedAt")
    VA_weeks = age_in_weeks(published_at)

    # Average view duration fallback proxy
    AVD = vl / 2 if vl else None

    if not is_video_eligible(AVD, vl, VA_weeks):
        return None

    score = video_score(AVD, vl, VA_weeks)
    views = int(item["statistics"].get("viewCount", 0))

    return {
        "video_id": video_id,
        "title": item["snippet"].get("title"),
        "channel": item["snippet"].get("channelTitle"),
        "published_at": published_at,
        "duration_minutes": round(vl, 2) if vl else None,
        "views": views,
        "score": round(score, 3),
        "used_in_blog": False
    }

def load_results():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                print(f"WARNING: Could not parse {OUTPUT_FILE}, starting fresh.")
                return {}
    else:
        return {}

def save_results(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

def fetch_and_score_youtube_videos():
    if not os.path.exists(KEYWORDS_FILE):
        raise RuntimeError(f"Missing keywords JSON file {KEYWORDS_FILE}.")

    with open(KEYWORDS_FILE, "r") as f:
        config = json.load(f)

    niches = config.get("niches", [])
    if not niches:
        raise RuntimeError(f"No niches found in {KEYWORDS_FILE}")

    result_data = load_results()

    for niche in niches:
        niche_name = niche.get("name")
        keywords = niche.get("tier1", []) + niche.get("tier2", []) + niche.get("tier3", [])

        if niche_name not in result_data:
            result_data[niche_name] = []

        existing_video_ids = {v["video_id"] for v in result_data[niche_name]}

        for keyword in keywords:
            try:
                search_res = youtube.search().list(
                    q=keyword,
                    type="video",
                    part="id",
                    maxResults=25,
                    order="relevance",
                    videoDuration="medium",
                    videoEmbeddable="true"
                ).execute()
            except Exception as e:
                print(f"Search API error for keyword '{keyword}': {e}")
                continue

            for item in search_res.get("items", []):
                vid = item["id"].get("videoId")
                if not vid or vid in existing_video_ids:
                    continue

                video_info = get_video_data(vid)
                if not video_info:
                    continue

                result_data[niche_name].append(video_info)
                existing_video_ids.add(vid)

        result_data[niche_name] = sorted(result_data[niche_name], key=lambda x: x["score"], reverse=True)

    save_results(result_data)
    print(f"✅ Completed update: {OUTPUT_FILE}")
    return result_data

if __name__ == "__main__":
    fetch_and_score_youtube_videos()
