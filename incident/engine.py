"""Orchestrates simulation -> detection -> risk -> root cause -> incident."""
from core.config import PERSISTENCE_RATIO, SERVICES, WINDOW_MINUTES
from core.logging import get_logger
from intelligence.anomaly_detection import build_default_detector
from intelligence.evaluation import evaluate_detector
from intelligence.risk_scoring import classify_severity, incident_risk, service_risk
from intelligence.root_cause import rank_root_causes
from simulator.failures import SCENARIOS
from simulator.services import PROFILES, build_graph
from simulator.telemetry import generate_timeseries
from storage.database import Database

log = get_logger(__name__)

RECOMMENDATIONS = {
    "Database": "Scale read replicas, review slow queries, cap connection pool.",
    "Payment Service": "Roll back last deployment, restart unhealthy instances, enable circuit breaker.",
    "API Gateway": "Add gateway instances, apply rate limiting, review upstream timeouts.",
    "User Service": "Scale out the service, check cache hit rate.",
    "Notification Service": "Pause retries, drain the queue, fail over to a backup provider.",
}

VALID_TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "RESOLVED"},
    "ACKNOWLEDGED": {"RESOLVED"},
    "RESOLVED": set(),
}


class IncidentEngine:
    def __init__(self, db: Database, detector=None):
        self.db = db
        self.detector = detector or build_default_detector()
        self.graph = build_graph()

    def analyze(self, scenario, seed=None, include_timeseries=False) -> dict:
        """Pure analysis, no persistence."""
        scored = self.detector.score(generate_timeseries(scenario, seed=seed))
        recent = scored.groupby("service").tail(WINDOW_MINUTES)
        stats = recent.groupby("service").agg(
            anomaly_ratio=("is_anomaly", "mean"),
            anomaly_score=("anomaly_score", "mean"),
            cpu=("cpu", "mean"),
            memory=("memory", "mean"),
            latency=("latency", "mean"),
            error_rate=("error_rate", "mean"),
            requests=("requests", "mean"),
        ).reindex(SERVICES)

        anomalous = {svc: float(r.anomaly_score) for svc, r in stats.iterrows()
                     if r.anomaly_ratio >= PERSISTENCE_RATIO}
        risks = {svc: service_risk(r.anomaly_score, r.error_rate, r.latency,
                                   PROFILES[svc].latency[0])
                 for svc, r in stats.iterrows()}
        risk = incident_risk(risks, len(anomalous))
        ranking = rank_root_causes(anomalous, self.graph)
        root = ranking[0]["service"] if ranking else None
        expected = SCENARIOS[scenario].root

        services = stats.round(3).reset_index().to_dict("records")
        for rec in services:
            rec["status"] = "ANOMALY" if rec["service"] in anomalous else "HEALTHY"

        result = {
            "scenario": scenario,
            "risk_score": risk,
            "severity": classify_severity(risk) if anomalous else "NONE",
            "anomalous_services": sorted(anomalous),
            "root_cause": root,
            "root_cause_ranking": ranking,
            "expected_root_cause": expected,
            "root_cause_correct": root == expected,
            "recommendation": (f"[SIMULATED, not executed] {RECOMMENDATIONS[root]}" if root else None),
            "services": services,
        }
        if include_timeseries:
            ts = scored.assign(timestamp=scored["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S"))
            result["timeseries"] = ts.round(3).to_dict("records")
        return result

    def run_cycle(self, scenario, seed=None, include_timeseries=False) -> dict:
        result = self.analyze(scenario, seed, include_timeseries)
        result["incident_id"] = None
        result["deduplicated"] = False
        root = result["root_cause"]
        if root:
            existing = self.db.find_active_incident(root)
            if existing:
                result["incident_id"] = existing["id"]
                result["deduplicated"] = True
            else:
                result["incident_id"] = self.db.create_incident(
                    scenario=scenario, severity=result["severity"],
                    risk_score=result["risk_score"], root_cause=root,
                    affected_services=result["anomalous_services"],
                    recommendation=result["recommendation"])
                log.info("Created incident %s (root=%s, severity=%s)",
                         result["incident_id"], root, result["severity"])
        return result

    def transition(self, incident_id: int, new_status: str) -> dict:
        incident = self.db.get_incident(incident_id)
        if incident is None:
            raise KeyError(incident_id)
        if new_status not in VALID_TRANSITIONS[incident["status"]]:
            raise ValueError(f"Cannot move {incident['status']} -> {new_status}")
        self.db.update_status(incident_id, new_status)
        return self.db.get_incident(incident_id)

    def benchmark(self, n_seeds: int = 5) -> dict:
        seeds = [1000 + s for s in range(n_seeds)]
        accuracy = {}
        for name, failure in SCENARIOS.items():
            if failure.root is None:
                continue
            hits = sum(self.analyze(name, seed=s)["root_cause"] == failure.root for s in seeds)
            accuracy[name] = round(hits / len(seeds), 3)
        false_alarms = sum(self.analyze("Normal Operations", seed=s)["root_cause"] is not None
                           for s in seeds)
        return {
            "detector_point_level": evaluate_detector(self.detector, seeds),
            "root_cause_top1_accuracy": accuracy,
            "normal_ops_false_alarm_rate": round(false_alarms / len(seeds), 3),
            "seeds": len(seeds),
            "note": "Synthetic train and test data from one simulator: optimistic estimate.",
        }
