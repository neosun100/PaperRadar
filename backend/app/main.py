from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .api.routes import create_router
from .api.knowledge_routes import create_knowledge_router
from .core.config import get_config
from .core.db import init_db
from .core.logger import setup_logging
from .services.document_processor import DocumentProcessor
from .services.task_manager import TaskManager

setup_logging()
config = get_config()
task_manager = TaskManager(ttl_minutes=config.storage.cleanup_minutes)
processor = DocumentProcessor(config=config, task_manager=task_manager)

_start_time = time.time()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="PaperRadar API",
    version="3.0.0",
    description="Discover, understand, and connect cutting-edge research — automatically.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "rate_limited", "detail": "Too many requests, please try again later"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "An unexpected error occurred"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No auth router — BYOK mode
app.include_router(create_router(task_manager, processor))
app.include_router(create_knowledge_router())


@app.get("/health")
async def healthcheck() -> dict:
    uptime = int(time.time() - _start_time)
    return {"status": "ok", "version": "3.0.0", "uptime_seconds": uptime}


@app.on_event("startup")
async def on_startup() -> None:
    init_db()
    Path(config.storage.temp_dir).mkdir(parents=True, exist_ok=True)
