# scraper.py — iSprout Radar v6 (COMPLEET)
# SIGNAAL-AGENT: zoekt per kantoor elke dag openbare sporen van offshoring-
# interesse (nieuws + woorden op eigen website) -> 🚨 meldingen bovenaan de app.
# VACATURE-PERSISTENTIE: telt hoeveel scans achtereen een kantoor doorlopend
#   vacatures open heeft (nieuws en/of eigen site). 7+ scans achtereen = 🧲
#   "staat al lang met open vacatures — open voor remote/offshore alternatief".
# Behouden uit v4: contact-suggesties (partner/HR met e-mail/telefoon),
#   carrièrepagina's, algemene e-mail/telefoon, deltas, anomalieen, netwerkveld.
import feedparser, json, sys, csv, io, time, datetime, re, urllib.request, urllib.parse
from html import unescape

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
    s = (s or "").replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

rijen_all = list(csv.reader(io.StringIO(tekst)))
HEADER = rijen_all[0] if rijen_all else []

def vind_kolom(woorden):
    for i, h in enumerate(HEADER):
        hl = (h or "").lower()
        if any(w in hl for w in woorden):
            return i
    return None

SITE_IDX = vind_kolom(["website", "url", "internet", "homepage"])
print("Website-kolom: " + (f"gevonden (kolom {SITE_IDX}: '{HEADER[SITE_IDX]}')"
                           if SITE_IDX is not None
                           else "NIET gevonden — website-scan wordt overgeslagen"))

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

kantoren = {}
for rij in rijen_all[1:]:
    org      = kolom(rij, 3)
    plaats   = kolom(rij, 4)
    klasse   = kolom(rij, 5)
    fte      = naar_getal(kolom(rij, 8))
    omzet    = naar_getal(kolom(rij, 9))
    netwerk  = kolom(rij, 15)
    eigenaar = kolom(rij, 0)
    website  = kolom(rij, SITE_IDX) if SITE_IDX is not None else ""
    if website and not website.lower().startswith("http"):
        website = "https://" + website
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
        "netwerk": netwerk if netwerk else "Onbekend",
        "internationaal": "Onbekend" not in netwerk and bool(netwerk),
        "eigenaar": eigenaar if eigenaar.lower() != "x" else "",
        "website": website,
    }

print(f"{len(rijen_all)-1} rijen ingelezen -> {len(kantoren)} unieke kantoren")

# ---------- 2. VORIGE SCAN (voor deltas en streaks) ----------
vorige_gen, VORIGE = "", {}
try:
    oud = json.load(open("leads.json", encoding="utf-8"))
    vorige_gen = oud.get("gegenereerd", "")
    for l in oud.get("leads", []):
        VORIGE[str(l.get("name") or "").lower()] = l
    print(f"Vorige scan gevonden ({vorige_gen}) — deltas en streaks worden berekend."
          if VORIGE else "Geen vorige scan — basis-meting.")
except Exception:
    print("Geen vorige scan — basis-meting.")

# ---------- 3. SIGNAALWOORDEN ----------
WOORDEN_A = {"outsourc": 5, "uitbested": 5, "backoffice": 4, "werkvoorraad": 4,
             "werkdruk": 3, "capaciteit": 4, "capacity": 4, "remote": 3, "op afstand": 3}
WOORDEN_B = {"vacature": 2, "werving": 3, "relocatie": 4, "expat": 4,
             "instroom": 2, "rekruteert": 3, "internationaal talent": 4}
WOORDEN_G = {"overname": 3, "fusie": 3, "groei": 2, "groeit": 2, "expandert": 2}
# AGENT: offshoring-interesse (zware gewichten)
WOORDEN_AGENT = {"offshor": 6, "nearshor": 6, "farshor": 5, "outsourc": 6, "uitbested": 6,
                 "zuid-afrika": 8, "south africa": 8, "kaapstad": 8, "remote": 4,
                 "remote working": 5, "remote team": 6, "op afstand werken": 5}
