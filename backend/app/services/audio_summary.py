"""Paper Audio Summary — NotebookLM-style podcast generation.

Flow: paper knowledge → LLM script → TTS audio (OpenAI-compatible /audio/speech)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

AUDIO_DIR = Path("/app/data/audio")

SCRIPT_SYSTEM_PROMPT = """\
You are a podcast script writer. Given an academic paper's knowledge, write a \
natural, engaging conversation between two hosts (Alex and Sam) discussing the paper.

Rules:
- 8-12 exchanges total (keep it concise, ~3 min when spoken)
- Alex introduces the paper and asks questions; Sam explains key findings
- Use simple language, avoid jargon — explain technical terms naturally
- Cover: what the paper is about, key methods, main findings, why it matters
- Each line should be 1-3 sentences max
- Output ONLY a JSON array of objects: [{"speaker": "Alex", "text": "..."}, ...]
- Respond in the same language as the paper title below
"""


class AudioSummaryService:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def generate(self, paper_id: str, knowledge_json: str) -> Path:
        """Generate audio summary, return path to MP3 file."""
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        out_path = AUDIO_DIR / f"{paper_id}.mp3"
        if out_path.exists():
            return out_path

        knowledge = json.loads(knowledge_json) if isinstance(knowledge_json, str) else knowledge_json
        script = await self._generate_script(knowledge)
        await self._synthesize_audio(script, out_path)
        return out_path

    def get_cached(self, paper_id: str) -> Path | None:
        p = AUDIO_DIR / f"{paper_id}.mp3"
        return p if p.exists() else None

    def delete_cached(self, paper_id: str) -> bool:
        p = AUDIO_DIR / f"{paper_id}.mp3"
        if p.exists():
            p.unlink()
            return True
        return False

    async def _generate_script(self, knowledge: dict) -> list[dict]:
        """Use LLM to generate podcast dialogue script."""
        context = self._build_context(knowledge)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            resp = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SCRIPT_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Write a podcast script for this paper:\n\n{context}"},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

        # Parse JSON from response (handle markdown code blocks)
        content = content.strip()
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
        if m:
            content = m.group(1)
        script = json.loads(content)
        # Cap at 12 exchanges to keep audio under 3 minutes
        return script[:12]

    async def _synthesize_audio(self, script: list[dict], out_path: Path) -> None:
        """Call TTS API for each line and concatenate raw MP3 bytes."""
        from ..core.config import get_config
        cfg = get_config()
        # Use server-side TTS config (falls back to LLM config)
        tts_base = cfg.tts.base_url or cfg.llm.base_url
        tts_key = cfg.tts.api_key or cfg.llm.api_key
        tts_model = cfg.tts.model or "openai/tts-1"

        voices = {"Alex": "alloy", "Sam": "nova"}
        chunks: list[bytes] = []

        async with httpx.AsyncClient(base_url=tts_base, timeout=60.0) as client:
            for line in script:
                speaker = line.get("speaker", "Alex")
                text = line.get("text", "")
                if not text:
                    continue
                voice = voices.get(speaker, "alloy")
                resp = await client.post(
                    "/audio/speech",
                    json={"model": tts_model, "input": text, "voice": voice, "response_format": "mp3"},
                    headers={"Authorization": f"Bearer {tts_key}", "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                chunks.append(resp.content)

        out_path.write_bytes(b"".join(chunks))

    def _build_context(self, knowledge: dict) -> str:
        parts = []
        meta = knowledge.get("metadata", {})
        parts.append(f"Title: {self._text(meta.get('title', ''))}")
        abstract = self._text(meta.get("abstract", ""))
        if abstract:
            parts.append(f"Abstract: {abstract[:800]}")
        findings = knowledge.get("findings", [])
        if findings:
            parts.append("Key Findings:")
            for f in findings[:6]:
                parts.append(f"- [{f.get('type','')}] {self._text(f.get('statement',''))}")
        methods = knowledge.get("methods", [])
        if methods:
            parts.append("Methods:")
            for m in methods[:4]:
                parts.append(f"- {self._text(m.get('name',''))}: {self._text(m.get('description',''))}")
        return "\n".join(parts)

    @staticmethod
    def _text(val) -> str:
        if isinstance(val, dict):
            return val.get("en", val.get("zh", ""))
        return str(val) if val else ""
