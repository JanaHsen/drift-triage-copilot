import os

import httpx
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Investigations", layout="wide")
st.title("Investigations")
st.caption("Drift events the agent has opened or closed.")

col_a, col_b = st.columns([1, 4])
with col_a:
    status_filter = st.selectbox(
        "Status",
        options=["all", "open", "pending_approval", "resolved"],
        index=0,
    )
with col_b:
    if st.button("Refresh"):
        st.rerun()

params: dict[str, str | int] = {"limit": 100}
if status_filter != "all":
    params["status"] = status_filter

try:
    r = httpx.get(f"{BACKEND_URL}/v1/investigations", params=params, timeout=5.0)
    r.raise_for_status()
    items = r.json()
except httpx.HTTPError as exc:
    st.error(f"Could not reach backend at {BACKEND_URL}: {exc}")
    st.stop()

if not items:
    st.info("No investigations yet.")
    st.stop()

st.dataframe(
    items,
    use_container_width=True,
    column_order=[
        "created_at",
        "severity",
        "previous_severity",
        "status",
        "action_decided",
        "is_stale",
        "model_name",
        "model_version",
        "id",
    ],
)

st.divider()
st.subheader("Inspect one")
ids = [i["id"] for i in items]
selected_id = st.selectbox("Investigation ID", options=ids)
if selected_id:
    selected = next(i for i in items if i["id"] == selected_id)
    st.json(selected)
