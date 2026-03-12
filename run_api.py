#!/usr/bin/env python3
"""Run the DocQuery API from the project root. Usage: python run_api.py"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.interface:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
