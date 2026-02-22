import os
import tempfile

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

# Set up test config before any app imports
_tmpdir = tempfile.mkdtemp()

_test_config_content = f"""\
llm:
  api_key: "test-key"
  base_url: "https://api.example.com/v1"
  model: "test-model"
  judge_model: "test-model"
storage:
  cleanup_minutes: 30
  temp_dir: "{_tmpdir}"
database:
  url: "sqlite:///:memory:"
logging:
  level: "WARNING"
  file: "{_tmpdir}/test.log"
security:
  secret_key: "test-secret-key"
  cors_origins:
    - "http://localhost"
"""

from pathlib import Path

_test_config_path = Path(_tmpdir) / "config.yaml"
_test_config_path.write_text(_test_config_content)
os.environ["APP_CONFIG_PATH"] = str(_test_config_path)

from app.core.config import get_config

get_config.cache_clear()

from app.core.db import get_session
from app.main import app

# Ensure all models are registered
from app.models.knowledge import *  # noqa: F401, F403
from app.models.task import *  # noqa: F401, F403
from app.models.user import *  # noqa: F401, F403


@pytest.fixture(name="client")
def client_fixture():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    def override():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
