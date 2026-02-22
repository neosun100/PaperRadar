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
import logging
from .core.logger import setup_logging

logger = logging.getLogger(__name__)
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
    # Count tasks by status
    from sqlmodel import Session, select, func
    from .core.db import engine as db_eng
    from .models.task import Task
    from .models.knowledge import PaperKnowledge
    with Session(db_eng) as session:
        total_tasks = session.exec(select(func.count(Task.task_id))).one()
        total_papers = session.exec(select(func.count(PaperKnowledge.id))).one()
    return {
        "status": "ok",
        "version": "3.0.0",
        "uptime_seconds": uptime,
        "total_tasks": total_tasks,
        "total_papers": total_papers,
    }


@app.on_event("startup")
async def on_startup() -> None:
    init_db()
    Path(config.storage.temp_dir).mkdir(parents=True, exist_ok=True)

    # Reset zombie tasks (stuck in processing from previous container)
    from sqlmodel import Session, select
    from .core.db import engine as db_eng
    from .models.task import Task, TaskStatus
    active_statuses = [TaskStatus.PARSING, TaskStatus.REWRITING, TaskStatus.RENDERING, TaskStatus.HIGHLIGHTING]
    with Session(db_eng) as session:
        stuck = session.exec(select(Task).where(Task.status.in_(active_statuses))).all()
        for t in stuck:
            # Check if original PDF still exists — if so, reset to pending; if not, mark error
            if t.original_pdf_path and Path(t.original_pdf_path).exists():
                t.status = TaskStatus.PENDING
                t.percent = 0
                t.message = "Queued (reset after restart)"
            else:
                t.status = TaskStatus.ERROR
                t.message = "Lost during restart (PDF not found)"
            session.add(t)
        if stuck:
            session.commit()
            logger.info("Reset %d zombie tasks after restart", len(stuck))

    # Re-process pending tasks that have original PDFs (deduplicated)
    pending_tasks = []
    with Session(db_eng) as session:
        pending_tasks = session.exec(select(Task).where(Task.status == TaskStatus.PENDING)).all()
        pending_tasks = [t for t in pending_tasks if t.original_pdf_path and Path(t.original_pdf_path).exists()]
        # Deduplicate by filename — keep newest, delete rest
        seen_names = {}
        dedup_tasks = []
        for t in sorted(pending_tasks, key=lambda x: x.created_at or "", reverse=True):
            if t.filename not in seen_names:
                seen_names[t.filename] = t
                dedup_tasks.append(t)
            else:
                session.delete(t)
        if len(dedup_tasks) < len(pending_tasks):
            session.commit()
            logger.info("Removed %d duplicate pending tasks", len(pending_tasks) - len(dedup_tasks))
        pending_tasks = dedup_tasks

    if pending_tasks:
        logger.info("Re-queuing %d pending tasks for processing", len(pending_tasks))
        for t in pending_tasks[:3]:  # Process max 3 at startup
            pdf_bytes = Path(t.original_pdf_path).read_bytes()
            llm_cfg = {"base_url": config.llm.base_url, "api_key": config.llm.api_key, "model": config.llm.model}
            asyncio.create_task(
                processor.process(t.task_id, pdf_bytes, t.filename, mode=t.mode or "translate", highlight=t.highlight or False, llm_config=llm_cfg)
            )

    # Start radar engine if enabled
    if config.radar.enabled:
        from .services.radar_engine import RadarEngine, _radar_instance
        from .services import radar_engine as re_mod
        radar = RadarEngine(config)
        radar.set_processor(task_manager, processor)
        re_mod._radar_instance = radar
        asyncio.create_task(radar.start_loop())
