import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import get_config


def setup_logging() -> None:
    config = get_config()
    log_file = Path(config.logging.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO))

    root_logger = logging.getLogger()
    root_logger.handlers = [file_handler, console_handler]

    # Filter out /api/tasks polling logs from uvicorn access logger
    class EndpointFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.getMessage().find("GET /api/tasks") == -1

    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
