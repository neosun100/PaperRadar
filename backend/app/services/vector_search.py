"""向量搜索服务 — ChromaDB + Bedrock Embedding"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import chromadb
import httpx

from ..core.config import get_config

logger = logging.getLogger(__name__)


class VectorSearchService:
    """嵌入式向量搜索：论文入库时自动嵌入，支持语义搜索和 RAG 检索。"""

    def __init__(self, persist_dir: str = "/app/data/vectordb") -> None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        # Collections: papers (abstract+title), chunks (findings+entities+methods)
        self._papers = self._client.get_or_create_collection(
            name="papers", metadata={"hnsw:space": "cosine"},
        )
        self._chunks = self._client.get_or_create_collection(
            name="chunks", metadata={"hnsw:space": "cosine"},
        )
        self._config = get_config()

    async def index_paper(self, paper_id: str, knowledge: dict) -> int:
        """将论文知识嵌入向量库。返回嵌入的 chunk 数量。"""
        cfg = self._config.llm
        if not cfg.embedding_model or not cfg.api_key:
            logger.info("No embedding model configured, skipping vector indexing")
            return 0

        meta = knowledge.get("metadata", {})
        title = self._text(meta.get("title", ""))
        abstract = self._text(meta.get("abstract", ""))

        # Build text chunks to embed
        chunks = []

        # 1. Title + Abstract (paper-level)
        if title:
            paper_text = f"{title}. {abstract}" if abstract else title
            chunks.append({"id": f"{paper_id}_abstract", "text": paper_text, "type": "abstract", "paper_id": paper_id})

        # 2. Each finding
        for i, f in enumerate(knowledge.get("findings", [])):
            stmt = self._text(f.get("statement", ""))
            if stmt:
                chunks.append({"id": f"{paper_id}_finding_{i}", "text": f"[{f.get('type','')}] {stmt}", "type": "finding", "paper_id": paper_id})

        # 3. Each method
        for i, m in enumerate(knowledge.get("methods", [])):
            name = self._text(m.get("name", ""))
            desc = self._text(m.get("description", ""))
            if name:
                chunks.append({"id": f"{paper_id}_method_{i}", "text": f"{name}: {desc}", "type": "method", "paper_id": paper_id})

        # 4. Key entities with definitions
        for i, e in enumerate(knowledge.get("entities", [])):
            name = self._text(e.get("name", ""))
            defn = self._text(e.get("definition", ""))
            if name and defn:
                chunks.append({"id": f"{paper_id}_entity_{i}", "text": f"{name} ({e.get('type','')}): {defn}", "type": "entity", "paper_id": paper_id})

        # 5. Flashcard Q&A pairs
        for i, fc in enumerate(knowledge.get("flashcards", [])):
            front = self._text(fc.get("front", ""))
            back = self._text(fc.get("back", ""))
            if front:
                chunks.append({"id": f"{paper_id}_flashcard_{i}", "text": f"Q: {front} A: {back}", "type": "flashcard", "paper_id": paper_id})

        if not chunks:
            return 0

        # Get embeddings from LLM API
        texts = [c["text"] for c in chunks]
        embeddings = await self._get_embeddings(texts)
        if not embeddings:
            return 0

        # Index paper-level
        paper_chunks = [c for c, e in zip(chunks, embeddings) if c["type"] == "abstract"]
        if paper_chunks:
            self._papers.upsert(
                ids=[paper_chunks[0]["id"]],
                embeddings=[embeddings[chunks.index(paper_chunks[0])]],
                documents=[paper_chunks[0]["text"]],
                metadatas=[{"paper_id": paper_id, "title": title[:200]}],
            )

        # Index all chunks
        self._chunks.upsert(
            ids=[c["id"] for c in chunks],
            embeddings=embeddings,
            documents=[c["text"] for c in chunks],
            metadatas=[{"paper_id": c["paper_id"], "type": c["type"]} for c in chunks],
        )

        logger.info("Indexed %d chunks for paper %s", len(chunks), paper_id)
        return len(chunks)

    async def search(self, query: str, n_results: int = 10, filter_type: str | None = None) -> list[dict]:
        """语义搜索：返回最相关的 chunks。"""
        cfg = self._config.llm
        if not cfg.embedding_model or not cfg.api_key:
            return []

        embeddings = await self._get_embeddings([query])
        if not embeddings:
            return []

        where = {"type": filter_type} if filter_type else None
        results = self._chunks.query(
            query_embeddings=embeddings,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for i in range(len(results["ids"][0])):
            hits.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i],  # cosine distance → similarity
            })
        return hits

    async def search_papers(self, query: str, n_results: int = 5) -> list[dict]:
        """论文级语义搜索。"""
        cfg = self._config.llm
        if not cfg.embedding_model or not cfg.api_key:
            return []

        embeddings = await self._get_embeddings([query])
        if not embeddings:
            return []

        results = self._papers.query(
            query_embeddings=embeddings,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for i in range(len(results["ids"][0])):
            hits.append({
                "paper_id": results["metadatas"][0][i].get("paper_id", ""),
                "title": results["metadatas"][0][i].get("title", ""),
                "text": results["documents"][0][i][:200],
                "score": 1 - results["distances"][0][i],
            })
        return hits

    async def get_context_for_chat(self, query: str, n_results: int = 15) -> str:
        """为 RAG 对话检索最相关的上下文片段。"""
        hits = await self.search(query, n_results=n_results)
        if not hits:
            return ""
        parts = []
        for h in hits:
            parts.append(f"[{h['metadata'].get('type','')}] {h['text']}")
        return "\n".join(parts)

    @property
    def stats(self) -> dict:
        return {
            "papers": self._papers.count(),
            "chunks": self._chunks.count(),
            "embedding_model": self._config.llm.embedding_model or "not configured",
        }

    async def _get_embeddings(self, texts: list[str]) -> list[list[float]] | None:
        """调用 LLM API 获取 embeddings。"""
        cfg = self._config.llm
        try:
            async with httpx.AsyncClient(base_url=cfg.base_url, timeout=60.0) as client:
                resp = await client.post(
                    "/embeddings",
                    json={"model": cfg.embedding_model, "input": texts},
                    headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                # OpenAI-compatible format
                return [item["embedding"] for item in data["data"]]
        except Exception:
            logger.exception("Embedding API call failed")
            return None

    def _text(self, val) -> str:
        if isinstance(val, dict):
            return val.get("en", val.get("zh", ""))
        return str(val) if val else ""


# Global instance
_vector_service: VectorSearchService | None = None


def get_vector_service() -> VectorSearchService | None:
    global _vector_service
    if _vector_service is None:
        cfg = get_config()
        if cfg.llm.embedding_model:
            _vector_service = VectorSearchService()
    return _vector_service
