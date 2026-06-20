from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import get_current_user
from ..database import get_session
from ..models import TestCase, User
from ..schemas import TestCaseBase, TestCaseRead
router = APIRouter()
@router.get("", response_model=list[TestCaseRead])
async def list_test_cases(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return (await session.execute(select(TestCase))).scalars().all()
@router.post("", response_model=TestCaseRead)
async def create_test_case(payload: TestCaseBase, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = TestCase(**payload.model_dump(), created_by=user.id); session.add(item); await session.commit(); await session.refresh(item); return item
@router.get("/{test_case_id}", response_model=TestCaseRead)
async def get_test_case(test_case_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(TestCase, test_case_id)
    if not item: raise HTTPException(404, "Test case not found")
    return item
@router.put("/{test_case_id}", response_model=TestCaseRead)
async def update_test_case(test_case_id: int, payload: TestCaseBase, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(TestCase, test_case_id)
    if not item: raise HTTPException(404, "Test case not found")
    for k, v in payload.model_dump().items(): setattr(item, k, v)
    await session.commit(); await session.refresh(item); return item
@router.delete("/{test_case_id}")
async def delete_test_case(test_case_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(TestCase, test_case_id)
    if not item: raise HTTPException(404, "Test case not found")
    await session.delete(item); await session.commit(); return {"deleted": True}
