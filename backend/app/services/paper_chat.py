"""Paper Chat 服务 — 与论文对话"""

from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = (
    "You are an expert research assistant. You have access to the full knowledge "
    "extracted from an academic paper. Answer the user's question based on this knowledge. "
    "Be precise, cite specific findings or methods from the paper when relevant. "
    "If the answer is not in the paper, say so clearly.\n\n"
    "Respond in the same language as the user's question.\n\n"
    "Paper knowledge:\n{context}\n"
)


class PaperChatService:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def chat(self, knowledge_json: str, message: str, history: list[dict] | None = None) -> str:
        """与论文对话"""
        # Build context from knowledge
        knowledge = json.loads(knowledge_json) if isinstance(knowledge_json, str) else knowledge_json
        context = self._build_context(knowledge)
        system = CHAT_SYSTEM_PROMPT.format(context=context)

        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history[-6:])  # Keep last 6 turns
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            resp = await client.post(
                "/chat/completions",
                json={"model": self.model, "messages": messages, "temperature": 0.3, "max_tokens": 2048},
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _build_context(self, knowledge: dict) -> str:
        """从知识 JSON 构建精简的上下文"""
        parts = []
        meta = knowledge.get("metadata", {})
        title = meta.get("title", "")
        if isinstance(title, dict):
            title = title.get("en", title.get("zh", ""))
        parts.append(f"Title: {title}")

        abstract = meta.get("abstract", "")
        if isinstance(abstract, dict):
            abstract = abstract.get("en", abstract.get("zh", ""))
        if abstract:
            parts.append(f"Abstract: {abstract}")

        # Findings
        findings = knowledge.get("findings", [])
        if findings:
            parts.append("Key Findings:")
            for f in findings[:10]:
                stmt = f.get("statement", "")
                if isinstance(stmt, dict):
                    stmt = stmt.get("en", stmt.get("zh", ""))
                parts.append(f"- [{f.get('type', '')}] {stmt}")

        # Methods
        methods = knowledge.get("methods", [])
        if methods:
            parts.append("Methods:")
            for m in methods:
                name = m.get("name", "")
                desc = m.get("description", "")
                if isinstance(name, dict):
                    name = name.get("en", "")
                if isinstance(desc, dict):
                    desc = desc.get("en", "")
                parts.append(f"- {name}: {desc}")

        # Entities
        entities = knowledge.get("entities", [])
        if entities:
            parts.append("Key Entities:")
            for e in entities[:15]:
                name = e.get("name", "")
                defn = e.get("definition", "")
                if isinstance(name, dict):
                    name = name.get("en", "")
                if isinstance(defn, dict):
                    defn = defn.get("en", "")
                parts.append(f"- {name} ({e.get('type', '')}): {defn}")

        return "\n".join(parts)
