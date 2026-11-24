# scraper.py — iSprout Radar: scant ALLE kantoren uit de masterlijst-CSV
# Bron: Kantorenlijst_audit_NL(Kantorenlijst).csv (Big 4 + AV-Top 50 + overige)
# Signaalbronnen: Google News per kantoor (incl. Accountancy Vanmorgen),
#                 accountant.nl (globale feed), AFM (globale feed), vacature-scan.
# Output: leads.json — leest de app automatisch in.
# Notities en contactgegevens uit de CSV worden NIET meegenomen (publieke repo).
import feedparser, json, sys, csv, io, time, datetime

# ---------- 1. CSV INLEZEN ----------
BRON = "Kantorenlijst_audit_NL(Kantorenlijst).csv"

try:
    ruw = open(BRON, "rb").read()
except FileNotFoundError:
    sys.exit(f"Bronbestand '{BRON}' niet gevonden — upload de CSV eerst naar de repo.")

tekst = None
for enc in ("utf-8-sig", "cp1252", "latin-1"):
    try:
        tekst = ruw.decode(enc)
        break
    except UnicodeDecodeError:
        continue
if tekst is None:
    sys.exit("Onleesbare codering in de CSV.")

def kolom(rij, i):
    return rij[i].strip() if i < len(rij) else ""

def naar_getal(s):
    """'1,394.0' -> 1394.0 ; '7,780' -> 7780 ; '' -> None"""
    s = (s or "").replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

# Plaats -> coördinaat (benaderend, city-level pins)
COORD = {
    "rotterdam": (51.92, 4.48), "amsterdam": (52.37, 4.90), "eindhoven": (51.44, 5.47),
    "amstelveen": (52.30, 4.86), "arnhem": (51.98, 5.90), "nijkerk": (52.22, 5.49),
    "hoofddorp": (52.30, 4.69), "zwolle": (52.51, 6.09), "alphen aan den rijn": (52.13, 4.66),
    "breda": (51.59, 4.78), "dordrecht": (51.81, 4.67), "hoorn": (52.64, 5.06),
    "amersfoort": (52.16, 5.39), "goes": (51.50, 3.89), "drachten": (53.11, 6.10),
    "tilburg": (51.56, 5.09), "ede": (52.04, 5.66), "boxmeer": (51.65, 5.95),
    "barneveld": (52.14, 5.59), "woudenberg": (52.09, 5.42), "heerhugowaard": (52.66, 4.84),
    "den helder": (52.96, 4.76), "doetinchem": (51.97, 6.29), "alkmaar": (52.63, 4.75),
    "hilversum": (52.23, 5.17), "purmerend": (52.50, 4.99), "lichtenvoorde": (51.98, 6.55),
    "sliedrecht": (51.82, 4.76), "s-hertogenbosch": (51.69, 5.30), "huizen": (52.30, 5.24),
    "gorredijk": (53.01, 6.07), "helmond": (51.48, 5.66), "nieuwegein": (52.03, 5.08),
    "noordwijk": (52.27, 4.44), "maastricht": (50.85, 5.69), "woerden": (52.08, 4.88),
    "genemuiden": (52.51, 6.04), "wijhe": (52.39, 6.13), "dirksland": (51.75, 4.10),
    "tynaarlo": (53.10, 6.60), "groningen": (53.22, 6.57), "zoetermeer": (52.06, 4.63),
    "almere": (52.37, 5.22), "delft": (52.01, 4.36), "zeddam": (51.98, 6.30),
    "halsteren": (51.53, 4.32), "uden": (51.66, 5.62), "voorburg": (52.08, 4.61),
    "hendrik-ido-ambacht": (51.84, 4.65), "zaandam": (52.44, 4.83), "haarlem": (52.38, 4.64),
    "leiden": (52.16, 4.49), "velsen-zuid": (52.45, 4.67), "nijmegen": (51.84, 5.86),
    "veldhoven": (51.42, 5.40), "bilthoven": (52.14, 5.20), "geleen": (50.96, 5.83),
    "apeldoorn": (52.21, 5.97), "veenendaal": (52.03, 5.55), "capelle aan den ijssel": (51.93, 4.58),
    "rijswijk": (52.05, 4.32), "voorschoten": (52.12, 4.45), "de meern": (52.07, 5.03),
    "dokkum": (53.33, 6.00), "rijnsburg": (52.22, 4.44), "zwaag": (52.68, 4.97),
    "s-gravenhage": (52.08, 4.31), "'s-gravenhage": (52.08, 4.31), "emmen": (52.79, 6.90),
    "naaldwijk": (51.99, 4.21), "harderwijk": (52.34, 5.62), "dalfsen": (52.51, 6.25),
    "diemen": (52.35, 4.96), "hoogeveen": (52.72, 6.48), "veghel": (51.62, 5.54),
    "volendam": (52.50, 5.07), "willemstad": (51.69, 4.40), "roermond": (51.19, 6.00),
    "roosendaal": (51.53, 4.47), "schagen": (52.79, 4.80), "middelburg": (51.50, 3.61),
    "urk": (52.66, 5.60), "reuver": (51.26, 6.08), "lisse": (52.26, 4.56),
    "obdam": (52.67, 4.94), "meppel": (52.70, 6.19), "bunnik": (52.06, 5.19),
    "barendrecht": (51.86, 4.53), "oud-beijerland": (51.82, 4.43), "assendelft": (52.46, 4.76),
    "schoonhoven": (51.95, 4.85), "sittard": (51.06, 5.87), "warmond": (52.20, 4.51),
    "deventer": (52.25, 6.16), "katwijk": (52.20, 4.40), "spijkenisse": (51.85, 4.33),
    "leeuwarden": (53.20, 5.79), "weert": (51.25, 5.71), "enschede": (52.22, 6.89),
    "twello": (52.18, 6.11), "krimpen aan den ijssel": (51.91, 4.59),
    "middelharnis": (51.76, 4.16), "simonshaven": (51.85, 4.37), "heerenveen": (52.96, 5.92),
    "heerlen": (50.89, 5.98), "rosmalen": (51.59, 5.53), "everdingen": (51.98, 5.05),
    "aalsmeer": (52.27, 4.76), "etten-leur": (51.57, 4.44), "waalwijk": (51.69, 5.06),
    "vlaardingen": (51.91, 4.34), "ridderkerk": (51.87, 4.61), "zaltbommel": (51.81, 5.25),
    "lopik": (51.99, 4.98), "druten": (51.89, 5.60), "herten": (51.05, 5.89),
    "pijnacker": (52.01, 4.53), "utrecht": (52.09, 5.12),
}

