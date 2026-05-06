from typing import Any, Literal

from pydantic import BaseModel

ActionType = Literal["replay", "retrain", "rollback"]


class ActionRequest(BaseModel):
    investigation_id: str
    approver_user_id: str | None = None
    target_model_uri: str
    payload: dict[str, Any] = {}


class ActionResponse(BaseModel):
    accepted: bool
    job_id: str | None = None
    message: str
