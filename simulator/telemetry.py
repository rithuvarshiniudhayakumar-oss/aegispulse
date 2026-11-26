"""Time-series telemetry generation with ground-truth fault labels."""
import numpy as np
import pandas as pd

from core.config import METRICS, SERVICES
from simulator.failures import CASCADE_ERROR, CASCADE_LATENCY, SCENARIOS, attenuation_map
from simulator.services import PROFILES


def _apply_failure(values, failure, is_root, attenuation, ramp):
    if is_root:
        values["cpu"] += failure.cpu_add * ramp
        values["memory"] += failure.memory_add * ramp
        values["latency"] *= 1 + (failure.latency_mult - 1) * ramp
        values["error_rate"] += failure.error_add * ramp
        values["requests"] *= 1 - (1 - failure.requests_mult) * ramp
    else:
        values["latency"] *= 1 + (failure.latency_mult - 1) * attenuation * CASCADE_LATENCY * ramp
        values["error_rate"] += failure.error_add * attenuation * CASCADE_ERROR * ramp


def generate_timeseries(scenario="Normal Operations", minutes=60, fault_start=40,
                        seed=None, end=None) -> pd.DataFrame:
    """One row per service per minute. The fault begins at minute `fault_start`
    and ramps to full strength over 3 minutes. `is_fault` / `is_root` are labels."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    rng = np.random.default_rng(seed)
    failure = SCENARIOS[scenario]
    attenuation = attenuation_map(failure)
    end = end if end is not None else pd.Timestamp.now().floor("min")
    start = end - pd.Timedelta(minutes=minutes)

    rows = []
    for svc in SERVICES:
        profile = PROFILES[svc]
        att = attenuation.get(svc, 0.0)
        for t in range(minutes):
            values = {m: float(rng.normal(*getattr(profile, m))) for m in METRICS}
            faulted = att > 0 and t >= fault_start
            is_root = faulted and svc == failure.root
            if faulted:
                ramp = min(1.0, (t - fault_start + 1) / 3)
                _apply_failure(values, failure, svc == failure.root, att, ramp)
            rows.append({
                "timestamp": start + pd.Timedelta(minutes=t),
                "service": svc,
                **values,
                "is_fault": faulted,
                "is_root": is_root,
            })

    df = pd.DataFrame(rows)
    df["cpu"] = df["cpu"].clip(0, 100)
    df["memory"] = df["memory"].clip(0, 100)
    df["latency"] = df["latency"].clip(1, None)
    df["error_rate"] = df["error_rate"].clip(0, 100)
    df["requests"] = df["requests"].clip(0, None)
    df[METRICS] = df[METRICS].round(3)
    return df
