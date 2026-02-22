from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    REWRITING = "rewriting"
    RENDERING = "rendering"
    HIGHLIGHTING = "highlighting"
    COMPLETED = "completed"
    ERROR = "error"


class TaskProgress(SQLModel):
    status: TaskStatus = TaskStatus.PENDING
    percent: int = 0
    message: str = "Task queued"
    error: str | None = None


class TaskResult(SQLModel):
    pdf_bytes: bytes | None = None
    preview_html: str | None = None
    filename: str | None = None


class Task(SQLModel, table=True):
    task_id: str = Field(primary_key=True)
    filename: str
    mode: str = Field(default="translate")

    # Progress fields
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    percent: int = Field(default=0)
    message: str = Field(default="Task queued")
    error: str | None = Field(default=None)

    # Highlight
    highlight: bool = Field(default=False)
    highlight_stats: str | None = Field(default=None)

    # Result fields
    original_pdf_path: str | None = Field(default=None)
    result_pdf_path: str | None = Field(default=None)
    result_preview_html: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # No user_id foreign key — BYOK mode, no auth
    user_id: int | None = Field(default=None, index=True)

    @property
    def progress(self) -> TaskProgress:
        return TaskProgress(status=self.status, percent=self.percent, message=self.message, error=self.error)

    @property
    def result(self) -> TaskResult:
        return TaskResult(pdf_bytes=None, preview_html=self.result_preview_html, filename=f"processed_{self.filename}")
