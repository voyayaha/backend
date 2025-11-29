# main.py rewritten with Yelp + OpenTripMap and optional Viator fallback

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os
import re

# Local modules
from hotels import search_hotels
from social import scrape_social, get_trending_spots
from db import init_db, save_message
from llm import get_global_city_context, generate_zephyr_response
from weather import get_weather_and_risk
from travelrisk import get_custom_travel_risk
from chat import register_chat_routes
from yelp_backend import yelp_search
from opentripmap import get_mindful_places
from experiences import search_experiences   # optional, only used as fallback

load_dotenv()

app = FastAPI(title="Voyayaha – AI Travel Concierge")

origins = [
    "https://voyayaha.lovestoblog.com",
    "http://localhost:5173",
    "https://voyayaha.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_chat_routes(app)

# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")

# ---------------------------------------------------------------------------
# EXPERIENCES (Yelp + OpenTripMap, Viator optional fallback)
# ---------------------------------------------------------------------------
@app.get("/experiences")
async def experiences(
    location: str = Query(..., description="City / destination"),
    query: str = Query("", description="Keyword"),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
):
    # Weather preference
    weather = await get_weather_and_risk(location)
    wants_indoor = weather.get("indoor_preferred", False)

    # Yelp primary
    yelp_results = await yelp_search(location, query, wants_indoor)

    # If coordinates given → enhance with OpenTripMap
    otm_results = []
    if lat and lon:
        try:
            otm_results = await get_mindful_places(lat, lon, radius=3000, limit=5)
        except:
            otm_results = []

    # Viator fallback ONLY if Yelp result empty
    viator_results = []
    if not yelp_results:
        try:
            viator_results = await search_experiences(location, query)
        except:
            viator_results = []

    return {
        "weather": weather,
        "yelp": yelp_results,
        "opentripmap": otm_results,
        "viator_fallback": viator_results,
    }

# ---------------------------------------------------------------------------
# HOTELS
# ---------------------------------------------------------------------------
@app.get("/hotels")
async def hotels(city: str, check_in: str, check_out: str, limit: int = 6):
    return await search_hotels(city, check_in, check_out, limit)

# ---------------------------------------------------------------------------
# WEATHER
# ---------------------------------------------------------------------------
@app.get("/weather")
async def weather(location: str):
    return await get_weather_and_risk(location)

# ---------------------------------------------------------------------------
# AI TRAVEL CHAT
# ---------------------------------------------------------------------------
@app.get("/chat/experiences")
async def chat_with_context(
    location: str,
    budget: str | None = None,
    activity: str | None = None,
    duration: str | None = None,
    motivation: str | None = None,
):
    try:
        weather_data = await get_weather_and_risk(location)
        yelp_data = await yelp_search(location, "")
        context = get_global_city_context(location)

        yelp_titles = [x.get("name", "") for x in yelp_data]

        weather_info = (
            f"Weather: {weather_data['summary']}, "
            f"Temp: {weather_data['temperature_c']}°C, "
            f"Prefer: {'Indoor' if weather_data['indoor_preferred'] else 'Outdoor'}"
        )

        pref = []
        if budget: pref.append(f"Budget: {budget}")
        if activity: pref.append(f"Activity: {activity}")
        if duration: pref.append(f"Duration: {duration}")
        if motivation: pref.append(f"Motivation: {motivation}")
        pref_str = " | ".join(pref) if pref else "No preferences"

        prompt = f"""
You are a travel assistant helping a user visiting {location}.
Context:
- {weather_info}
- Popular activities (Yelp): {', '.join(yelp_titles)}
- City facts: {context}
- User preferences: {pref_str}

Task:
Create a personalized itinerary with exactly 3 stops.
Use the format:

**Stop 1: [Activity]**
[One sentence]

**Stop 2: [Activity]**
[One sentence]

**Stop 3: [Activity]**
[One sentence]
"""

        raw = generate_zephyr_response(prompt)
        pattern = r"\*\*Stop \d: (.*?)\*\*\n(.+?)(?=(\*\*Stop \d|$))"
        matches = re.findall(pattern, raw, re.DOTALL)

        stops = [{"title": t.strip(), "description": d.strip()} for t, d, _ in matches]

        return {"stops": stops}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
@app.get("/social")
async def social(location: str, limit: int = 5):
    return await scrape_social(location, limit)

# ---------------------------------------------------------------------------
@app.get("/mindful")
async def mindful(lat: float, lon: float, radius: int = 2000, limit: int = 5):
    return await get_mindful_places(lat, lon, radius, limit)

# ---------------------------------------------------------------------------
@app.get("/trends")
async def trends(location: str = "Pune"):
    return await get_trending_spots(location)
