import pandas as pd

from core.config import SERVICES
from simulator.telemetry import generate_timeseries

END = pd.Timestamp("2026-01-01 12:00")


def test_shape_and_columns():
    df = generate_timeseries("Normal Operations", minutes=30, seed=1, end=END)
    assert len(df) == 30 * len(SERVICES)
    assert {"cpu", "memory", "latency", "error_rate", "requests", "is_fault"} <= set(df.columns)


def test_reproducible_with_seed():
    a = generate_timeseries("Database Overload", seed=5, end=END)
    b = generate_timeseries("Database Overload", seed=5, end=END)
    pd.testing.assert_frame_equal(a, b)


def test_normal_has_no_fault_labels():
    assert not generate_timeseries("Normal Operations", seed=1, end=END)["is_fault"].any()


def test_failure_cascades_to_dependents_only():
    df = generate_timeseries("Database Overload", seed=1, end=END)
    faulted = set(df.loc[df["is_fault"], "service"])
    assert "Database" in faulted and "Payment Service" in faulted
    assert "Notification Service" not in faulted
    assert set(df.loc[df["is_root"], "service"]) == {"Database"}
