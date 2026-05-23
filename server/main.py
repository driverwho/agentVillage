import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 确保项目根目录在 sys.path 中（支持 python server/main.py 直接执行）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 1. 加载 .env（项目根目录）
load_dotenv(_PROJECT_ROOT / ".env")

# 2. 从配置文件加载参数
from server.config import config as game_config

_yaml_path = os.getenv("GAME_CONFIG_PATH", "config.yaml")
if os.path.exists(_yaml_path):
    game_config = type(game_config).from_yaml(_yaml_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化 BackgroundManager → Orchestrator → 时间流逝
    from server.core.background_manager import BackgroundManager
    BackgroundManager.init()

    from server.core.orchestrator import Orchestrator
    import server.core.orchestrator as orch_mod

    orch = Orchestrator()
    orch_mod.orch = orch
    orch.start_auto_tick()
    yield
    # 关闭：停止时间流逝
    orch.stop_auto_tick()


app = FastAPI(title="Agent Village", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REST API ---
@app.get("/health")
async def health():
    return {"status": "ok"}


from server.api.routes import router
app.include_router(router)


@app.get("/world")
async def get_world():
    from server.core.orchestrator import orch
    return orch.get_world_state()


@app.post("/time/advance")
async def advance_time(minutes: int = 60):
    from server.core.orchestrator import orch
    orch.advance_time(minutes)
    return orch.get_world_state()


@app.post("/time/toggle")
async def toggle_pause():
    from server.core.orchestrator import orch
    orch.time_system.toggle_pause()
    return {"is_paused": orch.time_system.is_paused}


# --- WebSocket ---
from server.api.ws import ws_manager


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


@app.websocket("/ws/llm-monitor")
async def llm_monitor_endpoint(ws: WebSocket):
    from server.llm.request_logger import llm_logger
    import asyncio

    await ws.accept()
    queue = llm_logger.subscribe()
    try:
        # 先推送已有记录
        for entry in llm_logger.get_recent(50):
            await ws.send_json({"type": "log", "data": entry})
        # 持续推送新记录
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=30)
                await ws.send_json({"type": "log", "data": llm_logger._to_dict(entry)})
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        llm_logger.unsubscribe(queue)


# --- 静态文件（前端构建产物，挂载在最后避免拦截 API 路由）---
_dist = _PROJECT_ROOT / "client" / "dist"
_img = _PROJECT_ROOT / "img"

if _img.is_dir():
    app.mount("/img", StaticFiles(directory=str(_img)), name="images")


@app.get("/llm-monitor")
async def llm_monitor_page():
    from fastapi.responses import FileResponse
    return FileResponse(_PROJECT_ROOT / "client" / "llm-monitor.html")


if _dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
