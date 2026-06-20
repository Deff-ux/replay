from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

class PlaywrightRunner:
    def __init__(self, run_id: str, ws_manager):
        self.run_id = run_id; self.ws = ws_manager; self.browser = None; self.context = None; self.page = None; self._cancelled = False
    async def run_test_case(self, test_case: dict, env: dict) -> dict:
        steps_result = []; start_time = datetime.utcnow()
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            video_dir = f"/data/artifacts/{self.run_id}/video"; Path(video_dir).mkdir(parents=True, exist_ok=True)
            self.context = await self.browser.new_context(record_video_dir=video_dir, viewport={"width": 1366, "height": 768})
            self.page = await self.context.new_page()
            for index, step in enumerate(test_case.get("steps", [])):
                if self._cancelled: break
                step.setdefault("index", index + 1); step_start = datetime.utcnow(); error = None
                try: await self._execute_step(step); status = "passed"
                except Exception as exc: status = "failed"; error = str(exc)
                screenshot_path = await self._capture_screenshot(step["index"])
                result = {"step_index": step["index"], "action": step.get("description", step.get("action_type", "step")), "status": status, "duration_ms": int((datetime.utcnow() - step_start).total_seconds() * 1000), "error": error, "screenshot_path": screenshot_path, "console_log": []}
                steps_result.append(result); await self.ws.broadcast(self.run_id, {"type": "step_complete", "data": result})
            video_path = await self.page.video.path() if self.page.video else None
            await self.context.close(); await self.browser.close()
        return {"steps": steps_result, "total_duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000), "video_path": video_path, "overall_status": "passed" if all(s["status"] == "passed" for s in steps_result) else "failed"}
    async def _execute_step(self, step: dict):
        action = step["action_type"]; selector = step.get("selector"); value = step.get("value")
        if action == "goto": await self.page.goto(value, wait_until="networkidle")
        elif action == "click": await self.page.click(selector)
        elif action == "fill": await self.page.fill(selector, value)
        elif action == "select": await self.page.select_option(selector, value)
        elif action == "wait": await self.page.wait_for_timeout(int(value))
        elif action == "wait_for_selector": await self.page.wait_for_selector(selector, timeout=int(value or 30000))
        elif action == "assert_text":
            text = await self.page.text_content(selector); assert value in (text or ""), f"Expected '{value}' in element, got '{text}'"
        elif action == "assert_visible": await self.page.wait_for_selector(selector, state="visible")
        elif action == "screenshot": return
        elif action == "keypress": await self.page.keyboard.press(value)
        else: raise ValueError(f"Unknown action: {action}")
    async def _capture_screenshot(self, step_index: int) -> str:
        path = f"/data/artifacts/{self.run_id}/screenshots/step_{step_index:03d}.png"; Path(path).parent.mkdir(parents=True, exist_ok=True); await self.page.screenshot(path=path, full_page=True); return path
    def cancel(self): self._cancelled = True
