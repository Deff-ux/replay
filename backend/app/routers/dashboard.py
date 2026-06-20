from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..models import TestCase, TestRun, TestSuite, User
from ..schemas import DashboardStats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    total_tests = await session.scalar(select(func.count(TestCase.id))) or 0
    total_suites = await session.scalar(select(func.count(TestSuite.id))) or 0

    run_counts = (
        await session.execute(
            select(
                func.count(TestRun.id).label("total_runs"),
                func.sum(case((TestRun.status == "passed", 1), else_=0)).label("passed_runs"),
                func.avg(TestRun.duration_ms).label("avg_duration_ms"),
            )
        )
    ).one()

    last_run = (
        await session.execute(select(TestRun).order_by(TestRun.created_at.desc()).limit(1))
    ).scalar_one_or_none()

    total_runs = run_counts.total_runs or 0
    passed_runs = run_counts.passed_runs or 0
    pass_rate = round((passed_runs / total_runs) * 100, 1) if total_runs else 0.0

    return DashboardStats(
        total_tests=total_tests,
        total_suites=total_suites,
        total_runs=total_runs,
        pass_rate=pass_rate,
        avg_duration_ms=int(run_counts.avg_duration_ms or 0),
        last_run=last_run,
    )
