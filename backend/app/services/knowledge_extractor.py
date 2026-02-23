"""知识提取服务 - 使用 LLM 从学术论文中提取结构化知识（双语输出）"""

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

# ------------------------------------------------------------------
# 双语指令片段
# ------------------------------------------------------------------
BILINGUAL_INSTRUCTION = (
    "\n\nIMPORTANT: For ALL text fields (titles, descriptions, definitions, statements, "
    "questions, answers, summaries, etc.), output bilingual values as an object with "
    '"en" (English) and "zh" (Chinese) keys. Example: {"en": "Transformer", "zh": "Transformer 模型"}. '
    "Keep proper nouns, model names, and acronyms consistent across languages.\n"
)

METADATA_PROMPT = (
    "You are an expert academic paper metadata extractor. "
    "Extract the following metadata from the beginning of this paper:\n\n"
    "- title: the exact paper title (bilingual)\n"
    "- authors: list of authors, each with name and affiliation if available\n"
    "- year: publication year (integer or null)\n"
    "- doi: DOI string if present, otherwise null\n"
    "- arxiv_id: arXiv ID if present (e.g. '2301.12345'), otherwise null\n"
    "- venue: conference or journal name if present, otherwise null\n"
    "- abstract: the full abstract text (bilingual)\n"
    "- keywords: list of keywords (bilingual)\n"
    + BILINGUAL_INSTRUCTION +
    "Respond ONLY with a JSON object:\n"
    '{"title": {"en": "...", "zh": "..."}, "authors": [{"name": "...", "affiliation": "..."}], '
    '"year": 2025, "doi": "...", "arxiv_id": "...", "venue": "...", '
    '"abstract": {"en": "...", "zh": "..."}, "keywords": [{"en": "...", "zh": "..."}]}\n'
)

SECTIONS_PROMPT = (
    "You are an expert academic paper structure analyzer. "
    "Identify the section structure of this paper from the text.\n\n"
    "For each section, provide:\n"
    "- title: the section heading (bilingual)\n"
    "- level: heading level (1 for main sections like Introduction, 2 for subsections)\n"
    "- summary: a 1-2 sentence summary of the section content (bilingual)\n"
    + BILINGUAL_INSTRUCTION +
    "Respond ONLY with a JSON object:\n"
    '{"sections": [{"title": {"en": "Introduction", "zh": "引言"}, "level": 1, '
    '"summary": {"en": "...", "zh": "..."}}]}\n'
)

ENTITY_RELATIONSHIP_PROMPT = (
    "You are an expert academic knowledge extractor. "
    "From the following section of a paper, extract:\n"
    "1. Key entities (concepts, methods, models, datasets, metrics, tasks)\n"
    "2. Relationships between entities\n\n"
    "Entity types: method, model, dataset, metric, concept, task, person, organization\n"
    "Relationship types: extends, uses, evaluates_on, outperforms, similar_to, "
    "contradicts, part_of, requires\n\n"
    "For each entity: name (bilingual), type, aliases (list), definition (bilingual, 1 sentence), importance (0-1)\n"
    "For each relationship: source (entity English name), target (entity English name), type, "
    "description (bilingual), confidence (0-1)\n\n"
    "Return 3-10 entities and 1-8 relationships per section. "
    "Skip trivial or generic entities.\n"
    + BILINGUAL_INSTRUCTION +
    "Respond ONLY with JSON:\n"
    '{"entities": [{"name": {"en": "...", "zh": "..."}, "type": "method", "aliases": [], '
    '"definition": {"en": "...", "zh": "..."}, "importance": 0.8}], '
    '"relationships": [{"source": "English entity name", "target": "English entity name", "type": "extends", '
    '"description": {"en": "...", "zh": "..."}, "confidence": 0.8}]}\n'
)

FINDINGS_PROMPT = (
    "You are an expert academic paper analyst. "
    "Extract the key findings, methods, and datasets from this paper text.\n\n"
    "For findings, classify as: result, limitation, or contribution\n"
    "For methods, describe the approach with inputs and outputs\n"
    "For datasets, note the name, description, and how it was used\n"
    + BILINGUAL_INSTRUCTION +
    "Respond ONLY with JSON:\n"
    '{"findings": [{"type": "result", "statement": {"en": "...", "zh": "..."}, '
    '"evidence": {"en": "...", "zh": "..."}}], '
    '"methods": [{"name": {"en": "...", "zh": "..."}, "description": {"en": "...", "zh": "..."}}], '
    '"datasets": [{"name": {"en": "...", "zh": "..."}, "description": {"en": "...", "zh": "..."}, '
    '"usage": {"en": "...", "zh": "..."}}]}\n'
)

FLASHCARD_PROMPT = (
    "You are an expert educator creating spaced repetition flashcards. "
    "Given these key concepts and findings from a paper, create flashcards.\n\n"
    "Rules:\n"
    "- Create 5-15 cards per paper\n"
    "- Each card tests ONE specific concept or finding\n"
    "- Front: clear question (bilingual). Back: concise, accurate answer (bilingual)\n"
    "- Difficulty 1-5 (1=basic terminology, 5=nuanced understanding)\n"
    "- Tag each card with relevant categories\n"
    + BILINGUAL_INSTRUCTION +
    "Respond ONLY with JSON:\n"
    '{"flashcards": [{"front": {"en": "...", "zh": "..."}, '
    '"back": {"en": "...", "zh": "..."}, "tags": ["method"], "difficulty": 3}]}\n'
)


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _bi_text(val: any) -> str:
    """从双语字段中提取英文文本用于数据库索引。"""
    if isinstance(val, dict):
        return val.get("en", val.get("zh", ""))
    return str(val) if val else ""


import re as _re

