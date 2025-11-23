"""Search local experiences via Viator Partner API (free affiliate key)"""
import os, httpx
from weather import get_weather_and_risk

VIATOR_BASE = "https://api.viator.com/partner/v2"
VIATOR_TOKEN = os.getenv("VIATOR_TOKEN")

HEADERS = {
    "exp-api-key": VIATOR_TOKEN,
    "Accept": "application/json"
}

async def search_experiences(location: str, query: str = "", date: str | None = None, per_page: int = 6):
    """
    Return a list of curated activities for a given city using Viator v2 API.
    Works globally — no numerical destId required.
    Applies weather-based indoor/outdoor filtering.
    """
    try:
        # Weather check → indoor/outdoor preference
        weather_data = await get_weather_and_risk(location)
        indoor = weather_data.get("indoor_preferred", False)

        # Build Viator v2 request (NO destId)
        endpoint = f"{VIATOR_BASE}/search/products"

        search_query = f"{location} {query}".strip()

        params = {
            "query": search_query,
            "currency": "USD",
            "sort": "RECOMMENDED",
            "topX": per_page
        }

        if date:
            params["startDate"] = date  # Only add date if provided

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(endpoint, params=params, headers=HEADERS)
            r.raise_for_status()
            data = r.json()

        results = data.get("products", [])

        # --- Weather filtering ---
        filtered = []
        for item in results:
            text = (
                (item.get("title") or "") + " " +
                (item.get("description") or "") + " " +
                (item.get("subtitle") or "")
            ).lower()

            # Indoor-friendly keywords
            indoor_keywords = ["museum", "cooking", "temple", "palace", "spa", "indoor", "class"]
            # Outdoor-friendly keywords
            outdoor_keywords = ["hiking", "sunset", "cruise", "bike", "safari", "outdoor", "kayak"]

            if indoor and any(k in text for k in indoor_keywords):
                filtered.append(item)
            elif not indoor and any(k in text for k in outdoor_keywords):
                filtered.append(item)

        # If filtering removed everything → fallback to first results
        if not filtered:
            return results[:per_page]

        return filtered[:per_page]

    except Exception as e:
        print("Experience error:", e)
        return []
