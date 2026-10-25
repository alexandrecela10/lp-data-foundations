"""A: documents + search. No structured data: the AI reads the passages search returns.

OFFLINE STAND-IN. The offline reader does what a careful reader of the passages would do, and no more:
- expands the company name with the company reference sheet (a holding company's name);
- for each fund, takes the latest report it found (by the report's own as-of date) and multiplies each
  matching line by "your share" stated in that same document;
- reads manager-reported IRR and TVPI from report headers; sums notices for cash in a period;
- lists letters that mention an issue, with the letter as the citation.
It does not know that a fund of funds' look-through line needs the fund of funds' own share of the
underlying fund, when a report reached us, or how to apply a write-down from a letter to a number.
Live mode replaces this reader with Claude reading the same passages.
"""
from __future__ import annotations

import re
from collections import defaultdict

from ..answer import Answer, Shown, Step, money, pct, ratio
from ..pipeline import normalise
from .base import Foundation, refuse
from .search import Search

ISSUE = r"left the firm|restated|extended|fee|incident|written down|dispute|key person|breach|covenant|softened"


def _f(s):
    return float(s.replace(",", ""))


def share_in(text: str) -> float | None:
    for pat in [r"Your share of the fund of funds: ([\d.]+)%", r"Your share of the fund: ([\d.]+)%", r"ownership ([\d.]+)%",
                r"lp_ownership_pct;([\d.]+)"]:
        m = re.search(pat, text)
        if m:
            return float(m.group(1)) / 100
    return None


ROMAN_FIX = {"Ii": "II", "Iii": "III", "Iv": "IV", "Vi": "VI", "Vii": "VII", "Viii": "VIII", "Ix": "IX"}


def title(text: str) -> str:
    first = text.splitlines()[0]
    first = first.split(", quarterly statement")[0].split(" - Investor Report")[0].split(";REPORT")[0]
    if first.isupper():
        first = " ".join(ROMAN_FIX.get(w, w) for w in first.title().split())
    return first


def header(text: str) -> dict:
    out = {}
    m = re.search(r"Vintage:? (\d{4})|vintage;(\d{4})", text)
    if m:
        out["vintage"] = int(m.group(1) or m.group(2))
    m = re.search(r"[Ss]trategy:? (\w+)|strategy;(\w+)", text)
    if m:
        out["strategy"] = (m.group(1) or m.group(2)).lower()
    m = re.search(r"Net IRR since inception[^:]*: (\S+)|Reported net IRR: (\S+)|reported_net_irr;(\S+)", text)
    if m:
        s = next(g for g in m.groups() if g)
        out["irr"] = None if s == "n/m" else float(s.rstrip("%")) / 100
    m = re.search(r"Net TVPI \(fund level\): ([\d.]+)x|Reported net TVPI: ([\d.]+)x|reported_net_tvpi;([\d.]+)", text)
    if m:
        out["tvpi"] = float(next(g for g in m.groups() if g))
    m = re.search(r"Your net asset value: \$([\d,.]+)m|; NAV USD ([\d.]+)m|lp_nav_usd_m;([\d.]+)", text)
    if m:
        out["lp_nav"] = _f(next(g for g in m.groups() if g))
    return out


def mentions(line: str, terms: list[str]) -> bool:
    """A line names the company: its full name, a holding company name, or its first word followed by
    an abbreviation of the second ("Calder Pack.")."""
    low = " " + re.sub(r"[^a-z0-9. ]", " ", line.lower()) + " "
    for t in terms:
        if " " + t + " " in low or " " + t + "." in low:
            return True
        w = t.split()
        if len(w) >= 2:
            m = re.search(rf" {re.escape(w[0])} (\w+)\.", low)
            if m and w[1].startswith(m.group(1)):
                return True
    return False


def lines_for(text: str, terms: list[str]) -> list[tuple[str, float]]:
    out = []
    for ln in text.splitlines():
        if not mentions(ln, terms):
            continue
        nums = re.findall(r"(\d[\d,]*\.\d+)", ln)
        if nums:
            out.append((ln.strip(), _f(nums[-1])))
    return out


