"""Shared normalization and filesystem helpers for the downloader."""
from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path


def normalize(value: str) -> str:
    """Normalize accents, separators and whitespace for comparisons."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[_\-.(),]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def canonical_class(value: str) -> str:
    """Normalize equivalent P2/P3 class names."""
    return {"p2": "LMP2", "p3": "LMP3", "lmp2": "LMP2", "lmp3": "LMP3"}.get(normalize(value), value.strip())


def find_child(parent: Path, name: str) -> Path | None:
    """Find a direct child directory case-insensitively."""
    target = normalize(name)
    return next((child for child in parent.iterdir() if child.is_dir() and normalize(child.name) == target), None) if parent.is_dir() else None


def unique_path(path: Path) -> Path:
    """Avoid overwriting a downloaded file."""
    if not path.exists():
        return path
    for index in range(1, 10000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError(f"Impossibile creare un nome unico per {path}")


def copy_to_current(files: list[Path]) -> list[Path]:
    """Copy selected files to the current working directory."""
    copied: list[Path] = []
    for source in files:
        target = unique_path(Path.cwd() / source.name)
        shutil.copy2(source, target)
        copied.append(target)
    return copied
