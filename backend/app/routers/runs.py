from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import get_current_user
from ..database import get_session
from ..models import RunStep, TestRun, User
from ..schemas import RunCreate, RunRead, RunStepRead
from ..services.runner import RunExecutor
router = APIRouter()
@router.get("", response_model=list[RunRead])
async def list_runs(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return (await session.execute(select(TestRun).order_by(TestRun.created_at.desc()))).scalars().all()
@router.post("", response_model=RunRead)
async def create_run(payload: RunCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    run = TestRun(**payload.model_dump(), status="pending"); session.add(run); await session.commit(); await session.refresh(run)
    executor = RunExecutor(session); run = await executor.execute_run(run)
    return run
@router.get("/{run_id}", response_model=RunRead)
async def get_run(run_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    run = await session.get(TestRun, run_id)
    if not run: raise HTTPException(404, "Run not found")
    return run
@router.post("/{run_id}/stop", response_model=RunRead)
async def stop_run(run_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    run = await session.get(TestRun, run_id)
    if not run: raise HTTPException(404, "Run not found")
    run.status = "aborted"; run.finished_at = datetime.utcnow(); await session.commit(); await session.refresh(run); return run
@router.get("/{run_id}/steps", response_model=list[RunStepRead])
async def get_run_steps(run_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    result = await session.execute(select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.step_index))
    return result.scalars().all()
