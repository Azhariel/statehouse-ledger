"""Build governors_g6.json from extracted per-state work files plus manual overrides.
Usage: python -I build.py <work_dir> <out.json>
"""
import json
import os
import sys

WORK, OUT = sys.argv[1], sys.argv[2]
CUTOFF = "1856-01-01"

STATES = {
    "TN": ("Tennessee", "1796-06-01", 1),
    "TX": ("Texas", "1845-12-29", 0),
    "UT": ("Utah", "1896-01-04", 1),
    "VT": ("Vermont", "1791-03-04", 1),
    "VA": ("Virginia", "1788-06-25", 0),
    "WA": ("Washington", "1889-11-11", 1),
    "WV": ("West Virginia", "1863-06-20", 0),
    "WI": ("Wisconsin", "1848-05-29", 1),
    "WY": ("Wyoming", "1890-07-10", 1),
}

# acting flags (name, start) confirmed against the wikitext ("acting" in succession column)
ACTING = {
    ("Edward H. East", "1865-03-04"),
    ("Daniel D. T. Farnsworth", "1869-02-26"),
    ("Arthur MacArthur Sr.", "1856-03-21"),
    ("Amos W. Barber", "1890-11-24"),
    ("Fenimore Chatterton", "1903-04-28"),
    ("Frank L. Houx", "1917-02-24"),
    ("Frank Lucas", "1924-10-02"),
    ("Alonzo M. Clark", "1931-02-18"),
    ("Arthur G. Crane", "1949-01-03"),
    ("Clifford Joy Rogers", "1953-01-03"),
    ("Jack R. Gage", "1961-01-02"),
}

# Rows where the list's party column holds a non-party description instead of a party
NO_PARTY = {
    ("Andrew Jackson Hamilton", "1865-06-17"): "Military governor appointed by President",
    ("Elisha M. Pease", "1867-07-30"): "Installed by military occupation",
    ("Andrew Johnson", "1862-03-12"): "Military governor appointed by President",
    ("Edward H. East", "1865-03-04"): "Secretary of state acting",
    ("Henry H. Wells", "1868-04-04"): "Appointed by military occupation",
}

NOTES = {
    "TN": [
        "Civil War: Isham G. Harris (Confederate, Democratic) listed until 1862-03-12; he fled Nashville after Fort Donelson (Feb 1862). Union military governor Andrew Johnson (arrived in Nashville 1862-03-12) controlled the capital and is used from that date, matching the main list. Robert L. Caruthers, elected by Confederate-held West Tennessee in 1863, never took office and is not included.",
        "Andrew Johnson (1862-1865) and Edward H. East (1865, acting as secretary of state) have no party in the list; the party column reads 'Military governor appointed by President' / 'Secretary of state acting'. Recorded party_raw 'None' with the cell text in wikipedia_party_cell.",
        "Andrew Johnson's first term (1853-1857, Democratic) was in office on 1856-01-01 and is included.",
        "Governor-elect from Nov 2026 not included; Bill Lee is sitting governor.",
    ],
    "TX": [
        "Civil War: Texas had no rival Union government; Confederate-era governors Clark, Lubbock and Murrah controlled Austin and are listed as in the main table.",
        "Andrew Jackson Hamilton (1865-1866, provisional governor appointed by President Johnson) and Elisha M. Pease (1867-1869, installed by the military) have no party in the list (party column: 'Military governor appointed by President' / 'Installed by military occupation'). Recorded party_raw 'None' with the cell text in wikipedia_party_cell. Pease's 1853-1857 term is Democratic.",
        "1869-09-30 to 1870-01-08: list shows 'Vacant' (office vacated after Pease resigned; state under military Reconstruction). Added as '(vacant)', party_raw 'None'.",
        "Governor-elect Gina Hinojosa (takes office 2027-01-19 per the page) excluded; Greg Abbott is sitting governor.",
    ],
    "UT": [
        "Statehood 1896-01-04; first state governor Heber Manning Wells took office 1896-01-06 (territorial governor Caleb Walton West served to 1896-01-04). 2-day gap, not filled.",
    ],
    "VT": [
        "Stephen Royce (Whig) was in office on 1856-01-01.",
    ],
    "VA": [
        "Civil War rival governments: the main list shows both the Confederate governors in Richmond (John Letcher 1860-1864, William Smith 1864-1865-05-09) and Francis H. Pierpont of the Union 'Restored Government' (listed 1861-06-20 to 1868-04-04, seated in Wheeling then Alexandria). Richmond (the capital) was held by the Confederate government until 1865, so Letcher and Smith are used through 1865-05-09, and Pierpont's term is recorded starting 1865-05-09 (the list's own start date 1861-06-20 is kept in list_start). Pierpont moved his government to Richmond in May 1865.",
        "Henry H. Wells (1868-1869) has no party in the list ('Appointed by military occupation'); party_raw 'None', cell text in wikipedia_party_cell.",
        "Gilbert Carlton Walker is listed in two rows: first 'Appointed by military occupation' (from 1869-09-21) and then 'Republican' (elected 1869; ran as a 'Conservative Republican' per footnote). The list gives no split date, so one term with party_raw 'Republican' is recorded.",
        "Joseph Johnson's term ended 1856-01-01, the same day Henry A. Wise took office, so Johnson is excluded.",
    ],
    "WA": [
        "Statehood 1889-11-11; first state governor Elisha P. Ferry took office 1889-11-18 (territorial governor Miles C. Moore served to 1889-11-18). 7-day gap, not filled.",
    ],
    "WV": [
        "Statehood 1863-06-20; Arthur I. Boreman is first.",
        "Earl Ray Tomblin is listed in one row (2010-11-15 to 2017-01-16) with succession 'President of the Senate acting'. Split into an acting term (2010-11-15 to 2011-11-13) and a full term from 2011-11-13, using the date he was sworn in after the 2011 special election (from his own Wikipedia article infobox: 'Acting: November 15, 2010 - November 13, 2011').",
        "Jim Justice is listed as Democratic (2016 election) and Republican (2020 election); footnote says he 'switched to the Republican Party in August 2017' (cited NYT article dated 2017-08-03). Split at 2017-08-03.",
    ],
    "WI": [
        "William A. Barstow (Democratic) was in office on 1856-01-01; after the disputed 1855 election he resigned 1856-03-21, Arthur MacArthur Sr. acted for 4 days, then Coles Bashford (Republican) was seated by court ruling.",
        "Orland Steen Loomis (Progressive, elected 1942) died before taking office; listed in the table without a term and excluded.",
        "William Robert Taylor's party is listed as 'Reform' (Reform Party, a Democratic/Liberal Republican coalition in 1870s Wisconsin).",
        "Philip La Follette: first term (1931-1933) Republican, second term (1935-1939) Progressive, as listed.",
        "Governor-elect David Crowley (from Nov 2026) excluded; Tony Evers is sitting governor.",
    ],
    "WY": [
        "Statehood 1890-07-10; Francis E. Warren continued as territorial governor until he was inaugurated as first state governor on 1890-10-11 (listed in the territorial table). The ~3-month gap is not filled because territorial governors are excluded.",
        "Wyoming secretaries of state who acted as governor (Barber, Chatterton, Houx, Lucas, Clark, Crane, Rogers, Gage) are marked acting: true; the list shows them as 'Secretary of state acting' / 'Acting as governor'.",
        "Governor-elect Eric Barlow (from Nov 2026) excluded; Mark Gordon is sitting governor.",
    ],
}


