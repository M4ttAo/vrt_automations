"""Filesystem search and selectable result models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from database import DatabaseStore
from utils import find_child, normalize


@dataclass(frozen=True)
class SetupFile:
    """One setup file available for download."""

    path: Path
    creator: str
    modified: datetime


class SetupSearch:
    """Resolve user selections into setup files under the configured root."""

    def __init__(self, root: Path, database: DatabaseStore) -> None:
        self.root, self.database = root, database

    def games(self) -> list[Path]:
        """Return all game directories under the configured root."""
        return sorted((path for path in self.root.iterdir() if path.is_dir()), key=lambda path: path.name.lower()) if self.root.is_dir() else []

    def creators(self, game: Path) -> list[Path]:
        """Return all creator directories for a game."""
        return sorted((path for path in game.iterdir() if path.is_dir()), key=lambda path: path.name.lower())

    def car_roots(self, creators: list[Path], car: dict, series: str | None) -> list[tuple[Path, str]]:
        """Find matching car directories for selected creators and series."""
        car_name = f"{car.get('brand', '')} {car.get('model', '')}".strip()
        found: list[tuple[Path, str]] = []
        for creator in creators:
            car_dir = find_child(creator, car_name)
            if not car_dir:
                continue
            if series:
                series_dir = find_child(car_dir, series)
                if series_dir:
                    found.append((series_dir, creator.name))
            else:
                found.append((car_dir, creator.name))
        return found

    def files(self, roots: list[tuple[Path, str]], track: dict | None) -> list[SetupFile]:
        """Collect files under selected roots, optionally filtering by track."""
        results: list[SetupFile] = []
        track_name = normalize(track.get("name", "")) if track else None
        for root, creator in roots:
            track_dirs = [child for child in root.iterdir() if child.is_dir() and (not track_name or normalize(child.name) == track_name)]
            for track_dir in track_dirs:
                for path in sorted(child for child in track_dir.rglob("*") if child.is_file()):
                    results.append(SetupFile(path, creator, datetime.fromtimestamp(path.stat().st_mtime)))
        return results
