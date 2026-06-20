from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..models import Report, User
from ..schemas import ReportRead

router = APIRouter()


@router.get("", response_model=list[ReportRead])
async def list_reports(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return (await session.execute(select(Report).order_by(Report.created_at.desc()))).scalars().all()


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await session.get(Report, report_id)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found")
    return item