PERSIST_DREMP = 7   # scans achtereen met doorlopende vacatures -> 🧲 melding

DATUM_FILTER = "after:2026-05-23"

def gewicht(t, wb):
    t = t.lower()
    return sum(w for kw, w in wb.items() if kw in t)

# ---------- 4. GLOBALE FEEDS ----------
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
            gA, gB, gG = gewicht(e["titel"], WOORDEN_A), gewicht(e["titel"], WOORDEN_B), gewicht(e["titel"], WOORDEN_G)
            if gA + gB + gG > 0:
                hits.append({**e, "a": gA, "b": gB, "groei": gG})
    return hits

# ---------- 5. NIEUWSSCANS ----------
def google_nieuws(q):
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    try:
        return list(feedparser.parse(url).entries[:10])
    except Exception:
        return []

def scan_nieuws(naam):
    q = f'"{naam}" (overname OR groei OR vacature OR outsourcing OR uitbesteden OR werving) {DATUM_FILTER}'
    sigs = []
    for e in google_nieuws(q):
        gA, gB, gG = gewicht(e.title, WOORDEN_A), gewicht(e.title, WOORDEN_B), gewicht(e.title, WOORDEN_G)
        if gA + gB + gG > 0:
            sigs.append({"titel": e.title, "link": e.link,
                         "datum": getattr(e, "published", ""),
                         "bron": "Google News", "a": gA, "b": gB, "groei": gG})
    return sigs

def scan_vacatures(naam):
    q = f'"{naam}" (vacature OR "wij zoeken" OR gezocht OR aanname) {DATUM_FILTER}'
    sigs = []
    for e in google_nieuws(q):
        t = e.title.lower()
        if "vacature" in t or "zoeken" in t or "gevraagd" in t:
            sigs.append({"titel": e.title, "link": e.link,
                         "datum": getattr(e, "published", ""),
                         "bron": "Google News (vacatures)", "a": 1, "b": 3, "groei": 0})
    return sigs

def scan_agent(naam):
    """AGENT: openbare sporen van offshoring/remote/Zuid-Afrika-interesse."""
    q = (f'"{naam}" (offshoring OR nearshoring OR "Zuid-Afrika" OR "South Africa" '
         f'OR remote OR uitbesteden OR outsourcing) {DATUM_FILTER}')
    hits = []
    for e in google_nieuws(q):
        g = gewicht(e.title, WOORDEN_AGENT)
        if g > 0:
            hits.append({"titel": e.title, "link": e.link,
                         "datum": getattr(e, "published", ""), "gewicht": g})
    return hits

# ---------- 6. WEBSITE-SCAN ----------
CARW  = ("vacature", "werken", "carriere", "carrière", "jobs", "sollicit")
TEAMW = ("team", "partner", "directie", "over-ons", "over ons", "medewerkers",
         "people", "contact", "onze mensen", "organisatie", "management")

def haal_pagina(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
        ct = (r.headers.get("Content-Type") or "")
        enc = ct.split("charset=")[-1].strip("'\" ") if "charset=" in ct else "utf-8"
        try:
            return raw.decode(enc, "ignore")
        except Exception:
            return raw.decode("utf-8", "ignore")

def tekst_regels(html):
    html = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", "\n", html)
    regels = [re.sub(r"\s+", " ", l).strip() for l in unescape(html).split("\n")]
    return [l for l in regels if l]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,4}")
TEL_RE   = re.compile(r"(?:\+31|0031|0)[\s\-/(]?(?:\(0\))?[\s\-/]?(?:6[\s\-/]?\d{7}|\d{1,3}[\s\-/]?\d{6,8})(?!\d)")
ROL_PAT  = re.compile(r"\b(managing partner|managing director|mede[- ]directeur|regiodirecteur|"
                      r"hr[- ]?manager|hr[- ]?adviseur|personeels[a-z]*|recruiter|wervings[a-z]*|"
                      r"partner|directeur|vennoot|zakelijk leider|office manager)\b", re.I)

