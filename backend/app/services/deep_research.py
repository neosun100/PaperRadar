"""Deep Research — 给定话题，自动搜索、下载、分析论文，生成专家级综合报告"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import httpx
from sqlmodel import Session, select

from ..core.config import get_config
from ..core.db import engine
from ..models.knowledge import PaperKnowledge

logger = logging.getLogger(__name__)

EXPERT_SYNTHESIS_PROMPT = """\
You are a world-class AI research scientist. You have thoroughly read and analyzed \
the following {paper_count} papers on the topic: "{topic}".

Your task: Write a comprehensive expert analysis that synthesizes ALL the papers. \
This is NOT a simple summary — you must provide genuine expert insight.

Structure your analysis as:

## Executive Summary
One paragraph capturing the state of the field.

## Key Findings & Consensus
What do the papers collectively agree on? What are the established facts?

## Methodological Landscape
What approaches are being used? Which are most promising and why?

## Contradictions & Debates
Where do papers disagree? What are the open questions?

## Frontier & Gaps
What's at the cutting edge? What hasn't been explored yet?

## Expert Assessment
YOUR expert opinion: What should a researcher focus on next? What's overhyped vs underappreciated?

## Recommended Reading Order
Rank the papers by importance for someone entering this field.

Rules:
- Cite papers as [Author, Year] or by title
- Be specific — mention actual numbers, benchmarks, model names
- Be opinionated — give genuine expert judgment, not just neutral summaries
- Write in the same language as the topic query

