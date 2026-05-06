import hashlib


def compute_key(investigation_id: str, action: str, model_uri: str) -> str:
    raw = f"{investigation_id}:{action}:{model_uri}"
    return hashlib.sha256(raw.encode()).hexdigest()
