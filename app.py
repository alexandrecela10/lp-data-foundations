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
from answerdesk.foundations.semantic_arms import plain_route  # noqa: E402
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
md("**When the CIO asks about the portfolio, you send the right number, with its sources, in minutes.**")
st.caption("You're Sara, a portfolio analyst at a large LP (an investor in many private equity funds). Work through the first three tabs. "
           "How the foundations work shows five ways to organise the same data, how each one answers, and where each one breaks.")
st.caption(DISCLAIMER)

with st.sidebar:
    st.header("You are")
    role = st.radio("Role (a demo switch, not a login)", list(access.ROLES), format_func=lambda r: access.ROLES[r]["label"],
                    key="role")
    st.caption(f"Today is Monday {TODAY:%d %B %Y}, 08:12. The committee pack is as of {PACK_DATE:%d %B %Y}.")
    if llm.available():
        st.warning(f"Live mode: {llm.NOTICE}")
    else:
        st.info("Offline: no AI. Fixed rules read your question; code calculates every number.")
    st.header("Your morning")
    st.markdown("1. **Portfolio chat**: answer the CIO\n2. **Committee pack**: export Thursday's pack\n"
                "3. **Manager briefing**: brief the head of private equity\n4. **How the foundations work**: see why it works")
    footer()

tabs = st.tabs(["Portfolio chat", "Committee pack", "Manager briefing", "How the foundations work", "Under the hood"])
EXPLAINER = ROOT / "static" / "foundations.html"


@st.cache_data
def explainer_html(mtime: float) -> str:
    return EXPLAINER.read_text()


# ------------------------------------------------------------------ helpers for answers
def route_table(ans):
    rows = []
    for i, r in enumerate(ans.routes, 1):
        age = (ans.as_of - r["as_of"]).days if r.get("as_of") else None
        rows.append({"#": i, "how we own it": plain_route(r["route"]), "value ($m)": round(r["value"], 3),
                     "fund report date": str(r.get("as_of")), "days old": age,
                     "older than 90 days": "yes" if age and age > 90 else "no",
                     "cut by a later letter": "yes" if r.get("factor", 1.0) != 1.0 else "no"})
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
    md("**Portfolio chat: ask in plain English and get a number you can send, with every way we own the company, how the number is defined, and the date of every figure.**")
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
            md(f"**For the CIO:** about **\\${ans.value:,.2f}m**, held {len(ans.routes)} ways"
               + (", after the value cut a manager's letter told us about on 10 September" if any(r.get("factor", 1) != 1 for r in ans.routes) else "")
               + (". The fund reports behind it have different dates." if mixed else "."))
            st.dataframe(route_table(ans), hide_index=True, width="stretch")
            if ans.pending:
                st.warning(esc(f"{len(ans.pending)} letter item(s) not counted, waiting for review: \"{ans.pending[0]['quote']}\""))
            with st.expander("Show the ways we own it on a map (graph)"):
                n = total_hops(ans)
                c1, c2 = st.columns([1, 4])
                if c1.button("Next link", key="nexthop"):
                    ss.hop = min(ss.hop + 1, n)
                if c1.button("Show all", key="allhops"):
                    ss.hop = n
                if c1.button("Reset", key="resethops"):
                    ss.hop = 0
                c1.caption(f"Link {ss.hop} of {n}")
                c2.graphviz_chart(dot_routes(ans, ss.hop))
                st.caption("Each link is numbered; bold blue means the walk has reached it. The table above is the main view.")
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
    md("**Committee pack: every number calculated exactly like last quarter's, as of a date you choose.**")
    md("You're preparing Thursday's investment committee pack: how our buyout funds from 2019 to 2021 are doing against "
       "plan, after fees, and how much of the money we still owe funds they will ask for in the next 12 months.")
    c1, c2 = st.columns(2)
    as_of = c1.selectbox("As of", [PACK_DATE, dt.date(2026, 6, 30)], format_func=lambda d: d.strftime("%d %B %Y"))
    use_old = c2.toggle("Use last quarter's definition of money still owed (v1)", value=False)
    dash = interfaces.dashboard(S, role, as_of, "pack_2026_q2" if use_old else None)
    for c in dash["changes"]:
        st.info(esc(f"Changed since the 30 June pack: {c['metric']} v{c['version']} from {c['from_']:%d %b %Y}. {c['plain']}"))
    v1, v2, v3 = st.tabs(["Exposure", "Funds against plan", "Cash calls, next 12 months"])
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
    with st.expander("Two teams, two formulas, two answers (why each measure needs one agreed definition)"):
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
           f"\\${b26:,.2f}m, because commitment ignores what the company is worth. Without one agreed definition, "
           "the CIO gets whichever number the analyst happened to use.")
    st.subheader("Decide: export the pack")
    st.download_button("Export pack as of " + as_of.strftime("%d %b %Y"), interfaces.export_pack(dash),
                       file_name=f"pack-{as_of}.csv", type="primary")

