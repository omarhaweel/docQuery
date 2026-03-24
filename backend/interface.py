"""
FastAPI app: API only (no static frontend). Run from project root:
  python run_api.py
  API: http://localhost:8000
  Run the frontend separately: python run_frontend.py → http://localhost:3000
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="DocQuery RAG API", description="Chat with your documents.")

# Any Render / local origin; credentials off so "*" is valid in browsers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Heavy RAG stack loads on first use so /health stays fast for Render probes.
_agent = None
_load_error: str | None = None


def _get_agent():
    global _agent, _load_error
    if _load_error is not None:
        raise HTTPException(status_code=503, detail=_load_error)
    if _agent is not None:
        return _agent
    try:
        from backend.docQ import agent as loaded

        _agent = loaded
        return _agent
    except Exception as e:
        _load_error = f"{type(e).__name__}: {e}"
        raise HTTPException(status_code=503, detail=_load_error) from e


@app.get("/health")
def health():
    """Lightweight liveness (no doc/RAG import)."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Returns 503 with error detail if the RAG pipeline failed to initialize."""
    global _load_error
    if _load_error is not None:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "detail": _load_error},
        )
    try:
        _get_agent()
    except HTTPException as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "detail": e.detail},
        )
    return {"status": "ready"}


class DialogueRequest(BaseModel):
    """Request body for the dialogue endpoint."""
    message: str


class DialogueResponse(BaseModel):
    """Response with the agent's reply."""
    response: str


@app.post("/dialogue", response_model=DialogueResponse)
def dialogue(request: DialogueRequest) -> DialogueResponse:
    message = (request.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="please provide a message")

    agent = _get_agent()
    try:
        result = agent.invoke({"input": message})
        output = result.get("output", "")
        return DialogueResponse(response=output)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
