"""Paper Chat 服务 — 单篇论文对话 + 跨论文对话"""

from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = (
    "You are an expert research assistant. You have access to knowledge "
    "extracted from academic papers. Answer the user's question based on this knowledge. "
    "Be precise, cite specific findings or methods from the papers when relevant. "
    "If the answer is not in the papers, say so clearly.\n\n"
    "Respond in the same language as the user's question.\n\n"
    "Paper knowledge:\n{context}\n"
)


class PaperChatService:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def chat(self, knowledge_json: str, message: str, history: list[dict] | None = None) -> str:
        """与单篇论文对话"""
        knowledge = json.loads(knowledge_json) if isinstance(knowledge_json, str) else knowledge_json
        context = self._build_context(knowledge)
        return await self._call_llm(context, message, history)

    async def chat_multi(self, papers_json: list[dict], message: str, history: list[dict] | None = None) -> str:
        """跨论文对话"""
        context_parts = []
        for i, p in enumerate(papers_json[:10]):  # Limit to 10 papers
            meta = p.get("metadata", {})
            title = self._text(meta.get("title", f"Paper {i+1}"))
            context_parts.append(f"=== Paper {i+1}: {title} ===")
            context_parts.append(self._build_context(p))
            context_parts.append("")
        context = "\n".join(context_parts)
        return await self._call_llm(context, message, history)

    async def chat_with_context(self, rag_context: str, message: str, history: list[dict] | None = None) -> str:
        """RAG mode: use vector-retrieved context"""
        return await self._call_llm(rag_context, message, history)

    async def _call_llm(self, context: str, message: str, history: list[dict] | None) -> str:
        # Truncate context to ~12k chars to leave room for response
        if len(context) > 12000:
            context = context[:12000] + "\n... (truncated)"
        system = CHAT_SYSTEM_PROMPT.format(context=context)
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            resp = await client.post(
                "/chat/completions",
                json={"model": self.model, "messages": messages, "temperature": 0.3, "max_tokens": 2048},
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _text(self, val) -> str:
        if isinstance(val, dict):
            return val.get("en", val.get("zh", ""))
        return str(val) if val else ""

    def _build_context(self, knowledge: dict) -> str:
        parts = []
        meta = knowledge.get("metadata", {})
        parts.append(f"Title: {self._text(meta.get('title', ''))}")
        abstract = self._text(meta.get("abstract", ""))
        if abstract:
            parts.append(f"Abstract: {abstract[:500]}")

        findings = knowledge.get("findings", [])
        if findings:
            parts.append("Findings:")
            for f in findings[:8]:
                parts.append(f"- [{f.get('type','')}] {self._text(f.get('statement',''))}")

        methods = knowledge.get("methods", [])
        if methods:
            parts.append("Methods:")
            for m in methods[:5]:
                parts.append(f"- {self._text(m.get('name',''))}: {self._text(m.get('description',''))}")

        entities = knowledge.get("entities", [])
        if entities:
            parts.append("Entities:")
            for e in entities[:10]:
                parts.append(f"- {self._text(e.get('name',''))} ({e.get('type','')}): {self._text(e.get('definition',''))}")

        return "\n".join(parts)
