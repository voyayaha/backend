import requests

def get_aqi(city: str):
    url = "https://api.openaq.org/v2/latest"
    params = {
        "city": city,
        "limit": 1
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
    except Exception as e:
        return {
            "pm25": None,
            "health_note": "Unavailable",
            "error": "OpenAQ request failed"
        }

    # ✅ Defensive checks
    if "results" not in data or not data["results"]:
        return {
            "pm25": None,
            "health_note": "Unavailable",
            "note": "No AQI data for this city"
        }

    measurements = data["results"][0].get("measurements", [])

    pm25 = None
    for m in measurements:
        if m.get("parameter") == "pm25":
            pm25 = m.get("value")
            break

    return {
        "pm25": pm25,
        "unit": "µg/m³",
        "health_note": classify_pm25(pm25)
    }


def classify_pm25(pm25):
    if pm25 is None:
        return "Unknown"
    if pm25 <= 12:
        return "Good"
    if pm25 <= 35:
        return "Moderate"
    if pm25 <= 55:
        return "Unhealthy for sensitive groups"
    return "Unhealthy"
