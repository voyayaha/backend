import requests

def get_weather_16_days(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,weathercode",
        "forecast_days": 16,
        "timezone": "auto"
    }

    r = requests.get(url, params=params).json()

    forecast = []
    for i in range(len(r["daily"]["time"])):
        forecast.append({
            "date": r["daily"]["time"][i],
            "max_temp": r["daily"]["temperature_2m_max"][i],
            "min_temp": r["daily"]["temperature_2m_min"][i],
            "weather_code": r["daily"]["weathercode"][i]
        })

    return forecast
