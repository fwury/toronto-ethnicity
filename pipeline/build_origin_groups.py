"""Validate the origin grouping and write data/origin_groups.csv + docs/origin-groups.md.

Usage: python pipeline/build_origin_groups.py
Input:  data/reference/statcan_ethnic_origins_2021_toronto_cma.csv
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import origin_groups  # noqa: E402
from origin_groups import BROAD_ORDER, EXCLUDED, GROUPS, REMOVED  # noqa: E402
import json  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ref = list(csv.DictReader(open(ROOT / "data/reference/statcan_ethnic_origins_2021_toronto_cma.csv")))
by_id = {int(r["member_id"]): r for r in ref}
leaves = {i for i, r in by_id.items() if r["is_leaf"] == "1"}

# Census Profile (DA level) characteristic IDs, matched by name. The DA profile
# only publishes ~250 of the origins; the rest have no DA-level data.
chars = list(csv.DictReader(open(ROOT / "data/raw/characteristics.csv", encoding="cp1252")))
start = next(i for i, c in enumerate(chars) if c["characteristic_name"].startswith("Total - Ethnic or cultural origin"))
end = next(i for i in range(start + 1, len(chars)) if chars[i]["characteristic_name"].startswith("Total - "))
da_code = {c["characteristic_name"].strip(): int(c["characteristic_id"]) for c in chars[start + 1:end]}
unmatched = set(da_code) - {r["origin"] for r in ref}
if unmatched:
    sys.exit(f"DA profile origins with no match in the reference list: {sorted(unmatched)}")

assigned = Counter(i for v in [*GROUPS.values(), EXCLUDED, REMOVED] for i in v)
errors = []
errors += [f"assigned twice: {i} {by_id[i]['origin']}" for i, n in assigned.items() if n > 1]
errors += [f"not a leaf: {i} {by_id[i]['origin']}" for i in assigned if i not in leaves]
errors += [f"unassigned leaf: {i} {by_id[i]['origin']}" for i in sorted(leaves - set(assigned))]
errors += [f"unknown broad: {b}" for b, _ in GROUPS if b not in BROAD_ORDER]
if errors:
    sys.exit("\n".join(errors))

# Mapped totals per subcategory (sum of published DA counts in the CMA), used
# to order subcategories within each broad category.
gaf = pd.read_csv(ROOT / "data/raw/gaf_toronto.csv.gz", dtype=str, encoding="cp1252",
                  usecols=["CMAUID_RMRIDU", "DAUID_ADIDU"])
cma_das = set(gaf[gaf.CMAUID_RMRIDU == "535"].DAUID_ADIDU)
prof = pd.read_csv(ROOT / "data/raw/da_profile.csv.gz", dtype={"dauid": str, "count": str})
prof = prof[prof.dauid.isin(cma_das)]
da_sum = pd.to_numeric(prof["count"], errors="coerce").groupby(prof.characteristic_id).sum()
sub_tot = {}
for (broad, sub), members in GROUPS.items():
    sub_tot[f"{broad} / {sub}"] = int(sum(da_sum.get(da_code.get(by_id[i]["origin"]), 0) for i in members))
(ROOT / "data/sub_totals.json").write_text(json.dumps(sub_tot, indent=1, ensure_ascii=False))
GROUPS = origin_groups._sort_groups()

rows = []
for (broad, sub), members in GROUPS.items():
    for i in members:
        r = by_id[i]
        rows.append(dict(broad=broad, sub=sub, member_id=i, da_profile_id=da_code.get(r["origin"], ""),
                         origin=r["origin"],
                         statcan_group=r["parent_origin"],
                         toronto_cma_responses=int(r["toronto_cma_total_responses"])))
rows.sort(key=lambda r: (BROAD_ORDER.index(r["broad"]), list(GROUPS).index((r["broad"], r["sub"])),
                         -r["toronto_cma_responses"]))

with open(ROOT / "data/origin_groups.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

fmt = lambda n: f"{n:,}"
md = ["# Ethnic origin grouping (2021 Census, Toronto CMA)", "",
      "Codes are Statistics Canada member IDs from table 98-10-0356-01. Counts are total "
      "responses in the Toronto CMA (single + multiple), so group totals count a person "
      "once per origin they reported. Origins with 0 responses in Toronto are still listed.", "",
      "**DA code** is the Census Profile CHARACTERISTIC_ID used for the map. A dash means the "
      "origin is not published at DA level (about 1.2% of Toronto CMA responses), so it cannot be mapped.", "",
      "Excluded (religious responses): " + ", ".join(f"{by_id[i]['origin']} ({i})" for i in EXCLUDED), "",
      "Removed (no published responses in any Toronto DA): " + ", ".join(f"{by_id[i]['origin']} ({i})" for i in REMOVED), "",
      "Subcategories are ordered by mapped (DA-level) responses, with catch-all \"Other\" groups last.", ""]
for broad in BROAD_ORDER:
    b_rows = [r for r in rows if r["broad"] == broad]
    md += [f"## {broad} — {fmt(sum(r['toronto_cma_responses'] for r in b_rows))} responses", ""]
    for (b, sub) in GROUPS:
        if b != broad:
            continue
        s_rows = [r for r in b_rows if r["sub"] == sub]
        md += [f"### {sub} — {fmt(sum(r['toronto_cma_responses'] for r in s_rows))} "
               f"({fmt(sub_tot[f'{broad} / {sub}'])} mapped)", "",
               "| Code | DA code | Origin | Responses |", "|---:|---:|---|---:|"]
        md += [f"| {r['member_id']} | {r['da_profile_id'] or '–'} | {r['origin']} | {fmt(r['toronto_cma_responses'])} |" for r in s_rows]
        md.append("")
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/origin-groups.md").write_text("\n".join(md))
print(f"OK: {len(rows)} origins in {len(GROUPS)} subcategories, {len(BROAD_ORDER)} broad categories")
