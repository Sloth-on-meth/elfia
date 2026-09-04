#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Elfia Arcen line-up pages (NL + EN) from the programme API.

    python3 make-lineup.py [site-root] [programme.json] [labels.json]

Re-snapshot the programme with:
    curl -s -X POST -H 'Origin: https://elfia.nl' --data 'lang=en' \
         https://bo-elfia.lusolab.com/api/programme > programme.json

NOTE on the API shape (changed early Sept 2026): a slot's `activity` field now packs
name and description into one string as "Name (description)". This script splits them;
a short trailing parenthetical (<= 28 chars, e.g. "(All Day)") is kept as part of the name.

NOTE on labels: the genre/type chips are NOT in the API — they are editorial and live in
labels.json, keyed by a normalised act name. An act with no entry renders without a chip
and counts as a workshop/other for the filter.
"""
import html, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PROG = Path(sys.argv[2] if len(sys.argv) > 2 else "programme.json")
LABELS = json.loads(Path(sys.argv[3] if len(sys.argv) > 3 else "lineup-labels.json")
                    .read_text(encoding="utf-8"))

EVENT = "Arcen Castle Gardens"
DAYS = ["Saturday", "Sunday"]
# column order: the five original stages first, so returning visitors keep their bearings
STAGE_ORDER = ["La Piazza Dei Sogni", "Folk Faire", "Music Court", "Bard's Theater",
               "Elfia Academy", "Bandits Creek", "Elfia Treasures"]
ROW = 29           # px per quarter hour, matches style.css

clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()
def key(s):
    """Normalised act name: diacritics folded, so Żniwa and Zniwa collide on purpose."""
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())
esc = lambda s: html.escape(s, quote=False)


def split_activity(s):
    """'Name (description)' -> ('Name', 'description'). Short parentheticals stay in the name."""
    s = clean(s)
    m = re.match(r"^(.*?)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)$", s)
    if m and len(m.group(2)) > 28:
        return m.group(1).strip(), m.group(2).strip()
    return s, ""


def mins(t):
    h, m = map(int, t.split(":")[:2])
    return h * 60 + m


def read_days(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    ev = [p for p in doc["resultProgramme"] if p["title"] == EVENT]
    if not ev:
        sys.exit(f"event {EVENT!r} not in payload")
    out = {d: {} for d in DAYS}

    def walk(o):
        if isinstance(o, dict):
            if "slots" in o and "name" in o and "dayDate" in o:
                stage = clean(o["name"])
                # the back-office keeps a pseudo-stage carrying the "more updates" remark
                if not stage.startswith("This is just") and o["dayDate"] in out:
                    acts = out[o["dayDate"]].setdefault(stage, [])
                    for s in o["slots"]:
                        name, desc = split_activity(s["activity"])
                        lab = LABELS.get(key(name), {})
                        acts.append(dict(start=s["activityFromStr"][:5], end=s["activityToStr"][:5],
                                         name=name, desc=desc,
                                         cls=lab.get("cls", ""), tag=lab.get("tag", "")))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(ev[0])
    for d in out:
        for st in out[d]:
            out[d][st].sort(key=lambda a: (mins(a["start"]), mins(a["end"])))
    return out


def cat(cls):
    return "music" if "genre" in cls else ("show" if "perf" in cls else "work")


def stages_of(day_acts):
    known = [s for s in STAGE_ORDER if s in day_acts]
    return known + sorted(s for s in day_acts if s not in STAGE_ORDER)


def build_day(day_acts, day_id):
    """Returns (grid_html, list_html, meta)."""
    stages = stages_of(day_acts)
    allt = [t for st in stages for a in day_acts[st] for t in (a["start"], a["end"])]
    lo = min(mins(t) for t in allt) // 60 * 60
    hi = -(-max(mins(t) for t in allt) // 60) * 60
    quarters = (hi - lo) // 15
    row = lambda t: (mins(t) - lo) // 15 + 2

    g = [f'<div class="tt-h" style="grid-column:1;grid-row:1">{{time}}</div>']
    for i, st in enumerate(stages, start=2):
        have = {cat(a["cls"]) for a in day_acts[st]}
        miss = " ".join("n-" + c for c in ("music", "show", "work") if c not in have)
        g.append(f'<div class="tt-h{" " + miss if miss else ""}" '
                 f'style="grid-column:{i};grid-row:1">{esc(st)}</div>')
    for q in range(quarters + 1):
        m = lo + q * 15
        if m % 60 == 0:
            g.append(f'<div class="tt-t" style="grid-column:1;grid-row:{q + 2}">{m//60:02d}:00</div>')

    for i, st in enumerate(stages, start=2):
        for a in day_acts[st]:
            dur = mins(a["end"]) - mins(a["start"])
            # a roaming act spanning most of the day shares its column with real slots,
            # so it is tinted and painted underneath them rather than colliding
            size = (" allday" if dur >= 360 else
                    " s0" if dur <= 15 else " s1" if dur <= 30 else
                    " s2" if dur <= 45 else " s3" if dur <= 60 else "")
            chip = f'<i class="{a["cls"]}">{esc(a["tag"])}</i>' if a["tag"] else ""
            desc = f'<span>{esc(a["desc"])}</span>' if a["desc"] else ""
            title = f'{a["start"]}–{a["end"]}  {a["name"]}' + (f' — {a["desc"]}' if a["desc"] else "")
            g.append(f'<div class="tt-e{size}" title="{html.escape(title, quote=True)}" '
                     f'style="grid-column:{i};grid-row:{row(a["start"])}/{row(a["end"])}">'
                     f'<time>{a["start"]}–{a["end"]}</time><b>{esc(a["name"])}</b>{chip}{desc}</div>')

    grid = (f'<div class="tt-grid" style="--cols:{len(stages)};'
            f'grid-template-rows:auto repeat({quarters},{ROW}px)">' + "".join(g) + "</div>")

    lst = []
    for st in stages:
        rows = []
        for a in day_acts[st]:
            chip = f'<i class="{a["cls"]}">{esc(a["tag"])}</i>' if a["tag"] else ""
            desc = f'<span>{esc(a["desc"])}</span>' if a["desc"] else ""
            rows.append(f'<div class="tt-row"><time>{a["start"]}–{a["end"]}</time>'
                        f'<div><b>{esc(a["name"])}</b>{chip}{desc}</div></div>')
        lst.append(f'<div class="tt-stage"><h3>{esc(st)}</h3>{"".join(rows)}</div>')

    n = sum(len(v) for v in day_acts.values())
    counts = {c: sum(1 for st in stages for a in day_acts[st] if cat(a["cls"]) == c)
              for c in ("music", "show", "work")}
    meta = dict(stages=len(stages), n=n, counts=counts,
                span=f'{lo//60:02d}:00–{hi//60:02d}:00', id=day_id)
    return grid, '<div class="tt-list">' + "".join(lst) + "</div>", meta


THEME_SCRIPT = (
    '<script>document.documentElement.classList.add("js");'
    'try{if(localStorage.theme==="dark")document.documentElement.dataset.theme="dark"}catch(e){}\n'
    'function elfiaTheme(){var r=document.documentElement,d=r.dataset.theme==="dark";'
    'if(d)r.removeAttribute("data-theme");else r.dataset.theme="dark";'
    'try{localStorage.theme=d?"light":"dark"}catch(e){}}</script>')

SRCNOTE = {
 "nl": '<p class="srcnote"><strong>Waar komt dit vandaan?</strong> Deze lijst komt rechtstreeks '
       'uit de programma-API van Elfia en is ongeredigeerd overgenomen — namen, omschrijvingen '
       'en indeling zijn precies zoals de organisatie ze aanlevert. Elfia toont deze gegevens '
       'zelf nergens op de site, dus er is geen officiële pagina om het tegen te controleren. '
       'Het kan onvolledig of verouderd zijn en tot aan het evenement nog wijzigen. Dit is geen '
       'officiële uitgave van Elfia. De genre-aanduidingen zijn wel van ons.</p>',
 "en": '<p class="srcnote"><strong>Where does this come from?</strong> This list is taken '
       'straight from Elfia’s programme API and reproduced unedited — names, descriptions and '
       'grouping are exactly as the organisers supply them. Elfia does not display this data '
       'anywhere on their own site, so there is no official page to check it against. It may be '
       'incomplete or out of date and can still change before the event. This is not an official '
       'Elfia publication. The genre chips are ours.</p>',
}

T = {
 "nl": dict(file="lineup.html", lang="nl", pre="", other="en/lineup.html", otherlang="en",
   otherlabel="EN", skip="Naar de inhoud", nav="Programma",
   title="Programma — Elfia Arcen 2026",
   metadesc="Het volledige programma van Elfia Arcen 2026: alle optredens per podium en per tijdslot, zaterdag 19 en zondag 20 september.",
   h1="Programma",
   head="Alle optredens per podium en tijdslot. Op een smal scherm wordt het rooster een lijst per podium.",
   tabs=["Zaterdag 19 sept", "Zondag 20 sept"], az="Muziek A–Z", agenda="In je agenda",
   flabel="Filter op soort", f=["Alles", "Muziek", "Shows", "Workshops &amp; meer"],
   dayh=["Zaterdag 19 september", "Zondag 20 september"], days=["Za", "Zo"],
   stages="podia", count=["{} programmaonderdelen", "{} muziekoptredens", "{} shows",
                          "{} workshops &amp; meer"],
   warn="Dit is nog niet alles — er volgen meer programma-updates. Tijden kunnen wijzigen; kijk op de dag zelf op de borden bij de podia.",
   ics_lead="Alle {} muziekoptredens als agendabestand:", ics_music="Muziek in je agenda",
   ics_all="Volledig programma",
   az_lede="Elke muziekact van het weekend op alfabet, met alle speeltijden. Handig om te zien of je twee favorieten kunt combineren.",
   ag_h="Zet het programma in je agenda",
   ag_lede="Twee .ics-bestanden — tijden staan in Europe/Amsterdam (CEST), dus ze kloppen ook als je uit een andere tijdzone komt.",
   ag_cards=[("Google Agenda","Download het bestand, ga in Google Agenda naar <b>Instellingen → Importeren en exporteren → Importeren</b>, kies het bestand en de agenda waarin het mag. Maak eventueel eerst een aparte agenda “Elfia” aan, dan kun je alles in één klik weer weghalen."),
             ("Apple Agenda / iPhone","Open het gedownloade bestand; iOS en macOS vragen dan in welke agenda de afspraken mogen."),
             ("Outlook","<b>Bestand → Openen en exporteren → Importeren/exporteren → een iCalendar-bestand importeren</b>, of sleep het bestand naar je agenda.")],
   ag_note="Let op: het programma is nog niet definitief. Als er updates komen, download je het bestand opnieuw — afspraken met dezelfde naam en tijd worden door de meeste agenda-apps overschreven in plaats van gedupliceerd.",
   dl_music="Muziek ({} optredens, .ics)", dl_all="Volledig programma ({} items, .ics)"),
 "en": dict(file="en/lineup.html", lang="en", pre="../", other="../lineup.html", otherlang="nl",
   otherlabel="NL", skip="Skip to content", nav="Line-up",
   title="Line-up — Elfia Arcen 2026",
   metadesc="The full line-up for Elfia Arcen 2026: every act by stage and time slot, Saturday 19 and Sunday 20 September.",
   h1="Line-up",
   head="Every act by stage and time slot. On a narrow screen the grid becomes a list per stage.",
   tabs=["Saturday 19 Sept", "Sunday 20 Sept"], az="Music A–Z", agenda="Add to calendar",
   flabel="Filter by type", f=["All", "Music", "Shows", "Workshops &amp; more"],
   dayh=["Saturday 19 September", "Sunday 20 September"], days=["Sat", "Sun"],
   stages="stages", count=["{} items", "{} music sets", "{} shows", "{} workshops &amp; more"],
   warn="This is just the beginning — more programme updates are coming. Times can change; check the boards at the stages on the day.",
   ics_lead="All {} music sets as a calendar file:", ics_music="Music in your calendar",
   ics_all="Full line-up",
   az_lede="Every music act of the weekend in alphabetical order, with all set times — handy for working out whether you can catch two favourites.",
   ag_h="Add the line-up to your calendar",
   ag_lede="Two .ics files — all times carry the Europe/Amsterdam (CEST) time zone, so they stay correct if you are travelling in from elsewhere.",
   ag_cards=[("Google Calendar","Download the file, then in Google Calendar go to <b>Settings → Import &amp; export → Import</b>, pick the file and the calendar it should land in. Creating a separate “Elfia” calendar first makes it easy to remove everything again in one go."),
             ("Apple Calendar / iPhone","Open the downloaded file; iOS and macOS will ask which calendar the events should go into."),
             ("Outlook","<b>File → Open &amp; Export → Import/Export → Import an iCalendar file</b>, or drag the file onto your calendar.")],
   ag_note="Note: the line-up is not final yet. When updates land, download the file again — most calendar apps overwrite events with the same name and time rather than duplicating them.",
   dl_music="Music ({} sets, .ics)", dl_all="Full line-up ({} items, .ics)"),
}


def nav_of(t):
    doc = (ROOT / ("food.html" if t["lang"] == "nl" else "en/food.html")).read_text(encoding="utf-8")
    nav = re.search(r'<nav class="nav">.*?</nav>', doc, re.S).group(0)
    nav = nav.replace(' aria-current="page"', "")
    nav = nav.replace(f'<a href="lineup.html">{t["nav"]}</a>',
                      f'<a href="lineup.html" aria-current="page">{t["nav"]}</a>')
    nav = re.sub(r'<a class="lang" href="[^"]*"[^>]*>[^<]*</a>',
                 f'<a class="lang" href="{t["other"]}" hreflang="{t["otherlang"]}" '
                 f'rel="alternate">{t["otherlabel"]}</a>', nav)
    return nav, re.search(r"<footer>.*?</footer>", doc, re.S).group(0)


def build(t, days):
    parts, totals = [], dict(all=0, music=0, show=0, work=0)
    for i, dname in enumerate(DAYS):
        grid, lst, meta = build_day(days[dname], f"day{i+1}")
        grid = grid.replace("{time}", "Tijd" if t["lang"] == "nl" else "Time")
        totals["all"] += meta["n"]
        for c in ("music", "show", "work"):
            totals[c] += meta["counts"][c]
        spans = "".join(
            f'<span class="c c-{k}">{w.format(n)}</span>' for k, w, n in zip(
                ("all", "music", "show", "work"), t["count"],
                (meta["n"], meta["counts"]["music"], meta["counts"]["show"], meta["counts"]["work"])))
        parts.append(
            f'<section id="{meta["id"]}"><div class="wrap">\n  <h2>{t["dayh"][i]}</h2>\n'
            f'  <p class="lede">{meta["stages"]} {t["stages"]} · {spans} · {meta["span"]}</p>\n'
            f'</div><div class="wrap tt-wide">{grid}</div><div class="wrap">{lst}</div></section>')

    # music A–Z
    uniq = {}
    for i, dname in enumerate(DAYS):
        for st, acts in days[dname].items():
            for a in acts:
                if cat(a["cls"]) != "music":
                    continue
                u = uniq.setdefault(a["name"], dict(tag=a["tag"], desc="", sets=[]))
                u["desc"] = u["desc"] or a["desc"]
                u["sets"].append((i, a["start"], a["end"], st))
    azkey = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    cards = "".join(
        f'<article class="az"><h3>{esc(n)}</h3><i class="genre">{esc(uniq[n]["tag"])}</i>'
        + (f'<p>{esc(uniq[n]["desc"])}</p>' if uniq[n]["desc"] else "")
        + "<ul>" + "".join(
            f'<li><a href="#day{d+1}">{t["days"][d]} {s}–{e}</a><em>{esc(st)}</em></li>'
            for d, s, e, st in sorted(uniq[n]["sets"])) + "</ul></article>"
        for n in sorted(uniq, key=azkey))

    fids = ["all", "music", "show", "work"]
    pills = "".join(
        f'\n   <input type="radio" name="tt-filter" id="f-{i}"{" checked" if i == "all" else ""}>'
        f'<label for="f-{i}">{lbl} <b>{totals[i]}</b></label>'
        for i, lbl in zip(fids, t["f"]))
    tabs = "".join(f'\n   <a href="#day{i+1}">{x}</a>' for i, x in enumerate(t["tabs"]))
    tabs += f'\n   <a href="#muziek">{t["az"]}</a>\n   <a href="#agenda">{t["agenda"]}</a>'
    howto = "".join(f'<div class="card"><h3>{h}</h3><p>{b}</p></div>' for h, b in t["ag_cards"])
    nav, footer = nav_of(t)
    p = t["pre"]
    theme = THEME_SCRIPT

    return f"""<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t['title']}</title>
