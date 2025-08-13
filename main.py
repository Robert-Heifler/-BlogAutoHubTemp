from flask import Flask, jsonify
import os
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
import requests

app = Flask(__name__)

# --- Existing routes ---
@app.route("/")
def home():
    return "App is running."

# --- New diagnostics route ---
@app.route("/diagnostics")
def diagnostics():
    result = {}

    # Masked environment variables
    env_vars = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "CLAUDE_API_KEY",
        "BLOGGER_BLOG_ID"
    ]
    for var in env_vars:
        val = os.getenv(var, "MISSING")
        if val != "MISSING":
            val = val[:4] + "****" + val[-4:]
        result[var] = val

    # Google OAuth test
    try:
        creds = Credentials(
            None,
            refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            token_uri="https://oauth2.googleapis.com/token"
        )
        creds.refresh(google.auth.transport.requests.Request())
        result["google_auth"] = "SUCCESS"
    except Exception as e:
        result["google_auth"] = f"FAIL: {str(e)}"

    # Claude API test
    try:
        claude_key = os.getenv("CLAUDE_API_KEY")
        resp = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {claude_key}"}
        )
        result["claude_api"] = f"{resp.status_code} {resp.reason}"
    except Exception as e:
        result["claude_api"] = f"FAIL: {str(e)}"

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
