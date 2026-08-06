"""Safe extraction of ZIP, RAR and 7Z archives."""
from __future__ import annotations

import shutil
import subprocess
import sys
import os
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
                rar_tool = self._configure_rar_tool()
                tool_name = Path(rar_tool).name.lower()
                if tool_name in {"7z", "7z.exe", "7za", "7za.exe", "7zr", "7zr.exe"}:
                    self._extract_rar_with_7zip(rar_tool, archive, work)
                else:
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
        """Ignore consecutive single-folder wrappers around the actual files."""
        logical_root = work
        while files:
            children = tuple(logical_root.iterdir())
            if len(children) != 1 or not children[0].is_dir():
                break
            logical_root = children[0]
        return logical_root

    @staticmethod
    def _configure_rar_tool() -> str:
        """Select a RAR command-line backend available on the host."""
        if rarfile.UNRAR_TOOL and (Path(rarfile.UNRAR_TOOL).exists() or shutil.which(rarfile.UNRAR_TOOL)):
            return rarfile.UNRAR_TOOL
        executable_names = ("unrar", "UnRAR.exe", "unar", "bsdtar", "7z", "7z.exe", "7za", "7za.exe")
        application_dirs: list[Path] = []
        for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            value = os.environ.get(variable)
            if value:
                application_dirs.append(Path(value) / "7-Zip")
        application_dirs.append(Path(sys.executable).resolve().parent)
        bundled_dir = getattr(sys, "_MEIPASS", None)
        if bundled_dir:
            application_dirs.append(Path(bundled_dir))
        for executable in executable_names:
            resolved = shutil.which(executable)
            if resolved:
                rarfile.UNRAR_TOOL = resolved
                return resolved
            for application_dir in application_dirs:
                local_tool = application_dir / executable
                if local_tool.is_file():
                    rarfile.UNRAR_TOOL = str(local_tool)
                    return str(local_tool)
        raise RuntimeError("Per estrarre RAR installare UnRAR, WinRAR o 7-Zip e aggiungerlo al PATH")

    @staticmethod
    def _extract_rar_with_7zip(tool: str, archive: Path, destination: Path) -> None:
        """Extract RAR through 7-Zip, which does not require rarfile's UnRAR API."""
        result = subprocess.run(
            [tool, "x", "-y", str(archive), f"-o{destination}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            details = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"7-Zip non ha estratto il RAR: {details}")

    @staticmethod
    def _safe_zip(handle: zipfile.ZipFile) -> None:
        if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in handle.infolist()):
            raise ValueError("Archivio ZIP non sicuro: percorso fuori dalla directory temporanea")

    @staticmethod
    def _safe_rar(handle: rarfile.RarFile) -> None:
        if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in handle.infolist()):
            raise ValueError("Archivio RAR non sicuro: percorso fuori dalla directory temporanea")
