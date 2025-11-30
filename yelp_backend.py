# yelp_backend.py
import requests
import os

YELP_API_KEY = os.getenv("YELP_API_KEY")

def yelp_search(location):
    if not YELP_API_KEY:
        print("⚠ No Yelp API key found")
        return []

    url = "https://api.yelp.com/v3/businesses/search"

    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {YELP_API_KEY}"},
            params={"location": location, "limit": 10}
        ).json()

        if "businesses" not in r:
            return []

        results = []
        for biz in r["businesses"]:
            results.append({
                "title": biz["name"],
                "description": biz.get("location", {}).get("address1", "")
            })
        return results

    except:
        return []
