"""Keyword search (BM25) over the documents a role may see. Used by A for everything and by D for letters."""
from __future__ import annotations

import math
import re
from collections import Counter

from .. import access

_idx: dict = {}
KIND_WORDS = {"restatement": r"restated", "team_change": r"left the firm|key person", "extension": r"extended",
              "fee": r"\bfees?\b", "incident": r"incident"}


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


class Search:
    def __init__(self, store, role: str):
        key = (id(store), role)
        if key not in _idx:
            docs = [d for d in store.docs if d.text and access.can_see_doc(d.restricted_to, role)]
            tf = [Counter(tokens(d.text)) for d in docs]
            df = Counter()
            for c in tf:
                df.update(c.keys())
            avg = sum(sum(c.values()) for c in tf) / max(len(tf), 1)
            _idx[key] = (docs, tf, df, avg)
        self.docs, self.tf, self.df, self.avg = _idx[key]

    def query(self, q: str, k: int = 10, kinds: tuple = (), before=None) -> list:
        qt = tokens(q)
        n = len(self.docs)
        scored = []
        for d, c in zip(self.docs, self.tf):
            if kinds and d.kind not in kinds:
                continue
            if before and d.learnt_at > before:
                continue
            L = sum(c.values())
            s = 0.0
            for t in qt:
                if t in c:
                    idf = math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                    s += idf * c[t] * 2.2 / (c[t] + 1.2 * (0.25 + 0.75 * L / self.avg))
            if s > 0:
                scored.append((s, d))
        scored.sort(key=lambda x: -x[0])
        return [d for _, d in scored[:k]]

    def letters(self, manager: str | None, as_of, pattern: str, kinds: list | None = None) -> list[dict]:
        pat = "|".join(KIND_WORDS[k] for k in kinds if k in KIND_WORDS) if kinds else pattern
        out = []
        for d in self.docs:
            if d.kind != "letter" or d.learnt_at > as_of:
                continue
            frm = re.search(r"From: (.+)", d.text).group(1)
            if manager and not frm.lower().startswith(manager.lower()):
                continue
            body = d.text.split("\n", 2)[-1]
            for sent in re.split(r"(?<=\.)\s+", body):
                if re.search(pat, sent, re.I):
                    out.append(dict(doc_id=d.doc_id, learnt=d.learnt_at, quote=sent.strip()))
                    break
        return out
