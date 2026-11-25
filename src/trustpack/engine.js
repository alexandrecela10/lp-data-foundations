/* Trust Pack engine in the browser: a line-for-line port of retrieve.py and pipeline.py (offline path only),
   so a typed question runs in the page. tests/test_trustpack.py runs this file in Node on every golden
   question for every user and requires the same decision and answer as Python.
   Synthetic data. Not investment advice. */
var TrustEngine = function (E) {
  "use strict";
  const STOP = new Set(("a an the of to in on for and or is are was were be by at as it its our we what which who how much many " +
    "did does do from with that this there their they has have had any all into than when where why " +
    "under about say said tell large us me my please been being").split(" "));
  const IRREGULAR = new Map(Object.entries({paid: "pay", made: "make", held: "hold", took: "take", gave: "give"}));
  const MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December";
  const DATE_RE = new RegExp(`\\b\\d{1,2} (?:${MONTHS}) \\d{4}\\b`, "g");
  const ADVICE_RE = /\b(should (we|i)|recommend|good investment|worth (buying|investing)|buy or sell|increase our|sell our|exit (our|the)|strong buy)\b/i;
  const INJECTION = /ignore (all )?(previous|prior) (instructions|rules)|note to ai|you are now|system prompt/i;
  const PII_RE = /passport|emirates id|iban|bank account|phone number|mobile|email address/i;
  const ABSTAIN = "Not found in the documents you can see.";
  const ADVICE = "I can't give investment advice. I can tell you what the documents say.";
  const INJECT = "This request asks me to ignore my rules, so I won't answer it.";
  const PII_ASK = "That is personal data. It was redacted when the documents were loaded, so I can't show it.";

  const stem = t => {
    if (IRREGULAR.has(t)) return IRREGULAR.get(t);
    for (const suf of ["ing", "ed", "es", "s", "e"]) if (t.length > 4 && t.endsWith(suf)) return t.slice(0, -suf.length);
    return t;
  };
  const tokens = s => (s.toLowerCase().match(/[a-z0-9]+(?:\.[0-9]+)?/g) || []).filter(t => !STOP.has(t)).map(stem);
  const r3 = x => Math.round(x * 1000) / 1000;
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  const chunks = E.chunks;
  const tf = chunks.map(c => { const m = new Map(); for (const t of tokens(c.title + " " + c.text)) m.set(t, (m.get(t) || 0) + 1); return m; });
  const len = tf.map(m => [...m.values()].reduce((a, b) => a + b, 0));
  const df = new Map(); tf.forEach(m => m.forEach((_, t) => df.set(t, (df.get(t) || 0) + 1)));
  const avg = len.reduce((a, b) => a + b, 0) / Math.max(chunks.length, 1);
  const idf = t => { const d = df.get(t) || 0; return Math.log(1 + (chunks.length - d + 0.5) / (d + 0.5)); };

  function search(query, rooms, k = 5) {
    const q = tokens(query), hits = [];
    chunks.forEach((ch, i) => {
      if (rooms && !rooms.includes(ch.room)) return;            // the access filter: before scoring
      let s = 0;
      for (const t of q) { const c = tf[i].get(t); if (c) s += idf(t) * c * 2.2 / (c + 1.2 * (0.25 + 0.75 * len[i] / avg)); }
      if (s > 0) hits.push([r3(s), ch]);
    });
    hits.sort((a, b) => b[0] - a[0] || cmp(a[1].chunk_id, b[1].chunk_id));
    return hits.slice(0, k);
  }

  const sentences = text => text.split(/(?<=[.!?])\s+(?=[A-Z$\[])/).map(s => s.trim()).filter(Boolean);
  const inter = (a, b) => new Set([...a].filter(x => b.has(x)));
  const minus = (a, b) => new Set([...a].filter(x => !b.has(x)));
  const w = ts => { let s = 0; for (const t of ts) s += idf(t); return s; };

  function extractive(question, hits) {
    const q = new Set(tokens(question));
    const caps = new Set(tokens((question.match(/(?<!^)\b[A-Z][a-z]+/g) || []).join(" ")));
    const titleToks = hits.map(([, c]) => new Set(tokens(c.title)));
    const names = new Set([...q].filter(t => caps.has(t) || titleToks.some(s => s.has(t))));
    const asked = minus(q, names);
    const ql = question.toLowerCase();
    const asOf = question.match(DATE_RE) || [];
    const cands = [];
    hits.forEach(([, ch], rank) => {
      if (ch.suspected_injection) return;
      const ctx = new Set(tokens(ch.title + " " + ch.text));
      if (names.size && w(inter(names, ctx)) < 0.4 * w(names)) return;
      if (asOf.length && !asOf.every(d => (E.doc_dates[ch.doc_id] || "").includes(d))) return;
      for (const s of sentences(ch.text)) {
        const st = new Set(tokens(s));
        if (asked.size && w(inter(asked, st)) < 0.5 * w(asked)) continue;
        if (ql.startsWith("when") && !new RegExp(`${MONTHS}|\\b20\\d\\d\\b`).test(s)) continue;
        if ((ql.startsWith("how much") || ql.startsWith("how many")) && !/[$%]|\d/.test(s)) continue;
        const score = w(inter(q, st)) + 0.5 * w(minus(inter(q, ctx), st));
        cands.push([r3(score - 0.01 * rank), ch.chunk_id, s]);
      }
    });
    cands.sort((a, b) => b[0] - a[0]);
    if (!cands.length || cands[0][0] < E.abstain_floor) return {abstained: true, claims: [], best_score: cands.length ? cands[0][0] : 0};
    const best = cands[0], claims = [{text: best[2], chunk_id: best[1], quote: best[2]}];
    for (const c of cands.slice(1)) if (c[1] !== best[1] && c[0] >= 0.75 * best[0]) { claims.push({text: c[2], chunk_id: c[1], quote: c[2]}); break; }
    return {abstained: false, claims, best_score: best[0]};
  }

  function stoppedAt(decision, pre, leaked) {
    if (decision === "refused") return "input rule (layer 7)";
    if (pre === "pii") return "personal data rule (layer 2)";
    if (decision === "abstained") return leaked.length ? "access filter (layer 5), then nothing in scope supported an answer" : "abstain rule (layer 7): nothing supported an answer";
    return null;
  }

  function ask(userId, question) {
    const t0 = performance.now();
    const u = E.users[userId];
    const pre = ADVICE_RE.test(question) ? "advice" : INJECTION.test(question) ? "injection" : PII_RE.test(question) ? "pii" : null;
    const steps = [{name: "input guardrails", layer: 7, advice: pre === "advice", prompt_injection: pre === "injection", asks_for_pii: pre === "pii"}];
    const run = pre === null || pre === "pii";
    const hits = run ? search(question, u.rooms) : [];
    const leaked = (run ? search(question, null) : []).filter(([, c]) => !u.rooms.includes(c.room)).map(([, c]) => c.chunk_id);
    steps.push({name: "access filter", layer: 5, allowed_rooms: u.rooms, filter: `room IN (${u.rooms.join(", ")}) applied before scoring`,
      chunks_in_scope: chunks.filter(c => u.rooms.includes(c.room)).length, chunks_total: chunks.length, would_leak_if_filtered_after: leaked});
    steps.push({name: "retrieval", layer: 6, retriever: E.versions.retriever, k: 5, hits: hits.map(([score, c]) => ({...c, score}))});
    let out;
    if (pre === "advice" || pre === "injection") out = {answer: pre === "advice" ? ADVICE : INJECT, decision: "refused", claims: [], generator: "rule", best_score: null};
    else if (pre === "pii") out = {answer: PII_ASK, decision: "abstained", claims: [], generator: "rule", best_score: null};
    else {
      const g = extractive(question, hits);
      const allowed = new Map(hits.map(([, c]) => [c.chunk_id, c]));
      let claims = g.claims.map(c => ({...c, verified: allowed.has(c.chunk_id) && allowed.get(c.chunk_id).text.includes(c.quote)}));
      let abst = g.abstained || (claims.length && !claims.every(c => c.verified));
      out = {answer: abst ? ABSTAIN : claims.map(c => `${c.quote} [${c.chunk_id}]`).join(" "), decision: abst ? "abstained" : "answered",
        claims, generator: "extractive", best_score: g.best_score};
    }
    steps.push({name: "generation", layer: 7, generator: out.generator, abstain_floor: E.abstain_floor, best_sentence_score: out.best_score,
      injection_chunks_skipped: hits.filter(([, c]) => c.suspected_injection).map(([, c]) => c.chunk_id), restricted_kept_offline: false});
    steps.push({name: "citation check", layer: 7, claims: out.claims, all_verified: out.claims.length ? out.claims.every(c => c.verified) : null});
    const ms = Math.round((performance.now() - t0) * 100) / 100;
    steps.push({name: "trace and audit", layer: 10, latency_ms: ms});
    return {request_id: "rq-browser-" + Math.random().toString(16).slice(2, 12), ts: new Date().toISOString().slice(0, 19),
      user: {id: userId, ...u}, question, versions: E.versions, steps, answer: out.answer, decision: out.decision,
      citations: out.claims.map(c => c.chunk_id), latency_ms: ms, tokens: {input: 0, output: 0}, cost_usd: 0,
      stopped_at: stoppedAt(out.decision, pre, leaked),
      online_checks: {citations_valid: out.claims.every(c => c.verified), abstained: out.decision !== "answered", answer_chars: out.answer.length, pii_in_answer: false},
      in_browser: true};
  }
  return {ask, search, tokens};
};
if (typeof module !== "undefined") module.exports = TrustEngine;