# ------------------------------------------------------------------ 3. Manager briefing
with tabs[2]:
    md("**Manager briefing: one note on a manager's history with us. Numbers come from the agreed definitions; problems are quoted from the manager's letters.**")
    md("The head of private equity is deciding whether to commit to Brennick Capital Partners VI. You write the briefing.")
    note_md = interfaces.briefing(S, "Brennick", role)
    st.markdown(esc(note_md))
    st.subheader("Decide: send the briefing")
    st.download_button("Download briefing (Markdown)", note_md, file_name="brennick-briefing.md", type="primary")

# ------------------------------------------------------------------ 5a. SQL notebook (top of Under the hood)
with tabs[4]:
    md("**Under the hood: how one answer was made, what was checked, and the choices behind it.**")
    st.subheader("SQL notebook")
    md("For the data team: read-only SQL on the same checked tables, showing only what your role may see.")
    sql = st.text_area("Query", "SELECT fund_id, as_of, name_reported, company_id, match_method, value\nFROM gold.holdings\n"
                                "WHERE company_id = 'C0001' ORDER BY as_of DESC LIMIT 10", height=120)
    if st.button("Run query", key="runsql"):
        try:
            st.dataframe(interfaces.notebook(S, sql, role), hide_index=True, width="stretch")
        except Exception as e:
            st.error(esc(str(e)[:300]))
    st.caption("Try `SELECT mgmt_fee_pct FROM gold.positions` as Sara: the column doesn't exist in her copy of the data.")

