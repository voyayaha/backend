# yelp_backend.py
import os
import httpx
from typing import List, Dict, Any

YELP_API_KEY = os.getenv("YELP_API_KEY")
YELP_BASE = "https://api.yelp.com/v3/businesses/search"

async def yelp_search(location: str, term: str = "", limit: int = 8) -> List[Dict[str, Any]]:
    """
    Async Yelp Fusion search. Returns a list of normalized dicts.
    """
    if not YELP_API_KEY:
        return []

    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    params = {
        "location": location,
        "term": term or "things to do",
        "limit": limit,
        "sort_by": "rating"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(YELP_BASE, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    out = []
    for b in data.get("businesses", []):
        out.append({
            "title": b.get("name"),
            "rating": b.get("rating"),
            "review_count": b.get("review_count"),
            "categories": [c.get("title") for c in b.get("categories", [])],
            "image": b.get("image_url"),
            "url": b.get("url"),
            "address": ", ".join(b.get("location", {}).get("display_address", [])),
            "source": "yelp"
        })
    return out
