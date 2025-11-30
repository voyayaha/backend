# experiences.py
import time
from typing import List, Dict, Any, Optional
from yelp_backend import yelp_search
from foursquare_backend import foursquare_search
from weather import get_weather_and_risk  # existing weather module

_CACHE: Dict[str, Dict] = {}
CACHE_TTL = 60 * 60  # 1 hour

def cache_get(key: str) -> Optional[Any]:
    rec = _CACHE.get(key)
    if not rec:
        return None
    if time.time() - rec["ts"] > CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return rec["val"]

def cache_set(key: str, val: Any):
    _CACHE[key] = {"val": val, "ts": time.time()}

def mark_indoor_outdoor(item: Dict[str, Any]) -> Dict[str, Any]:
    text = (item.get("title", "") + " " + " ".join(item.get("categories", []))).lower()
    indoor_kw = ["museum", "gallery", "spa", "cafe", "aquarium", "temple", "theatre", "indoor", "class"]
    outdoor_kw = ["park", "hike", "trek", "cruise", "beach", "sunset", "outdoor", "bike", "safari"]
    if any(k in text for k in indoor_kw):
        item["indoor"] = True
    elif any(k in text for k in outdoor_kw):
        item["indoor"] = False
    else:
        item["indoor"] = None
    return item

async def search_experiences(location: str, query: str = "", per_page: int = 6) -> List[Dict[str, Any]]:
    cache_key = f"experiences:{location.lower()}:{query}:{per_page}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Weather preference
    try:
        weather = await get_weather_and_risk(location)
        indoor_pref = weather.get("indoor_preferred", False)
    except Exception:
        indoor_pref = False

    # Yelp primary
    try:
        results = await yelp_search(location, query, per_page)
    except Exception:
        results = []

    # Foursquare fallback
    if not results:
        results = await foursquare_search(location, query, per_page)

    # Normalize & mark indoor/outdoor
    normalized = [mark_indoor_outdoor(r) for r in results]

    # Prefer matching weather
    preferred = []
    others = []
    for it in normalized:
        if indoor_pref and it.get("indoor") is True:
            preferred.append(it)
        elif (not indoor_pref) and it.get("indoor") is False:
            preferred.append(it)
        else:
            others.append(it)

    final_result = (preferred + others)[:per_page]
    cache_set(cache_key, final_result)
    return final_result
