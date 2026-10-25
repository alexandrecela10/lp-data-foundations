"""Portfolio Answer Desk: a guided demo, written to you.

Runs offline with no key: the offline reader stands in for the AI, and every number is computed by
code. Run: streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from answerdesk import access, governance, graph, interfaces, llm, pipeline  # noqa: E402
from answerdesk.answer import DISCLAIMER  # noqa: E402
from answerdesk.foundations import ARMS, LABELS  # noqa: E402
from answerdesk.semantic.layer import MetricRequest, SemanticLayer, registry  # noqa: E402
from answerdesk.world import PACK_DATE, TODAY  # noqa: E402

st.set_page_config(page_title="Portfolio Answer Desk", layout="wide")
ss = st.session_state
ss.setdefault("question", "How exposed are we to Calder Packaging?")
ss.setdefault("hop", 0)
ss.setdefault("sent", [])
ss.setdefault("prev_intent", None)
ss.setdefault("fund_pick", None)
RESULTS = ROOT / "evals" / "results"
ARM_ORDER = ["A", "B", "C", "C+ids", "D"]


def esc(t) -> str:
    """Streamlit reads $...$ as maths. Money must show as text."""
    return str(t).replace("$", "\\$")


def md(t, **kw):
    st.markdown(esc(t), **kw)


@st.cache_resource(show_spinner="Building the synthetic world: six sources, bronze, silver, gold...")
def store():
    return pipeline.build(seed=42)


@st.cache_data
def results(name: str):
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else None


def footer():
    st.caption(DISCLAIMER + " All names are invented.")


S = store()

# ------------------------------------------------------------------ header and sidebar
st.title("Portfolio Answer Desk")
md("**You get a correct, sourced answer to a senior leader's portfolio question in minutes: "
   "every route, every definition and the date of every number, ready to send.** It runs on one shared data "
   "foundation (tables, a semantic layer of governed metrics, and a graph for routes and people) with a different "
   "front end per request. The Foundation test tab shows how we know.")
st.caption(DISCLAIMER)

with st.sidebar:
    st.header("You are")
    role = st.radio("Role (a demo switch, not a login)", list(access.ROLES), format_func=lambda r: access.ROLES[r]["label"],
                    key="role")
    st.caption(f"Today is Monday {TODAY:%d %B %Y}, 08:12. The committee pack is as of {PACK_DATE:%d %B %Y}.")
    if llm.available():
        st.warning(f"Live mode: {llm.NOTICE}")
    else:
        st.info("Offline: no AI calls. A fixed reader stands in for the AI; code computes every number.")
    st.header("Your morning")
    st.markdown("1. **Portfolio chat**: answer the CIO\n2. **Committee pack**: export Thursday's pack\n"
                "3. **Manager briefing**: brief the head of PE\n4. **Foundation test**: see why it works")
    footer()

tabs = st.tabs(["Portfolio chat", "Committee pack", "Manager briefing", "SQL notebook", "Foundation test",
                "How it works", "Under the hood"])


# ------------------------------------------------------------------ helpers for answers
def route_table(ans):
    rows = []
    for i, r in enumerate(ans.routes, 1):
        age = (ans.as_of - r["as_of"]).days if r.get("as_of") else None
        rows.append({"#": i, "route": r["route"], "value ($m)": round(r["value"], 3),
                     "report date": str(r.get("as_of")), "age (days)": age,
                     "freshness": "stale" if age and age > 90 else "ok",
                     "write-down applied": "yes" if r.get("factor", 1.0) != 1.0 else "no"})
    return pd.DataFrame(rows)


def dot_routes(ans, upto: int) -> str:
    """Graphviz picture of the routes; hops up to `upto` are drawn bold and numbered."""
    lines = ['digraph G { rankdir=LR; node [shape=box, style="rounded", fontsize=10]; edge [fontsize=9];']
    seen, step = set(), 0
    for r in ans.routes:
        for h in r.get("hops") or []:
            step += 1
            key = (h["src"], h["dst"])
            on = step <= upto
            if key in seen:
                continue
            seen.add(key)
            attrs = f'label="{step}. {h["label"]}", penwidth={3 if on else 1}, color="{"#1f6feb" if on else "#999999"}"'
            lines.append(f'"{h["src"]}" -> "{h["dst"]}" [{attrs}];')
    g = graph.build(access.role_db(S, role), ans.as_of)
    for n in {x for k in seen for x in k}:
        lab = g.nodes[n]["label"] if n in g else n
        kind = g.nodes[n].get("kind", "") if n in g else ""
        lines.append(f'"{n}" [label="{lab}\\n({kind})"];')
    lines.append("}")
    return "\n".join(lines)


def total_hops(ans) -> int:
    return sum(len(r.get("hops") or []) for r in ans.routes)


# ------------------------------------------------------------------ 1. Portfolio chat
with tabs[0]:
    md("**Portfolio chat: ask in plain words, get a number you can send, with its routes, definition and dates.**")
    md("You're Sara. At 08:10 the news says Calder Packaging is restructuring its debt. At 08:12 the CIO asks: "
       "*How exposed are we to Calder Packaging, and to European packaging? Through which managers? Did we know?*")
    samples = ["How exposed are we to Calder Packaging?", "What is our exposure to European packaging companies?",
               "Through which managers are we exposed to Calder Packaging?",
               "Did we know Calder Packaging was in trouble? When did we first learn of a write-down?",
               "How exposed were we to Calder Packaging as of 5 September 2026?",
               "What fees do we pay on the Calderwick Holdings co-investment?",
               "News says Calder Packaging has $400m of debt. What is our share of that debt?"]
    cols = st.columns(4)
    for i, s in enumerate(samples):
        if cols[i % 4].button(s, key=f"sample{i}"):
            ss.question = s
            ss.hop = 0
    q = st.text_input("Your question", key="question")
    ans, intent = interfaces.chat(S, q, role, "D", ss.prev_intent if q.lower().startswith("and") else None)
    governance.audit(ans)
    if ans.refused:
        st.error(esc(f"Not answered. {ans.reason}"))
        if ans.who_can:
            md(f"**Who can answer:** {ans.who_can}.")
        if st.button("Answer what I can see instead", key="see_instead"):
            ss.question = "How exposed are we to Calder Packaging?"
            st.rerun()
    elif not ans.shown and not ans.items and not ans.date:
        st.warning(esc(ans.text.replace(DISCLAIMER, "")))
    else:
        if ans.routes:
            mixed = len({r["as_of"] for r in ans.routes}) > 1
            md(f"**For the CIO:** about **\\${ans.value:,.2f}m** through {len(ans.routes)} routes"
               + (", after the write-down we learnt of on 10 September" if any(r.get("factor", 1) != 1 for r in ans.routes) else "")
               + (". Values as of mixed report dates." if mixed else "."))
            st.dataframe(route_table(ans), hide_index=True, width="stretch")
            if ans.pending:
                st.warning(esc(f"{len(ans.pending)} letter item(s) not counted, waiting for review: \"{ans.pending[0]['quote']}\""))
            with st.expander("Show routes on the graph"):
                n = total_hops(ans)
                c1, c2 = st.columns([1, 4])
                if c1.button("Next hop", key="nexthop"):
                    ss.hop = min(ss.hop + 1, n)
                if c1.button("Show all", key="allhops"):
                    ss.hop = n
                if c1.button("Reset", key="resethops"):
                    ss.hop = 0
                c1.caption(f"Hop {ss.hop} of {n}")
                c2.graphviz_chart(dot_routes(ans, ss.hop))
                st.caption("Each hop is numbered; bold blue means the walk has reached it. The route table above is the main view.")
        md(ans.text.replace(DISCLAIMER, ""))
        if ans.definitions:
            st.caption(esc("Definitions used: " + ", ".join(ans.definitions)))
    ss.prev_intent = intent
    st.subheader("Decide: send it?")
    note = st.text_area("Add a note that travels with the answer", key="note", placeholder="For example: July concern not counted")
    st.code(interfaces.copy_text(ans, note), language=None)
    if st.button("Send to the CIO", type="primary", key="send"):
        ss.sent.append(dict(question=q, at=dt.datetime.now().isoformat(timespec="seconds")))
        st.success("Logged as sent. The text above is what goes out.")

# ------------------------------------------------------------------ 2. Committee pack
with tabs[1]:
    md("**Committee pack: the same numbers as last quarter's pack, on the same definitions, as of a set date.**")
    md("You're preparing Thursday's investment committee pack: our 2019 to 2021 buyout funds against plan, after fees, "
       "and how much of our unfunded commitment will be called in the next 12 months.")
    c1, c2 = st.columns(2)
    as_of = c1.selectbox("As of", [PACK_DATE, dt.date(2026, 6, 30)], format_func=lambda d: d.strftime("%d %B %Y"))
    use_old = c2.toggle("Use last quarter's unfunded definition (v1)", value=False)
    dash = interfaces.dashboard(S, role, as_of, "pack_2026_q2" if use_old else None)
    for c in dash["changes"]:
        st.info(esc(f"Changed since the 30 June pack: {c['metric']} v{c['version']} from {c['from_']:%d %b %Y}. {c['plain']}"))
    v1, v2, v3 = st.tabs(["Exposure", "Funds against plan", "Cash next 12 months"])
    perf = dash["performance"]
    with v1:
        st.dataframe(dash["exposure"], hide_index=True, width="stretch")
        st.bar_chart(dash["sector"].head(10), x="sector", y="exposure_usd_m", color="region")
    with v2:
        sel = perf[(perf.strategy == "buyout") & perf.vintage.between(2019, 2021)].copy()
        st.dataframe(sel[["fund", "vintage", "net_irr", "net_tvpi", "net_dpi", "vs_plan"]].round(3), hide_index=True,
                     width="stretch")
        st.altair_chart(alt.Chart(sel).mark_bar().encode(x=alt.X("vs_plan:Q", title="TVPI against plan (x)"),
                                                         y=alt.Y("fund:N", sort="-x", title=None),
                                                         color=alt.condition("datum.vs_plan < 0", alt.value("#c0392b"),
                                                                             alt.value("#2e7d32"))), width="stretch")
        st.caption(esc(dash["definitions"]["tvpi_vs_plan"]))
    with v3:
        st.dataframe(perf[["fund", "unfunded", "calls_next_12m"]].round(3), hide_index=True, width="stretch")
        md(f"**Calls expected in the next 12 months:** \\${perf.calls_next_12m.sum():,.2f}m. {dash['definitions']['calls_next_12m']}")
    with st.expander("Two teams, two definitions, two answers (why one governed definition matters)"):
        sl = SemanticLayer(S, role, "resolved")
        gaps = {}
        for d in (dt.date(2026, 9, 9), TODAY):
            a = sl.run(MetricRequest(metric="lookthrough_exposure", as_of=d, company="Calder Packaging")).numbers[0].value
            b = sl.run(MetricRequest(metric="lookthrough_exposure", version=1, as_of=d, company="Calder Packaging")).numbers[0].value
            gaps[d] = (a, b)
            md(f"- As of {d:%d %b %Y}: Risk team (value, v2) **\\${a:,.2f}m**; Investment team (commitment, v1) **\\${b:,.2f}m**.")
        (a9, b9), (a26, b26) = gaps[dt.date(2026, 9, 9)], gaps[TODAY]
        md(f"Example: on 9 September the two teams were \\${abs(a9 - b9):,.2f}m apart. After the write-down letter on "
           f"10 September the value-based number fell to \\${a26:,.2f}m and the commitment-based one stayed at "
           f"\\${b26:,.2f}m, because commitment ignores what the company is worth. Without one governed definition, "
           "the CIO gets whichever number the analyst happened to use.")
    st.subheader("Decide: export the pack")
    st.download_button("Export pack as of " + as_of.strftime("%d %b %Y"), interfaces.export_pack(dash),
                       file_name=f"pack-{as_of}.csv", type="primary")

# ------------------------------------------------------------------ 3. Manager briefing
with tabs[2]:
    md("**Manager briefing: a manager's history with us in one note, numbers from governed metrics, issues quoted from their letters.**")
    md("The head of private equity is deciding whether to commit to Brennick Capital Partners VI. You write the briefing.")
    note_md = interfaces.briefing(S, "Brennick", role)
    st.markdown(esc(note_md))
    st.subheader("Decide: send the briefing")
    st.download_button("Download briefing (Markdown)", note_md, file_name="brennick-briefing.md", type="primary")

# ------------------------------------------------------------------ 4. SQL notebook
with tabs[3]:
    md("**SQL notebook: for the data team, read-only SQL on the same governed tables, limited to your role.**")
    sql = st.text_area("Query", "SELECT fund_id, as_of, name_reported, company_id, match_method, value\nFROM gold.holdings\n"
                                "WHERE company_id = 'C0001' ORDER BY as_of DESC LIMIT 10", height=120)
    if st.button("Run query", key="runsql"):
        try:
            st.dataframe(interfaces.notebook(S, sql, role), hide_index=True, width="stretch")
        except Exception as e:
            st.error(esc(str(e)[:300]))
    st.caption("Try `SELECT mgmt_fee_pct FROM gold.positions` as Sara: the column doesn't exist in her copy of the data.")

# ------------------------------------------------------------------ 5. Foundation test
with tabs[4]:
    off = results("offline-seed42.json")
    held = results("offline-heldout-seed7-noisy.json")
    md("**Foundation test: which data setup gets Sara a correct, sourced answer she'd send, fastest.**")
    if off:
        sm = off["summary"]
        md(f"**Decision: use C+ids (semantic layer plus an identity table) for numbers and routes, and add the graph only for "
           f"links between people and managers.** Offline, D answered {sm['D']['correct']}/60 and C+ids {sm['C+ids']['correct']}/60; "
           f"on the CIO's request they tie at {sm['D']['request_1']}/20 each, so by the rule set before the run the graph "
           f"doesn't earn its place for routes. It wins on 4 manager-history questions: 2 need people links, 2 need letter search.")
        st.warning("Offline results test mechanisms, not Claude. The AI is replaced by fixed readers; the live run with "
                   "claude-sonnet-5-5 is not yet run (one command in the README).")
        df = pd.DataFrame([dict(setup=f"{a}: {LABELS[a]}", request=f"Request {r}", correct=sm[a][f"request_{r}"])
                           for a in ARM_ORDER for r in (1, 2, 3)])
        st.altair_chart(alt.Chart(df).mark_bar().encode(
            x=alt.X("correct:Q", title="Correct answers (of 20 per request)", scale=alt.Scale(domain=[0, 60])),
            y=alt.Y("setup:N", sort=ARM_ORDER, title=None), color=alt.Color("request:N", title=None),
            tooltip=["setup", "request", "correct"]), width="stretch")
        tbl = pd.DataFrame([{
            "setup": a, "correct (of 60)": sm[a]["correct"],
            "wrong numbers shown as sourced": sm[a]["wrong_but_sourced"],
            "median time to a sendable answer (s)": round(sm[a]["median_time_to_send_s"] or 0),
            "expected time per question (min)": round(sm[a]["expected_time_per_question_s"] / 60, 1),
            "refusal traps refused": f"{sm[a]['correct_refusals']}/{sm[a]['refusal_traps']}",
            "est. cost per answer ($)": round(sm[a]["cost_per_answer_usd"], 4)} for a in ARM_ORDER])
        st.dataframe(tbl, hide_index=True, width="stretch")
        st.caption("Time = answer time (compute plus an assumed 3 s per AI call) plus Sara's checking time (assumed: 20 s to "
                   "read, 5 s per number with source and definition, 30 s with a source only, 120 s by hand). A wrong "
                   "answer counts as 2 hours of manual work in the expected time.")
        with st.expander("Chatbot against the other ways in: where each wins"):
            md("- **Documents + search (A)** wins on letters: it found every Brennick issue with a citation. It loses on numbers: "
               "it multiplied a fund of funds' look-through line by our share of the fund of funds, so it showed wrong numbers *with* sources (the most dangerous kind).\n"
               "- **AI-written SQL (B)** finds direct routes and simple sums. It misses what the schema doesn't say: when a report "
               "arrived, write-downs in letters, recallable distributions, the governed call forecast.\n"
               "- **Semantic layer (C)** gets every committee-pack number right, because each metric is defined once. It misses "
               "routes hidden behind other spellings.\n"
               "- **C plus an identity table** closes the spelling gap: 20/20 on the CIO's request.\n"
               "- **D** adds links between people and managers (where a departed partner went) and letter search.")
        with st.expander("Is the result fragile? Sensitivity of the ranking to the checking-time model"):
            st.dataframe(pd.DataFrame([dict(variant=v["variant"], ranking=" < ".join(v["ranking"]),
                                            **{a: round(v["median_s"][a] or 0) for a in ARM_ORDER}) for v in off["sensitivity"]]),
                         hide_index=True, width="stretch")
            st.caption("Median seconds to a sendable answer, correct answers only. Fastest first.")
        with st.expander("Held-out world (seed 7, spellings the pipeline was never tuned on)"):
            if held:
                st.dataframe(pd.DataFrame([dict(setup=a, correct=held["summary"][a]["correct"],
                                                wrong_but_sourced=held["summary"][a]["wrong_but_sourced"]) for a in ARM_ORDER]),
                             hide_index=True)
                idq = held["identity"]
                md(f"Company names matched: identity table {idq['identity table (C+ids, D)']['right']} right, "
                   f"{idq['identity table (C+ids, D)']['wrong']} wrong, {idq['identity table (C+ids, D)']['missed']} waiting for a person; "
                   f"exact names only {idq['exact name only (C, B)']['right']} right, {idq['exact name only (C, B)']['wrong']} wrong, "
                   f"{idq['exact name only (C, B)']['missed']} missed. No test question touched the unmatched names: a gap in the test set.")
        with st.expander("Every question, every setup"):
            rows = pd.DataFrame(off["rows"])[["arm", "qid", "question", "correct", "detail", "traps"]]
            st.dataframe(rows, hide_index=True, width="stretch")
    sc = results("scale.json")
    st.subheader("At 10x and 100x the data")
    if sc:
        long = []
        for r in sc:
            for k, lab in [("route_sql_ms", "Routes: recursive SQL (semantic layer)"),
                           ("route_graph_total_ms", "Routes: build graph + walk (NetworkX)"),
                           ("route_graph_walk_ms", "Routes: walk only, graph already built"),
                           ("route_pgq_ms", "Routes: DuckPGQ (SQL/PGQ)"),
                           ("portfolio_sum_sql_ms", "Sector sum: semantic layer SQL"),
                           ("portfolio_sum_graph_only_ms", "Sector sum: graph only (optional E)"),
                           ("perf_metric_ms", "Pooled TVPI: governed metric, one fund at a time")]:
                if r.get(k) is not None:
                    long.append(dict(scale=f"{r['scale']}x", ms=r[k], method=lab, funds=r["funds"]))
        ch = alt.Chart(pd.DataFrame(long)).mark_line(point=True).encode(
            x=alt.X("scale:N", sort=["1x", "10x", "100x"], title="Data size"), y=alt.Y("ms:Q", scale=alt.Scale(type="log"),
                                                                                    title="Milliseconds (log)"),
            color=alt.Color("method:N", title=None), tooltip=["method", "scale", "ms", "funds"])
        st.altair_chart(ch, width="stretch")
        b = sc[-1]
        md(f"**What changes at 100x** ({b['funds']:,} funds, {b['documents']:,} documents): the full rebuild takes "
           f"{b['build_s']:.0f} s, most of it matching company names ({b['pipeline_s']['silver']:.0f} s). One company's routes take "
           f"{b['route_sql_ms']:.0f} ms in recursive SQL, {b['graph_build_ms']:.0f} + {b['route_graph_walk_ms']:.0f} ms to build the "
           f"graph and walk it, and {b['route_pgq_ms']:.0f} ms for the DuckPGQ query once its graph is set up. Routes stay under a "
           f"second every way. What breaks first is a governed metric computed one fund at a time: pooled TVPI takes "
           f"{b['perf_metric_ms'] / 1000:.1f} s. Peak memory {b['max_rss_mb']:,.0f} MB, "
           "so 100x runs locally and the demo reads the committed results.")
    else:
        st.caption("Scale results not found (evals/results/scale.json).")
    st.subheader("Decide: which setup would you fund?")
    pick = st.radio("Your pick", ["C+ids for numbers and routes, graph for people links (recommended)",
                                  "D everywhere", "C only", "Documents + chatbot only"], key="fund_pick_radio")
    if st.button("Record my pick", key="pick"):
        ss.fund_pick = pick
        st.success(esc(f"Recorded: {pick}"))

# ------------------------------------------------------------------ 6. How it works
with tabs[5]:
    md("**How it works: the same question three ways, a graph you can step through, and one metric defined once.**")
    st.subheader("1. Walk the graph to Calder Packaging")
    a_cal, _ = interfaces.chat(S, "How exposed are we to Calder Packaging?", role, "D")
    n = total_hops(a_cal)
    ss.setdefault("edu_hop", 0)
    c1, c2 = st.columns([1, 4])
    if c1.button("Next hop", key="edu_next"):
        ss.edu_hop = min(ss.edu_hop + 1, n)
    if c1.button("Start again", key="edu_reset"):
        ss.edu_hop = 0
    c1.caption(f"Hop {ss.edu_hop} of {n}")
    c2.graphviz_chart(dot_routes(a_cal, ss.edu_hop))
    _sh = access.role_db(S, role).execute("SELECT lp_share FROM gold.reports WHERE fund_id = 'FOF01' ORDER BY as_of DESC LIMIT 1").fetchone()[0]
    _st = access.role_db(S, role).execute("SELECT share FROM gold.fof_stakes WHERE fund_id = 'F0009' ORDER BY as_of DESC LIMIT 1").fetchone()[0]
    md("A **graph** stores things (our pension plan, funds, companies, people) and the links between them. A question like "
       f"\"every route to Calder\" becomes a walk along links. Example: our plan holds {_sh * 100:.1f}% of Selbrook Fund of Funds III, "
       f"which holds {_st * 100:.0f}% of Ostrova Capital Partners IV, which reports \"Calder Pack.\". The identity link says Calder Pack. is "
       "Calder Packaging Ltd. Without that link, the walk stops at a name nobody recognises and the route is lost.")
    st.subheader("2. The same question, three ways")
    k1, k2, k3 = st.columns(3)
    k1.markdown("**SQL with joins**")
    k1.code(graph.SQL_JOINS, language="sql")
    k2.markdown("**Graph query (SQL/PGQ, and Cypher)**")
    k2.code(graph.PGQ + "\n\n" + graph.CYPHER, language="sql")
    k3.markdown("**Semantic-layer request**")
    k3.code(graph.SEMANTIC, language="yaml")
    md(f"All three return the same 5 routes and **\\${a_cal.value:,.2f}m**. The difference is who writes and maintains the "
       "logic: in SQL, every new route shape needs another block; in a graph, the walk handles any depth; in the semantic "
       "layer, the logic lives once inside the governed metric, and the person asking only picks it.")
    st.subheader("3. One metric, defined once")
    m = registry()["metrics"]["lookthrough_exposure"]
    md(f"**Look-through exposure, v2, owner {m['owner']}.** {m['versions'][2]['plain']}")
    dashv = interfaces.dashboard(S, role, TODAY)["exposure"]
    cal = SemanticLayer(S, role, "resolved").run(MetricRequest(metric="lookthrough_exposure", as_of=TODAY,
                                                               company="Calder Packaging")).numbers[0].value
    md(f"- **Chat:** \\${a_cal.value:,.2f}m\n- **Dashboard (same metric, same date):** \\${cal:,.2f}m\n"
       f"- **Notebook (`metric: lookthrough_exposure`):** \\${cal:,.2f}m")
    md("Same number everywhere, because all three ask the semantic layer. Counterfactual: if the dashboard team counted "
       "commitment instead of value (the Investment team's old v1), the dashboard would show a different number from "
       "the chat on the same morning. See the Committee pack tab, \"Two teams, two definitions\".")

# ------------------------------------------------------------------ 7. Under the hood
with tabs[6]:
    md("**Under the hood: how one answer was made, what was checked, and the choices behind it.**")
    st.graphviz_chart("""digraph { rankdir=LR; node [shape=box, style=rounded, fontsize=10];
      src [label="6 sources\\n(holdings, notices, reports,\\nletters, reference, news)"]; b [label="bronze\\n(as received)"];
      s [label="silver\\n(fixed fields, contracts,\\nidentity matching)"]; g [label="gold\\n(typed tables, lineage)"];
      sem [label="semantic layer\\n(governed metrics)"]; gr [label="graph\\n(routes, people)"]; ai [label="AI picks\\n(or offline reader)"];
      ui [label="chat / pack / briefing / notebook"];
      src -> b -> s -> g; g -> sem; g -> gr; ai -> sem; ai -> gr; sem -> ui; gr -> ui; }""")
    md("Sources land as received, are read into checked fields, then into typed tables; the AI only picks a governed "
       "metric, and code computes every number.")
    st.subheader("Trace of one answer")
    tq = st.selectbox("Question", ["How exposed are we to Calder Packaging?",
                                   "What is the pooled net TVPI of our 2019-2021 buyout funds?",
                                   "What issues has Brennick raised in its letters?"], key="traceq")
    tarm = st.selectbox("Setup", ARM_ORDER, index=4, format_func=lambda a: f"{a}: {LABELS[a]}", key="tracearm")
    ta, _ = ARMS[tarm](S, role).ask(tq)
    c = st.columns(4)
    c[0].metric("Time", f"{ta.latency_s:.1f} s", help="Compute plus an assumed 3 s per AI call, offline")
    c[1].metric("Cost", f"${ta.cost_usd:.4f}", help="Estimated from prompt size at claude-sonnet-5-5 prices")
    c[2].metric("AI calls", ta.llm_calls)
    c[3].metric("Tokens in", f"{ta.tokens_in:,}")
    i1, i2 = st.columns(2)
    i1.markdown("**What went in**")
    i1.code(tq, language=None)
    i2.markdown("**What came out**")
    i2.code(ta.text, language=None)
    md(f"**Checks saved on this run:** number check {'passed: every number in the text is one we computed or read' if ta.check_passed else 'failed: the answer was withheld'}; "
       f"{'refused: ' + ta.reason if ta.refused else 'not refused'}; definitions: {', '.join(ta.definitions) or 'none'}; "
       f"role: {access.ROLES[role]['label']}.")
    tl = pd.DataFrame([dict(step=s.name, ms=round(s.ms, 2)) for s in ta.steps])
    st.altair_chart(alt.Chart(tl).mark_bar().encode(x=alt.X("ms:Q", title="milliseconds"), y=alt.Y("step:N", sort=None, title=None)),
                    width="stretch")
    pick_step = st.selectbox("Step", [s.name for s in ta.steps], key="steppick")
    s0 = next(s for s in ta.steps if s.name == pick_step)
    p1, p2 = st.columns(2)
    p1.code(s0.input[:3000] or "(none)", language=None)
    p2.code(s0.output[:3000] or "(none)", language=None)
    st.caption(f"{s0.ms:.2f} ms. Langfuse tracing switches on when its keys are set; off here.")
    st.subheader("Evals in four lines")
    off = results("offline-seed42.json")
    if off:
        sm = off["summary"]
        md(f"- D answered {sm['D']['correct']}/60, C+ids {sm['C+ids']['correct']}/60, C {sm['C']['correct']}/60, B {sm['B']['correct']}/60, A {sm['A']['correct']}/60 (offline, mechanism test).\n"
           f"- Wrong numbers shown with a source: D {sm['D']['wrong_but_sourced']}, A {sm['A']['wrong_but_sourced']}.\n"
           f"- Same answer on a rerun: {round(100 * off['same_answer_on_rerun']['D'])}% for D (offline; live reruns not yet run).\n"
           f"- Held-out world with new spellings: D {results('offline-heldout-seed7-noisy.json')['summary']['D']['correct']}/60.")
    with st.expander("Choices behind it (plain English, one picture each)"):
        st.dataframe(pd.DataFrame([
            dict(choice="Where numbers come from", options="AI does the maths / code computes", picked="Code computes; the AI only picks a governed metric",
                 why="A wrong number can't hide in prose", gave_up="Questions outside the menu get refused"),
            dict(choice="Graph engine", options="Recursive SQL, DuckPGQ, NetworkX, Kuzu (archived), Neo4j (server)",
                 picked="Recursive SQL for numbers; NetworkX for people links and teaching", why="Runs anywhere, no server; same answers",
                 gave_up="A graph query language for analysts"),
            dict(choice="Semantic layer", options="Own YAML, MetricFlow, Boring Semantic Layer, Cube",
                 picked="Own YAML registry", why="1 dependency against 59 for MetricFlow; point in time fits", gave_up="A standard format other tools read"),
            dict(choice="Data layers", options="One table / bronze, silver, gold", picked="Bronze, silver, gold in DuckDB",
                 why="Bad rows blocked between layers, every number traced back", gave_up="Some storage and build time"),
            dict(choice="Point in time", options="Latest data / what we knew then", picked="What we knew then (two dates per fact)",
                 why="\"Did we know?\" has an honest answer", gave_up="Simpler queries"),
            dict(choice="Batch or stream", options="Stream / batch", picked="Batch, by source schedule",
                 why="Measured in Secondaries Radar: same answers, simpler; decisions take days", gave_up="Seconds-fresh news"),
            dict(choice="Evals", options="Tune on everything / keep a held-out world", picked="60 questions plus a held-out world",
                 why="Shows if rules only fit the test", gave_up="Fewer questions to tune on"),
        ]), hide_index=True, width="stretch")
        pics = {
            f"Code computes, the AI picks. Example: the AI picks lookthrough_exposure for Calder; code returns \\${a_cal.value:,.2f}m. Counterfactual: an AI adding numbers in text could write \\${a_cal.value:,.1f}m or \\${a_cal.value * 10:,.0f}m, and nothing would catch it; here the number check blocks any number we didn't compute.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];q[label="question"];ai[label="AI picks metric"];c[label="code computes"];chk[label="number check"];q->ai->c->chk;}',
            "Graph or recursive SQL. Example: both find Calder's 5 routes. Counterfactual: with plain joins and no recursion, a fund of funds inside a fund of funds needs new code.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];LP->FoF->Fund->Company;LP->Fund2->Company;}',
            "Point in time. Example: as of 9 September the write-down doesn't count; as of 10 September it does. Counterfactual: without the learnt date, a September answer would quietly use a letter we hadn't received.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];a[label="2 Sep: write-down happens"];b[label="10 Sep: letter reaches us"];c[label="as of 9 Sep: not counted"];d[label="as of 10 Sep: counted"];a->b;b->d;a->c[style=dashed];}',
            f"Layers. Example: {governance.contracts_report(S)['blocked']} malformed notices were blocked in silver and their corrected copies loaded. Counterfactual: one table would have mixed a European-format amount, 1.933.184,00, into the sums.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];bronze->silver->gold;silver->rejects[label="bad rows"];}',
        }
        for txt, dotg in pics.items():
            md(txt)
            st.graphviz_chart(dotg)
    with st.expander("Governance: roles, metric registry, audit log, contracts, lineage"):
        st.dataframe(pd.DataFrame([dict(role=v["label"], hidden_columns=", ".join(f"{t}.{c}" for t, cs in v["drop_columns"].items() for c in cs) or "none",
                                        hidden_tables=", ".join(v["drop_tables"]) or "none") for v in access.ROLES.values()]), hide_index=True)
        reg = registry()["metrics"]
        st.dataframe(pd.DataFrame([dict(metric=k, owner=m["owner"], version=max(m["versions"]), unit=m["unit"],
                                        definition=m["versions"][max(m["versions"])]["plain"]) for k, m in reg.items()]),
                     hide_index=True, width="stretch")
        rep = governance.contracts_report(S)
        md(f"**Data contracts:** {rep['blocked']} rows blocked at silver, each logged with its reason.")
        st.dataframe(pd.DataFrame(governance.session_log()[-10:]), hide_index=True, width="stretch")
        st.caption("Audit log for this session. On Streamlit Cloud it lasts for the session; a local run can also write logs/audit.jsonl.")
footer()
