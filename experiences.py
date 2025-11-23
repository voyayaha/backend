import os
import httpx
from weather import get_weather_and_risk

VIATOR_TOKEN = os.getenv("VIATOR_TOKEN")

HEADERS = {
    "exp-api-key": VIATOR_TOKEN,
    "Accept": "application/json"
}

VIATOR_URL = "https://api.viator.com/partner/v2/search/products"


async def search_experiences(location: str, query: str = "", date: str | None = None, per_page: int = 6):
    """
    Fully corrected Viator v2 search:
    - Uses ONLY valid parameters
    - Fully global (no destId)
    - Weather-filtered
    """

    try:
        # Weather logic (optional)
        weather_data = await get_weather_and_risk(location)
        indoor = weather_data["indoor_preferred"]

        # CORRECT v2 PARAMETERS
        params = {
            "q": f"{location} {query}".strip(),
            "currencyCode": "USD",
            "sortOrder": "RECOMMENDED",
            "page": 1,
            "pageSize": per_page
        }

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(VIATOR_URL, params=params, headers=HEADERS)

            # If Viator server error → return safe empty list
            if r.status_code >= 500:
                print("VIATOR 500 ERROR:", r.text)
                return []

            r.raise_for_status()
            data = r.json()

        products = data.get("data", {}).get("products", [])
        if not products:
            return []

        # Weather-based filtering
        filtered = []
        for item in products:
            text = (
                item.get("title", "") +
                item.get("shortDescription", "")
            ).lower()

            if indoor:
                if any(w in text for w in ["museum", "indoor", "spa", "cooking", "temple", "art"]):
                    filtered.append(item)
            else:
                if any(w in text for w in ["trek", "cruise", "outdoor", "bike", "sunset", "safari"]):
                    filtered.append(item)

        return filtered[:per_page] if filtered else products[:per_page]

    except Exception as e:
        print("Experience error:", e)
        return []
