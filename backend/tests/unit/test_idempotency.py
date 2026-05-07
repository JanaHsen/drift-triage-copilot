from app.services.idempotency import compute_key


def test_compute_key_is_deterministic():
    k1 = compute_key("inv-001", "retrain", "models:/bank-churn/3")
    k2 = compute_key("inv-001", "retrain", "models:/bank-churn/3")
    assert k1 == k2


def test_compute_key_different_investigation_ids():
    k1 = compute_key("inv-001", "retrain", "models:/bank-churn/3")
    k2 = compute_key("inv-002", "retrain", "models:/bank-churn/3")
    assert k1 != k2


def test_compute_key_different_actions():
    k1 = compute_key("inv-001", "retrain", "models:/bank-churn/3")
    k2 = compute_key("inv-001", "rollback", "models:/bank-churn/3")
    assert k1 != k2


def test_compute_key_different_model_uris():
    k1 = compute_key("inv-001", "retrain", "models:/bank-churn/3")
    k2 = compute_key("inv-001", "retrain", "models:/bank-churn/4")
    assert k1 != k2


def test_compute_key_is_sha256_hex():
    key = compute_key("inv-001", "retrain", "models:/bank-churn/3")
    assert len(key) == 64
    int(key, 16)  # raises ValueError if not valid hex
