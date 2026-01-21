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
def normalize_stops(stops, location, motivation):
    normalized = []

    for s in stops:
        normalized.append({
            "title": s.get("title") or s.get("name") or f"Explore {location}",
            "description": s.get("description") or "Enjoy this recommended place during your trip.",
            "why_it_fits": f"Matches your interest in {motivation or 'exploring new places'}."
        })

    return normalized


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
    Returns city guide style recommendations:
    - title
    - intro
    - top_places (3 items)
    """

    # Step 1: Fetch nearby places (Yelp + Geoapify fallback)
    stops_data = await get_combined_experiences(location, activity or "tourist")

    yelp_results = stops_data.get("yelp", [])
    geo_results = stops_data.get("geoapify", [])

    final_stops = yelp_results + geo_results

    # Step 2: If APIs give nothing → hard fallback
    if not final_stops:
        fallback = [
            {
                "title": f"Explore {location}",
                "intro": f"{location} is popular for sightseeing, food, and local culture.",
                "top_places": [
                    {"name": f"Famous Landmark in {location}", "tip": "Visit the main historical attraction."},
                    {"name": f"Local Market in {location}", "tip": "Try local food and shopping."},
                    {"name": f"Scenic Area in {location}", "tip": "Relax and enjoy city views."}
                ]
            }
        ]
        return {"stops": fallback}

    # Step 3: LLM prompt for structured output
    prompt = f"""
You are Voyayaha AI Travel Guide.

The user is visiting: {location}

Generate 3 recommendations.

Each recommendation MUST be a JSON object with:

- title: short heading
- intro: 1–2 lines describing what people like to do in this city
- top_places: an array of exactly 3 objects:
    - name: place name
    - tip: what the traveler can do there

Example:

[
  {{
    "title": "Explore Paris",
    "intro": "Paris is famous for art, romance, and historic landmarks.",
    "top_places": [
      {{"name": "Eiffel Tower", "tip": "Enjoy city views from the top."}},
      {{"name": "Louvre Museum", "tip": "Explore world-famous artworks."}},
      {{"name": "Seine River Cruise", "tip": "Relax with an evening cruise."}}
    ]
  }}
]

Here are some nearby places for reference:
{final_stops}

Return ONLY valid JSON. No extra text.
"""

    # Step 4: Call LLM
    try:
        ai_output = generate_itinerary(prompt)

        # Validate output
        if not ai_output or not isinstance(ai_output, list):
            raise ValueError("Invalid AI output format")

        # Ensure required keys exist
        cleaned = []
        for item in ai_output:
            cleaned.append({
                "title": item.get("title", f"Explore {location}"),
                "intro": item.get("intro", f"{location} is popular for travel and sightseeing."),
                "top_places": item.get("top_places", [])[:3]
            })

        return {"stops": cleaned}

    except Exception as e:
        # Final safe fallback
        safe = [
            {
                "title": f"Explore {location}",
                "intro": f"{location} is popular for sightseeing, food, and culture.",
                "top_places": [
                    {"name": "City Center", "tip": "Walk around and explore main attractions."},
                    {"name": "Local Market", "tip": "Try local cuisine and shopping."},
                    {"name": "Famous Landmark", "tip": "Visit the most iconic place in the city."}
                ]
            }
        ]
        return {
            "stops": safe,
            "warning": f"LLM failed, used fallback: {str(e)}"
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





