# main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from experiences import search_experiences
from weather import get_weather_and_risk
from llm import generate_zephyr_response
import re

load_dotenv()

app = FastAPI(title="Voyayaha – AI Travel Concierge")

origins = ["*"]  # Adjust for your domains
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")

@app.get("/experiences")
async def experiences(location: str = Query(...), query: str = Query(""), per_page: int = 6):
    weather = await get_weather_and_risk(location)
    experiences_list = await search_experiences(location, query, per_page=per_page)
    return {"weather": weather, "experiences": experiences_list}

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
