"""Application configuration loaded from ``.env``."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Immutable settings used by the application."""

    base_dir: Path
    destination_root: Path
    archive_dir: Path
    temp_dir: Path
    logs_dir: Path
    dry_run: bool
    supervisor_mode: bool
    match_threshold: int

    @classmethod
    def load(cls) -> "Config":
        """Read ``.env`` next to the executable or source file."""
        base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        load_dotenv(base / ".env")
        destination = Path(os.getenv("DESTINATION_ROOT", str(base / "destination"))).expanduser()
        return cls(
            base_dir=base,
            destination_root=destination,
            archive_dir=base / "archive",
            temp_dir=base / "temp",
            logs_dir=base / "logs",
            dry_run=os.getenv("DRY_RUN", "False").strip().lower() in {"1", "true", "yes", "on"},
            supervisor_mode=os.getenv("SUPERVISOR_MODE", "False").strip().lower() in {"1", "true", "yes", "on"},
            match_threshold=int(os.getenv("MATCH_THRESHOLD", "72")),
        )
