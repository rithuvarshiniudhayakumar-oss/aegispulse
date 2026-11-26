"""Central configuration and service topology."""
import os
from pathlib import Path

SERVICES = [
    "API Gateway",
    "Payment Service",
    "User Service",
    "Database",
    "Notification Service",
]

# Edge A -> B means "A depends on B".
DEPENDENCIES = [
    ("API Gateway", "Payment Service"),
    ("API Gateway", "User Service"),
    ("Payment Service", "Database"),
    ("User Service", "Database"),
    ("Payment Service", "Notification Service"),
]

METRICS = ["cpu", "memory", "latency", "error_rate", "requests"]

WINDOW_MINUTES = 5        # recent window used for incident decisions
PERSISTENCE_RATIO = 0.6   # share of the window that must be anomalous


def get_db_path() -> str:
    path = Path(os.getenv("AEGISPULSE_DB", "data/aegispulse.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)
