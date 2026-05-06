from pydantic import BaseModel


class JobPayload(BaseModel):
    investigation_id: str
    action: str
    model_uri: str
    idempotency_key: str
    approver_user_id: str | None = None
