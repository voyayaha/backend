import httpx
from typing import Optional
from datetime import datetime, timedelta
import os

VIATOR_API_KEY = os.getenv("VIATOR_TOKEN")

BASE_HEADERS = {
    "Accept": "application/json",
    "exp-api-key": VIATOR_API_KEY
}

# ───────────────────────────────────────────────
# 1. Resolve ANY city name → destinationId (global)
# ───────────────────────────────────────────────
async def get_destination_id(city: str) -> Optional[str]:
    url = f"https://api.viator.com/partner/v2/search/geocodes?query={city}"

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=BASE_HEADERS, timeout=15)
            res.raise_for_status()
            data = res.json().get("data", [])

            if data and "destinationId" in data[0]:
                return data[0]["destinationId"]

        return None

    except Exception:
        return None


# ───────────────────────────────────────────────
# 2. Universal safe request wrapper (no crashes)
# ───────────────────────────────────────────────
async def safe_viator(url: str, method="GET", payload=None):
    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                res = await client.get(url, headers=BASE_HEADERS, timeout=20)
            else:
                res = await client.post(url, headers=BASE_HEADERS, json=payload, timeout=20)

            if res.status_code == 500:
                return {"data": [], "error": "viator_500"}

            res.raise_for_status()
            return res.json()

    except Exception:
        return {"data": [], "error": "viator_exception"}


# ───────────────────────────────────────────────
# 3. MAIN FUNCTION: Global Viator Activity Search
# ───────────────────────────────────────────────
async def search_viator_activities(
    query: str,
    location: str,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    limit: int = 6
):
    # Dates
    start_date = checkin or datetime.today().strftime("%Y-%m-%d")
    end_date = checkout or (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")

    # First try to fetch destinationId (best results)
    dest_id = await get_destination_id(location)

    if dest_id:
        # Use destinationId for most accurate search
        url = (
            f"https://api.viator.com/partner/v2/search/products?"
            f"destinationId={dest_id}&currency=USD&sort=RECOMMENDED&count={limit}"
        )
        data = await safe_viator(url)
    else:
        # Fallback: text search
        url = (
            f"https://api.viator.com/partner/v2/search/products?"
            f"query={location}&currency=USD&sort=RECOMMENDED&count={limit}"
        )
        data = await safe_viator(url)

    products = data.get("data", [])

    # If Viator returns nothing
    if not products:
        return []

    # Clean & standardize
    results = []
    for p in products:
        results.append({
            "title": p.get("title", ""),
            "description": p.get("description", f"Explore {location}."),
            "image": p.get("images", [{}])[0].get("url", ""),
            "rating": p.get("rating", None),
            "price": p.get("fromPrice", {}).get("amount", None),
            "priceFormatted": p.get("fromPrice", {}).get("amountFormatted", None),
            "webURL": p.get("webURL", "")
        })

    return results
