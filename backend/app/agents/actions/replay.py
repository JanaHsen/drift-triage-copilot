from app.agents.actions.base import run_action


def run_replay(payload_dict: dict) -> None:
    run_action("replay", payload_dict, require_approver=False)
