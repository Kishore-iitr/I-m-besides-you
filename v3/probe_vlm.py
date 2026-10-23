import urllib.request
import json
import time

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"

candidates = [
    "openrouter:google/gemini-2.0-flash-exp:free",
    "openrouter:google/gemini-2.0-flash-lite:free",
    "openrouter:qwen/qwen-2.5-vl-72b-instruct:free",
    "openrouter:meta-llama/llama-3.2-11b-vision-instruct:free",
    "openrouter:minimax/minimax-m3.1-flash:free",
    "openrouter:deepseek/deepseek-chat:free",
    "openrouter:meta-llama/llama-3.3-70b-instruct:free"
]

for m in candidates:
    payload = {
        "interface": "puter-chat-completion",
        "driver": "ai-chat",
        "test_mode": False,
        "method": "complete",
        "args": {
            "messages": [{"role": "user", "content": "Say hello"}],
            "model": m,
            "stream": False
        }
    }
    req = urllib.request.Request(
        "https://api.puter.com/drivers/call",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode("utf-8"))
            content = data.get("result", {}).get("message", {}).get("content", "")
            print(f"{m:<55} -> SUCCESS: {content[:40]}")
    except Exception as e:
        print(f"{m:<55} -> FAILED: {e}")
    time.sleep(1)
