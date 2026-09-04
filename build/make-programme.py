#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the "Wat je te wachten staat" pages from the programme API.

    python3 build/make-programme.py [site-root] [build/programme.json]

The API's realm list cannot be used as-is. It carries 20 entries, but:
  * two are superseded names kept alongside their replacements (Giostra Fortunia,
    Academy Hall) — folded via realm-aliases.json;
  * three areas printed on the official 2026 map are missing from it entirely
    (Border to Fantasy, Bandits Creek, Elfia Academy — the last exists only as a
    workshop entry);
  * several have a description but no stage, no traders and no place on the map.

So the map is used as the spine (MAP_AREAS below, transcribed from arcen-map.webp),
API descriptions are matched onto it, and everything left over is shown separately
and labelled for what it is. Update MAP_AREAS when the map changes.
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PROG = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "build" / "programme.json")
ALIASES = {k: v for k, v in json.loads(
    (ROOT / "build" / "realm-aliases.json").read_text(encoding="utf-8")).items()
    if not k.startswith("_")}
EVENT = "Arcen Castle Gardens"

# the 13 numbered areas on the official 2026 map, in map order
MAP_AREAS = ["Border to Fantasy", "Elfia Academy", "Iron Fjord", "Odin's Vale",
             "La Piazza Dei Sogni", "Bard's Theater", "Black Skull Bay", "Music Court",
             "The Garden of Eve", "The Steamworks", "Folk Faire", "The Zen Garden",
             "Bandits Creek"]

clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()
norm = lambda s: re.sub(r"[^a-z0-9]", "", clean(s).lower())
canon = lambda s: ALIASES.get(norm(s), clean(s))
esc = lambda s: html.escape(s, quote=False)

COPY = {
 "nl": dict(file="programme.html",
   areas_h="De gebieden", areas_lede='De {} genummerde themagebieden van de officiële '
     '<a href="map.html">plattegrond</a>, in de volgorde waarin ze genummerd staan.',
   nodesc="Staat op de plattegrond; de organisatie heeft er nog geen omschrijving bij gegeven.",
   bandits="Hier loopt de hele dag een akoestische act rond en wordt er line dancing gegeven — "
           "zie het <a href=\"lineup.html\">programma</a>.",
   market_h="Marktgebieden", market_lede='Deze gebieden staan niet als genummerd vak op de '
     'plattegrond, maar hebben wel eigen kramen. Alle kramen staan op '
     '<a href="vendors.html">Vendors</a>.',
   stalls="kramen", also_h="Ook aangekondigd",
   also_lede="De organisatie beschrijft deze gebieden wel, maar ze staan niet op de plattegrond "
             "en er hangen geen kramen, podia of tijden aan. Mogelijk vervallen of nog geheim.",
   hi_h="Hoogtepunten", hi_lede="Acts, gasten en tradities op Elfia Arcen.",
   ws_h="Elfia Academy", ws_lede="Workshops, talks en watch parties."),
 "en": dict(file="en/programme.html",
   areas_h="The areas", areas_lede='The {} numbered themed areas on the official '
     '<a href="map.html">map</a>, in the order they are numbered.',
   nodesc="On the map; the organisers have not given it a description yet.",
   bandits="A roaming acoustic act plays here all day and there is line dancing — see the "
           "<a href=\"lineup.html\">line-up</a>.",
   market_h="Market areas", market_lede='These are not numbered areas on the map, but they do '
     'have their own stalls. Every stall is listed on <a href="vendors.html">Vendors</a>.',
   stalls="stalls", also_h="Also announced",
   also_lede="The organisers describe these areas, but they are not on the map and have no "
             "stalls, stage or times attached. Possibly dropped, possibly still under wraps.",
   hi_h="Highlights", hi_lede="Acts, guests and traditions featured at Elfia Arcen.",
   ws_h="Elfia Academy", ws_lede="Workshops, talks and watch parties."),
}


def load():
    doc = json.loads(PROG.read_text(encoding="utf-8"))
    ev = [p for p in doc["resultProgramme"] if p["title"] == EVENT][0]
    realms, highlights, workshops = {}, [], []
    for x in ev["highlightImage"]:
        t, desc = canon(x.get("title")), clean(x.get("description"))
        ct = x.get("categoryType")
        if ct == "realms":
            r = realms.setdefault(t, dict(name=t, desc="", shops=0, exh=0))
            r["desc"] = r["desc"] or desc
            r["shops"] += len(x.get("shops") or [])
            r["exh"] += len(x.get("exhibitors") or [])
        elif ct == "highlight":
            highlights.append((clean(x.get("title")), desc))
        elif ct == "workshop":
            workshops.append((clean(x.get("title")), desc))
    return realms, highlights, workshops


def cards(items):
    return "".join(f'<div class="card"><h3>{esc(t)}</h3><p>{esc(d)}</p></div>' for t, d in items)


def main():
    realms, highlights, workshops = load()
    used = set()
    for lang, c in COPY.items():
        area_cards = []
        for name in MAP_AREAS:
            r = realms.get(name) or next((v for k, v in realms.items() if norm(k) == norm(name)), None)
            if r:
                used.add(r["name"])
                body = esc(r["desc"])
            elif norm(name) == norm("Bandits Creek"):
                body = c["bandits"]
            else:
                body = c["nodesc"]
            area_cards.append(f'<div class="card"><h3>{esc(name)}</h3><p>{body}</p></div>')

        rest = [v for k, v in realms.items() if v["name"] not in used]
        market = [v for v in rest if v["shops"] or v["exh"]]
        other = [v for v in rest if not (v["shops"] or v["exh"])]
        market_cards = "".join(
            f'<div class="card"><h3>{esc(v["name"])} '
            f'<small style="color:var(--dim);font-weight:400">· {v["exh"] + v["shops"]} '
            f'{c["stalls"]}</small></h3><p>{esc(v["desc"])}</p></div>' for v in market)

        page = (ROOT / "build" / "templates" /
                f'programme.{lang}.html').read_text(encoding="utf-8")
        page = (page.replace("<!--AREAS-->", "".join(area_cards))
                    .replace("<!--NAREAS-->", str(len(MAP_AREAS)))
                    .replace("<!--MARKET-->", market_cards)
                    .replace("<!--OTHER-->", cards((v["name"], v["desc"]) for v in other))
                    .replace("<!--HIGHLIGHTS-->", cards(highlights))
                    .replace("<!--NHI-->", str(len(highlights)))
                    .replace("<!--WORKSHOPS-->", cards(workshops)))
        out = ROOT / c["file"]
        out.write_text(page, encoding="utf-8")

        # the home page teases the first six areas from the same source
        teaser = "".join(area_cards[:6])
        home = (ROOT / "build" / "templates" /
                f"index.{lang}.html").read_text(encoding="utf-8")
        home = (home.replace("<!--REALMS6-->", teaser)
                    .replace("<!--NAREAS-->", str(len(MAP_AREAS))))
        (ROOT / ("index.html" if lang == "nl" else "en/index.html")).write_text(
            home, encoding="utf-8")
        print(f'{out}: {len(MAP_AREAS)} areas, {len(market)} market, {len(other)} other, '
              f'{len(highlights)} highlights, {len(workshops)} workshops')


if __name__ == "__main__":
    main()
