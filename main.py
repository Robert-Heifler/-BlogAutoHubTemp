import os
import json
from flask import Flask, request

# -----------------------------
# Runtime config generation
# -----------------------------
CONFIG_PATH = "config.json"

if not os.path.exists(CONFIG_PATH):
    config_data = {
        "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "GOOGLE_REFRESH_TOKEN": os.environ.get("GOOGLE_REFRESH_TOKEN")
    }

    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f)

# -----------------------------
# Load config for use in app
# -----------------------------
with open(CONFIG_PATH) as f:
    config = json.load(f)

# -----------------------------
# Initialize Flask app
# -----------------------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "BlogWorker is live!"

# -----------------------------
# Example route using config
# -----------------------------
@app.route("/test-config", methods=["GET"])
def test_config():
    return {
        "client_id": config.get("GOOGLE_CLIENT_ID"),
        "client_secret_present": bool(config.get("GOOGLE_CLIENT_SECRET")),
        "refresh_token_present": bool(config.get("GOOGLE_REFRESH_TOKEN"))
    }

# -----------------------------
# Start the app
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
