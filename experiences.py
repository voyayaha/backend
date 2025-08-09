"""Search local experiences via Viator Partner API (free affiliate key)"""
import os, httpx
from weather import get_weather_and_risk

VIATOR_BASE = "https://api.viator.com/partner/v1"
VIATOR_TOKEN = os.getenv("VIATOR_TOKEN")
HEADERS = {
    "exp-api-key": VIATOR_TOKEN,
    "Content-Type": "application/json"
}

async def search_experiences(location: str, query: str = "", date: str | None = None, per_page: int = 6):
    """Return a list of curated activities for a city or landmark based on weather (indoor/outdoor)."""
    try:
        # Fetch weather to decide indoor/outdoor
        weather_data = await get_weather_and_risk(location)
        indoor = weather_data["indoor_preferred"]

        # Build query
        endpoint = f"{VIATOR_BASE}/product/search"
        params = {
            "destId": location,  # Assumes numeric Viator destination ID
            "keyword": query,
            "startDate": date,
            "topX": per_page,
            "currencyCode": "USD",
            "sortOrder": "RECOMMENDED"
        }

        async with httpx.AsyncClient(timeout=10) as client:
            # First attempt with destId
            r = await client.get(endpoint, params=params, headers=HEADERS)
            if r.status_code == 400:
                params.pop("destId")  # Fallback to keyword-only
                r = await client.get(endpoint, params=params, headers=HEADERS)

            r.raise_for_status()
            data = r.json()
            results = data.get("data", {}).get("products", [])

            # Filter based on weather
            filtered = []
            for item in results:
                text = (item.get("title", "") + item.get("shortDescription", "")).lower()
                if indoor and any(w in text for w in ["museum", "cooking", "temple", "palace", "indoor"]):
                    filtered.append(item)
                elif not indoor and any(w in text for w in ["hiking", "sunset", "cruise", "bike", "safari", "outdoor"]):
                    filtered.append(item)

            return filtered[:per_page] if filtered else results[:per_page]

    except Exception as e:
        print("Experience error:", e)
        return []
