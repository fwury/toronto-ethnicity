"""Validate the origin grouping and write data/origin_groups.csv + docs/origin-groups.md.

Usage: python pipeline/build_origin_groups.py
Input:  data/reference/statcan_ethnic_origins_2021_toronto_cma.csv
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from origin_groups import BROAD_ORDER, EXCLUDED, GROUPS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ref = list(csv.DictReader(open(ROOT / "data/reference/statcan_ethnic_origins_2021_toronto_cma.csv")))
by_id = {int(r["member_id"]): r for r in ref}
leaves = {i for i, r in by_id.items() if r["is_leaf"] == "1"}

assigned = Counter(i for v in [*GROUPS.values(), EXCLUDED] for i in v)
errors = []
errors += [f"assigned twice: {i} {by_id[i]['origin']}" for i, n in assigned.items() if n > 1]
errors += [f"not a leaf: {i} {by_id[i]['origin']}" for i in assigned if i not in leaves]
errors += [f"unassigned leaf: {i} {by_id[i]['origin']}" for i in sorted(leaves - set(assigned))]
errors += [f"unknown broad: {b}" for b, _ in GROUPS if b not in BROAD_ORDER]
if errors:
    sys.exit("\n".join(errors))

rows = []
for (broad, sub), members in GROUPS.items():
    for i in members:
        r = by_id[i]
        rows.append(dict(broad=broad, sub=sub, member_id=i, origin=r["origin"],
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
      "Excluded (religious responses): " + ", ".join(f"{by_id[i]['origin']} ({i})" for i in EXCLUDED), ""]
for broad in BROAD_ORDER:
    b_rows = [r for r in rows if r["broad"] == broad]
    md += [f"## {broad} — {fmt(sum(r['toronto_cma_responses'] for r in b_rows))} responses", ""]
    for (b, sub) in GROUPS:
        if b != broad:
            continue
        s_rows = [r for r in b_rows if r["sub"] == sub]
        md += [f"### {sub} — {fmt(sum(r['toronto_cma_responses'] for r in s_rows))}", "",
               "| Code | Origin | Responses |", "|---:|---|---:|"]
        md += [f"| {r['member_id']} | {r['origin']} | {fmt(r['toronto_cma_responses'])} |" for r in s_rows]
        md.append("")
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/origin-groups.md").write_text("\n".join(md))
print(f"OK: {len(rows)} origins in {len(GROUPS)} subcategories, {len(BROAD_ORDER)} broad categories")
