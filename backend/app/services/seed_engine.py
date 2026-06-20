import json, re
from datetime import datetime, timedelta
class SeedEngine:
    def __init__(self, db_session): self.session = db_session
    async def seed(self, template_name: str, params: dict, run_id: str): return {"template": template_name, "params": params, "run_id": run_id}
    async def cleanup(self, run_id: str, method: str = "prefix"): return {"cleaned": True, "run_id": run_id, "method": method}
    async def _load_template(self, name: str) -> dict:
        with open(f"/data/seeds/{name}.json", encoding="utf-8") as f: return json.load(f)
    @staticmethod
    def _resolve_relative_date(expr: str, params: dict) -> str:
        match = re.match(r"^(-?\d+)\s*(months|days|years)$", expr)
        if not match: return expr
        amount = int(match.group(1)); unit = match.group(2); days = {"days": 1, "months": 30, "years": 365}[unit] * amount
        return (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")
