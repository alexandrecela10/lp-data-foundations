"""Deterministic synthetic world: the LP, its managers, funds, companies, holdings, cash flows,
letters, people and news. All names are invented. Extends the universe of Secondaries Radar
(github.com/alexandrecela10/secondaries-radar, quicklook/synth/universe.py): the J-curve shape and
manager names come from there; funds of funds, co-investments, second-hand stakes, companies with
name variants and parents, people and letters are new.

The generator knows everything. Sources (sources.py) render what the LP would actually receive.
Truth (truth.py) computes known answers from these objects only.

Planted facts (exist for any seed, so the questions and the demo always have them):
- Calder Packaging Ltd, held through 5 routes, under 3 spellings, written down on 2 Sep 2026,
  learnt 10 Sep 2026 from Halvane's letter; a low-confidence concern on 28 Jul 2026.
- Brennick Capital Partners (Manager X) raising Fund VI, with 5 letter issues and 2 departed partners.
"""
from __future__ import annotations

import datetime as dt
import math
import random
from dataclasses import dataclass, field

LP_NAME = "Aldermoor Pension Plan"
NOW = dt.datetime(2026, 10, 26, 8, 12)          # the CIO's question, Monday
TODAY = NOW.date()
PACK_DATE = dt.date(2026, 9, 30)                 # the committee pack's as-of date
FIRST_REPORT_Q = dt.date(2023, 3, 31)            # reports rendered from here on
UNFUNDED_V2_FROM = dt.date(2026, 8, 1)

SHAPES = {  # from secondaries-radar: tau years to call ~63%, final TVPI (mean, sd), realisation centre
    "buyout": dict(tau=1.8, cap=(0.90, 1.00), mult=(1.85, 0.35), centre=9.0, jdip=0.15),
    "growth": dict(tau=1.6, cap=(0.88, 0.98), mult=(1.95, 0.50), centre=9.5, jdip=0.12),
    "venture": dict(tau=2.5, cap=(0.85, 0.97), mult=(2.10, 0.90), centre=11.0, jdip=0.25),
}
SUFFIX = {"buyout": "Capital Partners", "growth": "Growth Partners", "venture": "Ventures"}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
COUNTRY = {"europe": ["United Kingdom", "Germany", "France", "Spain", "Netherlands"],
           "north_america": ["United States", "Canada"], "asia": ["Japan", "Singapore", "Australia"]}
LEGAL = {"United Kingdom": "Ltd", "Germany": "GmbH", "France": "SA", "Spain": "SL", "Netherlands": "BV",
         "United States": "Inc.", "Canada": "Inc.", "Japan": "KK", "Singapore": "Pte Ltd", "Australia": "Pty Ltd"}
SECTORS = ["Software", "Health", "Foods", "Dental", "Analytics", "Labs", "Marine", "Fibre", "Tools", "Education",
           "Payments", "Chemicals", "Clinics", "Logistics", "Security", "Testing", "Packaging", "Pet Care"]
FIRST = ["Mara", "Tomas", "Ilse", "Joel", "Ada", "Pieter", "Selma", "Rafe", "Odile", "Bram", "Ines", "Corin",
         "Lusa", "Fenna", "Arvid", "Noor", "Edda", "Kasimir", "Thea", "Orla"]
LAST = ["Ellingsby", "Reyvik", "Varnholt", "Brandtke", "Morrowen", "Lundqvast", "Achterberg", "Quennell",
        "Dravik", "Holmbrae", "Ostergaard", "Penhallow", "Wrexley", "Calloway-Strand", "Tiernach", "Vasskog"]


@dataclass
class Manager:
    id: str
    name: str
    strategy: str
    region: str
    kind: str = "gp"         # gp | fof
    style: int = 0           # how this manager spells company names (0..3; 4..5 only in the noisy world)
    layout: int = 0          # report layout (0..2; fund of funds use 3)
    domain: str = ""


@dataclass
class Company:
    id: str
    name: str                # canonical legal name
    sector: str
    country: str
    region: str
    parent_id: str | None = None
    is_holdco: bool = False


@dataclass
class Fund:
    id: str
    manager_id: str
    name: str
    vintage: int
    strategy: str
    region: str
    size: float              # $m commitments
    kind: str = "fund"       # fund | fof
    path: dict = field(default_factory=dict)       # quarter end -> (called $m, distributed $m, nav $m)
    weights: dict = field(default_factory=dict)    # company_id -> share of fund value
    stakes: dict = field(default_factory=dict)     # fof only: fund_id -> share of that fund
    report_lag: dict = field(default_factory=dict) # quarter end -> days until the report reached us


