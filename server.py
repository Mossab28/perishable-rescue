"""Lightweight FastAPI backend. Serves the single-page visual demo and streams a live
pipeline run to the browser over Server-Sent Events (SSE). Runs fully offline.
"""
import json
import queue
import threading

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse

import config
from orchestrator import run_pipeline

app = FastAPI(title="Perishable Rescue + Equity Coordinator")
FRONTEND = config.ROOT / "frontend" / "index.html"


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND.read_text()


@app.get("/config")
def get_config():
    return {"llm_enabled": config.LLM_ENABLED, "model": config.OPENAI_MODEL,
            "run_date": config.RUN_DATE}


@app.get("/run")
def run(fresh: int = 0, persist: int = 0):
    """Stream a real pipeline run as SSE. Each agent event is forwarded as it happens."""
    q: "queue.Queue" = queue.Queue()
    SENTINEL = object()

    def emit(event: dict):
        q.put(event)

    def worker():
        try:
            run_pipeline(emit_cb=emit, fresh=bool(fresh), persist_learning=bool(persist))
        except Exception as e:  # never let the stream hang on an error
            q.put({"type": "error", "message": str(e)})
        finally:
            q.put(SENTINEL)

    threading.Thread(target=worker, daemon=True).start()

    def event_stream():
        while True:
            item = q.get()
            if item is SENTINEL:
                yield "event: end\ndata: {}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    import uvicorn
    print("→ open http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