# ------------------------------------------------------------------ 4. How the foundations work
with tabs[3]:
    md("**How the foundations work: the same question through five setups, animated, with where each one breaks.**")
    if EXPLAINER.exists():
        st.components.v1.html(explainer_html(EXPLAINER.stat().st_mtime), height=1250, scrolling=True)
        st.caption("[Open full screen](app/static/foundations.html). Rebuild with `python -m answerdesk.cli explainer`.")
    else:
        st.caption("static/foundations.html not found. Build it with `python -m answerdesk.cli explainer`.")
    off = results("offline-seed42.json")
    held = results("offline-heldout-seed7-noisy.json")
    st.subheader("The scores behind the chapters")
    live = results("live-claude-sonnet-5-5.json")
    live = live if live and "summary" in live and live["meta"].get("valid", True) else None
    runs = (["Live: Claude reads every question"] if live else []) + ["Offline: fixed rules stand in for the AI"]
    which = st.radio("Results", runs, horizontal=True, key="which_run")
    res = live if which.startswith("Live") else off
    if res:
        sm = res["summary"]
        md(f"**Decision: use C+ids (agreed definitions, a company name list and letter search) for numbers and for finding every "
           f"way we own a company. Add the graph only for links between people and managers.** {which.split(':')[0]}, D got "
           f"{sm['D']['correct']}/60 right and C+ids {sm['C+ids']['correct']}/60. On the CIO's questions they tie at "
           f"{sm['D']['request_1']}/20 each, so by the rule set before the test, the graph isn't worth adding for those. "
           f"It adds the 2 questions about where Brennick's former partners went.")
        if res is live:
            pa = res["meta"]["all_passes"]
            st.caption(esc(f"Live run {res['meta']['run_at']}: claude-sonnet-5-5 read every question for every setup, read the "
                           f"document passages in A and wrote the database query in B. {pa['passes']} runs, {pa['llm_calls']} calls, "
                           f"{pa['live_failures']} failed, ${pa['cost_usd']:.2f} billed. Same answer when asked again: "
                           + ", ".join(f"{a} {round(100 * res['same_answer_on_rerun'][a])}%" for a in ARM_ORDER) + "."))
        else:
            st.warning("Offline, fixed rules read the questions instead of the AI: these scores show what each setup can do, not how often Claude gets it wrong.")
        kinds = {1: "Company in the news", 2: "Committee pack", 3: "Manager decision"}
        df = pd.DataFrame([dict(setup=f"{a}: {LABELS[a]}", request=kinds[r], correct=sm[a][f"request_{r}"])
                           for a in ARM_ORDER for r in (1, 2, 3)])
        st.altair_chart(alt.Chart(df).mark_bar().encode(
            x=alt.X("correct:Q", title="Right answers (20 questions per kind)", scale=alt.Scale(domain=[0, 60])),
            y=alt.Y("setup:N", sort=ARM_ORDER, title=None), color=alt.Color("request:N", title=None),
            tooltip=["setup", "request", "correct"]), width="stretch")
        tbl = pd.DataFrame([{
            "setup": a, "right (of 60)": sm[a]["correct"],
            "wrong numbers shown with a source": sm[a]["wrong_but_sourced"],
            "median seconds to an answer you can send": round(sm[a]["median_time_to_send_s"] or 0),
            "expected minutes per question": round(sm[a]["expected_time_per_question_s"] / 60, 1),
            "trick questions refused": f"{sm[a]['correct_refusals']}/{sm[a]['refusal_traps']}",
            "est. cost per answer ($)": round(sm[a]["cost_per_answer_usd"], 4)} for a in ARM_ORDER])
        st.dataframe(tbl, hide_index=True, width="stretch")
        st.caption("Time = time to produce the answer (computing, plus an assumed 3 s per AI call) plus Sara's time to check it "
                   "(assumed: 20 s to read, 5 s per number that shows its source and definition, 30 s per number with a source "
                   "only, 120 s per number she checks by hand). In the expected time, a wrong answer adds 2 hours to find and fix it.")
        with st.expander("Where each setup wins and where it fails"):
            md("- **Documents and an AI chatbot (A)** wins on letters: it found every Brennick problem and quoted the letter. It "
               "fails on numbers: it multiplied a line from the fund of funds' report by our share of the fund of funds, so it "
               "showed wrong numbers *with* sources (the most dangerous kind).\n"
               "- **AI-written database query (B)** finds companies held directly and simple totals. It misses what the tables "
               "don't spell out: when a report arrived, value cuts announced in letters, payouts a fund can call back, and the "
               "agreed cash-call forecast.\n"
               "- **Agreed definitions (C)** gets every committee-pack number right, because each measure is defined once. It "
               "misses ways we own a company that are reported under another spelling.\n"
               "- **C+ids** adds a list linking every spelling to one company, and letter search: 20/20 on the CIO's questions.\n"
               "- **D** adds a graph of links between people and managers: where a partner went after leaving.")
        with st.expander("If the checking times are wrong, does the order change?"):
            st.dataframe(pd.DataFrame([dict(variant=v["variant"], ranking=" < ".join(v["ranking"]),
                                            **{a: round(v["median_s"][a] or 0) for a in ARM_ORDER}) for v in res["sensitivity"]]),
                         hide_index=True, width="stretch")
            st.caption("Median seconds to send a right answer, fastest first. Wrong answers are left out.")
        with st.expander("A second made-up portfolio, with spellings the code was never tuned on"):
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
            rows = pd.DataFrame(res["rows"])[["arm", "qid", "question", "correct", "detail", "traps"]]
            st.dataframe(rows, hide_index=True, width="stretch")
    sc = results("scale.json")
    st.subheader("With 10 and 100 times more data")
    if sc:
        long = []
        for r in sc:
            for k, lab in [("route_sql_ms", "Every way we own a company: database query"),
                           ("route_graph_total_ms", "Same, graph: build + walk (NetworkX)"),
                           ("route_graph_walk_ms", "Same, graph: walk only, already built"),
                           ("route_pgq_ms", "Same, graph inside the database (DuckPGQ)"),
                           ("portfolio_sum_sql_ms", "Sector total: agreed definition"),
                           ("portfolio_sum_graph_only_ms", "Sector total: graph only"),
                           ("perf_metric_ms", "TVPI across funds: agreed definition, one fund at a time")]:
                if r.get(k) is not None:
                    long.append(dict(scale=f"{r['scale']}x", ms=r[k], method=lab, funds=r["funds"]))
        ch = alt.Chart(pd.DataFrame(long)).mark_line(point=True).encode(
            x=alt.X("scale:N", sort=["1x", "10x", "100x"], title="Data size"), y=alt.Y("ms:Q", scale=alt.Scale(type="log"),
                                                                                    title="Milliseconds (log)"),
            color=alt.Color("method:N", title=None), tooltip=["method", "scale", "ms", "funds"])
        st.altair_chart(ch, width="stretch")
        b = sc[-1]
        md(f"**What changes at 100x** ({b['funds']:,} funds, {b['documents']:,} documents): the full rebuild takes "
           f"{b['build_s']:.0f} s, most of it matching company names ({b['pipeline_s']['silver']:.0f} s). Finding every way we own one "
           f"company takes {b['route_sql_ms']:.0f} ms with a database query, {b['graph_build_ms']:.0f} + {b['route_graph_walk_ms']:.0f} ms "
           f"to build the graph and walk it, and {b['route_pgq_ms']:.0f} ms with DuckPGQ once its graph is set up: under a second "
           f"every way. What slows down first is a measure calculated one fund at a time: TVPI across funds takes "
           f"{b['perf_metric_ms'] / 1000:.1f} s. Peak memory {b['max_rss_mb']:,.0f} MB, "
           "so 100x runs locally and the demo reads the committed results.")
    else:
        st.caption("Scale results not found (evals/results/scale.json).")
    st.subheader("Decide: which setup would you fund?")
    pick = st.radio("Your pick", ["C+ids for numbers and ownership, graph for people links (recommended)",
                                  "D everywhere", "C only", "Documents and an AI chatbot only"], key="fund_pick_radio")
    if st.button("Record my pick", key="pick"):
        ss.fund_pick = pick
        st.success(esc(f"Recorded: {pick}"))

