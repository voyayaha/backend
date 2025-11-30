from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os
import re

from hotels import search_hotels
from social import scrape_social, get_trending_spots
from llm import get_global_city_context, generate_zephyr_response
from weather import get_weather_and_risk
from yelp_backend import yelp_search

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

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")

# ──────────────────────────────
# EXPERIENCES (Yelp + OpenTripMap)
# ──────────────────────────────
@app.get("/experiences")
async def experiences(location: str = Query(...), query: str = Query("")):
    weather = await get_weather_and_risk(location)
    wants_indoor = weather.get("indoor_preferred", False)

    yelp_results = await yelp_search(location, query)

    # OpenTripMap fallback
    context = get_global_city_context(location)
    otm_results = context.get("attractions", [])

    return {
        "weather": weather,
        "yelp": yelp_results,
        "opentripmap": otm_results
    }

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
            f"Weather: {weather_data.get('summary', 'N/A')}, "
            f"Temp: {weather_data.get('temperature_c', 'N/A')}°C, "
            f"Prefer: {'Indoor' if weather_data.get('indoor_preferred') else 'Outdoor'}"
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

        if not raw or raw.startswith("Error generating text"):
            return {"stops": [], "error": raw}

        matches = re.findall(r"\*\*Stop \d: (.*?)\*\*\n(.+?)(?=(\*\*Stop \d|$))", raw, re.DOTALL)

        stops = []
        for match in matches:
            if len(match) >= 2:
                stops.append({"title": match[0].strip(), "description": match[1].strip()})

        if not stops:
            stops = [{"title": "No data", "description": "Could not generate itinerary at this time."}]

        return {"stops": stops}

    except Exception as e:
        return {"stops": [], "error": str(e)}

# ──────────────────────────────
# SOCIAL
# ──────────────────────────────
@app.get("/social")
async def social(location: str, limit: int = 5):
    return await scrape_social(location, limit)

# ──────────────────────────────
# TRENDS
# ──────────────────────────────
@app.get("/trends")
async def trends(location: str = "Pune"):
    return await get_trending_spots(location)
