"""通知服务 — Bark (iOS) + Lark (Card 2.0) 推送"""

from __future__ import annotations

import logging

import httpx

from ..core.config import NotificationConfig

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, config: NotificationConfig) -> None:
        self.config = config

    async def notify_new_papers(self, papers: list[dict]) -> None:
        """推送新发现的论文通知"""
        if not papers:
            return
        count = len(papers)
        titles = "\n".join(f"• {p.get('title', '')[:80]}" for p in papers[:5])
        if count > 5:
            titles += f"\n... and {count - 5} more"

        if self.config.bark_key:
            await self._send_bark(count, titles)
        if self.config.lark_webhook:
            await self._send_lark(count, papers)
        if self.config.webhook_url:
            await self._send_webhook(count, papers)

    async def _send_bark(self, count: int, titles: str) -> None:
        """Bark iOS 推送"""
        url = self.config.bark_url or "https://api.day.app"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(f"{url}/{self.config.bark_key}", json={
                    "title": f"🛰️ PaperRadar: {count} new papers",
                    "body": titles,
                    "group": "PaperRadar",
                    "sound": "minuet",
                })
            logger.info("Bark notification sent: %d papers", count)
        except Exception:
            logger.exception("Bark notification failed")

    async def _send_lark(self, count: int, papers: list[dict]) -> None:
        """Lark Card 2.0 推送"""
        # Build card elements
        elements = []
        for p in papers[:8]:
            score = p.get("score", 0)
            score_emoji = "🟢" if score >= 0.9 else "🟡" if score >= 0.8 else "🔵"
            elements.append({
                "tag": "markdown",
                "content": f"{score_emoji} **{p.get('title', '')[:80]}**\n"
                           f"Score: {score:.0%} | {', '.join(p.get('authors', [])[:3])}\n"
                           f"[PDF]({p.get('pdf_url', '')})",
            })
            elements.append({"tag": "hr"})

        if len(papers) > 8:
            elements.append({"tag": "markdown", "content": f"... and {len(papers) - 8} more papers"})

        card = {
            "msg_type": "interactive",
            "card": {
                "schema": "2.0",
                "header": {
                    "title": {"tag": "plain_text", "content": f"🛰️ PaperRadar: {count} New Papers Discovered"},
                    "template": "turquoise",
                },
                "body": {"elements": elements},
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.config.lark_webhook, json=card)
                resp.raise_for_status()
            logger.info("Lark notification sent: %d papers", count)
        except Exception:
            logger.exception("Lark notification failed")

    async def _send_webhook(self, count: int, papers: list[dict]) -> None:
        """Generic webhook — works with Slack, Discord, Telegram bots, n8n, etc."""
        payload = {
            "event": "new_papers",
            "count": count,
            "papers": [
                {
                    "title": p.get("title", "")[:120],
                    "authors": p.get("authors", [])[:3],
                    "score": p.get("score", 0),
                    "source": p.get("source", ""),
                    "pdf_url": p.get("pdf_url", ""),
                    "arxiv_id": p.get("arxiv_id", ""),
                }
                for p in papers[:10]
            ],
            "source": "PaperRadar",
        }
        # Detect Slack/Discord format
        url = self.config.webhook_url
        if "hooks.slack.com" in url or "discord.com/api/webhooks" in url:
            titles = "\n".join(f"• {p.get('title', '')[:80]}" for p in papers[:5])
            payload = {"text": f"🛰️ PaperRadar: {count} new papers discovered\n{titles}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            logger.info("Webhook notification sent: %d papers to %s", count, url[:50])
        except Exception:
            logger.exception("Webhook notification failed")