def _repair_json(raw: str) -> dict:
    """Attempt to repair common LLM JSON issues: trailing commas, unescaped quotes, truncation."""
    s = raw
    # Remove trailing commas before } or ]
    s = _re.sub(r',\s*([}\]])', r'\1', s)
    # Fix unescaped newlines inside strings
    s = _re.sub(r'(?<!\\)\n', r'\\n', s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Try truncation repair: close all open brackets/braces
    brackets = []
    in_str = False
    escape = False
    for ch in s:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in '{[':
            brackets.append('}' if ch == '{' else ']')
        elif ch in '}]' and brackets:
            brackets.pop()
    # Close unclosed brackets
    if brackets:
        # Remove trailing partial content after last complete value
        last_comma = s.rfind(',')
        last_brace = max(s.rfind('}'), s.rfind(']'))
        if last_comma > last_brace:
            s = s[:last_comma]
        s += ''.join(reversed(brackets))
        s = _re.sub(r',\s*([}\]])', r'\1', s)
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError("Cannot repair JSON", raw, 0)


class KnowledgeExtractor:
    """从学术论文 PDF 中提取结构化知识（双语输出）。"""

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
            paper.title = _bi_text(knowledge.get("metadata", {}).get("title", ""))
            paper.doi = knowledge.get("metadata", {}).get("doi")
            paper.arxiv_id = knowledge.get("metadata", {}).get("arxiv_id")
            paper.year = knowledge.get("metadata", {}).get("year")
            paper.venue = knowledge.get("metadata", {}).get("venue")
            paper.extraction_status = "completed"
            paper.updated_at = datetime.utcnow()
            self._save_paper(paper)
            logger.info("Knowledge extraction completed: %s - %s", paper_id, paper.title)

            # Auto-index to vector database
            try:
                from .vector_search import get_vector_service
                vs = get_vector_service()
                if vs:
                    indexed = await vs.index_paper(paper_id, knowledge)
                    logger.info("Vector indexed %d chunks for %s", indexed, paper_id)
            except Exception:
                logger.warning("Vector indexing failed for %s", paper_id)

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
        pages_text = self._extract_text(pdf_bytes)
        full_text = "\n\n".join(pages_text)

        first_pages = "\n\n".join(pages_text[:2])
        metadata = await self._llm_call(METADATA_PROMPT, first_pages, "metadata")

        sections_data = await self._llm_call(SECTIONS_PROMPT, full_text[:8000], "sections")
        sections = sections_data.get("sections", [])
        for i, sec in enumerate(sections):
            sec["id"] = f"sec_{i + 1}"

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

        entities = self._deduplicate_entities(all_entities)

        entity_map: dict[str, str] = {}
        for ent in entities:
            ent_id = _gen_id("ent")
            # 用英文名做 key（兼容双语和纯字符串）
            name_en = _bi_text(ent.get("name", "")).lower()
            entity_map[name_en] = ent_id
            ent["id"] = ent_id

        for rel in all_relationships:
            rel["id"] = _gen_id("rel")
            src = rel.get("source", "").lower()
            tgt = rel.get("target", "").lower()
            rel["source_entity_id"] = entity_map.get(src, "")
            rel["target_entity_id"] = entity_map.get(tgt, "")

        relationships = [
            r for r in all_relationships
            if r.get("source_entity_id") and r.get("target_entity_id")
        ]

        findings_data = await self._llm_call(
            FINDINGS_PROMPT, full_text[:8000], "findings"
        )
        findings = findings_data.get("findings", [])
        for _i, f in enumerate(findings):
            f["id"] = _gen_id("find")
        methods = findings_data.get("methods", [])
        datasets = findings_data.get("datasets", [])

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
            "bilingual": True,
        }

        self._save_index_tables(paper_id, user_id, entities, relationships, flashcards)

        return knowledge

    # ------------------------------------------------------------------
    # PDF 文本提取
    # ------------------------------------------------------------------

    def _extract_text(self, pdf_bytes: bytes) -> list[str]:
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
                raw = content[start : end + 1]
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    # Try to repair common LLM JSON issues
                    return _repair_json(raw)
            raise

    # ------------------------------------------------------------------
    # 实体去重
    # ------------------------------------------------------------------

    def _deduplicate_entities(self, entities: list[dict]) -> list[dict]:
        seen: dict[str, dict] = {}
        for ent in entities:
            key = _bi_text(ent.get("name", "")).lower().strip()
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
        if not sections:
            return [full_text]

        chunks: list[str] = []
        text_lower = full_text.lower()
        positions: list[int] = []

        for sec in sections:
            title_val = sec.get("title", "")
            title = _bi_text(title_val).lower()
            pos = text_lower.find(title)
            positions.append(pos if pos >= 0 else -1)

        valid = [(pos, i) for i, pos in enumerate(positions) if pos >= 0]
        valid.sort()

        if len(valid) < 2:
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
        with Session(engine) as session:
            for ent in entities:
                session.merge(KnowledgeEntity(
                    id=ent["id"],
                    paper_id=paper_id,
                    user_id=user_id,
                    name=_bi_text(ent.get("name", "")),
                    type=ent.get("type", "concept"),
                    aliases_json=json.dumps(ent.get("aliases", []), ensure_ascii=False),
                    definition=_bi_text(ent.get("definition")),
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
                    description=_bi_text(rel.get("description")),
                    confidence=rel.get("confidence", 0.5),
                ))

            now = datetime.utcnow()
            for fc in flashcards:
                session.merge(Flashcard(
                    id=fc["id"],
                    paper_id=paper_id,
                    user_id=user_id,
                    front=_bi_text(fc.get("front", "")),
                    back=_bi_text(fc.get("back", "")),
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
