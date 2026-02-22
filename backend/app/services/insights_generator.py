"""跨论文研究洞察服务 — 用 LLM 对知识库中所有论文做综合分析"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

INSIGHTS_PROMPT = (
    "You are an expert academic research analyst. Given structured knowledge extracted "
    "from multiple research papers, produce a comprehensive cross-paper analysis.\n\n"
    "You MUST output ALL text fields as bilingual objects: {\"en\": \"...\", \"zh\": \"...\"}.\n\n"
    "Generate the following sections:\n\n"
    "1. **field_overview**: A 3-5 paragraph literature review synthesizing all papers. "
    "Cover: research background, major methodological approaches, key findings, and trends.\n\n"
    "2. **method_comparison**: A list of methods across papers. For each:\n"
    "   - paper_title, method_name, core_idea, strengths, limitations, metrics (key results)\n\n"
    "3. **timeline**: A chronological list of papers with: year, paper_title, contribution "
    "(one sentence describing what this paper added to the field)\n\n"
    "4. **research_gaps**: A list of unresolved problems and future directions, each with:\n"
    "   - gap (description of the problem), evidence (which papers mention this), "
    "   suggested_direction (possible approach)\n\n"
    "5. **paper_connections**: A list of connections between papers:\n"
    "   - source_paper, target_paper, relation_type (extends/improves/contradicts/"
    "uses_same_data/cites/compares_with), description\n\n"
    "Respond ONLY with a JSON object with these 5 keys. All text fields bilingual {en, zh}.\n"
)


class InsightsGenerator:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=httpx.Timeout(300.0, connect=10.0),
        )

    async def generate(self, papers_json: list[dict]) -> dict:
        """从多篇论文的知识 JSON 生成跨论文洞察。"""
        # 构建精简的上下文（避免超 token）
        context = []
        for p in papers_json:
            meta = p.get("metadata", {})
            entry = {
                "title": meta.get("title", ""),
                "year": meta.get("year"),
                "abstract": meta.get("abstract", ""),
                "findings": [f.get("statement", "") for f in p.get("findings", [])[:5]],
                "methods": [{"name": m.get("name", ""), "description": m.get("description", "")} for m in p.get("methods", [])],
                "entities": [{"name": e.get("name", ""), "type": e.get("type", "")} for e in p.get("entities", [])[:10]],
                "datasets": [d.get("name", "") for d in p.get("datasets", [])],
            }
            context.append(entry)

        user_content = json.dumps(context, ensure_ascii=False)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": INSIGHTS_PROMPT},
                {"role": "user", "content": f"Papers data ({len(context)} papers):\n\n{user_content}"},
            ],
            "temperature": 0.2,
            "max_tokens": 8192,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        response = await self._client.post("/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        # Parse JSON
        if content.startswith("```"):
            lines = content.split("\n")
            start = 1 if lines[0].startswith("```") else 0
            end = -1 if lines[-1].strip() == "```" else len(lines)
            content = "\n".join(lines[start:end])
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            s, e = content.find("{"), content.rfind("}")
            if s != -1 and e != -1:
                result = json.loads(content[s:e + 1])
            else:
                raise

        result["generated_at"] = datetime.utcnow().isoformat()
        result["paper_count"] = len(papers_json)
        return result

    async def close(self) -> None:
        await self._client.aclose()
