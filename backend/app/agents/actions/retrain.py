from app.agents.actions.base import run_action


def run_retrain(payload_dict: dict) -> None:
    run_action("retrain", payload_dict, require_approver=True)
