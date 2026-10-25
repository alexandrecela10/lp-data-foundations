"""Build the 'How the foundations work' page: one HTML file, every number from the real pipeline and results.

The page is a template (explainer_template.html) plus one JSON blob. Nothing on the page is typed by hand
except the teaching text: routes, values, spellings, dates, scores and timings all come from here.
Run: python -m answerdesk.cli explainer  ->  static/foundations.html
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import access, graph, pipeline
from .answer import DISCLAIMER
from .foundations import ARMS, LABELS
from .semantic.layer import MetricRequest, SemanticLayer, registry
from .world import TODAY

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
TEMPLATE = Path(__file__).with_name("explainer_template.html")
OUT = ROOT / "static" / "foundations.html"
ARM_ORDER = ["A", "B", "C", "C+ids", "D"]
QUESTION = "How exposed are we to Calder Packaging?"
BEFORE_LETTER = dt.date(2026, 9, 9)


def _sig(route: dict, label: dict) -> str:
    """Same route signature the scorer uses: direct:<fund>, fof:<underlying fund>, coinvest:<id>."""
    path = route["path"]
    if route["kind"] == "coinvest":
        return f"coinvest:{path[1]}"
    return f"fof:{label[path[2]]}" if route["kind"] == "fof" else f"direct:{label[path[1]]}"


def _load(name: str):
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else None


def _scores(res: dict | None) -> dict | None:
    if not res or "summary" not in res:
        return None
    out = {}
    for a in ARM_ORDER:
        s = res["summary"][a]
        rows = [r for r in res["rows"] if r["arm"] == a]
        fails = {}
        for r in rows:
            if r["correct"]:
                continue
            d = r["detail"]
            k = ("refused: number check failed" if "number check" in d else "refused" if d.startswith("refused") else
                 "wrong number" if d.startswith("value") or "rows within" in d else "missed routes or items")
            fails[k] = fails.get(k, 0) + 1
        out[a] = dict(correct=s["correct"], r1=s["request_1"], r2=s["request_2"], r3=s["request_3"],
                      wrong_sourced=s["wrong_but_sourced"], refusals=f"{s['correct_refusals']}/{s['refusal_traps']}",
                      expected_min=round(s["expected_time_per_question_s"] / 60, 1),
                      median_send_s=round(s["median_time_to_send_s"] or 0),
                      cost=round(s["cost_per_answer_usd"], 4),
                      rerun=res.get("same_answer_on_rerun", {}).get(a), fails=fails,
                      calder=next((dict(correct=r["correct"], detail=r["detail"], answer=r["answer"][:500])
                                   for r in rows if r["qid"] == "R1-01"), None))
    meta = res["meta"]
    return dict(mode=meta["mode"], run_at=meta["run_at"], valid=meta.get("valid", True),
                billed=meta.get("all_passes"), arms=out)


def build_data(store=None) -> dict:
    S = store or pipeline.build(seed=42)
    con = access.role_db(S, "analyst")
    g = graph.build(con, TODAY)

    # the ideal answer: D's routes, with every hop
    ideal, _ = ARMS["D"](S, "analyst").ask(QUESTION)
    nodes, edges, routes = {}, {}, []
    for i, r in enumerate(ideal.routes):
        for h in r["hops"]:
            for n in (h["src"], h["dst"]):
                if n not in nodes:
                    lab = g.nodes[n]["label"] if n in g else n.replace("name:", "")
                    kind = g.nodes[n].get("kind", "") if n in g else ""
                    nodes[n] = dict(id=n, label=lab, kind="name" if n.startswith("name:") else kind)
            edges.setdefault(f"{h['src']}>{h['dst']}", dict(src=h["src"], dst=h["dst"], label=h["label"]))
        routes.append(dict(id=_sig(r, {k: v["label"] for k, v in nodes.items()}), kind=r["kind"], value=r["value"], factor=r.get("factor") or 1.0,
                           as_of=str(r.get("as_of")), path=r["path"], sources=sorted(set(r["sources"])),
                           hops=[h["label"] for h in r["hops"]]))

    # what each setup actually returned for the same question (offline run)
    setups = {}
    for a in ARM_ORDER:
        ans, _ = ARMS[a](S, "analyst").ask(QUESTION)
        setups[a] = dict(label=LABELS[a], value=ans.value, routes=ans.route_sigs, refused=ans.refused,
                         text=ans.text.replace(DISCLAIMER, "").strip()[:900], sql=(ans.sql or "")[:2600],
                         lines=[dict(label=x.label, value=x.value, sourced=x.sourced) for x in ans.shown],
                         steps=[s.name for s in ans.steps])

    spellings = [dict(name=n, method=m, fund=f) for n, m, f in con.execute(
        "SELECT DISTINCT h.name_reported, h.match_method, f.name FROM gold.holdings h JOIN gold.funds f USING (fund_id) "
        "WHERE h.company_id = 'C0001' ORDER BY 2 DESC").fetchall()]
    spellings += [dict(name=n, method="holding company", fund="Co-investment") for (n,) in con.execute(
        "SELECT DISTINCT name_reported FROM gold.coinvest_values WHERE company_id = 'C0001'").fetchall()]
    letter = con.execute("SELECT kind, factor, effective, learnt, quote, doc_id FROM gold.events "
                         "WHERE company_id = 'C0001' AND kind = 'write_down' ORDER BY learnt LIMIT 1").fetchone()

    sl = SemanticLayer(S, "analyst", "resolved")
    def lt(d, v=None):
        return sl.run(MetricRequest(metric="lookthrough_exposure", as_of=d, company="Calder Packaging",
                                    **({"version": v} if v else {}))).numbers[0].value
    m = registry()["metrics"]["lookthrough_exposure"]

    brennick = graph.former_partner_moves(g, "M02")

    off = _load("offline-seed42.json")
    live = _load("live-claude-sonnet-5-5.json")
    people_q = {}
    if off:
        for r in off["rows"]:
            if r["qid"] in ("R3-11", "R3-12"):
                people_q.setdefault(r["qid"], dict(question=r["question"], arms={}))["arms"][r["arm"]] = r["correct"]

    return dict(
        question=QUESTION, today=str(TODAY), disclaimer=DISCLAIMER,
        ideal=dict(value=ideal.value, routes=routes, nodes=list(nodes.values()), edges=list(edges.values()),
                   definitions=ideal.definitions),
        setups=setups, spellings=spellings,
        letter=dict(kind=letter[0], factor=letter[1], effective=str(letter[2]), learnt=str(letter[3]),
                    quote=letter[4], doc=letter[5]) if letter else None,
        point_in_time=dict(before=str(BEFORE_LETTER), before_value=lt(BEFORE_LETTER), today_value=lt(TODAY)),
        definitions=dict(owner=m["owner"], v2_plain=m["versions"][2]["plain"], v1_plain=m["versions"][1]["plain"],
                         v2_before=lt(BEFORE_LETTER), v1_before=lt(BEFORE_LETTER, 1),
                         v2_today=lt(TODAY), v1_today=lt(TODAY, 1)),
        people=dict(manager="Brennick Capital Partners",
                    moves=[dict(person=x["person"], left=str(x["left"]), joined=x["joined"], start=str(x["start"]))
                           for x in brennick],
                    questions=people_q),
        code=dict(joins=graph.SQL_JOINS, pgq=graph.PGQ, cypher=graph.CYPHER, semantic=graph.SEMANTIC),
        scale=_load("scale.json") or [],
        identity=(off or {}).get("identity"),
        scores=dict(offline=_scores(off), live=_scores(live) if live and "summary" in live else None),
        built_at=dt.datetime.now().isoformat(timespec="minutes"),
    )


def render(data: dict | None = None, out: Path = OUT) -> Path:
    data = data or build_data()
    blob = json.dumps(data, default=str).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", blob)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out
