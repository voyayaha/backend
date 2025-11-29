# main.py
import os
import re
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from hotels import search_hotels
from social import scrape_social, get_trending_spots
from db import init_db, save_message
from llm import get_global_city_context, generate_zephyr_response
from weather import get_weather_and_risk
from experiences import search_experiences
from opentripmap import get_mindful_places
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


@app.get("/experiences")
async def experiences(location: str = Query(..., description="City / destination"),
                      query: str = Query("", description="Activity keyword"),
                      date: str | None = Query(None, description="Optional trip date (YYYY-MM-DD)")):
    return await search_experiences(location, query, date)


@app.get("/hotels")
async def hotels(city: str = Query(...), check_in: str = Query(..., regex=r"\d{4}-\d{2}-\d{2}"),
                 check_out: str = Query(..., regex=r"\d{4}-\d{2}-\d{2}"), limit: int = Query(6, ge=1, le=20)):
    return await search_hotels(city, check_in, check_out, limit)


@app.get("/weather")
async def weather(location: str):
    return await get_weather_and_risk(location)


# Chat route supports both GET query params and POST JSON
@app.get("/chat/experiences")
@app.post("/chat/experiences")
async def chat_with_context(request: Request,
                            location: str | None = Query(None),
                            budget: str | None = Query(None),
                            activity: str | None = Query(None),
                            duration: str | None = Query(None),
                            motivation: str | None = Query(None)):
    # read JSON body only if POST and body exists
    if request.method == "POST":
        try:
            body = await request.json()
            # body may be string if client sent plain text; guard with dict check
            if isinstance(body, dict):
                location = location or body.get("location")
                budget = budget or body.get("budget")
                activity = activity or body.get("activity")
                duration = duration or body.get("duration")
                motivation = motivation or body.get("motivation")
        except Exception:
            pass

    if not location:
        raise HTTPException(status_code=400, detail="Missing required parameter: location")

    # Build context
    weather_data = await get_weather_and_risk(location)
    experiences = await search_experiences(location, query=activity or "")
    context = get_global_city_context(location)

    experience_titles = [exp.get("title") or exp.get("title") or exp.get("name") for exp in experiences]
    weather_info = (
        f"Weather: {weather_data.get('summary','')}, "
        f"Temp: {weather_data.get('temperature_c','')}°C, "
        f"Prefer: {'Indoor' if weather_data.get('indoor_preferred') else 'Outdoor'}"
    )

    preferences = []
    if budget:
        preferences.append(f"Budget: {budget}")
    if activity:
        preferences.append(f"Activity Type: {activity}")
    if duration:
        preferences.append(f"Duration: {duration}")
    if motivation:
        preferences.append(f"Motivation: {motivation}")

    preferences_str = " | ".join(preferences) if preferences else "No extra preferences given"

    prompt = f"""
You are a travel assistant helping a user visiting {location}.
Context:
- {weather_info}
- Recommended experiences: {', '.join(experience_titles)}
- City facts: {context}
- User preferences: {preferences_str}

Task:
Create a personalized itinerary with exactly 3 stops that match the preferences above.
Use this exact format:

**Stop 1: [Name of activity]**
[One-sentence description]

**Stop 2: [Name of activity]**
[One-sentence description]

**Stop 3: [Name of activity]**
[One-sentence description]
"""

    raw_response = generate_zephyr_response(prompt)
    # fallback if model returned nothing or an error string
    if not raw_response or raw_response.lower().startswith("error"):
        raise HTTPException(status_code=500, detail=f"LLM error: {raw_response}")

    pattern = r"\*\*Stop \d: (.*?)\*\*\n(.+?)(?=(\*\*Stop \d|$))"
    matches = re.findall(pattern, raw_response, re.DOTALL)

    stops = []
    for m in matches:
        title = m[0].strip()
        desc = m[1].strip()
        stops.append({"title": title, "description": desc})

    return {"stops": stops}


@app.get("/social")
async def social(location: str = Query(...), limit: int = 5):
    return await scrape_social(location, limit)


@app.get("/mindful")
async def mindful(lat: float = Query(...), lon: float = Query(...), radius: int = Query(2000), limit: int = Query(5)):
    return await get_mindful_places(lat, lon, radius, limit)


@app.get("/trends")
async def trends(location: str = Query("Pune")):
    return await get_trending_spots(location)