def coordinaat(plaats):
    key = (plaats or "").lower().strip()
    return COORD.get(key, (52.20, 5.30))

rijen = list(csv.reader(io.StringIO(tekst)))
kantoren = {}
for rij in rijen[1:]:                      # kopregel overslaan
    org      = kolom(rij, 3)               # "Naam organisatie"
    plaats   = kolom(rij, 4)               # "Plaats (hoofdvestiging)"
    klasse   = kolom(rij, 5)               # Big 4 / AV-Top 50 / ...
    fte      = naar_getal(kolom(rij, 8))
    omzet    = naar_getal(kolom(rij, 9))
    netwerk  = kolom(rij, 15)              # "Internationaal netwerk"
    eigenaar = kolom(rij, 0)               # initialen Tom/Mo/... (GEEN notities!)
    if not org or len(org) < 3:
        continue
    key = org.lower()
    if key in kantoren:
        continue
    lat, lng = coordinaat(plaats)
    kantoren[key] = {
        "name": org,
        "city": plaats.title(),
        "lat": lat, "lng": lng,
        "klasse": klasse or "Onbekend",
        "fte": fte, "omzet": omzet,
        "internationaal": "Onbekend" not in netwerk and bool(netwerk),
        "eigenaar": eigenaar if eigenaar.lower() != "x" else "",
    }

print(f"{len(rijen)-1} rijen ingelezen -> {len(kantoren)} unieke kantoren")

# ---------- 2. SIGNAALWOORDEN ----------
WOORDEN_A = {"outsourc": 5, "uitbested": 5, "backoffice": 4, "werkvoorraad": 4,
             "werkdruk": 3, "capaciteit": 4, "capacity": 4, "remote": 3, "op afstand": 3}
WOORDEN_B = {"vacature": 2, "werving": 3, "relocatie": 4, "expat": 4,
             "instroom": 2, "rekruteert": 3, "internationaal talent": 4}
