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

        # 启动时扫描（可配置）
        if self.radar_cfg.scan_on_startup:
            await self._scan_and_process()
        else:
            logger.info("Radar: skip startup scan (scan_on_startup=false)")

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
        """扫描 + 仅在队列空闲时处理新论文"""
        try:
            # Check how many tasks are currently active
            from ..models.task import TaskStatus
            active_statuses = {TaskStatus.PARSING, TaskStatus.REWRITING, TaskStatus.RENDERING, TaskStatus.HIGHLIGHTING, TaskStatus.PENDING}
            tasks = self._task_manager.list_tasks(limit=200)
            active_count = sum(1 for t in tasks if t.status in active_statuses)

            if active_count >= 3:
                logger.info("Radar: %d tasks active, skipping auto-process (will scan only)", active_count)
                await self.scan()  # Still scan to discover papers, just don't process
                return

            papers = await self.scan()
            if papers and self._task_manager and self._processor:
                slots = max(0, 3 - active_count)
                if slots > 0:
                    asyncio.create_task(self._auto_process(papers[:slots]))
        except Exception:
            logger.exception("Radar scan failed")

    async def scan(self) -> list[dict]:
        """执行一次扫描：arXiv + Semantic Scholar → LLM 评分 → 去重 → 返回高相关论文"""
        self._running = True
        logger.info("Radar scan started")
        try:
            # Fetch from multiple sources
            arxiv_papers = await asyncio.to_thread(self._fetch_arxiv)
            s2_papers = await self._fetch_semantic_scholar()
            hf_papers = await self._fetch_huggingface_daily()
            
            # Merge and deduplicate by arxiv_id
            seen = set()
            candidates = []
            for p in arxiv_papers + s2_papers + hf_papers:
                aid = p.get("arxiv_id", "")
                if aid and aid not in seen:
                    seen.add(aid)
                    candidates.append(p)
            
            logger.info("Sources: arXiv=%d, S2=%d, HF=%d, merged=%d",
                        len(arxiv_papers), len(s2_papers), len(hf_papers), len(candidates))
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

            # Ensure diversity: at least 1 paper from each source if available
            sources_in_top = {p.get("source") for p in relevant}
            all_sources = {p.get("source") for p in scored if p.get("score", 0) >= threshold}
            for src in all_sources - sources_in_top:
                src_papers = [p for p in scored if p.get("source") == src and p.get("score", 0) >= threshold]
                if src_papers:
                    relevant.append(max(src_papers, key=lambda p: p.get("score", 0)))

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
        """排除已在知识库、任务队列或本次运行已发现的论文"""
        from ..models.task import Task
        with Session(db_engine) as session:
            existing_kb = session.exec(select(PaperKnowledge.arxiv_id)).all()
            existing_tasks = session.exec(select(Task.filename)).all()
        existing_ids = {aid for aid in existing_kb if aid}
        # Check task filenames for arxiv IDs
        for fn in existing_tasks:
            if fn:
                # Match radar_XXXX.pdf or arxiv_XXXX.pdf patterns
                for prefix in ("radar_", "arxiv_"):
                    if fn.startswith(prefix):
                        existing_ids.add(fn.replace(prefix, "").replace(".pdf", ""))
        # Also exclude papers already discovered in this session
        for p in self._recent_papers:
            existing_ids.add(p.get("arxiv_id", ""))
        return [p for p in candidates if p["arxiv_id"] not in existing_ids]

    async def _auto_process(self, papers: list[dict]) -> None:
        """自动下载并处理论文（串行）：翻译 → 高亮 → 知识提取"""
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
                # Store paper title as filename for better UI display
                title_clean = p.get("title", "")[:80].replace("/", "-").replace("\\", "-")
                if title_clean:
                    self._task_manager.update_task_filename(task.task_id, f"{title_clean}.pdf")
                dest = Path(self._task_manager.config.storage.temp_dir) / f"{task.task_id}_original.pdf"
                dest.write_bytes(pdf_bytes)
                self._task_manager.update_original_path(task.task_id, str(dest))

                llm_cfg = {
                    "base_url": self.config.llm.base_url,
                    "api_key": self.config.llm.api_key,
                    "model": self.config.llm.model,
                }

                # Step 1: Translate + Highlight
                try:
                    await self._processor.process(task.task_id, pdf_bytes, filename, mode="translate", highlight=True, llm_config=llm_cfg)
                    p["task_id"] = task.task_id
                    p["status"] = "translated"
                    logger.info("Radar translated: %s", title)
                except Exception:
                    logger.exception("Radar translation failed for %s, cleaning up", p["arxiv_id"])
                    try:
                        self._task_manager.delete_task(task.task_id)
                    except Exception:
                        pass
                    continue

                # Step 2: Auto-extract knowledge
                try:
                    from .knowledge_extractor import KnowledgeExtractor
                    extractor = KnowledgeExtractor(
                        api_key=llm_cfg["api_key"], model=llm_cfg["model"], base_url=llm_cfg["base_url"],
                    )
                    async with extractor:
                        await extractor.extract(pdf_bytes, task.task_id, user_id=0)
                    p["status"] = "completed"
                    logger.info("Radar knowledge extracted: %s", title)
                except Exception:
                    logger.exception("Radar knowledge extraction failed for %s", p["arxiv_id"])
                    p["status"] = "translated"  # still usable, just no knowledge

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
                        "source": "arxiv",
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

    async def _fetch_semantic_scholar(self) -> list[dict]:
        """从 Semantic Scholar 获取近期高引用论文"""
        papers = []
        topics = self.radar_cfg.topics.split(",")[0].strip()  # Use first topic
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": topics,
                        "fields": "paperId,externalIds,title,abstract,authors,year,citationCount,publicationDate",
                        "limit": 20,
                        "sort": "citationCount:desc",
                        "publicationDateOrYear": f"{datetime.utcnow().year}-",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    for item in data:
                        arxiv_id = (item.get("externalIds") or {}).get("ArXiv", "")
                        if not arxiv_id:
                            continue
                        papers.append({
                            "arxiv_id": arxiv_id,
                            "title": item.get("title", ""),
                            "abstract": (item.get("abstract") or "")[:500],
                            "authors": [a.get("name", "") for a in (item.get("authors") or [])[:5]],
                            "published": item.get("publicationDate", ""),
                            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                            "categories": [],
                            "source": "semantic_scholar",
                            "citations": item.get("citationCount", 0),
                        })
        except Exception:
            logger.exception("Failed to fetch Semantic Scholar papers")
        return papers

    async def _fetch_huggingface_daily(self) -> list[dict]:
        """从 HuggingFace Daily Papers 获取社区策划的热门论文（按 upvotes 排序）"""
        papers = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get("https://huggingface.co/api/daily_papers", params={"limit": 50})
                if resp.status_code == 200:
                    items = resp.json()
                    # Sort by upvotes descending
                    items.sort(key=lambda x: x.get("paper", {}).get("upvotes", 0), reverse=True)
                    for item in items:
                        p = item.get("paper", {})
                        arxiv_id = p.get("id", "")
                        if not arxiv_id:
                            continue
                        upvotes = p.get("upvotes", 0)
                        papers.append({
                            "arxiv_id": arxiv_id,
                            "title": p.get("title", ""),
                            "abstract": (p.get("summary") or "")[:500],
                            "authors": [a.get("name", "") for a in (p.get("authors") or [])[:5]],
                            "published": p.get("publishedAt", ""),
                            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                            "categories": p.get("ai_keywords", [])[:3],
                            "source": "huggingface",
                            "upvotes": upvotes,
                        })
            logger.info("HuggingFace: %d papers fetched", len(papers))
        except Exception:
            logger.exception("Failed to fetch HuggingFace Daily Papers")
        return papers

    async def _score_papers(self, papers: list[dict]) -> list[dict]:
        cfg = self.config.llm
        # Build keyword list: split by comma, also add common abbreviations
        raw_topics = [t.strip().lower() for t in self.radar_cfg.topics.split(",")]
        # Expand: "large language model" also matches "llm", "llms"
        keywords = set(raw_topics)
        for t in raw_topics:
            # Add individual words for multi-word topics
            words = t.split()
            if len(words) > 1:
                keywords.update(words)
        # Common AI/ML abbreviations
        keywords.update(["llm", "llms", "rag", "rlhf", "moe", "vllm", "lora", "qlora",
                         "transformer", "attention", "fine-tuning", "finetuning", "pretraining",
                         "pre-training", "benchmark", "instruction tuning", "chain-of-thought",
                         "cot", "in-context learning", "icl", "multimodal", "vlm"])

        for p in papers:
            # HuggingFace papers: score by community upvotes
            if p.get("source") == "huggingface":
                upvotes = p.get("upvotes", 0)
                if upvotes >= 30:
                    p["score"] = 0.98
                    p["reason"] = f"🔥 HF trending ({upvotes} upvotes)"
                elif upvotes >= 10:
                    p["score"] = 0.95
                    p["reason"] = f"HF popular ({upvotes} upvotes)"
                else:
                    p["score"] = 0.85
                    p["reason"] = f"HF curated ({upvotes} upvotes)"
                continue
            # Semantic Scholar high-citation papers get a boost
            if p.get("source") == "semantic_scholar" and p.get("citations", 0) > 10:
                p["score"] = 0.9
                p["reason"] = f"High citations ({p.get('citations', 0)})"
                continue
            # Quick keyword pre-filter for arXiv papers
            title_lower = p.get("title", "").lower()
            abstract_lower = p.get("abstract", "").lower()
            text = title_lower + " " + abstract_lower
            keyword_hits = sum(1 for t in keywords if t in text)
            if keyword_hits == 0:
                p["score"] = 0.3
                p["reason"] = "No keyword match"
                continue
            if keyword_hits >= 2:
                p["score"] = 0.85
                p["reason"] = f"Multiple keyword matches ({keyword_hits})"
                continue
            # Single keyword match — use LLM for precise scoring if available
            p["_needs_llm"] = True

        # LLM scoring only for papers that need it
        needs_llm = [p for p in papers if p.get("_needs_llm")]
        if needs_llm and cfg.api_key:
            await self._llm_score_batch(needs_llm, cfg)
        else:
            for p in needs_llm:
                p["score"] = 0.75
                p["reason"] = "Single keyword match"

        # Cleanup temp flag
        for p in papers:
            p.pop("_needs_llm", None)

        return papers

    async def _llm_score_batch(self, papers: list[dict], cfg) -> None:
        """LLM 评分（仅对需要精确评分的论文）"""
        async with httpx.AsyncClient(base_url=cfg.base_url, timeout=90.0) as client:
            sem = asyncio.Semaphore(2)

            async def score_one(paper: dict) -> None:
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
                        raw = resp.json()["choices"][0]["message"].get("content", "")
                        if not raw or not raw.strip():
                            paper["score"] = 0.75
                            paper["reason"] = "LLM returned empty"
                            return
                        content = raw.strip()
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
                        paper["score"] = 0.75
                        paper["reason"] = "scoring failed"

            await asyncio.gather(*[score_one(p) for p in papers])

    async def _notify(self, papers: list[dict]) -> None:
        try:
            from .notification import NotificationService
            svc = NotificationService(self.config.notification)
            await svc.notify_new_papers(papers)
        except Exception:
            logger.exception("Notification failed")


# Global instance
_radar_instance: RadarEngine | None = None
