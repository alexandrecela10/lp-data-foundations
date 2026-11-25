"""Layers 1 to 3: document contracts, classification and PII redaction, chunk lineage.

Each file in trust_pack/data/room is a document with a front-matter header. A document that
fails its contract is rejected with a reason and never reaches the index. PII is redacted in
every chunk before indexing; the redaction log keeps the type, position and a hash, never the value.
Synthetic data. Not investment advice.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[2] / "trust_pack"
ROOM_DIR = ROOT / "data" / "room"
INGEST_DATE = dt.date(2026, 11, 20)  # fixed, so every run is reproducible
REGISTRY = yaml.safe_load((ROOT / "registry.yaml").read_text())

Room = Literal["public", "governance", "investments", "advisor"]
Label = Literal["public", "confidential", "restricted"]
ROOM_LABEL = {"public": "public", "governance": "restricted", "investments": "confidential", "advisor": "confidential"}

PII = {  # uae-pii-v1. All values in the data room are fake.
    "PASSPORT": r"\b[A-Z]\d{7}\b",
    "EMIRATES_ID": r"\b784-\d{4}-\d{7}-\d\b",
    "IBAN": r"\bAE\d{21}\b",
    "PHONE": r"\+971[ \d]{9,12}\d",
    "EMAIL": r"\b[\w.]+@[\w.]+\.example\b",
}


class DocRecord(BaseModel):
    """The contract every document must meet before it is indexed."""
    doc_id: str = Field(pattern=r"^[A-Z]\d{2}$")
    title: str = Field(min_length=3)
    doc_type: str
    room: Room
    classification: Label
    doc_date: dt.date
    source_path: str
    sha256: str = Field(min_length=64, max_length=64)
    text: str

    @field_validator("doc_date")
    @classmethod
    def _date_sane(cls, v: dt.date) -> dt.date:
        if v > INGEST_DATE:
            raise ValueError(f"document date {v} is after the ingest date {INGEST_DATE}")
        if v.year < 2000:
            raise ValueError(f"document date {v} is before 2000")
        return v

    @field_validator("text")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if len(v.strip()) < 20:
            raise ValueError("empty text (no text layer, or under 20 characters)")
        return v

    @model_validator(mode="after")
    def _label_matches_room(self):
        if ROOM_LABEL[self.room] != self.classification:
            raise ValueError(f"room {self.room} needs label {ROOM_LABEL[self.room]}, got {self.classification}")
        return self


class Chunk(BaseModel):
    """One retrievable passage, with full lineage back to the bytes it came from."""
    chunk_id: str
    doc_id: str
    title: str
    room: Room
    classification: Label
    doc_sha256: str
    char_start: int
    char_end: int
    text: str                      # redacted text: what retrieval and the answerer see
    pii_redacted: int
    suspected_injection: bool
    chunker_version: str
    index_version: str = ""


INJECTION = re.compile(r"ignore (all )?(previous|prior) (instructions|rules)|note to ai|you are now|system prompt", re.I)


def _split(raw: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    if not m:
        return {}, raw
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def redact(text: str) -> tuple[str, list[dict]]:
    """Replace PII with [TYPE]. Returns the new text and one log row per hit (no values kept)."""
    log = []
    for kind, pat in PII.items():
        for m in re.finditer(pat, text):
            log.append(dict(type=kind, start=m.start(), value_sha256=hashlib.sha256(m.group().encode()).hexdigest()[:12]))
        text = re.sub(pat, f"[{kind}]", text)
    return text, log


def load(room_dir: Path = ROOM_DIR) -> tuple[list[DocRecord], list[dict]]:
    """Read every file, apply the contract, reject failures and duplicates with a logged reason."""
    docs, rejects, seen = [], [], {}
    for p in sorted(room_dir.glob("*.md")):
        meta, body = _split(p.read_text())
        sha = hashlib.sha256(body.encode()).hexdigest()
        base = dict(doc_id=str(meta.get("doc_id", p.stem[:3])), file=p.name)
        if sha in seen:
            rejects.append(dict(**base, reason=f"duplicate content: same SHA-256 as {seen[sha]}"))
            continue
        try:
            d = DocRecord(**{**meta, "source_path": f"trust_pack/data/room/{p.name}", "sha256": sha, "text": body})
        except ValidationError as e:
            reason = "; ".join(f"{'.'.join(map(str, x['loc'])) or 'document'}: {x['msg'].removeprefix('Value error, ')}"
                               for x in e.errors())
            rejects.append(dict(**base, reason=reason))
            continue
        seen[sha] = d.doc_id
        docs.append(d)
    return docs, rejects


def chunk(docs: list[DocRecord]) -> tuple[list[Chunk], list[dict]]:
    """paragraph-v1: one chunk per paragraph. Offsets point into the original (unredacted) body."""
    chunks, pii_log = [], []
    for d in docs:
        n = 0
        for m in re.finditer(r"\S(?:.|\n(?!\n))*", d.text):
            red, log = redact(m.group())
            n += 1
            cid = f"{d.doc_id}-c{n}"
            pii_log += [dict(chunk_id=cid, **row) for row in log]
            chunks.append(Chunk(chunk_id=cid, doc_id=d.doc_id, title=d.title, room=d.room,
                                classification=d.classification, doc_sha256=d.sha256, char_start=m.start(),
                                char_end=m.end(), text=red, pii_redacted=len(log),
                                suspected_injection=bool(INJECTION.search(red)), chunker_version=REGISTRY["chunker"]))
    iv = hashlib.sha256("|".join(f"{c.chunk_id}:{c.doc_sha256}:{c.char_start}" for c in chunks).encode()).hexdigest()[:10]
    for c in chunks:
        c.index_version = f"idx-{iv}"
    return chunks, pii_log


def build() -> dict:
    docs, rejects = load()
    chunks, pii_log = chunk(docs)
    return dict(docs=docs, rejects=rejects, chunks=chunks, pii_log=pii_log,
                index_version=chunks[0].index_version if chunks else "idx-empty")
