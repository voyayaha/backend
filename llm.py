import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# API KEYS
# ─────────────────────────────────────────────────────────────────────────────

GROQ_RECOMMENDATION_KEY = os.getenv("GROQ_RECOMMENDATION_KEY")
OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")

MODEL_ID = "llama3-70b-8192"

# Groq API constants
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_HEADERS = {
    "Authorization": f"Bearer {GROQ_RECOMMENDATION_KEY}",
    "Content-Type": "application/json"
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Resolve ANY city in the world → Coordinates
# ─────────────────────────────────────────────────────────────────────────────

def get_city_coordinates(city_name: str):
    """Resolve a city name into latitude and longitude using OpenTripMap."""
    try:
        url = (
            f"https://api.opentripmap.com/0.1/en/places/geoname?"
            f"name={city_name}&apikey={OPENTRIPMAP_API_KEY}"
        )
        res = requests.get(url, timeout=20)
        res.raise_for_status()
        data = res.json()

        if "lat" in data and "lon" in data:
            return {"lat": data["lat"], "lon": data["lon"]}

        return None

    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Fetch attractions near that location
# ─────────────────────────────────────────────────────────────────────────────

def get_nearby_attractions(lat: float, lon: float, radius: int = 5000, limit: int = 10):
    """
    Use OpenTripMap radius API to fetch popular nearby attractions.
    Works globally for any location.
    """
    try:
        url = (
            f"https://api.opentripmap.com/0.1/en/places/radius?"
            f"radius={radius}&lon={lon}&lat={lat}&limit={limit}&apikey={OPENTRIPMAP_API_KEY}"
        )

        res = requests.get(url, timeout=20)
        res.raise_for_status()
        items = res.json().get("features", [])

        attractions = []
        for item in items:
            props = item.get("properties", {})

            attractions.append({
                "name": props.get("name", "Unnamed attraction"),
                "kinds": props.get("kinds", ""),
                "rating": props.get("rate", None),
                "osm": props.get("osm", None),
                # Simple default image; optional to upgrade later
                "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Blank_map.png/600px-Blank_map.png"
            })

        return attractions

    except Exception:
        return []

# ─────────────────────────────────────────────────────────────────────────────
# Combined helper for main.py
# ─────────────────────────────────────────────────────────────────────────────

def get_global_city_context(city_name: str):
    """
    Returns both coordinates + attractions in a single dictionary.

    {
        "coordinates": {"lat": ..., "lon": ...},
        "attractions": [...]
    }
    """
    coords = get_city_coordinates(city_name)
    if not coords:
        return {"error": f"City '{city_name}' not found"}

    attractions = get_nearby_attractions(coords["lat"], coords["lon"])

    return {
        "coordinates": coords,
        "attractions": attractions
    }

# ─────────────────────────────────────────────────────────────────────────────
# ░▒▓  LLM GENERATOR — MAIN EXPORT  ▓▒░
# ─────────────────────────────────────────────────────────────────────────────

def generate_zephyr_response(prompt: str, max_tokens: int = 350) -> str:
    """Send prompt to Groq's LLaMA model and return raw generated text."""
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a global travel assistant. Respond clearly and concisely. "
                    "Make sure your text is well-structured, factual, and directly useful."
                )
            },
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
