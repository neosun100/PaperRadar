"""知识提取服务 - 使用 LLM 从学术论文中提取结构化知识"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime

import fitz
import httpx
from sqlmodel import Session

from ..core.db import engine
from ..models.knowledge import (
    Flashcard,
    KnowledgeEntity,
    KnowledgeRelationship,
    PaperKnowledge,
)

logger = logging.getLogger(__name__)


METADATA_PROMPT = (
    "You are an expert academic paper metadata extractor. "
    "Extract the following metadata from the beginning of this paper:\n\n"
    "- title: the exact paper title\n"
    "- authors: list of authors, each with name and affiliation if available\n"
    "- year: publication year (integer or null)\n"
    "- doi: DOI string if present, otherwise null\n"
    "- arxiv_id: arXiv ID if present (e.g. '2301.12345'), otherwise null\n"
    "- venue: conference or journal name if present, otherwise null\n"
    "- abstract: the full abstract text\n"
    "- keywords: list of keywords if present, otherwise empty list\n\n"
    "Respond ONLY with a JSON object:\n"
    '{"title": "...", "authors": [{"name": "...", "affiliation": "..."}], '
    '"year": 2025, "doi": "...", "arxiv_id": "...", "venue": "...", '
    '"abstract": "...", "keywords": ["..."]}\n'
)

SECTIONS_PROMPT = (
    "You are an expert academic paper structure analyzer. "
    "Identify the section structure of this paper from the text.\n\n"
    "For each section, provide:\n"
    "- title: the section heading\n"
    "- level: heading level (1 for main sections like Introduction, 2 for subsections)\n"
    "- summary: a 1-2 sentence summary of the section content\n\n"
    "Respond ONLY with a JSON object:\n"
    '{"sections": [{"title": "Introduction", "level": 1, "summary": "..."}]}\n'
)

ENTITY_RELATIONSHIP_PROMPT = (
    "You are an expert academic knowledge extractor. "
    "From the following section of a paper, extract:\n"
    "1. Key entities (concepts, methods, models, datasets, metrics, tasks)\n"
    "2. Relationships between entities\n\n"
    "Entity types: method, model, dataset, metric, concept, task, person, organization\n"
    "Relationship types: extends, uses, evaluates_on, outperforms, similar_to, "
    "contradicts, part_of, requires\n\n"
    "For each entity: name, type, aliases (list), definition (1 sentence), importance (0-1)\n"
    "For each relationship: source (entity name), target (entity name), type, "
    "description, confidence (0-1)\n\n"
    "Return 3-10 entities and 1-8 relationships per section. "
    "Skip trivial or generic entities.\n\n"
    "Respond ONLY with JSON:\n"
    '{"entities": [{"name": "...", "type": "method", "aliases": [], '
    '"definition": "...", "importance": 0.8}], '
    '"relationships": [{"source": "...", "target": "...", "type": "extends", '
    '"description": "...", "confidence": 0.8}]}\n'
)

FINDINGS_PROMPT = (
    "You are an expert academic paper analyst. "
    "Extract the key findings, methods, and datasets from this paper text.\n\n"
    "For findings, classify as: result, limitation, or contribution\n"
    "For methods, describe the approach with inputs and outputs\n"
    "For datasets, note the name, description, and how it was used\n\n"
    "Respond ONLY with JSON:\n"
    '{"findings": [{"type": "result", "statement": "...", "evidence": "..."}], '
    '"methods": [{"name": "...", "description": "...", "inputs": ["..."], "outputs": ["..."]}], '
    '"datasets": [{"name": "...", "description": "...", "usage": "evaluation"}]}\n'
)

FLASHCARD_PROMPT = (
    "You are an expert educator creating spaced repetition flashcards. "
    "Given these key concepts and findings from a paper, create flashcards.\n\n"
    "Rules:\n"
    "- Create 5-15 cards per paper\n"
    "- Each card tests ONE specific concept or finding\n"
    "- Front: clear question. Back: concise, accurate answer\n"
    "- Difficulty 1-5 (1=basic terminology, 5=nuanced understanding)\n"
    "- Tag each card with relevant categories\n\n"
    "Respond ONLY with JSON:\n"
    '{"flashcards": [{"front": "...", "back": "...", "tags": ["method"], "difficulty": 3}]}\n'
)


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class KnowledgeExtractor:
    """从学术论文 PDF 中提取结构化知识。"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        max_concurrent: int = 3,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_concurrent = max_concurrent
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(180.0, connect=10.0),
        )

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def extract(
        self,
        pdf_bytes: bytes,
        task_id: str | None,
        user_id: int,
        paper_id: str | None = None,
    ) -> PaperKnowledge:
        """完整提取流水线：PDF → 结构化知识 JSON → 存入数据库。"""
        if paper_id is None:
            paper_id = _gen_id("pk")

        # 创建初始记录
        paper = PaperKnowledge(
            id=paper_id,
            task_id=task_id,
            user_id=user_id,
            extraction_status="extracting",
            extraction_model=self.model,
        )
        self._save_paper(paper)

        try:
            knowledge = await self._run_pipeline(pdf_bytes, paper_id, user_id)
            paper.knowledge_json = json.dumps(knowledge, ensure_ascii=False)
            paper.title = knowledge.get("metadata", {}).get("title", "")
            paper.doi = knowledge.get("metadata", {}).get("doi")
            paper.arxiv_id = knowledge.get("metadata", {}).get("arxiv_id")
            paper.year = knowledge.get("metadata", {}).get("year")
            paper.venue = knowledge.get("metadata", {}).get("venue")
            paper.extraction_status = "completed"
            paper.updated_at = datetime.utcnow()
            self._save_paper(paper)
            logger.info("知识提取完成: %s - %s", paper_id, paper.title)
            return paper
        except Exception as exc:
            logger.exception("知识提取失败: %s", exc)
            paper.extraction_status = "error"
            paper.extraction_error = str(exc)
            paper.updated_at = datetime.utcnow()
            self._save_paper(paper)
            raise

    async def _run_pipeline(
        self, pdf_bytes: bytes, paper_id: str, user_id: int
    ) -> dict:
        """执行提取流水线的各阶段。"""
        # 1. 提取 PDF 全文
        pages_text = self._extract_text(pdf_bytes)
        full_text = "\n\n".join(pages_text)

        # 2. 提取 metadata（前2页）
        first_pages = "\n\n".join(pages_text[:2])
        metadata = await self._llm_call(METADATA_PROMPT, first_pages, "metadata")

        # 3. 识别 section 结构
        sections_data = await self._llm_call(SECTIONS_PROMPT, full_text[:8000], "sections")
        sections = sections_data.get("sections", [])
        for i, sec in enumerate(sections):
            sec["id"] = f"sec_{i + 1}"

        # 4. 并发提取实体和关系（按 section 分块）
        chunks = self._split_by_sections(full_text, sections)
        all_entities: list[dict] = []
        all_relationships: list[dict] = []

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def extract_chunk(chunk_text: str, sec_id: str):
            async with semaphore:
                return await self._llm_call(
                    ENTITY_RELATIONSHIP_PROMPT, chunk_text, "entities"
                )

        tasks = [
            extract_chunk(chunk, sec.get("id", f"sec_{i}"))
            for i, (sec, chunk) in enumerate(zip(sections, chunks, strict=False))
            if len(chunk.strip()) >= 100
        ]

        if not tasks:
            # 如果没有足够的 section 分块，对全文做一次提取
            result = await self._llm_call(
                ENTITY_RELATIONSHIP_PROMPT, full_text[:6000], "entities"
            )
            all_entities.extend(result.get("entities", []))
            all_relationships.extend(result.get("relationships", []))
        else:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                all_entities.extend(result.get("entities", []))
                all_relationships.extend(result.get("relationships", []))

        # 去重实体
        entities = self._deduplicate_entities(all_entities)

        # 给实体和关系分配 ID
        entity_map: dict[str, str] = {}
        for ent in entities:
            ent_id = _gen_id("ent")
            entity_map[ent["name"].lower()] = ent_id
            ent["id"] = ent_id

        for rel in all_relationships:
            rel["id"] = _gen_id("rel")
            src = rel.get("source", "").lower()
            tgt = rel.get("target", "").lower()
            rel["source_entity_id"] = entity_map.get(src, "")
            rel["target_entity_id"] = entity_map.get(tgt, "")

        # 过滤掉无效关系
        relationships = [
            r for r in all_relationships
            if r.get("source_entity_id") and r.get("target_entity_id")
        ]

        # 5. 提取 findings + methods + datasets
        findings_data = await self._llm_call(
            FINDINGS_PROMPT, full_text[:8000], "findings"
        )
        findings = findings_data.get("findings", [])
        for _i, f in enumerate(findings):
            f["id"] = _gen_id("find")
        methods = findings_data.get("methods", [])
        datasets = findings_data.get("datasets", [])

        # 6. 生成闪卡
        flashcard_context = json.dumps(
            {"entities": entities[:15], "findings": findings[:10]},
            ensure_ascii=False,
        )
        flashcards_data = await self._llm_call(
            FLASHCARD_PROMPT, flashcard_context, "flashcards"
        )
        flashcards = flashcards_data.get("flashcards", [])
        for fc in flashcards:
            fc["id"] = _gen_id("fc")
            fc["srs"] = {
                "interval_days": 1.0,
                "ease_factor": 2.5,
                "repetitions": 0,
                "next_review": datetime.utcnow().isoformat(),
            }

        # 7. 组装 PaperKnowledge JSON
        knowledge = {
            "id": paper_id,
            "metadata": metadata,
            "structure": {"sections": sections},
            "entities": entities,
            "relationships": relationships,
            "findings": findings,
            "methods": methods,
            "datasets": datasets,
            "flashcards": flashcards,
            "annotations": [],
            "extracted_at": datetime.utcnow().isoformat(),
            "extraction_model": self.model,
        }

        # 8. 存入索引表
        self._save_index_tables(paper_id, user_id, entities, relationships, flashcards)

        return knowledge

    # ------------------------------------------------------------------
    # PDF 文本提取
    # ------------------------------------------------------------------

    def _extract_text(self, pdf_bytes: bytes) -> list[str]:
        """用 PyMuPDF 提取每页文本。"""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        try:
            for i in range(doc.page_count):
                page = doc.load_page(i)
                text = page.get_text("text")
                if text.strip():
                    pages.append(text)
        finally:
            doc.close()
        return pages

    # ------------------------------------------------------------------
    # LLM 调用（带重试）
    # ------------------------------------------------------------------

    async def _llm_call(
        self, system_prompt: str, user_content: str, label: str
    ) -> dict:
        """单次 LLM API 调用，带重试和 JSON 解析。"""
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                return await self._do_llm_call(system_prompt, user_content)
            except Exception as exc:
                if attempt == max_retries - 1:
                    logger.error("LLM call [%s] failed after %d retries: %s", label, max_retries, exc)
                    return {}
                delay = base_delay * (2 ** attempt)
                logger.warning("LLM call [%s] error: %s, retrying in %ds...", label, exc, delay)
                await asyncio.sleep(delay)
        return {}

    async def _do_llm_call(self, system_prompt: str, user_content: str) -> dict:
        """执行 LLM API 调用并解析 JSON 响应。"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = await self._client.post(
            "/chat/completions", json=payload, headers=headers
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # 去除 markdown 代码围栏
        if content.startswith("```"):
            lines = content.split("\n")
            start_idx = 1 if lines[0].startswith("```") else 0
            end_idx = -1 if lines[-1].strip() == "```" else len(lines)
            content = "\n".join(lines[start_idx:end_idx])

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                return json.loads(content[start : end + 1])
            raise

    # ------------------------------------------------------------------
    # 实体去重
    # ------------------------------------------------------------------

    def _deduplicate_entities(self, entities: list[dict]) -> list[dict]:
        """按名称（小写）去重实体，保留 importance 更高的。"""
        seen: dict[str, dict] = {}
        for ent in entities:
            key = ent.get("name", "").lower().strip()
            if not key:
                continue
            existing = seen.get(key)
            if existing is None or ent.get("importance", 0) > existing.get("importance", 0):
                seen[key] = ent
        return list(seen.values())

    # ------------------------------------------------------------------
    # Section 分块
    # ------------------------------------------------------------------

    def _split_by_sections(self, full_text: str, sections: list[dict]) -> list[str]:
        """尝试按 section 标题分割文本，回退到等分。"""
        if not sections:
            return [full_text]

        chunks: list[str] = []
        text_lower = full_text.lower()
        positions: list[int] = []

        for sec in sections:
            title = sec.get("title", "").lower()
            pos = text_lower.find(title)
            positions.append(pos if pos >= 0 else -1)

        # 用有效位置分割
        valid = [(pos, i) for i, pos in enumerate(positions) if pos >= 0]
        valid.sort()

        if len(valid) < 2:
            # 回退：按 2000 字符等分
            chunk_size = 2000
            for start in range(0, len(full_text), chunk_size):
                chunks.append(full_text[start : start + chunk_size])
            return chunks

        for idx, (pos, _) in enumerate(valid):
            end = valid[idx + 1][0] if idx + 1 < len(valid) else len(full_text)
            chunks.append(full_text[pos:end])

        return chunks

    # ------------------------------------------------------------------
    # 数据库持久化
    # ------------------------------------------------------------------

    def _save_paper(self, paper: PaperKnowledge) -> None:
        with Session(engine) as session:
            session.merge(paper)
            session.commit()

    def _save_index_tables(
        self,
        paper_id: str,
        user_id: int,
        entities: list[dict],
        relationships: list[dict],
        flashcards: list[dict],
    ) -> None:
        """将实体、关系、闪卡存入索引表。"""
        with Session(engine) as session:
            for ent in entities:
                session.merge(KnowledgeEntity(
                    id=ent["id"],
                    paper_id=paper_id,
                    user_id=user_id,
                    name=ent.get("name", ""),
                    type=ent.get("type", "concept"),
                    aliases_json=json.dumps(ent.get("aliases", []), ensure_ascii=False),
                    definition=ent.get("definition"),
                    importance=ent.get("importance", 0.5),
                ))

            for rel in relationships:
                session.merge(KnowledgeRelationship(
                    id=rel["id"],
                    paper_id=paper_id,
                    user_id=user_id,
                    source_entity_id=rel["source_entity_id"],
                    target_entity_id=rel["target_entity_id"],
                    type=rel.get("type", "uses"),
                    description=rel.get("description"),
                    confidence=rel.get("confidence", 0.5),
                ))

            now = datetime.utcnow()
            for fc in flashcards:
                session.merge(Flashcard(
                    id=fc["id"],
                    paper_id=paper_id,
                    user_id=user_id,
                    front=fc.get("front", ""),
                    back=fc.get("back", ""),
                    tags_json=json.dumps(fc.get("tags", []), ensure_ascii=False),
                    difficulty=fc.get("difficulty", 3),
                    interval_days=1.0,
                    ease_factor=2.5,
                    repetitions=0,
                    next_review=now,
                ))

            session.commit()

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> KnowledgeExtractor:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.close()
