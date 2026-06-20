from apscheduler.schedulers.asyncio import AsyncIOScheduler
class SuiteScheduler:
    def __init__(self, db_url: str | None = None): self.scheduler = AsyncIOScheduler()
    def start(self):
        if not self.scheduler.running: self.scheduler.start()
    def shutdown(self):
        if self.scheduler.running: self.scheduler.shutdown()
    async def schedule_suite(self, suite_id: int, cron_expr: str, env_id: int):
        self.scheduler.add_job(self._execute_suite_job, "cron", id=f"suite_{suite_id}", replace_existing=True, args=[suite_id, env_id], **self._parse_cron(cron_expr))
    async def _execute_suite_job(self, suite_id: int, env_id: int): return None
    @staticmethod
    def _parse_cron(cron_expr: str) -> dict:
        minute, hour, day, month, day_of_week = cron_expr.split()
        return {"minute": minute, "hour": hour, "day": day, "month": month, "day_of_week": day_of_week}
