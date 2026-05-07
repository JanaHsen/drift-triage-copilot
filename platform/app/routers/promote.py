"""POST /v1/promote — checklist gate, atomic transition, audit log."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_bearer_token
from app.db.models import PromotionAudit
from app.db.session import get_session
from app.promotion.checklist import run_checklist
from app.promotion.registry import promote_to_production
from contracts.v1.promote import PromotionRequest, PromotionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/promote", tags=["promote"])


@router.post(
    "",
    response_model=PromotionResponse,
    dependencies=[Depends(require_bearer_token)],
)
async def promote(
    payload: PromotionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PromotionResponse:
    # Idempotency: same request_id returns the original outcome.
    existing = (await session.execute(
        select(PromotionAudit).where(PromotionAudit.request_id == payload.request_id)
    )).scalar_one_or_none()

    if existing is not None:
        return PromotionResponse(
            promoted=existing.promoted,
            model_name=existing.model_name,
            promoted_version=payload.target_version if existing.promoted else None,
            archived_versions=existing.archived_versions or [],
            checklist=existing.checklist_results,
            audit_log_id=str(existing.id),
            message=f"duplicate request_id; original outcome: promoted={existing.promoted}",
            timestamp=existing.created_at,
        )

    # Run the checklist. Every gate runs even if earlier ones fail — the audit
    # log shows the complete picture, not just the first failure.
    checklist = run_checklist(payload.model_name, payload.target_version)
    all_passed = all(c.passed for c in checklist)

    if not all_passed:
        failed = [c.name for c in checklist if not c.passed]
        audit = PromotionAudit(
            request_id=payload.request_id,
            model_name=payload.model_name,
            target_version=payload.target_version,
            approver_user_id=payload.approver_user_id,
            investigation_id=payload.investigation_id,
            promoted=False,
            archived_versions=[],
            checklist_results=[c.model_dump() for c in checklist],
            error_message=f"checklist failed: {failed}",
            reason=payload.reason,
        )
        session.add(audit)
        await session.commit()
        await session.refresh(audit)
        return PromotionResponse(
            promoted=False,
            model_name=payload.model_name,
            promoted_version=None,
            archived_versions=[],
            checklist=checklist,
            audit_log_id=str(audit.id),
            message=f"promotion blocked: {len(failed)} check(s) failed: {failed}",
            timestamp=audit.created_at,
        )

    # Checks passed → attempt transition. Failure here means MLflow itself rejected
    # the call (permissions, network, race) — distinct from a checklist failure.
    try:
        promoted_version, archived = promote_to_production(payload.model_name, payload.target_version)
    except Exception as exc:
        logger.exception("Registry transition failed for %s v%s", payload.model_name, payload.target_version)
        audit = PromotionAudit(
            request_id=payload.request_id,
            model_name=payload.model_name,
            target_version=payload.target_version,
            approver_user_id=payload.approver_user_id,
            investigation_id=payload.investigation_id,
            promoted=False,
            archived_versions=[],
            checklist_results=[c.model_dump() for c in checklist],
            error_message=f"transition failed: {exc}",
            reason=payload.reason,
        )
        session.add(audit)
        await session.commit()
        await session.refresh(audit)
        return PromotionResponse(
            promoted=False,
            model_name=payload.model_name,
            promoted_version=None,
            archived_versions=[],
            checklist=checklist,
            audit_log_id=str(audit.id),
            message=f"checklist passed but registry transition failed: {exc}",
            timestamp=audit.created_at,
        )

    # Success.
    audit = PromotionAudit(
        request_id=payload.request_id,
        model_name=payload.model_name,
        target_version=payload.target_version,
        approver_user_id=payload.approver_user_id,
        investigation_id=payload.investigation_id,
        promoted=True,
        archived_versions=archived,
        checklist_results=[c.model_dump() for c in checklist],
        error_message=None,
        reason=payload.reason,
    )
    session.add(audit)
    await session.commit()
    await session.refresh(audit)

    return PromotionResponse(
        promoted=True,
        model_name=payload.model_name,
        promoted_version=promoted_version,
        archived_versions=archived,
        checklist=checklist,
        audit_log_id=str(audit.id),
        message=f"v{promoted_version} promoted to Production; archived: {archived}",
        timestamp=audit.created_at,
    )
