from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from urllib.parse import unquote
import httpx
from dotenv import load_dotenv
import os
import copy

from hotels import search_hotels
from social import get_youtube_posts, get_reddit_posts
from experiences import get_combined_experiences
from llm import generate_itinerary
from weather import get_weather_and_risk
from pydantic import BaseModel
from typing import Optional
import json

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

class ExperienceRequest(BaseModel):
    location: str
    budget: Optional[str] = ""
    activity: Optional[str] = ""
    duration: str                # half_day | full_day | multi_day
    motivation: Optional[str] = ""
    num_days: Optional[int] = 1  # only used if multi_day


# -----------------------------
# CHAT / FRONTEND RECOMMENDATIONS
# -----------------------------

@app.post("/chat/experiences")
async def chat_experiences_post(data: ExperienceRequest):
    try:
        location = data.location
        budget = data.budget or ""
        activity = data.activity or ""
        duration = data.duration
        motivation = data.motivation or ""
        num_days = data.num_days or 1

        # 🧠 Decide experiences per day
        if duration in ["half_day", "full_day"]:
            experiences_per_day = 3
            days = 1
        else:
            experiences_per_day = 2
            days = max(1, num_days)

        total_experiences = days * experiences_per_day

        print("RECEIVED:", data)
        print("TOTAL EXPERIENCES:", total_experiences)

        prompt = f"""
You are Voyayaha AI Travel Guide.

The user is visiting: {location}

User preferences:
Budget: {budget}
Activity: {activity}
Motivation: {motivation}
Trip duration: {days} days

Your task:
Generate a multi-day itinerary in CITY GUIDE style.

Rules:
- For each day, generate exactly {experiences_per_day} recommendations.
- Total items must be exactly {total_experiences}.
- Each item MUST include:
    - day: day number (1, 2, 3...)
    - title: short heading for that experience block
    - intro: 1–2 lines describing what people enjoy
    - top_places: array of exactly 3 objects:
        - name
        - tip

Example format:

[
  {{
    "day": 1,
    "title": "Bangkok Relaxation Day",
    "intro": "Unwind in Bangkok’s green and wellness spots.",
    "top_places": [
      {{"name": "Lumphini Park", "tip": "Relax with a walk and lake views."}},
      {{"name": "Suan Rot Fai Park", "tip": "Enjoy gardens and cycling tracks."}},
      {{"name": "Mandara Spa", "tip": "Rejuvenate with a traditional Thai massage."}}
    ]
  }}
]

IMPORTANT:
- Use REAL places in {location}.
- Respect indoor vs outdoor based on common sense.

Return ONLY valid JSON array. No extra text.
"""


        llm_output = generate_itinerary(prompt)

        # Parse LLM output safely
        if isinstance(llm_output, list):
            experiences = llm_output
        else:
            cleaned = llm_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned.split("```json")[-1].split("```")[0].strip()

            experiences = json.loads(cleaned)

        # 🔒 Enforce exact count
        if len(experiences) > total_experiences:
            experiences = experiences[:total_experiences]
        elif len(experiences) < total_experiences:
            last = experiences[-1] if experiences else {
                "day": 1,
				"title": f"Explore {location}",
				"intro": f"Discover more of {location}.",
				"top_places": []
            }
            while len(experiences) < total_experiences:
                new_item = copy.deepcopy(last)
    			new_item["title"] = f"{last['title']} (More ideas)"
    			experiences.append(new_item)

        # ✅ Match frontend expectation
        return {"stops": experiences}

    except Exception as e:
        print("ERROR in /chat/experiences:", e)
        return {"stops": [], "error": str(e)}

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












