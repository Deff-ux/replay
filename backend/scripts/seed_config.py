#!/usr/bin/env python3
"""
Replay — Seed Configuration Loader

Reads config/environments.yaml and upserts environments + users into DB.

Usage:
    python scripts/seed_config.py                    # Apply all
    python scripts/seed_config.py --env-only         # Only environments
    python scripts/seed_config.py --users-only       # Only users
    python scripts/seed_config.py --reset            # Delete all, then seed
    python scripts/seed_config.py --dry-run          # Preview only
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure project root is in path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))  # add /app/backend for app module

# ── Colors ──────────────────────────────────────────────────────────────────
G = "\033[92m"  # green
Y = "\033[93m"  # yellow
R = "\033[91m"  # red
C = "\033[96m"  # cyan
B = "\033[1m"
N = "\033[0m"   # reset


def pgreen(t): print(f"{G}{t}{N}")
def pyellow(t): print(f"{Y}{t}{N}")
def pred(t): print(f"{R}{t}{N}")
def pcyan(t): print(f"{C}{t}{N}")
def pbold(t): print(f"{B}{t}{N}")


# ── Config path ─────────────────────────────────────────────────────────────
def get_config_path() -> Path:
    """Resolve environments.yaml path."""
    # 1. Env override
    env_path = os.environ.get("REPLAY_ENVIRONMENTS_CONFIG")
    if env_path:
        return Path(env_path)
    # 2. Next to this script
    local = PROJECT_ROOT / "config" / "environments.yaml"
    if local.exists():
        return local
    # 3. Default Docker path
    return Path("/app/backend/config/environments.yaml")


def load_config(config_path: Path) -> dict:
    """Load and validate YAML config file."""
    if not config_path.exists():
        pred(f"✗ Config not found: {config_path}")
        sys.exit(1)

    try:
        import yaml
        with open(config_path) as f:
            data = yaml.safe_load(f)
    except ImportError:
        # Fallback: read as JSON-compatible YAML via json if no pyyaml
        pred("✗ PyYAML not installed. Install with: pip install pyyaml")
        sys.exit(1)

    if not isinstance(data, dict):
        pred("✗ Invalid config: expected a top-level mapping")
        sys.exit(1)

    return data


# ── DB helpers ──────────────────────────────────────────────────────────────
async def _get_session():
    """Get an async DB session using the app's engine."""
    from app.database import async_session
    async with async_session() as session:
        yield session


async def seed_environments(config: dict, reset: bool, dry_run: bool) -> list:
    """Upsert environments from config."""
    from app.database import async_session
    from app.models import Environment
    from sqlalchemy import select, delete

    envs_data = config.get("environments", [])
    results = []

    async with async_session() as session:
        if reset:
            if dry_run:
                pyellow(f"  [DRY-RUN] Would delete {len(envs_data)} existing environments")
            else:
                await session.execute(delete(Environment))
                await session.commit()
                pgreen("  ✓ All existing environments deleted")

        for ed in envs_data:
            name = ed.get("name", "?")
            base_url = ed.get("base_url", "")
            auth_type = ed.get("auth_type", "none")
            auth_config = ed.get("auth_config", {})
            variables = ed.get("variables", {})
            is_active = ed.get("is_active", True)

            # Check existing by name
            result = await session.execute(
                select(Environment).where(Environment.name == name)
            )
            existing = result.scalar_one_or_none()

            if dry_run:
                action = "UPDATE" if existing else "CREATE"
                pyellow(f"  [DRY-RUN] {action} env '{name}' → {base_url}")
                results.append({"action": action.lower(), "name": name})
                continue

            if existing:
                existing.base_url = base_url
                existing.auth_type = auth_type
                existing.auth_config = auth_config
                existing.variables = variables
                existing.is_active = is_active
                pgreen(f"  ✓ Updated env '{name}'")
                results.append({"action": "updated", "name": name})
            else:
                env = Environment(
                    name=name, base_url=base_url, auth_type=auth_type,
                    auth_config=auth_config, variables=variables,
                    is_active=is_active
                )
                session.add(env)
                pgreen(f"  ✓ Created env '{name}'")
                results.append({"action": "created", "name": name})

        if not dry_run:
            await session.commit()

    return results


