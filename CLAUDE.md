# Elfia Arcen — working notes

Context for anyone (human or agent) picking this repo up cold. `README.md` documents
*what the site is*; this file documents *how it got here and what to watch out for*.

Site: a lean, information-only static rebuild of the Elfia website for **Elfia Arcen,
19 & 20 September 2026**, Kasteeltuinen Arcen. Served at <https://3w3.nl/elfia>.
No frameworks, no third-party requests, no build step at request time. The site is light
by default like elfia.com; a dark theme is opt-in via a toggle in the nav.

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
| `build/make-programme.py` | builds `programme.html` + the home page's area teaser |
| `build/make-ics.py` | builds both `.ics` files |
| `build/realm-aliases.json` | folds superseded realm names onto the map's names |

`make-lineup.py` prints any act with no label — add those to `lineup-labels.json` or they
render without a chip and count as "workshops & more" in the filter.

Pages **not** generated (hand-maintained): `map`, `visit`, `policy`, `faq`.
Adding a page means adding its nav entry to all the others.

## Styling

The look borrows from elfia.com deliberately, but only what is ours to take:

* **`IM Fell French Canon`** for headings and the wordmark — the display face the official
  site uses, open licence, **self-hosted** in `fonts/` (37 KB, `font-display:swap` so first
  paint never waits on it). Their other face, `Ode`, is a commercial MPF family served as
  `.otf` from their own server: not copied, not hotlinked.
* **Their palette**, read out of `styles.css`: cream `#EAE5D4`, beige `#FFFBE8`,
  tan `#D8D2BB`, red `#8E2F2C`, poster maroon `#4D1014`, gold `#F0D589`.
* **Light by default.** `:root` carries the light palette and `:root[data-theme="dark"]` the
  dark one — `prefers-color-scheme` is deliberately *not* consulted, so a visitor on a
  dark-mode OS still gets the cream page the official site has. Dark is opt-in.
* **Ornament layer** (Sept 2026): a paper-grain background (inline SVG turbulence, ~330 bytes,
  no request), a fleuron `❦` after every top-level `h2` plus a hairline rule, corner ticks on
  `.card`, notched `clip-path` on `.btn`, a four-corner frame around the hero, and the
  timetable's stage headers in the display face. All scoped so the dense pages — the 7-column
  grid, the 124 vendor cards — stay calm. **A drop cap was tried and removed**: several page
  ledes start with a digit ("13 themagebieden", "124 kramen") and `::first-letter` turns that
  into a stray floating character.
* **Poster framing** — the double rule inside `.card` is our own CSS. Their equivalent is
  `border-image` off `ContentBorder.svg`; that SVG was not taken.

Everything their site does that we deliberately don't: a JS loading screen that sits at 18%,
client-side rendering of every list, Cookiebot, ~400 KB of script.

### Scripts

Two, both inline, both degrade to nothing:

* the theme toggle (below);
* **“Nu gaande” on `lineup.html`** — a panel above the timetable that reads the `.tt-row`
  entries straight out of the page (so it cannot drift from the schedule), works out what is
  playing on each stage and what follows, and draws a progress bar through the current set.
  It reads the clock via `Intl.DateTimeFormat` with `timeZone: "Europe/Amsterdam"`, so it is
  correct for a visitor whose device is in another zone — verified with the browser set to
  America/New_York. Four states: countdown before, live during, "nothing further today", and
  a sign-off after. The section carries `hidden` in the HTML and JS removes it, so without
  JavaScript it never appears. Day dates live in `DAY_DATES` in `make-lineup.py`;
* a ~10-line live search on `vendors.html` — 124 stalls is past the point where scrolling
  works, and CSS `:has()` cannot match text. It filters `.ven` cards, hides realm blocks that
  end up empty, filters the A–Z list and reports a count. The input is `display:none` until the
  `js` class lands, so without JavaScript the full list is simply there.

* **the nav** — below `70rem` the ten links collapse into a hamburger. `<button>` with
  `aria-expanded` and `aria-controls`, a 44×44 target, Escape closes it and returns focus to
  the button, a click outside or on a link closes it, and resizing past the breakpoint resets
  it. Closed means `display:none`, so the links are not reachable by keyboard while hidden.
  The bar-to-X animation sits behind `prefers-reduced-motion`. Without JavaScript the button
  never appears and the menu falls back to the horizontally scrolling row it was before.

