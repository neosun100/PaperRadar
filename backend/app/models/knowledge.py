"""知识库模型 - 可迁移的学术论文知识存储"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class PaperKnowledge(SQLModel, table=True):
    id: str = Field(primary_key=True)
    task_id: str | None = Field(default=None, index=True)
    user_id: int = Field(default=0, index=True)

    title: str = Field(default="")
    doi: str | None = Field(default=None, index=True)
    arxiv_id: str | None = Field(default=None)
    year: int | None = Field(default=None)
    venue: str | None = Field(default=None)

    knowledge_json: str | None = Field(default=None)

    extraction_status: str = Field(default="pending")
    extraction_model: str | None = Field(default=None)
    extraction_error: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeEntity(SQLModel, table=True):
    id: str = Field(primary_key=True)
    paper_id: str = Field(foreign_key="paperknowledge.id", index=True)
    user_id: int = Field(default=0, index=True)

    name: str = Field(index=True)
    type: str
    aliases_json: str | None = Field(default=None)
    definition: str | None = Field(default=None)
    importance: float = Field(default=0.5)


class KnowledgeRelationship(SQLModel, table=True):
    id: str = Field(primary_key=True)
    paper_id: str = Field(foreign_key="paperknowledge.id", index=True)
    user_id: int = Field(default=0, index=True)

    source_entity_id: str = Field(index=True)
    target_entity_id: str = Field(index=True)
    type: str
    description: str | None = Field(default=None)
    confidence: float = Field(default=0.5)


class Flashcard(SQLModel, table=True):
    id: str = Field(primary_key=True)
    paper_id: str = Field(foreign_key="paperknowledge.id", index=True)
    user_id: int = Field(default=0, index=True)

    front: str
    back: str
    tags_json: str | None = Field(default=None)
    difficulty: int = Field(default=3)

    interval_days: float = Field(default=1.0)
    ease_factor: float = Field(default=2.5)
    repetitions: int = Field(default=0)
    next_review: datetime = Field(default_factory=datetime.utcnow)
    last_review: datetime | None = Field(default=None)


class UserAnnotation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    paper_id: str = Field(foreign_key="paperknowledge.id", index=True)
    user_id: int = Field(default=0, index=True)

    type: str
    content: str
    target_type: str = Field(default="paper")
    target_id: str = Field(default="")
    tags_json: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
