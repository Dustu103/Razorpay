import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print(f"GROQ_API_KEY: {GROQ_API_KEY[:10] if GROQ_API_KEY else 'None'}")
print(f"GEMINI_API_KEY: {GEMINI_API_KEY[:10] if GEMINI_API_KEY else 'None'}")

# Test Groq with llama-3.3-70b-versatile or llama-3.1-70b-versatile or llama3-70b-8192
models = ["llama-3.3-70b-specdec", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]
for model in models:
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 10
            },
            timeout=5
        )
        print(f"Groq {model} status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Groq {model} success: {resp.json()['choices'][0]['message']['content']}")
            break
    except Exception as e:
        print(f"Groq {model} error: {e}")

# Test Gemini
try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    resp = requests.post(
        url,
        json={"contents": [{"parts": [{"text": "hello"}]}]},
        timeout=5
    )
    print(f"Gemini status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Gemini success: {resp.json()['candidates'][0]['content']['parts'][0]['text']}")
except Exception as e:
    print(f"Gemini error: {e}")
