"""
FastAPI app: API only (no static frontend). Run from project root:
  python run_api.py
  API: http://localhost:8000
  Run the frontend separately: python run_frontend.py → http://localhost:3000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.docQ import agent

app = FastAPI(title="DocQuery RAG API", description="Chat with your documents.")

# CORS so the frontend (different port) can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://docquery-frontend.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    try:
        result = agent.invoke({"input": message})
        output = result.get("output", "")
        return DialogueResponse(response=output)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}") from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
