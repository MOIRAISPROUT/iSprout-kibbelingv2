# evenementen.py — scant nieuws naar accountancy-evenementen, schrijft events.json
import feedparser, json, datetime

QUERIES = [
    '"accountantsdag" OR "accountancydag" (congres OR event OR editie OR aanmelden)',
    '"payroll day" OR "payroll awards" accountancy',
    'accountancy congres 2027 OR accountants event 2027',
    'netwerkdag accountantskantoren',
    '"Audit Event" accountancy',
    'accountancy vanmorgen (event OR congres OR padel OR bijeenkomst)',
]
TREFWOORD = ["congres", "event", "dag ", "editie", "aanmelden", "tickets",
             "conferentie", "netwerk", "bijeenkomst", "padel"]

evenementen, gezien = [], set()
for q in QUERIES:
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    try:
        for e in feedparser.parse(url).entries[:15]:
            t = e.title.strip()
            tl = t.lower()
            if tl in gezien or not any(w in tl for w in TREFWOORD):
                continue
            gezien.add(tl)
            evenementen.append({"naam": t, "link": e.link,
                                "datum": getattr(e, "published", ""),
                                "bron": "Google News", "gevonden": str(datetime.date.today())})
    except Exception:
        pass

json.dump({"gegenereerd": str(datetime.datetime.now()), "events": evenementen},
          open("events.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"Klaar — {len(evenementen)} event-signalen gevonden.")
