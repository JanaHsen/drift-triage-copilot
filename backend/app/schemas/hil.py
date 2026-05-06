from pydantic import BaseModel


class HILApproveRequest(BaseModel):
    approver_user_id: str


class HILRejectRequest(BaseModel):
    approver_user_id: str
    reason: str | None = None
