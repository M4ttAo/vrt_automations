"""Safe extraction of ZIP, RAR and 7Z archives."""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import py7zr
import rarfile


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
                    handle.extractall(work)
            elif suffix == ".rar":
                self._configure_rar_tool()
                with rarfile.RarFile(archive) as handle:
                    self._safe_rar(handle)
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
        """Ignore a single arbitrary top-level folder used as an archive wrapper."""
        top_level = tuple(work.iterdir())
        if len(top_level) == 1 and top_level[0].is_dir() and files:
            return top_level[0]
        return work

    @staticmethod
    def _configure_rar_tool() -> None:
        """Select a RAR command-line backend available on the host."""
        if rarfile.UNRAR_TOOL and (Path(rarfile.UNRAR_TOOL).exists() or shutil.which(rarfile.UNRAR_TOOL)):
            return
        executable_names = ("unrar", "UnRAR.exe", "unar", "bsdtar", "7z", "7z.exe")
        application_dir = Path(sys.executable).resolve().parent
        for executable in executable_names:
            local_tool = application_dir / executable
            resolved = shutil.which(executable) or (str(local_tool) if local_tool.is_file() else None)
            if resolved:
                rarfile.UNRAR_TOOL = resolved
                return
        raise RuntimeError("Per estrarre RAR installare UnRAR, WinRAR o 7-Zip e aggiungerlo al PATH")

    @staticmethod
    def _safe_zip(handle: zipfile.ZipFile) -> None:
        if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in handle.infolist()):
            raise ValueError("Archivio ZIP non sicuro: percorso fuori dalla directory temporanea")

    @staticmethod
    def _safe_rar(handle: rarfile.RarFile) -> None:
        if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in handle.infolist()):
            raise ValueError("Archivio RAR non sicuro: percorso fuori dalla directory temporanea")
