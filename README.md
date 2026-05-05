# Drift Triage Co-Pilot

Self-healing MLOps stack: model service + LangGraph supervisor agent + Redis queue + Streamlit dashboard.

Built for AIE Bootcamp Week 5.

## Stack
- FastAPI + MLflow for the model service
- LangGraph supervisor (triage / action / comms) with Postgres checkpoints
- Redis queue + DLQ for slow tools (replay test, retrain, rollback)
- Streamlit dashboard surfacing registry state, investigations, queue depth, HIL approvals

## Setup
```bash
cp .env.example .env
# Fill in secrets
docker compose up
```

## Docs
- `ARCH.md` — architecture and contracts
- `DECISIONS.md` — design decisions and trade-offs
- `RUNBOOK.md` — how to operate the system