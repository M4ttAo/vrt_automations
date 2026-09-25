"""Configuration for the setup downloader."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Runtime paths loaded from the local ``.env`` file."""

    base_dir: Path
    root_dir: Path
    database_dir: Path
    dry_run: bool
    supervisor_mode: bool

    @classmethod
    def load(cls) -> "Config":
        """Load configuration next to the script or compiled executable."""
        base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        load_dotenv(base / ".env")
        root = Path(os.getenv("ROOT_DIR", str(base / "SimSetups"))).expanduser()
        configured_db = os.getenv("DATABASE_DIR", "").strip()
        candidates = [Path(configured_db).expanduser()] if configured_db else []
        candidates.extend((base / "db", base.parent / "vrt_setups_uploader" / "db", Path.cwd() / "db"))
        required = ("cars.json", "tracks.json", "creators.json")
        database = next((path for path in candidates if all((path / name).is_file() for name in required)), candidates[0] if candidates else base / "db")
        return cls(
            base,
            root,
            database,
            os.getenv("DRY_RUN", "False").strip().lower() in {"1", "true", "yes", "on"},
            os.getenv("SUPERVISOR_MODE", "False").strip().lower() in {"1", "true", "yes", "on"},
        )
