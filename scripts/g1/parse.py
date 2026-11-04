"""Parse governor tables from Wikipedia wikitext. Usage: python -I parse.py <wikitext file> [out.json]"""
import re, sys, json

MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}
DROP_TPL = {"sfn", "efn", "refn", "efn-ua", "efn-lr", "cn", "citation needed", "nbsp", "snd", "sfnm", "r", "multiref", "cite web", "cite book", "cite news"}


def strip_templates(s, names=DROP_TPL):
    out, i = [], 0
    while i < len(s):
        if s.startswith("{{", i):
            m = re.match(r"\{\{\s*([^|}]+)", s[i:])
            name = m.group(1).strip().lower() if m else ""
            # find matching close
            depth, j = 0, i
            while j < len(s):
                if s.startswith("{{", j):
                    depth += 1; j += 2
                elif s.startswith("}}", j):
                    depth -= 1; j += 2
                    if depth == 0:
                        break
                else:
                    j += 1
            inner = s[i:j]
            if name in names or name.startswith("efn") or name.startswith("sfn"):
                pass
            else:
                out.append(inner)
            i = j
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def strip_refs(s):
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    return s


def clean(s):
    s = strip_refs(strip_templates(s))
    return s


def link_text(s):
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


DATE_RE = re.compile(r"(?:(January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:(\d{1,2}),\s*)?)?(\d{4})")


def parse_dates(txt):
    res = []
    for m in DATE_RE.finditer(txt):
        mon, day, yr = m.groups()
        if mon and day:
            res.append(("%s-%02d-%02d" % (yr, MONTHS[mon], int(day)), "day"))
        elif mon:
            res.append(("%s-%02d-01" % (yr, MONTHS[mon]), "month"))
        else:
            res.append(("%s-01-01" % yr, "year"))
    return res


def cell_value(c):
    # strip leading attributes "attr|value" (attr part has = and no [[ )
    c = c[1:] if c[:1] in "|!" else c
    m = re.match(r'^([^|\[{]*=[^|\[]*?)\|(?!\|)(.*)$', c, re.S)
    if m and "[[" not in m.group(1):
        return m.group(1), m.group(2)
    return "", c


def rows(text):
    tables = re.split(r"\n\{\|", text)
    for ti, t in enumerate(tables):
        t = t.split("\n|}")[0]
        for r in re.split(r"\n\|-[^\n]*", t):
            cells = []
            for line in r.split("\n"):
                if line.startswith("|") or line.startswith("!"):
                    # split inline || cells
                    for part in re.split(r"\|\||!!", line):
                        cells.append(part if part[:1] in "|!" else "|" + part)
                elif cells:
                    cells[-1] += "\n" + line
            yield ti, cells


def parse(text):
    text = clean(text)
    out = []
    for ti, cells in rows(text):
        vals = [cell_value(c) for c in cells]
        name_i = None
        for i, (a, v) in enumerate(vals):
            if re.search(r"'''\s*\[\[", v) or re.search(r"\{\{sortname", v, re.I) and "'''" in v:
                name_i = i; break
        if name_i is None:
            # vacancy rows
            for i, (a, v) in enumerate(vals):
                if re.search(r"''\s*(Vacant|vacant)", v) or re.search(r"Military|military rule", v) and "data-sort" not in a:
                    pass
            joined = " ".join(v for a, v in vals)
            if re.search(r"Vacant|vacant", joined) and parse_dates(joined):
                out.append({"table": ti, "name": "(vacant)", "raw": link_text(joined)[:200]})
            continue
        name = link_text(re.sub(r"\{\{[Ss]mall\|[^}]*\}\}", "", vals[name_i][1]).split("<br")[0])
        name = re.sub(r"\{\{sortname\|([^|}]*)\|([^|}]*)[^}]*\}\}", r"\1 \2", name)
        rest = vals[name_i + 1:]
        term_i = None
        for i, (a, v) in enumerate(rest):
            if parse_dates(v) and re.search(r"January|February|March|April|May|June|July|August|September|October|November|December|\d{4}", v):
                term_i = i; break
        term = rest[term_i][1] if term_i is not None else ""
        party = rest[term_i + 1][1] if term_i is not None and term_i + 1 < len(rest) else ""
        succ = rest[term_i + 2][1] if term_i is not None and term_i + 2 < len(rest) else ""
        acting = bool(re.search(r"[Aa]cting|acted", link_text(term) + " " + link_text(succ) + " " + link_text(vals[name_i][1])))
        out.append({"table": ti, "name": name, "term_raw": link_text(term)[:200],
                    "dates": parse_dates(link_text(term)), "party_raw": link_text(party)[:80],
                    "acting_hint": acting, "succ_raw": link_text(succ)[:120], "name_cell": link_text(vals[name_i][1])[:150]})
    return out


if __name__ == "__main__":
    res = parse(open(sys.argv[1], encoding="utf-8").read())
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for r in res:
        if "dates" in r:
            print(r["table"], "|", r["name"], "|", r["term_raw"][:70], "|", r["party_raw"], "|", "ACT" if r["acting_hint"] else "", "|", r["succ_raw"][:60])
        else:
            print(r["table"], "| VACANT |", r["raw"][:120])
