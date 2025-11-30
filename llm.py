# llm.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

VY_GROQ_API_KEY = os.getenv("VY_GROQ_API_KEY")
MODEL_ID = "llama3-70b-8192"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_HEADERS = {
    "Authorization": f"Bearer {VY_GROQ_API_KEY}",
    "Content-Type": "application/json"
}

def generate_zephyr_response(prompt: str, max_tokens: int = 350) -> str:
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a global travel assistant. Respond clearly and concisely."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": max_tokens
    }
    try:
        res = requests.post(GROQ_API_URL, headers=GROQ_HEADERS, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error generating text: {e}"
