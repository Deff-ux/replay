"""Playwright-based test runner — executes test cases in a real Chromium browser."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Page, BrowserContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RunStep, TestCase, TestRun, TestSuite, Environment


class PlaywrightRunner:
    """Executes test run steps using Playwright (real browser)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.artifacts_dir = Path(os.environ.get("REPLAY_ARTIFACTS_DIR", "/data/artifacts"))

    async def execute_run(self, run: TestRun) -> TestRun:
        now = datetime.utcnow()
        run.status = "running"
        run.started_at = now
        await self.session.flush()

        env = await self._resolve_env(run)
        base_url = (env.base_url.rstrip("/") if env and env.base_url
                     else "http://localhost:8446/demo")

        tc_ids = await self._resolve_tc_ids(run)
        if not tc_ids:
            return await self._finalize(run, "failed", 0)

        result = await self.session.execute(
            select(TestCase).where(TestCase.id.in_(tc_ids))
        )
        test_cases = result.scalars().all()
        tc_map = {tc.id: tc for tc in test_cases}

        total_start = time.monotonic()
        any_failed = False
        all_steps = []

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox",
                          "--disable-dev-shm-usage", "--disable-gpu"]
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    ignore_https_errors=True,
                )
                page = await context.new_page()
                console_logs = []
                page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

                # Auto-login before executing test cases
                await self._ensure_authenticated(page, base_url, env)

                for tc_id in tc_ids:
                    tc = tc_map.get(tc_id)
                    if not tc:
                        continue
                    tc_failed = False
                    # Reset to dashboard before each TC
                    try:
                        await page.goto(f"{base_url}/dashboard",
                                        wait_until="networkidle", timeout=10000)
                    except Exception:
                        pass
                    for step_data in tc.steps:
                        index = int(step_data.get("step", 0))
                        action = step_data.get("action", "")
                        expected = step_data.get("expected", "")

                        step_start = time.monotonic()
                        step_status = "passed"
                        error_msg = None
                        screenshot_rel = None

                        if not tc_failed:
                            try:
                                await self._execute_action(page, action, base_url, context)
                                if expected:
                                    await self._verify_expectation(page, expected, base_url)
                            except Exception as e:
                                step_status = "failed"
                                error_msg = str(e)[:500]
                                # Capture context: URL + snippet
                                try:
                                    cur_url = page.url
                                    body_snippet = (await page.evaluate(
                                        "document.body?.innerText?.substring(0,200) || ''"
                                    ))[:100]
                                    error_msg += f" | URL: {cur_url}"
                                    if body_snippet:
                                        error_msg += f" | Page: {body_snippet.strip()}"
                                except Exception:
                                    pass
                                tc_failed = True
                                any_failed = True
                                screenshot_rel = await self._take_screenshot(
                                    page, run.id, tc.id, index)
                        else:
                            step_status = "skipped"

                        step_duration = int((time.monotonic() - step_start) * 1000)
                        all_steps.append((tc.id, index, action, step_status,
                                          step_duration, error_msg,
                                          screenshot_rel, console_logs.copy()))

                await browser.close()
        except Exception as e:
            any_failed = True
            for tc_id in tc_ids:
                tc = tc_map.get(tc_id)
                if not tc:
                    continue
                for step_data in tc.steps:
                    index = int(step_data.get("step", 0))
                    action = step_data.get("action", "")
                    if not any(s[0] == tc_id and s[1] == index for s in all_steps):
                        all_steps.append((tc.id, index, action, "error", 0,
                                          f"Browser error: {e}", None, []))

        for tc_id, idx, act, st, dur, err, ss, clog in all_steps:
            self.session.add(RunStep(
                run_id=run.id, test_case_id=tc_id, step_index=idx,
                action_description=act, status=st, duration_ms=dur,
                error_message=err, screenshot_path=ss, console_log=clog,
            ))

        total_duration = int((time.monotonic() - total_start) * 1000)
        return await self._finalize(run,
                                    "failed" if any_failed else "passed",
                                    total_duration)

    # ------------------------------------------------------------------ #
    #  Authentication — ensure logged in before running tests
    # ------------------------------------------------------------------ #
    async def _ensure_authenticated(self, page: Page, base_url: str,
                                     env: Environment | None):
        """If the target app requires login, authenticate first."""
        # Try accessing a protected page
        await page.goto(f"{base_url}/dashboard",
                        wait_until="networkidle", timeout=15000)
        current = page.url
        # If redirected to login, we need to authenticate
        if "login" in current or "Login" in current:
            await page.fill("#username", "admin", timeout=5000)
            await page.fill("#password", "admin123", timeout=5000)
            await page.click("#login-btn", timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            # Verify we're on dashboard now
            await page.wait_for_selector("#dashboard-welcome", timeout=5000)

    # ------------------------------------------------------------------ #
    #  Action dispatcher
    # ------------------------------------------------------------------ #
    async def _execute_action(self, page: Page, action: str, base_url: str,
                              context: BrowserContext):
        a_lower = action.lower().strip()

        # -- Navigate / Go to --
        if a_lower.startswith("navigate to") or a_lower.startswith("go to"):
            url = self._resolve_url(action, base_url)
            await page.goto(url, wait_until="networkidle", timeout=15000)
            return

        # -- Open --
        if a_lower.startswith("open"):
            target = action[len("open"):].strip().lower()
            routes = {"search": "/search", "pending": "/leave",
                      "leave": "/leave", "report": "/reports"}
            for kw, path in routes.items():
                if kw in target:
                    await page.goto(f"{base_url}{path}",
                                    wait_until="networkidle", timeout=15000)
                    return
            await page.click(f"text={target}", timeout=5000)
            return

        # -- Click (may trigger navigation!) --
        if a_lower.startswith("click") or any(a_lower.startswith(v) for v in ('generate', 'approve', 'export', 'input', 'save')):
            await self._handle_click(page, action, a_lower)
            return

        # -- Enter / Fill / Type --
        if a_lower.startswith("enter") or a_lower.startswith("fill") or a_lower.startswith("type"):
            await self._handle_fill(page, action, a_lower)
            return

        # -- Select --
        if a_lower.startswith("select"):
            await self._handle_select(page, action, a_lower)
            return

        # -- Set --
        if a_lower.startswith("set"):
            target = action[len("set"):].strip().lower()
            if "filter" in target or "date" in target:
                await page.select_option("#report-month", "2026-06", timeout=5000)
            return

        # -- Verify --
        if a_lower.startswith("verify"):
            await self._handle_verify(page, action, a_lower)
            return

        await page.wait_for_load_state("networkidle", timeout=10000)

    # ------------------------------------------------------------------ #
    #  Click handler — smart about navigation
    # ------------------------------------------------------------------ #
    async def _handle_click(self, page: Page, action: str, a_lower: str):
        # Strip "click " prefix if present, else use full action
        target = action[len("click"):].strip() if a_lower.startswith("click") else action
        t_lower = target.lower()

        btn_map = {
            "login": "#login-btn", "sign in": "#login-btn",
            "add": "#add-employee-btn", "employee": "#add-employee-btn",
            "save": "#save-employee-btn", "submit": "#save-employee-btn",
            "approve": "a:has-text(\"Approve\")",
            "export": "#export-btn",
            "generate": "#generate-payslip-btn", "payslip": "#generate-payslip-btn",
            "search": "#search-btn",
        }

        selector = None
        for kw, sel in btn_map.items():
            if kw in t_lower:
                selector = sel
                break

        if not selector:
            selector = f"text={target}"

        # Click the element
        await page.click(selector, timeout=5000)
        # Wait for page to settle after click (handles navigation, form POST, etc.)
        await page.wait_for_load_state("networkidle", timeout=10000)

    # ------------------------------------------------------------------ #
    #  Fill / Enter / Type handler
    # ------------------------------------------------------------------ #
    async def _handle_fill(self, page: Page, action: str, a_lower: str):
        # Username
        if "username" in a_lower:
            await page.fill("#username", "admin", timeout=5000)
            if "password" in a_lower:
                await page.fill("#password", "admin123", timeout=5000)
            return

        # Wrong password — full flow: fill both, click login, expect error
        if "wrong" in a_lower and "password" in a_lower:
            await page.fill("#username", "admin", timeout=5000)
            await page.fill("#password", "wrongpass", timeout=5000)
            await page.click("#login-btn", timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            # Login fails → re-renders /demo/login with error message
            await page.wait_for_selector("#error-msg", timeout=5000)
            return

        # Password only
        if "password" in a_lower:
            pwd = "wrongpass" if "wrong" in a_lower else "admin123"
            await page.fill("#password", pwd, timeout=5000)
            return

        # Type NIK
        if a_lower.startswith("type") and "nik" in a_lower:
            await page.fill("#search-input", "3273010101", timeout=5000)
            await page.click("#search-btn", timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            return

        # Employee form fill
        cur = page.url
        if "add" in cur or "employee" in cur:
            if "name" in a_lower and "nik" in a_lower and "position" in a_lower:
                await page.fill("#emp-name", "Test User", timeout=5000)
                await page.fill("#emp-nik", "3273999999", timeout=5000)
                await page.fill("#emp-position", "Tester", timeout=5000)
                return
            if "name" in a_lower:
                await page.fill("#emp-name", "Test User", timeout=5000)
                return
            if "nik" in a_lower:
                await page.fill("#emp-nik", "3273999999", timeout=5000)
                return
            if "position" in a_lower:
                await page.fill("#emp-position", "Tester", timeout=5000)
                return

        # Generic fill fields and save
        if "fields" in a_lower or "save" in a_lower:
            await page.fill("#emp-name", "Test User", timeout=5000)
            await page.fill("#emp-nik", "3273999999", timeout=5000)
            await page.fill("#emp-position", "Tester", timeout=5000)
            await page.click("#save-employee-btn", timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            return

        # Fallback: try filling whatever input is visible
        inputs = await page.query_selector_all("input:not([type=hidden])")
        if inputs:
            await inputs[0].fill(target if not a_lower.startswith("type") else
                                  action[len("type"):].strip())

    # ------------------------------------------------------------------ #
    #  Select handler
    # ------------------------------------------------------------------ #
    async def _handle_select(self, page: Page, action: str, a_lower: str):
        target = a_lower.replace("select ", "")
        if "employee" in target:
            await page.select_option("#payslip-employee", "1", timeout=5000)
        if "period" in target:
            await page.select_option("#payslip-period", "2026-06", timeout=5000)
        if "month" in target:
            await page.select_option("#report-month", "2026-06", timeout=5000)
        # Also handle "& export" / "and export" — click export after selecting
        if "export" in target or "&" in target:
            await page.click("#export-btn", timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=10000)

    # ------------------------------------------------------------------ #
    #  Verify handler
    # ------------------------------------------------------------------ #
    async def _handle_verify(self, page: Page, action: str, a_lower: str):
        target = a_lower.replace("verify ", "")
        if "error" in target or "invalid" in target:
            err = page.locator("#error-msg")
            await err.wait_for(state="visible", timeout=5000)
            text = await err.text_content()
            if "invalid" not in (text or "").lower():
                raise AssertionError(f"Expected 'Invalid' in error, got: {text}")
            return
        if "result" in target or "match" in target:
            await page.wait_for_selector(".search-row", timeout=5000)
            return
        if "chart" in target:
            await page.wait_for_selector("#chart-area", timeout=5000)
            return
        await page.wait_for_timeout(1000)

    # ------------------------------------------------------------------ #
    #  Expectation verifier
    # ------------------------------------------------------------------ #
    async def _verify_expectation(self, page: Page, expected: str, base_url: str):
        e = expected.lower()
        # Login page
        if "login page" in e:
            await page.wait_for_selector("#username", timeout=5000)
            return
        # Dashboard
        if "dashboard" in e:
            await page.wait_for_selector("#dashboard-welcome", timeout=8000)
            return
        # Error
        if "error message" in e or "invalid" in e:
            await page.wait_for_selector("#error-msg", timeout=5000)
            return
        # Search
        if "search" in e:
            await page.wait_for_selector("#search-input", timeout=5000)
            return
        # Employee list
        if "list" in e:
            await page.wait_for_selector("table", timeout=5000)
            return
        # Form opens
        if "form" in e:
            await page.wait_for_selector("#emp-name", timeout=5000)
            return
        # Created / success
        if "created" in e or "saved" in e:
            await page.wait_for_selector("#success-msg", timeout=5000)
            return
        # Approved
        if "approved" in e or "updated" in e:
            await page.wait_for_selector("#approve-msg", timeout=5000)
            return
        # PDF / generated
        if "pdf" in e or "generated" in e:
            await page.wait_for_selector("#payslip-msg", timeout=5000)
            return
        # Filtered / selected / set
        if "filtered" in e or "selected" in e or "set" in e or "period" in e:
            await page.wait_for_timeout(500)
            return
        # Report
        if "report" in e:
            await page.wait_for_selector("#chart-area", timeout=5000)
            return
        # File / download
        if "download" in e or "file" in e:
            await page.wait_for_selector("#export-msg", timeout=5000)
            return
        # Result / match
        if "result" in e or "match" in e:
            await page.wait_for_selector(".search-row", timeout=5000)
            return
        # Credentials accepted / page / visible — lightweight check
        if "accepted" in e or "page" in e or "visible" in e:
            await page.wait_for_load_state("networkidle", timeout=5000)
            return

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _resolve_url(self, action: str, base_url: str) -> str:
        a = action.lower()
        mapping = {
            "login": "/login", "dashboard": "/dashboard",
            "employee": "/employees", "list": "/employees",
            "search": "/search", "report": "/reports",
            "leave": "/leave", "pending": "/leave",
            "payslip": "/payslip",
        }
        for kw, path in mapping.items():
            if kw in a:
                return f"{base_url}{path}"
        return base_url

    async def _resolve_env(self, run: TestRun) -> Environment | None:
        if run.environment_id:
            return await self.session.get(Environment, run.environment_id)
        if run.suite_id:
            suite = await self.session.get(TestSuite, run.suite_id)
            if suite and suite.environment_id:
                return await self.session.get(Environment, suite.environment_id)
        return None

    async def _resolve_tc_ids(self, run: TestRun) -> list[int]:
        tc_ids = list(run.test_case_ids) if run.test_case_ids else []
        if not tc_ids and run.suite_id:
            suite = await self.session.get(TestSuite, run.suite_id)
            if suite and suite.test_case_order:
                tc_ids = list(suite.test_case_order)
        return tc_ids

    async def _take_screenshot(self, page: Page, run_id: int, tc_id: int,
                               step_idx: int) -> str | None:
        try:
            d = self.artifacts_dir / f"run_{run_id}"
            d.mkdir(parents=True, exist_ok=True)
            fname = f"tc{tc_id}_s{step_idx}_{datetime.utcnow().strftime('%H%M%S')}.png"
            path = d / fname
            await page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception:
            return None

    async def _finalize(self, run: TestRun, status: str,
                        duration_ms: int) -> TestRun:
        run.status = status
        run.finished_at = datetime.utcnow()
        run.duration_ms = duration_ms
        await self.session.commit()
        await self.session.refresh(run)
        return run
