"""Continuity check for governors_g2.json. Usage: python -I check_g2.py <json>"""
import json
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
d = json.load(open(sys.argv[1], encoding="utf-8"))
parties = set()
for code, s in d.items():
    t = s["terms"]
    print("== %s: %d terms, first %s (%s), last %s (%s, end=%s)" % (
        code, len(t), t[0]["name"], t[0]["start"], t[-1]["name"], t[-1]["start"], t[-1]["end"]))
    for a, b in zip(t, t[1:]):
        parties.add(a["party_raw"])
        if a["end"] is None:
            print("  NULL END mid-list:", a["name"])
            continue
        gap = (date.fromisoformat(b["start"]) - date.fromisoformat(a["end"])).days
        if gap != 0:
            print("  gap %+d days: %s (%s) -> %s (%s)" % (gap, a["name"], a["end"], b["name"], b["start"]))
        if b["start"] < a["start"]:
            print("  ORDER", a["name"], b["name"])
    parties.add(t[-1]["party_raw"])
    for x in t:
        if x["acting"]:
            print("  acting:", x["name"], x["start"])
print("parties:", sorted(parties))
