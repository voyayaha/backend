import os
import httpx
from weather import get_weather_and_risk

YELP_KEY = os.getenv("YELP_API_KEY")
OTM_KEY = os.getenv("OPENTRIPMAP_API_KEY")

YELP_URL = "https://api.yelp.com/v3/businesses/search"
OTM_GEOCODE_URL = "https://api.opentripmap.com/0.1/en/places/geoname"
OTM_RADIUS_URL = "https://api.opentripmap.com/0.1/en/places/radius"


# ──────────────────────────────────────────────
# Helper: Convert city name → lat/lon via OTM
# ──────────────────────────────────────────────
async def geocode_city(city: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            OTM_GEOCODE_URL,
            params={"name": city, "apikey": OTM_KEY}
        )
        data = r.json()
        return data.get("lat"), data.get("lon")


# ──────────────────────────────────────────────
# Experience Search (Yelp + OpenTripMap)
# ──────────────────────────────────────────────
async def search_experiences(location: str, query: str = "", date: str | None = None, limit: int = 6):
    """
    Replacement for Viator.
    1. Yelp Fusion → places, activities, food, experiences
    2. Falls back to OpenTripMap if Yelp returns nothing
    """

    # Weather preference for filtering
    weather = await get_weather_and_risk(location)
    indoor_preferred = weather.get("indoor_preferred", False)

    # ────────────────────────────────
    # Step 1: Yelp Fusion search
    # ────────────────────────────────
    try:
        headers = {"Authorization": f"Bearer {YELP_KEY}"}

        params = {
            "location": location,
            "term": query if query else "things to do",
            "sort_by": "best_match",
            "limit": limit
        }

        async with httpx.AsyncClient(timeout=12) as client:
            yelp_response = await client.get(YELP_URL, headers=headers, params=params)
            yelp_response.raise_for_status()
            yelp_data = yelp_response.json()

        businesses = yelp_data.get("businesses", [])

        # Weather-based filtering
        indoor_keywords = ["museum", "spa", "cafe", "gallery", "indoor"]
        outdoor_keywords = ["park", "hike", "trek", "outdoor", "beach"]

        def matches_weather(biz):
            name = biz.get("name", "").lower()
            cats = " ".join([c["title"].lower() for c in biz.get("categories", [])])

            text = f"{name} {cats}"

            if indoor_preferred:
                return any(w in text for w in indoor_keywords)
            else:
                return any(w in text for w in outdoor_keywords)

        filtered = [b for b in businesses if matches_weather(b)]

        if filtered:
            return [
                {
                    "title": b["name"],
                    "rating": b.get("rating", None),
                    "address": ", ".join(b["location"].get("display_address", [])),
                    "image": b.get("image_url", ""),
                    "categories": [c["title"] for c in b.get("categories", [])],
                    "source": "Yelp"
                }
                for b in filtered[:limit]
            ]

        # Fallback: return top results (no weather match)
        if businesses:
            return [
                {
                    "title": b["name"],
                    "rating": b.get("rating", None),
                    "address": ", ".join(b["location"].get("display_address", [])),
                    "image": b.get("image_url", ""),
                    "categories": [c["title"] for c in b.get("categories", [])],
                    "source": "Yelp"
                }
                for b in businesses[:limit]
            ]

    except Exception as e:
        print("Yelp error:", e)

    # ────────────────────────────────
    # Step 2: OpenTripMap fallback
    # ────────────────────────────────
    try:
        lat, lon = await geocode_city(location)

        if not lat:
            return []

        async with httpx.AsyncClient(timeout=12) as client:
            radius_resp = await client.get(
                OTM_RADIUS_URL,
                params={
                    "radius": 3000,
                    "lon": lon,
                    "lat": lat,
                    "limit": limit,
                    "apikey": OTM_KEY
                }
            )
            radius_resp.raise_for_status()
            items = radius_resp.json().get("features", [])

        results = []
        for item in items:
            props = item.get("properties", {})
            results.append({
                "title": props.get("name"),
                "kind": props.get("kinds", ""),
                "source": "OpenTripMap",
            })

        return results[:limit]

    except Exception as e:
        print("OpenTripMap error:", e)
        return []