<meta name="description" content="{t['metadesc']}">
<link rel="stylesheet" href="{p}style.css">
<link rel="alternate" hreflang="nl" href="https://elfia.nl/lineup.html">
<link rel="alternate" hreflang="en" href="https://elfia.nl/en/lineup.html">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ctext y='26' font-size='26'%3E%F0%9F%8F%B0%3C/text%3E%3C/svg%3E">
{theme}
</head>
<body>
<a href="#main" class="sr">{t['skip']}</a>
{nav}
<main id="main">
<header class="page-head"><div class="wrap"><h1>{t['h1']}</h1><p>{t['head']}</p>{SRCNOTE[t['lang']]}</div></header><section style="padding-bottom:0;border:0"><div class="wrap">
  <div class="daytabs">{tabs}
  </div>
  <div class="filters" role="group" aria-label="{t['flabel']}">{pills}
  </div>
  <p class="icsline">{t['ics_lead'].format(totals['music'])} <a class="btn" href="{p}elfia-2026-muziek.ics" type="text/calendar" download>↓ {t['ics_music']}</a> <a class="btn ghost" href="{p}elfia-2026-programma.ics" type="text/calendar" download>↓ {t['ics_all']}</a></p>
  <p class="note warn">{t['warn']}</p>
</div></section>{''.join(parts)}<section id="muziek"><div class="wrap">
  <h2>{t['az']}</h2>
  <p class="lede">{t['az_lede']}</p>
  <div class="azgrid">{cards}</div>
