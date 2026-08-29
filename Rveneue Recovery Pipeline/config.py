import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "your-google-api-key-here")
LLM_MODEL = "gemini-1.5-flash"
PORT = int(os.getenv("PORT", 8000))
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
os.makedirs(MODELS_DIR, exist_ok=True)