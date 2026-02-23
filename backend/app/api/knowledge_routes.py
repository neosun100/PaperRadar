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
    UserAnnotation,
)
from ..models.task import Task, TaskStatus
from ..services.knowledge_extractor import KnowledgeExtractor
from .deps import get_llm_config

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
            if p.knowledge_json and p.extraction_status == "completed":
                try:
                    kj = json.loads(p.knowledge_json)
                    meta = kj.get("metadata", {})
                    abstract = meta.get("abstract", "")
                    if isinstance(abstract, dict):
                        abstract = abstract.get("en", abstract.get("zh", ""))
                    summary = str(abstract)[:200] if abstract else ""
                except Exception:
                    pass
            result.append({
                "id": p.id, "task_id": p.task_id, "title": p.title,
                "doi": p.doi, "year": p.year, "venue": p.venue,
                "extraction_status": p.extraction_status,
                "summary": summary,
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

    return router
