import httpx
class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str): self.api_url = f"https://api.telegram.org/bot{bot_token}"; self.chat_id = chat_id
    async def send_failure(self, run_result: dict):
        async with httpx.AsyncClient() as client: await client.post(f"{self.api_url}/sendMessage", json={"chat_id": self.chat_id, "text": f"❌ Regression FAILED — Run {run_result.get('run_id')}", "parse_mode": "Markdown"})
    async def send_summary(self, suite_result: dict):
        emoji = "✅" if suite_result.get("passed") else "❌"
        async with httpx.AsyncClient() as client: await client.post(f"{self.api_url}/sendMessage", json={"chat_id": self.chat_id, "text": f"{emoji} {suite_result.get('suite_name', 'Suite')} summary"})
