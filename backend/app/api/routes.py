from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.config import get_config
from ..models.task import TaskStatus
from ..services.document_processor import DocumentProcessor
from ..services.task_manager import TaskManager
from .deps import get_llm_config, get_client_id

logger = logging.getLogger(__name__)


class TestConnectionRequest(BaseModel):
    base_url: str = ""
    api_key: str
    model: str = ""


def create_router(task_manager: TaskManager, processor: DocumentProcessor) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["documents"])
    cfg = get_config()
    # Per-client semaphores: each user (identified by API key prefix) gets their own concurrency limit
    _client_semaphores: dict[str, asyncio.Semaphore] = {}
    _max_concurrent = cfg.processing.max_concurrent
    _queue: list[str] = []  # track queued task_ids for position info
    limiter = Limiter(key_func=get_remote_address)

    def _get_semaphore(client_id: str) -> asyncio.Semaphore:
        if client_id not in _client_semaphores:
            _client_semaphores[client_id] = asyncio.Semaphore(_max_concurrent)
        return _client_semaphores[client_id]

    @router.post("/upload")
    @limiter.limit("10/minute")
    async def upload_pdf(
        request: Request,
        file: UploadFile = File(...),
        mode: str = Form("translate"),
        highlight: bool = Form(False),
    ) -> dict[str, Any]:
        llm_config = get_llm_config(request)
        client_id = get_client_id(request)

        if mode not in ("translate", "simplify", "zh2en"):
            raise HTTPException(status_code=400, detail="mode must be 'translate', 'simplify', or 'zh2en'")
        if file.content_type not in {"application/pdf", "application/octet-stream"}:
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File is empty")

        task = task_manager.create_task(file.filename or "document.pdf", mode=mode, highlight=highlight)

        original_path = Path(task_manager.config.storage.temp_dir) / f"{task.task_id}_original.pdf"
        with open(original_path, "wb") as f:
            f.write(file_bytes)
        task_manager.update_original_path(task.task_id, str(original_path))

        _queue.append(task.task_id)
        queue_pos = len(_queue)
        if queue_pos > _max_concurrent:
            task_manager.update_progress(
                task.task_id, TaskStatus.PENDING, 0,
                f"Queued (position {queue_pos - _max_concurrent})"
            )

        sem = _get_semaphore(client_id)

        async def _process_with_limit() -> None:
            async with sem:
                if task.task_id in _queue:
                    _queue.remove(task.task_id)
                await processor.process(task.task_id, file_bytes, task.filename, mode=mode, highlight=highlight, llm_config=llm_config)

        asyncio.create_task(_process_with_limit())
        return {"task_id": task.task_id}

    @router.post("/upload-url")
    async def upload_from_url(request: Request) -> dict[str, Any]:
        """Upload a paper by arXiv URL or ID"""
        llm_config = get_llm_config(request)
        body = await request.json()
        url_or_id = body.get("url", "").strip()
        mode = body.get("mode", "translate")
        highlight = body.get("highlight", True)

        if not url_or_id:
            raise HTTPException(400, "url is required")

        # Extract arXiv ID from various URL formats
        import re
        arxiv_id = None
        patterns = [
            r"arxiv\.org/abs/(\d+\.\d+(?:v\d+)?)",
            r"arxiv\.org/pdf/(\d+\.\d+(?:v\d+)?)",
            r"^(\d{4}\.\d{4,5}(?:v\d+)?)$",
        ]
        for pat in patterns:
            m = re.search(pat, url_or_id)
            if m:
                arxiv_id = m.group(1)
                break
        if not arxiv_id:
            raise HTTPException(400, "Could not parse arXiv ID from URL")

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        filename = f"arxiv_{arxiv_id}.pdf"

        # Download PDF
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(pdf_url)
            if resp.status_code != 200:
                raise HTTPException(400, f"Failed to download PDF: HTTP {resp.status_code}")
            file_bytes = resp.content

        task = task_manager.create_task(filename, mode=mode, highlight=highlight)
        original_path = Path(task_manager.config.storage.temp_dir) / f"{task.task_id}_original.pdf"
        with open(original_path, "wb") as f:
            f.write(file_bytes)
        task_manager.update_original_path(task.task_id, str(original_path))

        client_id = get_client_id(request)
        sem = _get_semaphore(client_id)

        async def _process():
            async with sem:
                await processor.process(task.task_id, file_bytes, filename, mode=mode, highlight=highlight, llm_config=llm_config)

        asyncio.create_task(_process())
        return {"task_id": task.task_id, "arxiv_id": arxiv_id}

    _CN_TO_EN = {"正在使用 AI 翻译": "AI translating", "正在使用 AI 简化": "AI simplifying",
                 "正在生成 PDF": "Generating PDF", "正在准备翻译": "Preparing to translate",
                 "正在准备简化": "Preparing to simplify", "正在使用 AI 标注关键句": "AI highlighting key sentences",
                 "页": "pages", "生成完成": "Completed", "处理失败": "Processing failed"}

    def _sanitize_msg(msg: str) -> str:
        if not msg:
            return msg
        for cn, en in _CN_TO_EN.items():
            msg = msg.replace(cn, en)
        return msg

    @router.get("/tasks")
    async def list_tasks() -> list[dict[str, Any]]:
        tasks = task_manager.list_tasks()
        return [
            {
                "task_id": t.task_id,
                "filename": t.filename,
                "status": t.status,
                "created_at": t.created_at,
                "percent": t.percent,
                "message": _sanitize_msg(t.message or ""),
                "mode": t.mode,
                "highlight": t.highlight,
            }
            for t in tasks
        ]

    @router.get("/queue")
    async def queue_status() -> dict[str, int]:
        tasks = task_manager.list_tasks(limit=200)
        active_statuses = {TaskStatus.PARSING, TaskStatus.REWRITING, TaskStatus.RENDERING, TaskStatus.HIGHLIGHTING}
        processing = sum(1 for t in tasks if t.status in active_statuses)
        queued = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
        return {"processing": processing, "queued": queued, "max_concurrent": _max_concurrent}

    @router.get("/status/{task_id}")
    async def get_status(task_id: str) -> dict[str, Any]:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        progress = task.progress
        result: dict[str, Any] = {
            "status": progress.status,
            "percent": progress.percent,
            "message": progress.message,
            "error": progress.error,
        }
        if task.highlight_stats:
            result["highlight_stats"] = json.loads(task.highlight_stats)
        return result

    @router.get("/result/{task_id}/preview", response_class=HTMLResponse)
    async def get_preview(task_id: str) -> str:
        task = task_manager.get_task(task_id)
        if not task or task.status != TaskStatus.COMPLETED:
            raise HTTPException(status_code=404, detail="Result not ready")
        if not task.result_preview_html:
            raise HTTPException(status_code=404, detail="No preview available")
        return task.result_preview_html

    @router.get("/result/{task_id}/pdf")
    async def download_pdf(task_id: str):
        task = task_manager.get_task(task_id)
        if not task or task.status != TaskStatus.COMPLETED:
            raise HTTPException(status_code=404, detail="Result not ready")
        if not task.result_pdf_path or not Path(task.result_pdf_path).exists():
            raise HTTPException(status_code=404, detail="PDF not found or expired")
        return FileResponse(task.result_pdf_path, media_type="application/pdf", filename=f"processed_{task.filename}")

    @router.delete("/tasks/{task_id}")
    async def delete_task(task_id: str) -> dict[str, str]:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task_manager.delete_task(task_id)
        return {"status": "deleted"}

    @router.get("/original/{task_id}/pdf")
    async def get_original_pdf(task_id: str):
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if not task.original_pdf_path or not Path(task.original_pdf_path).exists():
            raise HTTPException(status_code=404, detail="Original file not found or expired")
        return FileResponse(task.original_pdf_path, media_type="application/pdf", filename=f"original_{task.filename}")

    @router.get("/status/{task_id}/stream")
    async def stream_status(task_id: str):
        """SSE endpoint for real-time task progress."""
        from starlette.responses import StreamingResponse

        async def event_generator():
            prev = ""
            while True:
                task = task_manager.get_task(task_id)
                if not task:
                    yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                    return
                payload = json.dumps({
                    "status": task.status,
                    "percent": task.percent,
                    "message": task.message,
                    "error": task.error,
                })
                if payload != prev:
                    yield f"data: {payload}\n\n"
                    prev = payload
                if task.status in (TaskStatus.COMPLETED, TaskStatus.ERROR):
                    return
                await asyncio.sleep(1)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @router.post("/test-connection")
    @limiter.limit("10/minute")
    async def test_connection(request: Request, body: TestConnectionRequest) -> dict[str, Any]:
        """Test LLM API connection with user-provided credentials."""
        base_url = body.base_url or "https://api.openai.com/v1"
        start = time.time()
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                resp = await client.post(
                    "/chat/completions",
                    json={
                        "model": body.model or "gpt-4o",
                        "messages": [{"role": "user", "content": "Say hi"}],
                        "max_tokens": 5,
                    },
                    headers={"Authorization": f"Bearer {body.api_key}", "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                latency_ms = int((time.time() - start) * 1000)
                model_used = data.get("model", body.model or "unknown")
                return {"status": "ok", "model": model_used, "latency_ms": latency_ms}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "detail": f"API returned {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"status": "error", "detail": str(e)[:200]}

    # ------------------------------------------------------------------
    # Radar
    # ------------------------------------------------------------------

    @router.get("/radar/status")
    async def radar_status() -> dict[str, Any]:
        from ..services.radar_engine import _radar_instance
        if _radar_instance is None:
            return {"enabled": False, "running": False}
        return _radar_instance.status

    @router.get("/radar/trending")
    async def radar_trending(days: int = 7) -> dict[str, Any]:
        """Get trending papers from HuggingFace over N days"""
        from datetime import datetime, timedelta
        papers = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(min(days, 30)):
                date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                try:
                    resp = await client.get("https://huggingface.co/api/daily_papers", params={"date": date, "limit": 50})
                    if resp.status_code == 200:
                        for item in resp.json():
                            p = item.get("paper", {})
                            if p.get("id"):
                                papers.append({
                                    "arxiv_id": p["id"],
                                    "title": p.get("title", ""),
                                    "upvotes": p.get("upvotes", 0),
                                    "authors": [a.get("name", "") for a in (p.get("authors") or [])[:3]],
                                    "published": p.get("publishedAt", ""),
                                    "pdf_url": f"https://arxiv.org/pdf/{p['id']}.pdf",
                                    "date": date,
                                })
                except Exception:
                    pass
        # Deduplicate and sort by upvotes
        seen = set()
        unique = []
        for p in papers:
            if p["arxiv_id"] not in seen:
                seen.add(p["arxiv_id"])
                unique.append(p)
        unique.sort(key=lambda x: x.get("upvotes", 0), reverse=True)
        return {"papers": unique[:50], "days": days, "total": len(unique)}

    @router.post("/radar/scan")
    async def trigger_radar_scan() -> dict[str, Any]:
        from ..services.radar_engine import _radar_instance
        if _radar_instance is None:
            raise HTTPException(400, "Radar engine not enabled")
        papers = await _radar_instance.scan()
        return {"found": len(papers), "papers": papers}

    @router.post("/radar/topics")
    async def update_radar_topics(request: Request) -> dict[str, Any]:
        """Update radar topics at runtime (no restart needed)"""
        from ..services.radar_engine import _radar_instance
        if _radar_instance is None:
            raise HTTPException(400, "Radar engine not enabled")
        body = await request.json()
        topics = body.get("topics", "")
        if topics:
            _radar_instance.radar_cfg.topics = topics
        return {"topics": _radar_instance.radar_cfg.topics}

    @router.get("/radar/recommendations")
    async def get_recommendations() -> dict[str, Any]:
        """Get paper recommendations based on knowledge base papers"""
        from sqlmodel import Session, select
        from ..core.db import engine as db_eng
        from ..models.knowledge import PaperKnowledge
        # Get arxiv IDs from knowledge base
        with Session(db_eng) as session:
            papers = session.exec(select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")).all()
        if not papers:
            return {"recommendations": [], "message": "No papers in knowledge base yet"}

        # Get S2 paper IDs for our papers
        arxiv_ids = [p.arxiv_id for p in papers if p.arxiv_id][:5]
        if not arxiv_ids:
            return {"recommendations": [], "message": "No arXiv IDs found"}

        # Call S2 recommendations API
        s2_ids = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for aid in arxiv_ids:
                try:
                    resp = await client.get(f"https://api.semanticscholar.org/graph/v1/paper/ArXiv:{aid}", params={"fields": "paperId"})
                    if resp.status_code == 200:
                        s2_ids.append(resp.json().get("paperId", ""))
                except Exception:
                    pass
                if len(s2_ids) >= 3:
                    break

        if not s2_ids:
            return {"recommendations": [], "message": "Could not resolve paper IDs"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.semanticscholar.org/recommendations/v1/papers/",
                    params={"limit": 10, "fields": "paperId,externalIds,title,abstract,citationCount,year,authors"},
                    json={"positivePaperIds": s2_ids},
                )
                if resp.status_code == 200:
                    recs = resp.json().get("recommendedPapers", [])
                    results = []
                    for r in recs:
                        aid = (r.get("externalIds") or {}).get("ArXiv", "")
                        results.append({
                            "arxiv_id": aid,
                            "title": r.get("title", ""),
                            "abstract": (r.get("abstract") or "")[:300],
                            "citations": r.get("citationCount", 0),
                            "year": r.get("year"),
                            "authors": [a.get("name", "") for a in (r.get("authors") or [])[:3]],
                            "pdf_url": f"https://arxiv.org/pdf/{aid}.pdf" if aid else "",
                        })
                    return {"recommendations": results, "based_on": len(s2_ids)}
        except Exception:
            pass
        return {"recommendations": [], "message": "Recommendation API unavailable"}

    return router
