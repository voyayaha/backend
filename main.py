from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os
import re

from hotels import search_hotels
from social import scrape_social, get_trending_spots
from experiences import get_travel_recommendations
from llm import generate_llm_fallback
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
    return {"message": "Voyayaha API is running"}

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
def chat_experiences(
    location: str = Query(...),
    budget: str = "",
    activity: str = "",
    duration: str = "",
    motivation: str = "",
):
    # Fetch structured recommendations
    stops = get_travel_recommendations(location)

    if not stops:
        # If both Yelp + FS fail → LLM fallback
        llm_stops = generate_llm_fallback(location, budget, activity, duration, motivation)
        return {"stops": llm_stops}

    return {"stops": stops}



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


