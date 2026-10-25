"""Roles and access. Every foundation reads a per-role copy of gold: restricted columns and
rows are absent, so no query (governed or AI-written) can reach them. Documents carry the roles
that may see them; search drops the rest. The role picker in the demo is a switch, not a login."""
from __future__ import annotations

import duckdb

ROLES = {
    "analyst": dict(label="Sara, portfolio analyst",
                    drop_columns={"positions": ["mgmt_fee_pct", "carry_pct"]},
                    drop_tables=["coinvest_fees", "planned"]),
    "head_of_pe": dict(label="Head of private equity", drop_columns={}, drop_tables=[]),
    "cio": dict(label="CIO", drop_columns={}, drop_tables=["planned"]),
}
WHO_CAN = {"coinvest_fees": "the head of private equity", "planned": "the head of private equity"}

_cache: dict = {}


def role_db(store, role: str) -> duckdb.DuckDBPyConnection:
    """A fresh in-memory database holding only what this role may see (schema `gold`)."""
    key = (id(store), role)
    if key in _cache:
        return _cache[key]
    rules = ROLES[role]
    con = duckdb.connect()
    con.execute("CREATE SCHEMA gold")
    tables = [r[0] for r in store.con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'gold'").fetchall()]
    for t in tables:
        if t in rules["drop_tables"]:
            continue
        cols = [r[0] for r in store.con.execute(f"DESCRIBE gold.{t}").fetchall()]
        keep = [c for c in cols if c not in rules["drop_columns"].get(t, [])]
        arrow = store.con.execute(f"SELECT {', '.join(keep)} FROM gold.{t}").arrow()
        con.register("_t", arrow)
        con.execute(f"CREATE TABLE gold.{t} AS SELECT * FROM _t")
        con.unregister("_t")
    _cache[key] = con
    return con


def can_see_doc(restricted_to: str | tuple, role: str) -> bool:
    if not restricted_to:
        return True
    roles = restricted_to.split(",") if isinstance(restricted_to, str) else restricted_to
    return role in roles


def visible(role: str, table: str) -> bool:
    return table not in ROLES[role]["drop_tables"]
