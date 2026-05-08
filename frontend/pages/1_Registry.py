import os

import httpx
import streamlit as st

PLATFORM_URL = os.environ.get("PLATFORM_URL", "http://localhost:8001")

st.set_page_config(page_title="Registry", layout="wide")
st.title("Registry")
st.caption("Currently loaded model in the platform service.")

if st.button("Refresh"):
    st.rerun()

try:
    r = httpx.get(f"{PLATFORM_URL}/v1/model/info", timeout=5.0)
    r.raise_for_status()
    info = r.json()
except httpx.HTTPError as exc:
    st.error(f"Could not reach platform at {PLATFORM_URL}: {exc}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Name", info["model_name"])
col2.metric("Version", info["model_version"])
col3.metric("URI", info["model_uri"])

st.divider()
st.subheader("Promotion")
st.info(
    "Promotion is gated by the day-4 checklist and goes through the agent's HIL flow. "
    "Approvals appear in the **HIL Inbox** page."
)
