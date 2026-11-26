"""Healthy behaviour profile of each simulated microservice."""
from dataclasses import dataclass

import networkx as nx

from core.config import DEPENDENCIES, SERVICES


@dataclass(frozen=True)
class ServiceProfile:
    """(mean, std) of each metric while the service is healthy."""
    cpu: tuple
    memory: tuple
    latency: tuple
    error_rate: tuple
    requests: tuple


PROFILES = {
    "API Gateway": ServiceProfile(cpu=(30, 5), memory=(45, 4), latency=(60, 10),
                                  error_rate=(0.4, 0.2), requests=(800, 80)),
    "Payment Service": ServiceProfile(cpu=(38, 6), memory=(55, 5), latency=(140, 20),
                                      error_rate=(0.5, 0.25), requests=(300, 35)),
    "User Service": ServiceProfile(cpu=(32, 5), memory=(50, 5), latency=(90, 15),
                                   error_rate=(0.4, 0.2), requests=(500, 50)),
    "Database": ServiceProfile(cpu=(42, 6), memory=(60, 4), latency=(25, 5),
                               error_rate=(0.1, 0.05), requests=(900, 90)),
    "Notification Service": ServiceProfile(cpu=(22, 4), memory=(40, 4), latency=(200, 30),
                                           error_rate=(0.8, 0.3), requests=(150, 20)),
}


def build_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(SERVICES)
    graph.add_edges_from(DEPENDENCIES)
    return graph
