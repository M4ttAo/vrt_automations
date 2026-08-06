"""Safe extraction of ZIP and 7Z archives."""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import py7zr


@dataclass(frozen=True)
class ExtractionResult:
    """Extracted files and the temporary root that owns them."""

    root: Path
    cleanup_root: Path
    files: tuple[Path, ...]


class ArchiveExtractor:
    """Extract supported archives into an isolated temporary directory."""

    def extract(self, archive: Path, temp_root: Path) -> ExtractionResult:
        """Extract files and keep them available until the caller cleans up."""
        work = Path(tempfile.mkdtemp(prefix="vrt-", dir=temp_root))
        try:
            suffix = archive.suffix.lower()
            if suffix == ".zip":
                with zipfile.ZipFile(archive) as handle:
                    self._safe_zip(handle)
                    handle.extractall(work)
            elif suffix == ".7z":
                with py7zr.SevenZipFile(archive, mode="r") as handle:
                    self._safe_7z(handle)
                    handle.extractall(work)
            else:
                raise ValueError(f"Formato non supportato: {archive.suffix}")
            files = tuple(path for path in sorted(work.rglob("*")) if path.is_file())
            logical_root = self._remove_wrapper_directory(work, files)
            return ExtractionResult(logical_root, work, files)
        except Exception:
            shutil.rmtree(work, ignore_errors=True)
            raise

    @staticmethod
    def cleanup(result: ExtractionResult) -> None:
        """Remove the temporary extraction directory after installation."""
        shutil.rmtree(result.cleanup_root, ignore_errors=True)

    @staticmethod
    def _remove_wrapper_directory(work: Path, files: tuple[Path, ...]) -> Path:
        """Ignore consecutive single-folder wrappers around the actual files."""
        logical_root = work
        while files:
            children = tuple(logical_root.iterdir())
            if len(children) != 1 or not children[0].is_dir():
                break
            logical_root = children[0]
        return logical_root

    @staticmethod
    def _safe_zip(handle: zipfile.ZipFile) -> None:
        if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in handle.infolist()):
            raise ValueError("Archivio ZIP non sicuro: percorso fuori dalla directory temporanea")

    @staticmethod
    def _safe_7z(handle: py7zr.SevenZipFile) -> None:
        """Reject 7Z entries that could escape the temporary directory."""
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in handle.getnames()):
            raise ValueError("Archivio 7Z non sicuro: percorso fuori dalla directory temporanea")
