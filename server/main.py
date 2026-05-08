from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Agent Village")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


from server.core.orchestrator import Orchestrator

orch = Orchestrator()


@app.get("/world")
async def get_world():
    return orch.get_world_state()


@app.post("/time/advance")
async def advance_time(minutes: int = 60):
    orch.advance_time(minutes)
    return orch.get_world_state()


@app.post("/time/toggle")
async def toggle_pause():
    orch.time_system.toggle_pause()
    return {"is_paused": orch.time_system.is_paused}