async def seed_users(config: dict, reset: bool, dry_run: bool) -> list:
    """Upsert users from config."""
    from app.database import async_session
    from app.models import User
    from app.auth import get_password_hash
    from sqlalchemy import select, delete

    users_data = config.get("users", [])
    results = []

    async with async_session() as session:
        if reset:
            if dry_run:
                pyellow(f"  [DRY-RUN] Would delete {len(users_data)} existing users")
            else:
                await session.execute(delete(User))
                await session.commit()
                pgreen("  ✓ All existing users deleted")

        for ud in users_data:
            username = ud.get("username", "?")
            email = ud.get("email", f"{username}@local")
            password = ud.get("password", "changeme")
            role = ud.get("role", "qa")

            result = await session.execute(
                select(User).where(User.username == username)
            )
            existing = result.scalar_one_or_none()

            if dry_run:
                action = "UPDATE" if existing else "CREATE"
                pyellow(f"  [DRY-RUN] {action} user '{username}' ({role})")
                results.append({"action": action.lower(), "name": username})
                continue

            hashed = get_password_hash(password)

            if existing:
                existing.email = email
                existing.hashed_password = hashed
                existing.role = role
                pgreen(f"  ✓ Updated user '{username}'")
                results.append({"action": "updated", "name": username})
            else:
                user = User(
                    username=username, email=email,
                    hashed_password=hashed, role=role
                )
                session.add(user)
                pgreen(f"  ✓ Created user '{username}'")
                results.append({"action": "created", "name": username})

        if not dry_run:
            await session.commit()

    return results


def print_summary(env_results, user_results, dry_run):
    """Print nice summary table."""
    print()
    pbold("═" * 50)
    pbold("  SUMMARY")
    pbold("═" * 50)

    total_env = len(env_results)
    total_user = len(user_results)
    created_env = sum(1 for r in env_results if r["action"] == "created")
    updated_env = sum(1 for r in env_results if r["action"] == "updated")
    created_user = sum(1 for r in user_results if r["action"] == "created")
    updated_user = sum(1 for r in user_results if r["action"] == "updated")

    if dry_run:
        pyellow(f"  DRY RUN — no changes made")
    else:
        pgreen(f"  Environments: {created_env} created, {updated_env} updated")
        pgreen(f"  Users:        {created_user} created, {updated_user} updated")

    print(f"  {'─' * 30}")

    if env_results:
        pcyan(f"  Environments ({total_env}):")
        for r in env_results:
            icon = "✓" if r["action"] == "created" else "↻"
            print(f"    {icon} {r['name']}")

    if user_results:
        pcyan(f"  Users ({total_user}):")
        for r in user_results:
            icon = "✓" if r["action"] == "created" else "↻"
            print(f"    {icon} {r['name']}")

    print()


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Replay — Seed environments & users from YAML config"
    )
    parser.add_argument("--env-only", action="store_true", help="Only seed environments")
    parser.add_argument("--users-only", action="store_true", help="Only seed users")
    parser.add_argument("--reset", action="store_true", help="Delete existing before seeding")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    args = parser.parse_args()

    # Determine scope
    do_env = not args.users_only
    do_users = not args.env_only

    # Load config
    config_path = get_config_path()
    pbold(f"\n📄 Config: {config_path}")
    config = load_config(config_path)

    env_count = len(config.get("environments", []))
    user_count = len(config.get("users", []))
    pcyan(f"   Found {env_count} environments, {user_count} users")

    if args.dry_run:
        pyellow("\n⚠️  DRY RUN MODE — no changes will be made\n")
    elif args.reset:
        pred("\n⚠️  RESET MODE — existing data will be deleted!\n")

    # Run
    async def run():
        env_results = []
        user_results = []

        if do_env:
            pbold("\n── Environments ──")
            env_results = await seed_environments(config, args.reset, args.dry_run)

        if do_users:
            pbold("\n── Users ──")
            user_results = await seed_users(config, args.reset, args.dry_run)

        print_summary(env_results, user_results, args.dry_run)

    asyncio.run(run())


if __name__ == "__main__":
    main()
