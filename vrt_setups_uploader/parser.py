"""Heuristics for extracting setup entities from archive names."""
from __future__ import annotations

import re
from pathlib import Path

from database import DatabaseStore
from matcher import Match, Matcher
from utils import canonical_class, normalize


class FilenameParser:
    """Resolve creator, car, track and optional car class from a filename."""

    def __init__(self, matcher: Matcher, store: DatabaseStore, prompt) -> None:
        self.matcher, self.store, self.prompt = matcher, store, prompt

    def parse(self, archive: Path) -> tuple[Match, Match, Match, str]:
        """Parse the filename and interactively resolve unknown entities/classes."""
        stem = normalize(archive.stem)
        creator = self.matcher.resolve("creators", stem, self.prompt, archive.name)
        car = self.matcher.resolve("cars", stem, self.prompt, archive.name)
        track = self.matcher.resolve("tracks", stem, self.prompt, archive.name)
        same_car = [
            record
            for record in self.store.records["cars"]
            if normalize(f"{record.get('brand', '')} {record.get('model', '')}")
            == normalize(f"{car.record.get('brand', '')} {car.record.get('model', '')}")
        ]
        series_names = sorted({series for record in same_car for series in record.get("series", [])})
        mentioned_series = [series for series in series_names if re.search(rf"\b{re.escape(normalize(series))}\b", stem)]
        if len(series_names) > 1 and not mentioned_series:
            selected = self.prompt("series", [{"name": series} for series in series_names], archive.name, stem)
            selected_record = next(record for record in same_car if selected["name"] in record.get("series", []))
            car = Match(selected_record, car.alias, 100.0)
        elif mentioned_series:
            selected_record = next((record for record in same_car if mentioned_series[0] in record.get("series", [])), car.record)
            car = Match(selected_record, car.alias, car.score)
        categories = car.record.get("class", ["Unknown"])
        mentioned = [
            c for c in categories
            if any(re.search(rf"\b{re.escape(normalize(alias))}\b", stem) for alias in (c, {"LMP2": "P2", "LMP3": "P3"}.get(c, c)))
        ]
        if len(categories) > 1 and not mentioned:
            selected = self.prompt("class", [{"name": c} for c in categories], archive.name, stem)
            category = canonical_class(selected["name"])
        else:
            category = canonical_class(mentioned[0] if mentioned else categories[0])
        return creator, car, track, category
