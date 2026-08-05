#!/usr/bin/env python3
"""Copy setup files from a ZIP archive into a Google Drive folder."""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


PLATFORMS = {"1": "LMU", "2": "ACC", "3": "ACC EVO"}


def load_env(path: Path) -> dict[str, str]:
    """Load the small KEY=VALUE configuration used by this script."""
    values: dict[str, str] = {}
    if not path.is_file():
        raise FileNotFoundError(f"Configurazione non trovata: {path}")

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Riga non valida in {path}:{line_number}")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def choose_platform() -> str:
    print("\nPiattaforma di destinazione:")
    print("  1. LMU")
    print("  2. ACC")
    print("  3. ACC EVO")
    while True:
        choice = input("Seleziona la piattaforma: ").strip()
        if choice in PLATFORMS:
            return PLATFORMS[choice]
        print("Scelta non valida.")


def find_circuit(archive: Path, configured_names: str) -> str:
    names = [name.strip() for name in configured_names.split(",") if name.strip()]
    matches = [name for name in names if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", archive.stem, re.I)]
    if not matches:
        raise ValueError(
            f"Impossibile ricavare il circuito dal nome '{archive.name}'. "
            "Aggiungilo a CIRCUIT_NAMES nel file .env."
        )
    return max(matches, key=len)


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Reject archive entries that could escape the temporary directory."""
    members = []
    for member in archive.infolist():
        target = Path(member.filename)
        if target.is_absolute() or ".." in target.parts:
            raise ValueError(f"Percorso non sicuro nello ZIP: {member.filename}")
        members.append(member)
    return members


def copy_archive(archive: Path, destination: Path) -> int:
    copied = 0
    with tempfile.TemporaryDirectory(prefix="vrt-uploader-") as temp_dir:
        extraction_dir = Path(temp_dir)
        with zipfile.ZipFile(archive) as zip_file:
            members = safe_members(zip_file)
            zip_file.extractall(extraction_dir, members)

        for source in sorted(path for path in extraction_dir.rglob("*") if path.is_file()):
            relative_path = source.relative_to(extraction_dir)
            target = destination / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
            print(f"  Copiato: {relative_path}")
    return copied


def main() -> int:
    try:
        config = load_env(Path(__file__).with_name(".env"))
        source_dir = Path(config["ZIP_SOURCE_DIR"]).expanduser()
        drive_root = Path(config["DRIVE_ROOT_DIR"]).expanduser()
        if not source_dir.is_dir():
            raise NotADirectoryError(f"Cartella ZIP non trovata: {source_dir}")
        if not drive_root.is_dir():
            raise NotADirectoryError(f"Cartella Google Drive non trovata: {drive_root}")

        archives = sorted(source_dir.glob("*.zip"))
        if not archives:
            raise FileNotFoundError(f"Nessun file ZIP trovato in {source_dir}")

        platform = choose_platform()
        print(f"\nTrovati {len(archives)} ZIP. Piattaforma: {platform}")

        total_copied = 0
        skipped = 0
        for archive in archives:
            try:
                circuit = find_circuit(archive, config.get("CIRCUIT_NAMES", ""))
                destination = drive_root / platform / circuit
                print(f"\nElaboro: {archive.name}")
                print(f"Destinazione: {destination}")
                destination.mkdir(parents=True, exist_ok=True)
                total_copied += copy_archive(archive, destination)
            except (OSError, ValueError, zipfile.BadZipFile) as error:
                skipped += 1
                print(f"Saltato: {archive.name}: {error}", file=sys.stderr)

        print(f"\nCompletato: {total_copied} file copiati, {skipped} ZIP saltati")
        return 0
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Errore: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
