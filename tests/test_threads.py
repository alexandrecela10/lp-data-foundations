"""The demo caches one Store for every visitor, so sessions query it from several threads at once.

One DuckDB connection used from two threads at once crashes the process (segmentation fault),
which took the hosted demo down on 14 November 2026. Each thread must get its own cursor.
"""
import threading

from answerdesk import access, interfaces
from answerdesk.foundations import ARMS
from answerdesk.foundations.sql_arm import warehouse


def test_each_thread_gets_its_own_cursor(store):
    seen = {}

    def grab(i):
        seen[i] = (store.con, access.role_db(store, "analyst"), warehouse(store, "analyst"))

    ts = [threading.Thread(target=grab, args=(i,)) for i in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    for slot in range(3):
        assert len({id(v[slot]) for v in seen.values()}) == 4
    assert store.con is store.con  # same thread, same cursor


def test_concurrent_questions_on_one_store(store):
    expected = {a: interfaces.chat(store, "How exposed are we to Calder Packaging?", arm=a)[0].value for a in ARMS}
    errors, got = [], []

    def ask(arm):
        try:
            for _ in range(3):
                got.append((arm, interfaces.chat(store, "How exposed are we to Calder Packaging?", arm=arm)[0].value))
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    # Daemon threads and a deadline: on macOS a shared connection deadlocks instead of crashing.
    ts = [threading.Thread(target=ask, args=(a,), daemon=True) for a in list(ARMS) * 2]
    [t.start() for t in ts]
    [t.join(timeout=120) for t in ts]
    assert not any(t.is_alive() for t in ts), "threads still running: likely a shared DuckDB connection"
    assert not errors
    assert all(v == expected[a] for a, v in got)
