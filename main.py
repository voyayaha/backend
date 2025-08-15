from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
from hotels import search_hotels
from social import scrape_social
from db import init_db, save_message
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from experiences import search_experiences
from weather import get_weather_and_risk
from travelrisk import get_custom_travel_risk
from llm import generate_zephyr_response
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from opentripmap import get_mindful_places
from social import get_trending_spots
import praw  # <-- ADD THIS
from chat import register_chat_routes
from fastapi import FastAPI, HTTPException, Query
from typing import List
import re






load_dotenv()   # pull API keys from .env

app = FastAPI(title="Voyayaha – AI Travel Concierge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_chat_routes(app)

# ─── Basic route ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")          # Swagger UI

# ─── Experiences (Viator, weather‑filtered) ──────────────────────────────────
@app.get("/experiences")
async def experiences(
    location: str = Query(..., description="City / destination"),
    query:    str = Query("",  description="Activity keyword"),
    date:     str | None = Query(None, description="Optional trip date (YYYY‑MM‑DD)")
):
    return await search_experiences(location, query, date)

# ─── Hotels (Travelpayouts) ───────────────────────────────────────────────────
@app.get("/hotels")
async def hotels(
    city: str = Query(...),
    check_in: str = Query(..., regex=r"\d{4}-\d{2}-\d{2}"),
    check_out: str = Query(..., regex=r"\d{4}-\d{2}-\d{2}"),
    limit: int = Query(6, ge=1, le=20)
):
    return await search_hotels(city, check_in, check_out, limit)
    

# ─── Weather summary (plus indoor/outdoor flag) ───────────────────────────────
@app.get("/weather")
async def weather(location: str):
    return await get_weather_and_risk(location)


# ─── AI Chat powered by Zephyr + optional voice ──────────────────────────────
@app.get("/chat/experiences")
async def chat_with_context(
    location: str = Query(..., description="City or location name"),
    budget: str = Query(None, description="Budget level: budget, midrange, luxury"),
    activity: str = Query(None, description="Type of activity: adventure, cultural, relaxation, nature"),
    duration: str = Query(None, description="Trip duration: half_day, full_day, multi_day"),
    motivation: str = Query(None, description="Reason for travel: honeymoon, family, friends, solo")
):
    try:
        # Fetch weather and experiences
        weather_data = await get_weather_and_risk(location)
        experiences = await search_experiences(location)

        experience_titles = [exp.get("title", "") for exp in experiences if exp.get("title")]
        weather_info = (
            f"Weather: {weather_data['summary']}, "
            f"Temp: {weather_data['temperature_c']}°C, "
            f"Prefer: {'Indoor' if weather_data['indoor_preferred'] else 'Outdoor'}"
        )

        # Build personalization details
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

        # Create AI prompt
        prompt = f"""
You are a travel assistant helping a user visiting {location}.
Context:
- {weather_info}
- Recommended experiences: {', '.join(experience_titles)}
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

        # Parse stops from AI response
        pattern = r"\*\*Stop \d: (.*?)\*\*\n(.+?)(?=(\*\*Stop \d|$))"
        matches = re.findall(pattern, raw_response, re.DOTALL)

        stops = [
            {
                "title": title.strip(),
                "description": description.strip()
            }
            for title, description, _ in matches
        ]

        return {"stops": stops}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/village/experiences")
async def chat_village_experiences(
    location: str = Query(..., description="Location for village tourism"),
    budget: str = Query(None, description="Budget range"),
    duration: str = Query(None, description="Duration of stay"),
    activity_type: str = Query(None, description="Type of activities interested in"),
    motivation: str = Query(None, description="Reason for visit, e.g. honeymoon, family trip")
):
    """
    Tailored village tourism recommendations.
    """
    try:
        # Fetch weather + travel risk for better recommendations
        weather_data = await get_weather_and_risk(location)

        # Fetch base experiences for that location
        experiences = await search_experiences(location)

        # Build context prompt for AI
        experience_titles = [exp.get("title", "") for exp in experiences if exp.get("title")]
        weather_info = f"Weather: {weather_data['summary']}, Temp: {weather_data['temperature_c']}°C, Prefer: {'Indoor' if weather_data['indoor_preferred'] else 'Outdoor'}"

        prompt = f"""
You are a travel assistant specializing in **village tourism**.
User is visiting {location} with the following preferences:
- Budget: {budget}
- Duration: {duration}
- Activity Type: {activity_type}
- Motivation: {motivation}
- {weather_info}

Recommended experiences in the area: {', '.join(experience_titles)}

Create a **personalized 1-day village itinerary** with 3 stops, focusing on:
- Nostalgic experiences like 'Nani ka Gaon', peepal trees, rivers, fresh farm food
- Local arts (pottery, weaving, folk music)
- Farm activities (fruit picking, vegetable harvesting)
- Self-sustainability practices
- Community life

**Stop 1: [Name of activity]**
[One-sentence description]

**Stop 2: [Name of activity]**
[One-sentence description]

**Stop 3: [Name of activity]**
[One-sentence description]
"""

        raw_response = generate_zephyr_response(prompt)

        # Parse stops
        import re
        pattern = r"\*\*Stop \d: (.*?)\*\*\n(.+?)(?=(\*\*Stop \d|$))"
        matches = re.findall(pattern, raw_response, re.DOTALL)

        stops = [
            {
                "title": title.strip(),
                "description": description.strip()
            }
            for title, description, _ in matches
        ]

        return {"stops": stops}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/social")
async def social(location: str = Query(...), limit: int = 5):
    return await scrape_social(location, limit)





        
# ─── Nearby attractions using OpenTripMap ─────────────────────────────────
@app.get("/mindful")
async def mindful_places(
    lat: float = Query(..., description="Latitude of location"),
    lon: float = Query(..., description="Longitude of location"),
    radius: int = Query(2000, description="Radius in meters"),
    limit: int = Query(5, description="Number of places to return")
):
    try:
        return await get_mindful_places(lat, lon, radius, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching mindful places: {e}")


# ─── Travel trend predictions or data ─────────────────────────────────────
@app.get("/trends")
async def travel_trends(location: str = Query("Pune")):
    return await get_trending_spots(location)







