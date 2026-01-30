def build_traveler_advice(traffic, crowd):
    advice = []

    if traffic.get("traffic_level") == "High":
        advice.append("Expect delays reaching popular attractions")

    if crowd.get("crowd_level") == "High":
        advice.append("This location is usually crowded at this time")

    if not advice:
        advice.append("Good time to visit with minimal delays")

    return " | ".join(advice)
