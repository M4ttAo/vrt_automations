"""Access to shared setup databases with first-run bootstrap."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson

from utils import canonical_class, normalize


SEEDS: dict[str, list[dict[str, Any]]] = {
    "cars": [
        {"brand": "Ferrari", "model": "296 GT3", "class": ["GT3"], "aliases": ["f296", "ferrari296", "296gt3"]},
        {"brand": "Ferrari", "model": "488 GT3 Evo", "class": ["GT3"], "aliases": ["488gt3", "488gt3evo"]},
        {"brand": "BMW", "model": "M4 GT3", "class": ["GT3"], "aliases": ["bmwm4gt3", "m4gt3"]},
        {"brand": "Porsche", "model": "911 GT3 R (992)", "class": ["GT3"], "aliases": ["992", "992gt3r", "porsche992"]},
        {"brand": "Lamborghini", "model": "Huracan GT3 Evo2", "class": ["GT3"], "aliases": ["huracan", "lamborghinigt3"]},
        {"brand": "McLaren", "model": "720S GT3", "class": ["GT3"], "aliases": ["720s", "mclaren720"]},
        {"brand": "Oreca", "model": "07", "class": ["LMP2", "P2"], "series": ["WEC"], "aliases": ["oreca07wec", "oreca 07 wec", "oreca wec lmp2"]},
        {"brand": "Oreca", "model": "07", "class": ["LMP2", "P2"], "series": ["ELMS"], "aliases": ["oreca07elms", "oreca 07 elms", "oreca 07 lmp2 elms", "oreca elms p2"]},
    ],
    "tracks": [
        {"name": "Daytona", "country": "United States", "aliases": ["daytona", "daytona road", "day"]},
        {"name": "Monza", "country": "Italy", "aliases": ["monza"]},
        {"name": "Spa-Francorchamps", "country": "Belgium", "aliases": ["spa", "spa francorchamps"]},
        {"name": "Nurburgring", "country": "Germany", "aliases": ["nurburgring", "nordschleife"]},
        {"name": "Imola", "country": "Italy", "aliases": ["imola"]},
        {"name": "Silverstone", "country": "United Kingdom", "aliases": ["silverstone"]},
        {"name": "Le Mans", "country": "France", "aliases": ["lemans", "le mans"]},
    ],
    "creators": [
        {"name": "GO", "aliases": ["go"]},
        {"name": "HYMO", "aliases": ["hymo"]},
        {"name": "SIMSETUPS", "aliases": ["simsetups"]},
    ],
}


class DatabaseStore:
    """Load local JSON databases and bootstrap missing files with seed data."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, list[dict[str, Any]]] = {}
        for kind in SEEDS:
            path = directory / f"{kind}.json"
            if path.is_file():
                self.records[kind] = orjson.loads(path.read_bytes())
            else:
                self.records[kind] = SEEDS[kind]
                path.write_bytes(orjson.dumps(self.records[kind], option=orjson.OPT_INDENT_2))

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