# ------------------------------------------------------------------ 4b. the same question in code, one metric everywhere
a_cal, _ = interfaces.chat(S, "How exposed are we to Calder Packaging?", role, "D")
with tabs[3], st.expander("The same question in code, and one metric in every screen"):
    st.subheader("1. Every way we own Calder, as a walk along links")
    _sh = access.role_db(S, role).execute("SELECT lp_share FROM gold.reports WHERE fund_id = 'FOF01' ORDER BY as_of DESC LIMIT 1").fetchone()[0]
    _st = access.role_db(S, role).execute("SELECT share FROM gold.fof_stakes WHERE fund_id = 'F0009' ORDER BY as_of DESC LIMIT 1").fetchone()[0]
    md("A **graph** stores things (our pension plan, funds, companies, people) and the links between them. A question like "
       f"\"every way we own Calder\" becomes a walk along links. Example: our plan holds {_sh * 100:.1f}% of Selbrook Fund of Funds III, "
       f"which holds {_st * 100:.0f}% of Ostrova Capital Partners IV, which reports \"Calder Pack.\". The identity link says Calder Pack. is "
       "Calder Packaging Ltd. Without that link, the walk stops at a name nobody recognises, and that holding is missed.")
    st.subheader("2. The same question, three ways")
    k1, k2, k3 = st.columns(3)
    k1.markdown("**SQL with joins**")
    k1.code(graph.SQL_JOINS, language="sql")
    k2.markdown("**Graph query (SQL/PGQ, and Cypher)**")
    k2.code(graph.PGQ + "\n\n" + graph.CYPHER, language="sql")
    k3.markdown("**Semantic-layer request**")
    k3.code(graph.SEMANTIC, language="yaml")
    md(f"All three find the same 5 ways we own Calder and **\\${a_cal.value:,.2f}m**. The difference is who writes and "
       "maintains the logic: in SQL, every new shape of ownership chain needs another block of code; in a graph, the walk "
       "handles chains of any length; in the semantic layer, the logic is written once inside the agreed definition, and "
       "the person asking only picks it.")
    st.subheader("3. One measure, defined once")
    m = registry()["metrics"]["lookthrough_exposure"]
    md(f"**Exposure, version 2, owned by {m['owner']}.** {m['versions'][2]['plain']}")
    dashv = interfaces.dashboard(S, role, TODAY)["exposure"]
    cal = SemanticLayer(S, role, "resolved").run(MetricRequest(metric="lookthrough_exposure", as_of=TODAY,
                                                               company="Calder Packaging")).numbers[0].value
    md(f"- **Chat:** \\${a_cal.value:,.2f}m\n- **Dashboard (same metric, same date):** \\${cal:,.2f}m\n"
       f"- **Notebook (`metric: lookthrough_exposure`):** \\${cal:,.2f}m")
    md("Same number everywhere, because all three ask the semantic layer. If instead the dashboard team counted "
       "commitment instead of value (the Investment team's old v1), the dashboard would show a different number from "
       "the chat on the same morning. See the Committee pack tab, \"Two teams, two definitions\".")

