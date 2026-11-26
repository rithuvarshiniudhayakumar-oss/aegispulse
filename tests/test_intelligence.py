import pytest

from intelligence.risk_scoring import classify_severity
from simulator.failures import SCENARIOS
from simulator.telemetry import generate_timeseries
from storage.database import Database
from incident.engine import IncidentEngine


def test_healthy_data_rarely_alerts(detector):
    scored = detector.score(generate_timeseries("Normal Operations", seed=7))
    assert scored["alert"].mean() < 0.02


def test_scores_are_absolute_not_relative(detector):
    scored = detector.score(generate_timeseries("Normal Operations", seed=7))
    assert scored["anomaly_score"].mean() < 25  # old prototype always showed a 100


@pytest.mark.parametrize("scenario", [n for n, f in SCENARIOS.items() if f.root])
def test_root_cause_identified(detector, tmp_path, scenario):
    engine = IncidentEngine(Database(str(tmp_path / "t.db")), detector)
    for seed in (1, 2, 3):
        assert engine.analyze(scenario, seed=seed)["root_cause"] == SCENARIOS[scenario].root


def test_normal_operations_creates_no_incident(detector, tmp_path):
    engine = IncidentEngine(Database(str(tmp_path / "t.db")), detector)
    assert engine.run_cycle("Normal Operations", seed=3)["incident_id"] is None


def test_severity_bands():
    assert classify_severity(90) == "CRITICAL"
    assert classify_severity(10) == "LOW"


def test_benchmark_regression_guard(detector, tmp_path):
    engine = IncidentEngine(Database(str(tmp_path / "t.db")), detector)
    report = engine.benchmark(n_seeds=3)
    assert report["detector_point_level"]["f1"] > 0.5
