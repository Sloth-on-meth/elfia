# Elfia Arcen — working notes

Context for anyone (human or agent) picking this repo up cold. `README.md` documents
*what the site is*; this file documents *how it got here and what to watch out for*.

Site: a lean, information-only static rebuild of the Elfia website for **Elfia Arcen,
19 & 20 September 2026**, Kasteeltuinen Arcen. Served at <https://3w3.nl/elfia>.
No JavaScript, no frameworks, no webfonts, no build step at request time.

## The one thing to understand first

Almost all content comes from Elfia's own back-office API, which is **POST-only** and
CORS-restricted to `elfia.nl`. There is no linkable URL for it — `GET` returns `405`.

```sh
curl -s -X POST -H 'Origin: https://elfia.nl' --data 'lang=en' \
     https://bo-elfia.lusolab.com/api/programme > build/programme.json
```

The `programme` endpoint is the mother lode. Inside the `Arcen Castle Gardens` node:

| path | contents |
|---|---|
| `area[].slots[]` | the timetable |
| `highlightImage[categoryType=realms][].shops[]` | **caterers** → `food.html` |
| `highlightImage[categoryType=realms][].exhibitors[]` | **traders** → `vendors.html` |
| `highlightImage[categoryType=highlight]` | act/guest highlights |
| `highlightImage[categoryType=workshop]` | academy workshops |

**elfia.com fetches `shops` and `exhibitors` on every page load and renders neither.**
No script on their site references either field. That is why visitors cannot find a
caterer list anywhere — it does not exist as a published page. This site is the only
place that data is surfaced, which is why every page built from it carries a
`.srcnote` provenance block.

Other endpoints: `faqList`, `news` (36 articles, unused here), `header` (live ticket
banner, unused), `termsAndConditions`, `winnerList` (**real names — do not republish**),
`getInvolved?programmeId=1` (application categories; needs the param or returns
`{"code":104}`), plus `enquiry` and `chatBot` — both **write** endpoints, never call them.

## Build

Everything generated lives under `build/`. One command rebuilds it all:

```sh
sh build/build-all.sh
```

| file | does |
|---|---|
| `build/programme.json` | API snapshot — refresh with the curl above |
| `build/lineup-labels.json` | **editorial** genre/type chips, keyed by normalised act name |
| `build/templates/*.html` | prose for food & vendors pages, with `<!--MARKER-->` data slots |
| `build/make-lineup.py` | builds `lineup.html` + `en/lineup.html` from scratch |
| `build/make-food.py` | fills the markers in the food templates |
| `build/make-vendors.py` | fills the markers in the vendors templates |
| `build/make-ics.py` | builds both `.ics` files |

`make-lineup.py` prints any act with no label — add those to `lineup-labels.json` or they
render without a chip and count as "workshops & more" in the filter.

Pages **not** generated (hand-maintained): `index`, `programme`, `map`, `visit`, `policy`,
`faq`, `team`, `history`. Adding a page means adding its nav entry to all the others.

## Traps

- **The API changed shape in early Sept 2026.** A slot's `activity` field now packs name
  and description into one string: `"Merulsa (A folk project led by...)"`. The generators
  split on the last parenthetical, keeping short ones (`(All Day)`) as part of the name.
  A diff that ignores this makes every act look replaced.
- **Genre chips are not in the API.** They are ours, in `lineup-labels.json`. Say so.
- **Name normalisation folds diacritics.** `Żniwa` and `Zniwa` both appear in the source
  data and must collide, hence `unicodedata.normalize` in every key function.
- **Nav has 11 entries** and only just fits the 66rem wrap at desktop width; item font and
  padding were tightened for it. A twelfth entry overflows into the horizontal scroll.
- **The map is no longer the castle-gardens map.** Since 4 Sept 2026 it is the Elfia
  festival map: 13 themed areas plus three embassies, no numbered locations. Anything
  referencing pin numbers (`food.html` used to) is wrong.
- Filtering on every page is pure CSS `:has()` — Safari 15.4+, Chrome 105+, Firefox 121+.
  Older browsers show everything, which is the correct degradation.

## History

**26–27 Aug 2026** — line-up page rebuilt: category filter (All/Music/Shows/Workshops),
Music A–Z index, calendar downloads. Two `.ics` files added. Fixed 30-minute blocks
clipping their titles.

**26–27 Aug 2026** — dug through the API, found `shops` and built `food.html`: caterers by
realm, dietary filter, and an allergen section. The dietary labels are only four values
and 5 of the stalls carry none, so the page states plainly that this is **not** an allergen
declaration and points people at the stall and at the medical-exemption in `policy.html`.

**26–27 Aug 2026** — found 110 unused `exhibitors` and built `vendors.html` (market, by
realm, with an A–Z index). Added the `.srcnote` provenance block to line-up, food and
vendors after a Reddit thread where a visitor could not find any caterer list.

**4 Sept 2026** — new festival map committed. Re-pulled the API and found the line-up
badly stale: **Giostra Fortunia → La Piazza Dei Sogni**, **Academy Hall → Elfia Academy**,
two new stages (**Bandits Creek**, **Elfia Treasures**), 16 acts added, 2 removed, day now
starting at 10:00. Caterers 14 → 19 entries, traders 110 → 124. Rebuilt everything and
moved all generators into `build/` — the previous ones lived in a scratch directory and
were lost, which is why they are committed now.

Bandits Creek and Elfia Treasures are **deliberately excluded from the `.ics` files**
(`EXCLUDED_STAGES` in `make-ics.py`): a roaming all-day act, quarter-hour line-dancing
slots and signing sessions are calendar clutter.

## Open

- `programme.html` is stale: it lists ten realms and eleven highlights; the API has
  **20 realms and 41 highlights**, and the ten names barely overlap.
- `header` carries a live ticket banner (currently "Only 643 Legendary Elf Sunday Tickets
  Left!"). Nothing on the site shows it. It is the most visitor-relevant fact in the API
  and the most volatile — baking it into static HTML can go stale the wrong way.
- 36 news articles unused.
- The official elfia.nl TLS certificate expired 22 Aug 2026.
