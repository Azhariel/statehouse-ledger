"""Build governors_g4.json from the per-state extraction output.
Usage: python -I build.py <work_dir> <out_json>
"""
import json, sys, os
from datetime import date

CUTOFF = '1856-01-01'

STATES = {
    'MT': dict(file='Montana', name='Montana', admitted='1889-11-08', notes=[
        "Robert Burns Smith (1897-1901): Wikipedia labels his party 'Fusion' (Democratic-Populist fusion ticket; a footnote says Glashan labels him only as Populist). Kept as 'Fusion'.",
    ]),
    'NE': dict(file='Nebraska', name='Nebraska', admitted='1867-03-01', notes=[
        "Statehood was March 1, 1867, but the first state governor (David Butler) took office March 27, 1867. The 26 days in between were covered by the territorial administration and are not represented (territorial governors excluded).",
        "William H. James (1871-1873) was secretary of state acting as governor after Butler's impeachment and removal; Wikipedia lists him unnumbered, so acting=true.",
        "1891-1893 Boyd/Thayer dispute: Wikipedia lists James E. Boyd (D), then John Milton Thayer (R) after the Nebraska Supreme Court ruled Boyd ineligible, then Boyd again after the U.S. Supreme Court reversed. Recorded as three consecutive terms exactly as listed.",
        "Silas A. Holcomb and William A. Poynter: Wikipedia labels party as 'Fusion' (Populist-Democratic fusion).",
    ]),
    'NV': dict(file='Nevada', name='Nevada', admitted='1864-10-31', notes=[
        "Statehood was October 31, 1864, but Henry G. Blasdel took office December 5, 1864. The 35 days in between were covered by the territorial administration and are not represented.",
        "Wikipedia labels several lieutenant governors who took over after a death/resignation as 'Lieutenant governor acting' (all numbered as governors). acting=true for those whose whole tenure was in that capacity (Frank Bell, Denver S. Dickerson, Morley Griswold). Reinhold Sadler, Vail Pittman and Bob Miller started as acting governors and were later elected in their own right; Wikipedia shows each as one continuous row, so each is one term with acting=false.",
        "Party labels 'Silver' and 'Silver-Democratic' (John Sparks, Denver S. Dickerson) are as shown on Wikipedia (Silver Party).",
    ]),
    'NH': dict(file='New_Hampshire', name='New Hampshire', admitted=None, notes=[
        "Ralph Metcalf (Know Nothing, 1855-1857) was in office on 1856-01-01 and is the first term listed.",
        "Unnumbered acting governors (presidents of the Senate) included with acting=true: Vesta M. Roy (1982-83), Ralph D. Hough (1993), Chuck Morse (2017).",
    ]),
    'NJ': dict(file='New_Jersey', name='New Jersey', admitted=None, notes=[
        "Rodman M. Price (1854-1857) was in office on 1856-01-01 and is the first term listed.",
        "Unnumbered acting governors (Senate presidents / Assembly speakers / attorney general) included with acting=true, including the January 2002 sequence DiFrancesco -> John Farmer Jr. (about 90 minutes on 2002-01-08) -> John O. Bennett -> Richard Codey.",
        "Donald DiFrancesco (2001-2002) and Richard Codey (2004-2006) were constitutionally acting governors as Senate presidents, but Wikipedia numbers them as governors (51 and 53), so acting=false for those two terms.",
        "Mikie Sherrill took office 2026-01-20 and is the sitting governor.",
    ]),
    'NM': dict(file='New_Mexico', name='New Mexico', admitted='1912-01-06', notes=[
        "Statehood was January 6, 1912, but William C. McDonald took office January 15, 1912. The 9 days in between were covered by the last territorial governor and are not represented.",
    ]),
    'NY': dict(file='New_York', name='New York', admitted=None, notes=[
        "Myron H. Clark (1855-1857) was in office on 1856-01-01. Wikipedia labels his party 'Whig/Free Soil (fusion)' (footnote: widely labeled Whig, or Whig-Free Soil, or Anti-Nebraska). Kept verbatim.",
        "Reuben Fenton (1865-1869) is labeled 'Union' on Wikipedia (National Union ticket).",
        "New York lists no unnumbered acting governors in the main table; lieutenant governors who succeeded are numbered governors (acting=false).",
    ]),
    'NC': dict(file='North_Carolina', name='North Carolina', admitted=None, notes=[
        "Thomas Bragg (1855-1859) was in office on 1856-01-01 and is the first term listed.",
        "Civil War: no rival government ever held Raleigh; Wikipedia lists the Confederate-era governors (Ellis, Clark, Vance) as the state's governors. Zebulon Vance is labeled 'Conservative' (1862-1865), as is Jonathan Worth (1865-1868).",
        "1865-05-13 to 1865-05-29: Wikipedia shows the office vacant after the Civil War (Vance arrested). Recorded as '(vacant)', party_raw 'None'. This period was de facto Union military occupation, but Wikipedia labels it a vacancy, so '(vacant)' was used.",
        "William Woods Holden's first tenure (1865-05-29 to 1865-12-15) has no party on Wikipedia; the cell reads 'Provisional governor appointed by President' (colour coded nonpartisan/'Appointed'). party_raw kept as that literal label; central normalization should treat it as no party (Holden later served as a Republican).",
        "1867-1868 Reconstruction Acts military district: Wikipedia keeps Jonathan Worth as governor until 1868-07-01, so no separate military-rule term was added.",
        "Wikipedia labels lieutenant governors who succeeded as 'Lieutenant governor acting' (numbered as governors). acting=true where the whole tenure was in that capacity (Curtis Hooks Brogden, Thomas Michael Holt) and for Speakers of the Senate acting (Henry Toole Clark). Tod R. Caldwell, Thomas J. Jarvis and Luther H. Hodges were later elected in their own right; each is one continuous Wikipedia row, so acting=false.",
    ]),
}