WOORDEN_G = {"overname": 3, "fusie": 3, "groei": 2, "groeit": 2, "expandert": 2}
DATUM_FILTER = "after:2026-05-23"

def gewicht(t, wb):
    t = t.lower()
    return sum(w for kw, w in wb.items() if kw in t)

# ---------- 3. GLOBALE FEEDS ----------
def laad_feed(url, bron):
    out = []
    try:
        for e in feedparser.parse(url).entries[:80]:
            out.append({"titel": e.title, "link": e.link,
                        "datum": getattr(e, "published", ""), "bron": bron})
    except Exception as ex:
        print(f"  (feed {bron} niet beschikbaar: {ex})")
    return out

GLOBAL_FEEDS = (
    laad_feed("https://www.accountant.nl/rss/nieuws/", "accountant.nl")
    + laad_feed("https://www.afm.nl/nl/nieuwsberichten/rss", "AFM")
)
print(f"Globale feeds opgehaald: {len(GLOBAL_FEEDS)} artikelen")

def match_globale_feeds(naam):
    token = naam.lower().split()[0]
    if len(token) < 5:
        return []
    hits = []
    for e in GLOBAL_FEEDS:
        if token in e["titel"].lower():
            gA = gewicht(e["titel"], WOORDEN_A)
            gB = gewicht(e["titel"], WOORDEN_B)
            gG = gewicht(e["titel"], WOORDEN_G)
            if gA + gB + gG > 0:
                hits.append({**e, "a": gA, "b": gB, "groei": gG})
    return hits

# ---------- 4. SCANS PER KANTOOR ----------
def scan_nieuws(naam):
    q = f'"{naam}" (overname OR groei OR vacature OR outsourcing OR uitbesteden OR werving) {DATUM_FILTER}'
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    sigs = []
    try:
        for e in feedparser.parse(url).entries[:10]:
            gA = gewicht(e.title, WOORDEN_A)
            gB = gewicht(e.title, WOORDEN_B)
            gG = gewicht(e.title, WOORDEN_G)
            if gA + gB + gG > 0:
                sigs.append({"titel": e.title, "link": e.link,
                             "datum": getattr(e, "published", ""),
                             "bron": "Google News", "a": gA, "b": gB, "groei": gG})
    except Exception:
        pass
    return sigs

def scan_vacatures(naam):
    q = f'"{naam}" (vacature OR "wij zoeken" OR gezocht OR aanname) {DATUM_FILTER}'
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    sigs = []
    try:
        for e in feedparser.parse(url).entries[:10]:
            t = e.title.lower()
            if "vacature" in t or "zoeken" in t or "gevraagd" in t:
                sigs.append({"titel": e.title, "link": e.link,
                             "datum": getattr(e, "published", ""),
                             "bron": "Google News (vacatures)", "a": 1, "b": 3, "groei": 0})
    except Exception:
        pass
    return sigs

# ---------- 5. HOOFDLOOP ----------
leads = []
totaal = len(kantoren)
for i, k in enumerate(kantoren.values()):
    sigs = scan_nieuws(k["name"]) + scan_vacatures(k["name"]) + match_globale_feeds(k["name"])
    n_vac = sum(1 for s in sigs if "vacature" in s["bron"].lower())
    sA = min(100, 30 + sum(s["a"] for s in sigs) * 8 + sum(s["groei"] for s in sigs) * 4 + min(15, n_vac * 5))
    sB = min(100, 30 + sum(s["b"] for s in sigs) * 8 + min(20, n_vac * 5) + (8 if k["internationaal"] else 0))
    leads.append({**k, "score_out": sA, "score_nl": sB,
                  "vacatures": n_vac, "signalen": sigs})
    if i % 25 == 0:
        print(f"...{i}/{totaal} gescand", flush=True)
    time.sleep(0.35)   # rustig aan naar Google toe

# ---------- 6. WEGSCHRIJVEN ----------
json.dump({
    "gegenereerd": str(datetime.datetime.now()),
    "bron": "Masterlijst-CSV (Big 4 + AV-Top 50) + Google News (+vacatures) + accountant.nl + AFM",
    "let_op": "Scores zijn keyword-based, geen AI. Signalen bevatten echte titels, datums en links.",
    "leads": leads,
}, open("leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nKlaar — {len(leads)} kantoren in leads.json.")
