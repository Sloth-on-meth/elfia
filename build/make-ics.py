#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the Elfia Arcen calendar files from the programme API.

    python3 build/make-ics.py [site-root] [build/programme.json] [build/lineup-labels.json]

Writes elfia-2026-muziek.ics (music only) and elfia-2026-programma.ics (everything),
both iCalendar 2.0 with an embedded Europe/Amsterdam VTIMEZONE so imports are correct
from any time zone. UIDs are date+stage+start+name, so re-importing an updated file
replaces events rather than duplicating them. No alarms are set.

EXCLUDED_STAGES are left out of both files on purpose: Bandits Creek is a roaming
all-day act plus quarter-hour line-dancing slots, and Elfia Treasures is a signing
session — calendar clutter rather than things you plan a day around.
"""
import html, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PROG = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "build" / "programme.json")
LABELS = json.loads(Path(sys.argv[3] if len(sys.argv) > 3 else ROOT / "build" / "lineup-labels.json")
                    .read_text(encoding="utf-8"))

EVENT = "Arcen Castle Gardens"
EXCLUDED_STAGES = {"Bandits Creek", "Elfia Treasures"}
DATES = {"Saturday": "20260919", "Sunday": "20260920"}
DAYNAME = {"Saturday": "Saturday 19 September", "Sunday": "Sunday 20 September"}
VENUE = "Kasteeltuinen Arcen, Lingsforterweg 26, 5944 BE Arcen"
DTSTAMP = "20260904T000000Z"

clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()
fold_txt = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def key(s):
    return re.sub(r"[^a-z0-9]", "", fold_txt(clean(s)).lower())


def split_activity(s):
    s = clean(s)
    m = re.match(r"^(.*?)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)$", s)
    if m and len(m.group(2)) > 28:
        return m.group(1).strip(), m.group(2).strip()
    return s, ""


def esc(s):
    return (s.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    if len(line.encode()) <= 73:
        return line
    out, cur = [], b""
    for ch in line:
        e = ch.encode()
        if len(cur) + len(e) > 73:
            out.append(cur.decode()); cur = b""
        cur += e
    out.append(cur.decode())
    return "\r\n ".join(out)


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", fold_txt(s).lower())).strip("-")


VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Amsterdam
X-LIC-LOCATION:Europe/Amsterdam
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE""".split("\n")


def read_slots():
    doc = json.loads(PROG.read_text(encoding="utf-8"))
    ev = [p for p in doc["resultProgramme"] if p["title"] == EVENT][0]
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "slots" in o and "name" in o and "dayDate" in o:
                stage = clean(o["name"])
                if (not stage.startswith("This is just") and stage not in EXCLUDED_STAGES
                        and o["dayDate"] in DATES):
                    for s in o["slots"]:
                        name, desc = split_activity(s["activity"])
                        lab = LABELS.get(key(name), {})
                        out.append(dict(day=o["dayDate"], stage=stage, name=name, desc=desc,
                                        start=s["activityFromStr"][:5], end=s["activityToStr"][:5],
                                        cls=lab.get("cls", ""), tag=lab.get("tag", "")))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(ev)
    out.sort(key=lambda a: (DATES[a["day"]], a["start"], a["stage"]))
    return out


def build(slots, calname, keep):
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Elfia Arcen//Line-up 2026//EN",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:" + esc(calname),
         "X-WR-TIMEZONE:Europe/Amsterdam",
         "X-WR-CALDESC:" + esc("Elfia Arcen 2026 \u2014 Kasteeltuinen Arcen, 19 & 20 September "
                               "2026. Times can still change; check the boards at the stages on "
                               "the day. Roaming acts (Bandits Creek) and signing sessions "
                               "(Elfia Treasures) are not included.")] + VTIMEZONE
    n = 0
    for a in slots:
        if not keep(a):
            continue
        n += 1
        d = DATES[a["day"]]
        summary = f'{a["name"]} \u2014 {a["tag"]}' if a["tag"] else a["name"]
        body = ([a["desc"]] if a["desc"] else []) + [
            f'Stage: {a["stage"]}', f'{DAYNAME[a["day"]]}, {a["start"]}\u2013{a["end"]}',
            "Elfia Arcen 2026 \u2014 times can change; check the boards at the stages."]
        cat = ("Music" if "genre" in a["cls"] else
               ("Show" if "perf" in a["cls"] else "Workshop"))
        L += ["BEGIN:VEVENT",
              f'UID:{d}-{slug(a["stage"])}-{a["start"].replace(":","")}'
              f'-{slug(a["name"])[:40]}@elfia.nl',
              f"DTSTAMP:{DTSTAMP}",
              f'DTSTART;TZID=Europe/Amsterdam:{d}T{a["start"].replace(":","")}00',
              f'DTEND;TZID=Europe/Amsterdam:{d}T{a["end"].replace(":","")}00',
              "SUMMARY:" + esc(summary),
              "LOCATION:" + esc(f'{a["stage"]} \u00b7 {VENUE}'),
              "DESCRIPTION:" + esc("\n".join(body)),
              "CATEGORIES:" + esc(cat), "TRANSP:OPAQUE", "STATUS:CONFIRMED", "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(fold(x) for x in L) + "\r\n", n


def main():
    slots = read_slots()
    for fn, calname, keep in (
            ("elfia-2026-muziek.ics", "Elfia Arcen 2026 \u2014 Muziek / Music",
             lambda a: "genre" in a["cls"]),
            ("elfia-2026-programma.ics",
             "Elfia Arcen 2026 \u2014 Volledig programma / Full line-up", lambda a: True)):
        text, n = build(slots, calname, keep)
        (ROOT / fn).write_text(text, encoding="utf-8", newline="")
        print(f"{fn}: {n} events")


if __name__ == "__main__":
    main()