Papers:
{papers_context}
"""


class DeepResearchService:
    def __init__(self, llm_config: dict) -> None:
        self.api_key = llm_config["api_key"]
        self.model = llm_config.get("model", "")
        self.base_url = llm_config.get("base_url", "")
        # Use non-thinking model for synthesis
        if "-thinking" in self.model:
            self.model = self.model.replace("-thinking", "")

    async def research(self, topic: str, max_papers: int = 10) -> dict:
        """Full deep research pipeline: search → collect → synthesize."""
        # Step 1: Search Semantic Scholar
        papers_found = await self._search_papers(topic, max_papers)

        # Step 1b: Fallback to KB vector search if S2 is unavailable
        kb_matched = []
        if not papers_found:
            try:
                from .vector_search import get_vector_service
                vs = get_vector_service()
                if vs:
                    hits = await vs.search_papers(topic, n_results=max_papers)
                    with Session(engine) as session:
                        for h in hits:
                            p = session.get(PaperKnowledge, h.get("paper_id", ""))
                            if p and p.extraction_status == "completed":
                                kb_matched.append({"title": p.title or h.get("title", ""), "year": p.year, "citations": 0, "arxiv_id": p.arxiv_id or "", "abstract": "", "s2_id": ""})
                    if kb_matched:
                        papers_found = kb_matched
            except Exception:
                pass

        if not papers_found:
            return {"status": "no_papers", "topic": topic, "message": "No papers found. Try a different topic or wait for S2 rate limit to reset."}

        # Step 2: Check which papers are already in KB
        existing_ids = set()
        with Session(engine) as session:
            all_papers = session.exec(select(PaperKnowledge)).all()
            for p in all_papers:
                if p.arxiv_id:
                    existing_ids.add(p.arxiv_id)
                if p.title:
                    existing_ids.add(p.title.lower().strip())

        # Step 3: Identify new papers to process
        new_papers = []
        kb_papers = []
        for p in papers_found:
            arxiv_id = p.get("arxiv_id", "")
            title = p.get("title", "").lower().strip()
            if arxiv_id in existing_ids or title in existing_ids:
                kb_papers.append(p)
            elif arxiv_id:
                new_papers.append(p)
            else:
                kb_papers.append(p)  # No arXiv ID, can't download but include metadata

        # Step 4: Queue new papers for download (non-blocking)
        queued = []
        if new_papers:
            queued = await self._queue_papers(new_papers[:5])  # Max 5 new downloads

        # Step 5: Gather all available knowledge for synthesis
        knowledge_context = await self._gather_knowledge(topic, papers_found)

        # Step 6: Generate expert synthesis
        synthesis = await self._synthesize(topic, knowledge_context, len(papers_found))

        return {
            "status": "completed",
            "topic": topic,
            "papers_found": len(papers_found),
            "papers_in_kb": len(kb_papers),
            "papers_queued": len(queued),
            "papers": [{"title": p["title"], "year": p.get("year"), "citations": p.get("citations", 0), "arxiv_id": p.get("arxiv_id", "")} for p in papers_found],
            "synthesis": synthesis,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _search_papers(self, topic: str, limit: int) -> list[dict]:
        """Search Semantic Scholar for relevant papers, with retry on rate limit."""
        for attempt in range(3):
            async with httpx.AsyncClient(timeout=20.0) as client:
                try:
                    r = await client.get(
                        "https://api.semanticscholar.org/graph/v1/paper/search",
                        params={"query": topic, "limit": min(limit, 20), "fields": "title,year,authors,citationCount,externalIds,abstract"},
                    )
                    if r.status_code == 429:
                        wait = 5 * (attempt + 1)
                        logger.warning("S2 rate limited, waiting %ds...", wait)
                        await asyncio.sleep(wait)
                        continue
                    if r.status_code != 200:
                        return []
                    results = []
                    for p in r.json().get("data", []):
                        results.append({
                            "title": p.get("title", ""),
                            "year": p.get("year"),
                            "authors": [a.get("name", "") for a in (p.get("authors") or [])[:4]],
                            "citations": p.get("citationCount", 0),
                            "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                            "abstract": (p.get("abstract") or "")[:500],
                            "s2_id": p.get("paperId", ""),
                        })
                    results.sort(key=lambda x: x.get("citations", 0), reverse=True)
                    return results
                except Exception as e:
                    logger.warning("S2 search failed: %s", e)
                    break
        # Fallback: arXiv API search
        try:
            import arxiv
            search = arxiv.Search(query=topic, max_results=limit, sort_by=arxiv.SortCriterion.Relevance)
            results = []
            for paper in search.results():
                aid = paper.entry_id.split("/")[-1].split("v")[0] if paper.entry_id else ""
                results.append({"title": paper.title, "year": paper.published.year if paper.published else None,
                    "authors": [a.name for a in (paper.authors or [])[:4]], "citations": 0,
                    "arxiv_id": aid, "abstract": (paper.summary or "")[:500], "s2_id": ""})
            if results:
                logger.info("arXiv fallback: found %d papers for '%s'", len(results), topic)
                return results
        except Exception as e:
            logger.warning("arXiv fallback failed: %s", e)
        return []

    async def _queue_papers(self, papers: list[dict]) -> list[str]:
        """Queue arXiv papers for download and processing."""
        cfg = get_config()
        queued = []
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
            for p in papers:
                if not p.get("arxiv_id"):
                    continue
                try:
                    headers = {}
                    if cfg.security.api_token:
                        headers["Authorization"] = f"Bearer {cfg.security.api_token}"
                    r = await client.post("/api/upload-url",
                        json={"url": p["arxiv_id"], "mode": "translate", "highlight": True},
                        headers=headers)
                    if r.status_code == 200:
                        queued.append(p["arxiv_id"])
                except Exception:
                    pass
                await asyncio.sleep(0.5)
        return queued

    async def _gather_knowledge(self, topic: str, search_results: list[dict]) -> str:
        """Gather knowledge from KB papers + search results for synthesis."""
        parts = []

        # 1. RAG context from vector DB (most relevant chunks)
        try:
            from .vector_search import get_vector_service
            vs = get_vector_service()
            if vs:
                hits = await vs.search(topic, n_results=30)
                if hits:
                    parts.append("=== Knowledge Base (vector-retrieved) ===")
                    seen_papers = set()
                    for h in hits:
                        pid = h.get("metadata", {}).get("paper_id", "")
                        if pid not in seen_papers:
                            seen_papers.add(pid)
                        parts.append(f"[{h['metadata'].get('type','')}] {h['text']}")
                    parts.append("")
        except Exception:
            pass

        # 2. Full knowledge from top KB papers matching the topic
        with Session(engine) as session:
            completed = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
            ).all()

        # Match KB papers to search results by title
        search_titles = {p["title"].lower().strip() for p in search_results}
        matched_papers = [p for p in completed if p.title and p.title.lower().strip() in search_titles]

        for p in matched_papers[:10]:
            if p.knowledge_json:
                kj = json.loads(p.knowledge_json)
                meta = kj.get("metadata", {})
                title = meta.get("title", "")
                if isinstance(title, dict): title = title.get("en", "")
                abstract = meta.get("abstract", "")
                if isinstance(abstract, dict): abstract = abstract.get("en", "")
                parts.append(f"=== Paper: {title} ===")
                if abstract:
                    parts.append(f"Abstract: {abstract[:400]}")
                for f in kj.get("findings", [])[:5]:
                    stmt = f.get("statement", "")
                    if isinstance(stmt, dict): stmt = stmt.get("en", "")
                    parts.append(f"[{f.get('type','')}] {stmt}")
                for m in kj.get("methods", [])[:3]:
                    name = m.get("name", "")
                    if isinstance(name, dict): name = name.get("en", "")
                    desc = m.get("description", "")
                    if isinstance(desc, dict): desc = desc.get("en", "")
                    parts.append(f"Method: {name} — {desc}")
                parts.append("")

        # 3. Search results metadata (for papers not in KB)
        for p in search_results:
            if p["title"].lower().strip() not in {pp.title.lower().strip() for pp in matched_papers if pp.title}:
                parts.append(f"=== External: {p['title']} ({p.get('year','?')}, {p.get('citations',0)} cites) ===")
                if p.get("abstract"):
                    parts.append(f"Abstract: {p['abstract'][:300]}")
                parts.append("")

        return "\n".join(parts)

    async def _synthesize(self, topic: str, context: str, paper_count: int) -> str:
        """Generate expert synthesis using LLM."""
        # Truncate context to fit in context window
        if len(context) > 30000:
            context = context[:30000] + "\n... (truncated)"

        prompt = EXPERT_SYNTHESIS_PROMPT.format(
            topic=topic, paper_count=paper_count, papers_context=context
        )

        async with httpx.AsyncClient(base_url=self.base_url, timeout=180.0) as client:
            resp = await client.post(
                "/chat/completions",
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000, "temperature": 0.3},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            return (msg.get("content") or "").strip() or msg.get("reasoning_content", "")
