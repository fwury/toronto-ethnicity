"""Residential buildings in the Toronto CMA from the National Address Register.

Each NAR location (building) gets its number of residential addresses (every
apartment is its own address, so towers get many) and is assigned to the
dissemination block (DB) it falls in. Output: data/work/homes.parquet

Usage: python pipeline/homes.py /path/to/nar   (folder holding Addresses/Address_35_*.csv)
"""
import glob
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data/work"


def load_blocks():
    """DB polygons in the Toronto CMA with their 2021 population (EPSG:3347)."""
    gaf = pd.read_csv(ROOT / "data/raw/gaf_toronto.csv.gz", dtype=str, encoding="cp1252")
    gaf = gaf[gaf["CMAUID_RMRIDU"] == "535"]
    gaf = gaf.rename(columns={"DBUID_IDIDU": "DBUID", "DAUID_ADIDU": "DAUID"})
    gaf["db_pop"] = gaf["DBPOP2021_IDPOP2021"].astype(int)
    gaf["db_dwell"] = gaf["DBURDWELL2021_IDRHLOG2021"].astype(int)
    WORK.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ROOT / "data/raw/ldb_000a21a_e_toronto.zip") as z:
        z.extractall(WORK / "ldb")
    db = gpd.read_file(WORK / "ldb/ldb_000a21a_e_toronto.shp", encoding="cp1252")[["DBUID", "geometry"]]
    return db.merge(gaf[["DBUID", "DAUID", "db_pop", "db_dwell"]], on="DBUID")


def load_addresses(nar_dir, bounds):
    cols = ["LOC_GUID", "APT_NO_LABEL", "BG_X", "BG_Y", "BF_REPPOINT_X", "BF_REPPOINT_Y", "BU_USE"]
    xmin, ymin, xmax, ymax = bounds
    parts = []
    for f in sorted(glob.glob(str(Path(nar_dir) / "Addresses/Address_35_*.csv"))):
        for chunk in pd.read_csv(f, usecols=cols, dtype=str, encoding="utf-8-sig", chunksize=500_000):
            chunk = chunk[chunk["BU_USE"].isin(["1", "2"])]
            x = pd.to_numeric(chunk["BG_X"], errors="coerce")
            y = pd.to_numeric(chunk["BG_Y"], errors="coerce")
            keep = x.between(xmin, xmax) & y.between(ymin, ymax)
            parts.append(chunk[keep].assign(x=x[keep], y=y[keep]))
        print(f"  {Path(f).name}: {sum(len(p) for p in parts):,} residential addresses so far", flush=True)
    return pd.concat(parts)


def main(nar_dir):
    blocks = load_blocks()
    print(f"{len(blocks):,} blocks in Toronto CMA, population {blocks.db_pop.sum():,}")
    addr = load_addresses(nar_dir, blocks.total_bounds)
    homes = addr.groupby("LOC_GUID").agg(
        x=("x", "first"), y=("y", "first"), units=("LOC_GUID", "size"),
        bu_use=("BU_USE", "first")).reset_index()
    print(f"{len(addr):,} residential addresses in {len(homes):,} buildings")
    pts = gpd.GeoDataFrame(homes, geometry=gpd.points_from_xy(homes.x, homes.y), crs=blocks.crs)
    pts = gpd.sjoin(pts, blocks[["DBUID", "DAUID", "geometry"]], predicate="within", how="inner")
    pts = pts.drop(columns=["geometry", "index_right"])
    pts.to_parquet(WORK / "homes.parquet")
    covered = blocks.DBUID.isin(pts.DBUID)
    print(f"{len(pts):,} buildings inside the CMA; "
          f"{blocks[covered].db_pop.sum() / blocks.db_pop.sum():.1%} of population lives in blocks with addresses")
    blocks.to_parquet(WORK / "blocks.parquet")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/home/user/nar")
