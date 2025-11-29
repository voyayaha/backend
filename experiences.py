import os
import requests
from flask import Blueprint, request, jsonify

experiences_bp = Blueprint("experiences", __name__)

OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")
VIATOR_KEY = os.getenv("VIATOR_API_KEY")  # Optional


# ----------------------------- HELPERS -----------------------------

def safe_json(response):
    """Avoid JSON decode errors."""
    try:
        return response.json()
    except Exception:
        return None


# ----------------------------- OPENTRIPMAP -----------------------------

def fetch_opentripmap(city):
    url = "https://api.opentripmap.com/0.1/en/places/geoname"
    params = {
        "apikey": OPENTRIPMAP_API_KEY,
        "name": city
    }
    r = requests.get(url, params=params)

    data = safe_json(r)
    if not data or "lat" not in data:
        return []

    lat, lon = data["lat"], data["lon"]

    list_url = "https://api.opentripmap.com/0.1/en/places/radius"
    params = {
        "apikey": OPENTRIPMAP_API_KEY,
        "radius": 5000,
        "lon": lon,
        "lat": lat,
        "limit": 20
    }
    r = requests.get(list_url, params=params)
    data = safe_json(r)

    if not data:
        return []

    return [
        {
            "name": p.get("name", "Unknown"),
            "category": p.get("kinds"),
            "source": "OpenTripMap"
        }
        for p in data.get("features", [])
    ]


# ----------------------------- YELP -----------------------------

def fetch_yelp(city):
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    url = "https://api.yelp.com/v3/businesses/search"

    params = {"location": city, "limit": 20}

    r = requests.get(url, headers=headers, params=params)
    data = safe_json(r)

    if not data or "businesses" not in data:
        return []

    return [
        {
            "name": b["name"],
            "rating": b.get("rating"),
            "location": ", ".join(b["location"]["display_address"]),
            "image": b.get("image_url"),
            "source": "Yelp"
        }
        for b in data["businesses"]
    ]


# ----------------------------- VIATOR (OPTIONAL) -----------------------------

def fetch_viator(city):
    if not VIATOR_KEY:
        return []

    url = "https://viatorapi.viator.com/v1/taxonomy/locations/search"
    headers = {"api-key": VIATOR_KEY}

    params = {"text": city}

    r = requests.get(url, headers=headers, params=params)
    data = safe_json(r)

    if not data:
        return []

    return [
        {
            "name": item.get("title"),
            "price": item.get("fromPrice"),
            "rating": item.get("rating"),
            "image": item.get("imageURL"),
            "source": "Viator"
        }
        for item in data.get("data", [])
    ]


# ----------------------------- MAIN ROUTE -----------------------------

@experiences_bp.route("/experiences", methods=["GET"])
def get_experiences():
    city = request.args.get("city")

    if not city:
        return jsonify({"error": "Missing 'city' parameter"}), 400

    try:
        results = []

        # Always try OpenTripMap
        results += fetch_opentripmap(city)

        # Try Yelp if key exists
        if YELP_API_KEY:
            results += fetch_yelp(city)

        # Optional
        if VIATOR_KEY:
            results += fetch_viator(city)

        if not results:
            return jsonify({"message": "No results found"}), 200

        return jsonify({"experiences": results})

    except Exception as e:
        return jsonify({"response": f"Error generating experiences: {str(e)}"}), 500
