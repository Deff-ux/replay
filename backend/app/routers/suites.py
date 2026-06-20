from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import get_current_user
from ..database import get_session
from ..models import TestSuite, User
from ..schemas import TestSuiteBase, TestSuiteRead
router = APIRouter()
@router.get("", response_model=list[TestSuiteRead])
async def list_suites(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return (await session.execute(select(TestSuite))).scalars().all()
@router.post("", response_model=TestSuiteRead)
async def create_suite(payload: TestSuiteBase, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = TestSuite(**payload.model_dump(), created_by=user.id); session.add(item); await session.commit(); await session.refresh(item); return item
@router.get("/{suite_id}", response_model=TestSuiteRead)
async def get_suite(suite_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(TestSuite, suite_id)
    if not item: raise HTTPException(404, "Suite not found")
    return item
@router.put("/{suite_id}", response_model=TestSuiteRead)
async def update_suite(suite_id: int, payload: TestSuiteBase, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(TestSuite, suite_id)
    if not item: raise HTTPException(404, "Suite not found")
    for k, v in payload.model_dump().items(): setattr(item, k, v)
    await session.commit(); await session.refresh(item); return item
@router.delete("/{suite_id}")
async def delete_suite(suite_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(TestSuite, suite_id)
    if not item: raise HTTPException(404, "Suite not found")
    await session.delete(item); await session.commit(); return {"deleted": True}
