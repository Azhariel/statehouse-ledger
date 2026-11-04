"""Extract governor rows from a state's wikitext table section.
Usage: python -I extract.py <wikitext_file> <start_line> <end_line> <out_json>
Writes a list of raw term dicts (pre-filtering) and prints a review table.
"""
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_rows import rows, split_cells, clean  # noqa: E402

MONTHS = {m: i for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
     'September', 'October', 'November', 'December'], 1)}
DATE_RE = re.compile(r'(?:(%s)\s+(?:(\d{1,2}),\s*)?)?(\d{4})' % '|'.join(MONTHS))


def parse_date(s):
    s = s.strip()
    if re.search(r'incumbent', s, re.I):
        return None, None
    m = DATE_RE.search(s)
    if not m:
        return 'UNPARSED:' + s, None
    mon, day, yr = m.groups()
    if mon and day:
        return '%s-%02d-%02d' % (yr, MONTHS[mon], int(day)), 'day'
    if mon:
        return '%s-%02d-01' % (yr, MONTHS[mon]), 'month'
    return '%s-01-01' % yr, 'year'


def party_text(raw):
    # join <br> pieces: no space after a hyphen/slash, else a space
    raw = re.sub(r'([-/–])\s*<br\s*/?>\s*', r'\1', raw)
    raw = re.sub(r'<br\s*/?>', ' ', raw)
    return clean(raw)


def is_term_cell(txt):
    mon = '|'.join(MONTHS)
    return bool(re.match(r'^(?:(?:%s)\s+(?:\d{1,2},\s*)?)?(?:c\.\s*)?\d{4}\s*(?:/\s*)?–' % mon, txt))


def main():
    f, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    text = open(f, encoding='utf-8').read()
    terms = []
    for r in rows(text, a, b):
        cells = split_cells(r)
        texts = [clean(c) for _, c in cells]
        ti = next((i for i, t in enumerate(texts) if is_term_cell(t) and i > 0), None)
        if ti is None:
            continue
        name = texts[ti - 1].split(' / ')[0].strip()
        term_txt = texts[ti]
        parts = re.split(r'\s*/\s*–\s*/\s*', term_txt, maxsplit=1)
        if len(parts) < 2:
            parts = re.split(r'\s*–\s*', term_txt, maxsplit=1)
        start, sp = parse_date(parts[0])
        end_part = parts[1].split(' / (')[0] if len(parts) > 1 else ''
        end, ep = parse_date(end_part)
        party = party_text(cells[ti + 1][1]) if ti + 1 < len(cells) else ''
        rest = ' | '.join(texts[ti + 1:])
        num = texts[0]
        acting_hint = ('acting' in rest.lower().split('|')[1] if rest.count('|') >= 1 else False) \
            or '(acting)' in texts[ti - 1] or num in ('—', '', '–')
        terms.append(dict(name=name, party_raw=party, start=start, end=end,
                          start_precision=sp, end_precision=ep, num=num,
                          acting_hint=acting_hint, rest=rest[:160]))
    json.dump(terms, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for t in terms:
        print(f"{t['num']:>3} {t['start']} {t['end']} {'A' if t['acting_hint'] else ' '} "
              f"{t['name']} [{t['party_raw']}]  || {t['rest'][:90]}")


if __name__ == '__main__':
    main()
