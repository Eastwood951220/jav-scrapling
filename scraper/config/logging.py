import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from scraper.config.settings import LOG_DIR

LOG_DIR = Path(LOG_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMATTER = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Rotating file handler — prevents unbounded log growth
        file_handler = RotatingFileHandler(
            LOG_DIR / f"{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(LOG_FORMATTER)
        logger.addHandler(file_handler)

        # Console handler — visible in docker compose logs
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(LOG_FORMATTER)
        logger.addHandler(console_handler)

    return logger
