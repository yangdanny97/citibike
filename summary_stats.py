import json

METERS_PER_MILE = 1609.344


def summarize(features) -> None:
    total_miles = 0.0
    total_hours = 0.0
    count = 0

    max_distance = -1.0
    max_distance_feat = None

    max_speed = -1.0
    max_speed_feat = None

    for feat in features:
        props = feat["properties"]
        dist_m = props["distance_m"]
        dur_s = props["duration_s"]

        miles = float(dist_m) / METERS_PER_MILE
        hours = float(dur_s) / 3600.0

        total_miles += miles
        total_hours += hours
        count += 1

        if miles > max_distance:
            max_distance = miles
            max_distance_feat = props

        speed = miles / hours
        if speed > max_speed:
            max_speed = speed
            max_speed_feat = props

    avg_distance = total_miles / count
    avg_speed = total_miles / total_hours

    print(f"Avg est. distance: {avg_distance:.2f} miles")
    print(f"Avg est. speed: {avg_speed:.2f} mph")

    if max_distance_feat is not None:
        origin = max_distance_feat["origin"]
        destination = max_distance_feat["destination"]
        print(
            f"Largest est. distance: {max_distance:.2f} miles, {origin} -> {destination}"
        )

    if max_speed_feat is not None:
        origin = max_speed_feat["origin"]
        destination = max_speed_feat["destination"]
        print(f"Highest est. speed: {max_speed:.2f} mph, {origin} -> {destination}")


if __name__ == "__main__":
    with open("citibike_routes.geojson", "r", encoding="utf-8") as f:
        data = json.load(f)
    features = data["features"]
    summarize(features)
