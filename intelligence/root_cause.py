"""Dependency-aware root-cause ranking. A heuristic, not causal proof.

A service ranks higher when many other anomalous services depend on it, and
lower when it depends on another anomalous service (that one is the likelier source)."""
import networkx as nx


def rank_root_causes(anomalous: dict, graph: nx.DiGraph) -> list:
    """anomalous: service -> mean anomaly score. Returns candidates, best first.
    `share` is the candidate's fraction of total score, not a probability."""
    if not anomalous:
        return []
    names = set(anomalous)
    raw = {}
    for svc, score in anomalous.items():
        dependents = nx.ancestors(graph, svc) & names
        dependencies = nx.descendants(graph, svc) & names
        value = max(score, 1.0) * (1 + len(dependents))
        value *= 0.5 ** len(dependencies)
        raw[svc] = value
    total = sum(raw.values())
    ranked = sorted(raw.items(), key=lambda kv: kv[1], reverse=True)
    return [{"service": s, "score": round(v, 2), "share": round(v / total, 3)} for s, v in ranked]