# names whose whole numbered tenure was acting (see notes)
ACTING_NUMBERED = {
    'NV': {'Frank Bell', 'Denver S. Dickerson', 'Morley Griswold'},
    'NC': {'Henry Toole Clark', 'Curtis Hooks Brogden', 'Thomas Michael Holt', 'Warren Winslow'},
}


def main():
    work, out = sys.argv[1], sys.argv[2]
    result = {}
    for code, cfg in STATES.items():
        raw = json.load(open(os.path.join(work, cfg['file'] + '.json'), encoding='utf-8'))
        terms = []
        for t in raw:
            if t['end'] is not None and t['end'] < CUTOFF:
                continue
            name, party = t['name'], t['party_raw']
            acting = t['num'] in ('—', '–', '') or name in ACTING_NUMBERED.get(code, set())
            if name == 'Vacant':
                name, party, acting = '(vacant)', 'None', False
            if code == 'NC' and name == 'William Woods Holden' and t['start'] == '1865-05-29':
                party = 'Provisional governor appointed by President'
            term = dict(name=name, party_raw=party, start=t['start'], end=t['end'], acting=acting)
            if t['start_precision'] not in ('day', None) or t['end_precision'] not in ('day', None):
                term['date_precision'] = t['start_precision'] if t['start_precision'] != 'day' else t['end_precision']
            terms.append(term)
        terms.sort(key=lambda x: x['start'])
        result[code] = dict(state_name=cfg['name'], admitted=cfg['admitted'],
                            source='https://en.wikipedia.org/wiki/List_of_governors_of_' + cfg['file'],
                            terms=terms, notes=cfg['notes'])
        # continuity check
        print(f"== {code}: {len(terms)} terms, {terms[0]['name']} -> {terms[-1]['name']} (end={terms[-1]['end']})")
        for a, b in zip(terms, terms[1:]):
            gap = (date.fromisoformat(b['start']) - date.fromisoformat(a['end'])).days
            if abs(gap) > 1:
                print(f"   gap {gap}d: {a['name']} end {a['end']} -> {b['name']} start {b['start']}")
        for t in terms:
            if 'UNPARSED' in str(t['start']) + str(t['end']) or not t['party_raw']:
                print('   PROBLEM', t)
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
