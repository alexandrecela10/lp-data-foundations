"""Pure metric functions, the registry, and every governed metric against known answers."""
import datetime as dt

import pytest

from answerdesk import truth as T
from answerdesk.semantic import fin
from answerdesk.semantic.layer import MetricRequest, SemanticLayer, changes_since, registry
from answerdesk.world import PACK_DATE, TODAY


def test_xirr_known_case():
    # -100 today, +110 in exactly one year: 10%
    r = fin.xirr([(dt.date(2025, 1, 1), -100), (dt.date(2026, 1, 1), 110)])
    assert abs(r - 0.10) < 0.002
    assert fin.xirr([(dt.date(2025, 1, 1), 100)]) is None          # no sign change: not meaningful


def test_unfunded_versions_differ_by_recallable():
    flows = [dict(kind="call", amount=60, recallable=0, value_date=dt.date(2024, 1, 1)),
             dict(kind="dist", amount=20, recallable=5, value_date=dt.date(2025, 1, 1))]
    assert fin.unfunded(100, flows, 1) == 40
    assert fin.unfunded(100, flows, 2) == 45


def test_call_rate_and_plan_curve():
    assert fin.call_rate(1.0) == 0.35 and fin.call_rate(3.0) == 0.25 and fin.call_rate(5.0) == 0.12 and fin.call_rate(9) == 0.05
    assert fin.plan_tvpi(2.0, 1.0) == 1.0 and fin.plan_tvpi(2.0, 6.0) == 1.5 and fin.plan_tvpi(2.0, 12) == 2.0


def test_every_metric_has_owner_version_and_plain_definition():
    for name, m in registry()["metrics"].items():
        assert m["owner"], name
        assert m["versions"], name
        for v, spec in m["versions"].items():
            assert spec["plain"] and len(spec["plain"].split()) >= 4, (name, v)


def test_changes_since_last_pack():
    assert {c["metric"] for c in changes_since(dt.date(2026, 6, 30))} == {"unfunded"}


@pytest.fixture(scope="module")
def sl(store):
    return SemanticLayer(store, "head_of_pe", "resolved")


@pytest.mark.parametrize("d", [TODAY, dt.date(2026, 9, 5), dt.date(2026, 9, 9), dt.date(2026, 9, 10), dt.date(2026, 6, 30)])
def test_lookthrough_exposure_matches_truth(store, sl, d):
    got = sl.run(MetricRequest(metric="lookthrough_exposure", as_of=d, company="Calder Packaging")).numbers[0].value
    assert abs(got - T.exposure(store.world, "C0001", d)) < 0.005 * max(1, got)


def test_sector_exposure_matches_truth(store, sl):
    got = sl.run(MetricRequest(metric="lookthrough_exposure", as_of=TODAY, sector="Packaging", region="europe")).numbers[0].value
    assert abs(got - T.sector_exposure(store.world, "Packaging", TODAY, region="europe")) < 0.01


@pytest.mark.parametrize("metric,kind", [("net_tvpi", "tvpi"), ("net_dpi", "dpi")])
def test_pooled_ratios_match_truth(store, sl, metric, kind):
    w = store.world
    pids = T.our_funds(w, PACK_DATE, "buyout", (2019, 2021))
    got = sl.run(MetricRequest(metric=metric, as_of=PACK_DATE, strategy="buyout", vintage_from=2019, vintage_to=2021)).numbers[0].value
    assert abs(got - T.pooled(w, pids, PACK_DATE, kind)) < 0.002


def test_irr_unfunded_calls_match_truth(store, sl):
    w = store.world
    pids = T.our_funds(w, PACK_DATE, "buyout", (2019, 2021))
    q = dict(as_of=PACK_DATE, strategy="buyout", vintage_from=2019, vintage_to=2021)
    assert abs(sl.run(MetricRequest(metric="net_irr", **q)).numbers[0].value - T.pooled_irr(w, pids, PACK_DATE)) < 0.001
    for v in (1, 2):
        got = sl.run(MetricRequest(metric="unfunded", version=v, **q)).numbers[0].value
        assert abs(got - sum(T.unfunded(w, p, PACK_DATE, v) for p in pids)) < 0.01
    got = sl.run(MetricRequest(metric="calls_next_12m", **q)).numbers[0].value
    assert abs(got - sum(T.calls_next_12m(w, p, PACK_DATE) for p in pids)) < 0.01


def test_unknown_metric_is_refused(sl):
    r = sl.run(MetricRequest(metric="pme", as_of=TODAY))
    assert r.refused and "No governed definition" in r.reason


def test_two_definitions_two_answers(store, sl):
    v1 = sl.run(MetricRequest(metric="lookthrough_exposure", version=1, as_of=TODAY, company="Calder Packaging")).numbers[0].value
    v2 = sl.run(MetricRequest(metric="lookthrough_exposure", as_of=TODAY, company="Calder Packaging")).numbers[0].value
    assert abs(v1 - T.exposure_v1_commitment(store.world, "C0001", TODAY)) < 0.01
    assert abs(v1 - v2) > 0.05 * v2
