from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os
import re

from hotels import search_hotels
from social import get_youtube_posts, get_reddit_posts
from experiences import get_combined_experiences
from llm import generate_itinerary
from weather import get_weather_and_risk
from yelp_backend import search_yelp


load_dotenv()

app = FastAPI(title="Voyayaha – AI Travel Concierge")

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

@app.get("/")
def root():
    return {"status": "Voyayaha backend running"}

# ──────────────────────────────
# EXPERIENCES 
# ──────────────────────────────
@app.get("/experiences")
async def experiences(location: str, query: str = "tourist"):
    """
    Returns weather, Yelp results, Geoapify fallback results.
    """
    return await get_combined_experiences(location, query)

# ──────────────────────────────
# HOTELS
# ──────────────────────────────
@app.get("/hotels")
async def hotels(city: str, check_in: str, check_out: str, limit: int = 6):
    return await search_hotels(city, check_in, check_out, limit)

# ──────────────────────────────
# WEATHER
# ──────────────────────────────
@app.get("/weather")
async def weather(location: str):
    return await get_weather_and_risk(location)

# ──────────────────────────────
# CHAT WITH CONTEXT
# ──────────────────────────────
@app.get("/chat/experiences")
async def chat_experiences(
    location: str = Query(...),
    budget: str = "",
    activity: str = "",
    duration: str = "",
    motivation: str = "",
):
    stops = await get_combined_experiences(location, activity or "tourist")

    final_stops = stops.get("yelp", []) + stops.get("geoapify", [])
    if not final_stops:
        return {"stops": [], "message": "No results found. Try changing your filters."}

    prompt = f"""
    You are Voyayaha AI Trip Planner.
    User wants recommendations for:
    Location: {location}
    Budget: {budget}
    Activity: {activity}
    Duration: {duration}
    Motivation: {motivation}

    Here are nearby places:
    {final_stops}

    Generate 4–6 travel stops with:
      - Title
      - Description
      - Why it fits the user's preferences
    """

    try:
        ai_output = generate_itinerary(prompt)
        return {"stops": ai_output}
    except Exception as e:
        return {"error": f"LLM error: {str(e)}"}


# --------------------------------------------------
# SOCIAL ENDPOINT
# --------------------------------------------------

@app.get("/social")
async def social(location: str = "Mumbai", limit: int = 5):
    reddit_posts = await get_reddit_posts(location, limit)
    youtube_posts = await get_youtube_posts(location, limit)
    return youtube_posts + reddit_posts

# --------------------------------------------------
# TRENDING SPOTS
# --------------------------------------------------

@app.get("/trends")
async def trends(location: str = "Pune"):
    query = f"{location} travel OR {location} places OR {location} itinerary"
    return await get_reddit_posts(query, limit=8)









