import os

import httpx
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Queue", layout="wide")
st.title("Queue")
st.caption("Redis-backed action queue with dead-letter queue.")

if st.button("Refresh"):
    st.rerun()

try:
    r = httpx.get(f"{BACKEND_URL}/v1/queue/stats", timeout=5.0)
    r.raise_for_status()
    stats = r.json()
except httpx.HTTPError as exc:
    st.error(f"Could not reach backend at {BACKEND_URL}: {exc}")
    st.stop()

col1, col2 = st.columns(2)
col1.metric("Queue depth", stats["queue_depth"])
col2.metric("DLQ depth", stats["dlq_depth"])

st.divider()
st.subheader("Queued jobs")
if stats["jobs"]:
    st.dataframe(stats["jobs"], use_container_width=True)
else:
    st.info("No jobs queued.")

st.subheader("Dead-letter queue")
if stats["dlq_jobs"]:
    st.dataframe(stats["dlq_jobs"], use_container_width=True)
else:
    st.info("DLQ is empty.")
