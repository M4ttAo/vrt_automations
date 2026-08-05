"""Filename normalization and RapidFuzz entity matching."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from rapidfuzz import fuzz, process

from database import DatabaseStore
from utils import normalize


@dataclass(frozen=True)
class Match:
    """A resolved entity and the evidence used to resolve it."""
    record: dict[str, Any]
    alias: str
    score: float


class Matcher:
    """Match cars, tracks and creators against the shared databases."""

    def __init__(self, store: DatabaseStore, threshold: int = 72) -> None:
        self.store, self.threshold = store, threshold

    def _aliases(self, kind: str) -> dict[str, tuple[dict[str, Any], str]]:
        return {normalize(alias): (record, alias) for record in self.store.records[kind] for alias in record["aliases"]}

    def find(self, kind: str, text: str) -> Match | None:
        """Return best fuzzy match, including original alias and score."""
        aliases = self._aliases(kind)
        if not aliases:
            return None
        normalized = normalize(text)
        contained = [(alias, 100.0, None) for alias in aliases if f" {alias} " in f" {normalized} "]
        contained.sort(key=lambda item: len(item[0]), reverse=True)
        result = contained[0] if contained else process.extractOne(normalized, list(aliases), scorer=fuzz.token_set_ratio)
        if not result or result[1] < self.threshold:
            return None
        record, alias = aliases[result[0]]
        return Match(record, alias, float(result[1]))

    def resolve(
        self,
        kind: str,
        text: str,
        prompt: Callable[[str, list[dict[str, Any]], str, str], tuple[dict[str, Any], str]],
        filename: str,
    ) -> Match:
        """Match an entity or ask the operator and learn the new token."""
        found = self.find(kind, text)
        if found:
            return found
        record, alias = prompt(kind, self.store.records[kind], filename, text)
        self.store.add_alias(kind, record, alias)
        return Match(record, alias, 100.0)
