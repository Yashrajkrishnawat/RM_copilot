from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.loop import run_agent
from app.config import settings

app = FastAPI(title="RM Copilot")


class ChatRequest(BaseModel):
    rm_id: str
    message: str


@app.get("/health")
def health():
    return {"status": "ok", "model": settings.llm_model}


@app.post("/chat")
def chat(req: ChatRequest):
    return run_agent(req.message, req.rm_id)