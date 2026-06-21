from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_password_hash, require_role
from ..database import get_session
from ..models import User
from ..schemas import UserCreate, UserRead, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    return (await session.execute(select(User).order_by(User.username))).scalars().all()


@router.post("", response_model=UserRead)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    existing = await session.execute(
        select(User).where((User.username == payload.username) | (User.email == payload.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already exists")
    item = User(
        username=payload.username,
        email=payload.email,
        role=payload.role,
        hashed_password=get_password_hash(payload.password),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    item = await session.get(User, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    if item.id == user.id:
        raise HTTPException(status_code=405, detail="Cannot delete yourself")
    await session.delete(item)
    await session.commit()
    return {"message": "User deleted"}


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    item = await session.get(User, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "password":
            item.hashed_password = get_password_hash(value)
        else:
            setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item
