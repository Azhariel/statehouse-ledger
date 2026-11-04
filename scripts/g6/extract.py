"""Extract candidate governor terms (name, start, end, party) from wikitext tables.
Usage: python -I extract.py <file.wiki> <out.json>
Prints one compact line per row for eyeballing.
"""
import json
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from dump_rows import clean  # noqa: E402

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
MRE = "|".join(MONTHS)
DATE = r"(?:(?:%s)\s+\d{1,2},?\s+\d{4}|(?:%s)\s+\d{4}|\d{4})" % (MRE, MRE)
RANGE_RE = re.compile(r"(%s)\s*(?:&ndash;|–|—|-|&mdash;|to)\s*(%s|[Ii]ncumbent|[Pp]resent)" % (DATE, DATE))


def iso(d):
    d = d.strip()
    m = re.match(r"(%s)\s+(\d{1,2}),?\s+(\d{4})" % MRE, d)
    if m:
        return "%s-%02d-%02d" % (m.group(3), MONTHS.index(m.group(1)) + 1, int(m.group(2))), "day"
    m = re.match(r"(%s)\s+(\d{4})" % MRE, d)
    if m:
        return "%s-%02d-01" % (m.group(2), MONTHS.index(m.group(1)) + 1), "month"
    m = re.match(r"(\d{4})$", d)
    if m:
        return "%s-01-01" % m.group(1), "year"
    return None, None


def simplify(b):
    b = re.sub(r"<br\s*/?>", " ", b)
    b = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", b)
    b = re.sub(r"\[\[([^\]]+)\]\]", r"\1", b)
    b = b.replace("&ndash;", "–").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", b).strip()


def cells_of(row):
    cells = []
    for l in row.split("\n"):
        if not l.strip():
            continue
        if l.startswith("|") or l.startswith("!"):
            for c in re.split(r"\|\||!!", l[1:]):
                cells.append(c)
        elif cells:
            cells[-1] += "\n" + l
    return cells


def body(c):
    # strip leading attribute section "attr=..|" if it exists (outside links/templates)
    depth = 0
    i = 0
    while i < len(c):
        if c.startswith("[[", i) or c.startswith("{{", i):
            depth += 1
            i += 2
            continue
        if c.startswith("]]", i) or c.startswith("}}", i):
            depth -= 1
            i += 2
            continue
        if c[i] == "|" and depth == 0:
            pre = c[:i]
            if "=" in pre:
                return c[i + 1:], pre
            return c, ""
        i += 1
    return c, ""


def main():
    text = clean(open(sys.argv[1], encoding="utf-8").read())
    tables = re.findall(r"^\{\|.*?^\|\}", text, flags=re.S | re.M)
    out = []
    for ti, tb in enumerate(tables):
        rows = re.split(r"^\|-.*$", tb, flags=re.M)
        for r in rows[1:]:
            cells = cells_of(r)
            name = None
            rng = None
            party = None
            title_party = None
            idx_date = None
            for k, c in enumerate(cells):
                b, attrs = body(c)
                for t in re.findall(r'title="([^"]*)"', attrs):
                    title_party = title_party or t
                sb = simplify(b)
                if name is None:
                    m = re.search(r"'''+(.+?)'''+", sb)
                    if m:
                        name = m.group(1).strip("'")
                        continue
                if rng is None:
                    m = RANGE_RE.search(sb)
                    if m and name is not None:
                        rng = (m.group(1), m.group(2))
                        idx_date = k
                        continue
                if rng is not None and party is None and k > idx_date:
                    if sb and not re.search(r"\d", sb) and len(sb) < 60 and "small" not in sb.lower() and "Vacant" not in sb:
                        party = sb.strip("'")
            if name is None and rng is None:
                continue
            num = simplify(body(cells[0])[0]) if cells else ""
            acting = bool(re.search(r"\bacting\b", simplify(r), re.I))
            rec = {"table": ti, "num": num, "name": name, "range": rng, "party": party, "title": title_party, "acting": acting}
            if rng:
                s, p1 = iso(rng[0])
                e, p2 = iso(rng[1]) if not re.match(r"[Ii]ncumbent|[Pp]resent", rng[1]) else (None, "day")
                rec.update(start=s, end=e, sp=p1, ep=p2)
            out.append(rec)
            print(ti, "|", num[:6], "|", "ACT" if acting else "", "|", name, "|", rec.get("start"), "|", rec.get("end"), "|", party, "|", title_party)
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
