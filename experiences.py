"""
Unified global experiences search using the new Viator API wrapper.
Automatically applies weather-based indoor/outdoor filtering.
"""

import os
from typing import Optional
import httpx

from weather import get_weather_and_risk
from viator import search_viator_activities  # <-- use the new global-safe wrapper


async def search_experiences(
    location: str,
    query: str = "",
    date: Optional[str] = None,
    per_page: int = 6
):
    """
    Returns curated experiences for any city worldwide.
    Uses the improved 'search_viator_activities' function (destinationId → text fallback).
    Safe for all countries and all city spellings.
    """

    try:
        # 1. Get indoor/outdoor preference from weather module
        weather = await get_weather_and_risk(location)
        indoor_preferred = weather.get("indoor_preferred", False)

        # 2. Fetch activities (robust global method)
        viator_results = await search_viator_activities(
            query=query,
            location=location,
            checkin=date,
            checkout=date,
            limit=per_page
        )

        if not viator_results:
            return []

        # 3. Weather-aware filtering
        indoor_keywords = ["museum", "temple", "palace", "spa", "cafe", "aquarium", "gallery", "indoor"]
        outdoor_keywords = ["hiking", "sunset", "trek", "cruise", "safari", "beach", "bike", "kayak", "outdoor"]

        def is_indoor(item):
            text = (
                (item.get("title", "") or "") + " " +
                (item.get("description", "") or "")
            ).lower()
            return any(k in text for k in indoor_keywords)

        def is_outdoor(item):
            text = (
                (item.get("title", "") or "") + " " +
                (item.get("description", "") or "")
            ).lower()
            return any(k in text for k in outdoor_keywords)

        filtered = []
        for item in viator_results:
            if indoor_preferred and is_indoor(item):
                filtered.append(item)
            elif not indoor_preferred and is_outdoor(item):
                filtered.append(item)

        # 4. Fallback if filtering yields nothing
        if not filtered:
            return viator_results[:per_page]

        return filtered[:per_page]

    except Exception as e:
        print("Experience error:", e)
        return []
