from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import get_current_user
from ..database import get_session
from ..models import Environment, User
from ..schemas import EnvironmentBase, EnvironmentRead
router = APIRouter()
@router.get("", response_model=list[EnvironmentRead])
async def list_envs(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)): return (await session.execute(select(Environment))).scalars().all()
@router.post("", response_model=EnvironmentRead)
async def create_env(payload: EnvironmentBase, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    env = Environment(**payload.model_dump()); session.add(env); await session.commit(); await session.refresh(env); return env
