import os

import httpx
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
PLATFORM_URL = os.environ.get("PLATFORM_URL", "http://localhost:8001")

st.set_page_config(page_title="Drift Triage Co-Pilot", layout="wide")
st.title("Drift Triage Co-Pilot")
st.caption("Self-healing MLOps stack — model + agent + queue + dashboard")

st.markdown(
    """
Use the sidebar to navigate:

- **Registry** — currently loaded model info
- **Investigations** — open and resolved drift investigations
- **HIL Inbox** — pending human approvals
- **Queue** — job queue depth and dead-letter queue
- **Demo Controls** — inject drift, trigger detection
"""
)

st.divider()
st.subheader("Quick status")

col1, col2, col3 = st.columns(3)


def _try(url: str, timeout: float = 3.0) -> dict | None:
    try:
        r = httpx.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


with col1:
    info = _try(f"{PLATFORM_URL}/v1/model/info")
    if info:
        st.metric("Model", f"{info['model_name']} v{info['model_version']}")
    else:
        st.metric("Model", "unavailable")

with col2:
    qs = _try(f"{BACKEND_URL}/v1/queue/stats")
    st.metric("Queue depth", qs["queue_depth"] if qs else "—")

with col3:
    st.metric("DLQ depth", qs["dlq_depth"] if qs else "—")
