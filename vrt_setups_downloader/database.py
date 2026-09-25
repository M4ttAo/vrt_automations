"""Read-only access to the shared setup databases."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson

from utils import canonical_class, normalize


class DatabaseStore:
    """Load cars, tracks and creators from local JSON files only."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.records: dict[str, list[dict[str, Any]]] = {}
        for kind in ("cars", "tracks", "creators"):
            path = directory / f"{kind}.json"
            if not path.is_file():
                raise FileNotFoundError(f"Database non trovato: {path}")
            self.records[kind] = orjson.loads(path.read_bytes())

    def car_label(self, record: dict[str, Any]) -> str:
        """Return the display label for a car including class and series."""
        name = f"{record.get('brand', '')} {record.get('model', '')}".strip()
        classes = ", ".join(f"[{canonical_class(str(value))}]" for value in record.get("class", []))
        series = ", ".join(f"[{value}]" for value in record.get("series", []))
        return f"{name} {classes} {series}".strip()

    def find_track(self, query: str) -> dict[str, Any] | None:
        """Find a circuit whose canonical name or alias contains the query."""
        normalized = normalize(query)
        return next(
            (record for record in self.records["tracks"] if any(normalized in normalize(str(alias)) for alias in [record.get("name", ""), *record.get("aliases", [])])),
            None,
        )

    def find_cars(self, query: str) -> list[dict[str, Any]]:
        """Return all cars matching aliases, names, classes or series."""
        normalized = normalize(query)
        matches: list[tuple[int, dict[str, Any]]] = []
        for record in self.records["cars"]:
            values = [
                f"{record.get('brand', '')} {record.get('model', '')}",
                *record.get("aliases", []),
                *record.get("class", []),
                *record.get("series", []),
            ]
            score = max((100 if normalized in normalize(str(value)) else 0 for value in values), default=0)
            if score:
                matches.append((score, record))
        return [record for _, record in matches]
