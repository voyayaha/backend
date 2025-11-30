# experiences.py
import requests
from yelp_backend import yelp_search, YELP_API_KEY
import os

FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")

def foursquare_search(location):
    """
    Simple Foursquare search using Places API (Sandbox OK)
    """
    if not FOURSQUARE_API_KEY:
        print("⚠ No Foursquare API key found")
        return []

    # Geocode using Nominatim
    try:
        geo = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json"}
        ).json()

        if not geo:
            return []

        lat = geo[0]["lat"]
        lon = geo[0]["lon"]

    except:
        return []

    url = "https://api.foursquare.com/v3/places/search"

    headers = {
        "Authorization": FOURSQUARE_API_KEY,
        "accept": "application/json"
    }

    params = {
        "ll": f"{lat},{lon}",
        "radius": 8000,
        "limit": 20
    }

    try:
        r = requests.get(url, headers=headers, params=params)
        data = r.json()

        results = []
        if "results" in data:
            for place in data["results"]:
                results.append({
                    "title": place.get("name", "Unknown Place"),
                    "description": place.get("location", {}).get("formatted_address", "")
                })
        return results

    except Exception as e:
        print("Foursquare error:", e)
        return []


def get_travel_recommendations(location):
    """
    First try: Yelp
    Second try: Foursquare
    """
    results = []

    # 1. Try Yelp
    if YELP_API_KEY:
        yelp_results = yelp_search(location)
        if yelp_results:
            results.extend(yelp_results)

    # 2. Fallback → Foursquare
    if not results:
        fs_results = foursquare_search(location)
        if fs_results:
            results.extend(fs_results)

    return results
