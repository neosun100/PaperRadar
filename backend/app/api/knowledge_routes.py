"""知识库 API 路由 — BYOK edition (no auth)"""

from __future__ import annotations

import asyncio
import io
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from sqlmodel import Session, select

from ..core.db import engine
from ..models.knowledge import (
    Flashcard,
    KnowledgeEntity,
    KnowledgeRelationship,
    PaperCollection,
    PaperKnowledge,
    ReadingEvent,
    ReadingProgress,
    UserAnnotation,
)
from ..models.task import Task, TaskStatus
from ..services.knowledge_extractor import KnowledgeExtractor
from .deps import get_llm_config, get_client_id

logger = logging.getLogger(__name__)


def create_knowledge_router() -> APIRouter:
    router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

    # ------------------------------------------------------------------
    # 知识提取
    # ------------------------------------------------------------------

    @router.post("/extract/{task_id}")
    async def extract_knowledge(task_id: str, request: Request) -> dict[str, str]:
        llm_config = get_llm_config(request)

        with Session(engine) as session:
            task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Task not completed yet")

        with Session(engine) as session:
            existing = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.task_id == task_id)
            ).first()
        if existing and existing.extraction_status == "completed":
            return {"paper_id": existing.id, "status": "already_completed"}

        if not task.original_pdf_path or not Path(task.original_pdf_path).exists():
            raise HTTPException(status_code=404, detail="Original PDF not found or expired")

        pdf_bytes = Path(task.original_pdf_path).read_bytes()
        paper_id = existing.id if existing else None

        extractor = KnowledgeExtractor(
            api_key=llm_config["api_key"],
            model=llm_config.get("model", ""),
            base_url=llm_config.get("base_url", ""),
        )

        async def _do_extract():
            try:
                async with extractor:
                    await extractor.extract(pdf_bytes, task_id, user_id=0, paper_id=paper_id)
            except Exception:
                pass

        asyncio.create_task(_do_extract())
        return {"paper_id": paper_id or "pending", "status": "extracting"}

    @router.get("/extract/status/{paper_id}")
    async def extraction_status(paper_id: str) -> dict[str, Any]:
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        return {
            "paper_id": paper.id,
            "status": paper.extraction_status,
            "error": paper.extraction_error,
            "title": paper.title,
        }

    # ------------------------------------------------------------------
    # 论文知识 CRUD
    # ------------------------------------------------------------------

    @router.get("/papers")
    async def list_papers() -> list[dict[str, Any]]:
        with Session(engine) as session:
            papers = session.exec(
                select(PaperKnowledge).order_by(PaperKnowledge.created_at.desc())
            ).all()
        result = []
        for p in papers:
            summary = ""
            tldr = ""
            if p.knowledge_json and p.extraction_status == "completed":
                try:
                    kj = json.loads(p.knowledge_json)
                    meta = kj.get("metadata", {})
                    abstract = meta.get("abstract", "")
                    if isinstance(abstract, dict):
                        abstract = abstract.get("en", abstract.get("zh", ""))
                    summary = str(abstract)[:200] if abstract else ""
                    tldr_obj = kj.get("tldr", {})
                    if isinstance(tldr_obj, dict):
                        tldr = tldr_obj.get("en", tldr_obj.get("zh", ""))
                        if tldr and "unable to generate" in tldr.lower():
                            tldr = ""
                    elif tldr_obj:
                        tldr = str(tldr_obj)
                except Exception:
                    pass
            result.append({
                "id": p.id, "task_id": p.task_id, "title": p.title,
                "doi": p.doi, "year": p.year, "venue": p.venue,
                "extraction_status": p.extraction_status,
                "summary": summary,
                "tldr": tldr,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return result

    @router.get("/papers/{paper_id}")
    async def get_paper(paper_id: str) -> dict[str, Any]:
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        if paper.knowledge_json:
            return json.loads(paper.knowledge_json)
        return {"id": paper.id, "title": paper.title, "extraction_status": paper.extraction_status}

    @router.delete("/papers/{paper_id}")
    async def delete_paper(paper_id: str) -> dict[str, str]:
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
            if not paper:
                raise HTTPException(status_code=404, detail="Paper not found")
            for model in (Flashcard, UserAnnotation, KnowledgeRelationship, KnowledgeEntity):
                items = session.exec(select(model).where(model.paper_id == paper_id)).all()
                for item in items:
                    session.delete(item)
            session.delete(paper)
            session.commit()
        return {"status": "deleted"}

    # ------------------------------------------------------------------
    # 知识图谱
    # ------------------------------------------------------------------

    @router.get("/graph")
    async def get_graph() -> dict[str, Any]:
        with Session(engine) as session:
            entities = session.exec(select(KnowledgeEntity)).all()
            relationships = session.exec(select(KnowledgeRelationship)).all()
        nodes = [
            {"id": e.id, "name": e.name, "type": e.type, "definition": e.definition, "importance": e.importance, "paper_id": e.paper_id}
            for e in entities
        ]
        edges = [
            {"id": r.id, "source": r.source_entity_id, "target": r.target_entity_id, "type": r.type, "description": r.description, "confidence": r.confidence}
            for r in relationships
        ]
        return {"nodes": nodes, "edges": edges}

    @router.get("/graph/search")
    async def search_entities(q: str) -> list[dict[str, Any]]:
        with Session(engine) as session:
            entities = session.exec(
                select(KnowledgeEntity).where(KnowledgeEntity.name.contains(q))
            ).all()
        return [{"id": e.id, "name": e.name, "type": e.type, "definition": e.definition, "paper_id": e.paper_id} for e in entities]

    # ------------------------------------------------------------------
    # 闪卡
    # ------------------------------------------------------------------

    @router.get("/flashcards")
    async def list_flashcards() -> list[dict[str, Any]]:
        with Session(engine) as session:
            cards = session.exec(select(Flashcard)).all()
        return [_flashcard_to_dict(c) for c in cards]

    @router.get("/flashcards/due")
    async def get_due_flashcards(limit: int = 20) -> list[dict[str, Any]]:
        from datetime import datetime
        with Session(engine) as session:
            cards = session.exec(
                select(Flashcard)
                .where(Flashcard.next_review <= datetime.utcnow())
                .order_by(Flashcard.next_review)
                .limit(limit)
            ).all()
        return [_flashcard_to_dict(c) for c in cards]

    @router.post("/flashcards/{card_id}/review")
    async def review_flashcard(card_id: str, quality: int) -> dict[str, Any]:
        if not 0 <= quality <= 5:
            raise HTTPException(status_code=400, detail="quality must be 0-5")
        from ..services.srs_engine import SRSEngine
        with Session(engine) as session:
            card = session.get(Flashcard, card_id)
            if not card:
                raise HTTPException(status_code=404, detail="Flashcard not found")
            SRSEngine.review(card, quality)
            session.add(card)
            session.commit()
            session.refresh(card)
        return _flashcard_to_dict(card)

    @router.post("/flashcards")
    async def create_flashcard(paper_id: str, front: str, back: str, tags: str = "", difficulty: int = 3) -> dict[str, Any]:
        import uuid
        from datetime import datetime
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
            if not paper:
                raise HTTPException(status_code=404, detail="Paper not found")
            card = Flashcard(
                id=f"fc_{uuid.uuid4().hex[:12]}",
                paper_id=paper_id,
                user_id=0,
                front=front,
                back=back,
                tags_json=json.dumps(tags.split(",") if tags else []),
                difficulty=difficulty,
                next_review=datetime.utcnow(),
            )
            session.add(card)
            session.commit()
            session.refresh(card)
        return _flashcard_to_dict(card)

    @router.delete("/flashcards/{card_id}")
    async def delete_flashcard(card_id: str) -> dict[str, str]:
        with Session(engine) as session:
            card = session.get(Flashcard, card_id)
            if not card:
                raise HTTPException(status_code=404, detail="Flashcard not found")
            session.delete(card)
            session.commit()
        return {"status": "deleted"}

    # ------------------------------------------------------------------
    # 研究洞察（跨论文分析）
    # ------------------------------------------------------------------

    # In-memory cache for insights (regenerate on demand)
    _insights_cache: dict[str, Any] = {}

    @router.post("/insights/generate")
    async def generate_insights(request: Request) -> dict[str, Any]:
        from ..services.insights_generator import InsightsGenerator
        llm_config = get_llm_config(request)
        papers_json = _get_completed_papers_json()
        if len(papers_json) < 2:
            raise HTTPException(400, "Need at least 2 papers to generate insights")

        generator = InsightsGenerator(
            api_key=llm_config["api_key"],
            model=llm_config.get("model", ""),
            base_url=llm_config.get("base_url", ""),
        )
        try:
            result = await generator.generate(papers_json)
            _insights_cache["latest"] = result
            return result
        finally:
            await generator.close()

    @router.get("/insights")
    async def get_insights() -> dict[str, Any]:
        if "latest" not in _insights_cache:
            return {"paper_count": 0, "message": "No insights generated yet. Click 'Generate Insights' to analyze your papers."}
        return _insights_cache["latest"]

    # ------------------------------------------------------------------
    # 语义搜索（向量）
    # ------------------------------------------------------------------

    @router.get("/search")
    async def semantic_search(q: str, n: int = 10, type: str = "") -> dict[str, Any]:
        from ..services.vector_search import get_vector_service
        vs = get_vector_service()
        if not vs:
            raise HTTPException(400, "Vector search not configured (set embedding_model in config)")
        hits = await vs.search(q, n_results=n, filter_type=type or None)
        return {"query": q, "results": hits, "total": len(hits)}

    @router.get("/search/papers")
    async def search_papers_semantic(q: str, n: int = 5) -> dict[str, Any]:
        from ..services.vector_search import get_vector_service
        vs = get_vector_service()
        if not vs:
            raise HTTPException(400, "Vector search not configured")
        hits = await vs.search_papers(q, n_results=n)
        return {"query": q, "results": hits, "total": len(hits)}

    @router.get("/vector/stats")
    async def vector_stats() -> dict[str, Any]:
        from ..services.vector_search import get_vector_service
        vs = get_vector_service()
        if not vs:
            return {"configured": False}
        return {"configured": True, **vs.stats}

    # ------------------------------------------------------------------
    # 文献综述生成
    # ------------------------------------------------------------------

    @router.post("/review/generate")
    async def generate_review(request: Request) -> dict[str, Any]:
        from ..services.literature_review import LiteratureReviewGenerator
        llm_config = get_llm_config(request)
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        topic = body.get("topic", "")

        papers_json = _get_completed_papers_json()
        if not papers_json:
            raise HTTPException(400, "No papers in knowledge base")

        gen = LiteratureReviewGenerator(
            api_key=llm_config["api_key"],
            model=llm_config.get("model", ""),
            base_url=llm_config.get("base_url", ""),
        )
        review = await gen.generate(papers_json, topic)
        return {"review": review, "paper_count": len(papers_json), "topic": topic}

    # ------------------------------------------------------------------
    # 笔记 / 标注
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/annotations")
    async def list_annotations(paper_id: str) -> list[dict[str, Any]]:
        with Session(engine) as session:
            anns = session.exec(
                select(UserAnnotation)
                .where(UserAnnotation.paper_id == paper_id)
                .order_by(UserAnnotation.created_at.desc())
            ).all()
        result = []
        for a in anns:
            meta = {}
            if a.tags_json:
                try:
                    meta = json.loads(a.tags_json)
                    if isinstance(meta, list):
                        meta = {"tags": meta}
                except Exception:
                    meta = {}
            result.append({
                "id": a.id, "type": a.type, "content": a.content,
                "target_type": a.target_type, "target_id": a.target_id,
                "color": meta.get("color", ""),
                "tags": meta.get("tags", []),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })
        return result

    @router.post("/papers/{paper_id}/annotations")
    async def create_annotation(paper_id: str, request: Request) -> dict[str, Any]:
        import uuid
        from datetime import datetime
        body = await request.json()
        ann_type = body.get("type", "note")
        content = body.get("content", "")
        target_type = body.get("target_type", "paper")
        target_id = body.get("target_id", "")
        tags = body.get("tags", [])
        color = body.get("color", "")
        if not content:
            raise HTTPException(400, "content is required")
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
            if not paper:
                raise HTTPException(status_code=404, detail="Paper not found")
            ann = UserAnnotation(
                id=f"ann_{uuid.uuid4().hex[:12]}",
                paper_id=paper_id,
                user_id=0,
                type=ann_type,
                content=content,
                target_type=target_type,
                target_id=target_id,
                tags_json=json.dumps({"tags": tags if isinstance(tags, list) else [], "color": color}),
                created_at=datetime.utcnow(),
            )
            session.add(ann)
            session.commit()
            session.refresh(ann)
        meta = json.loads(ann.tags_json) if ann.tags_json else {}
        return {"id": ann.id, "type": ann.type, "content": ann.content, "target_type": ann.target_type,
                "target_id": ann.target_id, "color": meta.get("color", ""), "tags": meta.get("tags", []),
                "created_at": ann.created_at.isoformat() if ann.created_at else None}

    @router.delete("/annotations/{ann_id}")
    async def delete_annotation(ann_id: str) -> dict[str, str]:
        with Session(engine) as session:
            ann = session.get(UserAnnotation, ann_id)
            if not ann:
                raise HTTPException(status_code=404, detail="Annotation not found")
            session.delete(ann)
            session.commit()
        return {"status": "deleted"}

    # ------------------------------------------------------------------
    # 论文对话
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/chat")
    async def chat_with_paper(paper_id: str, request: Request) -> dict[str, Any]:
        from ..services.paper_chat import PaperChatService
        llm_config = get_llm_config(request)
        body = await request.json()
        message = body.get("message", "")
        history = body.get("history", [])
        if not message:
            raise HTTPException(400, "message is required")

        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.knowledge_json:
            raise HTTPException(404, "Paper not found or knowledge not extracted")

        svc = PaperChatService(
            api_key=llm_config["api_key"],
            model=llm_config.get("model", ""),
            base_url=llm_config.get("base_url", ""),
        )
        reply = await svc.chat(paper.knowledge_json, message, history)
        return {"reply": reply}

    @router.post("/chat")
    async def chat_cross_papers(request: Request) -> dict[str, Any]:
        """跨论文对话 — RAG 增强，用向量检索最相关内容"""
        from ..services.paper_chat import PaperChatService
        from ..services.vector_search import get_vector_service
        llm_config = get_llm_config(request)
        body = await request.json()
        message = body.get("message", "")
        history = body.get("history", [])
        if not message:
            raise HTTPException(400, "message is required")

        # Try RAG first
        vs = get_vector_service()
        rag_context = ""
        if vs:
            rag_context = await vs.get_context_for_chat(message, n_results=15)

        svc = PaperChatService(
            api_key=llm_config["api_key"],
            model=llm_config.get("model", ""),
            base_url=llm_config.get("base_url", ""),
        )

        if rag_context:
            # RAG mode: use retrieved context
            reply = await svc.chat_with_context(rag_context, message, history)
        else:
            # Fallback: use all papers
            papers_json = _get_completed_papers_json()
            if not papers_json:
                raise HTTPException(400, "No papers in knowledge base")
            reply = await svc.chat_multi(papers_json, message, history)

        return {"reply": reply, "mode": "rag" if rag_context else "full"}

    @router.post("/compare")
    async def compare_papers(request: Request) -> dict[str, Any]:
        """对比 2-3 篇论文"""
        from ..services.paper_chat import PaperChatService
        llm_config = get_llm_config(request)
        body = await request.json()
        paper_ids = body.get("paper_ids", [])
        if len(paper_ids) < 2:
            raise HTTPException(400, "Need at least 2 paper IDs")

        papers_json = []
        with Session(engine) as session:
            for pid in paper_ids[:5]:
                p = session.get(PaperKnowledge, pid)
                if p and p.knowledge_json:
                    papers_json.append(json.loads(p.knowledge_json))

        if len(papers_json) < 2:
            raise HTTPException(400, "Need at least 2 papers with extracted knowledge")

        svc = PaperChatService(
            api_key=llm_config["api_key"],
            model=llm_config.get("model", ""),
            base_url=llm_config.get("base_url", ""),
        )
        prompt = (
            "Compare these papers in detail. Create a structured comparison with:\n"
            "1. **Overview** — What each paper is about (1 sentence each)\n"
            "2. **Methods Comparison** — Table comparing approaches\n"
            "3. **Results Comparison** — Key metrics and findings side by side\n"
            "4. **Strengths & Weaknesses** — Of each paper\n"
            "5. **Relationship** — How these papers relate to each other\n"
            "Output as Markdown. Respond in the same language as this prompt."
        )
        reply = await svc.chat_multi(papers_json, prompt)
        return {"comparison": reply, "paper_count": len(papers_json)}

    # ------------------------------------------------------------------
    # Elicit-style Data Extraction Table
    # ------------------------------------------------------------------

    @router.post("/extract-table")
    async def extract_data_table(request: Request) -> dict[str, Any]:
        """Extract structured data from papers into a comparison table."""
        llm_config = get_llm_config(request)
        body = await request.json()
        paper_ids = body.get("paper_ids", [])
        columns = body.get("columns", ["method", "dataset", "metric", "result", "limitation"])

        if not paper_ids:
            raise HTTPException(400, "paper_ids is required")

        papers_json = []
        with Session(engine) as session:
            for pid in paper_ids[:20]:
                p = session.get(PaperKnowledge, pid)
                if p and p.knowledge_json:
                    papers_json.append(json.loads(p.knowledge_json))

        if not papers_json:
            raise HTTPException(400, "No papers with extracted knowledge")

        context = _build_writing_context(papers_json)
        cols_str = ", ".join(columns)
        cols_json = ", ".join(f'"{c}"' for c in columns)
        prompt = (
            f"Extract structured data from these papers into a table.\n\n"
            f"Columns: {cols_str}\n\n"
            f"Return a JSON object with:\n"
            f"- \"columns\": [{cols_json}]\n"
            f"- \"rows\": array of objects, one per paper, each with \"paper\" (title+year) and a value for each column\n\n"
            f"If a value is not available, use \"-\".\n"
            f"Be concise — each cell should be 1-2 sentences max.\n\n"
            f"Papers:\n{context}\n\n"
            f"Respond ONLY with valid JSON."
        )

        import httpx as hx
        async with hx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{llm_config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                json={
                    "model": llm_config.get("model", "gpt-4o"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

        # Parse JSON from response
        try:
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                table_data = json.loads(content[start:end+1])
            else:
                table_data = json.loads(content)
        except json.JSONDecodeError:
            table_data = {"columns": columns, "rows": [], "error": "Failed to parse table"}

        return table_data

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------

    @router.get("/export/json")
    async def export_full_json() -> dict[str, Any]:
        from datetime import datetime
        papers_json = _get_completed_papers_json()
        global_entities: dict[str, dict] = {}
        for pj in papers_json:
            for ent in pj.get("entities", []):
                key = ent.get("name", "").lower().strip()
                if key and key not in global_entities:
                    global_entities[key] = ent
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.utcnow().isoformat(),
            "papers": papers_json,
            "global_entities": list(global_entities.values()),
            "global_relationships": [],
        }

    @router.get("/export/paper/{paper_id}")
    async def export_paper_json(paper_id: str) -> dict[str, Any]:
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        if not paper.knowledge_json:
            raise HTTPException(status_code=400, detail="Knowledge not extracted yet")
        return json.loads(paper.knowledge_json)

    @router.get("/export/bibtex")
    async def export_bibtex():
        from fastapi.responses import PlainTextResponse
        papers_json = _get_completed_papers_json()
        bib_entries = []
        for pj in papers_json:
            metadata = pj.get("metadata", {})
            bibtex = metadata.get("bibtex")
            if bibtex:
                bib_entries.append(bibtex)
            else:
                authors = metadata.get("authors", [])
                author_str = " and ".join(a.get("name", "") for a in authors)
                cite_key = pj.get("id", "unknown").replace("pk_", "")
                entry = f"@article{{{cite_key},\n  title = {{{metadata.get('title', '')}}},\n  author = {{{author_str}}},\n  year = {{{metadata.get('year', '')}}},\n"
                if metadata.get("doi"):
                    entry += f"  doi = {{{metadata['doi']}}},\n"
                if metadata.get("venue"):
                    entry += f"  journal = {{{metadata['venue']}}},\n"
                entry += "}\n"
                bib_entries.append(entry)
        return PlainTextResponse(content="\n".join(bib_entries), media_type="text/plain",
                                 headers={"Content-Disposition": "attachment; filename=paperradar_references.bib"})

    @router.get("/export/obsidian")
    async def export_obsidian():
        from fastapi.responses import Response
        from ..services.knowledge_export import KnowledgeExporter
        papers_json = _get_completed_papers_json()
        zip_bytes = KnowledgeExporter.export_obsidian_vault(papers_json)
        return Response(content=zip_bytes, media_type="application/zip",
                        headers={"Content-Disposition": "attachment; filename=paperradar_vault.zip"})

    @router.get("/export/csv")
    async def export_csv():
        import zipfile as zf_mod
        from fastapi.responses import Response
        from ..services.knowledge_export import KnowledgeExporter
        papers_json = _get_completed_papers_json()
        ent_csv, rel_csv = KnowledgeExporter.export_csv(papers_json)
        buf = io.BytesIO()
        with zf_mod.ZipFile(buf, "w", zf_mod.ZIP_DEFLATED) as zf:
            zf.writestr("entities.csv", ent_csv)
            zf.writestr("relationships.csv", rel_csv)
        return Response(content=buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": "attachment; filename=paperradar_csv.zip"})

    @router.get("/export/csl-json")
    async def export_csl_json():
        from fastapi.responses import Response
        from ..services.knowledge_export import KnowledgeExporter
        papers_json = _get_completed_papers_json()
        csl_bytes = KnowledgeExporter.export_csl_json(papers_json)
        return Response(content=csl_bytes, media_type="application/json",
                        headers={"Content-Disposition": "attachment; filename=paperradar_references.json"})

    # ------------------------------------------------------------------
    # 音频摘要 (Paper Audio Summary)
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/audio")
    async def generate_audio_summary(paper_id: str, request: Request) -> dict[str, Any]:
        from ..services.audio_summary import AudioSummaryService
        llm_config = get_llm_config(request)
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.knowledge_json:
            raise HTTPException(404, "Paper not found or knowledge not extracted")

        svc = AudioSummaryService(
            api_key=llm_config["api_key"],
            model=llm_config.get("model", ""),
            base_url=llm_config.get("base_url", ""),
        )

        # Check cache first
        cached = svc.get_cached(paper_id)
        if cached:
            return {"status": "ready", "url": f"/api/knowledge/papers/{paper_id}/audio/file"}

        # Generate in background
        async def _do_generate():
            try:
                await svc.generate(paper_id, paper.knowledge_json)
            except Exception as e:
                logger.error("Audio generation failed for %s: %s", paper_id, e)

        asyncio.create_task(_do_generate())
        return {"status": "generating"}

    @router.get("/papers/{paper_id}/audio/status")
    async def audio_status(paper_id: str) -> dict[str, Any]:
        from ..services.audio_summary import AudioSummaryService
        svc = AudioSummaryService("", "", "")
        cached = svc.get_cached(paper_id)
        if cached:
            return {"status": "ready", "url": f"/api/knowledge/papers/{paper_id}/audio/file"}
        return {"status": "not_found"}

    @router.get("/papers/{paper_id}/audio/file")
    async def get_audio_file(paper_id: str):
        from fastapi.responses import FileResponse as FR
        from ..services.audio_summary import AudioSummaryService
        svc = AudioSummaryService("", "", "")
        cached = svc.get_cached(paper_id)
        if not cached:
            raise HTTPException(404, "Audio not generated yet")
        return FR(str(cached), media_type="audio/mpeg", filename=f"{paper_id}.mp3")

    @router.delete("/papers/{paper_id}/audio")
    async def delete_audio(paper_id: str) -> dict[str, str]:
        from ..services.audio_summary import AudioSummaryService
        svc = AudioSummaryService("", "", "")
        svc.delete_cached(paper_id)
        return {"status": "deleted"}

    # ------------------------------------------------------------------
    # Citation Network
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/citations")
    async def get_citation_network(paper_id: str) -> dict[str, Any]:
        """Fetch citation network for a paper via Semantic Scholar API."""
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        if not paper.arxiv_id:
            return {"nodes": [], "edges": [], "message": "No arXiv ID available"}

        s2_fields = "paperId,externalIds,title,year,citationCount,authors"
        base = "https://api.semanticscholar.org/graph/v1/paper"
        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Resolve S2 paper ID and get basic info
            try:
                r = await client.get(f"{base}/ArXiv:{paper.arxiv_id}", params={"fields": s2_fields})
                if r.status_code != 200:
                    return {"nodes": [], "edges": [], "message": "Paper not found on Semantic Scholar"}
                center = r.json()
            except Exception:
                return {"nodes": [], "edges": [], "message": "Semantic Scholar API unavailable"}

            s2id = center.get("paperId", "")
            nodes[s2id] = {
                "id": s2id, "title": center.get("title", ""), "year": center.get("year"),
                "citations": center.get("citationCount", 0),
                "authors": [a.get("name", "") for a in (center.get("authors") or [])[:3]],
                "arxiv_id": paper.arxiv_id, "is_center": True,
            }

            # Fetch references (papers this paper cites) and citations (papers citing this)
            for rel, direction in [("references", "cites"), ("citations", "citedBy")]:
                try:
                    r2 = await client.get(
                        f"{base}/{s2id}/{rel}",
                        params={"fields": s2_fields, "limit": 20},
                    )
                    if r2.status_code != 200:
                        continue
                    for item in r2.json().get("data", []):
                        cp = item.get("citingPaper") or item.get("citedPaper") or item
                        cid = cp.get("paperId", "")
                        if not cid or not cp.get("title"):
                            continue
                        if cid not in nodes:
                            nodes[cid] = {
                                "id": cid, "title": cp.get("title", ""), "year": cp.get("year"),
                                "citations": cp.get("citationCount", 0),
                                "authors": [a.get("name", "") for a in (cp.get("authors") or [])[:3]],
                                "arxiv_id": (cp.get("externalIds") or {}).get("ArXiv", ""),
                                "is_center": False,
                            }
                        if direction == "cites":
                            edges.append({"source": s2id, "target": cid, "type": "cites"})
                        else:
                            edges.append({"source": cid, "target": s2id, "type": "cites"})
                except Exception:
                    continue

        return {"nodes": list(nodes.values()), "edges": edges}

    # ------------------------------------------------------------------
    # Smart Citations (scite.ai-style citation contexts)
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/citation-contexts")
    async def get_citation_contexts(paper_id: str) -> dict[str, Any]:
        """Fetch citation contexts showing how this paper is cited (supporting/contrasting/mentioning)."""
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        if not paper.arxiv_id:
            return {"contexts": [], "message": "No arXiv ID available"}

        base = "https://api.semanticscholar.org/graph/v1/paper"
        contexts: list[dict] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                r = await client.get(f"{base}/ArXiv:{paper.arxiv_id}", params={"fields": "paperId"})
                if r.status_code != 200:
                    return {"contexts": [], "message": "Paper not found on Semantic Scholar"}
                s2id = r.json().get("paperId", "")
            except Exception:
                return {"contexts": [], "message": "Semantic Scholar API unavailable"}

            # Fetch citations with contexts
            try:
                r2 = await client.get(
                    f"{base}/{s2id}/citations",
                    params={"fields": "contexts,intents,title,year,authors,citationCount,externalIds", "limit": 30},
                )
                if r2.status_code == 200:
                    for item in r2.json().get("data", []):
                        cp = item.get("citingPaper", {})
                        if not cp.get("title"):
                            continue
                        ctxs = item.get("contexts") or []
                        intents = item.get("intents") or []
                        if not ctxs:
                            continue
                        contexts.append({
                            "title": cp.get("title", ""),
                            "year": cp.get("year"),
                            "authors": [a.get("name", "") for a in (cp.get("authors") or [])[:3]],
                            "citations": cp.get("citationCount", 0),
                            "arxiv_id": (cp.get("externalIds") or {}).get("ArXiv", ""),
                            "s2_id": cp.get("paperId", ""),
                            "contexts": ctxs[:3],
                            "intents": intents,
                        })
            except Exception:
                pass

        return {"contexts": contexts}

    # ------------------------------------------------------------------
    # Paper lookup by task_id (for Reader annotations)
    # ------------------------------------------------------------------

    @router.get("/paper-by-task/{task_id}")
    async def get_paper_by_task(task_id: str) -> dict[str, Any]:
        with Session(engine) as session:
            paper = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.task_id == task_id)
            ).first()
        if not paper:
            raise HTTPException(status_code=404, detail="No paper found for this task")
        return {"paper_id": paper.id, "title": paper.title}

    # ------------------------------------------------------------------
    # AI Inline Explanation
    # ------------------------------------------------------------------

    @router.post("/explain")
    async def explain_text(request: Request) -> dict[str, str]:
        llm_config = get_llm_config(request)
        body = await request.json()
        text = body.get("text", "").strip()
        context = body.get("context", "")
        if not text:
            raise HTTPException(400, "text is required")

        import httpx as hx
        prompt = (
            "You are a helpful research assistant. Explain the following academic text "
            "in simple, easy-to-understand language (CEFR A2/B1 level). "
            "Be concise (2-4 sentences). If the text contains technical terms, define them briefly.\n\n"
        )
        if context:
            prompt += f"Paper context: {context}\n\n"
        prompt += f"Text to explain:\n\"{text}\""

        async with hx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{llm_config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                json={
                    "model": llm_config.get("model", "gpt-4o"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            reply = resp.json()["choices"][0]["message"]["content"]
        return {"explanation": reply}

    # ------------------------------------------------------------------
    # Reading History / Timeline
    # ------------------------------------------------------------------

    @router.post("/reading-events")
    async def record_reading_event(request: Request) -> dict[str, str]:
        import uuid
        from datetime import datetime
        body = await request.json()
        event = ReadingEvent(
            id=f"re_{uuid.uuid4().hex[:12]}",
            paper_id=body.get("paper_id", ""),
            task_id=body.get("task_id", ""),
            event_type=body.get("event_type", "view"),
            created_at=datetime.utcnow(),
        )
        with Session(engine) as session:
            session.add(event)
            session.commit()
        return {"status": "recorded"}

    @router.get("/reading-history")
    async def get_reading_history(days: int = 30) -> dict[str, Any]:
        from datetime import datetime, timedelta
        from sqlmodel import func
        cutoff = datetime.utcnow() - timedelta(days=days)
        with Session(engine) as session:
            # Recent events
            events = session.exec(
                select(ReadingEvent)
                .where(ReadingEvent.created_at >= cutoff)
                .order_by(ReadingEvent.created_at.desc())
            ).all()
            # Stats
            total_events = session.exec(select(func.count(ReadingEvent.id))).one()
            unique_papers = session.exec(
                select(func.count(func.distinct(ReadingEvent.paper_id)))
                .where(ReadingEvent.paper_id != "")
            ).one()
            # Daily counts for chart
            daily: dict[str, int] = {}
            for e in events:
                day = e.created_at.strftime("%Y-%m-%d") if e.created_at else ""
                if day:
                    daily[day] = daily.get(day, 0) + 1

        return {
            "events": [
                {"id": e.id, "paper_id": e.paper_id, "task_id": e.task_id,
                 "event_type": e.event_type, "created_at": e.created_at.isoformat() if e.created_at else None}
                for e in events[:100]
            ],
            "stats": {"total_events": total_events, "unique_papers": unique_papers},
            "daily": daily,
        }

    # ------------------------------------------------------------------
    # OpenAlex Enrichment
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/enrich")
    async def enrich_paper_openalex(paper_id: str) -> dict[str, Any]:
        """Enrich paper metadata from OpenAlex (free, open API)."""
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")

        # Try DOI first, then title search
        query = None
        if paper.doi:
            query = f"https://api.openalex.org/works/doi:{paper.doi}"
        elif paper.title:
            query = f"https://api.openalex.org/works?filter=title.search:{paper.title[:100]}&per_page=1"

        if not query:
            return {"enriched": False, "reason": "No DOI or title available"}

        enriched_data = {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                r = await client.get(query, headers={"User-Agent": "PaperRadar/2.1 (mailto:contact@paperradar.dev)"})
                if r.status_code != 200:
                    return {"enriched": False, "reason": "OpenAlex API error"}
                data = r.json()
                # Handle search results vs direct lookup
                work = data if "id" in data else (data.get("results", [{}])[0] if data.get("results") else {})
                if not work.get("id"):
                    return {"enriched": False, "reason": "Paper not found in OpenAlex"}

                enriched_data = {
                    "openalex_id": work.get("id", ""),
                    "cited_by_count": work.get("cited_by_count", 0),
                    "type": work.get("type", ""),
                    "open_access": work.get("open_access", {}).get("is_oa", False),
                    "concepts": [c.get("display_name", "") for c in (work.get("concepts") or [])[:5]],
                    "topics": [t.get("display_name", "") for t in (work.get("topics") or [])[:3]],
                    "institutions": list({i.get("display_name", "") for a in (work.get("authorships") or []) for i in (a.get("institutions") or []) if i.get("display_name")}),
                }
                # Update paper fields if missing
                with Session(engine) as session:
                    p = session.get(PaperKnowledge, paper_id)
                    if p:
                        if not p.doi and work.get("doi"):
                            p.doi = work["doi"].replace("https://doi.org/", "")
                        if not p.year and work.get("publication_year"):
                            p.year = work["publication_year"]
                        if not p.venue and work.get("primary_location", {}).get("source", {}).get("display_name"):
                            p.venue = work["primary_location"]["source"]["display_name"]
                        session.add(p)
                        session.commit()
            except Exception as exc:
                return {"enriched": False, "reason": str(exc)[:100]}

        return {"enriched": True, "data": enriched_data}

    # ------------------------------------------------------------------
    # Paper Collections (ResearchRabbit-style)
    # ------------------------------------------------------------------

    @router.get("/collections")
    async def list_collections() -> list[dict[str, Any]]:
        with Session(engine) as session:
            cols = session.exec(select(PaperCollection).order_by(PaperCollection.updated_at.desc())).all()
        return [
            {"id": c.id, "name": c.name, "description": c.description, "color": c.color,
             "paper_ids": json.loads(c.paper_ids_json) if c.paper_ids_json else [],
             "paper_count": len(json.loads(c.paper_ids_json)) if c.paper_ids_json else 0,
             "created_at": c.created_at.isoformat() if c.created_at else None,
             "updated_at": c.updated_at.isoformat() if c.updated_at else None}
            for c in cols
        ]

    @router.post("/collections")
    async def create_collection(request: Request) -> dict[str, Any]:
        import uuid
        from datetime import datetime
        body = await request.json()
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(400, "name is required")
        cid = f"col_{uuid.uuid4().hex[:12]}"
        with Session(engine) as session:
            col = PaperCollection(
                id=cid, name=name, description=body.get("description", ""),
                color=body.get("color", "blue"), paper_ids_json="[]",
                created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            )
            session.add(col)
            session.commit()
        return {"id": cid, "name": name}

    @router.put("/collections/{col_id}")
    async def update_collection(col_id: str, request: Request) -> dict[str, str]:
        from datetime import datetime
        body = await request.json()
        with Session(engine) as session:
            col = session.get(PaperCollection, col_id)
            if not col:
                raise HTTPException(404, "Collection not found")
            if "name" in body:
                col.name = body["name"]
            if "description" in body:
                col.description = body["description"]
            if "color" in body:
                col.color = body["color"]
            col.updated_at = datetime.utcnow()
            session.add(col)
            session.commit()
        return {"status": "updated"}

    @router.delete("/collections/{col_id}")
    async def delete_collection(col_id: str) -> dict[str, str]:
        with Session(engine) as session:
            col = session.get(PaperCollection, col_id)
            if not col:
                raise HTTPException(404, "Collection not found")
            session.delete(col)
            session.commit()
        return {"status": "deleted"}

    @router.post("/collections/{col_id}/papers")
    async def add_paper_to_collection(col_id: str, request: Request) -> dict[str, Any]:
        from datetime import datetime
        body = await request.json()
        paper_id = body.get("paper_id", "")
        if not paper_id:
            raise HTTPException(400, "paper_id is required")
        with Session(engine) as session:
            col = session.get(PaperCollection, col_id)
            if not col:
                raise HTTPException(404, "Collection not found")
            ids = json.loads(col.paper_ids_json) if col.paper_ids_json else []
            if paper_id not in ids:
                ids.append(paper_id)
                col.paper_ids_json = json.dumps(ids)
                col.updated_at = datetime.utcnow()
                session.add(col)
                session.commit()
        return {"paper_count": len(ids)}

    @router.delete("/collections/{col_id}/papers/{paper_id}")
    async def remove_paper_from_collection(col_id: str, paper_id: str) -> dict[str, Any]:
        from datetime import datetime
        with Session(engine) as session:
            col = session.get(PaperCollection, col_id)
            if not col:
                raise HTTPException(404, "Collection not found")
            ids = json.loads(col.paper_ids_json) if col.paper_ids_json else []
            ids = [pid for pid in ids if pid != paper_id]
            col.paper_ids_json = json.dumps(ids)
            col.updated_at = datetime.utcnow()
            session.add(col)
            session.commit()
        return {"paper_count": len(ids)}

    # ------------------------------------------------------------------
    # Paper Writing Assistant
    # ------------------------------------------------------------------

    @router.post("/writing/related-work")
    async def generate_related_work(request: Request) -> dict[str, str]:
        """Generate a 'Related Work' section from selected papers."""
        llm_config = get_llm_config(request)
        body = await request.json()
        paper_ids = body.get("paper_ids", [])
        topic = body.get("topic", "")
        style = body.get("style", "ieee")  # ieee, acm, apa

        if not paper_ids:
            raise HTTPException(400, "paper_ids is required")

        papers_json = []
        with Session(engine) as session:
            for pid in paper_ids[:20]:
                p = session.get(PaperKnowledge, pid)
                if p and p.knowledge_json:
                    papers_json.append(json.loads(p.knowledge_json))

        if not papers_json:
            raise HTTPException(400, "No papers with extracted knowledge found")

        context = _build_writing_context(papers_json)
        prompt = (
            f"You are an expert academic writer. Generate a 'Related Work' section for a research paper.\n\n"
            f"Citation style: {style.upper()}\n"
            f"{'Topic focus: ' + topic if topic else ''}\n\n"
            f"Requirements:\n"
            f"- Write in formal academic style\n"
            f"- Organize thematically, not paper-by-paper\n"
            f"- Cite papers as [Author et al., Year] or numbered references\n"
            f"- Compare and contrast approaches\n"
            f"- Identify the gap your work fills\n"
            f"- Output as Markdown\n"
            f"- Include a References section at the end\n\n"
            f"Papers:\n{context}"
        )

        import httpx as hx
        async with hx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{llm_config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                json={
                    "model": llm_config.get("model", "gpt-4o"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
        return {"related_work": text}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_writing_context(papers: list[dict]) -> str:
        parts = []
        for i, p in enumerate(papers):
            meta = p.get("metadata", {})
            title = meta.get("title", "")
            if isinstance(title, dict):
                title = title.get("en", "")
            authors = ", ".join(a.get("name", "") for a in (meta.get("authors") or [])[:3])
            year = meta.get("year", "")
            abstract = meta.get("abstract", "")
            if isinstance(abstract, dict):
                abstract = abstract.get("en", "")
            findings = []
            for f in p.get("findings", [])[:5]:
                s = f.get("statement", "")
                findings.append(s.get("en", "") if isinstance(s, dict) else str(s))
            methods = []
            for m in p.get("methods", []):
                n = m.get("name", "")
                methods.append(n.get("en", "") if isinstance(n, dict) else str(n))

            parts.append(f"[{i+1}] {title} ({authors}, {year})")
            if abstract:
                parts.append(f"  Abstract: {str(abstract)[:300]}")
            if findings:
                parts.append(f"  Findings: {'; '.join(findings)}")
            if methods:
                parts.append(f"  Methods: {', '.join(methods)}")
            parts.append("")
        return "\n".join(parts)

    def _get_completed_papers_json() -> list[dict]:
        with Session(engine) as session:
            papers = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
            ).all()
        return [json.loads(p.knowledge_json) for p in papers if p.knowledge_json]

    def _flashcard_to_dict(card: Flashcard) -> dict[str, Any]:
        return {
            "id": card.id,
            "paper_id": card.paper_id,
            "front": card.front,
            "back": card.back,
            "tags": json.loads(card.tags_json) if card.tags_json else [],
            "difficulty": card.difficulty,
            "srs": {
                "interval_days": card.interval_days,
                "ease_factor": card.ease_factor,
                "repetitions": card.repetitions,
                "next_review": card.next_review.isoformat() if card.next_review else None,
                "last_review": card.last_review.isoformat() if card.last_review else None,
            },
        }

    # ------------------------------------------------------------------
    # Chirpz-style Paper Prioritization (personalized ranking)
    # ------------------------------------------------------------------

    @router.post("/prioritize")
    async def prioritize_papers(request: Request) -> dict[str, Any]:
        """Rank papers by personal relevance based on your KB and reading history."""
        llm_config = get_llm_config(request)
        body = await request.json()
        candidate_papers = body.get("papers", [])  # list of {title, abstract, ...}
        if not candidate_papers:
            raise HTTPException(400, "papers list is required")

        # Build user research profile from KB
        with Session(engine) as session:
            completed = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
            ).all()
        profile_parts = []
        for p in completed[:10]:
            if p.knowledge_json:
                kj = json.loads(p.knowledge_json)
                meta = kj.get("metadata", {})
                title = meta.get("title", "")
                if isinstance(title, dict):
                    title = title.get("en", "")
                methods = [m.get("name", "") for m in kj.get("methods", [])[:3]]
                methods = [m.get("en", "") if isinstance(m, dict) else str(m) for m in methods]
                profile_parts.append(f"- {title} (methods: {', '.join(methods)})")

        if not profile_parts:
            return {"ranked": candidate_papers, "message": "No KB papers for profiling"}

        profile = "\n".join(profile_parts[:10])
        candidates = "\n".join(
            f"[{i}] {p.get('title', '')[:100]} — {p.get('abstract', '')[:150]}"
            for i, p in enumerate(candidate_papers[:20])
        )

        prompt = (
            f"You are a research assistant. Based on the user's research profile, "
            f"rank these candidate papers by relevance (most relevant first).\n\n"
            f"User's research profile (papers they've read):\n{profile}\n\n"
            f"Candidate papers to rank:\n{candidates}\n\n"
            f"Return ONLY a JSON array of indices in order of relevance, e.g. [3, 0, 7, 1, ...]"
        )

        import httpx as hx
        try:
            async with hx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{llm_config['base_url']}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                    json={"model": llm_config.get("model", "gpt-4o"), "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                # Parse indices
                start = content.find("[")
                end = content.rfind("]")
                if start != -1 and end != -1:
                    indices = json.loads(content[start:end+1])
                    ranked = [candidate_papers[i] for i in indices if i < len(candidate_papers)]
                    # Append any missing
                    seen = set(indices)
                    for i, p in enumerate(candidate_papers):
                        if i not in seen:
                            ranked.append(p)
                    return {"ranked": ranked}
        except Exception:
            pass
        return {"ranked": candidate_papers, "message": "Ranking failed, returning original order"}

    # ------------------------------------------------------------------
    # Digest (summary of recent activity for email/webhook)
    # ------------------------------------------------------------------

    @router.get("/digest")
    async def get_digest(days: int = 7) -> dict[str, Any]:
        """Generate a digest of recent activity for email/webhook notifications."""
        from datetime import datetime, timedelta
        from sqlmodel import func
        cutoff = datetime.utcnow() - timedelta(days=days)

        with Session(engine) as session:
            # New papers
            new_papers = session.exec(
                select(PaperKnowledge)
                .where(PaperKnowledge.created_at >= cutoff)
                .order_by(PaperKnowledge.created_at.desc())
            ).all()
            # Reading events
            events = session.exec(
                select(ReadingEvent)
                .where(ReadingEvent.created_at >= cutoff)
            ).all()
            total_papers = session.exec(select(func.count(PaperKnowledge.id))).one()

        papers_summary = [
            {"title": p.title[:100], "year": p.year, "status": p.extraction_status}
            for p in new_papers[:20]
        ]

        # Build text digest
        lines = [f"📊 PaperRadar Weekly Digest ({days}d)\n"]
        lines.append(f"📚 Knowledge Base: {total_papers} papers total")
        lines.append(f"🆕 New papers: {len(new_papers)}")
        lines.append(f"📖 Reading events: {len(events)}")
        if new_papers:
            lines.append(f"\n🆕 Recently Added:")
            for p in new_papers[:10]:
                lines.append(f"  • {p.title[:80]} ({p.year or '?'})")

        return {
            "period_days": days,
            "new_papers": len(new_papers),
            "reading_events": len(events),
            "total_papers": total_papers,
            "papers": papers_summary,
            "text": "\n".join(lines),
        }

    # ------------------------------------------------------------------
    # Research Gaps (dedicated analysis)
    # ------------------------------------------------------------------

    @router.post("/research-gaps")
    async def generate_research_gaps(request: Request) -> dict[str, Any]:
        """Generate detailed research gaps analysis from knowledge base papers."""
        llm_config = get_llm_config(request)
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        topic = body.get("topic", "")
        papers_json = _get_completed_papers_json()
        if len(papers_json) < 2:
            raise HTTPException(400, "Need at least 2 papers")

        # Build context from papers
        context_parts = []
        for p in papers_json[:15]:
            meta = p.get("metadata", {})
            title = meta.get("title", "")
            if isinstance(title, dict):
                title = title.get("en", "")
            findings = [f.get("statement", "") for f in p.get("findings", [])[:5]]
            findings_text = "; ".join(str(f) if not isinstance(f, dict) else f.get("en", "") for f in findings)
            context_parts.append(f"Paper: {title}\nFindings: {findings_text}")

        prompt = (
            "You are a senior research advisor. Analyze these papers and identify:\n"
            "1. **Open Problems** — Unsolved challenges mentioned across papers\n"
            "2. **Contradictions** — Conflicting findings between papers\n"
            "3. **Underexplored Areas** — Topics mentioned but not deeply studied\n"
            "4. **Future Directions** — Explicitly suggested next steps\n"
            "5. **Methodology Gaps** — Missing baselines, datasets, or evaluation methods\n\n"
            f"{'Focus on: ' + topic if topic else ''}\n\n"
            "For each gap, provide: title, description, evidence (which papers), impact (high/medium/low), "
            "and a suggested research question.\n\n"
            "Respond in Markdown format with clear sections.\n\n"
            + "\n\n".join(context_parts)
        )

        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=120.0) as client:
            resp = await client.post(
                "/chat/completions",
                json={"model": llm_config.get("model", ""), "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000},
                headers={"Authorization": f"Bearer {llm_config['api_key']}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]

        return {"gaps": result, "paper_count": len(papers_json), "topic": topic}

    # ------------------------------------------------------------------
    # Zotero Import
    # ------------------------------------------------------------------

    @router.post("/import/zotero")
    async def import_from_zotero(request: Request) -> dict[str, Any]:
        """Import papers from Zotero library. Requires user_id or API key + library type/id."""
        body = await request.json()
        api_key = body.get("api_key", "")
        library_type = body.get("library_type", "user")  # user or group
        library_id = body.get("library_id", "")
        limit = min(body.get("limit", 25), 50)

        if not api_key or not library_id:
            raise HTTPException(400, "api_key and library_id are required")

        base = f"https://api.zotero.org/{library_type}s/{library_id}"
        headers = {"Zotero-API-Key": api_key, "Zotero-API-Version": "3"}
        imported = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{base}/items/top", headers=headers, params={"limit": limit, "format": "json", "itemType": "-attachment"})
            if resp.status_code != 200:
                raise HTTPException(400, f"Zotero API error: {resp.status_code}")
            items = resp.json()
            for item in items:
                data = item.get("data", {})
                title = data.get("title", "")
                doi = data.get("DOI", "")
                url = data.get("url", "")
                year = None
                date_str = data.get("date", "")
                if date_str:
                    import re
                    m = re.search(r"(\d{4})", date_str)
                    if m:
                        year = int(m.group(1))
                # Check if already in KB by title
                with Session(engine) as session:
                    existing = session.exec(select(PaperKnowledge).where(PaperKnowledge.title == title)).first()
                if existing:
                    imported.append({"title": title, "status": "exists", "paper_id": existing.id})
                    continue
                # Create a KB entry from Zotero metadata
                import uuid
                paper_id = f"pk_{uuid.uuid4().hex[:12]}"
                authors = [{"name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()} for c in data.get("creators", [])]
                knowledge = {
                    "id": paper_id,
                    "metadata": {
                        "title": {"en": title, "zh": title},
                        "authors": authors,
                        "year": year,
                        "doi": doi,
                        "venue": data.get("publicationTitle", ""),
                        "abstract": {"en": data.get("abstractNote", ""), "zh": ""},
                        "keywords": [],
                    },
                    "entities": [], "relationships": [], "findings": [],
                    "methods": [], "datasets": [], "flashcards": [], "annotations": [],
                    "source": "zotero",
                }
                with Session(engine) as session:
                    paper = PaperKnowledge(
                        id=paper_id, title=title, doi=doi, year=year,
                        venue=data.get("publicationTitle", ""),
                        knowledge_json=json.dumps(knowledge, ensure_ascii=False),
                        extraction_status="imported",
                    )
                    session.add(paper)
                    session.commit()
                imported.append({"title": title, "status": "imported", "paper_id": paper_id})
        return {"imported": len([i for i in imported if i["status"] == "imported"]), "total": len(imported), "items": imported}

    # ------------------------------------------------------------------
    # Paper Similarity Map (2D embedding visualization)
    # ------------------------------------------------------------------

    @router.get("/similarity-map")
    async def get_similarity_map() -> dict[str, Any]:
        """Get 2D coordinates for all papers based on vector embeddings (PCA)."""
        from ..services.vector_search import get_vector_service
        vs = get_vector_service()
        if not vs:
            raise HTTPException(400, "Vector search not configured")
        # Get all paper embeddings from ChromaDB
        collection = vs._papers
        count = collection.count()
        if count < 2:
            return {"points": [], "message": "Need at least 2 papers with embeddings"}
        data = collection.get(include=["embeddings", "metadatas"])
        embeddings_data = data.get("embeddings")
        if embeddings_data is None or len(embeddings_data) < 2:
            return {"points": [], "message": "No embeddings found"}
        import numpy as np
        embeddings = np.array(embeddings_data)
        # Simple PCA to 2D
        mean = embeddings.mean(axis=0)
        centered = embeddings - mean
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # Take top 2 eigenvectors (largest eigenvalues are last)
        top2 = eigenvectors[:, -2:][:, ::-1]
        projected = centered @ top2
        # Normalize to [0, 1]
        mins = projected.min(axis=0)
        maxs = projected.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1
        normalized = (projected - mins) / ranges
        points = []
        for i, meta in enumerate(data["metadatas"]):
            points.append({
                "paper_id": meta.get("paper_id", ""),
                "title": meta.get("title", "")[:100],
                "x": float(normalized[i][0]),
                "y": float(normalized[i][1]),
            })
        return {"points": points, "total": len(points)}

    # ------------------------------------------------------------------
    # Figure & Table Extraction
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/figures")
    async def get_paper_figures(paper_id: str) -> dict[str, Any]:
        """Extract figures/images from a paper's PDF."""
        from ..services.figure_extractor import extract_figures
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        # Find original PDF via task
        pdf_path = None
        if paper.task_id:
            with Session(engine) as session:
                task = session.get(Task, paper.task_id)
                if task and task.original_pdf_path:
                    pdf_path = task.original_pdf_path
        if not pdf_path or not Path(pdf_path).exists():
            raise HTTPException(404, "Original PDF not found")
        pdf_bytes = Path(pdf_path).read_bytes()
        figures = extract_figures(pdf_bytes)
        # Strip base64 for listing (return separately per figure)
        listing = [{"index": f["index"], "page": f["page"], "width": f["width"], "height": f["height"]} for f in figures]
        return {"paper_id": paper_id, "figures": listing, "total": len(figures)}

    @router.get("/papers/{paper_id}/figures/{fig_index}")
    async def get_paper_figure_image(paper_id: str, fig_index: int) -> Any:
        """Get a specific figure image as PNG."""
        from fastapi.responses import Response
        from ..services.figure_extractor import extract_figures
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        pdf_path = None
        if paper.task_id:
            with Session(engine) as session:
                task = session.get(Task, paper.task_id)
                if task and task.original_pdf_path:
                    pdf_path = task.original_pdf_path
        if not pdf_path or not Path(pdf_path).exists():
            raise HTTPException(404, "Original PDF not found")
        figures = extract_figures(Path(pdf_path).read_bytes())
        if fig_index < 0 or fig_index >= len(figures):
            raise HTTPException(404, "Figure not found")
        import base64
        img_bytes = base64.b64decode(figures[fig_index]["data_b64"])
        return Response(content=img_bytes, media_type="image/png")

    @router.get("/papers/{paper_id}/tables")
    async def get_paper_tables(paper_id: str) -> dict[str, Any]:
        """Extract tables from a paper's PDF."""
        from ..services.figure_extractor import extract_tables_text
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        pdf_path = None
        if paper.task_id:
            with Session(engine) as session:
                task = session.get(Task, paper.task_id)
                if task and task.original_pdf_path:
                    pdf_path = task.original_pdf_path
        if not pdf_path or not Path(pdf_path).exists():
            raise HTTPException(404, "Original PDF not found")
        tables = extract_tables_text(Path(pdf_path).read_bytes())
        return {"paper_id": paper_id, "tables": tables, "total": len(tables)}

    # ------------------------------------------------------------------
    # Similar Papers (vector-based)
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/similar")
    async def get_similar_papers(paper_id: str, n: int = 5) -> dict[str, Any]:
        """Find similar papers based on vector embeddings."""
        from ..services.vector_search import get_vector_service
        vs = get_vector_service()
        if not vs:
            return {"similar": [], "message": "Vector search not configured"}
        try:
            data = vs._papers.get(ids=[f"{paper_id}_abstract"], include=["embeddings"])
            embeddings = data.get("embeddings")
            if embeddings is None or len(embeddings) == 0 or len(embeddings[0]) == 0:
                return {"similar": [], "message": "Paper not indexed"}
            embedding = embeddings[0]
            results = vs._papers.query(
                query_embeddings=[embedding], n_results=n + 1,
                include=["metadatas", "distances"],
            )
            similar = []
            for i in range(len(results["ids"][0])):
                pid = results["metadatas"][0][i].get("paper_id", "")
                if pid == paper_id:
                    continue
                similar.append({
                    "paper_id": pid,
                    "title": results["metadatas"][0][i].get("title", ""),
                    "score": round(1 - results["distances"][0][i], 3),
                })
            return {"similar": similar[:n]}
        except Exception as exc:
            logger.warning("Similar papers failed for %s: %s", paper_id, exc)
            return {"similar": []}

    # ------------------------------------------------------------------
    # Reading Progress (save/restore scroll position)
    # ------------------------------------------------------------------

    @router.get("/reading-progress/{item_id}")
    async def get_reading_progress(item_id: str) -> dict[str, Any]:
        from ..models.knowledge import ReadingProgress
        with Session(engine) as session:
            prog = session.get(ReadingProgress, item_id)
        if not prog:
            return {"scroll_position": 0, "page_number": 0}
        return {"scroll_position": prog.scroll_position, "page_number": prog.page_number}

    @router.put("/reading-progress/{item_id}")
    async def save_reading_progress(item_id: str, request: Request) -> dict[str, str]:
        from datetime import datetime
        from ..models.knowledge import ReadingProgress
        body = await request.json()
        with Session(engine) as session:
            prog = session.get(ReadingProgress, item_id)
            if not prog:
                prog = ReadingProgress(id=item_id)
            prog.scroll_position = body.get("scroll_position", 0)
            prog.page_number = body.get("page_number", 0)
            prog.updated_at = datetime.utcnow()
            session.merge(prog)
            session.commit()
        return {"status": "saved"}

    # ------------------------------------------------------------------
    # TLDR Backfill (generate TLDR for existing papers that don't have one)
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/generate-tldr")
    async def generate_tldr(paper_id: str, request: Request) -> dict[str, Any]:
        llm_config = get_llm_config(request)
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.knowledge_json:
            raise HTTPException(404, "Paper not found or no knowledge")
        kj = json.loads(paper.knowledge_json)
        if kj.get("tldr"):
            return {"tldr": kj["tldr"], "status": "already_exists"}

        meta = kj.get("metadata", {})
        title = meta.get("title", "")
        if isinstance(title, dict):
            title = title.get("en", "")
        abstract = meta.get("abstract", "")
        if isinstance(abstract, dict):
            abstract = abstract.get("en", "")

        prompt = (
            "Write a single-sentence TLDR summary of this paper (max 30 words). "
            "Focus on the key contribution. Be specific.\n"
            'Respond ONLY with JSON: {"tldr": {"en": "...", "zh": "..."}}\n\n'
            f"Title: {title}\nAbstract: {abstract}"
        )
        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=30.0) as client:
            # Use non-thinking model for simple TLDR generation
            model = llm_config.get("model", "")
            if "-thinking" in model:
                model = model.replace("-thinking", "")
            resp = await client.post(
                "/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0.1},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"},
            )
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            if not content:
                content = msg.get("reasoning_content", "")
            try:
                start = content.find("{")
                end = content.rfind("}")
                tldr_data = json.loads(content[start:end+1]) if start >= 0 else {}
            except Exception:
                tldr_data = {"tldr": {"en": content[:100], "zh": ""}}

        tldr = tldr_data.get("tldr", {})
        kj["tldr"] = tldr
        with Session(engine) as session:
            p = session.get(PaperKnowledge, paper_id)
            if p:
                p.knowledge_json = json.dumps(kj, ensure_ascii=False)
                session.add(p)
                session.commit()
        return {"tldr": tldr, "status": "generated"}

    # ------------------------------------------------------------------
    # Scholar Search (Semantic Scholar public API)
    # ------------------------------------------------------------------

    @router.get("/scholar-search")
    async def scholar_search(q: str, n: int = 5) -> dict[str, Any]:
        """Search Semantic Scholar for papers."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": q, "limit": min(n, 10), "fields": "title,year,authors,citationCount,externalIds,abstract"},
            )
            if r.status_code != 200:
                return {"results": [], "message": f"S2 API error: {r.status_code}"}
            data = r.json()
        results = []
        for p in data.get("data", []):
            results.append({
                "title": p.get("title", ""),
                "year": p.get("year"),
                "authors": [a.get("name", "") for a in (p.get("authors") or [])[:4]],
                "citations": p.get("citationCount", 0),
                "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                "abstract": (p.get("abstract") or "")[:200],
                "s2_id": p.get("paperId", ""),
            })
        return {"results": results, "total": data.get("total", 0)}

    # ------------------------------------------------------------------
    # Paper Sharing (public link)
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/share")
    async def share_paper(paper_id: str) -> dict[str, Any]:
        """Generate a share token for public access to paper knowledge."""
        import uuid
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
            if not paper or not paper.knowledge_json:
                raise HTTPException(404, "Paper not found or no knowledge")
            kj = json.loads(paper.knowledge_json)
            token = kj.get("share_token")
            if not token:
                token = uuid.uuid4().hex[:12]
                kj["share_token"] = token
                paper.knowledge_json = json.dumps(kj, ensure_ascii=False)
                session.add(paper)
                session.commit()
        return {"token": token, "url": f"/share/{token}"}

    # ------------------------------------------------------------------
    # Batch TLDR generation
    # ------------------------------------------------------------------

    @router.post("/batch-generate-tldr")
    async def batch_generate_tldr(request: Request) -> dict[str, Any]:
        """Generate TLDR for all papers that don't have one."""
        llm_config = get_llm_config(request)
        with Session(engine) as session:
            papers = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
            ).all()
        missing = []
        for p in papers:
            if p.knowledge_json:
                kj = json.loads(p.knowledge_json)
                if not kj.get("tldr"):
                    missing.append(p.id)
        # Process in background
        async def _do_batch():
            import asyncio as aio
            success, fail = 0, 0
            for pid in missing:
                try:
                    with Session(engine) as session:
                        paper = session.get(PaperKnowledge, pid)
                    if not paper or not paper.knowledge_json:
                        continue
                    kj = json.loads(paper.knowledge_json)
                    meta = kj.get("metadata", {})
                    title = meta.get("title", "")
                    if isinstance(title, dict): title = title.get("en", "") or title.get("zh", "")
                    abstract = meta.get("abstract", "")
                    if isinstance(abstract, dict): abstract = abstract.get("en", "") or abstract.get("zh", "")
                    if not title and paper.title:
                        title = paper.title
                    if not title:
                        continue
                    prompt = (
                        "Write a single-sentence TLDR summary of this paper (max 30 words). "
                        "Focus on the key contribution. Be specific.\n"
                        'Respond ONLY with JSON: {"tldr": {"en": "...", "zh": "..."}}\n\n'
                        f"Title: {title}\nAbstract: {abstract}"
                    )
                    async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=30.0) as client:
                        batch_model = llm_config.get("model", "")
                        if "-thinking" in batch_model:
                            batch_model = batch_model.replace("-thinking", "")
                        resp = await client.post(
                            "/chat/completions",
                            json={"model": batch_model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0.1},
                            headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                        )
                        resp.raise_for_status()
                        msg = resp.json()["choices"][0]["message"]
                        content = (msg.get("content") or "").strip()
                        if not content:
                            content = msg.get("reasoning_content", "")
                        start = content.find("{"); end = content.rfind("}")
                        tldr_data = json.loads(content[start:end+1]) if start >= 0 else {}
                    tldr = tldr_data.get("tldr", {})
                    kj["tldr"] = tldr
                    with Session(engine) as session:
                        p = session.get(PaperKnowledge, pid)
                        if p:
                            p.knowledge_json = json.dumps(kj, ensure_ascii=False)
                            session.add(p); session.commit()
                    success += 1
                except Exception:
                    fail += 1
                await aio.sleep(1)
            logger.info("Batch TLDR: %d success, %d fail out of %d", success, fail, len(missing))
        asyncio.create_task(_do_batch())
        return {"queued": len(missing), "message": f"Generating TLDR for {len(missing)} papers in background"}

    # ------------------------------------------------------------------
    # Paper Quiz (NotebookLM-style)
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/quiz")
    async def generate_quiz(paper_id: str, request: Request) -> dict[str, Any]:
        llm_config = get_llm_config(request)
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.knowledge_json:
            raise HTTPException(404, "Paper not found or no knowledge")
        kj = json.loads(paper.knowledge_json)
        meta = kj.get("metadata", {})
        title = meta.get("title", "")
        if isinstance(title, dict): title = title.get("en", "")
        abstract = meta.get("abstract", "")
        if isinstance(abstract, dict): abstract = abstract.get("en", "")
        findings = "; ".join(
            (f.get("statement", {}).get("en", "") if isinstance(f.get("statement"), dict) else str(f.get("statement", "")))
            for f in kj.get("findings", [])[:5]
        )
        prompt = (
            "Based on this paper, generate 5 multiple-choice quiz questions (4 options A-D, one correct). "
            "Test understanding of key concepts, methods, and findings. "
            'Respond ONLY with JSON: {"questions": [{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct": "A", "explanation": "..."}]}\n\n'
            f"Title: {title}\nAbstract: {abstract}\nFindings: {findings}"
        )
        model = llm_config.get("model", "")
        if "-thinking" in model: model = model.replace("-thinking", "")
        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=60.0) as client:
            resp = await client.post("/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000, "temperature": 0.3},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip() or msg.get("reasoning_content", "")
        try:
            start = content.find("{"); end = content.rfind("}")
            data = json.loads(content[start:end+1]) if start >= 0 else {"questions": []}
        except Exception:
            data = {"questions": []}
        return {"questions": data.get("questions", []), "paper_id": paper_id}

    # ------------------------------------------------------------------
    # Paper Briefing Doc
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/briefing")
    async def generate_briefing(paper_id: str, request: Request) -> dict[str, Any]:
        llm_config = get_llm_config(request)
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.knowledge_json:
            raise HTTPException(404, "Paper not found or no knowledge")
        kj = json.loads(paper.knowledge_json)
        meta = kj.get("metadata", {})
        title = meta.get("title", "")
        if isinstance(title, dict): title = title.get("en", "")
        abstract = meta.get("abstract", "")
        if isinstance(abstract, dict): abstract = abstract.get("en", "")
        findings = "\n".join(
            f"- {f.get('statement', {}).get('en', '') if isinstance(f.get('statement'), dict) else str(f.get('statement', ''))}"
            for f in kj.get("findings", [])[:8]
        )
        methods = "\n".join(
            f"- {m.get('name', {}).get('en', '') if isinstance(m.get('name'), dict) else str(m.get('name', ''))}: {m.get('description', {}).get('en', '') if isinstance(m.get('description'), dict) else str(m.get('description', ''))}"
            for m in kj.get("methods", [])[:5]
        )
        prompt = (
            "Generate a structured briefing document for this paper in Markdown. Include:\n"
            "## Key Takeaways (3-5 bullet points)\n## Problem Statement\n## Methodology\n"
            "## Key Results\n## Limitations\n## Implications\nBe concise and specific.\n\n"
            f"Title: {title}\nAbstract: {abstract}\nFindings:\n{findings}\nMethods:\n{methods}"
        )
        model = llm_config.get("model", "")
        if "-thinking" in model: model = model.replace("-thinking", "")
        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=120.0) as client:
            resp = await client.post("/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000, "temperature": 0.2},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip() or msg.get("reasoning_content", "")
        return {"briefing": content, "paper_id": paper_id}

    # ------------------------------------------------------------------
    # Deep Research (auto search → collect → expert synthesis)
    # ------------------------------------------------------------------

    @router.post("/deep-research")
    async def deep_research(request: Request) -> dict[str, Any]:
        """Given a topic, search papers, gather knowledge, and generate expert synthesis."""
        from ..services.deep_research import DeepResearchService
        llm_config = get_llm_config(request)
        body = await request.json()
        topic = body.get("topic", "").strip()
        max_papers = min(body.get("max_papers", 10), 20)
        if not topic:
            raise HTTPException(400, "topic is required")

        svc = DeepResearchService(llm_config)
        result = await svc.research(topic, max_papers)

        # Persist report
        if result.get("status") == "completed":
            import uuid
            from ..models.knowledge import ResearchReport
            report = ResearchReport(
                id=f"rr_{uuid.uuid4().hex[:12]}", topic=topic,
                synthesis=result.get("synthesis", ""),
                papers_json=json.dumps(result.get("papers", []), ensure_ascii=False),
                papers_found=result.get("papers_found", 0),
            )
            with Session(engine) as session:
                session.add(report)
                session.commit()
            result["report_id"] = report.id

        return result

    # ------------------------------------------------------------------
    # Expert Chat (topic-focused RAG with deep context)
    # ------------------------------------------------------------------

    @router.post("/expert-chat")
    async def expert_chat(request: Request) -> dict[str, Any]:
        """Expert-level chat that searches for relevant knowledge before answering."""
        from ..services.paper_chat import PaperChatService
        from ..services.vector_search import get_vector_service
        llm_config = get_llm_config(request)
        body = await request.json()
        message = body.get("message", "")
        history = body.get("history", [])
        topic = body.get("topic", "")
        mode = body.get("mode", "expert")  # expert or claim
        if not message:
            raise HTTPException(400, "message is required")

        # Build rich context: vector search + topic-specific papers
        context_parts = []
        sources = []

        vs = get_vector_service()
        if vs:
            queries = [message]
            if topic and topic.lower() not in message.lower():
                queries.append(topic)
            seen_chunks = set()
            for q in queries:
                hits = await vs.search(q, n_results=20)
                for h in hits:
                    cid = h.get("id", "")
                    if cid not in seen_chunks:
                        seen_chunks.add(cid)
                        idx = len(context_parts) + 1
                        context_parts.append(f"[{idx}] ({h['metadata'].get('type','')}) {h['text']}")
                        sources.append({"index": idx, "text": h["text"][:100], "paper_id": h["metadata"].get("paper_id", ""), "type": h["metadata"].get("type", ""), "score": round(h.get("score", 0), 3)})

        if not context_parts:
            return {"reply": "No knowledge available. Upload papers or run Deep Research first.", "sources": []}

        if mode == "claim":
            system_prompt = (
                "You are a research evidence analyst. Given a research claim or question, "
                "analyze the evidence from the papers below and classify each relevant finding as:\n"
                "- ✅ SUPPORTS — evidence that supports the claim\n"
                "- ❌ CONTRADICTS — evidence that contradicts the claim\n"
                "- ➡️ RELATED — relevant but neither supports nor contradicts\n\n"
                "Structure your response as:\n"
                "## Verdict\nOne sentence: what does the evidence say overall?\n\n"
                "## Supporting Evidence\n## Contradicting Evidence\n## Related Findings\n\n"
                "Cite sources using [1], [2] etc. Be specific about methods and numbers.\n"
                "Respond in the same language as the user's question.\n\n"
                f"Research knowledge:\n" + "\n".join(context_parts[:40])
            )
        else:
            system_prompt = (
                "You are a world-class AI research expert with deep knowledge of the academic literature. "
                "Answer with the depth and nuance of a senior researcher. "
                "Be specific — cite paper findings, mention actual methods/numbers/benchmarks. "
                "When answering, cite sources using [1], [2] etc. "
                "Respond in the same language as the user's question.\n\n"
                f"{'Topic context: ' + topic if topic else ''}\n\n"
                "Research knowledge:\n" + "\n".join(context_parts[:40])
            )

        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=120.0) as client:
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-6:])
            messages.append({"role": "user", "content": message})
            resp = await client.post("/chat/completions",
                json={"model": llm_config.get("model", ""), "messages": messages, "temperature": 0.3, "max_tokens": 3000},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            reply = (msg.get("content") or "").strip() or msg.get("reasoning_content", "")

        return {"reply": reply, "sources": sources[:20], "context_chunks": len(context_parts), "mode": mode}

    # ------------------------------------------------------------------
    # Deep Research History (server-side persistence)
    # ------------------------------------------------------------------

    @router.get("/research-history")
    async def list_research_history() -> list[dict[str, Any]]:
        from ..models.knowledge import ResearchReport
        with Session(engine) as session:
            reports = session.exec(select(ResearchReport).order_by(ResearchReport.created_at.desc()).limit(50)).all()
        return [{"id": r.id, "topic": r.topic, "papers_found": r.papers_found, "created_at": r.created_at.isoformat() if r.created_at else None} for r in reports]

    @router.get("/research-history/{report_id}")
    async def get_research_report(report_id: str) -> dict[str, Any]:
        from ..models.knowledge import ResearchReport
        with Session(engine) as session:
            r = session.get(ResearchReport, report_id)
        if not r:
            raise HTTPException(404, "Report not found")
        return {"id": r.id, "topic": r.topic, "synthesis": r.synthesis, "papers": json.loads(r.papers_json) if r.papers_json else [], "papers_found": r.papers_found, "created_at": r.created_at.isoformat() if r.created_at else None}

    # ------------------------------------------------------------------
    # PDF Thumbnail (first page as image)
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/thumbnail")
    async def get_paper_thumbnail(paper_id: str):
        """Generate and return a thumbnail of the paper's first page."""
        from fastapi.responses import Response
        import fitz
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        pdf_path = None
        if paper.task_id:
            with Session(engine) as session:
                task = session.get(Task, paper.task_id)
                if task and task.original_pdf_path:
                    pdf_path = task.original_pdf_path
        if not pdf_path or not Path(pdf_path).exists():
            raise HTTPException(404, "PDF not found")
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))  # 50% scale
            img_bytes = pix.tobytes("png")
            doc.close()
            return Response(content=img_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
        except Exception:
            raise HTTPException(500, "Failed to generate thumbnail")

    # ------------------------------------------------------------------
    # Paper Tags
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/tags")
    async def get_paper_tags(paper_id: str) -> list[str]:
        from ..models.knowledge import PaperTag
        with Session(engine) as session:
            tags = session.exec(select(PaperTag).where(PaperTag.paper_id == paper_id)).all()
        return [t.tag for t in tags]

    @router.post("/papers/{paper_id}/tags")
    async def add_paper_tag(paper_id: str, request: Request) -> dict[str, Any]:
        import uuid
        from ..models.knowledge import PaperTag
        body = await request.json()
        tag = body.get("tag", "").strip().lower()
        if not tag:
            raise HTTPException(400, "tag is required")
        with Session(engine) as session:
            existing = session.exec(select(PaperTag).where(PaperTag.paper_id == paper_id, PaperTag.tag == tag)).first()
            if not existing:
                session.add(PaperTag(id=f"tag_{uuid.uuid4().hex[:8]}", paper_id=paper_id, tag=tag))
                session.commit()
        return {"status": "added", "tag": tag}

    @router.delete("/papers/{paper_id}/tags/{tag}")
    async def remove_paper_tag(paper_id: str, tag: str) -> dict[str, str]:
        from ..models.knowledge import PaperTag
        with Session(engine) as session:
            t = session.exec(select(PaperTag).where(PaperTag.paper_id == paper_id, PaperTag.tag == tag)).first()
            if t:
                session.delete(t)
                session.commit()
        return {"status": "removed"}

    @router.get("/tags")
    async def list_all_tags() -> list[dict[str, Any]]:
        """List all unique tags with paper counts."""
        from ..models.knowledge import PaperTag
        from sqlmodel import func
        with Session(engine) as session:
            results = session.exec(
                select(PaperTag.tag, func.count(PaperTag.id).label("count"))
                .group_by(PaperTag.tag)
                .order_by(func.count(PaperTag.id).desc())
            ).all()
        return [{"tag": r[0], "count": r[1]} for r in results]

    # ------------------------------------------------------------------
    # Custom Extraction (user-defined columns)
    # ------------------------------------------------------------------

    @router.post("/custom-extract")
    async def custom_extract(request: Request) -> dict[str, Any]:
        """Extract user-defined fields from selected papers."""
        llm_config = get_llm_config(request)
        body = await request.json()
        paper_ids = body.get("paper_ids", [])
        columns = body.get("columns", [])  # e.g. ["sample size", "GPU hours", "dataset"]
        if not paper_ids or not columns:
            raise HTTPException(400, "paper_ids and columns are required")

        # Gather paper contexts
        papers_context = []
        with Session(engine) as session:
            for pid in paper_ids[:15]:
                p = session.get(PaperKnowledge, pid)
                if p and p.knowledge_json:
                    kj = json.loads(p.knowledge_json)
                    meta = kj.get("metadata", {})
                    title = meta.get("title", "")
                    if isinstance(title, dict): title = title.get("en", "")
                    abstract = meta.get("abstract", "")
                    if isinstance(abstract, dict): abstract = abstract.get("en", "")
                    findings = "; ".join(
                        (f.get("statement", {}).get("en", "") if isinstance(f.get("statement"), dict) else str(f.get("statement", "")))
                        for f in kj.get("findings", [])[:5]
                    )
                    papers_context.append(f"Paper: {title}\nAbstract: {abstract[:300]}\nFindings: {findings}")

        cols_str = ", ".join(columns)
        cols_example = ", ".join(f'"{c}": "value"' for c in columns)
        papers_text = "\n\n".join(papers_context)
        prompt = (
            f"Extract the following fields from each paper: {cols_str}\n\n"
            "For each paper, output a JSON object with the paper title and each requested field.\n"
            "If a field is not found, use \"-\".\n"
            f'Respond ONLY with JSON: {{"rows": [{{"paper": "title", {cols_example}}}]}}\n\n'
            + papers_text
        )
        model = llm_config.get("model", "")
        if "-thinking" in model: model = model.replace("-thinking", "")
        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=120.0) as client:
            resp = await client.post("/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000, "temperature": 0.1},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip() or msg.get("reasoning_content", "")
        try:
            start = content.find("{"); end = content.rfind("}")
            data = json.loads(content[start:end+1]) if start >= 0 else {"rows": []}
        except Exception:
            data = {"rows": []}
        return {"columns": columns, "rows": data.get("rows", []), "paper_count": len(papers_context)}

    # ------------------------------------------------------------------
    # AI Paper Writer (generate full paper sections)
    # ------------------------------------------------------------------

    @router.post("/writing/generate-section")
    async def generate_paper_section(request: Request) -> dict[str, Any]:
        """Generate a paper section (Introduction, Methodology, Results, Discussion) from KB papers."""
        llm_config = get_llm_config(request)
        body = await request.json()
        section = body.get("section", "introduction")  # introduction, methodology, results, discussion, conclusion
        paper_ids = body.get("paper_ids", [])
        topic = body.get("topic", "")
        style = body.get("style", "ieee")

        if not paper_ids:
            raise HTTPException(400, "paper_ids required")

        # Gather context
        context_parts = []
        with Session(engine) as session:
            for pid in paper_ids[:15]:
                p = session.get(PaperKnowledge, pid)
                if p and p.knowledge_json:
                    kj = json.loads(p.knowledge_json)
                    meta = kj.get("metadata", {})
                    title = meta.get("title", "")
                    if isinstance(title, dict): title = title.get("en", "")
                    abstract = meta.get("abstract", "")
                    if isinstance(abstract, dict): abstract = abstract.get("en", "")
                    findings_list = []
                    for f in kj.get("findings", [])[:5]:
                        s = f.get("statement", "")
                        findings_list.append(s.get("en", "") if isinstance(s, dict) else str(s))
                    methods_list = []
                    for m in kj.get("methods", [])[:3]:
                        n = m.get("name", "")
                        methods_list.append(n.get("en", "") if isinstance(n, dict) else str(n))
                    context_parts.append(f"[{len(context_parts)+1}] {title}\nAbstract: {abstract[:300]}\nFindings: {'; '.join(findings_list)}\nMethods: {', '.join(methods_list)}")

        section_prompts = {
            "introduction": "Write an Introduction section that motivates the research problem, reviews key related work, and states the contribution.",
            "methodology": "Write a Methodology section describing the approaches, experimental setup, datasets, and evaluation metrics.",
            "results": "Write a Results section presenting key findings, comparisons, and analysis of the experimental outcomes.",
            "discussion": "Write a Discussion section interpreting results, comparing with prior work, discussing limitations, and suggesting future directions.",
            "conclusion": "Write a Conclusion section summarizing key contributions and findings.",
        }
        section_prompt = section_prompts.get(section, section_prompts["introduction"])
        context_text = "\n\n".join(context_parts)
        prompt = (
            f"You are an expert academic writer. {section_prompt}\n\n"
            f"Citation style: {style.upper()}\n"
            f"{'Topic: ' + topic if topic else ''}\n"
            "Use [Author, Year] citations referencing the papers below.\n"
            "Write in formal academic style. Output as Markdown.\n\n"
            f"Reference papers:\n{context_text}"
        )
        model = llm_config.get("model", "")
        if "-thinking" in model: model = model.replace("-thinking", "")
        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=180.0) as client:
            resp = await client.post("/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000, "temperature": 0.3},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip() or msg.get("reasoning_content", "")
        return {"section": section, "content": content, "paper_count": len(context_parts)}

    # ------------------------------------------------------------------
    # Paper Recommendation Feed (personalized daily)
    # ------------------------------------------------------------------

    @router.get("/recommendation-feed")
    async def get_recommendation_feed() -> dict[str, Any]:
        """Personalized paper recommendations based on KB content and reading patterns."""
        from ..services.vector_search import get_vector_service

        # Build profile from recent papers
        with Session(engine) as session:
            recent = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
                .order_by(PaperKnowledge.created_at.desc()).limit(10)
            ).all()

        if not recent:
            return {"recommendations": [], "message": "Add papers to get recommendations"}

        # Use vector search to find papers similar to recent ones
        vs = get_vector_service()
        if not vs:
            return {"recommendations": [], "message": "Vector search not configured"}

        # Combine recent paper titles as query
        titles = " ".join(p.title for p in recent[:5] if p.title)
        hits = await vs.search_papers(titles, n_results=10)
        existing_ids = {p.id for p in recent}
        recs = [h for h in hits if h.get("paper_id") not in existing_ids]

        # Enrich with paper details
        enriched = []
        with Session(engine) as session:
            for r in recs[:8]:
                p = session.get(PaperKnowledge, r.get("paper_id", ""))
                if p:
                    tldr = ""
                    if p.knowledge_json:
                        try:
                            kj = json.loads(p.knowledge_json)
                            tldr_obj = kj.get("tldr", {})
                            if isinstance(tldr_obj, dict):
                                tldr = tldr_obj.get("en", "")
                        except Exception:
                            pass
                    enriched.append({"paper_id": p.id, "title": p.title, "year": p.year, "tldr": tldr, "score": r.get("score", 0)})

        return {"recommendations": enriched, "based_on": len(recent)}

    # ------------------------------------------------------------------
    # Mind Map Data (entity relationship graph for a paper)
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/mindmap")
    async def get_paper_mindmap(paper_id: str) -> dict[str, Any]:
        """Generate mind map data from paper entities and relationships."""
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.knowledge_json:
            raise HTTPException(404, "Paper not found")
        kj = json.loads(paper.knowledge_json)
        meta = kj.get("metadata", {})
        title = meta.get("title", "")
        if isinstance(title, dict): title = title.get("en", "")

        # Build mind map: center = paper title, branches = entities grouped by type
        nodes = [{"id": "center", "label": title[:60], "type": "paper", "level": 0}]
        edges = []

        # Group entities by type
        type_groups: dict[str, list] = {}
        for e in kj.get("entities", []):
            etype = e.get("type", "concept")
            name = e.get("name", "")
            if isinstance(name, dict): name = name.get("en", "")
            if not name: continue
            type_groups.setdefault(etype, []).append({"id": e.get("id", ""), "name": name, "importance": e.get("importance", 0.5)})

        for etype, entities in type_groups.items():
            # Type node
            type_id = f"type_{etype}"
            nodes.append({"id": type_id, "label": etype.capitalize(), "type": "category", "level": 1})
            edges.append({"source": "center", "target": type_id})
            # Entity nodes (top 5 per type)
            for ent in sorted(entities, key=lambda x: x["importance"], reverse=True)[:5]:
                nodes.append({"id": ent["id"], "label": ent["name"], "type": etype, "level": 2, "importance": ent["importance"]})
                edges.append({"source": type_id, "target": ent["id"]})

        # Add relationship edges between entities
        for rel in kj.get("relationships", []):
            src = rel.get("source_entity_id", "")
            tgt = rel.get("target_entity_id", "")
            if src and tgt:
                node_ids = {n["id"] for n in nodes}
                if src in node_ids and tgt in node_ids:
                    edges.append({"source": src, "target": tgt, "label": rel.get("type", ""), "dashed": True})

        # Add key findings as leaf nodes
        for i, f in enumerate(kj.get("findings", [])[:5]):
            stmt = f.get("statement", "")
            if isinstance(stmt, dict): stmt = stmt.get("en", "")
            if stmt:
                fid = f"finding_{i}"
                nodes.append({"id": fid, "label": stmt[:80], "type": "finding", "level": 2})
                edges.append({"source": "center", "target": fid})

        return {"nodes": nodes, "edges": edges, "title": title}

    # ------------------------------------------------------------------
    # Systematic Review Pipeline
    # ------------------------------------------------------------------

    @router.post("/systematic-review")
    async def systematic_review(request: Request) -> dict[str, Any]:
        """Automated systematic review: search → screen → extract → synthesize."""
        llm_config = get_llm_config(request)
        body = await request.json()
        query = body.get("query", "").strip()
        inclusion = body.get("inclusion_criteria", "")
        exclusion = body.get("exclusion_criteria", "")
        max_papers = min(body.get("max_papers", 10), 20)
        if not query:
            raise HTTPException(400, "query is required")

        # Step 1: Search
        search_results = []
        for attempt in range(3):
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.get("https://api.semanticscholar.org/graph/v1/paper/search",
                    params={"query": query, "limit": max_papers, "fields": "title,year,authors,citationCount,abstract,externalIds"})
                if r.status_code == 429:
                    await asyncio.sleep(5 * (attempt + 1)); continue
                if r.status_code == 200:
                    search_results = r.json().get("data", []); break

        if not search_results:
            # Fallback to arXiv
            try:
                import arxiv
                for paper in arxiv.Search(query=query, max_results=max_papers, sort_by=arxiv.SortCriterion.Relevance).results():
                    search_results.append({"title": paper.title, "year": paper.published.year if paper.published else None,
                        "abstract": (paper.summary or "")[:500], "authors": [{"name": a.name} for a in (paper.authors or [])[:4]]})
            except Exception:
                pass

        if not search_results:
            return {"status": "no_results", "query": query}

        # Step 2: Screen with LLM
        screen_prompt = (
            f"You are screening papers for a systematic review.\n"
            f"Research question: {query}\n"
            f"{'Inclusion criteria: ' + inclusion if inclusion else ''}\n"
            f"{'Exclusion criteria: ' + exclusion if exclusion else ''}\n\n"
            "For each paper, decide: INCLUDE or EXCLUDE with a brief reason.\n"
            'Respond with JSON: {"decisions": [{"index": 0, "decision": "INCLUDE", "reason": "..."}]}\n\n'
        )
        for i, p in enumerate(search_results):
            screen_prompt += f"[{i}] {p.get('title','')} — {(p.get('abstract') or '')[:200]}\n"

        model = llm_config.get("model", "")
        if "-thinking" in model: model = model.replace("-thinking", "")
        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=120.0) as client:
            resp = await client.post("/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": screen_prompt}], "max_tokens": 2000, "temperature": 0.1},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip() or msg.get("reasoning_content", "")

        try:
            start = content.find("{"); end = content.rfind("}")
            screen_data = json.loads(content[start:end+1]) if start >= 0 else {"decisions": []}
        except Exception:
            screen_data = {"decisions": []}

        decisions = {d["index"]: d for d in screen_data.get("decisions", []) if isinstance(d.get("index"), int)}
        included = []
        excluded = []
        for i, p in enumerate(search_results):
            d = decisions.get(i, {"decision": "INCLUDE", "reason": "No screening data"})
            entry = {"title": p.get("title", ""), "year": p.get("year"), "abstract": (p.get("abstract") or "")[:300],
                "authors": [a.get("name", "") for a in (p.get("authors") or [])[:3]],
                "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                "decision": d.get("decision", "INCLUDE"), "reason": d.get("reason", "")}
            if d.get("decision") == "INCLUDE":
                included.append(entry)
            else:
                excluded.append(entry)

        return {
            "status": "completed", "query": query,
            "total_found": len(search_results), "included": len(included), "excluded": len(excluded),
            "included_papers": included, "excluded_papers": excluded,
            "prisma": {"identified": len(search_results), "screened": len(search_results), "included": len(included), "excluded": len(excluded)},
        }

    # ------------------------------------------------------------------
    # Slide Deck Generation
    # ------------------------------------------------------------------

    @router.post("/papers/{paper_id}/slides")
    async def generate_slides(paper_id: str, request: Request) -> dict[str, Any]:
        """Generate presentation slides from paper knowledge."""
        llm_config = get_llm_config(request)
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.knowledge_json:
            raise HTTPException(404, "Paper not found")
        kj = json.loads(paper.knowledge_json)
        meta = kj.get("metadata", {})
        title = meta.get("title", "")
        if isinstance(title, dict): title = title.get("en", "")
        abstract = meta.get("abstract", "")
        if isinstance(abstract, dict): abstract = abstract.get("en", "")
        findings = "; ".join(
            (f.get("statement", {}).get("en", "") if isinstance(f.get("statement"), dict) else str(f.get("statement", "")))
            for f in kj.get("findings", [])[:6]
        )
        methods = "; ".join(
            (m.get("name", {}).get("en", "") if isinstance(m.get("name"), dict) else str(m.get("name", "")))
            for m in kj.get("methods", [])[:4]
        )

        prompt = (
            "Generate a 6-slide presentation for this paper. Output as JSON array of slides.\n"
            "Each slide: {\"title\": \"...\", \"bullets\": [\"point 1\", \"point 2\", ...], \"notes\": \"speaker notes\"}\n"
            "Slides: 1) Title slide, 2) Problem & Motivation, 3) Methodology, 4) Key Results, 5) Discussion, 6) Conclusion\n"
            'Respond ONLY with JSON: {"slides": [...]}\n\n'
            f"Paper: {title}\nAbstract: {abstract[:400]}\nFindings: {findings}\nMethods: {methods}"
        )
        model = llm_config.get("model", "")
        if "-thinking" in model: model = model.replace("-thinking", "")
        async with httpx.AsyncClient(base_url=llm_config.get("base_url", ""), timeout=120.0) as client:
            resp = await client.post("/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000, "temperature": 0.2},
                headers={"Authorization": f"Bearer {llm_config['api_key']}"})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip() or msg.get("reasoning_content", "")
        try:
            start = content.find("{"); end = content.rfind("}")
            data = json.loads(content[start:end+1]) if start >= 0 else {"slides": []}
        except Exception:
            data = {"slides": []}

        # Generate HTML slide deck
        slides = data.get("slides", [])
        html_parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"><style>',
            'body{font-family:system-ui;margin:0}.slide{width:100vw;height:100vh;display:flex;flex-direction:column;justify-content:center;padding:8%;box-sizing:border-box;page-break-after:always}',
            'h1{font-size:2.5em;margin-bottom:0.5em}h2{font-size:1.8em;color:#3b82f6;margin-bottom:0.5em}ul{font-size:1.3em;line-height:1.8}',
            '.title-slide{background:linear-gradient(135deg,#1e3a5f,#3b82f6);color:white;text-align:center}',
            '</style></head><body>']
        for i, s in enumerate(slides):
            cls = "title-slide" if i == 0 else ""
            html_parts.append(f'<div class="slide {cls}"><h2>{s.get("title","")}</h2><ul>')
            for b in s.get("bullets", []):
                html_parts.append(f"<li>{b}</li>")
            html_parts.append("</ul></div>")
        html_parts.append("</body></html>")

        return {"slides": slides, "html": "".join(html_parts), "paper_id": paper_id}

    # ------------------------------------------------------------------
    # User Preferences (per API key, stored in localStorage on frontend)
    # ------------------------------------------------------------------

    @router.get("/preferences")
    async def get_preferences(request: Request) -> dict[str, Any]:
        """Get user preferences (stored server-side keyed by client ID)."""
        client_id = get_client_id(request)
        # Simple file-based storage
        prefs_dir = Path("/app/data/preferences")
        prefs_dir.mkdir(parents=True, exist_ok=True)
        prefs_file = prefs_dir / f"{client_id}.json"
        if prefs_file.exists():
            return json.loads(prefs_file.read_text())
        return {"radar_topics": "", "notification_email": "", "language": "en", "theme": "system"}

    @router.put("/preferences")
    async def save_preferences(request: Request) -> dict[str, str]:
        """Save user preferences."""
        client_id = get_client_id(request)
        body = await request.json()
        prefs_dir = Path("/app/data/preferences")
        prefs_dir.mkdir(parents=True, exist_ok=True)
        prefs_file = prefs_dir / f"{client_id}.json"
        # Only save allowed fields
        allowed = {"radar_topics", "notification_email", "language", "theme", "default_mode", "highlight_default"}
        prefs = {k: v for k, v in body.items() if k in allowed}
        prefs_file.write_text(json.dumps(prefs, ensure_ascii=False))
        return {"status": "saved"}

    # ------------------------------------------------------------------
    # Paper Impact Score
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/impact")
    async def get_paper_impact(paper_id: str) -> dict[str, Any]:
        """Calculate composite impact score for a paper."""
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")

        scores = {"citations": 0, "year_recency": 0, "kb_connections": 0, "has_tldr": 0}

        # Citation count from OpenAlex or knowledge
        if paper.knowledge_json:
            kj = json.loads(paper.knowledge_json)
            # Check if enriched with OpenAlex data
            meta = kj.get("metadata", {})
            scores["has_tldr"] = 10 if kj.get("tldr") else 0

        # Year recency (newer = higher)
        if paper.year:
            scores["year_recency"] = max(0, min(20, (paper.year - 2020) * 4))

        # KB connections (entities, relationships)
        with Session(engine) as session:
            from sqlmodel import func
            ent_count = session.exec(select(func.count(KnowledgeEntity.id)).where(KnowledgeEntity.paper_id == paper_id)).one()
            rel_count = session.exec(select(func.count(KnowledgeRelationship.id)).where(KnowledgeRelationship.paper_id == paper_id)).one()
        scores["kb_connections"] = min(30, (ent_count + rel_count) * 2)

        # Similar papers count
        try:
            from ..services.vector_search import get_vector_service
            vs = get_vector_service()
            if vs:
                data = vs._papers.get(ids=[f"{paper_id}_abstract"], include=["embeddings"])
                if data.get("embeddings") and len(data["embeddings"]) > 0:
                    results = vs._papers.query(query_embeddings=[data["embeddings"][0]], n_results=6, include=["distances"])
                    close = sum(1 for d in results["distances"][0] if d < 0.5)
                    scores["citations"] = close * 10
        except Exception:
            pass

        total = sum(scores.values())
        return {"paper_id": paper_id, "impact_score": min(100, total), "breakdown": scores}

    # ------------------------------------------------------------------
    # Cross-Paper Timeline
    # ------------------------------------------------------------------

    @router.get("/timeline")
    async def get_paper_timeline() -> dict[str, Any]:
        """Get papers organized by year for timeline visualization."""
        with Session(engine) as session:
            papers = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
            ).all()

        timeline: dict[int, list] = {}
        for p in papers:
            year = p.year or 0
            if year < 2000:
                continue
            tldr = ""
            if p.knowledge_json:
                try:
                    kj = json.loads(p.knowledge_json)
                    tldr_obj = kj.get("tldr", {})
                    if isinstance(tldr_obj, dict):
                        tldr = tldr_obj.get("en", "")
                except Exception:
                    pass
            timeline.setdefault(year, []).append({
                "id": p.id, "title": p.title, "venue": p.venue, "tldr": tldr,
            })

        years = sorted(timeline.keys())
        return {"years": [{
            "year": y, "count": len(timeline[y]),
            "papers": sorted(timeline[y], key=lambda x: x["title"])
        } for y in years], "total": len(papers)}

    # ------------------------------------------------------------------
    # Method Benchmark Tracker
    # ------------------------------------------------------------------

    @router.get("/benchmarks")
    async def get_benchmark_tracker() -> dict[str, Any]:
        """Extract and track benchmark results across papers."""
        with Session(engine) as session:
            papers = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
            ).all()

        entries = []
        for p in papers:
            if not p.knowledge_json:
                continue
            kj = json.loads(p.knowledge_json)
            title = kj.get("metadata", {}).get("title", "")
            if isinstance(title, dict): title = title.get("en", "")
            for f in kj.get("findings", []):
                if f.get("type") == "result":
                    stmt = f.get("statement", "")
                    if isinstance(stmt, dict): stmt = stmt.get("en", "")
                    entries.append({"paper": title[:60], "paper_id": p.id, "year": p.year, "finding": stmt})

        return {"entries": entries, "total": len(entries)}

    # ------------------------------------------------------------------
    # Quick Notes (global scratchpad)
    # ------------------------------------------------------------------

    @router.get("/notes")
    async def get_quick_notes(request: Request) -> dict[str, str]:
        client_id = get_client_id(request)
        notes_file = Path("/app/data/preferences") / f"{client_id}_notes.md"
        if notes_file.exists():
            return {"content": notes_file.read_text()}
        return {"content": ""}

    @router.put("/notes")
    async def save_quick_notes(request: Request) -> dict[str, str]:
        client_id = get_client_id(request)
        body = await request.json()
        notes_dir = Path("/app/data/preferences")
        notes_dir.mkdir(parents=True, exist_ok=True)
        (notes_dir / f"{client_id}_notes.md").write_text(body.get("content", ""))
        return {"status": "saved"}

    # ------------------------------------------------------------------
    # 1. Discussion Discovery (Reddit/HN via web search)
    # ------------------------------------------------------------------

    @router.get("/papers/{paper_id}/discussions")
    async def find_paper_discussions(paper_id: str) -> dict[str, Any]:
        """Search for online discussions about a paper."""
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
        if not paper or not paper.title:
            raise HTTPException(404, "Paper not found")

        title = paper.title[:80]
        discussions = []

        # Search via arXiv ID on known platforms
        arxiv_id = paper.arxiv_id or ""
        search_queries = []
        if arxiv_id:
            search_queries.append(f"site:reddit.com {arxiv_id}")
            search_queries.append(f"site:news.ycombinator.com {arxiv_id}")
        search_queries.append(f"site:reddit.com \"{title[:50]}\"")

        # Use Semantic Scholar to check if paper has community engagement
        if arxiv_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(f"https://api.semanticscholar.org/graph/v1/paper/ArXiv:{arxiv_id}",
                        params={"fields": "citationCount,influentialCitationCount,tldr"})
                    if r.status_code == 200:
                        data = r.json()
                        discussions.append({
                            "source": "Semantic Scholar",
                            "url": f"https://www.semanticscholar.org/paper/{data.get('paperId', '')}",
                            "title": f"{data.get('citationCount', 0)} citations ({data.get('influentialCitationCount', 0)} influential)",
                            "snippet": (data.get("tldr") or {}).get("text", ""),
                        })
            except Exception:
                pass

        # alphaXiv discussion link
        if arxiv_id:
            discussions.append({
                "source": "alphaXiv",
                "url": f"https://alphaxiv.org/abs/{arxiv_id}",
                "title": f"Community discussion on alphaXiv",
                "snippet": "View line-by-line discussions and comments",
            })

        # HuggingFace papers link
        if arxiv_id:
            discussions.append({
                "source": "HuggingFace",
                "url": f"https://huggingface.co/papers/{arxiv_id}",
                "title": "HuggingFace Daily Papers",
                "snippet": "Community upvotes and discussion",
            })

        # Reddit search link
        discussions.append({
            "source": "Reddit",
            "url": f"https://www.reddit.com/search/?q={title[:50].replace(' ', '+')}",
            "title": f"Search Reddit for this paper",
            "snippet": "Find community discussions on r/MachineLearning, r/LocalLLaMA, etc.",
        })

        return {"paper_id": paper_id, "discussions": discussions}

    # ------------------------------------------------------------------
    # 2. Paper Dependency Graph
    # ------------------------------------------------------------------

    @router.get("/dependency-graph")
    async def get_dependency_graph() -> dict[str, Any]:
        """Build a dependency graph showing which papers build on which."""
        with Session(engine) as session:
            papers = session.exec(
                select(PaperKnowledge).where(PaperKnowledge.extraction_status == "completed")
            ).all()

        nodes = []
        edges = []
        paper_methods: dict[str, set] = {}  # paper_id -> set of method names

        for p in papers:
            if not p.knowledge_json:
                continue
            kj = json.loads(p.knowledge_json)
            meta = kj.get("metadata", {})
            title = meta.get("title", "")
            if isinstance(title, dict): title = title.get("en", "")
            nodes.append({"id": p.id, "title": title[:60], "year": p.year or 0})

            methods = set()
            for m in kj.get("methods", []):
                name = m.get("name", "")
                if isinstance(name, dict): name = name.get("en", "")
                if name: methods.add(name.lower().strip())
            paper_methods[p.id] = methods

            # Check relationships for "extends" or "uses"
            for rel in kj.get("relationships", []):
                if rel.get("type") in ("extends", "uses", "builds_on"):
                    # Try to find the target paper in KB
                    target_name = rel.get("target", "").lower()
                    for other_p in papers:
                        if other_p.id != p.id and other_p.title and target_name in other_p.title.lower():
                            edges.append({"source": p.id, "target": other_p.id, "type": rel.get("type", "uses")})
                            break

        # Also find method-based connections (papers sharing methods)
        paper_ids = list(paper_methods.keys())
        for i in range(len(paper_ids)):
            for j in range(i + 1, len(paper_ids)):
                shared = paper_methods[paper_ids[i]] & paper_methods[paper_ids[j]]
                if len(shared) >= 2:
                    edges.append({"source": paper_ids[i], "target": paper_ids[j], "type": "shared_methods", "methods": list(shared)[:3]})

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # 3. Bulk Re-extract Knowledge
    # ------------------------------------------------------------------

    @router.post("/bulk-reextract")
    async def bulk_reextract(request: Request) -> dict[str, Any]:
        """Re-run knowledge extraction on papers with outdated or incomplete data."""
        llm_config = get_llm_config(request)
        body = await request.json()
        paper_ids = body.get("paper_ids", [])
        if not paper_ids:
            # Default: all papers with errors or incomplete extraction
            with Session(engine) as session:
                papers = session.exec(
                    select(PaperKnowledge).where(
                        PaperKnowledge.extraction_status.in_(["error", "imported", "pending"])
                    )
                ).all()
                paper_ids = [p.id for p in papers if p.task_id]

        queued = 0
        for pid in paper_ids[:20]:
            with Session(engine) as session:
                paper = session.get(PaperKnowledge, pid)
            if not paper or not paper.task_id:
                continue
            with Session(engine) as session:
                task = session.get(Task, paper.task_id)
            if not task or not task.original_pdf_path or not Path(task.original_pdf_path).exists():
                continue

            pdf_bytes = Path(task.original_pdf_path).read_bytes()
            from ..services.knowledge_extractor import KnowledgeExtractor
            extractor = KnowledgeExtractor(
                api_key=llm_config["api_key"], model=llm_config.get("model", ""), base_url=llm_config.get("base_url", ""),
            )
            async def _do(ext, pdf, tid, pid):
                try:
                    async with ext:
                        await ext.extract(pdf, tid, user_id=0, paper_id=pid)
                except Exception:
                    pass
            asyncio.create_task(_do(extractor, pdf_bytes, paper.task_id, pid))
            queued += 1

        return {"queued": queued, "total_candidates": len(paper_ids)}

    # ------------------------------------------------------------------
    # 4. API Rate Limit Info
    # ------------------------------------------------------------------

    @router.get("/api-status")
    async def get_api_status() -> dict[str, Any]:
        """Show API usage status and rate limit info."""
        import time
        from ..core.config import get_config
        cfg = get_config()

        status = {
            "llm": {"base_url": cfg.llm.base_url, "model": cfg.llm.model, "embedding_model": cfg.llm.embedding_model},
            "radar": {"enabled": cfg.radar.enabled, "interval_hours": cfg.radar.interval_hours, "categories": cfg.radar.categories},
            "tts": {"model": cfg.tts.model},
            "notifications": {
                "bark": bool(cfg.notification.bark_key),
                "lark": bool(cfg.notification.lark_webhook),
                "webhook": bool(cfg.notification.webhook_url),
            },
            "storage": {},
        }

        # Check data sizes
        data_dir = Path("/app/data")
        if data_dir.exists():
            db_size = 0
            for f in data_dir.rglob("*.db"):
                db_size += f.stat().st_size
            vector_size = 0
            vector_dir = data_dir / "vectordb"
            if vector_dir.exists():
                for f in vector_dir.rglob("*"):
                    if f.is_file():
                        vector_size += f.stat().st_size
            audio_size = sum(f.stat().st_size for f in (data_dir / "audio").rglob("*") if f.is_file()) if (data_dir / "audio").exists() else 0
            status["storage"] = {
                "database_mb": round(db_size / 1024 / 1024, 1),
                "vector_db_mb": round(vector_size / 1024 / 1024, 1),
                "audio_mb": round(audio_size / 1024 / 1024, 1),
            }

        return status

    return router
