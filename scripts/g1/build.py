"""Build governors_g1.json. Usage: python -I build.py <scripts_dir_with_tmp_json> <out.json>"""
import json, re, sys, os

CUTOFF = "1856-01-01"
D, OUT = sys.argv[1], sys.argv[2]
MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}
DRE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:(\d{1,2}),\s*)?(\d{4})")

STATES = {
    "AL": ("Alabama", "1819-12-14", 2),
    "AK": ("Alaska", "1959-01-03", 3),
    "AZ": ("Arizona", "1912-02-14", 2),
    "AR": ("Arkansas", "1836-06-15", 2),
    "CA": ("California", "1850-09-09", 1),
    "CO": ("Colorado", "1876-08-01", 2),
    "CT": ("Connecticut", "1788-01-09", 1),
    "DE": ("Delaware", "1787-12-07", 1),
    "FL": ("Florida", "1845-03-03", 3),
}


def dates(raw):
    raw = raw.split('"|')[-1]  # drop {{age in years and days|...}} residue on incumbent rows
    out = []
    for mon, day, yr in DRE.findall(raw):
        if day:
            out.append(("%s-%02d-%02d" % (yr, MONTHS[mon], int(day)), "day"))
        else:
            out.append(("%s-%02d-01" % (yr, MONTHS[mon]), "month"))
    incumbent = "Incumbent" in raw
    return out, incumbent


def clean_party(p):
    p = re.sub(r"\{\{small\|.*", "", p).strip()
    return p.replace("Democratic- Republican", "Democratic-Republican")


result = {}
for ab, (name, admitted, tbl) in STATES.items():
    rows = json.load(open(os.path.join(D, "tmp_%s.json" % name), encoding="utf-8"))
    terms = []
    for r in rows:
        if r.get("table") != tbl or "dates" not in r:
            if r.get("table") == tbl and r.get("name") == "(vacant)":
                ds, _ = dates(r["raw"])
                if len(ds) >= 2 and ds[1][0] >= CUTOFF:
                    terms.append({"name": "(vacant)", "party_raw": "None", "start": ds[0][0], "end": ds[1][0], "acting": False})
            continue
        if re.search(r"governor[- ]elect", r["term_raw"], re.I) and "Incumbent" not in r["term_raw"]:
            continue  # governor-elect rows
        ds, inc = dates(r["term_raw"])
        if not ds:
            continue
        start = ds[0]
        end = None if inc else (ds[1] if len(ds) > 1 else None)
        if end is not None and end[0] < CUTOFF:
            continue
        t = {"name": r["name"], "party_raw": clean_party(r["party_raw"]), "start": start[0],
             "end": end[0] if end else None, "acting": bool(r["acting_hint"])}
        if start[1] != "day" or (end and end[1] != "day"):
            t["date_precision"] = start[1] if start[1] != "day" else end[1]
        terms.append(t)
    terms.sort(key=lambda t: t["start"])
    result[ab] = {"state_name": name, "admitted": admitted,
                  "source": "https://en.wikipedia.org/wiki/List_of_governors_of_%s" % name,
                  "terms": terms, "notes": []}


def find(ab, nm, start=None):
    for t in result[ab]["terms"]:
        if t["name"] == nm and (start is None or t["start"] == start):
            return t
    raise KeyError((ab, nm, start))


# ---- Overrides / judgment calls ----
AL = result["AL"]
sw = find("AL", "Wager Swayne")
AL["terms"].remove(sw)
AL["notes"].append("Wager Swayne (military commander, listed unnumbered as 'Military occupation', 1867-03-02 to 1868-01-11) is omitted as a separate term because it overlaps Robert M. Patton, whom Wikipedia lists as governor through 1868-07-14. Patton was stripped of most authority in March 1867 but remained the nominal civilian governor, so no '(military rule)' gap was inserted.")
for nm in ("Lewis E. Parsons",):
    find("AL", nm)["party_raw"] = "None"
AL["notes"].append("Lewis E. Parsons was a provisional governor appointed by President Andrew Johnson; Wikipedia gives no party (cell reads 'Provisional governor appointed by President'), recorded as party_raw 'None'.")
AL["notes"].append("Robert M. Patton: Wikipedia labels the 1865 election 'Non-partisan' (footnote: politically a Whig). Recorded as 'Non-partisan'.")
sam = find("AL", "William J. Samford")
sam["start"] = "1900-12-26"
AL["notes"].append("William D. Jelks acted as governor 1900-12-01 to 1900-12-26 because William J. Samford was ill; Wikipedia lists Samford's term from 1900-12-01 but its footnote says he could not perform duties until 1900-12-26, so Samford's start is set to 1900-12-26 to avoid overlap.")
AL["notes"].append("Vacancy 1865-05-03 to 1865-06-21 (Watts arrested at end of Civil War) recorded as '(vacant)', as listed by Wikipedia.")
AL["notes"].append("Wikipedia also lists Tommy Tuberville as governor-elect (takes office January 2027); excluded.")

