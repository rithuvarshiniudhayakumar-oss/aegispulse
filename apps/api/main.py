"""AegisPulse FastAPI backend. Run: uvicorn apps.api.main:app --reload"""
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel

from core.config import get_db_path
from core.logging import get_logger
from incident.engine import IncidentEngine
from simulator.failures import SCENARIOS
from storage.database import Database

log = get_logger("aegispulse.api")
_state = {}

CYCLES = Counter("aegispulse_cycles_total", "Monitoring cycles executed", ["scenario"])
INCIDENTS = Counter("aegispulse_incidents_created_total", "Incidents created", ["severity"])
RISK = Gauge("aegispulse_last_risk_score", "Risk score of the most recent cycle")
CYCLE_SECONDS = Histogram("aegispulse_cycle_seconds", "Monitoring cycle duration")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["engine"] = IncidentEngine(Database(get_db_path()))
    log.info("AegisPulse engine ready")
    yield
    _state.clear()


app = FastAPI(
    title="AegisPulse API",
    version="0.2.0",
    description="Anomaly detection, risk scoring and root-cause ranking over simulated microservice telemetry.",
    lifespan=lifespan,
)


def _engine() -> IncidentEngine:
    if "engine" not in _state:
        raise HTTPException(503, "Engine not ready")
    return _state["engine"]


class SimulateRequest(BaseModel):
    scenario: str = "Normal Operations"
    seed: Optional[int] = None
    include_timeseries: bool = False


class StatusUpdate(BaseModel):
    status: Literal["ACKNOWLEDGED", "RESOLVED"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/scenarios")
def scenarios():
    return [{"name": f.name, "root_service": f.root} for f in SCENARIOS.values()]


@app.post("/simulate")
def simulate(req: SimulateRequest):
    if req.scenario not in SCENARIOS:
        raise HTTPException(422, f"Unknown scenario. Choose from {list(SCENARIOS)}")
    with CYCLE_SECONDS.time():
        result = _engine().run_cycle(req.scenario, req.seed, req.include_timeseries)
    CYCLES.labels(req.scenario).inc()
    RISK.set(result["risk_score"])
    if result["incident_id"] and not result["deduplicated"]:
        INCIDENTS.labels(result["severity"]).inc()
    return result


@app.get("/incidents")
def list_incidents(status: Optional[Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]] = None,
                   limit: int = Query(100, ge=1, le=1000)):
    return _engine().db.list_incidents(status, limit)


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    incident = _engine().db.get_incident(incident_id)
    if incident is None:
        raise HTTPException(404, "Incident not found")
    return incident


@app.patch("/incidents/{incident_id}/status")
def update_status(incident_id: int, body: StatusUpdate):
    try:
        return _engine().transition(incident_id, body.status)
    except KeyError:
        raise HTTPException(404, "Incident not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.get("/benchmark")
def benchmark(seeds: int = Query(5, ge=1, le=20)):
    return _engine().benchmark(seeds)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
