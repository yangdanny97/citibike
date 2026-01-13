"""
Rasterize routes from citibike_routes.geojson into a count GeoTIFF & a PNG

Creates a raster (default 2000x2000) where each pixel's value is the
number of route geometries that pass through that pixel.

Usage:
python3 raster.py --geojson citibike_routes.geojson
"""

from pathlib import Path
import json
import argparse

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize
from shapely.geometry import shape, LineString, MultiLineString
from pyproj import Transformer
import math
import matplotlib
from PIL import Image


def load_geometries(geojson_path):
    data = json.loads(Path(geojson_path).read_text())
    geoms = []
    for feat in data.get("features", []):
        geom = feat.get("geometry")
        if geom is None:
            continue
        try:
            g = shape(geom)
        except Exception:
            continue
        if g.is_empty:
            continue
        geoms.append(g)
    return geoms


def jitter_geom(geom, max_meters, rng, to_m_transformer, to_deg_transformer):
    """Return a copy of `geom` with each point randomly displaced up to
    `max_meters` meters. Uses the provided pyproj Transformers to convert
    to/from a meter-based CRS (EPSG:3857).
    """
    if max_meters <= 0:
        return geom

    to_m = to_m_transformer.transform
    to_deg = to_deg_transformer.transform

    def jitter_coords(coords):
        out = []
        for x, y in coords:
            xm, ym = to_m(x, y)
            r = max_meters * math.sqrt(rng.random())
            theta = rng.random() * 2 * math.pi
            xm2 = xm + r * math.cos(theta)
            ym2 = ym + r * math.sin(theta)
            x2, y2 = to_deg(xm2, ym2)
            out.append((x2, y2))
        return out

    t = geom.geom_type
    if t == "LineString":
        return LineString(jitter_coords(list(geom.coords)))
    if t == "MultiLineString":
        return MultiLineString([
            LineString(jitter_coords(list(part.coords))) for part in geom.geoms
        ])
    assert False, f"Unsupported geometry type: {t}"


def compute_bounds(geoms):
    xs = []
    ys = []
    for g in geoms:
        minx, miny, maxx, maxy = g.bounds
        xs.extend([minx, maxx])
        ys.extend([miny, maxy])
    return min(xs), min(ys), max(xs), max(ys)


def rasterize_counts(geoms, bounds, width=2000, height=2000):
    minx, miny, maxx, maxy = bounds
    transform = from_bounds(minx, miny, maxx, maxy, width, height)

    counts = np.zeros((height, width), dtype=np.uint32)

    # rasterize each route into a temporary uint8 array and accumulate
    for i, g in enumerate(geoms, 1):
        try:
            arr = rasterize(
                [(g, 1)],
                out_shape=(height, width),
                transform=transform,
                fill=0,
                dtype="uint8",
                all_touched=True,
            )
        except Exception:
            continue
        counts += arr.astype(np.uint32)
    return counts, transform


def write_geotiff(path, counts, transform, crs="EPSG:4326"):
    height, width = counts.shape
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint32",
        "crs": crs,
        "transform": transform,
        "compress": "lzw",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(counts, 1)


def write_colormap_png(path, counts, cmap_name="inferno"):
    """Write a PNG using histogram-equalized values mapped through a
    matplotlib colormap (`cmap_name`). Zeros are kept mapped to 0 (lowest
    color).
    """
    h, w = counts.shape
    flat = counts.ravel()

    # ignore zeros when building histogram equalization (so empty pixels
    # don't dominate the mapping)
    mask = flat > 0
    if mask.sum() == 0:
        # all zeros -> output a black image
        img = np.zeros((h, w, 3), dtype=np.uint8)
        Image.fromarray(img, mode="RGB").save(path)
        return

    vals = flat[mask].astype(np.int64)
    maxv = vals.max()

    # build histogram and CDF
    hist = np.bincount(vals, minlength=maxv + 1)
    cdf = hist.cumsum().astype(np.float64)
    cdf = cdf / cdf[-1]

    # mapping function: for a value v>0, normalized = cdf[v]
    mapped = np.zeros_like(flat, dtype=np.float32)
    mapped[mask] = cdf[flat[mask]]
    mapped = mapped.reshape((h, w))

    # pyrefly: ignore
    cmap = matplotlib.colormaps.get_cmap(cmap_name)

    # pyrefly: ignore
    rgba = cmap(mapped)  # returns floats in [0,1], shape (h,w,4)
    rgb = (rgba[..., :3] * 255).astype(np.uint8)

    Image.fromarray(rgb, mode="RGB").save(path)


def main():
    p = argparse.ArgumentParser(
        description="Rasterize routes to a count GeoTIFF.")
    p.add_argument("--geojson", default="citibike_routes.geojson",
                   help="Routes GeoJSON file")
    p.add_argument("--out", default="citibike_raster.tif",
                   help="Output GeoTIFF path")
    p.add_argument("--width", type=int, default=2000,
                   help="Raster width in pixels")
    p.add_argument("--height", type=int, default=2000,
                   help="Raster height in pixels")
    p.add_argument("--cmap", type=str, default="inferno",
                   help="Matplotlib colormap name to use for PNG (e.g. inferno, viridis)")
    p.add_argument("--jitter", type=float, default=0.0,
                   help="Max jitter per point in meters (default 0)")
    args = p.parse_args()

    geojson_path = Path(args.geojson)
    if not geojson_path.exists():
        raise SystemExit(f"GeoJSON file not found: {geojson_path}")

    geoms = load_geometries(geojson_path)
    if not geoms:
        raise SystemExit("No geometries found in GeoJSON.")

    # apply jitter to geometry vertices if requested
    if getattr(args, "jitter", 0) and args.jitter > 0:
        rng = np.random.default_rng()
        to_m_t = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        to_deg_t = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        jittered = []
        for g in geoms:
            try:
                jittered.append(jitter_geom(g, args.jitter, rng, to_m_t, to_deg_t))
            except Exception:
                jittered.append(g)
        geoms = jittered

    bounds = compute_bounds(geoms)

    counts, transform = rasterize_counts(
        geoms, bounds, width=args.width, height=args.height
    )

    write_geotiff(args.out, counts, transform)
    # also emit a bucketed PNG next to the output GeoTIFF
    out_png = Path(args.out).with_suffix('.png')
    try:
        write_colormap_png(out_png, counts, cmap_name=args.cmap)
        print(f"Wrote raster with shape {counts.shape} to {args.out} and PNG to {out_png} (cmap={args.cmap})")
    except Exception as e:
        print(f"Wrote raster to {args.out}. Failed to write PNG: {e}")


if __name__ == "__main__":
    main()
