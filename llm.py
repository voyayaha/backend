import os
import requests

GROQ_RECOMMENDATION_KEY = os.getenv("GROQ_RECOMMENDATION_KEY")
MODEL_ID = "llama3-70b-8192"

API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {GROQ_RECOMMENDATION_KEY}",
    "Content-Type": "application/json"
}

def generate_zephyr_response(prompt: str, max_tokens: int = 250) -> str:
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a travel assistant. Respond ONLY with a JSON array of 3 unique travel experiences "
                    "in this format: [{\"title\": \"\", \"description\": \"\", \"image\": \"\", \"url\": \"\"}]. "
                    "The 'image' should be a REAL image URL and the 'url' should be a real tour link from Viator, if possible. "
                    "Ensure variety in the experiences (e.g., cultural, adventure, relaxation). No extra text."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error generating text: {e}"
