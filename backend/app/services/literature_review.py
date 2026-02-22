"""文献综述生成服务 — 基于知识库自动生成结构化文献综述"""

from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)

REVIEW_PROMPT = (
    "You are an expert academic researcher writing a literature review. "
    "Based on the following papers from a knowledge base, write a comprehensive, "
    "well-structured literature review.\n\n"
    "The review MUST include:\n"
    "1. **Introduction** — Research background, motivation, scope of the review\n"
    "2. **Methodology Overview** — Summary of approaches across papers\n"
    "3. **Key Findings** — Major results and contributions, organized thematically\n"
    "4. **Comparative Analysis** — How methods/results compare across papers\n"
    "5. **Limitations & Gaps** — What remains unsolved\n"
    "6. **Future Directions** — Promising research directions\n"
    "7. **References** — Cite each paper as [Author, Year]\n\n"
    "Write in academic style. Cite specific papers when making claims. "
    "Output as Markdown. Respond in the same language as the user's query.\n\n"
    "Papers:\n{context}\n"
)


class LiteratureReviewGenerator:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def generate(self, papers_json: list[dict], topic: str = "") -> str:
        context = self._build_context(papers_json)
        user_msg = f"Topic: {topic}\n\nWrite a literature review based on these {len(papers_json)} papers." if topic else f"Write a literature review based on these {len(papers_json)} papers."

        async with httpx.AsyncClient(base_url=self.base_url, timeout=300.0) as client:
            resp = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": REVIEW_PROMPT.format(context=context)},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _text(self, val) -> str:
        if isinstance(val, dict):
            return val.get("en", val.get("zh", ""))
        return str(val) if val else ""

    def _build_context(self, papers: list[dict]) -> str:
        parts = []
        for i, p in enumerate(papers[:15]):
            meta = p.get("metadata", {})
            title = self._text(meta.get("title", ""))
            authors = ", ".join(a.get("name", "") for a in (meta.get("authors") or [])[:3])
            year = meta.get("year", "")
            abstract = self._text(meta.get("abstract", ""))[:300]
            findings = [self._text(f.get("statement", "")) for f in p.get("findings", [])[:5]]
            methods = [self._text(m.get("name", "")) for m in p.get("methods", [])]

            parts.append(f"[Paper {i+1}] {title} ({authors}, {year})")
            if abstract:
                parts.append(f"  Abstract: {abstract}")
            if findings:
                parts.append(f"  Findings: {'; '.join(findings)}")
            if methods:
                parts.append(f"  Methods: {', '.join(methods)}")
            parts.append("")
        return "\n".join(parts)
