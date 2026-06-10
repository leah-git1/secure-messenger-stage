"""
main.py — Application entry point.

╔══════════════════════════════════════════════════════════════╗
║  THIS FILE IS COMPLETE — you do not need to change anything. ║
╚══════════════════════════════════════════════════════════════╝

This file does three things only:
  1. Creates the FastAPI app
  2. Sets up logging
  3. Registers the router from routes.py

All actual route logic lives in routes.py.
This separation is the standard pattern in production FastAPI projects.

HOW TO RUN:
  uvicorn server.main:app --reload

  Then open: http://localhost:8000 (web UI) or http://localhost:8000/docs (API docs)
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import create_tables
from .routes import router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Secure Messenger — Stage 2",
    description="Authenticated, encrypted real-time messaging with Server-Sent Events (SSE)",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS middleware ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API router (register first) ────────────────────────────────────────────
app.include_router(router)

# ── Serve static files (mount second, so /api routes take precedence) ──────
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")
