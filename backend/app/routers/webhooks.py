from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import TestRun
from ..schemas import RunRead, WebhookRunRequest

router = APIRouter()


@router.post("/runs", response_model=RunRead)
async def create_webhook_run(
    payload: WebhookRunRequest,
    session: AsyncSession = Depends(get_session),
):
    run = TestRun(
        suite_id=payload.suite_id,
        test_case_ids=payload.test_case_ids,
        environment_id=payload.environment_id,
        triggered_by="webhook",
        trigger_detail=payload.trigger_detail,
        status="pending",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run
