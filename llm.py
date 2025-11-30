import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def generate_itinerary(prompt: str):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    body = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {"role": "system", "content": "You generate structured JSON trip suggestions."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 600
    }

    r = requests.post(url, json=body, headers=headers)
    
    if r.status_code != 200:
        raise ValueError(f"Error generating text: {r.text}")

    content = r.json()["choices"][0]["message"]["content"]

    # Expecting JSON output
    import json
    try:
        return json.loads(content)
    except:
        return [{"title": "AI Output", "description": content}]
