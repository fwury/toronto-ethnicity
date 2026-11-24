#!/usr/bin/env python3
"""Cut the huge 2021 Census files down to the Toronto CMA area.

Run this on your own computer, in the folder that holds the downloaded files.
It needs only Python 3.8+ (no extra packages) and streams the 8.8 GB CSV
without loading it into memory.

    python extract_toronto.py

It looks in the current folder for (any that are present are processed):
  * 98-401-X2021006_English_CSV_data_Ontario.csv   Census Profile, Ontario DAs
  * lda_000?21a_e.shp (+ .shx .dbf .prj)            DA boundaries
  * ldb_000?21a_e.shp (+ .shx .dbf .prj)            Dissemination block boundaries (optional)
  * 2021_92-151_X.csv                              Geographic Attribute File (optional)
Zips are fine too: unzip them first.

Output goes to ./toronto_extract/. Upload those files (not the originals).

"Toronto area" here = every DA in the census divisions that the Toronto CMA
touches (Durham, York, Toronto, Peel, Dufferin, Halton, Simcoe). That is a
little more than the CMA; the exact CMA cut is done later in the pipeline.
"""
import argparse
import csv
import glob
import gzip
import os
import re
import struct
import sys
import time
import zipfile

CDS = ("3518", "3519", "3520", "3521", "3522", "3524", "3543")
OUT = "toronto_extract"
ENC = dict(encoding="utf-8", errors="surrogateescape")  # round-trips any byte

csv.field_size_limit(10**8)


def log(msg):
    print(msg, flush=True)


def wanted(uid):
    return uid[:4] in CDS


# ----------------------------------------------------------------- census profile
def extract_profile(path):
    log(f"\nCensus Profile: {path} ({os.path.getsize(path) / 1e9:.1f} GB)")
    da_dguid = re.compile(r"2021S0512(?:%s)\d{4}" % "|".join(CDS))
    with open(path, newline="", **ENC) as f:
        header = next(csv.reader([f.readline()]))
        col = {name.strip().lstrip("﻿"): i for i, name in enumerate(header)}
        need = ["DGUID", "ALT_GEO_CODE", "CHARACTERISTIC_ID", "CHARACTERISTIC_NAME", "C1_COUNT_TOTAL"]
        missing = [n for n in need if n not in col]
        if missing:
            sys.exit(f"Unexpected columns. Missing {missing}. Found: {header}")
        i_uid, i_cid, i_name, i_cnt = (col[n] for n in need[1:])
        i_sym = col.get("SYMBOL")
        meta_cols = [c for c in ("GEO_LEVEL", "TNR_SF", "TNR_LF", "DATA_QUALITY_FLAG") if c in col]

        chars = {}
        meta = {}
        n_lines = n_kept = 0
        bytes_read = 0
        total = os.path.getsize(path)
        t0 = time.time()
        with gzip.open(os.path.join(OUT, "da_profile.csv.gz"), "wt", newline="", **ENC) as g:
            w = csv.writer(g)
            w.writerow(["dauid", "characteristic_id", "count", "symbol"])
            for line in f:
                n_lines += 1
                bytes_read += len(line)
                if n_lines % 2_000_000 == 0:
                    pct = 100 * bytes_read / total
                    log(f"  {pct:5.1f}%  {n_lines:,} lines read, {n_kept:,} kept, {time.time() - t0:,.0f}s")
                if not da_dguid.search(line):
                    continue
                r = next(csv.reader([line]))
                uid = r[i_uid]
                if len(uid) != 8 or not wanted(uid):
                    continue
                cid = r[i_cid]
                if cid not in chars:
                    chars[cid] = r[i_name]
                if uid not in meta:
                    meta[uid] = [r[col[c]] for c in meta_cols]
                cnt = r[i_cnt].strip()
                sym = r[i_sym].strip() if i_sym is not None else ""
                if cnt in ("0", "0.0") and not sym:
                    continue  # sparse: zeros are implied
                w.writerow([uid, cid, cnt, sym])
                n_kept += 1

    with open(os.path.join(OUT, "characteristics.csv"), "w", newline="", **ENC) as c:
        w = csv.writer(c)
        w.writerow(["characteristic_id", "characteristic_name"])
        for cid, name in sorted(chars.items(), key=lambda kv: int(kv[0])):
            w.writerow([cid, name])
    with open(os.path.join(OUT, "da_meta.csv"), "w", newline="", **ENC) as m:
        w = csv.writer(m)
        w.writerow(["dauid"] + [c.lower() for c in meta_cols])
        for uid in sorted(meta):
            w.writerow([uid] + meta[uid])
    log(f"  done: {len(meta):,} DAs, {len(chars):,} characteristics, {n_kept:,} non-zero values")
    if not meta:
        log("  WARNING: no DAs matched. Send me the first 3 lines of the CSV.")


# ---------------------------------------------------------------- shapefile filter
def read_dbf(path):
    with open(path, "rb") as f:
        head = f.read(32)
        n_rec, hdr_len, rec_len = struct.unpack("<IHH", head[4:12])
        fields, off = [], 1
        while True:
            d = f.read(32)
            if d[0] == 0x0D:
                break
            name = d[:11].split(b"\0")[0].decode("ascii")
            length = d[16]
            fields.append((name, off, length))
            off += length
        f.seek(0)
        header = f.read(hdr_len)
        records = [f.read(rec_len) for _ in range(n_rec)]
    return header, fields, records