@dataclass
class Position:
    id: str
    vehicle_id: str
    vehicle_type: str        # fund | fof | coinvest
    acquired: str            # primary | secondary
    commitment: float
    share: float             # our ownership of the vehicle (coinvest: 1.0)
    start: dt.date
    purchase_price: float = 0.0
    unfunded_at_purchase: float = 0.0
    plan_tvpi: float = 0.0
    plan_irr: float = 0.0


@dataclass
class Coinvest:
    id: str
    company_id: str
    alongside_fund_id: str
    name_on_docs: str
    invested: float
    date: dt.date
    mgmt_fee_pct: float      # restricted column
    carry_pct: float         # restricted column
    growth: float            # value multiple gained per year


@dataclass
class CashFlow:
    id: str
    position_id: str
    kind: str                # call | dist | purchase
    amount: float            # $m, positive
    notice_date: dt.date     # learnt
    value_date: dt.date      # paid or received
    recallable: float = 0.0


@dataclass
class Event:
    id: str
    letter_id: str
    manager_id: str
    kind: str                # write_down | exit | team_change | restatement | extension | fee | incident | concern
    effective: dt.date
    learnt: dt.date
    company_id: str | None = None
    fund_id: str | None = None
    coinvest_ids: tuple = ()
    factor: float | None = None
    person_id: str | None = None
    parseable: bool = True   # does the fixed-pattern reader recognise it
    confidence: float = 0.95
    sentence: str = ""


@dataclass
class Letter:
    id: str
    manager_id: str
    learnt: dt.date
    text: str
    event_ids: list = field(default_factory=list)


@dataclass
class Person:
    id: str
    name: str
    jobs: list               # (manager_id, start, end or None, title)


@dataclass
class News:
    id: str
    ts: dt.datetime
    headline: str
    body: str
    company_id: str | None = None


@dataclass
class World:
    seed: int
    scale: int
    noisy: bool
    managers: dict
    companies: dict
    funds: dict
    positions: dict
    coinvests: dict
    flows: list
    events: dict
    letters: dict
    people: dict
    news: list
    pipeline: list           # planned commitments, restricted rows
    planted: dict

    def manager_of(self, fund_id: str) -> Manager:
        return self.managers[self.funds[fund_id].manager_id]

    def spelling(self, manager_id: str, company_id: str) -> str:
        return spell(self.companies, company_id, self.managers[manager_id].style)


# ------------------------------------------------------------------ helpers

def quarter_ends(start: dt.date, end: dt.date) -> list[dt.date]:
    out, y, q = [], start.year, 1
    while True:
        m = q * 3
        d = dt.date(y, m, 31 if m in (3, 12) else 30)
        if d > end:
            return out
        if d >= start:
            out.append(d)
        q += 1
        if q == 5:
            y, q = y + 1, 1


def legal_strip(name: str) -> str:
    for suf in sorted(set(LEGAL.values()), key=len, reverse=True):
        if name.endswith(" " + suf):
            return name[: -len(suf) - 1]
    return name


def spell(companies: dict, cid: str, style: int) -> str:
    """How a manager writes a company's name. 0 legal name, 1 no suffix, 2 abbreviated, 3 holding
    company name when there is one. 4 and 5 appear only in the noisy (held-out) world."""
    c = companies[cid]
    base = legal_strip(c.name)
    words = base.split()
    if style == 0:
        return c.name
    if style == 1:
        return base
    if style == 2:
        if len(words) >= 2 and len(words[-1]) > 5:
            return " ".join(words[:-1] + [words[-1][:4] + "."])
        return base
    if style == 3:
        par = companies.get(c.parent_id) if c.parent_id else None
        return par.name if par is not None and par.is_holdco else base
    if style == 4:                      # upper case, long legal form
        return (base + " LIMITED").upper() if c.country == "United Kingdom" else base.upper()
    if style == 5:                      # dropped letter in the first word
        w = words[0]
        return " ".join([w[:2] + w[3:]] + words[1:]) if len(w) > 4 else base
    raise ValueError(style)


