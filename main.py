import os
import json
import random
import datetime
import requests
from flask import Flask

app = Flask(__name__)

# -------------------------------
# Load keywords.json OR fallback
# -------------------------------
try:
    with open("keywords.json", "r", encoding="utf-8") as f:
        keywords = json.load(f)
except FileNotFoundError:
    print("⚠️ keywords.json not found — using default placeholder keywords")
    keywords = {
        "weight_loss": ["diet", "exercise", "fat burning"],
        "pelvic_health": ["pelvic floor", "postpartum recovery"],
        "joint_relief": ["arthritis relief", "joint pain"],
        "liver_detox": ["liver cleanse", "detox tips"],
        "side_hustles": ["make money online", "passive income"],
        "respiratory_health": ["lung health", "breathing exercises"],
    }

# -------------------------------
# Example function that uses keywords
# -------------------------------
def get_random_keyword(niche: str) -> str:
    """Return a random keyword for the given niche."""
    return random.choice(keywords.get(niche, ["general health"]))

# -------------------------------
# Main route for Render health check
# -------------------------------
@app.route("/")
def index():
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"App running. Time: {today} | Example keyword: {get_random_keyword('weight_loss')}"

# -------------------------------
# Run app
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
