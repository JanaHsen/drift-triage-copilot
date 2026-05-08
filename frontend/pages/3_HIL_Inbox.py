import os

import httpx
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")

st.set_page_config(page_title="HIL Inbox", layout="wide")
st.title("HIL Inbox")
st.caption("Pending human-in-the-loop approvals. Approving resumes the agent.")

if not AGENT_TOKEN:
    st.warning("AGENT_TOKEN env var is empty — approve/reject calls will be unauthorized.")

auth_headers = {"Authorization": f"Bearer {AGENT_TOKEN}"} if AGENT_TOKEN else {}

approver = st.text_input("Approver (your user id)", value="demo-user")

if st.button("Refresh"):
    st.rerun()

try:
    r = httpx.get(
        f"{BACKEND_URL}/v1/hil",
        params={"status": "pending"},
        timeout=5.0,
    )
    r.raise_for_status()
    items = r.json()
except httpx.HTTPError as exc:
    st.error(f"Could not reach backend at {BACKEND_URL}: {exc}")
    st.stop()

if not items:
    st.success("Inbox is empty — no pending approvals.")
    st.stop()

for item in items:
    with st.container(border=True):
        cols = st.columns([3, 1, 1])
        cols[0].markdown(
            f"**Action:** `{item['proposed_action']}`  \n"
            f"**Investigation:** `{item['investigation_id']}`  \n"
            f"**Created:** {item['created_at']}"
        )

        if cols[1].button("Approve", key=f"approve-{item['id']}", type="primary"):
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/v1/hil/{item['id']}/approve",
                    json={"approver_user_id": approver},
                    headers=auth_headers,
                    timeout=10.0,
                )
                resp.raise_for_status()
                st.success(f"Approved — {resp.json()}")
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Approve failed: {exc}")

        if cols[2].button("Reject", key=f"reject-{item['id']}"):
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/v1/hil/{item['id']}/reject",
                    json={"approver_user_id": approver},
                    headers=auth_headers,
                    timeout=10.0,
                )
                resp.raise_for_status()
                st.warning(f"Rejected — {resp.json()}")
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Reject failed: {exc}")
