"""Rough parser for List_of_governors_of_<State> wikitext. Prints candidate terms for review."""
import json
import re
import sys

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}


def strip_nested(text, open_tok, close_tok, name_re):
    out = []
    i = 0
    while i < len(text):
        m = name_re.match(text, i) if text.startswith(open_tok, i) else None
        if m:
            depth = 0
            j = i
            while j < len(text):
                if text.startswith(open_tok, j):
                    depth += 1
                    j += len(open_tok)
                elif text.startswith(close_tok, j):
                    depth -= 1
                    j += len(close_tok)
                    if depth == 0:
                        break
                else:
                    j += 1
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def clean(text):
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = strip_nested(text, "{{", "}}", re.compile(r"\{\{\s*(efn|sfn|refn|cite|Cite|r\||NoteTag|ref)", re.I))
    return text


def split_attr(cell):
    # cell content without leading |/!; strip attributes before a top-level |
    depth_sq = depth_br = 0
    for i, ch in enumerate(cell):
        if cell.startswith("[[", i):
            depth_sq += 1
        elif cell.startswith("]]", i):
            depth_sq -= 1
        elif cell.startswith("{{", i):
            depth_br += 1
        elif cell.startswith("}}", i):
            depth_br -= 1
        elif ch == "|" and depth_sq == 0 and depth_br == 0:
            return cell[:i], cell[i + 1:]
    return "", cell


def plain(s):
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"\{\{(?:small|Small)\|(.*?)\}\}", r"\1", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})")


def iso(m):
    return "%s-%02d-%02d" % (m.group(3), MONTHS[m.group(1)], int(m.group(2)))


def main(path):
    raw = open(path, encoding="utf-8").read()
    rows = re.split(r"\n\|-[^\n]*", raw)
    out = []
    cur = None
    for row in rows:
        row = clean(row)
        lines = [l for l in row.split("\n") if l.startswith("|") or l.startswith("!")]
        cells = []
        for l in lines:
            if l.startswith("|}") or l.startswith("{|") or l.startswith("|+"):
                continue
            attr, content = split_attr(l[1:])
            cells.append((attr, content))
        govcell = [c for c in cells if c[1].lstrip().startswith("'''[[") or c[1].lstrip().startswith("'''{{")]
        if govcell:
            name = plain(govcell[0][1].split("<br")[0])
            idx = cells.index(govcell[0])
            term = None
            party = None
            elec = None
            title = None
            for a, c in cells:
                if "title=" in a and not c.strip():
                    tm = re.search(r'title="([^"]*)"', a)
                    if tm and title is None:
                        title = tm.group(1)
            for k in range(idx + 1, len(cells)):
                a, c = cells[k]
                if term is None and DATE_RE.search(c) or (term is None and re.search(r"\d{4}", c) and "–" in c):
                    term = c
                    if k + 1 < len(cells):
                        party = plain(cells[k + 1][1])
                    if k + 2 < len(cells):
                        elec = plain(cells[k + 2][1])
                    break
            dates = [iso(m) for m in DATE_RE.finditer(term or "")]
            cur = {"name": name, "dates": dates, "term_plain": plain(term or "")[:120],
                   "party": party, "title": title, "elec": elec, "raw_term": term}
            cur["extra"] = []
            out.append(cur)
        elif cur is not None:
            for a, c in cells:
                pc = plain(c)
                if ("Party" in c or "party" in c.lower()) and pc:
                    cur["extra"].append(pc[:60])
                if "election" in c and pc:
                    cur.setdefault("extra_elec", []).append(pc[:40])
    for o in out:
        print(json.dumps(o, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