### The theme switch

A `<button role="switch" aria-checked>` styled as a pill: sun on the left, moon on the right,
a knob that slides between them. The knob moves via `left`/`right` rather than a transform, so
it stays put when the switch is inside a sticky nav. `aria-checked` is set on click and on
`DOMContentLoaded` (a returning dark-mode visitor must not get a switch that claims "off").
Hidden without JavaScript, like everything else.

### The language switch

A bordered pill with an **inline SVG flag** plus the language code — the Union Jack on Dutch
pages, the Dutch tricolour on English ones. Flags are inline SVG rather than emoji on purpose:
Windows has no flag emoji, so 🇬🇧 renders there as the letters "GB". Roughly 300 bytes each,
no request.

### Nav sizing

**The nav wrapped onto two lines at every width, including 1600px** — the eleven links plus
brand, EN and switch need 1048px and the shared `.wrap` is 1056px, which the flex gaps ate.
The nav now has its own wider `max-width:74rem`, `.navmenu` is `flex-wrap:nowrap`, and the
hamburger takes over below **70rem** (was 60rem). Verified: one line from 1180px up, hamburger
from 1100px down.

The regression that hid this: the breakpoint test only checked `scrollWidth > clientWidth`.
A wrapping flex row does not overflow, so it passed while looking broken. **Count the distinct
`top` values of the nav links instead.**

### The old theme toggle

A four-line inline script in every page head is the site's only JavaScript: it adds a `js`
class to `<html>`, restores `localStorage.theme`, and defines `elfiaTheme()` for the nav
button. It is inline and in the head on purpose — no extra request, and it runs before first
paint so a returning dark-mode visitor never sees a flash of cream. Without JavaScript the
toggle is `display:none` (via the `js` class) so no dead button is left behind, and the page
stays light. `build/make-lineup.py` emits the same script; the other generators inherit it
from their templates. Keep the three copies in sync.

## Design sweep (4 Sept 2026)

Measured, not eyeballed — a Playwright pass over all 20 pages at 320/768/1440 px computing
contrast, font sizes, tap targets and overflow, plus a static pass over meta and headings.
The audit's **first** run was wrong: `color-mix()` computes to `color(srgb 1 0.98 0.91)` and
the parser divided those 0–1 values by 255, inventing contrast failures everywhere. If you
re-run it, parse both `rgb()` and `color(srgb …)`.

Fixed from that pass:

* `hreflang` pointed at `https://elfia.nl/…` — the official site, where these pages do not
  exist. Now `https://3w3.nl/elfia/…`, with `canonical`, Open Graph, Twitter card and
  `theme-color` added to every page (link previews matter: the site gets shared on Reddit).
* `index.html` still carried the **old map**: `alt` describing "40 genummerde tuinlocaties"
  and intrinsic size 1600×1132 for an 1800×1273 image — wrong description and layout shift.
* `.grid-2` had a 19rem minimum track, wider than a 320px viewport — horizontal overflow on
  every page using it. All nine grid definitions now use `minmax(min(Xrem,100%),1fr)`.
* Heading jumps: `vendors.html` h1→h3 (added an h2), `policy.html` h1→h4 (added a section h2
  and demoted the stray h4).
* Tap targets under 24×24: header nav links (23px), footer nav links, and standalone links
  that fill their own paragraph (`p>a:only-child`).
* Text below 11px in nine places — chips, times, counts, labels.
* **Dark mode: the `.type.perf` chips were red on near-black, contrast 1.92.** Now a
  `--perf` token, dark red in light mode and a light rose in dark.
* A print stylesheet: the timetable prints as the per-stage list, chrome and provenance
  blocks are dropped, external URLs are printed after their link.

The 1×1 radio inputs in `.filters` still show up as "tap target too small". That is the
intended pattern — the `<label>` is the target — so it is a known false positive.

## "Nu gaande" density

The panel is built to be read in one glance on a phone: one compact row per stage, 66px each,
so all of them fit above the fold on a 360×640 screen. Stage label and end time share a line,
the act is one truncated line, the progress bar is 3px, and the next act sits on a single line
behind an arrow (the word "Hierna" is hidden on narrow screens — `font-size:0` plus a `→` in
`::before` — which buys horizontal room for the title).

