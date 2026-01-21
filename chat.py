from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime
import json

from llm import generate_itinerary
from experiences import get_combined_experiences  # 🔑 real data + weather

# Only needed if run standalone
app = FastAPI()

# -----------------------------
# Models
# -----------------------------

class ExperienceRequest(BaseModel):
    location: str
    checkin: str  # "2025-08-04"
    checkout: str

# -----------------------------
# Route registration
# -----------------------------

def register_chat_routes(app: FastAPI):

    # ==========================================
    # 1️⃣ GET route – used by your current frontend
    # ==========================================
    @app.get("/chat/experiences")
    async def chat_experiences_get(
        location: str = Query(...),
        budget: str = "",
        activity: str = "",
        duration: str = "",
        motivation: str = ""
    ):
        """
        Returns:
        - total items = days * 2 (if multiday)
        - uses weather + Yelp + Geoapify
        - NO generic Explore / Food Walk / Heritage
        """

        # 1️⃣ Decide how many items to return
        def get_item_limit(duration: str):
            if not duration or duration == "full_day":
                return 3
            try:
                # expected formats: "2_days", "3_days"
                days = int(duration.split("_")[0])
                return days * 2
            except:
                return 3

        limit = get_item_limit(duration)

        # 2️⃣ Fetch real nearby experiences with weather logic
        try:
            stops_data = await get_combined_experiences(location, activity or "tourist")
            yelp_results = stops_data.get("yelp", [])
            geo_results = stops_data.get("geoapify", [])
            final_stops = yelp_results + geo_results
        except Exception as e:
            print("❌ Experience fetch failed:", e)
            final_stops = []

        # 3️⃣ If we got real places → format them
        cleaned = []

        for item in final_stops[:limit]:
            cleaned.append({
                "title": item.get("name", "Popular Place"),
                "description": (
                    f"Visit {item.get('name')} and enjoy this place in {location}."
                )
            })

        # 4️⃣ Hard fallback if APIs return nothing
        if not cleaned:
            cleaned = [
                {
                    "title": f"City Center of {location}",
                    "description": "Walk around the main city area and explore landmarks."
                },
                {
                    "title": f"Local Market in {location}",
                    "description": "Try local food and explore street markets."
                },
                {
                    "title": f"Famous Attraction in {location}",
                    "description": "Visit one of the most well-known places in the city."
                }
            ][:limit]

        return {"stops": cleaned}

    # ==========================================
    # 2️⃣ POST route – for daily itinerary (LLM)
    # ==========================================
    @app.post("/chat/experiences")
    async def chat_experiences_post(data: ExperienceRequest):
        try:
            checkin_date = datetime.strptime(data.checkin, "%Y-%m-%d")
            checkout_date = datetime.strptime(data.checkout, "%Y-%m-%d")
            duration_days = (checkout_date - checkin_date).days

            prompt = f"""
You are a travel assistant. The user is visiting {data.location} between {data.checkin} and {data.checkout} ({duration_days} days).

Generate a JSON array of daily experiences.

Each item in the array must be:
{{
  "title": "Marine Drive",
  "time": "9:00 am - 10:30 am",
  "description": "Walk along the sea during the misty morning."
}}

Include at least 2 experiences per day.
Total items must be exactly {duration_days * 2}.
Output only the JSON array — no extra text.
            """

            llm_output = generate_itinerary(prompt)

            # If LLM already returns JSON list
            if isinstance(llm_output, list):
                return {"response": llm_output}

            # Else try parsing
            llm_output_cleaned = llm_output.strip()
            if llm_output_cleaned.startswith("```json"):
                llm_output_cleaned = llm_output_cleaned.split("```json")[-1].split("```")[0].strip()

            experiences = json.loads(llm_output_cleaned)

            return {"response": experiences}

        except Exception as e:
            return {"response": [], "error": f"Error generating experiences: {e}"}
