from typing import Any, Literal

from pydantic import BaseModel, model_validator

ActionType = Literal["replay", "retrain", "rollback"]


class ActionRequest(BaseModel):
    schema_version: str = "1.0"
    investigation_id: str
    approver_user_id: str | None = None
    target_model_uri: str
    action: ActionType
    payload: dict[str, Any] = {}

    @model_validator(mode="after")
    def require_approver_for_destructive_actions(self) -> "ActionRequest":
        if self.action in ("retrain", "rollback") and not self.approver_user_id:
            raise ValueError("approver_user_id is required for retrain and rollback")
        return self


class ActionResponse(BaseModel):
    accepted: bool
    job_id: str | None = None
    message: str
