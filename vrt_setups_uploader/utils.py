"""Small, dependency-light utility functions."""
from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path


def normalize(value: str) -> str:
    """Normalize punctuation, accents and whitespace for matching."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    ascii_value = re.sub(r"[_\-.(),]+", " ", ascii_value.lower())
    return re.sub(r"\s+", " ", ascii_value).strip()


def slug(value: str) -> str:
    """Return a safe, readable Windows directory name."""
    value = re.sub(r'[<>:"/\\|?*]', "", value).strip().rstrip(".")
    return value or "Unknown"


def unique_path(path: Path) -> Path:
    """Return a non-existing path by adding a numeric suffix if needed."""
    if not path.exists():
        return path
    for index in range(1, 10000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError(f"Impossibile creare un nome univoco per {path}")


def move_to_archive(source: Path, archive_dir: Path) -> Path:
    """Move an archive into the archive directory without overwriting files."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(archive_dir / source.name)
    shutil.move(str(source), str(target))
    return target
