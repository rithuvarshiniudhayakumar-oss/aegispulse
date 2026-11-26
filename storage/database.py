"""SQLite persistence for incidents."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    scenario TEXT NOT NULL,
    severity TEXT NOT NULL,
    risk_score REAL NOT NULL,
    root_cause TEXT NOT NULL,
    affected_services TEXT NOT NULL,
    recommendation TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN'
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_dict(row) -> dict:
    d = dict(row)
    d["affected_services"] = json.loads(d["affected_services"])
    return d


class Database:
    def __init__(self, path: str):
        self.path = path
        with self._connect() as conn:
            conn.execute(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_incident(self, *, scenario, severity, risk_score, root_cause,
                        affected_services, recommendation) -> int:
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO incidents (created_at, updated_at, scenario, severity, risk_score,"
                " root_cause, affected_services, recommendation) VALUES (?,?,?,?,?,?,?,?)",
                (now, now, scenario, severity, float(risk_score), root_cause,
                 json.dumps(affected_services), recommendation),
            )
            return cur.lastrowid

    def get_incident(self, incident_id: int):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        return _to_dict(row) if row else None

    def list_incidents(self, status=None, limit=100) -> list:
        query, params = "SELECT * FROM incidents", []
        if status:
            query += " WHERE status=?"
            params.append(status)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            return [_to_dict(r) for r in conn.execute(query, params).fetchall()]

    def find_active_incident(self, root_cause: str):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM incidents WHERE root_cause=? AND status IN ('OPEN','ACKNOWLEDGED')"
                " ORDER BY id DESC LIMIT 1", (root_cause,)).fetchone()
        return _to_dict(row) if row else None

    def update_status(self, incident_id: int, status: str) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE incidents SET status=?, updated_at=?, "
                "resolved_at=CASE WHEN ?='RESOLVED' THEN ? ELSE resolved_at END WHERE id=?",
                (status, now, status, now, incident_id))
