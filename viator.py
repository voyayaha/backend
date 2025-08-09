import httpx
from typing import Optional
from datetime import datetime, timedelta
import os

VIATOR_API_KEY = os.getenv("VIATOR_TOKEN")

async def search_viator_activities(query: str, location: str, checkin: Optional[str] = None, checkout: Optional[str] = None):
    try:
        start_date = checkin or datetime.today().strftime("%Y-%m-%d")
        end_date = checkout or (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")

        url = "https://api.viator.com/partner/products/search"

        headers = {
            "Accept": "application/json;version=2.0",
            "Accept-Language": "en-US",
            "Content-Type": "application/json",
            "exp-api-key": VIATOR_API_KEY
        }

        payload = {
            "filtering": {
                "text": f"{query} {location}",
                "startDate": start_date,
                "endDate": end_date
            },
            "pagination": {
                "start": 1,
                "count": 1
            },
            "currency": "USD"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

        products = result.get("data", [])
        if not products:
            return None

        product = products[0]
        return {
            "title": product.get("title", query),
            "description": product.get("description", f"Explore {query} in {location}."),
            "image": product.get("images", [{}])[0].get("url", ""),
            "rating": product.get("rating", 0),
            "price": product.get("fromPrice", {}).get("amountFormatted", "N/A"),
        }

    except Exception as e:
        print(f"Viator API Error: {e}")
        return None
