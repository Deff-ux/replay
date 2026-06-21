"""Test run executor — delegates to Playwright for real browser execution."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import TestRun
from .playwright_runner import PlaywrightRunner


class RunExecutor:
    """Executes a test run using Playwright (real browser)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._pw = PlaywrightRunner(session)

    async def execute_run(self, run: TestRun) -> TestRun:
        return await self._pw.execute_run(run)
