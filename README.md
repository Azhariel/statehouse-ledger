# Statehouse Ledger

Party control of every US state, year by year, from 1856 to 2026, plus federal control (President, Senate, House) on a timeline below the map.

Live site: https://statehouse-ledger.vercel.app/

## How to read it

- Each year goes to the party in charge of a state on **July 1**, which is whoever held office for most of that year.
- The number in each state is the running lead: years for the leading party minus years for the other.
- The number is shown in the leading party's color, or in **white** when the party in charge right now is also the one ahead.
  - 40 years Republican, 10 Democratic, Democrats in charge now: red **30**.
  - 10 years Democratic, 5 Republican, Democrats in charge now: white **5**.

Two scoring rules:

- **Governor:** the year goes to the governor's party.
- **2 of 3:** the year goes to whichever party holds at least two of the governorship, the state Senate and the state House.
  - Otherwise the state is split and the year counts for nobody.
  - Where the legislature was nonpartisan (Nebraska since 1937, Minnesota from 1913 to 1973) or has no data, the governor decides.

You can change the start year to a preset, or type any year, such as your birth year. The URL keeps the current year, mode and start year, so a link opens the same view.

Keyboard: Space plays and pauses, the left and right arrow keys step one year.

## Start years

Counting starts at the chosen year, and earlier years are dimmed on the federal timeline. Each preset marks a turning point:

| Preset | Why |
|---|---|
| 1856 | The first presidential election with a Republican candidate (John C. Frémont), so the first Democrat versus Republican contest. Everything is counted. |
| 1900 | Right after the 1896 McKinley versus Bryan election, which began three decades of Republican dominance outside the South. |
| 1932 | Franklin D. Roosevelt's election and the New Deal coalition that kept Democrats in charge of Congress for most of the next 60 years. |
| 1964 | The Civil Rights Act and Barry Goldwater carrying the Deep South, the start of the Southern realignment. |
| 1980 | Ronald Reagan's election and the rise of the modern conservative movement and the Religious Right. |
| 2000 | Bush versus Gore and roughly the modern, sorted parties. It's also when TV maps settled on red for Republicans and blue for Democrats. |
| Custom | Any year from 1856 to 2026, such as the year you were born. |

Comparing 1856 with 1964 or later is the quickest way to see the realignment described below.

## Caveat: party labels are not ideology

The count follows party **names**, not positions, and what each party stood for has changed a lot. Don't read the older years as today's Democrats versus today's Republicans.

- **Southern Democrats.** For about a century after Reconstruction, a Democrat in the South usually meant a defender of segregation and one-party rule. On race and social issues they were closer to today's Republicans. A long blue streak in Mississippi or Texas mostly measures that, not a liberal electorate.
- **Northern Republicans.** Republicans in the Northeast and Midwest were often the more liberal party of their region, backing civil rights and, in some places, positions now associated with Democrats.
- **Economics didn't line up either.** Southern Democrats backed the early New Deal and wanted free trade. Republicans were the party of high tariffs and Northern business.
- **When the modern labels apply.** The parties sorted into their current shape over roughly 1964 to 2010, from the top of the ballot down:
  - presidential voting realigned first (1960s to 1980s);
  - then Congress (around 1994);
  - Southern statehouses last (mostly the 2000s and 2010s).

  The modern meaning of each label fits best from about the 1990s on.

That's why Texas and Georgia carry large blue numbers when counted from 1856. Pick a later start year to see the modern picture.

## Data

Compiled from Wikipedia:

- "List of governors of [State]"
- "Political party strength in [State]" (state Senate and House majorities)
- "Party divisions of United States Congresses"
- "List of presidents of the United States"

The page lists the judgment calls (Civil War "Union" parties, Reconstruction "Conservatives", North Dakota's Nonpartisan League and so on) and the known gaps in its "About the data" section.

## Running locally

It's a single static page with no build step for the site itself. Open `index.html` directly, or serve the folder:

```
python -m http.server 8000
```

D3 and topojson-client load from the jsDelivr CDN, so you need an internet connection.

## Rebuilding the data

The raw Wikipedia wikitext is saved in `data/raw/wikitext/`, so everything below runs offline.

```
python -I scripts/legislature.py data/raw/wikitext/strength data/raw/legislature.json
python -I scripts/build.py .
python -I scripts/check.py .
python -I scripts/check_legislature.py .
```

- `legislature.py` turns the "Political party strength" tables into `data/raw/legislature.json`.
- `build.py` merges the governor, legislature and Congress data into `data/dataset.js`, which the page loads, and `data/governors.json`, the full governor term list.
- `check.py` and `check_legislature.py` run sanity and spot checks.
- `scripts/g1` to `scripts/g6` and `scripts/congress` are the parsers that produced `data/raw/governors_g*.json` and `data/raw/congress.json`.

## Project layout

```
index.html            the whole app (HTML, CSS, JS)
og-image.png          social preview image (1200x630)
data/dataset.js       built dataset loaded by the page
data/governors.json   every governor term, with raw party labels
data/raw/             source wikitext and intermediate JSON
scripts/              parsers, build and checks
```

`.vercelignore` keeps `data/raw/` and `scripts/` out of the deployed site.

## License

The data comes from Wikipedia contributors under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), and the derived data in this repo is shared under the same license.
