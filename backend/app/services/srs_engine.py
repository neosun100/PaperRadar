"""SM-2 间隔重复算法实现"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models.knowledge import Flashcard


class SRSEngine:
    """SuperMemo SM-2 算法。"""

    @staticmethod
    def review(card: Flashcard, quality: int) -> None:
        """
        处理一次复习。

        quality: 0-5
            0 = 完全遗忘
            1 = 回忆错误
            2 = 回忆错误但看到答案后觉得熟悉
            3 = 回忆正确但很费力
            4 = 回忆正确稍有犹豫
            5 = 完美回忆
        """
        now = datetime.utcnow()
        card.last_review = now

        if quality >= 3:
            # 回忆成功
            if card.repetitions == 0:
                card.interval_days = 1.0
            elif card.repetitions == 1:
                card.interval_days = 6.0
            else:
                card.interval_days = card.interval_days * card.ease_factor
            card.repetitions += 1
        else:
            # 回忆失败，重置
            card.repetitions = 0
            card.interval_days = 1.0

        # 更新 ease factor
        card.ease_factor = max(
            1.3,
            card.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
        )

        card.next_review = now + timedelta(days=card.interval_days)

    @staticmethod
    def get_due_count(cards: list[Flashcard]) -> int:
        """计算到期闪卡数量。"""
        now = datetime.utcnow()
        return sum(1 for c in cards if c.next_review <= now)
