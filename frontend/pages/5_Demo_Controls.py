import asyncio
import os

import httpx
import streamlit as st

PLATFORM_URL = os.environ.get("PLATFORM_URL", "http://localhost:8001")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")

st.set_page_config(page_title="Demo Controls", layout="wide")
st.title("Demo Controls")
st.caption("Inject shifted predictions and trigger drift detection on demand.")

if not AGENT_TOKEN:
    st.warning("AGENT_TOKEN env var is empty — predict and drift-check calls will be unauthorized.")

auth_headers = {"Authorization": f"Bearer {AGENT_TOKEN}"} if AGENT_TOKEN else {}

# Pre-baked shifted row — euribor3m training mean ≈ 3.8, cons.price.idx ≈ 93.6.
# Drops below the rolling baseline so PSI flags drift.
SHIFTED_ROW = {
    "age": 35,
    "job": "admin.",
    "marital": "married",
    "education": "university.degree",
    "default": "no",
    "housing": "yes",
    "loan": "no",
    "contact": "cellular",
    "month": "may",
    "day_of_week": "mon",
    "campaign": 1,
    "pdays": 999,
    "previous": 0,
    "poutcome": "nonexistent",
    "emp.var.rate": -3.4,
    "cons.price.idx": 90.0,
    "cons.conf.idx": -50.0,
    "euribor3m": 0.5,
    "nr.employed": 4963.6,
}

with st.expander("PSI thresholds (rough guide)"):
    st.markdown(
        """
| N requests | Expected PSI | Severity | Action |
|---|---|---|---|
| ~50 | < 0.1 | low | no-op |
| ~100 | 0.1–0.25 | medium | replay |
| ~150 | 0.25–0.5 | high | retrain (HIL) |
| ~200 | ≥ 0.5 | critical | rollback (HIL) |
"""
    )

n = st.number_input("Prediction requests to inject", value=200, step=50, min_value=10)

col1, col2 = st.columns(2)


async def _flood(n_requests: int) -> tuple[int, int]:
    successes = 0
    failures = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        async def _one() -> bool:
            try:
                resp = await client.post(
                    f"{PLATFORM_URL}/predict",
                    json=SHIFTED_ROW,
                    headers=auth_headers,
                )
                return resp.status_code == 200
            except httpx.HTTPError:
                return False

        results = await asyncio.gather(*[_one() for _ in range(n_requests)])
    successes = sum(1 for r in results if r)
    failures = n_requests - successes
    return successes, failures


with col1:
    if st.button("Inject Drift", use_container_width=True, type="primary"):
        with st.spinner(f"Sending {n} shifted predictions..."):
            ok, fail = asyncio.run(_flood(int(n)))
        if fail == 0:
            st.success(f"Sent {ok} shifted predictions. Click 'Trigger Check Now' to detect.")
        else:
            st.warning(f"Sent {ok} ok / {fail} failed. Check platform logs.")

with col2:
    if st.button("Trigger Check Now", use_container_width=True):
        try:
            r = httpx.post(
                f"{PLATFORM_URL}/drift/check",
                headers=auth_headers,
                timeout=10.0,
            )
            if r.status_code == 200:
                payload = r.json()
                st.success(
                    f"Drift check ran — severity={payload['severity']}, "
                    f"prev={payload['previous_severity']}, "
                    f"webhook_emitted={payload['webhook_emitted']}"
                )
                st.json(payload)
            elif r.status_code == 409:
                st.warning(f"409 — empty window. Inject some predictions first. ({r.text})")
            else:
                st.error(f"Status {r.status_code}: {r.text}")
        except httpx.HTTPError as exc:
            st.error(f"Drift check failed: {exc}")
