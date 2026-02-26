"""
GreenPulse — FastAPI Backend
Lazy imports = instant startup, no blocking
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── NO heavy imports at module level ──────────────────────────────
# Langchain / ChromaDB / RAG are imported lazily on first request
# This cuts startup from 20-40s down to ~2s

from backend.pathway_stream import get_processor, CITIES_CONFIG

app = FastAPI(title="GreenPulse", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_latest: Dict[str, Any] = {}
_ws_clients: List[WebSocket] = []
_active_cities = list(CITIES_CONFIG.keys())
_rag = None  # loaded lazily


def get_rag_lazy():
    """Import and init RAG only on first use — not at startup."""
    global _rag
    if _rag is None:
        from backend.rag import get_rag
        _rag = get_rag()
    return _rag


# ── Streaming Loop ─────────────────────────────────────────────────
async def stream_loop():
    processor = get_processor(_active_cities)
    async for batch in processor.start():
        global _latest
        _latest = batch
        payload = json.dumps({"type": "update", "data": batch})
        dead = []
        for ws in list(_ws_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in _ws_clients:
                _ws_clients.remove(ws)


@app.on_event("startup")
async def startup():
    # Kick off RAG loading in background immediately at startup
    # so it's ready by the time user opens browser
    def _preload_rag():
        try:
            get_rag_lazy()
        except Exception:
            pass
    import threading
    threading.Thread(target=_preload_rag, daemon=True).start()

    asyncio.create_task(stream_loop())
    print("✅ GreenPulse streaming started")


# ── WebSocket ──────────────────────────────────────────────────────
@app.websocket("/ws/stream")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    if _latest:
        await websocket.send_text(json.dumps({"type": "update", "data": _latest}))
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, Exception):
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


# ── REST ───────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"service": "GreenPulse", "status": "live", "cities": list(CITIES_CONFIG.keys())}


@app.get("/api/snapshot")
def snapshot():
    return _latest or {"readings": [], "cities": {}}


@app.get("/api/cities")
def get_cities():
    return {
        "cities": [
            {"name": n, "stations": len(c["stations"]), "color": c["color"], "emoji": c["emoji"]}
            for n, c in CITIES_CONFIG.items()
        ]
    }


class CitySelection(BaseModel):
    cities: List[str]


@app.post("/api/cities/select")
def select_cities(req: CitySelection):
    global _active_cities
    _active_cities = [c for c in req.cities if c in CITIES_CONFIG]
    processor = get_processor(_active_cities)
    processor.cities = _active_cities
    return {"status": "ok", "active": _active_cities}


class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    rag = get_rag_lazy()
    live = _latest or {}

    async def generate():
        async for token in rag.query_stream(req.question, live):
            yield f"data: {json.dumps({'token': token})}\n\n"
        sources = rag.get_sources(req.question)
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat")
async def chat(req: ChatRequest):
    rag = get_rag_lazy()
    live = _latest or {}
    answer = ""
    async for token in rag.query_stream(req.question, live):
        answer += token
    return {"answer": answer, "sources": rag.get_sources(req.question)}


@app.get("/api/rag/status")
def rag_status():
    """Check if RAG is ready without triggering load."""
    global _rag
    return {
        "loaded": _rag is not None,
        "ready": getattr(_rag, "_ready", False) if _rag else False,
        "error": getattr(_rag, "_init_error", None) if _rag else None,
    }


@app.post("/api/rag/preload")
def preload_rag():
    """Trigger RAG loading on page load so it's ready when user wants to chat."""
    def _trigger_load():
        try:
            get_rag_lazy()
        except Exception:
            pass
    import threading
    threading.Thread(target=_trigger_load, daemon=True).start()
    return {"status": "loading_triggered"}


# ── Frontend ───────────────────────────────────────────────────────
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/app")
    def serve_app():
        return FileResponse(str(frontend_dir / "index.html"))
