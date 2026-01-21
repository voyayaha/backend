from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import json
from llm import generate_itinerary

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

    # ❌ DO NOT DEFINE GET /chat/experiences HERE
    # You are correctly using POST only

    # ==========================================
    # POST route – daily itineraries (FIXED)
    # ==========================================
    @app.post("/chat/experiences")
    async def chat_experiences_post(data: ExperienceRequest):
        try:
            checkin_date = datetime.strptime(data.checkin, "%Y-%m-%d")
            checkout_date = datetime.strptime(data.checkout, "%Y-%m-%d")
            duration_days = (checkout_date - checkin_date).days

            # 🔑 Total activities = days * 2
            total_items = max(duration_days * 2, 2)

            prompt = f"""
You are a travel assistant.

The user is visiting {data.location} between {data.checkin} and {data.checkout} ({duration_days} days).

Generate EXACTLY {total_items} travel activities.

Rules:
- Suggest 2 activities per day.
- Spread them logically across days.
- Each item must be a JSON object with:

{{
  "day": "Day 1",
  "title": "Marine Drive",
  "time": "9:00 am - 10:30 am",
  "description": "Walk along the sea during the misty morning."
}}

IMPORTANT:
- Output a JSON array with exactly {total_items} items.
- Do NOT add extra text.
- Do NOT add more or fewer items.
"""

            llm_output = generate_itinerary(prompt)

            # If LLM already returns list
            if isinstance(llm_output, list):
                # 🔑 Enforce correct count
                trimmed = llm_output[:total_items]
                return {"response": trimmed}

            # Else parse string output
            llm_output_cleaned = llm_output.strip()
            if llm_output_cleaned.startswith("```json"):
                llm_output_cleaned = llm_output_cleaned.split("```json")[-1].split("```")[0].strip()

            experiences = json.loads(llm_output_cleaned)

            # 🔑 Enforce correct count again
            experiences = experiences[:total_items]

            return {"response": experiences}

        except Exception as e:
            return {
                "response": [],
                "error": f"Error generating experiences: {e}"
            }
