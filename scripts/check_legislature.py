"""Alignment + spot checks for data/raw/legislature.json. Usage: python -I scripts/check_legislature.py <project_dir>"""
import json, os, re, sys
root = sys.argv[1]
L = json.load(open(os.path.join(root, "data", "raw", "legislature.json"), encoding="utf-8"))
SEATS = re.compile(r"\d+\s*[A-Za-z]")
print("cells that look like names/tickets, not seat counts (likely misaligned):")
for st, years in L.items():
    bad = [(y, k, r[k]["text"][:40]) for y, r in years.items() for k in ("senate", "house") if k in r and r[k]["text"] and not SEATS.search(r[k]["text"]) and "[[" in r[k]["text"]]
    if bad:
        print(f"  {st} {len(bad):3}  e.g. {bad[0]}")
def show(st, y):
    r = L[st][str(y)]
    f = lambda k: f"{r[k]['code']} ({r[k]['text'][:22]})" if k in r else "-"
    print(f"{st} {y}: S={f('senate')}  H={f('house')}")
print()
for st, y in [("TX",1996),("TX",1998),("TX",2002),("TX",2004),("VA",1999),("VA",2001),("NC",2010),("NC",2012),("MN",1950),("MN",1980),
              ("VT",1856),("MS",1900),("AL",1960),("PA",2026),("MI",2024),("MI",2026),("NY",2008),("NY",2010),("AR",2012),("AR",2014),("WV",2014),("WV",2016),("KY",2016),("KY",2017)]:
    show(st, y)
