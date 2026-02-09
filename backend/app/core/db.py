from typing import Generator

from sqlmodel import Session, create_engine, SQLModel

from .config import get_config

config = get_config()

connect_args = {"check_same_thread": False} if "sqlite" in config.database.url else {}
engine = create_engine(config.database.url, echo=False, connect_args=connect_args)


def init_db():
    # Import models to register them with SQLModel metadata
    from ..models.user import User
    from ..models.task import Task
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
