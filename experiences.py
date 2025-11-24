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
    Fully compliant Viator v2 search.
    - Uses only VALID parameters
    - Works globally (any city, non-numeric)
    - Handles 500 errors gracefully
    """

    # Combine search terms
    q_full = f"{location} {query}".strip()

    # Build VALID Viator v2 parameters
    params = {
        "q": q_full,
        "currencyCode": "USD",
        "sortOrder": "RECOMMENDED",
        "page": 1,
        "pageSize": per_page
    }

    if date:
        params["startDate"] = date

    try:
        # Weather preference
        weather_data = await get_weather_and_risk(location)
        indoor = weather_data.get("indoor_preferred", False)

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(VIATOR_URL, params=params, headers=HEADERS)

            # Viator Internal Error
            if r.status_code >= 500:
                print("VIATOR 500 ERROR:", r.text)
                return []   # avoid crashing

            r.raise_for_status()
            data = r.json()

    except Exception as e:
        print("Experience error:", e)
        return []

    # Product extraction
    products = data.get("data", {}).get("products", [])
    if not products:
        return []

    # Weather filtering
    filtered = []
    indoor_words  = ["museum", "spa", "cooking", "temple", "indoor", "art", "gallery"]
    outdoor_words = ["cruise", "trek", "bike", "sunset", "safari", "outdoor"]

    for item in products:
        text = (
            (item.get("title") or "") + " " +
            (item.get("shortDescription") or "")
        ).lower()

        if indoor and any(w in text for w in indoor_words):
            filtered.append(item)
        elif not indoor and any(w in text for w in outdoor_words):
            filtered.append(item)

    # Fallback if filter becomes empty
    return filtered[:per_page] if filtered else products[:per_page]
