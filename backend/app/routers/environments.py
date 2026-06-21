from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import get_current_user
from ..database import get_session
from ..models import Environment, User
from ..schemas import EnvironmentBase, EnvironmentRead
router = APIRouter()


@router.get("", response_model=list[EnvironmentRead])
async def list_envs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return (await session.execute(select(Environment))).scalars().all()


@router.post("", response_model=EnvironmentRead)
async def create_env(
    payload: EnvironmentBase,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    env = Environment(**payload.model_dump())
    session.add(env)
    await session.commit()
    await session.refresh(env)
    return env


@router.put("/{env_id}", response_model=EnvironmentRead)
async def update_env(
    env_id: int,
    payload: EnvironmentBase,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    env = await session.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    for key, value in payload.model_dump().items():
        setattr(env, key, value)
    await session.commit()
    await session.refresh(env)
    return env


@router.delete("/{env_id}")
async def delete_env(
    env_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    env = await session.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    await session.delete(env)
    await session.commit()
    return {"message": "Environment deleted"}
