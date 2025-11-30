from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os
import re

from hotels import search_hotels
from social import scrape_social, get_trending_spots
from llm import generate_zephyr_response
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
# EXPERIENCES 
# ──────────────────────────────
@app.get("/experiences")
async def experiences(location: str = Query(...), query: str = Query(""), per_page: int = 6):
    weather = await get_weather_and_risk(location)
    experiences_list = await search_experiences(location, query, per_page=per_page)
    return {"weather": weather, "experiences": experiences_list}

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
        experiences_list = await search_experiences(location, "", per_page=6)
        titles = [x.get("title") for x in experiences_list]

        prompt = f"""
You are a travel assistant for {location}.
User preferences: budget={budget}, activity={activity}, duration={duration}, motivation={motivation}
Popular spots: {', '.join(titles)}

Create a 3-stop itinerary in format:

**Stop 1: [Activity]**
[Description]
**Stop 2: [Activity]**
[Description]
**Stop 3: [Activity]**
[Description]
"""
        raw = generate_zephyr_response(prompt)
        matches = re.findall(r"\*\*Stop \d: (.*?)\*\*\n(.*?)(?=\*\*Stop \d|$)", raw, re.DOTALL)
        stops = [{"title": m[0].strip(), "description": m[1].strip()} for m in matches] if matches else []
        return {"stops": stops or [{"title": "No data", "description": "Could not generate itinerary"}]}
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

