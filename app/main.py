from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.agent.loop import run_agent
from app.agent.memory import memory
from app.config import settings

app = FastAPI(title="RM Copilot")
STATIC = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(STATIC / "index.html")


class ChatRequest(BaseModel):
    rm_id: str
    message: str
    session_id: str | None = None


class ResetRequest(BaseModel):
    session_id: str


@app.get("/health")
def health():
    return {"status": "ok", "model": settings.llm_model}


@app.post("/chat")
def chat(req: ChatRequest):
    return run_agent(req.message, req.rm_id, session_id=req.session_id)


@app.post("/chat/reset")
def reset(req: ResetRequest):
    memory.clear(req.session_id)
    return {"status": "cleared"}