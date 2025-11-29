# experiences.py
import time
from typing import List, Dict, Any, Optional
from yelp_backend import yelp_search
from opentripmap import geocode_city, get_mindful_places
from weather import get_weather_and_risk  # your existing module

# simple in-memory TTL cache (process memory)
_CACHE: Dict[str, Dict] = {}
CACHE_TTL = 60 * 60  # seconds

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
    text = (item.get("title", "") + " " + (item.get("kinds", "") or "") + " " + (item.get("categories", "") or "")).lower()
    indoor_kw = ["museum", "gallery", "spa", "cafe", "aquarium", "temple", "theatre", "indoor", "class"]
    outdoor_kw = ["park", "hike", "trek", "cruise", "beach", "sunset", "outdoor", "bike", "safari"]
    if any(k in text for k in indoor_kw):
        item["indoor"] = True
    elif any(k in text for k in outdoor_kw):
        item["indoor"] = False
    else:
        item["indoor"] = None
    return item

async def search_experiences(location: str, query: str = "", date: Optional[str] = None, per_page: int = 6) -> List[Dict[str, Any]]:
    """
    Search experiences with Yelp first, fallback to OpenTripMap if needed.
    Returns normalized list of items.
    """
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
        yelp_results = await yelp_search(location, query, per_page)
    except Exception:
        yelp_results = []

    # If Yelp empty or insufficient, use OpenTripMap
    final: List[Dict[str, Any]] = []
    if yelp_results:
        final = yelp_results
    else:
        lat, lon = await geocode_city(location)
        if lat and lon:
            otm = await get_mindful_places(lat, lon, radius=3000, limit=per_page)
            final = otm
        else:
            final = []

    # Normalize & mark indoor/outdoor
    normalized = []
    for it in final:
        it = mark_indoor_outdoor(it)
        normalized.append(it)

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

    result = (preferred + others)[:per_page]
    cache_set(cache_key, result)
    return result
