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

    # ❌ REMOVE THE GET ROUTE COMPLETELY
    # DO NOT DEFINE @app.get("/chat/experiences") HERE

    # ==========================================
    # POST route – for future daily itineraries
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

Include at least 3 experiences per day.
Output only the JSON array — no extra text.
            """

            llm_output = generate_itinerary(prompt)

            if isinstance(llm_output, list):
                return {"response": llm_output}

            llm_output_cleaned = llm_output.strip()
            if llm_output_cleaned.startswith("```json"):
                llm_output_cleaned = llm_output_cleaned.split("```json")[-1].split("```")[0].strip()

            experiences = json.loads(llm_output_cleaned)

            return {"response": experiences}

        except Exception as e:
            return {"response": [], "error": f"Error generating experiences: {e}"}
