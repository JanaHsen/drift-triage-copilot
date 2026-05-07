from app.agents.actions.base import run_action


def run_rollback(payload_dict: dict) -> None:
    run_action("rollback", payload_dict, require_approver=True)
