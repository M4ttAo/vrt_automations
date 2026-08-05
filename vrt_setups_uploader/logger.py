"""Structured application logging."""
from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_dir: Path) -> logging.Logger:
    """Configure console and rotating daily-style file logging."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("vrt_setup_uploader")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_dir / "vrt_setup_uploader.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console)
    return logger
