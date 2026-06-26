import logging
import sys
from logging.handlers import RotatingFileHandler

from scraper.config.settings import LOG_DIR

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    """Configure console and rotating file logs for backend modules."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not any(getattr(handler, "_jav_scrapling_console", False) for handler in root.handlers):
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        console._jav_scrapling_console = True
        root.addHandler(console)


def get_app_logger(name: str) -> logging.Logger:
    """Return a backend logger with a module-scoped rotating file handler."""
    configure_logging()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    marker = f"jav_scrapling_file_{name}"
    if not any(getattr(handler, "_jav_scrapling_marker", None) == marker for handler in logger.handlers):
        file_handler = RotatingFileHandler(
            LOG_DIR / f"{name}.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        file_handler._jav_scrapling_marker = marker
        logger.addHandler(file_handler)

    return logger
