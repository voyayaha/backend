import requests

def get_lat_lon_from_city(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    r = requests.get(url, params=params, timeout=10).json()

    if "results" not in r or not r["results"]:
        return None, None

    return r["results"][0]["latitude"], r["results"][0]["longitude"]


def get_weather_16_days(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "weathercode,"
            "rain_sum,"
            "windspeed_10m_max"
        ),
        "forecast_days": 16,
        "timezone": "auto"
    }

    r = requests.get(url, params=params, timeout=10).json()

    daily = r.get("daily", {})

    forecast = []
    for i in range(len(daily.get("time", []))):
        forecast.append({
            "date": daily["time"][i],
            "max_temp": daily["temperature_2m_max"][i],
            "min_temp": daily["temperature_2m_min"][i],
            "weather_code": daily["weathercode"][i],
            "rain_mm": daily["rain_sum"][i],
            "wind_kmph": daily["windspeed_10m_max"][i],
        })

    return forecast
