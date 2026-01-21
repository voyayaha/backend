from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from urllib.parse import unquote
import httpx
from dotenv import load_dotenv
import os

from chat import register_chat_routes
from hotels import search_hotels
from social import get_youtube_posts, get_reddit_posts
from experiences import get_combined_experiences
from llm import generate_itinerary
from weather import get_weather_and_risk

load_dotenv()

app = FastAPI(title="Voyayaha – AI Travel Concierge")
register_chat_routes(app)

# -----------------------------
# CORS
# -----------------------------
origins = [
    "https://voyayaha.lovestoblog.com",
    "http://localhost:5173",
    "https://voyayaha.com",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# ROOT
# -----------------------------
@app.get("/")
def root():
    return {"status": "Voyayaha backend running"}

# -----------------------------
# IMAGE PROXY
# -----------------------------
@app.get("/img")
async def proxy_image(url: str):
    decoded = unquote(url)

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(decoded)
        r.raise_for_status()

        return Response(
            content=r.content,
            media_type=r.headers.get("content-type", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=86400"}
        )



# -----------------------------
# Main Endpoint
# -----------------------------
@app.get("/chat/experiences")
async def chat_experiences(
    location: str = Query(...),
    budget: str = "",
    activity: str = "",
    duration: str = "",
    motivation: str = "",
):
    """
    Always returns CITY-GUIDE STYLE itinerary:
    - title
    - intro
    - top_places (3 items)
    - indoor/outdoor suggestions based on current weather
    """

    # Step 1: Fetch nearby places + weather
    try:
        stops_data = await get_combined_experiences(location, activity or "tourist")
        yelp_results = stops_data.get("yelp", [])
        geo_results = stops_data.get("geoapify", [])
        final_stops = yelp_results + geo_results

        # Weather info
        weather = stops_data.get("weather", {"summary": "Unknown", "indoor_preferred": True})
        indoor_only = stops_data.get("indoor_only", weather.get("indoor_preferred", True))
    except Exception as e:
        print("Experience APIs failed:", e)
        final_stops = []
        weather = {"summary": "Unknown", "indoor_preferred": True}
        indoor_only = True

    # Step 2: Decide activity filter based on weather
    if indoor_only:
        activity_note = "Weather suggests indoor activities."
        query_suffix = " indoor"
    else:
        activity_note = "Weather is suitable for outdoor activities."
        query_suffix = " outdoor"

    # Step 3: Build LLM prompt (even if final_stops is empty)
    prompt = f"""
You are Voyayaha AI Travel Guide.

The user is visiting: {location}

User preferences:
Budget: {budget}
Activity: {activity}
Duration: {duration}
Motivation: {motivation}

Current weather: {weather.get("summary", "Unknown")}.
Suggestion: {activity_note}

Your task:
Generate 3 travel recommendations in CITY-GUIDE style.

Each recommendation MUST be a JSON object with:

- title: short heading
- intro: 1–2 lines describing what people generally enjoy in {location} (mention indoor/outdoor if relevant)
- top_places: an array of exactly 3 objects:
    - name: famous place or activity in {location}
    - tip: what the traveler can do there and why it's good

Example format:

[
  {{
    "title": "Highlights of Paris",
    "intro": "Paris is famous for romance, art, and iconic landmarks.",
    "top_places": [
      {{"name": "Eiffel Tower", "tip": "Enjoy panoramic views of the city."}},
      {{"name": "Louvre Museum", "tip": "Explore world-famous artworks."}},
      {{"name": "Seine Cruise", "tip": "Relax with an evening boat ride."}}
    ]
  }}
]

Nearby places for reference (may be empty):
{final_stops}

Return ONLY valid JSON. No extra text.
"""

    # Step 4: Call LLM
    try:
        ai_output = generate_itinerary(prompt)

        # Validate AI output
        if not ai_output or not isinstance(ai_output, list):
            raise ValueError("Invalid AI output")

        cleaned = []
        for item in ai_output:
            cleaned.append({
                "title": item.get("title", f"Highlights of {location}"),
                "intro": item.get("intro", f"{location} is popular for sightseeing, food, and culture. {activity_note}"),
                "top_places": item.get("top_places", [])[:3]
            })

        return {
            "stops": cleaned,
            "weather": weather
        }

    except Exception as e:
        # Final structured fallback (not generic titles)
        safe = [
            {
                "title": f"Highlights of {location}",
                "intro": f"{location} is known for its culture, food, and famous attractions. {activity_note}",
                "top_places": [
                    {"name": "City Center", "tip": "Walk around and explore major landmarks."},
                    {"name": "Local Market", "tip": "Try local cuisine and street food."},
                    {"name": "Famous Landmark", "tip": "Visit the most iconic place in the city."}
                ]
            }
        ]

        return {
            "stops": safe,
            "weather": weather,
            "warning": f"LLM failed, used structured fallback: {str(e)}"
        }



# -----------------------------
# EXPERIENCES (RAW DATA)
# -----------------------------
@app.get("/experiences")
async def experiences(location: str, query: str = "tourist"):
    """
    Returns weather, Yelp results, Geoapify fallback results.
    """
    return await get_combined_experiences(location, query)

# -----------------------------
# HOTELS
# -----------------------------
@app.get("/hotels")
async def hotels(city: str, check_in: str, check_out: str, limit: int = 6):
    return await search_hotels(city, check_in, check_out, limit)

# -----------------------------
# WEATHER
# -----------------------------
@app.get("/weather")
async def weather(location: str):
    return await get_weather_and_risk(location)

# -----------------------------
# CHAT / FRONTEND RECOMMENDATIONS (FIXED)
# -----------------------------

# -----------------------------
# SOCIAL
# -----------------------------
@app.get("/social")
async def social(location: str = "Mumbai", limit: int = 5):
    reddit_posts = await get_reddit_posts(location, limit)
    youtube_posts = await get_youtube_posts(location, limit)
    return youtube_posts + reddit_posts

# -----------------------------
# TRENDS
# -----------------------------
@app.get("/trends")
async def trends(location: str = "Pune"):
    query = f"{location} travel OR {location} places OR {location} itinerary"
    return await get_reddit_posts(query, limit=8)







