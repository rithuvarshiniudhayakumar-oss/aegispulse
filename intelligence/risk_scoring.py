"""Heuristic risk scoring (0-100). Not a calibrated probability."""


def service_risk(anomaly_score, error_rate, latency, baseline_latency) -> float:
    error_factor = min(error_rate / 20, 1.0) * 100
    latency_factor = min(latency / (baseline_latency * 5), 1.0) * 100
    return round(0.5 * anomaly_score + 0.3 * error_factor + 0.2 * latency_factor, 2)


def incident_risk(service_risks: dict, n_anomalous: int) -> float:
    """Worst service risk, plus a small bonus for each additional anomalous service."""
    if not service_risks:
        return 0.0
    base = max(service_risks.values())
    return round(min(100.0, base + 5 * max(n_anomalous - 1, 0)), 2)


def classify_severity(risk: float) -> str:
    if risk >= 80:
        return "CRITICAL"
    if risk >= 60:
        return "HIGH"
    if risk >= 35:
        return "MEDIUM"
    return "LOW"