</div></section><section id="agenda"><div class="wrap">
  <h2>{t['ag_h']}</h2>
  <p class="lede">{t['ag_lede']}</p>
  <p class="btnrow"><a class="btn" href="{p}elfia-2026-muziek.ics" type="text/calendar" download>↓ {t['dl_music'].format(totals['music'])}</a><a class="btn ghost" href="{p}elfia-2026-programma.ics" type="text/calendar" download>↓ {t['dl_all'].format(totals['all'])}</a></p>
  <div class="grid grid-2">{howto}</div>
  <p class="note" style="margin-top:1.15rem">{t['ag_note']}</p>
</div></section>
</main>
{footer}
</body>
</html>
"""


def main():
    days = read_days(PROG)
    missing = sorted({a["name"] for d in days.values() for st in d.values() for a in st
                      if not a["tag"]})
    for lang, t in T.items():
        (ROOT / t["file"]).write_text(build(t, days), encoding="utf-8")
        n = sum(len(v) for d in days.values() for v in d.values())
        print(f"{t['file']}: {n} slots, "
              f"{len({s for d in days.values() for s in d})} stages")
    if missing:
        print(f"\nzonder label ({len(missing)}) — vul labels.json aan:")
        for m in missing:
            print("   ", m)


if __name__ == "__main__":
    main()
