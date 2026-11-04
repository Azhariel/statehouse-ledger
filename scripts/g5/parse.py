"""Parse governor tables from Wikipedia wikitext. Usage: python -I parse.py <wikitext_dir> <out_json>"""
import json, re, sys, os
from datetime import date

MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}


def strip_refs(s):
    s = re.sub(r"<ref[^>/]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    # remove {{efn ...}} and {{sfn ...}} with nesting
    out, i = [], 0
    while i < len(s):
        m = re.match(r"\{\{\s*(efn|sfn|refn|efn-lr|NoteTag|Efn)\b", s[i:], flags=re.I)
        if m:
            depth, j = 0, i
            while j < len(s):
                if s.startswith("{{", j):
                    depth += 1; j += 2; continue
                if s.startswith("}}", j):
                    depth -= 1; j += 2
                    if depth == 0:
                        break
                    continue
                j += 1
            i = j
            continue
        out.append(s[i]); i += 1
    return "".join(out)


def split_cells(row):
    """Split a table row into cells (attrs, content)."""
    cells = []
    for line in row.split("\n"):
        if not line or line[0] not in "|!":
            if cells:
                cells[-1] += "\n" + line
            continue
        body = line[1:]
        # inline '||' separators
        parts = re.split(r"\|\||!!", body)
        cells.extend(parts)
    res = []
    for c in cells:
        # attribute separator: single '|' not inside [[ ]] or {{ }}
        depth, idx = 0, -1
        k = 0
        while k < len(c):
            if c.startswith("[[", k) or c.startswith("{{", k):
                depth += 1; k += 2; continue
            if c.startswith("]]", k) or c.startswith("}}", k):
                depth -= 1; k += 2; continue
            if c[k] == "|" and depth == 0:
                idx = k; break
            k += 1
        if idx >= 0 and ("=" in c[:idx] or c[:idx].strip() == ""):
            res.append((c[:idx], c[idx + 1:]))
        else:
            res.append(("", c))
    return res


def plain(s):
    s = strip_refs(s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    s = s.replace("'''", "").replace("''", "").replace("&nbsp;", " ").replace("&ndash;", "–")
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})"
                     r"|(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})"
                     r"|\b(\d{4})\b")


def parse_date(s):
    m = DATE_RE.search(s)
    if not m:
        return None, None
    if m.group(1):
        return date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat(), "day"
    if m.group(4):
        return date(int(m.group(5)), MONTHS[m.group(4)], 1).isoformat(), "month"
    return date(int(m.group(6)), 1, 1).isoformat(), "year"


def parse_table(tbl):
    rows = re.split(r"\n\|-[^\n]*", tbl)
    out = []
    for row in rows:
        cells = split_cells(row.strip())
        name_i = None
        for i, (a, c) in enumerate(cells):
            if ("'''" in c and "File:" not in c) or (plain(c) in ("Vacant", "Military rule", "Military government") and i < 4):
                name_i = i; break
        if name_i is None:
            continue
        number = ""
        for a, c in cells[:name_i]:
            if not c.strip().startswith("[[File") and "data-sort" not in a and "background" not in a and c.strip() and "Image" not in c:
                number = c.strip()
        raw_name = cells[name_i][1]
        nm = re.search(r"'''(.*?)'''", raw_name)
        name = plain(nm.group(1)) if nm else plain(raw_name)
        term_i = None
        for i in range(name_i + 1, len(cells)):
            if re.search(r"&ndash;|–|—", cells[i][1]) and DATE_RE.search(cells[i][1]):
                term_i = i; break
        if term_i is None:
            out.append({"name": name, "error": "no term", "rawcells": [c for _, c in cells]})
            continue
        term = strip_refs(cells[term_i][1])
        parts = re.split(r"&ndash;|–|—", term, maxsplit=1)
        start, sp = parse_date(parts[0])
        endtxt = parts[1] if len(parts) > 1 else ""
        endtxt_clean = re.sub(r"\{\{small\|.*", "", endtxt, flags=re.I | re.S)
        if re.search(r"[Ii]ncumbent", endtxt_clean) or not DATE_RE.search(endtxt_clean):
            end, ep = None, None
        else:
            end, ep = parse_date(endtxt_clean)
        party = plain(cells[term_i + 1][1]) if term_i + 1 < len(cells) else ""
        party = re.sub(r"([-–/])\s+", r"\1", party)
        party_attr =cells[term_i + 1][0] if term_i + 1 < len(cells) else ""
        out.append({"number": plain(number), "name": name, "start": start, "start_precision": sp,
                    "end": end, "end_precision": ep, "party_cell": party, "term_raw": plain(term)[:200],
                    "name_raw": plain(raw_name)[:200]})
    return out


def main():
    d, outp = sys.argv[1], sys.argv[2]
    res = {}
    for fn in sorted(os.listdir(d)):
        txt = open(os.path.join(d, fn), encoding="utf-8").read()
        tables = re.findall(r"\{\|.*?\n\|\}", txt, flags=re.S)
        st = []
        for t in tables:
            if "sticky-header-multi" not in t:
                continue
            cap = re.search(r"\|\+([^\n]*)", t)
            cap = cap.group(1) if cap else ""
            st.append({"caption": cap, "rows": parse_table(t)})
        res[fn] = st
    json.dump(res, open(outp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


main()
