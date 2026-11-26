"""Detector evaluation against simulator ground truth.

Caveat: train and test data come from the same simulator, so these numbers
are optimistic compared with real infrastructure."""
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from simulator.failures import SCENARIOS
from simulator.telemetry import generate_timeseries


def evaluate_detector(detector, seeds, column="is_anomaly") -> dict:
    y_true, y_pred = [], []
    for name in SCENARIOS:
        for seed in seeds:
            scored = detector.score(generate_timeseries(name, seed=seed))
            y_true += scored["is_fault"].astype(int).tolist()
            y_pred += scored[column].astype(int).tolist()
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "precision": round(float(p), 3),
        "recall": round(float(r), 3),
        "f1": round(float(f), 3),
        "false_positive_rate": round(float(fp / max(fp + tn, 1)), 4),
        "samples": int(len(y_true)),
        "confusion": {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)},
    }
