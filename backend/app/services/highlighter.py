"""
高亮服务 - 使用 LLM 识别学术论文中的关键句子并在 PDF 中添加多色高亮注释
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

import fitz
import httpx

logger = logging.getLogger(__name__)


@dataclass
class HighlightSentence:
    text: str
    category: str  # "core_conclusion" | "method_innovation" | "key_data"
    page_index: int


@dataclass
class HighlightStats:
    core_conclusions: int = 0
    method_innovations: int = 0
    key_data: int = 0
    total: int = 0
    failed_matches: int = 0

    def to_dict(self) -> dict:
        return {
            "core_conclusions": self.core_conclusions,
            "method_innovations": self.method_innovations,
            "key_data": self.key_data,
            "total": self.total,
            "failed_matches": self.failed_matches,
        }


# PyMuPDF RGB (0.0-1.0)
HIGHLIGHT_COLORS = {
    "core_conclusion": (1.0, 0.95, 0.6),
    "method_innovation": (0.7, 0.85, 1.0),
    "key_data": (0.7, 1.0, 0.7),
}

HIGHLIGHT_SYSTEM_PROMPT = (
    "You are an expert academic paper analyst. Your task is to identify key sentences "
    "from a page of an academic paper.\n\n"
    "Classify important sentences into exactly 3 categories:\n"
    "1. core_conclusion - Core conclusions or main findings of the research\n"
    "2. method_innovation - Methodological innovations, novel approaches, or technical contributions\n"
    "3. key_data - Key data points, experimental results, metrics, or quantitative findings\n\n"
    "RULES:\n"
    "- Return 3-8 sentences per page (fewer for short pages)\n"
    "- Each sentence must be an EXACT substring from the provided text\n"
    "- Do not modify, paraphrase, or truncate sentences\n"
    "- Focus on the most important sentences; skip boilerplate, references, and headers\n"
    "- If a page has no notable sentences (e.g., references, table of contents), return an empty list\n"
    "- For translated (Chinese) text, the sentences should match the Chinese text exactly\n\n"
    "Respond ONLY with a JSON object:\n"
    "{\n"
    '  "sentences": [\n'
    '    {"text": "exact sentence from the page", "category": "core_conclusion"},\n'
    '    {"text": "another exact sentence", "category": "method_innovation"}\n'
    "  ]\n"
    "}\n"
)


class HighlightService:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        max_concurrent_pages: int = 4,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_concurrent_pages = max_concurrent_pages
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

    async def highlight_pdf(self, pdf_bytes: bytes) -> tuple[bytes, HighlightStats]:
        """主入口：提取文本 → LLM 分类 → 添加注释 → 返回高亮后的 PDF"""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page_sentences = await self._extract_and_classify_pages(doc)
            stats = self._apply_highlights(doc, page_sentences)
            result_bytes = doc.tobytes()
            return result_bytes, stats
        except Exception as exc:
            logger.error("Highlight processing failed: %s", exc)
            return pdf_bytes, HighlightStats()
        finally:
            doc.close()

    async def _extract_and_classify_pages(
        self, doc: fitz.Document
    ) -> list[list[HighlightSentence]]:
        """提取每页文本并用 LLM 并发分类"""
        page_texts: list[tuple[int, str]] = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            if text.strip() and len(text.strip()) >= 50:
                page_texts.append((i, text))

        results: list[list[HighlightSentence]] = [[] for _ in range(doc.page_count)]
        semaphore = asyncio.Semaphore(self.max_concurrent_pages)

        async def classify_with_limit(page_index: int, text: str):
            async with semaphore:
                return page_index, await self._classify_page(text, page_index)

        tasks = [classify_with_limit(i, text) for i, text in page_texts]
        for coro in asyncio.as_completed(tasks):
            page_index, sentences = await coro
            results[page_index] = sentences

        return results

    async def _classify_page(
        self, page_text: str, page_index: int
    ) -> list[HighlightSentence]:
        """单页分类，带重试"""
        truncated = page_text[:4000]

        max_retries = 3
        base_delay = 2
        for attempt in range(max_retries):
            try:
                return await self._do_classify(truncated, page_index)
            except Exception as exc:
                if attempt == max_retries - 1:
                    logger.error("Page %d classification failed: %s", page_index, exc)
                    return []
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Page %d error: %s, retrying in %ds...", page_index, exc, delay
                )
                await asyncio.sleep(delay)
        return []

    async def _do_classify(
        self, page_text: str, page_index: int
    ) -> list[HighlightSentence]:
        """LLM API 调用 + JSON 解析"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": HIGHLIGHT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Page {page_index + 1} text:\n\n{page_text}",
                },
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
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

        # Strip markdown code fences
        if content.startswith("```"):
            lines = content.split("\n")
            start_idx = 1 if lines[0].startswith("```") else 0
            end_idx = -1 if lines[-1].strip() == "```" else len(lines)
            content = "\n".join(lines[start_idx:end_idx])

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON object from response
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(content[start : end + 1])
            else:
                raise

        sentences = []
        for item in parsed.get("sentences", []):
            text = item.get("text", "").strip()
            category = item.get("category", "")
            if text and category in HIGHLIGHT_COLORS:
                sentences.append(
                    HighlightSentence(
                        text=text, category=category, page_index=page_index
                    )
                )
        return sentences

    def _apply_highlights(
        self,
        doc: fitz.Document,
        page_sentences: list[list[HighlightSentence]],
    ) -> HighlightStats:
        """在 PDF 中添加高亮注释"""
        stats = HighlightStats()

        for page_index, sentences in enumerate(page_sentences):
            if not sentences:
                continue
            page = doc.load_page(page_index)
            for sent in sentences:
                quads = page.search_for(sent.text, quads=True)
                if quads:
                    annot = page.add_highlight_annot(quads)
                    color = HIGHLIGHT_COLORS[sent.category]
                    annot.set_colors(stroke=color)
                    annot.set_opacity(0.4)
                    annot.set_info(title=sent.category)
                    annot.update()

                    if sent.category == "core_conclusion":
                        stats.core_conclusions += 1
                    elif sent.category == "method_innovation":
                        stats.method_innovations += 1
                    elif sent.category == "key_data":
                        stats.key_data += 1
                    stats.total += 1
                else:
                    stats.failed_matches += 1
                    logger.debug(
                        "Could not find sentence in page %d: %s...",
                        page_index,
                        sent.text[:60],
                    )

        return stats

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> HighlightService:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.close()
