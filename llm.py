# llm.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

VY_GROQ_API_KEY = os.getenv("VY_GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def generate_llm_fallback(location, budget, activity, duration, motivation):
    prompt = f"""
    Generate 6 travel experience recommendations for {location}.
    Format as JSON list. 
    Each item must contain: title, description.

    User Filters:
    - Budget: {budget}
    - Activity: {activity}
    - Duration: {duration}
    - Motivation: {motivation}
    """

    try:
        res = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )

        text = res.choices[0].message.content

        import json
        return json.loads(text)

    except:
        return [{"title": "No results", "description": "LLM fallback failed"}]
