import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session
from app.db.models import Investigation

router = APIRouter(prefix="/v1/investigations")


class InvestigationOut(BaseModel):
    id: uuid.UUID
    event_id: str
    model_name: str
    model_version: str
    model_uri_at_open: str
    severity: str
    previous_severity: str | None
    status: str
    action_decided: str | None
    is_stale: bool
    summary: str | None
    resolution: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[InvestigationOut])
async def list_investigations(
    status: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[Investigation]:
    stmt = select(Investigation).order_by(Investigation.created_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(Investigation.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(
    investigation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation
