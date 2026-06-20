from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import auth, dashboard, environments, reports, runs, seeds, suites, test_cases, users, webhooks
from .services.scheduler import SuiteScheduler
from .services.ws_manager import WebSocketManager

scheduler = SuiteScheduler(settings.database_url)
ws_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(); scheduler.start(); yield; scheduler.shutdown()

app = FastAPI(title="Replay — Test Dashboard", version=settings.version, lifespan=lifespan)

@app.get("/api/v1/health")
async def health(): return {"status": "ok", "app": settings.app_name, "version": settings.version}

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(test_cases.router, prefix="/api/v1/test-cases", tags=["Test Cases"])
app.include_router(suites.router, prefix="/api/v1/suites", tags=["Suites"])
app.include_router(runs.router, prefix="/api/v1/runs", tags=["Runs"])
app.include_router(environments.router, prefix="/api/v1/environments", tags=["Environments"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(seeds.router, prefix="/api/v1/seeds", tags=["Seed Data"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

@app.websocket("/api/v1/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await ws_manager.connect(run_id, websocket)
    try:
        while True: await websocket.receive_text()
    except Exception: ws_manager.disconnect(run_id, websocket)

if Path(settings.frontend_dist_dir).exists():
    app.mount("/", StaticFiles(directory=settings.frontend_dist_dir, html=True), name="frontend")
