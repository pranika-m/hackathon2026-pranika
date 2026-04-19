"""
main.py — FastAPI entry point for the ShopWave agent backend.

Run with: uvicorn main:app --reload --port 8000
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# =========================
# [SETUP]
# =========================

# Ensure backend directory is in path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

# =========================
# [APP]
# =========================

app = FastAPI(
    title="ShopWave Support Agent",
    description="Autonomous Support Resolution Agent API",
    version="1.0.0"
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# [ROUTES]
# =========================

from api.routes import router
app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "ShopWave Support Agent",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
