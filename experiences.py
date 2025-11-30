import aiohttp
import os
from yelp_backend import search_yelp
from weather import get_weather_and_risk as get_weather



GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")


async def search_geoapify(location: str, query: str):
    """
    Geoapify fallback search for POIs
    """
    if not GEOAPIFY_API_KEY:
        return []

    url = "https://api.geoapify.com/v2/places"
    params = {
        "text": query,
        "filter": f"place:{location}",
        "bias": f"proximity:0,0",
        "limit": 10,
        "apiKey": GEOAPIFY_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as res:
            try:
                data = await res.json()
                features = data.get("features", [])
                results = [
                    {
                        "name": f["properties"].get("name", "Unknown"),
                        "category": f["properties"].get("categories", []),
                        "address": f["properties"].get("formatted"),
                        "lat": f["geometry"]["coordinates"][1],
                        "lon": f["geometry"]["coordinates"][0],
                    }
                    for f in features
                ]
                return results
            except:
                return []


async def get_combined_experiences(location: str, query: str):
    weather = await get_weather(location)
    yelp_results = await search_yelp(location, query)

    # Geoapify fallback
    geo_results = []
    if len(yelp_results) == 0:
        geo_results = await search_geoapify(location, query)

    return {
        "weather": weather,
        "yelp": yelp_results,
        "geoapify": geo_results
    }


