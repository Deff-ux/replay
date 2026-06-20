from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = {}
    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept(); self.connections.setdefault(run_id, set()).add(websocket)
    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.connections: self.connections[run_id].discard(websocket)
    async def broadcast(self, run_id: str, message: dict):
        dead = set()
        for ws in self.connections.get(run_id, set()):
            try: await ws.send_json(message)
            except Exception: dead.add(ws)
        self.connections.get(run_id, set()).difference_update(dead)