STOP = {"accountants", "accountancy", "accountant", "adviseurs", "advies", "en", "van",
        "de", "den", "der", "het", "the", "groep", "group", "nieuws", "contact", "home",
        "over", "ons", "meer", "lezen", "wij", "onze", "bv", "nv", "team"}

def tel_schoon(t):
    t = (t or "").strip()
    d = re.sub(r"\D", "", t)
    if 9 <= len(d) <= 12 and t.startswith(("0", "+31", "0031")):
        return t
    return ""

def email_schoon(e):
    return "" if re.search(r"\.(png|jpe?g|gif|webp|svg)$", e or "", re.I) else e

def naam_voor_rol(regel, pos):
    woorden = regel[:pos].rstrip(":·|—–- ").split()
    cur = []
    for w in reversed(woorden):
        if (w[:1].isupper() and len(w) > 1 and w.lower() not in STOP
                and not any(ch.isdigit() for ch in w)):
            cur.append(w)
            if len(cur) == 3:
                break
        else:
            break
    if len(cur) >= 2:
        return " ".join(reversed(cur))
    return ""

def contacten_uit_regels(regels):
    gevonden = {}
    for idx, regel in enumerate(regels):
        m = ROL_PAT.search(regel)
        if not m:
            continue
        naam = naam_voor_rol(regel, m.start())
        if not naam:
            continue
        rol = m.group(0).lower()
        nxt = regels[idx + 1] if idx + 1 < len(regels) else ""
        em, tm = "", ""
        for bron in (regel, nxt):
            mm = EMAIL_RE.search(bron)
            if mm:
                em = email_schoon(mm.group(0)); break
        for bron in (regel, nxt):
            mm = TEL_RE.search(bron)
            if mm:
                tm = tel_schoon(mm.group(0)); break
        item = gevonden.setdefault(naam.lower(), {"naam": naam, "rol": rol, "email": em, "tel": tm})
        if em and not item["email"]:
            item["email"] = em
        if tm and not item["tel"]:
            item["tel"] = tm
    return list(gevonden.values())

def scan_website(base):
    """Homepage -> agent-woorden, carrierepagina (vacatures), team-pagina's (contacten)."""
    if not base:
        return 0, "", [], "", "", 0
    try:
        home = haal_pagina(base)
    except Exception:
        return 0, "", [], "", "", 0
    regels_home = tekst_regels(home)
    n_home = len(re.findall(r"\bvacature", home, re.I))
    agent_site = sum(len(re.findall(re.escape(kw), home, re.I)) for kw in WOORDEN_AGENT)
    contacten = contacten_uit_regels(regels_home)

    carriere, teamlinks = "", []
    try:
        for href, txt in re.findall(r'<a[^>]+href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',
                                    home, re.I | re.S):
            hay = (href + " " + re.sub(r"<[^>]+>", " ", txt)).lower()
            vol = urllib.parse.urljoin(base, href.strip())
            if not vol.startswith("http"):
                continue
            if not carriere and any(w in hay for w in CARW):
                carriere = vol
            if (len(teamlinks) < 2 and any(w in hay for w in TEAMW)
                    and vol not in teamlinks
                    and vol.rstrip("/") != base.rstrip("/")):
                teamlinks.append(vol)
    except Exception:
        pass

    n_site = n_home
    if carriere:
        try:
            carr_html = haal_pagina(carriere)
            n_site = max(len(re.findall(r"\bvacature", carr_html, re.I)), n_home)
            agent_site += sum(len(re.findall(re.escape(kw), carr_html, re.I)) for kw in WOORDEN_AGENT)
        except Exception:
            pass
        time.sleep(0.2)
    for tl in teamlinks:
        try:
            contacten += contacten_uit_regels(tekst_regels(haal_pagina(tl)))
        except Exception:
            pass
        time.sleep(0.2)

    uniek, gezien = [], set()
    for c in contacten:
        key = (c["naam"].lower(), c["rol"][:12])
        if key in gezien:
            continue
        gezien.add(key)
        uniek.append(c)
    uniek = uniek[:8]

    em_al, tm_al = "", ""
    for e in EMAIL_RE.findall(home):
        e = email_schoon(e)
        if e and re.match(r"^(info|contact|welcome|office|hello)@", e, re.I):
            em_al = e
            break
        if e and not em_al:
            em_al = e
    mm = TEL_RE.search("\n".join(regels_home))
    tm_al = tel_schoon(mm.group(0)) if mm else ""

    return n_site, carriere, uniek, em_al, tm_al, agent_site