def _path(fund: Fund, rng: random.Random, until: dt.date) -> dict:
    """Quarterly (called, distributed, nav) in $m: a J-curve, adapted from secondaries-radar."""
    s = SHAPES[fund.strategy]
    cap = rng.uniform(*s["cap"])
    tau = s["tau"] * rng.uniform(0.85, 1.15)
    m = max(0.7, rng.gauss(*s["mult"]))
    centre = s["centre"] + rng.uniform(-1, 1)
    out, noise, best_d, called_prev = {}, 0.0, 0.0, 0.0
    for d in quarter_ends(dt.date(fund.vintage, 1, 1), until):
        a = (d - dt.date(fund.vintage, 1, 1)).days / 365.25
        called = max(called_prev, cap * (1 - math.exp(-a / tau)))
        growth = 1 / (1 + math.exp(-(a - 5.5) / 1.5)) - 1 / (1 + math.exp(5.5 / 1.5))
        noise += rng.gauss(0, 0.012)
        tvpi = 1 - s["jdip"] * math.exp(-a / 1.5) + (m - 1) * growth + noise * min(1.0, a / 3)
        realised = 0.97 / (1 + math.exp(-(a - centre) / 1.4)) - 0.97 / (1 + math.exp(centre / 1.4))
        dpi = max(best_d, m * realised)
        best_d = dpi
        tvpi = max(tvpi, dpi + 0.05)
        c = fund.size * called
        dist = c * dpi
        nav = c * (tvpi - dpi)
        # distributions only go up as called grows; keep cumulative distributions monotone
        if out:
            pc, pd, _ = out[list(out)[-1]]
            dist = max(dist, pd)
        out[d] = (round(c, 6), round(dist, 6), round(max(nav, 0.0), 6))
        called_prev = called
    return out


def _syll_name(rng: random.Random, used: set) -> str:
    syl = ["ar", "bel", "cor", "dun", "el", "fen", "gar", "hal", "is", "jor", "kel", "lan", "mor", "nor",
           "os", "pen", "quil", "ros", "sel", "tor", "ul", "ven", "wex", "yar", "zel"]
    while True:
        w = "".join(rng.choice(syl) for _ in range(rng.choice([2, 3]))).capitalize()
        if w not in used:
            used.add(w)
            return w


# ------------------------------------------------------------------ generator

