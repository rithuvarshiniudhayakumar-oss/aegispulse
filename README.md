# AegisPulse

Incident intelligence for microservices: simulates telemetry, detects anomalies,
scores risk, ranks likely root causes using the service dependency graph, and
tracks incidents through a lifecycle (OPEN, ACKNOWLEDGED, RESOLVED).

## Architecture

```
Simulator -> Isolation Forest -> Risk scoring -> Root-cause ranking -> Incident engine
                                                                          |
                                         FastAPI (+ /metrics) <-> SQLite  |
                                                 |                        |
                                   Streamlit dashboard           Prometheus
```

- **Simulator**: 5 services with healthy baselines and failure scenarios that cascade through dependencies, with ground-truth labels.
- **Detection**: one Isolation Forest per service, trained on healthy data. Scores are absolute (0-100), not relative to other services.
- **Root cause**: heuristic ranking that favours services many anomalous services depend on.
- **Incidents**: deduplicated by root cause, with validated status transitions.
- **Observability**: Prometheus metrics at `/metrics`.

## Run with Docker

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:8501 |
| API docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn apps.api.main:app --reload
streamlit run apps/dashboard/app.py
pytest -q
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Liveness |
| GET | /scenarios | Available failure scenarios |
| POST | /simulate | Run a monitoring cycle |
| GET | /incidents | List incidents |
| PATCH | /incidents/{id}/status | Acknowledge or resolve |
| GET | /benchmark | Evaluate detector and root cause |
| GET | /metrics | Prometheus metrics |

## Benchmark

<!-- BENCHMARK:START -->
Run `python scripts/run_benchmark.py` to fill this in.
<!-- BENCHMARK:END -->

## Limitations

Training and test data come from the same simulator, so these numbers are optimistic compared with real infrastructure. Root-cause ranking is a heuristic, not causal proof, and recommendations are simulated, never executed.
