from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import create_router
from .core.config import get_config
from .core.logger import setup_logging
from .services.document_processor import DocumentProcessor
from .services.task_manager import TaskManager


from .core.db import init_db

setup_logging()
config = get_config()
task_manager = TaskManager(ttl_minutes=config.storage.cleanup_minutes)
processor = DocumentProcessor(config=config, task_manager=task_manager)

app = FastAPI(title="PDF Simplifier", version="1.0.0")

@app.on_event("startup")
def on_startup():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .api.auth import router as auth_router

# ...

app.include_router(auth_router, prefix="/api/auth")
app.include_router(create_router(task_manager, processor))


@app.get("/health")
async def healthcheck() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
async def ensure_storage() -> None:
    from .core.db import init_db
    init_db()
    Path(config.storage.temp_dir).mkdir(parents=True, exist_ok=True)
    asyncio.create_task(run_cleanup_task())


async def run_cleanup_task() -> None:
    while True:
        try:
            task_manager.cleanup()
        except Exception as exc:  # noqa: BLE001
            # 避免 cleanup 失败导致整个循环退出
            print(f"Cleanup failed: {exc}")
        await asyncio.sleep(60 * config.storage.cleanup_minutes)
