"""知识库 API 路由 — BYOK edition (no auth)"""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import Session, select

from ..core.db import engine
from ..models.knowledge import (
    Flashcard,
    KnowledgeEntity,
    KnowledgeRelationship,
    PaperKnowledge,
    UserAnnotation,
)
from ..models.task import Task, TaskStatus
from ..services.knowledge_extractor import KnowledgeExtractor
from .deps import get_llm_config


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
        return [
            {
                "id": p.id,
                "task_id": p.task_id,
                "title": p.title,
                "doi": p.doi,
                "year": p.year,
                "venue": p.venue,
                "extraction_status": p.extraction_status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in papers
        ]

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
        return [
            {"id": a.id, "type": a.type, "content": a.content, "target_type": a.target_type, "target_id": a.target_id,
             "tags": json.loads(a.tags_json) if a.tags_json else [], "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in anns
        ]

    @router.post("/papers/{paper_id}/annotations")
    async def create_annotation(paper_id: str, type: str, content: str, target_type: str = "paper", target_id: str = "", tags: str = "") -> dict[str, Any]:
        import uuid
        from datetime import datetime
        with Session(engine) as session:
            paper = session.get(PaperKnowledge, paper_id)
            if not paper:
                raise HTTPException(status_code=404, detail="Paper not found")
            ann = UserAnnotation(
                id=f"ann_{uuid.uuid4().hex[:12]}",
                paper_id=paper_id,
                user_id=0,
                type=type,
                content=content,
                target_type=target_type,
                target_id=target_id,
                tags_json=json.dumps(tags.split(",") if tags else []),
                created_at=datetime.utcnow(),
            )
            session.add(ann)
            session.commit()
            session.refresh(ann)
        return {"id": ann.id, "type": ann.type, "content": ann.content, "created_at": ann.created_at.isoformat() if ann.created_at else None}

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
    # Helpers
    # ------------------------------------------------------------------

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

    return router
