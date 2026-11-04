"""Compare parsed term lengths vs Wikipedia day counts. Usage: python -I check_days.py <wikitext_dir>"""
import os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_gov
for s in "Georgia Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky".split():
    rows = parse_gov.extract(open(os.path.join(sys.argv[1], s + ".txt"), encoding="utf-8").read())
    for r in rows:
        if len(r["dates"]) < 2 or r["incumbent"] or r["dates"][0][0] < "1850":
            continue
        a, b = (date.fromisoformat(x[0]) for x in r["dates"][:2])
        d = (b - a).days
        if r["sortdays"] is None or abs(r["sortdays"] - d) > 1:
            print(s, r["name"], r["dates"][:2], d, r["sortdays"])
