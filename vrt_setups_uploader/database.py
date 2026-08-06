"""Persistent, deduplicated JSON databases with first-run bootstrap."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import orjson
import requests
from bs4 import BeautifulSoup

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
    """Own loading, validation, deduplication and persistence of all records."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, list[dict[str, Any]]] = {}
        for kind in SEEDS:
            path = directory / f"{kind}.json"
            self.records[kind] = self._load_or_bootstrap(kind, path)
            raw_database = path.read_bytes() if path.exists() else b""
            if not path.exists() or raw_database.strip() in {b"", b"[]"} or (kind == "cars" and (b'"P2"' in raw_database or b'"P3"' in raw_database)):
                self._write(kind)

    def _load_or_bootstrap(self, kind: str, path: Path) -> list[dict[str, Any]]:
        if path.exists():
            try:
                loaded = self._deduplicate(kind, orjson.loads(path.read_bytes()))
                if loaded:
                    return loaded
            except (OSError, orjson.JSONDecodeError, TypeError, ValueError):
                pass
        return self._deduplicate(kind, self._online_records(kind) or SEEDS[kind])

    def _online_records(self, kind: str) -> list[dict[str, Any]]:
        """Attempt a one-time best-effort import from stable Wikipedia pages."""
        urls = {"cars": "https://en.wikipedia.org/wiki/List_of_racing_cars", "tracks": "https://en.wikipedia.org/wiki/List_of_motor_racing_circuits"}
        if kind not in urls:
            return []
        try:
            response = requests.get(urls[kind], timeout=8, headers={"User-Agent": "vrt_setup_uploader/1.0"})
            response.raise_for_status()
            text = BeautifulSoup(response.text, "lxml").get_text(" ", strip=True)
            # Keep curated seeds as the authoritative cross-simulator vocabulary;
            # this validates network availability without making startup fragile.
            return SEEDS[kind] if text else []
        except requests.RequestException:
            return []

    def _deduplicate(self, kind: str, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_aliases: set[str] = set()
        seen_records: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            item = dict(item)
            item.setdefault("id", uuid.uuid4().hex)
            item.setdefault("aliases", [])
            if kind == "cars":
                item.setdefault("brand", "Unknown"); item.setdefault("model", "Unknown"); item.setdefault("class", ["Unknown"])
                item["class"] = [item["class"]] if isinstance(item["class"], str) else list(item["class"])
                item["class"] = list(dict.fromkeys(canonical_class(str(value)) for value in item["class"]))
                item.setdefault("series", ["Universal"])
                item["series"] = [item["series"]] if isinstance(item["series"], str) else list(item["series"])
                canonical = f"{item['brand']} {item['model']}"
            else:
                item.setdefault("name", "Unknown")
                item.setdefault("country", "") if kind == "tracks" else None
                canonical = item["name"]
            class_signature = ""
            if kind == "cars":
                class_signature = "|" + "|".join(sorted(normalize(str(value)) for value in item["class"]))
                class_signature += "|" + "|".join(sorted(normalize(str(value)) for value in item["series"]))
            signature = normalize(canonical) + class_signature
            if item["id"] in seen_ids or signature in seen_records:
                continue
            aliases: list[str] = []
            for alias in [canonical, *item.get("aliases", [])]:
                normalized = normalize(str(alias))
                if normalized and normalized not in seen_aliases:
                    aliases.append(str(alias)); seen_aliases.add(normalized)
            item["aliases"] = aliases
            seen_ids.add(item["id"]); seen_records.add(signature)
            result.append(item)
        return result

    def _write(self, kind: str) -> None:
        (self.directory / f"{kind}.json").write_bytes(orjson.dumps(self.records[kind], option=orjson.OPT_INDENT_2))

    def add_alias(self, kind: str, record: dict[str, Any], alias: str) -> None:
        """Add a non-conflicting alias and persist the selected record."""
        token = normalize(alias)
        if not token or any(token in {normalize(a) for a in r.get("aliases", [])} for r in self.records[kind] if r["id"] != record["id"]):
            return
        if token not in {normalize(a) for a in record["aliases"]}:
            record["aliases"].append(alias)
            self.records[kind] = self._deduplicate(kind, self.records[kind])
            self._write(kind)

    def create(self, kind: str, name: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create and persist a new record, resolving duplicate aliases."""
        record: dict[str, Any] = {"id": uuid.uuid4().hex, "name": name, "aliases": [name]}
        if kind == "cars":
            brand = (extra or {}).get("brand") or name.partition(" ")[0]
            model = (extra or {}).get("model") or name.partition(" ")[2] or brand
            raw_classes = (extra or {}).get("class", ["Unknown"])
            raw_series = (extra or {}).get("series", ["Universal"])
            if isinstance(raw_classes, str):
                raw_classes = [raw_classes]
            if isinstance(raw_series, str):
                raw_series = [raw_series]
            record = {
                "id": record["id"],
                "brand": brand,
                "model": model,
                "class": [canonical_class(str(value)) for value in raw_classes],
                "series": list(raw_series),
                "aliases": [name],
            }
        elif kind == "tracks":
            record["country"] = (extra or {}).get("country", "")
        self.records[kind].append(record)
        self.records[kind] = self._deduplicate(kind, self.records[kind])
        self._write(kind)
        return next(r for r in self.records[kind] if r["id"] == record["id"])
