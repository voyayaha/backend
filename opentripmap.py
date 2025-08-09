import os, httpx
import pprint
from dotenv import load_dotenv

load_dotenv()
OTM_KEY = os.getenv("OPENTRIPMAP_API_KEY")
BASE = "https://api.opentripmap.com/0.1/en/places"



async def get_mindful_places(lat: float, lon: float, radius: int = 2000, limit: int = 5):
    params = {
        "apikey": OTM_KEY,
        "lat": lat,
        "lon": lon,
        "radius": radius,
        "limit": limit,
        "rate": 2
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/radius", params=params)
        r.raise_for_status()
        data = r.json()
        
        print("✅ OpenTripMap response:")
        pprint.pprint(data)

        features = data.get("features", [])
        if not features:
            print("⚠️ No features found in OpenTripMap response.")

        return [
            {
                "name": x["properties"]["name"],
                "type": x["properties"]["kinds"].split(",")[0],
                "xid": x["properties"]["xid"]
            }
            for x in features
            if x.get("properties", {}).get("name")  # filter out empty names
        ]