`NOW_SKIP` in `make-lineup.py` keeps **Bandits Creek** and **Elfia Treasures** out of the
panel, the same two stages `make-ics.py` leaves out of the calendars: a roaming all-day act
and signing sessions are not what you plan the next hour around, and they crowded out the
five stages that are. They are still in the timetable itself.

**Watch for min-content overflow.** `grid-template-columns:1fr` has a min-content floor, so a
`white-space:nowrap` title inside made the card 419px wide in a 390px viewport. It needs
`minmax(0,1fr)` on the track plus `min-width:0` on the items. This is the second time this
exact trap bit — see the `.grid-2` note in the design sweep.

## The now-line

`lineup.html` draws a red rule across the grid at the current time, with the time in a badge
that fills the time gutter (and sticks to the left while the grid scrolls sideways). It is
placed by grid row plus a sub-row `margin-top`, so it lands on the exact minute rather than
snapping to the quarter. It only appears on the day that is actually today, and only inside
that day's range — the same `Intl.DateTimeFormat` Europe/Amsterdam clock the "nu gaande"
panel uses, and the same 60-second refresh. The grid carries `data-start` and `data-row` so
the script needs no hard-coded geometry.

To see it outside the event, fake the clock in the browser rather than editing the site:

```js
{const R=Date,F=new R("2026-09-19T14:00:00+02:00").getTime();
 class D extends R{constructor(...a){if(!a.length)super(F);else super(...a)}
   static now(){return F}} Date=D;}
```

## The timetable on a phone

Below `64rem` the grid used to be replaced by the per-stage list, full stop. There is now a
**Lijst / Rooster** switch (CSS-only radios, same pattern as the filters), defaulting to
Rooster. In Rooster mode the
grid scrolls horizontally inside `.tt-wide` with fixed 9.5rem columns and the time gutter
`position:sticky; left:0`.

Two things that cost real time and are worth knowing:

* `z-index` on `.tt-e` was **dead code** — the rule sat on a `position:static` element. It is
  now `position:relative; z-index:1`, which is what the rule always meant.
* The time gutter appeared to have text bleeding through it. It did not. The 2px grid `gap`
  between consecutive `.tt-t` cells let the column underneath show, and a 3× upscaled
  screenshot smeared those two pixel rows into what looked like a legible line of text. Never
  diagnose this kind of thing from a zoomed screenshot — sample the pixels. The cells now
  carry `margin-bottom:-2px; padding-bottom:2px` to close the gap, verified by scanning the
  rendered PNG for dark pixels left of the labels (zero).

The map also fitted to 180% of the viewport inside a scroll box on phones, so it looked cut
off with no affordance. It now fits the width, with an "open at full size" link for the
phone's own pinch-zoom.

## Traps

- **The API changed shape in early Sept 2026.** A slot's `activity` field now packs name
  and description into one string: `"Merulsa (A folk project led by...)"`. The generators
  split on the last parenthetical, keeping short ones (`(All Day)`) as part of the name.
  A diff that ignores this makes every act look replaced.
