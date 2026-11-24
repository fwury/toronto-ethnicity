"""Dissemination-area layer for the area breakdown panel.

* DA polygons for the Toronto CMA, with water (Lake Ontario, rivers, ponds)
  cut out using OpenStreetMap water from OpenFreeMap vector tiles, simplified
  for the web: site/data/areas.geojson.gz
* Per-DA census counts for every mapped origin (the published counts, not
  the dot counts), population, and municipality: site/data/areas.json.gz

Usage: python pipeline/areas.py
"""
import csv
import gzip
import json
import math
import sys
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import mapbox_vector_tile
import pandas as pd
import shapely
from shapely.geometry import shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data/work"
OUT = ROOT / "site/data"
Z = 12
UA = {"User-Agent": "toronto-ethnicity-map-pipeline/1.0"}


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def tile_range(bounds):
    lon0, lat0, lon1, lat1 = bounds
    n = 2 ** Z
    fx = lambda lon: int((lon + 180) / 360 * n)
    fy = lambda lat: int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return range(fx(lon0), fx(lon1) + 1), range(fy(lat1), fy(lat0) + 1)


def water(bounds):
    cache = WORK / "water.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    tj = json.loads(fetch("https://tiles.openfreemap.org/planet"))
    url = tj["tiles"][0]
    xs, ys = tile_range(bounds)
    n = 2 ** Z
    polys = []
    for tx in xs:
        for ty in ys:
            data = fetch(url.format(z=Z, x=tx, y=ty))
            layers = mapbox_vector_tile.decode(data, default_options={"y_coord_down": True})
            if "water" not in layers:
                continue
            ext = layers["water"]["extent"]

            def to_lonlat(x, y, z=None):
                lon = (tx + x / ext) / n * 360 - 180
                lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + y / ext) / n))))
                return lon, lat

            for f in layers["water"]["features"]:
                if f["properties"].get("class") == "swimming_pool":
                    continue
                g = shape(f["geometry"])
                if g.geom_type in ("Polygon", "MultiPolygon"):
                    polys.append(transform(lambda x, y, z=None: tuple(zip(*map(to_lonlat, x, y))), g))
        print(f"  water tiles: column {tx - xs.start + 1}/{len(xs)}", flush=True)
    w = gpd.GeoDataFrame(geometry=[unary_union(polys)], crs=4326).to_crs(3347)
    w.to_parquet(cache)
    return w


def main():
    gaf = pd.read_csv(ROOT / "data/raw/gaf_toronto.csv.gz", dtype=str, encoding="cp1252")
    gaf = gaf[gaf["CMAUID_RMRIDU"] == "535"]
    da_info = gaf.groupby("DAUID_ADIDU").agg(csd=("CSDNAME_SDRNOM", "first")).reset_index()
    da_info.columns = ["DAUID", "csd"]

    with zipfile.ZipFile(ROOT / "data/raw/lda_000a21a_e_toronto.zip") as z:
        z.extractall(WORK / "lda")
    das = gpd.read_file(WORK / "lda/lda_000a21a_e_toronto.shp", encoding="cp1252")[["DAUID", "geometry"]]
    das = das.merge(da_info, on="DAUID")
    print(f"{len(das):,} DAs in the Toronto CMA")

    w = water(das.to_crs(4326).total_bounds)
    wg = w.geometry.iloc[0].buffer(0)
    das["geometry"] = das.geometry.difference(wg)
    das["geometry"] = das.geometry.simplify(6, preserve_topology=True)
    das = das[~das.geometry.is_empty]
    das = das.to_crs(4326)
    das["geometry"] = shapely.set_precision(das.geometry.values, 1e-5)
    gj = json.loads(das[["DAUID", "geometry"]].to_json(drop_id=True))
    with gzip.open(OUT / "areas.geojson.gz", "wt", compresslevel=9) as f:
        json.dump(gj, f, separators=(",", ":"))

    # ---- counts
    groups = [g for g in csv.DictReader(open(ROOT / "data/origin_groups.csv")) if g["da_profile_id"]]
    code_to_idx = {int(g["da_profile_id"]): i for i, g in enumerate(groups)}
    prof = pd.read_csv(ROOT / "data/raw/da_profile.csv.gz", dtype={"dauid": str, "count": str, "symbol": str})
    prof = prof[prof.dauid.isin(set(das.DAUID))]
    prof["n"] = pd.to_numeric(prof["count"], errors="coerce")
    pop = prof[prof.characteristic_id == 1].set_index("dauid").n
    eo_total = prof[prof.characteristic_id == 1698].set_index("dauid").n
    supp = set(prof[(prof.characteristic_id == 1698) & (prof.symbol.fillna("") != "")].dauid)
    o = prof[prof.characteristic_id.isin(code_to_idx) & (prof.n > 0)]
    out = {}
    by_da = {k: g for k, g in o.groupby("dauid")}
    for d in das.itertuples():
        g = by_da.get(d.DAUID)
        c = [] if g is None else sorted(([code_to_idx[k], int(v)] for k, v in zip(g.characteristic_id, g.n)),
                                         key=lambda r: -r[1])
        p = pop.get(d.DAUID)
        e = eo_total.get(d.DAUID)
        out[d.DAUID] = {
            "m": d.csd,
            "p": None if pd.isna(p) else int(p),
            "e": None if (pd.isna(e) or d.DAUID in supp) else int(e),
            "c": c,
        }
    with gzip.open(OUT / "areas.json.gz", "wt", compresslevel=9) as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
    for name in ("areas.geojson.gz", "areas.json.gz"):
        print(f"wrote {name} ({(OUT / name).stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    sys.exit(main())
