import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..config import settings
from ..database import get_session
from ..models import User
from ..schemas import SeedCleanupRequest, SeedRunRequest, SeedTemplateRead
from ..services.seed_engine import SeedEngine

router = APIRouter()


@router.get("", response_model=list[SeedTemplateRead])
async def list_seed_templates(user: User = Depends(get_current_user)):
    seeds_dir = Path(settings.seeds_dir)
    if not seeds_dir.exists():
        return []

    templates: list[SeedTemplateRead] = []
    for path in sorted(seeds_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        templates.append(
            SeedTemplateRead(
                name=path.stem,
                description=data.get("description"),
                parameters=data.get("parameters", {}),
            )
        )
    return templates


@router.post("/run")
async def run_seed_template(
    payload: SeedRunRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    template_path = Path(settings.seeds_dir) / f"{payload.template_name}.json"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Seed template not found")
    return await SeedEngine(session).seed(payload.template_name, payload.params, payload.run_id)


@router.post("/cleanup")
async def cleanup_seed_data(
    payload: SeedCleanupRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await SeedEngine(session).cleanup(payload.run_id, payload.method)
