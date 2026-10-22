import json
import time
import urllib.request

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"

candidate_models = [
    "openrouter:minimax/minimax-m3.1-flash:free",
    "openrouter:meta-llama/llama-3.3-70b-instruct:free",
    "openrouter:google/gemini-2.0-flash-exp:free",
    "openrouter:mistralai/mistral-small-24b-instruct-2501:free",
    "openrouter:qwen/qwen-2.5-72b-instruct:free",
    "gpt-4o-mini"
]

def probe_model(model_name):
    url = "https://api.puter.com/drivers/call"
    payload = {
        "interface": "puter-chat-completion",
        "driver": "ai-chat",
        "test_mode": False,
        "method": "complete",
        "args": {
            "messages": [{"role": "user", "content": "Respond with the single word: OK"}],
            "model": model_name,
            "stream": False,
            "temperature": 0.1
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST"
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode("utf-8"))
            elapsed = time.time() - t0
            msg = data.get("result", {}).get("message", {}).get("content", "").strip()
            print(f"[OK] {model_name:55} -> {elapsed:.2f}s | Response: {msg[:30]}")
            return True, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[ERR] {model_name:55} -> {elapsed:.2f}s | Error: {e}")
        return False, elapsed

print("Probing Puter models for latency and availability...")
for m in candidate_models:
    probe_model(m)