def mk(name, party, start, end, acting=False, **extra):
    t = {"name": name, "party_raw": party, "start": start, "end": end, "acting": acting}
    t.update(extra)
    return t


def main():
    result = {}
    files = {"TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
             "WA": "Washington", "WV": "West_Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
    for code, (sname, admitted, table) in STATES.items():
        rows = json.load(open(os.path.join(WORK, files[code] + ".json"), encoding="utf-8"))
        terms = []
        for r in rows:
            if r["table"] != table or not r.get("range") or not r.get("start"):
                continue
            if r["end"] is not None and r["end"] <= CUTOFF:
                continue
            key = (r["name"], r["start"])
            party = r["party"]
            extra = {}
            if key in NO_PARTY:
                party = "None"
                extra["wikipedia_party_cell"] = NO_PARTY[key]
            if r.get("sp") != "day":
                extra["date_precision"] = r["sp"]
            if r["end"] and r.get("ep") != "day":
                extra["end_precision"] = r["ep"]
            terms.append(mk(r["name"], party, r["start"], r["end"], key in ACTING, **extra))

        new = []
        for t in terms:
            if code == "VA" and t["name"] == "Francis Harrison Pierpont":
                t["list_start"] = t["start"]
                t["start"] = "1865-05-09"
            if code == "VA" and t["name"] == "Gilbert Carlton Walker":
                t["party_raw"] = "Republican"
            if code == "WV" and t["name"] == "Earl Ray Tomblin":
                new.append(mk(t["name"], t["party_raw"], t["start"], "2011-11-13", True))
                new.append(mk(t["name"], t["party_raw"], "2011-11-13", t["end"]))
                continue
            if code == "WV" and t["name"] == "Jim Justice":
                new.append(mk(t["name"], "Democratic", t["start"], "2017-08-03"))
                new.append(mk(t["name"], "Republican", "2017-08-03", t["end"]))
                continue
            new.append(t)
        if code == "TX":
            new.append(mk("(vacant)", "None", "1869-09-30", "1870-01-08"))
        new.sort(key=lambda t: t["start"])
        result[code] = {
            "state_name": sname,
            "admitted": admitted,
            "source": "https://en.wikipedia.org/wiki/List_of_governors_of_" + sname.replace(" ", "_"),
            "terms": new,
            "notes": NOTES[code],
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


main()