AR = result["AR"]
fl = find("AR", "Harris Flanagin")
fl["end"] = "1863-09-10"
mu = find("AR", "Isaac Murphy")
AR["terms"].insert(AR["terms"].index(mu), {"name": "(military rule)", "party_raw": "None", "start": "1863-09-10", "end": "1864-01-20", "acting": False})
AR["notes"].append("Rival governments: Wikipedia lists Confederate governor Harris Flanagin 1862-11-15 to 1865-06-01 and Unionist Isaac Murphy from 1864-01-20, overlapping. Union forces captured Little Rock on 1863-09-10 and Flanagin's government went into exile at Washington, Arkansas. Per the 'controlled the capital' rule, Flanagin is cut at 1863-09-10, a '(military rule)' term covers Union occupation until Murphy's selection as provisional governor (1864-01-20, the date Wikipedia uses; he was formally inaugurated 1864-04-18). The 1863-09-10 capture date is general historical knowledge, not from the governor table.")
AR["notes"].append("Isaac Murphy's party: Wikipedia shows 'Independent' with a footnote that sources disagree (state: Independent, Sobel: Democratic, Kallenbach: Union).")
AR["notes"].append("Henry Rector is labelled 'Independent Democratic' by Wikipedia; Harris Flanagin 'Independent'.")

CT = result["CT"]
for nm in ("John H. Trumbull", "John N. Dempsey"):
    find("CT", nm)["acting"] = False
CT["notes"].append("Wikipedia marks lieutenant governors who succeeded under the pre-1965 constitution as 'Lieutenant governor acting' in the election column. Frank B. Weeks, Charles Wilbert Snow and James C. Shannon only served in that capacity and are marked acting: true. John H. Trumbull (1925) and John N. Dempsey (1961) also began as 'acting' but were later elected in their own right within the same continuous tenure, so they are kept as single terms with acting: false.")

DE = result["DE"]
find("DE", "Gove Saulsbury")["acting"] = False
DE["notes"].append("Gove Saulsbury succeeded as Speaker of the Senate 'acting' on 1865-03-01, then won the 1866 election; Wikipedia lists one continuous tenure to 1871-01-17, kept as one term with acting: false. William T. Watson (1895-1897, Speaker of the Senate acting, never elected) is acting: true.")
DE["notes"].append("Peter F. Causey (in office on 1856-01-01) is labelled 'American' (Know Nothing) by Wikipedia; William Cannon 'Union'.")

FL = result["FL"]
find("FL", "William Marvin")["party_raw"] = "None"
FL["notes"].append("William Marvin was a provisional governor appointed by President Andrew Johnson; Wikipedia gives no party, recorded as party_raw 'None'.")
FL["notes"].append("Vacancy 1865-05-19 to 1865-07-13 (after Allison's resignation at the end of the Civil War) recorded as '(vacant)', as listed by Wikipedia.")
FL["notes"].append("David S. Walker is labelled 'Conservative' by Wikipedia. Wikipedia lists Byron Donalds as governor-elect (January 2027); excluded.")

CA = result["CA"]
CA["notes"].append("J. Neely Johnson labelled 'American' (Know Nothing); Milton Latham and John G. Downey 'Lecompton Democratic'; Frederick Low 'Union'. Wikipedia lists Xavier Becerra as governor-elect (January 2027); excluded. Lieutenant governors who succeeded (McDougal, Downey, Pacheco, Waterman) are numbered governors on Wikipedia, so acting: false.")
CA["notes"].append("Earl Warren ended 1953-10-04 and Goodwin Knight started 1953-10-05 per Wikipedia (1-day seam).")

CO = result["CO"]
CO["notes"].append("Colorado was admitted 1876-08-01, but John Long Routt continued as territorial governor until sworn in as first state governor on 1876-11-03 (Wikipedia's state-table start). The 1876-08-01 to 1876-11-03 interval is therefore not covered by a state term.")
CO["notes"].append("Davis Hanson Waite labelled 'People's' (Populist). 1905: Alva Adams unseated after 66 days, James Peabody served one day, then Jesse McDonald, all as listed. Wikipedia lists Phil Weiser as governor-elect (January 2027); excluded.")

AK = result["AK"]
AK["notes"].append("Starts at statehood 1959-01-03 with William A. Egan; territorial governors excluded. Wally Hickel's 1990-1994 term labelled 'Alaskan Independence'; Bill Walker 'Independent'.")

AZ = result["AZ"]
AZ["notes"].append("Starts at statehood 1912-02-14 with George W. P. Hunt; territorial governors excluded. Thomas Edward Campbell's first term (1917) ended when the contested 1916 election was awarded to Hunt (removed 1917-12-25).")

json.dump(result, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# continuity check
for ab, s in result.items():
    ts = s["terms"]
    from datetime import date
    def d(x): return date.fromisoformat(x)
    print(ab, len(ts), ts[0]["name"], ts[0]["start"], "->", ts[-1]["name"], ts[-1]["end"])
    for a, b in zip(ts, ts[1:]):
        if a["end"] is None:
            print("  open end mid-list:", a["name"]); continue
        gap = (d(b["start"]) - d(a["end"])).days
        if abs(gap) > 1:
            print("  gap %d days: %s (%s) -> %s (%s)" % (gap, a["name"], a["end"], b["name"], b["start"]))