def filter_shapefile(shp):
    base = shp[:-4]
    log(f"\nBoundaries: {shp}")
    header, fields, records = read_dbf(base + ".dbf")
    key = next(((n, o, l) for n, o, l in fields if n.upper() in ("DAUID", "DBUID")), None)
    if not key:
        sys.exit(f"No DAUID/DBUID field in {base}.dbf; fields: {[f[0] for f in fields]}")
    _, o, l = key
    keep = [i for i, r in enumerate(records) if wanted(r[o:o + l].decode("ascii").strip())]
    log(f"  keeping {len(keep):,} of {len(records):,} shapes")

    with open(base + ".shx", "rb") as f:
        shx = f.read()
    shp_header = bytearray(shx[:100])
    index = [struct.unpack(">ii", shx[100 + 8 * i:108 + 8 * i]) for i in range(len(records))]

    out_base = os.path.join(OUT, os.path.basename(base) + "_toronto")
    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")
    body, offsets = [], []
    pos = 50  # in 16-bit words, after the 100-byte header
    with open(shp, "rb") as f:
        for n, i in enumerate(keep, 1):
            off, clen = index[i]
            f.seek(off * 2 + 8)
            content = f.read(clen * 2)
            if struct.unpack("<i", content[:4])[0] != 0:
                bx = struct.unpack("<4d", content[4:36])
                xmin, ymin = min(xmin, bx[0]), min(ymin, bx[1])
                xmax, ymax = max(xmax, bx[2]), max(ymax, bx[3])
            body.append(struct.pack(">ii", n, clen) + content)
            offsets.append((pos, clen))
            pos += 4 + clen

    def hdr(length_words):
        h = bytearray(shp_header)
        h[24:28] = struct.pack(">i", length_words)
        if keep:
            h[36:68] = struct.pack("<4d", xmin, ymin, xmax, ymax)
        return bytes(h)

    with open(out_base + ".shp", "wb") as f:
        f.write(hdr(pos))
        f.writelines(body)
    with open(out_base + ".shx", "wb") as f:
        f.write(hdr(50 + 4 * len(keep)))
        f.writelines(struct.pack(">ii", p, c) for p, c in offsets)
    with open(out_base + ".dbf", "wb") as f:
        h = bytearray(header)
        h[4:8] = struct.pack("<I", len(keep))
        f.write(h)
        f.writelines(records[i] for i in keep)
        f.write(b"\x1a")
    for ext in (".prj", ".cpg"):
        if os.path.exists(base + ext):
            with open(base + ext, "rb") as a, open(out_base + ext, "wb") as b:
                b.write(a.read())

    zpath = out_base + ".zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            if os.path.exists(out_base + ext):
                z.write(out_base + ext, os.path.basename(out_base + ext))
                os.remove(out_base + ext)
    log(f"  wrote {zpath} ({os.path.getsize(zpath) / 1e6:.1f} MB)")


# ------------------------------------------------------- geographic attribute file
def extract_gaf(path):
    log(f"\nGeographic Attribute File: {path}")
    with open(path, newline="", **ENC) as f, \
            gzip.open(os.path.join(OUT, "gaf_toronto.csv.gz"), "wt", newline="", **ENC) as g:
        r = csv.reader(f)
        header = next(r)
        i_da = next((i for i, h in enumerate(header) if h.strip().lstrip("﻿").upper().startswith("DAUID")), None)
        if i_da is None:
            sys.exit(f"No DAUID column in GAF. Columns: {header}")
        w = csv.writer(g)
        w.writerow(header)
        n = 0
        for row in r:
            if wanted(row[i_da].strip()):
                w.writerow(row)
                n += 1
    log(f"  kept {n:,} dissemination blocks")


def find(patterns):
    for p in patterns:
        hits = sorted(glob.glob(p, recursive=True))
        if hits:
            return hits[0]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile")
    ap.add_argument("--da-shp")
    ap.add_argument("--db-shp")
    ap.add_argument("--gaf")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if any([a.profile, a.da_shp, a.db_shp, a.gaf]):  # explicit paths: do only those
        profile, da_shp, db_shp, gaf = a.profile, a.da_shp, a.db_shp, a.gaf
    else:
        profile = find(["98-401-X2021006*Ontario*.csv", "98-401-X2021006*.csv"])
        da_shp = find(["lda_000?21a_e.shp", "**/lda_000?21a_e.shp"])
        db_shp = find(["ldb_000?21a_e.shp", "**/ldb_000?21a_e.shp"])
        gaf = find(["2021_92-151_X.csv", "**/2021_92-151_X.csv"])
    log(f"Found: profile={profile}\n       DA boundaries={da_shp}\n       DB boundaries={db_shp}\n       GAF={gaf}")
    if not any([profile, da_shp, db_shp, gaf]):
        sys.exit("Nothing to do: run this in the folder with the (unzipped) downloads.")

    if da_shp:
        filter_shapefile(da_shp)
    if db_shp:
        filter_shapefile(db_shp)
    if gaf:
        extract_gaf(gaf)
    if profile:
        extract_profile(profile)

    log(f"\nFinished. Upload everything in ./{OUT}/ :")
    for name in sorted(os.listdir(OUT)):
        log(f"  {name:45} {os.path.getsize(os.path.join(OUT, name)) / 1e6:8.1f} MB")


if __name__ == "__main__":
    main()
