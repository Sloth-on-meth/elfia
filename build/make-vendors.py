#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill the data regions of the Markt / Market pages from the programme API.

    python3 build/make-vendors.py [site-root] [build/programme.json]

Traders live at resultProgramme[Arcen Castle Gardens].highlightImage[].exhibitors[],
next to each realm's shops[] (the caterers, see make-food.py).

Prose lives in build/templates/vendors.{nl,en}.html; this script only replaces
<!--N-->, <!--R-->, <!--JUMPS-->, <!--BLOCKS--> and <!--AZ-->.
"""
import html, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PROG = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "build" / "programme.json")
EVENT = "Arcen Castle Gardens"
STALLS = {"nl": "kramen", "en": "stalls"}

ALIASES = {k: v for k, v in json.loads(
    (Path(__file__).parent / "realm-aliases.json").read_text(encoding="utf-8")).items()
    if not k.startswith("_")}


def canon(realm):
    """Fold superseded realm names onto the name printed on the official map."""
    return ALIASES.get(re.sub(r"[^a-z0-9]", "", realm.lower()), realm)


clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()
fold = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
anchor = lambda s: re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", fold(s).lower())).strip("-")


def read_exhibitors():
    doc = json.loads(PROG.read_text(encoding="utf-8"))
    ev = [p for p in doc["resultProgramme"] if p["title"] == EVENT][0]
    out = []
    for r in ev["highlightImage"]:
        for e in sorted(r.get("exhibitors") or [], key=lambda x: x.get("sequence") or 0):
            out.append(dict(name=clean(e["name"]), realm=canon(clean(r["title"])),
                            desc=clean(e.get("description")), link=(e.get("link") or "").strip()))
    return out


def main():
    ven = read_exhibitors()
    realms = list(dict.fromkeys(v["realm"] for v in ven))

    for lang, tpl in (("nl", "vendors.nl.html"), ("en", "vendors.en.html")):
        jumps = "".join(
            f'   <a href="#{anchor(r)}">{html.escape(r)} '
            f'<b>{sum(1 for v in ven if v["realm"] == r)}</b></a>\n' for r in realms).rstrip("\n")

        blocks = []
        for realm in realms:
            cards = []
            for v in (x for x in ven if x["realm"] == realm):
                name = html.escape(v["name"])
                if v["link"]:
                    name = (f'<a href="{html.escape(v["link"], quote=True)}" '
                            f'rel="noopener">{name}</a>')
                cards.append(f'<article class="ven"><h4>{name}</h4>'
                             f'<p>{html.escape(v["desc"])}</p></article>')
            blocks.append(
                f'<div class="realmblock" id="{anchor(realm)}"><h3>{html.escape(realm)} '
                f'<span>{len(cards)} {STALLS[lang]}</span></h3>'
                f'<div class="vengrid">{"".join(cards)}</div></div>')

        az = "".join(
            f'<li><a href="#{anchor(v["realm"])}">{html.escape(v["name"])}</a>'
            f'<em>{html.escape(v["realm"])}</em></li>'
            for v in sorted(ven, key=lambda x: fold(x["name"]).lower()))

        page = (ROOT / "build" / "templates" / tpl).read_text(encoding="utf-8")
        page = (page.replace("<!--N-->", str(len(ven)))
                    .replace("<!--R-->", str(len(realms)))
                    .replace("<!--JUMPS-->", jumps)
                    .replace("<!--BLOCKS-->", "".join(blocks))
                    .replace("<!--AZ-->", az))
        out = ROOT / ("vendors.html" if lang == "nl" else "en/vendors.html")
        out.write_text(page, encoding="utf-8")
        print(f"{out}: {len(ven)} stalls, {len(realms)} realms")


if __name__ == "__main__":
    main()
