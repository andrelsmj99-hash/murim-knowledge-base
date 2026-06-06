"""
Centralized logging configuration.

Writes to console and to a rotating file inside ``logs/`` (resolved relative
to the project root via :class:`app.utils.config.settings`).
"""
import logging
import sys
from logging.config import dictConfig

from app.utils.config import settings


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the whole application.

    Idempotent: callers may invoke this more than once safely.
    """
    log_file = settings.logs_dir / "murim.log"
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "level": level,
                "formatter": "default",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_file),
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
                "level": "DEBUG",
                "formatter": "default",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {  # root logger
                "level": level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app.scrapers": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app.processing": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }

    dictConfig(logging_config)
