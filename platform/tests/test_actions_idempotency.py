from app.routers.actions import _derive_idempotency_key
from contracts.v1.actions import ActionRequest


def _action(**overrides):
    base = {
        "investigation_id": "inv-001",
        "approver_user_id": "jana@bootcamp",
        "target_model_uri": "models:/bank-marketing-classifier/1",
        "action": "retrain",
        "payload": {"reason": "smoke test"},
    }
    base.update(overrides)
    return ActionRequest.model_validate(base)


def test_identical_requests_share_key():
    a, b = _action(), _action()
    assert _derive_idempotency_key(a) == _derive_idempotency_key(b)


def test_different_investigation_id_changes_key():
    a = _action(investigation_id="inv-001")
    b = _action(investigation_id="inv-002")
    assert _derive_idempotency_key(a) != _derive_idempotency_key(b)


def test_different_action_changes_key():
    a = _action(action="replay")
    b = _action(action="retrain")
    assert _derive_idempotency_key(a) != _derive_idempotency_key(b)


def test_different_target_model_uri_changes_key():
    a = _action(target_model_uri="models:/bank-marketing-classifier/1")
    b = _action(target_model_uri="models:/bank-marketing-classifier/2")
    assert _derive_idempotency_key(a) != _derive_idempotency_key(b)


def test_payload_is_not_part_of_key():
    a = _action(payload={"reason": "smoke test"})
    b = _action(payload={"reason": "different note"})
    assert _derive_idempotency_key(a) == _derive_idempotency_key(b)


def test_approver_is_not_part_of_key():
    a = _action(action="replay", approver_user_id=None)
    b = _action(action="replay", approver_user_id="rasha@bootcamp")
    assert _derive_idempotency_key(a) == _derive_idempotency_key(b)
