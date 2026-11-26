"""Failure scenarios. A fault starts at one root service and cascades to
every service that (transitively) depends on it, with attenuation."""
from dataclasses import dataclass

import networkx as nx

from simulator.services import build_graph


@dataclass(frozen=True)
class Failure:
    name: str
    root: "str | None"
    cpu_add: float = 0.0
    memory_add: float = 0.0
    latency_mult: float = 1.0
    error_add: float = 0.0
    requests_mult: float = 1.0


SCENARIOS = {
    f.name: f
    for f in [
        Failure("Normal Operations", None),
        Failure("Database Overload", "Database", cpu_add=45, memory_add=30,
                latency_mult=20.0, error_add=12, requests_mult=0.7),
        Failure("Payment Service Failure", "Payment Service", cpu_add=40,
                latency_mult=6.0, error_add=15, requests_mult=0.6),
        Failure("API Gateway Degradation", "API Gateway", cpu_add=45, memory_add=20,
                latency_mult=10.0, error_add=10, requests_mult=0.6),
        Failure("Notification Failure", "Notification Service", cpu_add=15,
                latency_mult=5.0, error_add=18, requests_mult=0.5),
    ]
}

CASCADE_LATENCY = 0.2  # share of latency effect propagated to callers
CASCADE_ERROR = 0.3    # share of error-rate effect propagated to callers


def attenuation_map(failure: Failure) -> dict:
    """service -> attenuation (1.0 for the root, 0.5**distance for dependents)."""
    if failure.root is None:
        return {}
    graph = build_graph()
    result = {failure.root: 1.0}
    for svc in nx.ancestors(graph, failure.root):
        distance = nx.shortest_path_length(graph, svc, failure.root)
        result[svc] = 0.5 ** distance
    return result
