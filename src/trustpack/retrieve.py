"""Layers 5 and 6: access control at retrieval, then BM25.

The user's rooms filter the chunks BEFORE scoring, so a chunk from another room is never scored,
never ranked and never reaches the answerer. BM25 formula reused from answerdesk/foundations/search.py.
"""
from __future__ import annotations

import math
import re
from collections import Counter

USERS = {
    "karim": dict(name="Karim Ardenvale", role="Principal", rooms=["public", "governance", "investments", "advisor"]),
    "leila": dict(name="Leila Ardenvale", role="Next-generation family member", rooms=["public", "investments"]),
    "priya": dict(name="Priya Kestrell", role="Chief investment officer", rooms=["public", "investments", "advisor"]),
    "selim": dict(name="Selim Dorrance", role="External counsel", rooms=["public", "advisor"]),
}
STOP = set("a an the of to in on for and or is are was were be by at as it its our we what which who how much many "
           "did does do from with that this there their they has have had any all into than when where why "
           "under about say said tell large us me my please been being".split())

IRREGULAR = {"paid": "pay", "made": "make", "held": "hold", "took": "take", "gave": "give"}


def stem(t: str) -> str:
    """Light suffix stripping so "declined" meets "decline" and "fees" meets "fee"."""
    if t in IRREGULAR:
        return IRREGULAR[t]
    for suf in ("ing", "ed", "es", "s", "e"):
        if len(t) > 4 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def tokens(s: str) -> list[str]:
    return [stem(t) for t in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", s.lower()) if t not in STOP]


class Index:
    def __init__(self, chunks):
        self.chunks = chunks
        self.tf = [Counter(tokens(c.title + " " + c.text)) for c in chunks]
        self.df = Counter()
        for c in self.tf:
            self.df.update(c.keys())
        self.avg = sum(sum(c.values()) for c in self.tf) / max(len(self.tf), 1)

    def idf(self, t: str) -> float:
        n = len(self.chunks)
        return math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))

    def _score(self, q: list[str], i: int) -> float:
        c, L = self.tf[i], sum(self.tf[i].values())
        return sum(self.idf(t) * c[t] * 2.2 / (c[t] + 1.2 * (0.25 + 0.75 * L / self.avg)) for t in q if t in c)

    def search(self, query: str, rooms: list[str] | None, k: int = 5) -> list[tuple[float, object]]:
        """rooms=None means no access filter (used only to measure what a post-filter design would leak)."""
        q = tokens(query)
        hits = []
        for i, ch in enumerate(self.chunks):
            if rooms is not None and ch.room not in rooms:   # the access filter: before scoring
                continue
            s = self._score(q, i)
            if s > 0:
                hits.append((round(s, 3), ch))
        hits.sort(key=lambda x: (-x[0], x[1].chunk_id))
        return hits[:k]
