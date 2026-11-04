"""Continuity / sanity checks. Usage: python -I check.py <governors.json>"""
import json
import sys
from datetime import date

d = json.load(open(sys.argv[1], encoding="utf-8"))
parties = set()
for code, s in d.items():
    t = s["terms"]
    print("==", code, len(t), "terms |", t[0]["name"], t[0]["start"], "->", t[-1]["name"], t[-1]["start"], t[-1]["end"])
    for a, b in zip(t, t[1:]):
        if a["end"] is None:
            print("   NON-LAST open end", a)
            continue
        gap = (date.fromisoformat(b["start"]) - date.fromisoformat(a["end"])).days
        if abs(gap) > 0:
            print("   gap %+d days: %s (%s) -> %s (%s)" % (gap, a["name"], a["end"], b["name"], b["start"]))
    for x in t:
        parties.add(x["party_raw"])
        if not x["party_raw"]:
            print("   MISSING PARTY", x)
        if x["acting"]:
            print("   acting:", x["name"], x["start"], x["end"])
print("parties:", sorted(parties))
