from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from api.routes_chat import router as chat_router
from api.routes_upload import router as upload_router


UI_PATH = Path(__file__).resolve().parents[1] / "ui" / "index.html"

app = FastAPI(title="Session 4 RAG", version="1.0.0")
app.include_router(upload_router)
app.include_router(chat_router)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(UI_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