- **Genre chips are not in the API.** They are ours, in `lineup-labels.json`. Say so.
- **The 14-allergen list on `food.html` is not API data either** — it is the legal Annex II
  list of Regulation 1169/2011. It was first written from memory and only verified later
  against the [NVWA](https://www.nvwa.nl/onderwerpen/voedselveiligheid/allergenen/over-welke-allergenen-moet-ik-informatie-geven)
  on 4 Sept 2026: the fourteen items and their order match, as does the rule that oral
  allergen information is allowed provided the stall states you can ask. The source is now
  cited on the page. Anything on that page people with an allergy act on needs a citation —
  do not write it from memory.
- **Name normalisation folds diacritics.** `Żniwa` and `Zniwa` both appear in the source
  data and must collide, hence `unicodedata.normalize` in every key function.
- **Nav has 10 entries** (Team was dropped 4 Sept, like History before it). The nav has its
  own `max-width:74rem`; it stays on one line from 1180px up and the hamburger takes over below
  `70rem`. Adding an entry means re-measuring — count distinct link `top` values, not overflow.
- **The API's realm list is not trustworthy.** It holds 20 entries: two are superseded
  names kept alongside their replacements (Giostra Fortunia, Academy Hall — folded via
  `realm-aliases.json`), three areas on the map are missing from it entirely (Border to
  Fantasy, Bandits Creek, Elfia Academy), and several have a description but no stage, no
  traders and no place on the map. `make-programme.py` uses the **map** as the spine and
  labels the leftovers. `status`/`statusCode` do not discriminate — every entry is
  `False`/`active`.
- The 41 highlights *were* checked for stale past-edition entries: all were created between
  Apr and Sep 2026 and none mention an earlier year. The old hand-written page did carry
  stale acts (Sunfire Band, a 2025 ChelseaBoy blurb); regenerating removed them.
- **The map is no longer the castle-gardens map.** Since 4 Sept 2026 it is the Elfia
  festival map: 13 numbered themed areas plus three embassies. The old castle-gardens pin
  numbers (1–40 plus buildings A–F) are gone; anything referencing those is wrong.
  Facilities are icon-only on the image — catering, Elfia Elixir Bar, toilets (plus a
  wheelchair-accessible variant), lockers, changing rooms, cosplay repair, Elfia Treasures,
  first aid, an information point, a drinking-water tap and smoking areas. `map.html` is
  hand-maintained and now carries a **facilities-by-area list read off the image**, so the
  page still works for someone who cannot see or zoom the map — that is the whole point of
  that page. Re-read the image and update that list whenever the map changes.
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

**4 Sept 2026, later** — `history.html` removed (not useful for a practical site), nav
labels changed to Bezoekinformatie and Vendors, `programme.html` and the home page's realm
teaser rebuilt from the API, and the styling brought closer to elfia.com (see above).

**17 Sept 2026** (two days out) — re-pulled `programme`, `faqList`, `header`, `news`.
The timetable was **byte-identical** to 4 Sept (65 slots), so the `.ics` files did not change.
What did change, and where it went:

* **Parking.** News item #38 "The Roads to the Kingdom are Changing": Waterschap Limburg's
  Maas2050 dike works have fenced off or removed most of the free verge and village parking
  around Arcen. `visit.html` had *nothing* on parking, buses or bikes — it now leads its
  "Getting here" section with a warning and four options: castle car park ticket
  (kasteeltuinen.nl), the **Lomm car park with a free shuttle** (from the FAQ, not the news
  item — the news only lists three routes), bus 83/30 to stop Rotonde N271, and bike parking.
* **Cups.** News #39: Elixir Bars serve in Drach-oc cups with a **€2 deposit**. News #37: the
  nearest Geldmaat is ~400 m from the entrance, reachable with the re-entry stamp. Both on
  `food.html`; the stamp also on `visit.html`.
* **FAQ.** Elfia Temptation registration moved **15:00 → 14:30** and to the "Information
  Booth"; the accessibility answer was rewritten; the whole **Horses** category (3 questions,
  incl. "only 5 riders per day") was removed. Horses are still welcome per the pets answer and
  a €1 horse parking permit per an older news item, so `visit.html` and the short FAQ answer
  keep horses but drop the no-longer-published five-rider limit. Question count 61 → 58.
* **Programme data.** Caterers 19 → 23 (Unitea, Eselmeisterei, Franz, Holy crepe), traders
  124 → 138 (several moved realm, e.g. six from Folk Faire to Willow Way), highlights 41 → 44
  (the embassies, Erik The Viking), one new Academy workshop. Merlin's Sanctum now has stalls,
  so it moved from "Also announced" to "Market areas" on its own.
* **"Plan vooruit"** on `programme.html` had been wrong since the first build ("Folk Ball",
  "claim at Tourist Info"). Rewritten from the current node description plus FAQ times. The
  info booth is placed at Elfia Treasures because the API labels that stage
  "(Merch and Info Booth)" and the map puts the S and i icons together at Music Court.

One trader is named just **"11"** in the source (Zen Garden, jewellery). Reproduced as-is.

## Open

- `header` carries a live ticket banner (17 Sept: "Last Tickets Still Available for Elfia
  Arcen 19–20 September!"). Nothing on the site shows it. It is the most visitor-relevant fact in the API
  and the most volatile — baking it into static HTML can go stale the wrong way.
- 38 news articles; #37–#39 are used on `visit.html`/`food.html`, the rest unused. **Check
  news before every update** — the parking change was only announced there.
- The API still carries the "This is just the beginning, more program updates are coming
  soon" remark, so the matching warning on the line-up stays, even two days out.
- The official elfia.nl TLS certificate expired 22 Aug 2026.
