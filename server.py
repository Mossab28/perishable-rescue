"""Lightweight FastAPI backend. Serves the single-page visual demo and streams a live
pipeline run to the browser over Server-Sent Events (SSE). Runs fully offline.
"""
import itertools
import json
import queue
import threading

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse

import config
from orchestrator import run_pipeline

app = FastAPI(title="Perishable Rescue + Equity Coordinator")
FRONTEND = config.ROOT / "frontend" / "index.html"

# In-memory holding area for CSVs uploaded live in the browser. EventSource can't POST,
# so the client POSTs the CSV here, gets a token, then opens /run?src=<token>.
_UPLOADS: dict = {}
_UPLOAD_IDS = itertools.count(1)


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND.read_text()


@app.get("/config")
def get_config():
    return {"llm_enabled": config.LLM_ENABLED, "model": config.OPENAI_MODEL,
            "run_date": config.RUN_DATE}


@app.post("/upload")
async def upload(request: Request):
    """Accept a raw inventory CSV (text body), stash it, return a token for /run?src=."""
    text = (await request.body()).decode("utf-8", "replace")
    uid = str(next(_UPLOAD_IDS))
    _UPLOADS[uid] = text
    return {"id": uid, "bytes": len(text)}


@app.get("/run")
def run(fresh: int = 0, persist: int = 0, src: str = ""):
    """Stream a real pipeline run as SSE. Each agent event is forwarded as it happens.
    If src points to an uploaded CSV, the run uses that inventory instead of the committed file.
    """
    inventory_csv = _UPLOADS.pop(src, None) if src else None
    q: "queue.Queue" = queue.Queue()
    SENTINEL = object()

    def emit(event: dict):
        q.put(event)

    def worker():
        try:
            run_pipeline(emit_cb=emit, fresh=bool(fresh), persist_learning=bool(persist),
                         inventory_csv=inventory_csv)
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
