# citibike

Visualizing my citibike ride history + a sample of global citibike rides in the style of a strava heatmap.

How to visualize your personal citibike data:

1. Download your data from the citibike website following the instructions here: https://github.com/fhoffa/code_snippets/tree/master/baywheels
2. Get a Google API key, and run `generate_routes.py` to use the Google Maps Routing API to find approximate the routes between station pairs
3. Run `raster.py` to generate a raster heatmap (see `citibike_raster.png` for an example), or `python3 -m http.server` + open `jitter.html` in your browser to view a SVG heatmap with configurable jitter.

How to visualize global citibike data:

1. Download the dataset of choice from here: https://citibikenyc.com/system-data
2. Run `sample_global_data.py` to extract a random sample of rides (I don't recommend more than 10k rides, because the Google Maps API is only free for the first 10k calls a month)
3. Get a Google API key, and run `generate_global_routes.py` to use the Google Maps Routing API to find approximate the routes between station pairs.
4. Run `raster.py` to generate a raster heatmap (see `citibike_global_raster.png` for an example), or `python3 -m http.server` + open `jitter_global.html` in your browser to view a SVG heatmap with configurable jitter.
