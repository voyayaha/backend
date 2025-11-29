import os
import httpx

YELP_API_KEY = os.getenv("YELP_API_KEY")

BASE_URL = "https://api.yelp.com/v3/businesses/search"

headers = {
    "Authorization": f"Bearer {YELP_API_KEY}"
}

async def yelp_search(location: str, term: str = "things to do", limit: int = 10):
    """
    Search experiences using Yelp Fusion API.
    """
    if not YELP_API_KEY:
        return {"error": "Missing Yelp API key"}

    params = {
        "location": location,
        "term": term,
        "limit": limit,
        "sort_by": "rating"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(BASE_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for b in data.get("businesses", []):
            results.append({
                "title": b.get("name"),
                "rating": b.get("rating"),
                "review_count": b.get("review_count"),
                "categories": [c["title"] for c in b.get("categories", [])],
                "image": b.get("image_url"),
                "url": b.get("url"),
                "address": ", ".join(b.get("location", {}).get("display_address", [])),
            })

        return {"results": results}

    except httpx.HTTPStatusError as e:
        return {"error": f"Yelp error {e.response.status_code}", "detail": str(e)}

    except Exception as e:
        return {"error": "Yelp API failed", "detail": str(e)}
