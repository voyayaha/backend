from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from urllib.parse import unquote
import httpx
from dotenv import load_dotenv
import os

from hotels import search_hotels
from social import get_youtube_posts, get_reddit_posts
from experiences import get_combined_experiences
from llm import generate_itinerary
from weather import get_weather_and_risk

load_dotenv()

app = FastAPI(title="Voyayaha – AI Travel Concierge")

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
@app.get("/chat/experiences")
async def chat_experiences(
    location: str = Query(...),
    budget: str = "",
    activity: str = "",
    duration: str = "",
    motivation: str = "",
):
    """
    This is the endpoint your frontend calls.
    It will NEVER return empty stops now.
    """

    # Step 1: Fetch nearby places (Yelp + Geoapify fallback)
    stops_data = await get_combined_experiences(location, activity or "tourist")

    yelp_results = stops_data.get("yelp", [])
    geo_results = stops_data.get("geoapify", [])

    final_stops = yelp_results + geo_results

    # Step 2: If nothing found, use SAFE FALLBACK (no empty UI)
    if not final_stops:
        fallback = [
            {
                "title": f"Explore {location}",
                "description": f"Popular attractions and must-visit places in {location}."
            },
            {
                "title": f"Food Walk in {location}",
                "description": "Discover famous local food spots and street food."
            },
            {
                "title": f"Heritage Tour of {location}",
                "description": "Visit historical landmarks and cultural sites."
            }
        ]
        return {"stops": fallback}

    # Step 3: Build prompt for LLM
    prompt = f"""
You are Voyayaha AI Trip Planner.

User preferences:
Location: {location}
Budget: {budget}
Activity: {activity}
Duration: {duration}
Motivation: {motivation}

Here are nearby places:
{final_stops}

Generate 4–6 travel stops as a JSON array.
Each item must have:
- title
- description
- why_it_fits

Output only JSON. No extra text.
"""

    # Step 4: Call LLM
    try:
        ai_output = generate_itinerary(prompt)

        # If LLM returns empty or invalid, fallback again
        if not ai_output or len(ai_output) == 0:
            return {"stops": final_stops[:5]}

        return {"stops": ai_output}

    except Exception as e:
        # Final safety fallback
        return {
            "stops": final_stops[:5],
            "warning": f"LLM failed, returned raw results instead: {str(e)}"
        }

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
