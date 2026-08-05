"""Safe extraction of ZIP, RAR and 7Z archives."""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterator

import py7zr
import rarfile


class ArchiveExtractor:
    """Extract supported archives into an isolated temporary directory."""

    def extract(self, archive: Path, temp_root: Path) -> Iterator[Path]:
        """Yield extracted files and remove the temporary directory afterwards."""
        work = Path(tempfile.mkdtemp(prefix="vrt-", dir=temp_root))
        try:
            suffix = archive.suffix.lower()
            if suffix == ".zip":
                with zipfile.ZipFile(archive) as handle:
                    self._safe_zip(handle)
                    handle.extractall(work)
            elif suffix == ".7z":
                with py7zr.SevenZipFile(archive, mode="r") as handle:
                    handle.extractall(work)
            elif suffix == ".rar":
                with rarfile.RarFile(archive) as handle:
                    self._safe_rar(handle)
                    handle.extractall(work)
            else:
                raise ValueError(f"Formato non supportato: {archive.suffix}")
            yield from (path for path in sorted(work.rglob("*")) if path.is_file())
        finally:
            shutil.rmtree(work, ignore_errors=True)

    @staticmethod
    def _safe_zip(handle: zipfile.ZipFile) -> None:
        if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in handle.infolist()):
            raise ValueError("Archivio ZIP non sicuro: percorso fuori dalla directory temporanea")

    @staticmethod
    def _safe_rar(handle: rarfile.RarFile) -> None:
        if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in handle.infolist()):
            raise ValueError("Archivio RAR non sicuro: percorso fuori dalla directory temporanea")
