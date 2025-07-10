import os, json, requests

_API = "https://openrouter.ai/api/v1/chat/completions"
_KEY = os.environ["OPENROUTER_API_KEY"]

def summarize(text: str, max_tokens: int = 256) -> str:
    body = {
        "model": "anthropic/claude-3-haiku",
        "messages": [{"role": "user", "content": f"Summarize:\n\n{text}"}],
        "max_tokens": max_tokens
    }
    r = requests.post(
        _API,
        headers={"Authorization": f"Bearer {_KEY}", "Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
