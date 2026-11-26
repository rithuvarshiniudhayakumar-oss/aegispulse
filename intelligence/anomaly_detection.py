"""Per-service Isolation Forest trained on a synthetic healthy baseline.

Scores are ABSOLUTE: 0-100 where 50 equals the 99.5th percentile of healthy
training scores. They do not depend on other services in the snapshot."""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from core.config import METRICS
from simulator.telemetry import generate_timeseries


@dataclass
class _ServiceModel:
    scaler: StandardScaler
    model: IsolationForest
    lo: float   # median healthy raw score
    thr: float  # anomaly threshold on raw score


class AnomalyDetector:
    def __init__(self, threshold_quantile=0.995, n_estimators=100, seed=42):
        self.threshold_quantile = threshold_quantile
        self.n_estimators = n_estimators
        self.seed = seed
        self.models = {}

    def fit(self, healthy: pd.DataFrame) -> "AnomalyDetector":
        for svc, grp in healthy.groupby("service"):
            X = grp[METRICS].to_numpy()
            scaler = StandardScaler().fit(X)
            Xs = scaler.transform(X)
            model = IsolationForest(n_estimators=self.n_estimators,
                                    random_state=self.seed).fit(Xs)
            train_raw = -model.score_samples(Xs)
            self.models[svc] = _ServiceModel(
                scaler, model,
                float(np.median(train_raw)),
                float(np.quantile(train_raw, self.threshold_quantile)),
            )
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.sort_values(["service", "timestamp"]).reset_index(drop=True)
        raw = np.zeros(len(out))
        for svc, idx in out.groupby("service").indices.items():
            m = self.models[svc]
            X = m.scaler.transform(out.loc[idx, METRICS].to_numpy())
            raw[idx] = -m.model.score_samples(X)
        lo = out["service"].map({s: m.lo for s, m in self.models.items()}).to_numpy()
        thr = out["service"].map({s: m.thr for s, m in self.models.items()}).to_numpy()
        out["anomaly_raw"] = raw
        out["anomaly_score"] = np.clip(50 * (raw - lo) / np.maximum(thr - lo, 1e-9), 0, 100).round(2)
        out["is_anomaly"] = raw > thr
        # Alert = at least 2 anomalous points in the last 3 minutes (suppresses one-off blips).
        out["alert"] = out.groupby("service")["is_anomaly"].transform(
            lambda s: s.astype(int).rolling(3, min_periods=1).sum() >= 2
        )
        return out


@lru_cache(maxsize=1)
def build_default_detector(seed: int = 42) -> AnomalyDetector:
    healthy = generate_timeseries("Normal Operations", minutes=2000, seed=seed)
    return AnomalyDetector(seed=seed).fit(healthy)