class DocsArm(Foundation):
    key, name = "A", "Documents + search"
    calls_per_answer = 1

    def __init__(self, store, role="analyst"):
        super().__init__(store, role)
        self.s = Search(store, role)

    def answer(self, text, it) -> Answer:
        if self.live:
            try:
                return self.live_answer(text, it)
            except Exception as e:
                self.failed("answer", e)
        fn = getattr(self, f"t_{it.task}", None)
        if fn is None:
            return refuse(self.key, "I found nothing in the documents that answers this.")
        return fn(it)

    def _passages(self, ans, q, docs):
        txt = "\n---\n".join(d.text[:1500] for d in docs)
        ans.steps.append(Step(name="AI reads passages", input=f"Question: {q}\n{txt}"[:12000],
                              output=f"{len(docs)} passages"))

    def live_answer(self, text, it) -> Answer:
        from .. import llm
        ans = Answer(foundation=self.key, question="")
        docs = self.s.query(text, k=12, before=it.as_of)
        self._passages(ans, text, docs)
        body = "\n---\n".join(f"[{d.doc_id}] (received {d.learnt_at})\n{d.text[:2500]}" for d in docs)
        data, use = llm.ask_json("You answer an LP analyst's question from these documents only. " + llm.ANSWER_RULES,
                                 f"Question: {text}\n\nDocuments:\n{body}", llm.ANSWER_SCHEMA)
        self._usage = getattr(self, "_usage", []) + [use]
        return llm.to_answer(ans, data, sourced=True)

    # ---------------------------------------------------------- exposure
    def _terms(self, company: str) -> list[str]:
        key = normalise(company)
        terms = {key} if key else set()
        for d in self.s.query(company + " holding company only asset", k=5, kinds=("company_text",)):
            m = re.search(r"Company reference: (.+?) is a holding company. Its only asset is (.+?) \(", d.text)
            if not m:
                continue
            hold, asset = normalise(m.group(1)), normalise(m.group(2))
            if hold == key:                      # asked by the holding company's name
                terms.add(asset)
            elif mentions(m.group(2), [key]) or asset == key:
                terms.add(hold)
        return sorted(terms)

    def _latest_docs(self, it, q, kinds=("fund_report", "coinvest_statement")):
        docs = self.s.query(q, k=500, kinds=kinds)
        latest = {}
        for d in docs:
            if d.as_of and d.as_of > it.as_of:
                continue
            k = title(d.text) if d.kind == "fund_report" else re.search(r"Reference: (\S+)", d.text).group(1)
            if k not in latest or d.as_of > latest[k].as_of:
                latest[k] = d
        return latest

    def _exposure(self, it, ans, company):
        terms = self._terms(company)
        latest = self._latest_docs(it, " ".join(terms + [company]))
        self._passages(ans, it.model_dump_json(), list(latest.values()))
        rows = []
        for k, d in latest.items():
            if d.kind == "coinvest_statement":
                if mentions(d.text.splitlines()[0], terms):
                    v = _f(re.search(r"Your value: \$([\d,.]+)m", d.text).group(1))
                    rows.append(dict(via="coinvest", fund=k, line=d.text.splitlines()[0], value=v, doc=d.doc_id, as_of=d.as_of))
                continue
            sh = share_in(d.text)
            fof = "quarterly statement" in d.text.splitlines()[0]
            for ln, val in lines_for(d.text, terms):
                if ln.startswith("* ") and "|" not in ln:
                    continue
                fund = ln[2:].split(" | ")[0] if fof else k
                rows.append(dict(via="fof" if fof else "direct", fund=fund, line=ln, value=val * (sh or 0), doc=d.doc_id,
                                 as_of=d.as_of))
        rows = [r for r in rows if r["via"] not in it.exclude_route_kinds and
                (not it.only_route_kinds or r["via"] in it.only_route_kinds)]
        return rows

    def t_exposure(self, it):
        ans = Answer(foundation=self.key, question="")
        if not it.company:
            return self._sector(it, ans)
        rows = self._exposure(it, ans, it.company)
        ans.value = sum(r["value"] for r in rows)
        ans.route_sigs = sorted({f"{r['via']}:{r['fund']}" for r in rows if r["value"] > 1e-9})
        ans.routes = [dict(route=f"{r['fund']}: {r['line']}", kind=r["via"], value=r["value"], as_of=r["as_of"],
                           sources=[r["doc"]]) for r in rows]
        ans.shown = [Shown(label="total", value=ans.value, unit="$m", sourced=True, sources=[r["doc"] for r in rows])] + \
                    [Shown(label=r["fund"], value=r["value"], unit="$m", sourced=True, sources=[r["doc"]]) for r in rows]
        notes = [d for d in self.s.query(it.company + " written down", k=5, kinds=("letter",), before=it.as_of)
                 if "written down" in d.text and mentions(d.text, self._terms(it.company))]
        ans.text = f"From the reports I found: about {money(ans.value)}.\n" + "\n".join(
            f"- {r['fund']}: {money(r['value'])} ({r['doc']})" for r in rows)
        if notes:
            ans.text += f"\nA letter mentions a write-down ({notes[0].doc_id}); I can't tell how it changes these figures."
            ans.allowed_numbers = [0.40, 2, 30]
        return ans

    def _sector(self, it, ans):
        docs = self.s.query(f"{it.sector or ''} {it.country or ''} portfolio", k=60, kinds=("fund_report",))
        latest = {}
        for d in docs:
            if d.as_of <= it.as_of and (title(d.text) not in latest or d.as_of > latest[title(d.text)].as_of):
                latest[title(d.text)] = d
        self._passages(ans, it.model_dump_json(), list(latest.values()))
        eu = ["United Kingdom", "Germany", "France", "Spain", "Netherlands"]
        tot, rows = 0.0, []
        ex = [normalise(x).split()[0] for x in it.exclude_companies]
        for k, d in latest.items():
            sh = share_in(d.text) or 0
            for m in re.finditer(r"^\| (.+?) \| (.+?) \| (.+?) \| ([\d,.]+) \|$", d.text, re.M):
                name, sector, country, val = m.groups()
                if sector != it.sector:
                    continue
                if it.country and country != it.country or it.region == "europe" and country not in eu:
                    continue
                if any(normalise(name).startswith(e) for e in ex):
                    continue
                tot += _f(val) * sh
                rows.append((k, name, _f(val) * sh, d.doc_id))
        ans.value = tot
        ans.shown = [Shown(label="total", value=tot, unit="$m", sourced=True)] + \
                    [Shown(label=r[1], value=r[2], unit="$m", sourced=True, sources=[r[3]]) for r in rows]
        ans.text = f"From reports that list sectors: {money(tot)}.\n" + "\n".join(f"- {r[0]}: {r[1]} {money(r[2])}" for r in rows)
        return ans

    def t_exposure_share(self, it):
        ans = self.t_exposure(it)
        navs = [header(d.text).get("lp_nav", 0) for d in self._latest_docs(it, "your net asset value", ("fund_report",)).values()]
        cos = [_f(re.search(r"Your value: \$([\d,.]+)m", d.text).group(1))
               for d in self._latest_docs(it, "co-investment statement your value", ("coinvest_statement",)).values()]
        tot = sum(navs) + sum(cos)
        share = 100 * ans.value / tot if tot else None
        ans.value = share
        ans.shown.append(Shown(label="portfolio", value=tot, unit="$m", sourced=True))
        ans.shown.append(Shown(label="share", value=share, unit="%", sourced=True))
        ans.text = f"About {share:.2f}% of our portfolio value." if share is not None else "Not found."
        return ans

    def t_routes_managers(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = [r for r in self._exposure(it, ans, it.company) if r["value"] > 1e-9]
        names = set()
        for r in rows:
            if r["via"] == "coinvest":
                d = next(x for x in self.store.docs if x.doc_id == r["doc"])
                names.add(re.search(r"Sponsor: (.+?)\.", d.text).group(1))
            else:
                names.add(re.sub(r" (I|II|III|IV|V|VI|VII)$", "", r["fund"]))
                if r["via"] == "fof":
                    d = next(x for x in self.store.docs if x.doc_id == r["doc"])
                    names.add(re.sub(r" (I|II|III|IV|V|VI|VII)$", "", title(d.text)))
        ans.items = sorted(names)
        ans.item_sources = {n: True for n in names}
        ans.text = "Managers named in the documents: " + ", ".join(ans.items)
        return ans

    def t_routes_funds(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = [r for r in self._exposure(it, ans, it.company) if r["value"] > 1e-9 and r["via"] != "coinvest"]
        ans.items = sorted({r["fund"] for r in rows})
        ans.item_sources = {n: True for n in ans.items}
        ans.text = "Funds: " + ", ".join(ans.items)
        return ans

    def t_top(self, it):
        ans = Answer(foundation=self.key, question="")
        latest = self._latest_docs(it, "portfolio holdings fair value", ("fund_report",))
        agg = defaultdict(float)
        for d in latest.values():
            sh = share_in(d.text) or 0
            for m in re.finditer(r"^(?:\| (.+?) \|.*\| ([\d,.]+) \||- (.+) - USD ([\d.]+)m|holding;(.+);([\d.]+))$", d.text, re.M):
                g = [x for x in m.groups() if x]
                agg[g[0].strip()] += _f(g[-1]) * sh
        top = sorted(agg.items(), key=lambda kv: -kv[1])[: it.top_n or 5]
        ans.items = [re.sub(r" (Pty Ltd|Pte Ltd|Inc\.|Ltd|BV|SA|SL|GmbH|KK)$", "", k) for k, _ in top]
        ans.item_sources = {n: True for n in ans.items}
        ans.shown = [Shown(label=k, value=v, sourced=True) for k, v in top]
        ans.text = "\n".join(f"{i + 1}. {k}: {money(v)}" for i, (k, v) in enumerate(top))
        return ans

    def t_learnt(self, it):
        ans = Answer(foundation=self.key, question="")
        terms = self._terms(it.company)
        hits = [d for d in self.s.query(f"{it.company} written down", k=10, kinds=("letter",), before=it.as_of)
                if "written down" in d.text and mentions(d.text, terms)]
        if not hits:
            ans.text = "No letter mentions a write-down."
            return ans
        d = min(hits, key=lambda x: x.learnt_at)
        ans.date = d.learnt_at
        ans.item_sources = {"date": True}
        ans.text = f"A letter dated {d.learnt_at} reports the write-down ({d.doc_id})."
        return ans

    # ---------------------------------------------------------- performance from report headers and notices
    def _fund_docs(self, it):
        latest = self._latest_docs(it, f"{it.strategy or ''} vintage report {it.manager or ''} {it.fund or ''}", ("fund_report",))
        out = {}
        for k, d in latest.items():
            h = header(d.text)
            if it.strategy and h.get("strategy") != it.strategy:
                continue
            if it.vintage_from and not (it.vintage_from <= h.get("vintage", 0) <= it.vintage_to):
                continue
            if it.manager and not k.lower().startswith(it.manager.lower().split()[0]):
                continue
            if it.fund and normalise(k) != normalise(it.fund):
                continue
            if not (it.strategy or it.vintage_from or it.manager or it.fund) or "fund of funds" not in d.text.lower():
                out[k] = (d, h)
        return out

    def t_perf(self, it):
        ans = Answer(foundation=self.key, question="")
        fd = self._fund_docs(it)
        self._passages(ans, it.model_dump_json(), [d for d, _ in fd.values()])
        m = it.metric
        if m in ("net_irr", "net_tvpi", "adjusted_nav"):
            key = {"net_irr": "irr", "net_tvpi": "tvpi", "adjusted_nav": "lp_nav"}[m]
            per = {k: h.get(key) for k, (d, h) in fd.items()}
            fmt = {"irr": pct, "tvpi": ratio, "lp_nav": money}[key]
            if it.group_by == "fund":
                ans.table = per
                ans.text = "Manager-reported figures:\n" + "\n".join(f"- {k}: {fmt(v)}" for k, v in per.items())
                ans.shown = [Shown(label=k, value=v, sourced=True) for k, v in per.items()]
                ans.allowed_numbers = [round(v * 100, 1) for v in per.values() if v]
                return ans
            vals = [v for v in per.values() if v is not None]
            if not vals:
                return refuse(self.key, "I found no reports for these funds.")
            val = sum(vals) if key == "lp_nav" else sum(vals) / len(vals)
            ans.value = val
            ans.shown = [Shown(label=m, value=val, sourced=True)]
            ans.allowed_numbers = [round(val * 100, 1)]
            ans.text = f"From the reports ({len(vals)} funds): {fmt(val)}."
            return ans
        if m in ("distributions", "calls"):
            names = set(fd)
            kind = "dist" if m == "distributions" else "call"
            tot, n = 0.0, 0
            for d in self.store.docs:
                if d.source != "notices" or d.kind != kind:
                    continue
                subj = re.search(r"Subject: (?:CORRECTED )?(?:Capital call notice, |Distribution notice, )(.+)", d.text)
                if not subj or subj.group(1).strip() not in names:
                    continue
                dd = re.search(r"(?:Due date|Distribution date): (\S+)", d.text).group(1)
                if it.period_start and not (str(it.period_start) <= dd <= str(it.period_end)):
                    continue
                am = re.search(r"(?:Amount due|Amount): USD ([\d,]+\.\d{2})\n", d.text)
                if am:
                    tot += _f(am.group(1)) / 1e6
                    n += 1
            ans.value = tot
            ans.shown = [Shown(label=m, value=tot, sourced=True)]
            ans.text = f"Sum of {n} notices: {money(tot)}."
            ans.allowed_numbers = [n]
            return ans
        return refuse(self.key, f"The documents don't state {m.replace('_', ' ')}.")

    def t_behind_plan(self, it):
        return refuse(self.key, "The documents don't state our plan for each fund.")

    # ---------------------------------------------------------- letters and links
    def t_issues(self, it):
        ans = Answer(foundation=self.key, question="")
        hits = self.s.letters(it.manager, it.as_of, ISSUE, it.issue_kinds)
        ans.items = sorted({h["doc_id"] for h in hits})
        ans.item_sources = {h["doc_id"]: True for h in hits}
        ans.text = "\n".join(f"- {h['learnt']}: \"{h['quote']}\" ({h['doc_id']})" for h in hits) or "No issues found."
        from ..answer import numbers_in
        ans.allowed_numbers = [x for h in hits for x in numbers_in(h["quote"])]
        return ans

    def t_coinvests(self, it):
        ans = Answer(foundation=self.key, question="")
        names = set()
        for d in self.s.query(f"co-investment statement sponsor {it.manager}", k=40, kinds=("coinvest_statement",)):
            if re.search(rf"Sponsor: {re.escape(it.manager or '')}", d.text, re.I):
                names.add(re.sub(r" (Pty Ltd|Pte Ltd|Inc\.|Ltd|BV|SA|SL|GmbH|KK)$", "", re.search(r"Co-investment statement: (.+)", d.text).group(1).split(" (")[0]))
        ans.items = sorted(names)
        ans.item_sources = {n: True for n in names}
        ans.text = "Co-investments: " + ", ".join(ans.items)
        return ans

    def t_fees(self, it):
        ans = Answer(foundation=self.key, question="")
        docs = [d for d in self.s.query(f"fee schedule {it.manager or ''}", k=10, kinds=("coinvest_fees",))
                if not it.manager or re.search(rf"Sponsor: {re.escape(it.manager)}", d.text, re.I)]
        if not docs:
            return refuse(self.key, "I found no fee documents I can see.")
        for d in docs:
            n = re.sub(r" (Pty Ltd|Pte Ltd|Inc\.|Ltd|BV|SA|SL|GmbH|KK)$", "", re.search(r"Co-investment fee schedule: (.+)", d.text).group(1).split(" (")[0])
            ans.table[n] = float(re.search(r"Management fee: ([\d.]+)%", d.text).group(1))
            ans.allowed_numbers.append(float(re.search(r"Carried interest: ([\d.]+)%", d.text).group(1)))
        ans.text = "\n".join(f"- {k}: {v:.2f}%" for k, v in ans.table.items())
        return ans

    def t_planned(self, it):
        return refuse(self.key, "I found no document with a planned commitment.")

    def t_people_where(self, it):
        hits = [d for d in self.s.query(f"{it.person} joined", k=5, kinds=("letter",)) if (it.person or "") in d.text]
        ans = Answer(foundation=self.key, question="")
        ans.text = "The letters say she left; none says where she went." if hits else "Nothing found."
        return ans

    def t_people_moves(self, it):
        ans = Answer(foundation=self.key, question="")
        ans.text = "The letters mention departures but not where people went."
        return ans

    def t_history(self, it):
        ans = self.t_issues(it.model_copy(update=dict(issue_kinds=[])))
        fd = self._fund_docs(it)
        ans.composite = dict(commitment=None, funds=sorted(fd), issues=ans.items)
        ans.text = "Funds with reports: " + ", ".join(sorted(fd)) + ". Commitments aren't stated in the documents.\n" + ans.text
        ans.items = []
        return ans

    def t_news_number(self, it):
        ans = Answer(foundation=self.key, question="")
        d = self.s.query(f"{it.company} debt", k=1, kinds=("news",))
        m = re.search(r"\$(\d+)m", d[0].text) if d else None
        if not m:
            return refuse(self.key, "Nothing found.")
        ans.value = float(m.group(1))
        ans.shown = [Shown(label="debt (news)", value=ans.value, sourced=True, sources=[d[0].doc_id])]
        ans.text = f"The news item says about ${m.group(1)}m of debt ({d[0].doc_id}); our share isn't in the documents."
        return ans

    def t_unknown_metric(self, it):
        return refuse(self.key, f"The documents don't define {it.metric}.")

    def t_advice(self, it):
        return refuse(self.key, "I can't make an investment decision.")
