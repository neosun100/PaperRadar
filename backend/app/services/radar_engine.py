"""Paper Radar Engine — 自动扫描 arXiv 发现新论文并处理"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import arxiv
import httpx

from ..core.config import AppConfig

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
        self._scan_count = 0
        self._papers_found = 0

    @property
    def status(self) -> dict:
        return {
            "enabled": self.radar_cfg.enabled,
            "running": self._running,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
            "scan_count": self._scan_count,
            "papers_found": self._papers_found,
            "categories": self.radar_cfg.categories,
            "interval_hours": self.radar_cfg.interval_hours,
        }

    async def start_loop(self) -> None:
        """后台循环：每 N 小时扫描一次"""
        if not self.radar_cfg.enabled:
            logger.info("Radar engine disabled in config")
            return
        logger.info("Radar engine started — scanning every %dh, categories: %s",
                     self.radar_cfg.interval_hours, self.radar_cfg.categories)
        while True:
            try:
                await self.scan()
            except Exception:
                logger.exception("Radar scan failed")
            await asyncio.sleep(self.radar_cfg.interval_hours * 3600)

    async def scan(self) -> list[dict]:
        """执行一次扫描：arXiv 查询 → LLM 评分 → 返回高相关论文"""
        self._running = True
        logger.info("Radar scan started")
        try:
            # 1. 从 arXiv 获取最近论文
            candidates = await asyncio.to_thread(self._fetch_arxiv)
            logger.info("arXiv returned %d candidates", len(candidates))

            if not candidates:
                return []

            # 2. 用 LLM 评估相关性
            scored = await self._score_papers(candidates)

            # 3. 过滤高相关论文
            threshold = self.radar_cfg.relevance_threshold
            relevant = [p for p in scored if p.get("score", 0) >= threshold]
            relevant.sort(key=lambda p: p.get("score", 0), reverse=True)
            relevant = relevant[:self.radar_cfg.max_papers_per_scan]

            self._last_scan = datetime.utcnow()
            self._scan_count += 1
            self._papers_found += len(relevant)
            logger.info("Radar found %d relevant papers (threshold=%.1f)", len(relevant), threshold)
            return relevant
        finally:
            self._running = False

    def _fetch_arxiv(self) -> list[dict]:
        """从 arXiv 获取最近 24h 的论文"""
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
                cutoff = datetime.utcnow() - timedelta(hours=48)
                for result in client.results(search):
                    pub = result.published.replace(tzinfo=None)
                    if pub < cutoff:
                        break
                    papers.append({
                        "arxiv_id": result.entry_id.split("/")[-1],
                        "title": result.title,
                        "abstract": result.summary,
                        "authors": [a.name for a in result.authors[:5]],
                        "published": pub.isoformat(),
                        "pdf_url": result.pdf_url,
                        "categories": [cat],
                    })
            except Exception:
                logger.exception("Failed to fetch arXiv category %s", cat)
        # Deduplicate by arxiv_id
        seen = set()
        unique = []
        for p in papers:
            if p["arxiv_id"] not in seen:
                seen.add(p["arxiv_id"])
                unique.append(p)
        return unique

    async def _score_papers(self, papers: list[dict]) -> list[dict]:
        """用 LLM 批量评估论文相关性"""
        cfg = self.config.llm
        if not cfg.api_key:
            # No LLM config — return all with score 1.0
            for p in papers:
                p["score"] = 1.0
                p["reason"] = "No LLM configured, accepting all"
            return papers

        async with httpx.AsyncClient(base_url=cfg.base_url, timeout=60.0) as client:
            sem = asyncio.Semaphore(5)

            async def score_one(paper: dict) -> dict:
                async with sem:
                    try:
                        prompt = RELEVANCE_PROMPT.format(topics=self.radar_cfg.topics)
                        user_msg = f"Title: {paper['title']}\n\nAbstract: {paper['abstract'][:1500]}"
                        resp = await client.post(
                            "/chat/completions",
                            json={
                                "model": cfg.model,
                                "messages": [
                                    {"role": "system", "content": prompt},
                                    {"role": "user", "content": user_msg},
                                ],
                                "temperature": 0.1,
                                "max_tokens": 100,
                            },
                            headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
                        )
                        resp.raise_for_status()
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        if content.startswith("```"):
                            lines = content.split("\n")
                            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                        data = json.loads(content)
                        paper["score"] = float(data.get("score", 0))
                        paper["reason"] = data.get("reason", "")
                    except Exception as e:
                        logger.warning("Failed to score paper %s: %s", paper["arxiv_id"], e)
                        paper["score"] = 0.5
                        paper["reason"] = "scoring failed"
                    return paper

            tasks = [score_one(p) for p in papers]
            return await asyncio.gather(*tasks)

    async def download_pdf(self, pdf_url: str, dest_path: str) -> bytes | None:
        """下载论文 PDF"""
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(pdf_url)
                resp.raise_for_status()
                pdf_bytes = resp.content
                Path(dest_path).write_bytes(pdf_bytes)
                return pdf_bytes
        except Exception:
            logger.exception("Failed to download PDF: %s", pdf_url)
            return None


# Global instance — set by main.py on startup
_radar_instance: RadarEngine | None = None
