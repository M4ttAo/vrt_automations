"""Installation orchestration for extracted setup files."""
from __future__ import annotations

import shutil
import os
import re
from pathlib import Path
from typing import Iterable

from utils import slug


class Installer:
    """Copy setup files into the canonical simulator hierarchy."""

    def install(self, files: Iterable[Path], destination: Path, dry_run: bool = False, extraction_root: Path | None = None) -> int:
        """Copy files preserving paths relative to the extraction root."""
        file_list = list(files)
        if not file_list:
            return 0
        # Extraction paths share a temporary root; derive it without depending
        # on a particular archive library implementation.
        common = extraction_root or Path(os.path.commonpath([str(path) for path in file_list]))
        if extraction_root is None and common.is_file():
            common = common.parent
        count = 0
        for source in file_list:
            relative = source.relative_to(common)
            target = destination / relative
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            count += 1
        return count

    @staticmethod
    def destination(root: Path, game: str, creator: str, car: dict, track: dict) -> Path:
        """Build the destination path using user-facing canonical names."""
        car_name = f"{car.get('brand', '')} {car.get('model', '')}".strip()
        track_name = re.sub(r"\s*\[[^]]+\]\s*$", "", str(track.get("name", "Unknown"))).strip()
        destination = root / slug(game) / slug(creator) / slug(car_name)
        series = {str(value).strip().upper() for value in car.get("series", [])}
        if series & {"WEC", "ELMS"}:
            destination /= slug(next(value for value in car["series"] if str(value).strip().upper() in {"WEC", "ELMS"}))
        return destination / slug(track_name)