def generate(seed: int = 42, scale: int = 1, noisy: bool = False) -> World:
    """Build the world. scale multiplies managers, funds and companies (planted facts stay)."""
    rng = random.Random(seed)
    until = dt.date(2026, 12, 31)
    managers: dict[str, Manager] = {}
    companies: dict[str, Company] = {}
    funds: dict[str, Fund] = {}
    positions: dict[str, Position] = {}
    coinvests: dict[str, Coinvest] = {}
    events: dict[str, Event] = {}
    letters: dict[str, Letter] = {}
    people: dict[str, Person] = {}

    # --- managers: planted 16, then generic ones for scale
    spec = [  # id, base, strategy, region, kind, style, layout
        ("M01", "Halvane", "buyout", "europe", "gp", 0, 0),
        ("M02", "Brennick", "buyout", "north_america", "gp", 1, 1),
        ("M03", "Tellmar", "buyout", "europe", "gp", 3, 2),
        ("M04", "Ostrova", "buyout", "europe", "gp", 2, 1),
        ("M05", "Wexcombe", "growth", "north_america", "gp", 1, 0),
        ("M06", "Quillon", "buyout", "europe", "gp", 1, 0),
        ("M07", "Marrowby", "growth", "north_america", "gp", 0, 2),
        ("M08", "Fenlow", "growth", "europe", "gp", 2, 1),
        ("M09", "Arkwell", "buyout", "north_america", "gp", 0, 0),
        ("M10", "Dunmere", "buyout", "europe", "gp", 2, 2),
        ("M11", "Varrow", "venture", "north_america", "gp", 1, 1),
        ("M12", "Orlaith", "growth", "asia", "gp", 0, 0),
        ("M13", "Thornhale", "buyout", "north_america", "gp", 1, 2),
        ("M14", "Caskel", "buyout", "europe", "gp", 0, 1),
        ("M15", "Selbrook", "buyout", "europe", "fof", 1, 3),
        ("M16", "Pellam", "buyout", "north_america", "gp", 3, 0),
    ]
    for mid, base, strat, region, kind, style, layout in spec:
        name = f"{base} Partners" if kind == "fof" else f"{base} {SUFFIX[strat]}"
        if noisy and mid in ("M06", "M09", "M12"):
            style = 4 if mid != "M12" else 5      # held-out world: spellings never tuned on
        managers[mid] = Manager(mid, name, strat, region, kind, style, layout, f"{base.lower()}.example")
    used = {s[1] for s in spec}
    for i in range(16 * (scale - 1)):
        base = _syll_name(rng, used)
        strat = rng.choices(["buyout", "growth", "venture"], [0.6, 0.25, 0.15])[0]
        region = rng.choices(list(COUNTRY), [0.45, 0.4, 0.15])[0]
        mid = f"M{17 + i:04d}"
        managers[mid] = Manager(mid, f"{base} {SUFFIX[strat]}", strat, region, "gp", rng.choice([0, 1, 2, 3]),
                                rng.choice([0, 1, 2]), f"{base.lower()}.example")

    # --- companies
    def add_company(cid, word, sector, country, parent=None, holdco=False, name=None):
        region = next(r for r, cs in COUNTRY.items() if country in cs)
        nm = name or f"{word} {sector} {LEGAL[country]}"
        companies[cid] = Company(cid, nm, sector, country, region, parent, holdco)

    add_company("C0001", "Calder", "Packaging", "United Kingdom", parent="H0001")
    add_company("H0001", "", "Packaging", "United Kingdom", holdco=True, name="Calderwick Holdings")
    add_company("C0002", "Brisolen", "Packaging", "Spain")
    add_company("C0003", "Marlowen", "Packaging", "Germany")
    add_company("C0004", "Junavel", "Software", "United States")
    add_company("C0005", "Kelmara", "Dental", "United States")
    add_company("C0006", "Sabrel", "Security", "United Kingdom")
    add_company("C0007", "Nordvale", "Logistics", "Netherlands")
    add_company("C0008", "Wyrecombe", "Packaging", "United Kingdom")   # held by a fund we don't own
    # Generated company names use invented words (syllables), so no generated name is a real company's.
    n_generic = 260 * scale
    wused = {"Calder", "Brisolen", "Marlowen", "Junavel", "Kelmara", "Sabrel", "Nordvale", "Wyrecombe"}
    pool = [(_syll_name(rng, wused), rng.choice(SECTORS)) for _ in range(n_generic)]
    hcount = 1
    for i, (w, s) in enumerate(pool[:n_generic]):
        region = rng.choices(list(COUNTRY), [0.45, 0.4, 0.15])[0]
        country = rng.choice(COUNTRY[region])
        cid = f"C{9 + i:05d}"
        parent = None
        if rng.random() < 0.08:                      # some companies sit under a pure holding company
            hcount += 1
            hid = f"H{hcount:04d}"
            hname = f"{w}wick Holdings"
            if any(c.name == hname for c in companies.values()):
                hname = f"{w}wick {s} Holdings"
            add_company(hid, "", s, country, holdco=True, name=hname)
            parent = hid
        add_company(cid, w, s, country, parent=parent)
    if noisy:  # near-duplicate names that are different companies (a precision trap)
        add_company("C0009N", "Brisolen", "Packing", "Spain")
        add_company("C0010N", "Sabrel", "Securities", "United Kingdom")
    operating = [c for c in companies.values() if not c.is_holdco and c.id not in
                 ("C0001", "C0002", "C0003", "C0004", "C0005", "C0006", "C0007", "C0008")]

    # --- funds
    fspec = [  # manager, number, vintage, size, our commitment (0 = none), acquired
        ("M01", 4, 2016, 800, 30, "primary"), ("M01", 5, 2020, 1000, 40, "primary"),
        ("M02", 2, 2012, 600, 0, ""), ("M02", 3, 2015, 750, 25, "primary"), ("M02", 4, 2018, 1000, 35, "primary"),
        ("M02", 5, 2021, 1250, 40, "primary"),
        ("M03", 2, 2013, 500, 0, ""), ("M03", 3, 2017, 700, 0, "secondary"),
        ("M04", 4, 2019, 900, 0, ""),
        ("M05", 1, 2016, 400, 20, "primary"), ("M05", 2, 2022, 650, 25, "primary"),
        ("M06", 3, 2016, 700, 30, "primary"), ("M06", 4, 2019, 900, 30, "primary"),
        ("M07", 3, 2018, 500, 20, "primary"),
        ("M08", 2, 2017, 450, 15, "primary"),
        ("M09", 2, 2017, 800, 0, ""), ("M09", 3, 2021, 1100, 35, "primary"),
        ("M10", 2, 2020, 750, 30, "primary"),
        ("M11", 4, 2019, 300, 10, "primary"),
        ("M12", 2, 2021, 500, 15, "primary"),
        ("M13", 3, 2015, 900, 0, ""), ("M13", 4, 2019, 1200, 30, "primary"),
        ("M14", 1, 2022, 600, 25, "primary"),
        ("M16", 2, 2023, 700, 20, "primary"),
    ]
    fid_of = {}
    for mid, num, vint, size, commit, acq in fspec:
        m = managers[mid]
        fid = f"F{len(funds) + 1:04d}"
        funds[fid] = Fund(fid, mid, f"{m.name} {ROMAN[num - 1]}", vint, m.strategy, m.region, float(size))
        fid_of[(mid, num)] = fid
        if commit:
            positions[f"P{fid}"] = Position(f"P{fid}", fid, "fund", "primary", float(commit), commit / size,
                                            dt.date(vint, 3, 1), plan_tvpi=round(rng.uniform(1.9, 2.3), 2),
                                            plan_irr=round(rng.uniform(0.16, 0.22), 3))
    # generic funds for scale
    for mid, m in managers.items():
        if int(mid[1:]) <= 16:
            continue
        v = rng.randint(2010, 2016)
        n = 0
        while v <= 2024 and n < 4:
            n += 1
            fid = f"F{len(funds) + 1:06d}"
            size = round(rng.uniform(300, 1500), -1)
            funds[fid] = Fund(fid, mid, f"{m.name} {ROMAN[n - 1]}", v, m.strategy, m.region, size)
            if rng.random() < 0.55:
                c = round(rng.uniform(10, 50), 0)
                positions[f"P{fid}"] = Position(f"P{fid}", fid, "fund", "primary", c, c / size, dt.date(v, 3, 1),
                                                plan_tvpi=round(rng.uniform(1.9, 2.3), 2),
                                                plan_irr=round(rng.uniform(0.16, 0.22), 3))
            v += rng.choice([3, 3, 4])

    for f in funds.values():
        f.path = _path(f, rng, until)

    # --- company holdings (weights of fund value)
    def hold(fid, planted: dict):
        n = rng.randint(8, 12)
        picks = rng.sample(operating, n - len(planted))
        raw = [rng.gammavariate(1.2, 1.0) for _ in picks]
        rest = 1.0 - sum(planted.values())
        w = {c.id: rest * r / sum(raw) for c, r in zip(picks, raw)}
        w.update(planted)
        funds[fid].weights = w

    hold(fid_of[("M01", 5)], {"C0001": 0.15, "C0006": 0.07})          # Halvane V: Calder, Sabrel
    hold(fid_of[("M04", 4)], {"C0001": 0.08})                         # Ostrova IV: "Calder Pack."
    hold(fid_of[("M03", 3)], {"C0001": 0.06, "C0003": 0.05})          # Tellmar III: "Calderwick Holdings"
    hold(fid_of[("M06", 4)], {"C0002": 0.09, "C0007": 0.06})          # Quillon IV: Brisolen Packaging
    hold(fid_of[("M02", 4)], {"C0004": 0.10})                         # Brennick IV: Junavel Software
    hold(fid_of[("M02", 5)], {"C0005": 0.08})                         # Brennick V: Kelmara Dental
    hold(fid_of[("M13", 3)], {"C0008": 0.05})                         # Thornhale III (not held): Wyrecombe
    for fid, f in funds.items():
        if not f.weights:
            hold(fid, {})
    # about 10% of generic companies are held by a second fund (club deals); weights renormalised
    fids = [fid for fid in funds if funds[fid].kind == "fund"]
    for fid in fids:
        if rng.random() < 0.3:
            other = funds[rng.choice(fids)]
            cid = rng.choice([c for c in other.weights if c.startswith("C0") and int(c[1:].rstrip("N")) > 8]
                             or list(other.weights))
            if cid not in funds[fid].weights and cid != "C0001":
                w = funds[fid].weights
                w[cid] = 0.04
                tot = sum(w.values())
                for k in w:
                    w[k] /= tot

    # --- report lags (days from quarter end to the day the report reached us)
    planted_lag = {(fid_of[("M01", 5)], dt.date(2026, 6, 30)): 51,     # Halvane V Q2: 20 Aug
                   (fid_of[("M03", 3)], dt.date(2026, 6, 30)): 59}     # Tellmar III Q2: 28 Aug
    for fid, f in funds.items():
        for q in f.path:
            f.report_lag[q] = planted_lag.get((fid, q), rng.randint(45, 88))

    # --- fund of funds: Selbrook FoF III holds stakes in five funds, two of them also held directly
    fof = Fund("FOF01", "M15", "Selbrook Fund of Funds III", 2018, "buyout", "europe", 0.0, kind="fof")
    fof.stakes = {fid_of[("M04", 4)]: 0.05, fid_of[("M01", 5)]: 0.03, fid_of[("M08", 2)]: 0.04,
                  fid_of[("M06", 4)]: 0.02, fid_of[("M07", 3)]: 0.03}
    fof.size = round(sum(s * funds[u].size for u, s in fof.stakes.items()), 4)
    path = {}
    for q in funds[fid_of[("M04", 4)]].path:
        c = d_ = n = 0.0
        for u, s in fof.stakes.items():
            pc, pd, pn = funds[u].path.get(q, (0.0, 0.0, 0.0))
            c, d_, n = c + s * pc, d_ + s * pd, n + s * pn
        path[q] = (round(c, 6), round(d_, 6), round(n, 6))
    fof.path = path
    fof.report_lag = {q: (77 if q == dt.date(2026, 6, 30) else rng.randint(60, 88)) for q in path}  # Q2: 15 Sep
    funds["FOF01"] = fof
    positions["PFOF01"] = Position("PFOF01", "FOF01", "fof", "primary", 50.0, 50.0 / fof.size,
                                   dt.date(2018, 6, 1), plan_tvpi=1.8, plan_irr=0.14)

    # --- the stake bought second-hand: 3% of Tellmar III, bought 30 Jun 2024 at 88% of its value
    t3 = funds[fid_of[("M03", 3)]]
    pq = dt.date(2024, 6, 30)
    share = 0.03
    pc, _, pn = t3.path[pq]
    positions[f"P{t3.id}"] = Position(f"P{t3.id}", t3.id, "fund", "secondary", round(share * t3.size, 4), share,
                                      pq, purchase_price=round(0.88 * share * pn, 6),
                                      unfunded_at_purchase=round(share * (t3.size - pc), 6),
                                      plan_tvpi=1.6, plan_irr=0.15)

    # --- co-investments (fee terms are restricted columns)
    co = [("CI01", "H0001", fid_of[("M01", 5)], "Calderwick Holdings (holding company of Calder Packaging Ltd)", 5.0,
           dt.date(2021, 3, 15), 0.0, 10.0, 0.045),
          ("CI02", "C0004", fid_of[("M02", 4)], "Junavel Software Inc.", 8.0, dt.date(2019, 9, 2), 1.0, 15.0, 0.12),
          ("CI03", "C0005", fid_of[("M02", 5)], "Kelmara Dental Inc.", 6.0, dt.date(2022, 5, 20), 0.0, 10.0, -0.12)]
    for cid, comp, along, nm, inv, d, fee, carry, g in co:
        coinvests[cid] = Coinvest(cid, comp, along, nm, inv, d, fee, carry, g)
        positions[f"P{cid}"] = Position(f"P{cid}", cid, "coinvest", "primary", inv, 1.0, d)
    for k in range(3 * (scale - 1)):
        along = rng.choice([p.vehicle_id for p in positions.values() if p.vehicle_type == "fund"])
        comp = rng.choice(list(funds[along].weights))
        cid = f"CI{4 + k:05d}"
        inv = round(rng.uniform(3, 12), 1)
        coinvests[cid] = Coinvest(cid, comp, along, companies[comp].name, inv, dt.date(2021, 6, 1), 1.0, 12.0, 0.05)
        positions[f"P{cid}"] = Position(f"P{cid}", cid, "coinvest", "primary", inv, 1.0, dt.date(2021, 6, 1))

    # --- our cash flows (calls, distributions, purchase), from the vehicle paths
    flows: list[CashFlow] = []
    for pid, p in sorted(positions.items()):
        if p.vehicle_type == "coinvest":
            c = coinvests[p.vehicle_id]
            flows.append(CashFlow(f"{pid}:C0", pid, "call", c.invested, c.date - dt.timedelta(days=10), c.date))
            continue
        f = funds[p.vehicle_id]
        qs = sorted(f.path)
        prev = (0.0, 0.0, 0.0)
        if p.acquired == "secondary":
            flows.append(CashFlow(f"{pid}:B", pid, "purchase", p.purchase_price, p.start, p.start))
            prev = f.path[p.start]
            qs = [q for q in qs if q > p.start]
        for i, q in enumerate(qs):
            c, d_, _ = f.path[q]
            dc = round(p.share * (c - prev[0]), 6)
            dd = round(p.share * (d_ - prev[1]), 6)
            prev = f.path[q]
            for kind, amt in (("call", dc), ("dist", dd)):
                if amt <= 0.0005:
                    continue
                vd = q - dt.timedelta(days=rng.randint(5, 80))
                if vd > TODAY:
                    continue
                nd = vd - dt.timedelta(days=10)
                rec = 0.0
                if kind == "dist" and (q.year - f.vintage) <= 5 and rng.random() < 0.4:
                    rec = round(amt * 0.25, 6)
                flows.append(CashFlow(f"{pid}:{kind[0].upper()}{i}", pid, kind, amt, nd, vd, rec))

    # --- letters and events
    def letter(lid, mid, learnt, sentences, evs=()):
        intro = f"Dear investors, this letter from {managers[mid].name} covers recent portfolio news."
        letters[lid] = Letter(lid, mid, learnt, " ".join([intro] + list(sentences)), [e.id for e in evs])
        for e in evs:
            events[e.id] = e

    hv = fid_of[("M01", 5)]
    e1 = Event("E0001", "L0001", "M01", "concern", dt.date(2026, 7, 28), dt.date(2026, 7, 28), "C0001", hv,
               parseable=True, confidence=0.55,
               sentence="Trading at Calder Packaging softened in the second quarter, and we are watching covenant headroom closely.")
    letter("L0001", "M01", dt.date(2026, 7, 28), [e1.sentence], [e1])
    e2 = Event("E0002", "L0002", "M01", "write_down", dt.date(2026, 9, 2), dt.date(2026, 9, 10), "C0001", hv,
               ("CI01",), 0.40,
               sentence="Calder Packaging Ltd was written down on 2 September 2026 to 0.40 times its 30 June 2026 value, after a weak trading update. The co-investment in Calderwick Holdings is marked at the same multiple.")
    letter("L0002", "M01", dt.date(2026, 9, 10), [e2.sentence], [e2])
    q7 = fid_of[("M06", 4)]
    e3 = Event("E0003", "L0003", "M06", "exit", dt.date(2026, 8, 12), dt.date(2026, 8, 19), "C0007", q7, (), 1.60,
               sentence="The sale of Nordvale Logistics BV was agreed on 12 August 2026, at 1.60 times its 30 June 2026 value.")
    letter("L0003", "M06", dt.date(2026, 8, 19), [e3.sentence], [e3])
    e4 = Event("E0004", "L0004", "M01", "write_down", dt.date(2026, 8, 20), dt.date(2026, 9, 1), "C0006", hv, (),
               0.50, sentence="Sabrel Security Ltd was written down on 20 August 2026 to 0.50 times its 30 June 2026 value, after the loss of a major contract.")
    letter("L0004", "M01", dt.date(2026, 9, 1), [e4.sentence], [e4])

    # Brennick (Manager X): five issues, one hard to parse, one low confidence
    b4, b5 = fid_of[("M02", 4)], fid_of[("M02", 5)]
    people["PE01"] = Person("PE01", "Mara Ellingsby", [("M02", dt.date(2005, 1, 1), dt.date(2024, 3, 15), "Founding partner"),
                                                    ("M05", dt.date(2024, 6, 1), None, "Partner")])
    people["PE02"] = Person("PE02", "Tomas Reyvik", [("M02", dt.date(2008, 1, 1), None, "Managing partner")])
    people["PE03"] = Person("PE03", "Ilse Varnholt", [("M02", dt.date(2011, 1, 1), None, "Partner")])
    people["PE04"] = Person("PE04", "Joel Brandtke", [("M02", dt.date(2009, 1, 1), dt.date(2019, 12, 31), "Partner"),
                                                   ("M14", dt.date(2020, 4, 1), None, "Partner")])
    bre = [
        Event("E0101", "L0101", "M02", "extension", dt.date(2023, 6, 30), dt.date(2023, 7, 20), fund_id=b4,
              sentence="We extended the investment period of Brennick Capital Partners IV by one year, with the consent of the advisory committee."),
        Event("E0102", "L0102", "M02", "restatement", dt.date(2023, 12, 31), dt.date(2024, 2, 20), fund_id=b4,
              sentence="The valuation of Brennick Capital Partners IV as of 31 December 2023 has been restated, down 3.6%, after an audit adjustment."),
        Event("E0103", "L0103", "M02", "team_change", dt.date(2024, 3, 15), dt.date(2024, 3, 15), person_id="PE01",
              sentence="Mara Ellingsby, a founding partner, has left the firm. The key person clause in Brennick Capital Partners V was not triggered."),
        Event("E0104", "L0104", "M02", "fee", dt.date(2025, 7, 1), dt.date(2025, 5, 10), parseable=False,
              sentence="After questions from investors, we will offset all transaction fees against management fees from 1 July 2025."),
        Event("E0105", "L0105", "M02", "incident", dt.date(2026, 4, 12), dt.date(2026, 4, 12), confidence=0.6,
              sentence="We are reviewing a reported data incident at a portfolio company and will update investors."),
    ]
    for e in bre:
        letter(e.letter_id, "M02", e.learnt, [e.sentence], [e])

    # routine quarterly letters (no events) and random exits and write-downs after 30 June 2026
    held_funds = [p.vehicle_id for p in positions.values() if p.vehicle_type == "fund"]
    n_ev = 0
    for fid in sorted(held_funds):
        f = funds[fid]
        if fid in (hv, q7) or rng.random() > 0.35:
            continue
        cid = rng.choice([c for c in f.weights if c not in ("C0001",)])
        exit_ = rng.random() < 0.6
        day = dt.date(2026, 6, 30) + dt.timedelta(days=rng.randint(5, 100))
        told = day + dt.timedelta(days=rng.randint(3, 20))
        if told > TODAY:
            continue
        n_ev += 1
        factor = round(rng.uniform(1.15, 1.6) if exit_ else rng.uniform(0.4, 0.8), 2)
        nm = spell(companies, cid, managers[f.manager_id].style)
        if exit_:
            s = f"The sale of {nm} was agreed on {day.day} {day:%B %Y}, at {factor:.2f} times its 30 June 2026 value."
        else:
            s = f"{nm} was written down on {day.day} {day:%B %Y} to {factor:.2f} times its 30 June 2026 value."
        eid, lid = f"E{1000 + n_ev:04d}", f"L{1000 + n_ev:04d}"
        letter(lid, f.manager_id, told, [s], [Event(eid, lid, f.manager_id, "exit" if exit_ else "write_down", day,
                                                     told, cid, fid, (), factor, sentence=s)])
    for mid, m in managers.items():
        if int(mid[1:]) > 16:
            continue
        for q in quarter_ends(FIRST_REPORT_Q, dt.date(2026, 9, 30)):
            lid = f"LQ{mid}{q:%Y%m}"
            learnt = q + dt.timedelta(days=rng.randint(20, 40))
            if learnt > TODAY:
                continue
            letter(lid, mid, learnt, [f"Portfolio activity in the quarter to {q.day} {q:%B %Y} was in line with plan."])

    # --- other people (invented manager partners)
    k = 5
    for mid in [m for m in managers if int(m[1:]) <= 16 and m != "M02"]:
        for _ in range(2):
            nm = f"{FIRST[k % len(FIRST)]} {LAST[(k * 7) % len(LAST)]}"
            people[f"PE{k:02d}"] = Person(f"PE{k:02d}", nm, [(mid, dt.date(2010 + k % 8, 1, 1), None, "Partner")])
            k += 1

    # --- news every 15 minutes for the 24 hours before the question
    news = []
    start = NOW.replace(minute=0) - dt.timedelta(hours=24)
    names = [c for c in companies.values() if not c.is_holdco]
    topics = ["wins a contract", "names a new chief executive", "opens a site", "is said to explore a sale",
              "reports steady trading", "faces a supplier delay"]
    for i in range(96):
        ts = start + dt.timedelta(minutes=15 * i)
        c = rng.choice(names)
        news.append(News(f"N{i:03d}", ts, f"{legal_strip(c.name)} {rng.choice(topics)}", "Synthetic news item.", c.id))
    news[-1] = News("N095", dt.datetime(2026, 10, 26, 8, 0), "Calder Packaging begins debt restructuring talks",
                    "Calder Packaging has started talks with lenders over about $400m of debt, people familiar said.",
                    "C0001")

    pipeline = [dict(manager_id="M02", fund_name="Brennick Capital Partners VI", proposed_commitment=45.0,
                     status="not yet approved")]
    planted = dict(calder="C0001", calder_holdco="H0001", halvane_v=hv, ostrova_iv=fid_of[("M04", 4)],
                   tellmar_iii=t3.id, fof="FOF01", brennick="M02", brennick_funds=[fid_of[("M02", n)] for n in (3, 4, 5)],
                   wexcombe="M05", caskel="M14", quillon_iv=q7)
    return World(seed, scale, noisy, managers, companies, funds, positions, coinvests, flows, events, letters,
                 people, news, pipeline, planted)
