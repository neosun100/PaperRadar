from __future__ import annotations

import asyncio
import json
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
    version="3.8.0",
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
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "An unexpected error occurred"})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


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
    # Vector stats
    vec_stats = {}
    try:
        from .services.vector_search import get_vector_service
        vs = get_vector_service()
        if vs:
            vec_stats = vs.stats
    except Exception:
        pass
    return {
        "status": "ok",
        "version": "3.8.0",
        "uptime_seconds": uptime,
        "total_tasks": total_tasks,
        "total_papers": total_papers,
        "vector": vec_stats,
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
            if t.original_pdf_path and Path(t.original_pdf_path).exists():
                t.status = TaskStatus.PENDING
                t.percent = 0
                t.message = "Queued (reset after restart)"
            else:
                t.status = TaskStatus.ERROR
                t.message = "Lost during restart (PDF not found)"
            session.add(t)
        # Also mark very old pending tasks as error (stuck > 24h)
        from datetime import datetime, timedelta
        old_pending = session.exec(
            select(Task).where(Task.status == TaskStatus.PENDING)
        ).all()
        for t in old_pending:
            if t.created_at and (datetime.utcnow() - t.created_at).total_seconds() > 86400:
                t.status = TaskStatus.ERROR
                t.message = "Timed out (pending > 24h)"
                session.add(t)
                stuck.append(t)
        if stuck:
            session.commit()
            logger.info("Reset %d zombie/stale tasks after restart", len(stuck))

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
        requeued = set()
        for t in pending_tasks[:1]:  # Process max 1 at startup to avoid duplicates
            if t.filename in requeued:
                continue
            requeued.add(t.filename)
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

    # Initialize vector search and index existing papers
    if config.llm.embedding_model:
        from .services.vector_search import get_vector_service
        from .models.knowledge import PaperKnowledge as PK_model
        vs = get_vector_service()

        async def _init_vector():
            if vs and vs.stats["chunks"] == 0:
                with Session(db_eng) as session:
                    completed = session.exec(
                        select(PK_model).where(PK_model.extraction_status == "completed")
                    ).all()
                for p in completed:
                    if p.knowledge_json:
                        try:
                            await vs.index_paper(p.id, json.loads(p.knowledge_json))
                        except Exception:
                            logger.warning("Failed to index paper %s", p.id)
                logger.info("Vector index initialized: %s", vs.stats)
        asyncio.create_task(_init_vector())

    # Start daily digest scheduler
    if config.notification.digest_hour >= 0:
        async def _digest_loop():
            import datetime
            from .services.notification import NotificationService
            notif = NotificationService(config.notification)
            while True:
                now = datetime.datetime.utcnow()
                target = now.replace(hour=config.notification.digest_hour, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += datetime.timedelta(days=1)
                wait_secs = (target - now).total_seconds()
                logger.info("Daily digest scheduled in %.0f seconds (UTC %02d:00)", wait_secs, config.notification.digest_hour)
                await asyncio.sleep(wait_secs)
                # Generate and send digest
                try:
                    from .models.knowledge import PaperKnowledge as PK_model
                    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=1)
                    with Session(db_eng) as session:
                        new_papers = session.exec(
                            select(PK_model).where(PK_model.created_at >= cutoff)
                        ).all()
                    if new_papers:
                        papers_for_notif = [{"title": p.title, "score": 0, "pdf_url": "", "authors": []} for p in new_papers[:10]]
                        await notif.notify_new_papers(papers_for_notif)
                        logger.info("Daily digest sent: %d papers", len(new_papers))
                except Exception:
                    logger.exception("Daily digest failed")
        asyncio.create_task(_digest_loop())
