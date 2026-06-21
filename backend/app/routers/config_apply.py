"""
Replay — Config Apply API Endpoint

POST /api/v1/config/apply — Trigger seed from environments.yaml via API.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..models import User

router = APIRouter()


class ConfigApplyRequest(BaseModel):
    reset: bool = False
    scope: str = "all"  # "all" | "envs" | "users"


class ConfigApplyResponse(BaseModel):
    status: str
    environments: list[dict]
    users: list[dict]
    message: str


@router.post("/apply", response_model=ConfigApplyResponse)
async def apply_config(
    payload: ConfigApplyRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Read config/environments.yaml and seed DB."""
    # Only admins can apply config
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can apply config")

    import sys
    from pathlib import Path

    # Find config file
    config_path = Path("/app/backend/config/environments.yaml")
    if not config_path.exists():
        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "environments.yaml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="environments.yaml not found")

    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot parse config: {e}")

    if not isinstance(config, dict):
        raise HTTPException(status_code=500, detail="Invalid config format")

    from ..models import Environment
    from ..auth import get_password_hash
    from sqlalchemy import select, delete

    do_env = payload.scope in ("all", "envs")
    do_users = payload.scope in ("all", "users")
    env_results = []
    user_results = []

    # ── Environments ──
    if do_env and "environments" in config:
        if payload.reset:
            await session.execute(delete(Environment))
            await session.commit()

        for ed in config["environments"]:
            name = ed.get("name", "?")
            result = await session.execute(
                select(Environment).where(Environment.name == name)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.base_url = ed.get("base_url", existing.base_url)
                existing.auth_type = ed.get("auth_type", existing.auth_type)
                existing.auth_config = ed.get("auth_config", existing.auth_config)
                existing.variables = ed.get("variables", existing.variables)
                existing.is_active = ed.get("is_active", existing.is_active)
                env_results.append({"action": "updated", "name": name})
            else:
                env = Environment(
                    name=name,
                    base_url=ed.get("base_url", ""),
                    auth_type=ed.get("auth_type", "none"),
                    auth_config=ed.get("auth_config", {}),
                    variables=ed.get("variables", {}),
                    is_active=ed.get("is_active", True),
                )
                session.add(env)
                env_results.append({"action": "created", "name": name})

    # ── Users ──
    if do_users and "users" in config:
        from ..models import User as UserModel

        if payload.reset:
            await session.execute(delete(UserModel))
            await session.commit()

        for ud in config["users"]:
            username = ud.get("username", "?")
            result = await session.execute(
                select(UserModel).where(UserModel.username == username)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.email = ud.get("email", existing.email)
                existing.role = ud.get("role", existing.role)
                if "password" in ud:
                    existing.hashed_password = get_password_hash(ud["password"])
                user_results.append({"action": "updated", "name": username})
            else:
                user = UserModel(
                    username=username,
                    email=ud.get("email", f"{username}@local"),
                    hashed_password=get_password_hash(ud.get("password", "changeme")),
                    role=ud.get("role", "qa"),
                )
                session.add(user)
                user_results.append({"action": "created", "name": username})

    await session.commit()

    return ConfigApplyResponse(
        status="ok",
        environments=env_results,
        users=user_results,
        message=f"Applied: {len(env_results)} envs, {len(user_results)} users",
    )
