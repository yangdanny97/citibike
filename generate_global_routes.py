#!/usr/bin/env python3
import csv
import json
import datetime
from generate_routes import get_bike_route_geojson, API_KEY, route_cache

INFILE = "citibike_sampled_data.csv"
OUTFILE = "citibike_global_routes.geojson"

features = []
with open(INFILE) as f:
    reader = csv.DictReader(f)
    for row in reader:
        # skip same-station rides
        if row.get("start_station_name") == row.get("end_station_name"):
            continue
        try:
            slat = float(row["start_lat"])
            slng = float(row["start_lng"])
            elat = float(row["end_lat"])
            elng = float(row["end_lng"])
        except Exception:
            print("skipping invalid coords " + str((row.get("start_lat"), row.get("start_lng"), row.get("end_lat"), row.get("end_lng"))))
            continue

        key = ((slat, slng), (elat, elng))
        rev = (key[1], key[0])
        if key in route_cache:
            route = route_cache[key]
        elif rev in route_cache:
            route = route_cache[rev]
        else:
            route = get_bike_route_geojson((slat, slng), (elat, elng), API_KEY)

        try:
            started = datetime.datetime.fromisoformat(row["started_at"])
            ended = datetime.datetime.fromisoformat(row["ended_at"])
            duration_s = int((ended - started).total_seconds())
            route["properties"]["duration_s"] = duration_s
        except Exception:
            pass

        route["properties"]["origin"] = row.get("start_station_name")
        route["properties"]["destination"] = row.get("end_station_name")
        features.append(route)

result = {"type": "FeatureCollection", "features": features}
with open(OUTFILE, "w") as f:
    json.dump(result, f)
