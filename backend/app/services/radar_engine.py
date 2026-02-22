"""Paper Radar Engine — 自动扫描 arXiv 发现新论文并处理"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import arxiv
import httpx
from sqlmodel import Session, select

from ..core.config import AppConfig
from ..core.db import engine as db_engine
from ..models.knowledge import PaperKnowledge

logger = logging.getLogger(__name__)

RELEVANCE_PROMPT = (
    "You are an expert AI research paper evaluator. Given a paper's title and abstract, "
    "score its relevance to the following research topics on a scale of 0.0 to 1.0.\n\n"
    "Topics of interest: {topics}\n\n"
    "Respond ONLY with a JSON object: {{\"score\": 0.85, \"reason\": \"brief reason\"}}\n"
)


class RadarEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.radar_cfg = config.radar
        self._running = False
        self._last_scan: datetime | None = None
        self._next_scan: datetime | None = None
        self._scan_count = 0
        self._papers_found = 0
        self._recent_papers: list[dict] = []
        self._task_manager = None
        self._processor = None

    def set_processor(self, task_manager, processor):
        self._task_manager = task_manager
        self._processor = processor

    @property
    def status(self) -> dict:
        return {
            "enabled": self.radar_cfg.enabled,
            "running": self._running,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
            "next_scan": self._next_scan.isoformat() if self._next_scan else None,
            "scan_count": self._scan_count,
            "papers_found": self._papers_found,
            "categories": self.radar_cfg.categories,
            "interval_hours": self.radar_cfg.interval_hours,
            "recent_papers": self._recent_papers[-10:],
        }

    async def start_loop(self) -> None:
        """启动时立即扫描一次，然后每整点扫描"""
        if not self.radar_cfg.enabled:
            logger.info("Radar engine disabled")
            return
        logger.info("Radar engine started — categories: %s", self.radar_cfg.categories)

        # 启动立即扫描
        await self._scan_and_process()

        # 然后等到下一个整点
        while True:
            now = datetime.utcnow()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            wait_seconds = (next_hour - now).total_seconds()
            self._next_scan = next_hour
            logger.info("Radar next scan at %s (in %.0fs)", next_hour.isoformat(), wait_seconds)
            await asyncio.sleep(wait_seconds)
            await self._scan_and_process()

    async def _scan_and_process(self) -> None:
        """扫描 + 自动处理前 3 篇"""
        try:
            papers = await self.scan()
            if papers and self._task_manager and self._processor:
                await self._auto_process(papers[:3])
        except Exception:
            logger.exception("Radar scan+process failed")

    async def scan(self) -> list[dict]:
        """执行一次扫描：arXiv → LLM 评分 → 去重 → 返回高相关论文"""
        self._running = True
        logger.info("Radar scan started")
        try:
            candidates = await asyncio.to_thread(self._fetch_arxiv)
            logger.info("arXiv returned %d candidates", len(candidates))
            if not candidates:
                self._last_scan = datetime.utcnow()
                self._scan_count += 1
                return []

            # 去重：排除已在知识库中的论文
            candidates = self._deduplicate(candidates)
            if not candidates:
                logger.info("All candidates already in knowledge base")
                self._last_scan = datetime.utcnow()
                self._scan_count += 1
                return []

            scored = await self._score_papers(candidates)
            threshold = self.radar_cfg.relevance_threshold
            relevant = [p for p in scored if p.get("score", 0) >= threshold]
            relevant.sort(key=lambda p: p.get("score", 0), reverse=True)
            relevant = relevant[:self.radar_cfg.max_papers_per_scan]

            self._last_scan = datetime.utcnow()
            self._scan_count += 1
            self._papers_found += len(relevant)
            self._recent_papers.extend(relevant)
            self._recent_papers = self._recent_papers[-20:]  # keep last 20
            logger.info("Radar found %d relevant papers", len(relevant))

            # Send notifications
            if relevant:
                await self._notify(relevant)

            return relevant
        finally:
            self._running = False

    def _deduplicate(self, candidates: list[dict]) -> list[dict]:
        """排除已在知识库中的论文（按 arxiv_id）"""
        with Session(db_engine) as session:
            existing = session.exec(select(PaperKnowledge.arxiv_id)).all()
        existing_ids = {aid for aid in existing if aid}
        return [p for p in candidates if p["arxiv_id"] not in existing_ids]

    async def _auto_process(self, papers: list[dict]) -> None:
        """自动下载并处理论文（串行，避免资源冲突）"""
        for p in papers:
            try:
                pdf_url = p.get("pdf_url", "")
                if not pdf_url:
                    continue
                title = p.get("title", "unknown")[:60]
                filename = f"radar_{p['arxiv_id']}.pdf"
                logger.info("Radar auto-processing: %s", title)

                pdf_bytes = await self._download_pdf(pdf_url)
                if not pdf_bytes:
                    logger.warning("Skipping %s: PDF download failed", p["arxiv_id"])
                    continue

                task = self._task_manager.create_task(filename, mode="translate", highlight=True)
                dest = Path(self._task_manager.config.storage.temp_dir) / f"{task.task_id}_original.pdf"
                dest.write_bytes(pdf_bytes)
                self._task_manager.update_original_path(task.task_id, str(dest))

                llm_cfg = {
                    "base_url": self.config.llm.base_url,
                    "api_key": self.config.llm.api_key,
                    "model": self.config.llm.model,
                }
                # Process synchronously to avoid font download race conditions
                try:
                    await self._processor.process(task.task_id, pdf_bytes, filename, mode="translate", highlight=True, llm_config=llm_cfg)
                    p["task_id"] = task.task_id
                    p["status"] = "completed"
                    logger.info("Radar processed: %s", title)
                except Exception:
                    logger.exception("Radar processing failed for %s, cleaning up", p["arxiv_id"])
                    p["status"] = "error"
                    # Auto-cleanup failed radar tasks so they don't clutter the UI
                    try:
                        self._task_manager.delete_task(task.task_id)
                    except Exception:
                        pass
            except Exception:
                logger.exception("Failed to auto-process paper %s", p.get("arxiv_id"))

    async def _download_pdf(self, pdf_url: str) -> bytes | None:
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(pdf_url)
                resp.raise_for_status()
                return resp.content
        except Exception:
            logger.exception("Failed to download PDF: %s", pdf_url)
            return None

    def _fetch_arxiv(self) -> list[dict]:
        papers = []
        for cat in self.radar_cfg.categories:
            try:
                client = arxiv.Client()
                search = arxiv.Search(
                    query=f"cat:{cat}",
                    max_results=50,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=arxiv.SortOrder.Descending,
                )
                cutoff = datetime.utcnow() - timedelta(hours=72)
                for result in client.results(search):
                    pub = result.published.replace(tzinfo=None)
                    if pub < cutoff:
                        break
                    papers.append({
                        "arxiv_id": result.entry_id.split("/")[-1],
                        "title": result.title,
                        "abstract": result.summary[:500],
                        "authors": [a.name for a in result.authors[:5]],
                        "published": pub.isoformat(),
                        "pdf_url": result.pdf_url,
                        "categories": [cat],
                    })
            except Exception:
                logger.exception("Failed to fetch arXiv category %s", cat)
        seen = set()
        unique = []
        for p in papers:
            if p["arxiv_id"] not in seen:
                seen.add(p["arxiv_id"])
                unique.append(p)
        return unique

    async def _score_papers(self, papers: list[dict]) -> list[dict]:
        cfg = self.config.llm
        if not cfg.api_key:
            for p in papers:
                p["score"] = 1.0
            return papers

        async with httpx.AsyncClient(base_url=cfg.base_url, timeout=60.0) as client:
            sem = asyncio.Semaphore(5)

            async def score_one(paper: dict) -> dict:
                async with sem:
                    try:
                        prompt = RELEVANCE_PROMPT.format(topics=self.radar_cfg.topics)
                        user_msg = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"
                        resp = await client.post(
                            "/chat/completions",
                            json={"model": cfg.model, "messages": [
                                {"role": "system", "content": prompt},
                                {"role": "user", "content": user_msg},
                            ], "temperature": 0.1, "max_tokens": 100},
                            headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
                        )
                        resp.raise_for_status()
                        raw = resp.json()["choices"][0]["message"]["content"]
                        # Handle thinking models that may have empty content
                        if not raw or not raw.strip():
                            paper["score"] = 0.8
                            paper["reason"] = "model returned empty, included by default"
                            return paper
                        content = raw.strip()
                        if content.startswith("```"):
                            lines = content.split("\n")
                            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                        # Try to find JSON in response
                        start = content.find("{")
                        end = content.rfind("}")
                        if start != -1 and end != -1:
                            data = json.loads(content[start:end + 1])
                        else:
                            data = json.loads(content)
                        paper["score"] = float(data.get("score", 0))
                        paper["reason"] = data.get("reason", "")
                    except Exception as e:
                        logger.warning("Score failed for %s: %s", paper["arxiv_id"], e)
                        paper["score"] = 0.8
                        paper["reason"] = "scoring failed, included by default"
                    return paper

            return await asyncio.gather(*[score_one(p) for p in papers])

    async def _notify(self, papers: list[dict]) -> None:
        try:
            from .notification import NotificationService
            svc = NotificationService(self.config.notification)
            await svc.notify_new_papers(papers)
        except Exception:
            logger.exception("Notification failed")


# Global instance
_radar_instance: RadarEngine | None = None