# ---------- 7. HOOFDLOOP ----------
leads, wijzigingen = [], []
tot_agent = 0

for i, k in enumerate(kantoren.values()):
    sigs = scan_nieuws(k["name"]) + scan_vacatures(k["name"]) + match_globale_feeds(k["name"])
    n_vac = sum(1 for s in sigs if "vacature" in s["bron"].lower())

    n_site, carr, sugg, em_al, tm_al, agent_site = scan_website(k["website"])
    agent_nieuw = scan_agent(k["name"])

    agent_bronnen = ([f"📰 {a['titel'][:90]}" for a in agent_nieuw]
                     + (["🌐 Website praat zelf over offshoring/remote/Zuid-Afrika"]
                        if agent_site >= 2 else []))
    n_agent = len(agent_bronnen)
    tot_agent += n_agent

    sA = min(100, 30 + sum(s["a"] for s in sigs) * 8 + sum(s["groei"] for s in sigs) * 4
             + min(15, n_vac * 5) + min(10, n_site * 2) + min(30, n_agent * 10))
    sB = min(100, 30 + sum(s["b"] for s in sigs) * 8 + min(20, n_vac * 5)
             + (8 if k["internationaal"] else 0) + min(8, n_site * 2))

    p = VORIGE.get(k["name"].lower())
    d_out = d_nl = d_vac = d_site = n_nieuw = 0
    anom = None
    streak_site = streak_vac = 0
    if p:
        p_vac  = int(p.get("vacatures") or 0)
        p_site = int(p.get("vacatures_site") or 0)
        d_out  = sA - int(p.get("score_out") or 0)
        d_nl   = sB - int(p.get("score_nl") or 0)
        d_vac  = n_vac - p_vac
        d_site = n_site - p_site
        streak_site = int(p.get("site_vac_streak") or 0)
        streak_vac  = int(p.get("vac_streak") or 0)
        oude_titels = {str(s.get("titel", "")).lower() for s in (p.get("signalen") or [])}
        n_nieuw = sum(1 for s in sigs if str(s.get("titel", "")).lower() not in oude_titels)
        if d_site >= 3 and n_site >= 3:
            anom = f"📈 site-vacatures opvallend toegenomen ({p_site} → {n_site})"
        elif p_site >= 2 and d_site <= -2:
            anom = f"📉 site-vacatures opvallend afgenomen ({p_site} → {n_site})"
        elif n_site >= 5:
            anom = f"🔥 structureel veel site-vacatures ({n_site})"
        elif d_vac >= 3 and n_vac >= 3:
            anom = f"📈 nieuws-vacatures opvallend toegenomen ({p_vac} → {n_vac})"
        elif p_vac >= 2 and d_vac <= -2:
            anom = f"📉 nieuws-vacatures opvallend afgenomen ({p_vac} → {n_vac})"
        elif n_vac >= 5:
            anom = f"🔥 structureel veel nieuws-vacatures ({n_vac})"
    else:
        if n_site >= 5:
            anom = f"🔥 structureel veel site-vacatures ({n_site})"
        elif n_vac >= 5:
            anom = f"🔥 structureel veel nieuws-vacatures ({n_vac})"

    # streaks bijwerken
    streak_site = streak_site + 1 if n_site >= 2 else 0
    streak_vac  = streak_vac + 1 if n_vac >= 2 else 0
    persist_tekst = ""
    langste = max(streak_site, streak_vac)
    if langste >= PERSIST_DREMP:
        soort = "op de eigen site" if streak_site >= streak_vac else "in het nieuws"
        persist_tekst = (f"🧲 {langste} scans achtereen doorlopende vacatures {soort} — "
                         f"kantoor zoekt al lang en isOPEN voor een remote/offshore alternatief")

    leads.append({**k, "score_out": sA, "score_nl": sB,
                  "delta_out": d_out, "delta_nl": d_nl,
                  "nieuwe_signalen": n_nieuw, "vac_delta": d_vac, "site_delta": d_site,
                  "anomalie": anom, "vacatures": n_vac,
                  "vacatures_site": n_site, "carriere_url": carr,
                  "site_vac_streak": streak_site, "vac_streak": streak_vac,
                  "agent_meldingen": agent_bronnen,
                  "suggesties": sugg,
                  "email_algemeen": em_al, "tel_algemeen": tm_al,
                  "signalen": sigs})

    redenen = []
    if agent_bronnen:
        redenen.append("🚨 OFFSHORING-SIGNAAL: " + " | ".join(agent_bronnen[:2]))
    if persist_tekst:
        redenen.append(persist_tekst)
    if n_nieuw:
        redenen.append(f"🆕 {n_nieuw} nieuw{'e' if n_nieuw != 1 else ''} signaal{'en' if n_nieuw != 1 else ''}")
    if d_out > 0:
        redenen.append(f"⬆ Optie A {sA - d_out}→{sA}")
    elif d_out < 0:
        redenen.append(f"⬇ Optie A {sA - d_out}→{sA}")
    if d_nl > 0:
        redenen.append(f"⬆ Optie B {sB - d_nl}→{sB}")
    elif d_nl < 0:
        redenen.append(f"⬇ Optie B {sB - d_nl}→{sB}")
    if abs(d_vac) >= 2:
        redenen.append(f"💼 nieuws-vacatures {'+' if d_vac > 0 else ''}{d_vac}")
    if abs(d_site) >= 2:
        redenen.append(f"🌐 site-vacatures {'+' if d_site > 0 else ''}{d_site}")
    if anom:
        redenen.append(anom)
    if redenen:
        gewichtje = (n_agent * 50 + (60 if persist_tekst else 0)
                     + n_nieuw * 2 + abs(d_out) + abs(d_nl)
                     + max(0, d_vac) * 3 + max(0, d_site) * 3 + (5 if anom else 0))
        wijzigingen.append({"naam": k["name"], "city": k["city"],
                            "tekst": " · ".join(redenen), "gewicht": gewichtje})

    if i % 25 == 0:
        print(f"...{i}/{len(kantoren)} gescand", flush=True)
    time.sleep(0.35)

wijzigingen.sort(key=lambda w: w["gewicht"], reverse=True)
wijzigingen = wijzigingen[:40]

# ---------- 8. WEGSCHRIJVEN ----------
json.dump({
    "gegenereerd": str(datetime.datetime.now()),
    "vorige_scan": vorige_gen or None,
    "bron": "Masterlijst-CSV + Google News (incl. offshoring-agent) + eigen kantoorwebsites "
            "(vacatures, contactpersonen, e-mail, telefoon, agent-woorden) + accountant.nl + AFM",
    "let_op": "Scores zijn keyword-based. Contactpersonen zijn SUGGESTIES van openbare "
              "kantoorwebsites; de gebruiker bevestigt ze in de app.",
    "wijzigingen": wijzigingen,
    "leads": leads,
}, open("leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
tot_sugg = sum(len(l.get("suggesties") or []) for l in leads)
print(f"\nKlaar — {len(leads)} kantoren, {len(wijzigingen)} met wijzigingen, "
      f"{tot_agent} agent-meldingen, {tot_sugg} contact-suggesties.")
