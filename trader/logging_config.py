"""
Centralised logging configuration for the NSE trader.

Call setup_logging() exactly once at the top of each entry point
(daily_run.py, main.py).  Subsequent calls from the same process
are no-ops because the root logger keeps its handlers.

Outputs:
  - StreamHandler → stdout  (always on — visible in docker logs / ECS CloudWatch)
  - RotatingFileHandler → LOG_FILE (when non-empty — readable from the host via bind mount)

Log rotation: 10 MB per file, 5 backups → max ~60 MB on disk.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

_ALREADY_CONFIGURED = False

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(
    level: str | None = None,
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB per file
    backup_count: int = 5,              # keep 5 rotated files → max ~60 MB
) -> None:
    """
    Configure the root logger.  Safe to call multiple times — only the
    first call has any effect.

    Args:
        level:        Log level string ("DEBUG", "INFO", …).
                      Defaults to the LOG_LEVEL env var, then "INFO".
        log_file:     Path to the rotating log file.
                      Defaults to the LOG_FILE env var, then "logs/trader.log".
                      Pass "" to disable file logging entirely.
        max_bytes:    Size threshold before rotating (default 10 MB).
        backup_count: Number of rotated files to keep (default 5).
    """
    global _ALREADY_CONFIGURED
    if _ALREADY_CONFIGURED:
        return
    _ALREADY_CONFIGURED = True

    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")
    if log_file is None:
        log_file = os.environ.get("LOG_FILE", "logs/trader.log")

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # ── 1. Console (stdout) ────────────────────────────────────────────────────
    # Only add if there isn't already a plain StreamHandler (avoids duplicates
    # when uvicorn / gunicorn add their own).
    has_stream = any(
        type(h) is logging.StreamHandler for h in root.handlers
    )
    if not has_stream:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        root.addHandler(ch)

    # ── 2. Rotating file ───────────────────────────────────────────────────────
    if log_file:
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            fh.setFormatter(formatter)
            root.addHandler(fh)
            logging.getLogger(__name__).info(
                "File logging enabled → %s (max %d MB × %d backups)",
                log_path.resolve(),
                max_bytes // (1024 * 1024),
                backup_count,
            )
        except OSError as e:
            # Non-fatal: log to console only if the file can't be opened
            logging.getLogger(__name__).warning(
                "Could not open log file %s: %s — logging to console only.", log_file, e
            )

    # Quiet noisy third-party loggers
    for noisy in ("urllib3", "botocore", "boto3", "httpx", "httpcore", "yfinance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
