#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill the data regions of the Eten & drinken pages from the programme API.

    python3 build/make-food.py [site-root] [build/programme.json]

Caterers live in the programme payload at
    resultProgramme[Arcen Castle Gardens].highlightImage[].shops[]
next to each realm's exhibitors[] (see make-vendors.py).

Prose lives in build/templates/food.{nl,en}.html; this script only replaces
<!--FILTER-->, <!--COUNTS--> and <!--CATERERS-->. Edit the templates for copy changes.
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PROG = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "build" / "programme.json")
EVENT = "Arcen Castle Gardens"
LABELS = [("Vegan", "vegan"), ("Vegetarian", "veg"), ("Halal", "halal"), ("Gluten Free", "gf")]

ALIASES = {k: v for k, v in json.loads(
    (Path(__file__).parent / "realm-aliases.json").read_text(encoding="utf-8")).items()
    if not k.startswith("_")}


def canon(realm):
    """Fold superseded realm names onto the name printed on the official map."""
    return ALIASES.get(re.sub(r"[^a-z0-9]", "", realm.lower()), realm)


clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()

COPY = {
 "nl": dict(diet=dict(vegan="Vegan", veg="Vegetarisch", halal="Halal", gf="Glutenvrij",
                      none="Geen dieetlabels"),
            f=["Alles", "Vegan", "Vegetarisch", "Halal", "Glutenvrij"],
            count=["{} eetkramen in {} rijken", "{} met veganistische opties",
                   "{} met vegetarische opties", "{} met halal opties",
                   "{} met glutenvrije opties"]),
 "en": dict(diet=dict(vegan="Vegan", veg="Vegetarian", halal="Halal", gf="Gluten free",
                      none="No dietary labels"),
            f=["All", "Vegan", "Vegetarian", "Halal", "Gluten free"],
            count=["{} food stalls in {} realms", "{} with vegan options",
                   "{} with vegetarian options", "{} with halal options",
                   "{} with gluten-free options"]),
}


def read_shops():
    doc = json.loads(PROG.read_text(encoding="utf-8"))
    ev = [p for p in doc["resultProgramme"] if p["title"] == EVENT][0]
    out = []
    for r in ev["highlightImage"]:
        for s in sorted(r.get("shops") or [], key=lambda x: x.get("sequence") or 0):
            out.append(dict(name=clean(s["name"]), realm=canon(clean(r["title"])),
                            desc=clean(s.get("description")),
                            labels=[l["label"] for l in sorted(s.get("labels") or [],
                                                               key=lambda x: x["sequence"])]))
    return out


def main():
    shops = read_shops()
    realms = list(dict.fromkeys(s["realm"] for s in shops))
    ids = ["all"] + [k for _, k in LABELS]
    counts = [len(shops)] + [sum(1 for s in shops if lab in s["labels"]) for lab, _ in LABELS]

    for lang, tpl in (("nl", "food.nl.html"), ("en", "food.en.html")):
        c = COPY[lang]
        pills = "".join(
            f'   <input type="radio" name="diet" id="d-{i}"{" checked" if i == "all" else ""}>'
            f'<label for="d-{i}">{lbl} <b>{n}</b></label>\n'
            for i, lbl, n in zip(ids, c["f"], counts)).rstrip("\n")
        spans = "".join(
            f'<span class="c c-d-{i}">'
            f'{w.format(n, len(realms)) if i == "all" else w.format(n)}</span>'
            for i, w, n in zip(ids, c["count"], counts))

        blocks = []
        for realm in realms:
            cards = []
            for s in (x for x in shops if x["realm"] == realm):
                keys = [k for lab, k in LABELS if lab in s["labels"]]
                pill = ("".join(f'<i class="diet {k}">{c["diet"][k]}</i>' for k in keys)
                        or f'<i class="diet none">{c["diet"]["none"]}</i>')
                cls = " ".join(["cat"] + [f"l-{k}" for k in keys])
                cards.append(f'<article class="{cls}"><h3>{html.escape(s["name"])}</h3>'
                             f'<p class="diets">{pill}</p>'
                             f'<p>{html.escape(s["desc"])}</p></article>')
            blocks.append(f'<div class="realmblock"><h3>{html.escape(realm)}</h3>'
                          f'<div class="catgrid">{"".join(cards)}</div></div>')

        page = (ROOT / "build" / "templates" / tpl).read_text(encoding="utf-8")
        page = (page.replace("<!--FILTER-->", pills)
                    .replace("<!--COUNTS-->", spans)
                    .replace("<!--CATERERS-->", "".join(blocks)))
        out = ROOT / ("food.html" if lang == "nl" else "en/food.html")
        out.write_text(page, encoding="utf-8")
        print(f"{out}: {len(shops)} caterers, {len(realms)} realms")


if __name__ == "__main__":
    main()
