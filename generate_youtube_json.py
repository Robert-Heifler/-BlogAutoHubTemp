import json
import time
from datetime import datetime, timedelta
from googleapiclient.discovery import build

API_KEY = "YOUR_API_KEY"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

NICHES_KEYWORDS = {
    "Weight Loss": {
        "tier1": ["weight loss", "fat loss", "diet"],
        "tier2": ["low carb diet", "HIIT workout", "calorie deficit", "intermittent fasting", "keto meal plan"],
        "tier3": ["how many calories to lose weight", "beginner hiit at home", "best time to eat for weight loss"],
    },
    "Pelvic Health": {
        "tier1": ["pelvic floor", "pelvic health", "kegels"],
        "tier2": ["pelvic floor exercises", "diastasis recti", "postpartum recovery", "bladder control exercises", "pelvic pain relief"],
        "tier3": ["safe ab exercises postpartum", "pelvic pain relief tips", "improve bladder control naturally"],
    },
    "Joint Relief": {
        "tier1": ["joint health", "arthritis", "pain relief"],
        "tier2": ["natural remedies for arthritis", "knee pain exercises", "anti inflammatory foods", "yoga for joint pain", "mobility stretches"],
        "tier3": ["best supplements for joint pain", "knee strengthening at home", "shoulder mobility routine"],
    },
    "Liver Detox": {
        "tier1": ["liver health", "detox", "cleanse"],
        "tier2": ["liver detox diet", "foods for liver health", "natural liver cleanse", "milk thistle benefits", "signs of fatty liver"],
        "tier3": ["daily habits for liver health", "best drinks for liver detox", "symptoms of poor liver function"],
    },
    "Side Hustles": {
        "tier1": ["make money online", "side hustle", "passive income"],
        "tier2": ["best side hustles 2025", "freelancing tips", "affiliate marketing for beginners", "print on demand business", "dropshipping explained"],
        "tier3": ["how to make money with ai", "low cost side hustles", "side hustles for introverts"],
    },
    "Respiratory Health": {
        "tier1": ["lung health", "breathing", "respiratory health"],
        "tier2": ["breathing exercises for lungs", "asthma natural remedies", "improve lung capacity", "quit smoking tips", "yoga breathing techniques"],
        "tier3": ["foods for better lung health", "breathing exercises for stress", "ways to increase oxygen levels"],
    },
}

# Settings for quota management and caching refresh frequency (days)
REFRESH_FREQ = {
    "tier1": 1,
    "tier2": 3,
    "tier3": 7,
}

MAX_SEARCH_RESULTS = 25  # Only 1 page of 25 results per keyword per day to save quota
MAX_VIDEOS_PER_CALL = 50
CACHE_FILENAME = "youtube_videos_cache.json"

def get_youtube_client():
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)

def youtube_search(youtube, query, page_token=None):
    return youtube.search().list(
        q=query,
        type="video",
        part="id",
        maxResults=MAX_SEARCH_RESULTS,
        pageToken=page_token
    ).execute()

def get_video_details(youtube, video_ids):
    return youtube.videos().list(
        part="statistics",
        id=",".join(video_ids)
    ).execute()

def compute_score(video):
    stats = video.get("statistics", {})
    view_count = int(stats.get("viewCount", 0))
    like_count = int(stats.get("likeCount", 0))
    return view_count * 0.7 + like_count * 0.3  # Adjust to your formula

def load_cache():
    try:
        with open(CACHE_FILENAME, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_cache(cache):
    with open(CACHE_FILENAME, "w") as f:
        json.dump(cache, f, indent=2)

def is_stale(cached_entry, refresh_days):
    last_updated_str = cached_entry.get("last_updated")
    if not last_updated_str:
        return True
    last_updated = datetime.fromisoformat(last_updated_str)
    return datetime.now() - last_updated > timedelta(days=refresh_days)

def main():
    youtube = get_youtube_client()
    cache = load_cache()
    output = []

    # Rotate tiers by day - only refresh lower tiers on selected days
    today = datetime.now().date()
    refresh_tiers = ["tier1"]
    if today.day % 3 == 0:
        refresh_tiers.append("tier2")
    if today.day % 7 == 0:
        refresh_tiers.append("tier3")

    for niche, tiers in NICHES_KEYWORDS.items():
        print(f"Processing niche: {niche}")
        unique_video_ids = set()

        # Priority tier processing with quota optimization
        for tier_name in refresh_tiers:
            keywords = tiers.get(tier_name, [])
            print(f"  Refreshing keywords in {tier_name}...")

            for keyword in keywords:
                # Search only one page (25 results) per keyword per day to save quota
                try:
                    search_response = youtube_search(youtube, keyword)
                except Exception as e:
                    print(f"    Search error for '{keyword}': {e}, skipping")
                    continue

                for item in search_response.get("items", []):
                    vid = item["id"]["videoId"]
                    # Check cache freshness before adding for update
                    cached = cache.get(vid)
                    if not cached or is_stale(cached, REFRESH_FREQ[tier_name]):
                        unique_video_ids.add(vid)

        # Batch video detail calls only for required fresh videos
        video_ids_list = list(unique_video_ids)
        print(f"  Fetching details for {len(video_ids_list)} videos...")
        for i in range(0, len(video_ids_list), MAX_VIDEOS_PER_CALL):
            batch_ids = video_ids_list[i:i+MAX_VIDEOS_PER_CALL]
            try:
                videos_response = get_video_details(youtube, batch_ids)
            except Exception as e:
                print(f"  Error fetching video details for batch: {e}, retry later")
                time.sleep(5)
                continue

            for video in videos_response.get("items", []):
                vid = video["id"]
                score = compute_score(video)
                cache[vid] = {
                    "score": score,
                    "niche": niche,
                    "last_updated": datetime.now().isoformat()
                }
                output.append({"video_id": vid, "niche": niche, "score": score})
            time.sleep(1)  # Respect YouTube API rate limits

        # Append cached videos that don't need refreshing
        for vid, data in cache.items():
            if data["niche"] == niche and vid not in unique_video_ids:
                output.append({"video_id": vid, "niche": niche, "score": data["score"]})

    save_cache(cache)

    with open("youtube_videos_scored.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Done. Total videos scored today: {len(output)}")

if __name__ == "__main__":
    main()
