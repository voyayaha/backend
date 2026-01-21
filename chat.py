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
			
			if duration_days <= 1:
				experiences_per_day = 3   # half-day or full-day
			else:
				experiences_per_day = 2   # multi-day

			total_experiences = max(1, duration_days) * experiences_per_day


            prompt = f"""
You are a travel assistant. The user is visiting {data.location} between {data.checkin} and {data.checkout} ({duration_days} days).

Rules:
- If the trip is 1 day or less, suggest at least 3 experiences.
- If the trip is more than 1 day, suggest exactly 2 experiences per day.
- Total number of experiences must be {total_experiences}.

Generate a JSON array of daily experiences.

Each item in the array must be:
{{
  "title": "Marine Drive",
  "time": "9:00 am - 10:30 am",
  "description": "Walk along the sea during the misty morning."
}}

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
