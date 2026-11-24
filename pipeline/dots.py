"""Generate the dot layer: 1 dot = 5 ethnic-origin responses, placed on homes.

For each DA, each mapped origin gets count/5 dots (stochastic rounding). Dots
are placed on residential buildings in the DA, chosen with probability equal
to each building's share of the DA's 2021 population. A building's share is
its block's population split across the block's buildings by unit count.
Blocks with people but no addresses get random points inside the block.
Dots get a small random offset that grows with building size so towers read
as clusters instead of a single stacked point.

Writes site/data/dots.bin.gz and site/data/meta.json.
"""
import csv
import gzip
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely import points as shp_points

sys.path.insert(0, str(Path(__file__).parent))
from origin_groups import BROAD_ORDER, GROUPS  # noqa: E402
from palette import palette  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data/work"
OUT = ROOT / "site/data"
DOT = 5
rng = np.random.default_rng(2021)


def candidates(homes, blocks):
    """Per-DA arrays of candidate points (x, y, weight, jitter radius)."""
    h = homes.merge(blocks[["DBUID", "db_pop"]], on="DBUID")
    h = h[h.db_pop > 0]
    h["w"] = h.units * h.db_pop / h.groupby("DBUID").units.transform("sum")
    h["r"] = 4 + 1.5 * np.sqrt(h.units)
    cand = [h[["DAUID", "x", "y", "w", "r"]]]

    empty = blocks[(blocks.db_pop > 0) & ~blocks.DBUID.isin(h.DBUID)]
    rows = []
    for b in empty.itertuples():
        k = int(np.clip(b.db_pop // 10, 3, 400))
        xmin, ymin, xmax, ymax = b.geometry.bounds
        got = []
        for _ in range(50):
            px = rng.uniform(xmin, xmax, k * 4)
            py = rng.uniform(ymin, ymax, k * 4)
            inside = b.geometry.contains(shp_points(px, py))
            got += list(zip(px[inside], py[inside]))
            if len(got) >= k:
                break
        if not got:
            c = b.geometry.representative_point()
            got = [(c.x, c.y)]
        got = got[:k]
        for x, y in got:
            rows.append((b.DAUID, x, y, b.db_pop / len(got), 0.0))
    cand.append(pd.DataFrame(rows, columns=["DAUID", "x", "y", "w", "r"]))
    print(f"  {len(h):,} buildings + {len(rows):,} random points for {len(empty):,} blocks without addresses")
    return pd.concat(cand).groupby("DAUID")


def main():
    blocks = pd.read_parquet(WORK / "blocks.parquet")
    blocks = gpd.GeoDataFrame(blocks, geometry=gpd.GeoSeries.from_wkb(blocks.geometry), crs="EPSG:3347")
    homes = pd.read_parquet(WORK / "homes.parquet")
    das = set(blocks.DAUID)

    # Origins mapped at DA level, in legend order
    groups = list(csv.DictReader(open(ROOT / "data/origin_groups.csv")))
    sub_keys = list(GROUPS)
    origins = [g for g in groups if g["da_profile_id"]]
    code_to_idx = {int(g["da_profile_id"]): i for i, g in enumerate(origins)}

    counts = pd.read_csv(ROOT / "data/raw/da_profile.csv.gz", dtype={"dauid": str, "count": str, "symbol": str})
    counts = counts[counts.characteristic_id.isin(code_to_idx) & counts.dauid.isin(das)]
    counts["n"] = pd.to_numeric(counts["count"], errors="coerce")
    counts = counts[counts.n > 0]
    print(f"{counts.dauid.nunique():,} DAs with origin data, {int(counts.n.sum()):,} responses")

    cand = candidates(homes, blocks)
    xs, ys, os_ = [], [], []
    missing_da = 0
    for dauid, grp in counts.groupby("dauid"):
        n = np.floor(grp.n.values / DOT + rng.random(len(grp))).astype(int)
        if n.sum() == 0:
            continue
        try:
            c = cand.get_group(dauid)
        except KeyError:
            missing_da += 1
            continue
        p = c.w.values / c.w.values.sum()
        pick = rng.choice(len(c), size=n.sum(), p=p)
        ang = rng.uniform(0, 2 * np.pi, n.sum())
        rad = c.r.values[pick] * np.sqrt(rng.random(n.sum()))
        xs.append(c.x.values[pick] + rad * np.cos(ang))
        ys.append(c.y.values[pick] + rad * np.sin(ang))
        os_.append(np.repeat([code_to_idx[k] for k in grp.characteristic_id.values], n))
    x, y, o = np.concatenate(xs), np.concatenate(ys), np.concatenate(os_)
    print(f"{len(o):,} dots ({missing_da} DAs had no people to place)")

    lon, lat = Transformer.from_crs(3347, 4326, always_xy=True).transform(x, y)
    order = rng.permutation(len(o))  # random draw order: no group always on top
    lon, lat, o = lon[order], lat[order], o[order]
    bbox = [float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())]
    qx = np.round((lon - bbox[0]) / (bbox[2] - bbox[0]) * 65535).astype("<u2")
    qy = np.round((lat - bbox[1]) / (bbox[3] - bbox[1]) * 65535).astype("<u2")
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / "dots.bin.gz", "wb", compresslevel=9) as f:
        f.write(qx.tobytes() + qy.tobytes() + o.astype("u1").tobytes())

    broad_col, sub_col = palette()
    dots_per = np.bincount(o, minlength=len(origins))
    meta = {
        "count": int(len(o)), "bbox": bbox, "dot": DOT,
        "broads": [{"name": b, "color": broad_col[b]} for b in BROAD_ORDER],
        "subs": [{"name": s, "broad": BROAD_ORDER.index(b), "color": sub_col[(b, s)]} for b, s in sub_keys],
        "origins": [{"name": g["origin"], "sub": sub_keys.index((g["broad"], g["sub"])),
                     "dots": int(dots_per[i])} for i, g in enumerate(origins)],
        "unmapped": [{"name": g["origin"], "sub": sub_keys.index((g["broad"], g["sub"])),
                      "cma_responses": int(g["toronto_cma_responses"])}
                     for g in groups if not g["da_profile_id"] and int(g["toronto_cma_responses"]) > 0],
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {OUT / 'dots.bin.gz'} ({(OUT / 'dots.bin.gz').stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