# ------------------------------------------------------------------ 5. Under the hood
with tabs[4]:
    st.subheader("How the pieces connect")
    st.graphviz_chart("""digraph { rankdir=LR; node [shape=box, style=rounded, fontsize=10];
      src [label="6 sources\\n(holdings, notices, reports,\\nletters, reference, news)"]; b [label="bronze\\n(as received)"];
      s [label="silver\\n(checked fields,\\nname matching)"]; g [label="gold\\n(tables, source of every row)"];
      sem [label="semantic layer\\n(agreed definitions)"]; gr [label="graph\\n(ownership, people)"]; ai [label="AI reads the question\\n(fixed rules offline)"];
      ui [label="chat / pack / briefing / notebook"];
      src -> b -> s -> g; g -> sem; g -> gr; ai -> sem; ai -> gr; sem -> ui; gr -> ui; }""")
    md("Documents are kept as received, read into checked fields, then into tables. The AI only works out which "
       "measure you're asking for; code calculates every number.")
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
    st.subheader("Test results in four lines")
    off = results("offline-seed42.json")
    if off:
        sm = off["summary"]
        md(f"- D answered {sm['D']['correct']}/60, C+ids {sm['C+ids']['correct']}/60, C {sm['C']['correct']}/60, B {sm['B']['correct']}/60, A {sm['A']['correct']}/60 (offline: fixed rules read the questions).\n"
           f"- Wrong numbers shown with a source: D {sm['D']['wrong_but_sourced']}, A {sm['A']['wrong_but_sourced']}.\n"
           f"- Live with claude-sonnet-5-5: D {results('live-claude-sonnet-5-5.json')['summary']['D']['correct']}/60, A {results('live-claude-sonnet-5-5.json')['summary']['A']['correct']}/60; D gave the same answer to every question when asked again.\n"
           f"- Second made-up portfolio, with new spellings: D {results('offline-heldout-seed7-noisy.json')['summary']['D']['correct']}/60.")
    with st.expander("Choices behind it (plain English, one picture each)"):
        st.dataframe(pd.DataFrame([
            dict(choice="Where numbers come from", options="AI does the maths / code computes", picked="Code calculates; the AI only picks the measure",
                 why="A wrong number can't hide in prose", gave_up="Questions outside the list of measures get a no"),
            dict(choice="Graph engine", options="Recursive SQL, DuckPGQ, NetworkX, Kuzu (archived), Neo4j (server)",
                 picked="Recursive SQL for numbers; NetworkX for people links and teaching", why="Runs anywhere, no server; same answers",
                 gave_up="A graph query language for analysts"),
            dict(choice="Semantic layer", options="Own YAML, MetricFlow, Boring Semantic Layer, Cube",
                 picked="Own YAML registry", why="1 dependency against 59 for MetricFlow; answering as of a past date fits", gave_up="A standard format other tools read"),
            dict(choice="Data layers", options="One table / bronze, silver, gold", picked="Bronze, silver, gold in DuckDB",
                 why="Bad rows blocked between layers, every number traced back", gave_up="Some storage and build time"),
            dict(choice="As of a past date", options="Latest data / what we knew then", picked="What we knew then (two dates per fact)",
                 why="\"Did we know?\" has an honest answer", gave_up="Simpler queries"),
            dict(choice="Batches or second-by-second", options="Second-by-second / batches", picked="Batches, on each source's schedule",
                 why="Measured in Secondaries Radar: same answers, simpler; decisions take days", gave_up="Seconds-fresh news"),
            dict(choice="Testing", options="Tune on everything / keep a second portfolio aside", picked="60 questions plus a second portfolio kept aside",
                 why="Shows if rules only fit the test", gave_up="Fewer questions to tune on"),
        ]), hide_index=True, width="stretch")
        pics = {
            f"Code computes, the AI picks. Example: the AI picks lookthrough_exposure for Calder; code returns \\${a_cal.value:,.2f}m. Counterfactual: an AI adding numbers in text could write \\${a_cal.value:,.1f}m or \\${a_cal.value * 10:,.0f}m, and nothing would catch it; here the number check blocks any number we didn't compute.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];q[label="question"];ai[label="AI picks metric"];c[label="code computes"];chk[label="number check"];q->ai->c->chk;}',
            "Graph or recursive SQL. Example: both find the 5 ways we own Calder. Counterfactual: with plain joins and no recursion, a fund of funds inside a fund of funds needs new code.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];LP->FoF->Fund->Company;LP->Fund2->Company;}',
            "As of a past date. Example: as of 9 September the write-down doesn't count; as of 10 September it does. Counterfactual: without the date the letter reached us, a September answer would quietly use a letter we hadn't received.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];a[label="2 Sep: write-down happens"];b[label="10 Sep: letter reaches us"];c[label="as of 9 Sep: not counted"];d[label="as of 10 Sep: counted"];a->b;b->d;a->c[style=dashed];}',
            f"Layers. Example: {governance.contracts_report(S)['blocked']} broken notices were stopped in silver and their corrected copies loaded. Counterfactual: one table would have mixed a European-format amount, 1.933.184,00, into the sums.":
                'digraph{rankdir=LR;node[shape=box,style=rounded];bronze->silver->gold;silver->rejects[label="bad rows"];}',
        }
        for txt, dotg in pics.items():
            md(txt)
            st.graphviz_chart(dotg)
    with st.expander("Controls: who sees what, the list of measures, the log of answers, rejected rows"):
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
