"""Build governors_g5.json from parse.py output. Usage: python -I build.py <parsed_json> <out_json>"""
import json, sys
from datetime import date

parsed = json.load(open(sys.argv[1], encoding="utf-8"))

STATES = {
    "ND": ("North_Dakota", "North Dakota", "1889-11-02"),
    "OH": ("Ohio", "Ohio", "1803-03-01"),
    "OK": ("Oklahoma", "Oklahoma", "1907-11-16"),
    "OR": ("Oregon", "Oregon", "1859-02-14"),
    "PA": ("Pennsylvania", "Pennsylvania", "1787-12-12"),
    "RI": ("Rhode_Island", "Rhode Island", "1790-05-29"),
    "SC": ("South_Carolina", "South Carolina", "1788-05-23"),
    "SD": ("South_Dakota", "South Dakota", "1889-11-02"),
}
CUTOFF = "1856-01-01"

NOTES = {
    "ND": [
        "John Miller took office 1889-11-20, 18 days after statehood (1889-11-02); no governor is listed for the interval.",
        "NPL-era governors are labeled 'Republican/Nonpartisan League' or 'Republican/Independent Voters' (dual labels) exactly as Wikipedia shows them.",
        "Walter Maddock: in office as 'Republican/Nonpartisan League'; Wikipedia adds a second label 'Democratic/Nonpartisan League' because he switched parties to run in the 1928 election (during his term). Kept the in-office Republican/Nonpartisan League label.",
        "William Langer 1933 start: sources disagree (State Historical Society says 1932-12-31); used Wikipedia's 1933-01-04. Langer was removed (ruled ineligible 1934-07-17) and Ole H. Olson formally took office 1934-07-19.",
        "Democratic-NPL era governors (Guy, Link, Sinner) are labeled 'Democratic–Nonpartisan League' (en dash, as on Wikipedia).",
    ],
    "OH": [
        "Amy Acton (Democratic) is listed as governor-elect taking office 2027-01-11; excluded.",
        "David Tod, John Brough and Charles Anderson are labeled 'Union' (Civil War National Union coalition) on Wikipedia.",
    ],
    "OK": [
        "Statehood 1907-11-16; Oklahoma Territory governors excluded.",
        "Jack C. Walton was impeached 1923-10-23 and Martin E. Trapp acted as governor from then until Walton's removal 1923-11-19; Wikipedia's table dates Trapp from 1923-11-19, so used that (acting period only in a footnote).",
        "Henry S. Johnston was impeached 1929-01-21 and William J. Holloway acted from then; table dates Holloway from 1929-03-20 (removal), used that.",
        "George Nigh 1979 term starts 1979-01-03, Boren's ends 1979-01-02 (1-day gap, as on Wikipedia).",
        "Mike Mazzei (Republican) is listed as governor-elect taking office 2027-01-11; excluded.",
    ],
    "OR": [
        "John Whiteaker took office under the state constitution on 1858-07-08, before formal admission on 1859-02-14; his start is clipped to the admission date 1859-02-14. George Law Curry (territorial) is excluded.",
    ],
    "PA": [
        "Robert E. Pattison and Gifford Pinchot served non-consecutive terms; each stint is a separate term.",
    ],
    "RI": [
        "William W. Hoppin (in office on 1856-01-01) is labeled 'Whig' on Wikipedia; a footnote says other sources call him Whig/Maine Law (1854), Whig/American (1855), Republican/American (1856). Used Wikipedia's 'Whig'.",
        "Helena Foulkes (Democratic) is listed as governor-elect taking office 2027-01-05; excluded.",
    ],
    "SC": [
        "James Hopkins Adams (in office on 1856-01-01) is the first term.",
        "1865-05-28 to 1865-06-30: office vacant after Magrath was arrested by Union forces; Wikipedia lists a 'Vacant' row, recorded as (vacant).",
        "Benjamin Franklin Perry (1865-06-30 to 1865-11-29) was a provisional governor appointed by President Johnson; Wikipedia gives no party (cell reads 'Provisional governor appointed by President', colored nonpartisan), so party_raw is 'None'.",
        "Disputed 1876-77 government: Wikipedia lists Chamberlain (Republican) to 1877-04-11 and Wade Hampton III (Democratic) from 1876-12-14, overlapping. Chamberlain's government held the State House in Columbia (with federal troops) until the troops were withdrawn in April 1877, so Chamberlain is kept to 1877-04-11 and Hampton's start is set to 1877-04-11 (Wikipedia start 1876-12-14).",
        "James Lawrence Orr (1865-11-29 to 1868-07-09): SC was under Second Military District oversight from 1867 under the Reconstruction Acts, but Wikipedia lists Orr as governor continuously until Scott took office, so no separate military-rule term was added.",
        "1942-02-27 to 1942-03-02: vacant after Harley's death while Jefferies delayed taking the oath; Wikipedia lists a 'Vacant' row, recorded as (vacant).",
        "Henry McMaster is term-limited; no governor-elect row was present in the wikitext at download time, and the 2026 winner takes office in 2027 anyway.",
    ],
    "SD": [
        "Larry Rhoden succeeded Kristi Noem on 2025-01-25.",
    ],
}


def days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


out = {}
for code, (fn, sname, admitted) in STATES.items():
    tables = parsed[fn + ".txt"]
    tbl = [t for t in tables if "Territory" not in t["caption"] and "Supreme" not in t["caption"]]
    assert len(tbl) == 1, (code, [t["caption"] for t in tables])
    terms = []
    for r in tbl[0]["rows"]:
        if "error" in r:
            continue  # governor-elect rows (no term dates)
        if r["end"] is not None and r["end"] < CUTOFF:
            continue
        vacant = r["name"] == "Vacant"
        t = {
            "name": "(vacant)" if vacant else r["name"],
            "party_raw": "None" if vacant else r["party_cell"],
            "start": r["start"],
            "end": r["end"],
            "acting": False,
        }
        if r["start_precision"] != "day":
            t["date_precision"] = r["start_precision"]
        if r["end_precision"] not in (None, "day"):
            t["date_precision"] = r["end_precision"]
        terms.append(t)
    # overrides
    for t in terms:
        if code == "SC" and t["name"] == "Benjamin Franklin Perry":
            t["party_raw"] = "None"
        if code == "SC" and t["name"] == "Wade Hampton III":
            assert t["start"] == "1876-12-14"
            t["start"] = "1877-04-11"
        if code == "OR" and t["name"] == "John Whiteaker":
            assert t["start"] == "1858-07-08"
            t["start"] = admitted
    terms.sort(key=lambda t: t["start"])
    notes = list(NOTES[code])
    # continuity check
    for a, b in zip(terms, terms[1:]):
        g = days(a["end"], b["start"])
        if abs(g) > 1:
            print(code, "GAP/OVERLAP", g, a["name"], a["end"], "->", b["name"], b["start"])
    assert terms[-1]["end"] is None and all(t["end"] for t in terms[:-1]), code
    out[code] = {
        "state_name": sname,
        "admitted": admitted,
        "source": "https://en.wikipedia.org/wiki/List_of_governors_of_" + fn,
        "terms": terms,
        "notes": notes,
    }
    print(code, len(terms), terms[0]["name"], terms[0]["start"], "...", terms[-1]["name"], terms[-1]["start"])
    print("   parties:", sorted({t["party_raw"] for t in terms}))

json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=2, ensure_ascii=False)
