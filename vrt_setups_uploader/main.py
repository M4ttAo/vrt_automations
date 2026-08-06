"""Command-line entry point for vrt_setup_uploader."""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from rich.console import Console

from config import Config
from database import DatabaseStore
from extractor import ArchiveExtractor
from installer import Installer
from logger import configure_logging
from matcher import Matcher
from parser import FilenameParser
from utils import move_to_archive

GAMES = {"1": "LMU", "2": "ACC", "3": "ACC EVO", "4": "iRacing"}
ARCHIVE_SUFFIXES = {".zip", ".rar", ".7z"}
console = Console()


def ask_game() -> str:
    """Ask which simulator receives the current batch."""
    console.print("\n[bold]Simulatore:[/bold] 1. Le Mans Ultimate  2. Assetto Corsa Competizione  3. Assetto Corsa EVO  4. iRacing")
    while True:
        choice = input("Scelta: ").strip()
        if choice in GAMES:
            return GAMES[choice]
        console.print("Scelta non valida.", style="red")


def ask_confirmation(archive: Path, destination: Path) -> bool:
    """Ask the supervisor to approve one archive installation."""
    console.print(f"Sto copiando [yellow]{archive.name}[/yellow] in [cyan]{destination}[/cyan]. Procedo? (s/n)")
    while True:
        answer = input("s/n: ").strip().lower()
        if answer in {"s", "si", "sì", "y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        console.print("Rispondi s oppure n.", style="red")


def ask_entity(kind: str, records: list[dict], filename: str, detected_text: str) -> tuple[dict, str] | dict:
    """Display candidates and create a record when requested."""
    labels = {"cars": "Auto", "tracks": "Circuito", "creators": "Creatore", "class": "Categoria", "series": "Campionato/versione"}
    console.print(f"\nFile in esame: [yellow]{filename}[/yellow]")
    print(f"\n{labels.get(kind, kind)} non riconosciuto.")
    for index, record in enumerate(records, 1):
        label = f"{record.get('brand', '')} {record.get('model', record.get('name', ''))}".strip()
        print(f"{index}. {label}")
    if kind in {"class", "series"}:
        while True:
            value = input("Seleziona voce: ").strip()
            if value.isdigit() and 1 <= int(value) <= len(records):
                return records[int(value) - 1]
    new_option = len(records) + 1
    print(f"{new_option}. Nuovo record")
    while True:
        value = input("Seleziona il numero dell'opzione: ").strip()
        if value.isdigit() and 1 <= int(value) <= new_option:
            break
        console.print("Seleziona una delle opzioni numeriche mostrate.", style="red")
    if int(value) <= len(records):
        record = records[int(value) - 1]
        return record, ask_alias(filename, detected_text)
    if kind == "cars":
        brand = ask_required("Produttore: ")
        model = ask_required("Modello: ")
        category = input("Categoria (GT3, GT4, CUP; separale con virgola se necessario): ").strip()
        series = input("Campionato/versione (WEC, ELMS, Universal; separali con virgola se necessario): ").strip()
        record = store_global.create(
            kind,
            f"{brand} {model}",
            {
                "brand": brand,
                "model": model,
                "class": [x.strip() for x in category.split(",") if x.strip()] or ["Unknown"],
                "series": [x.strip() for x in series.split(",") if x.strip()] or ["Universal"],
            },
        )
    elif kind == "tracks":
        name = ask_required("Nome circuito: ")
        country = ask_required("Nazione: ")
        record = store_global.create(kind, name, {"country": country})
    else:
        name = ask_required("Nome creatore: ")
        record = store_global.create(kind, name)
    return record, ask_alias(filename, detected_text)


store_global: DatabaseStore


def ask_required(label: str) -> str:
    """Read a mandatory database field without accepting an empty value."""
    while True:
        value = input(label).strip()
        if value:
            return value
        console.print("Il campo e obbligatorio.", style="red")


def ask_alias(filename: str, detected_text: str) -> str:
    """Ask for the exact filename fragment to persist as an alias."""
    while True:
        alias = input(
            f"Alias presente in '{filename}' (solo la porzione utile, es. 'bahrain'): "
        ).strip()
        if alias:
            return alias
        console.print("L'alias non puo essere vuoto e non deve contenere tutto il filename.", style="red")


def main() -> int:
    """Run the complete batch with per-archive fault isolation."""
    global store_global
    config = Config.load()
    logger = configure_logging(config.logs_dir)
    config.temp_dir.mkdir(parents=True, exist_ok=True)
    store_global = DatabaseStore(config.base_dir / "db")
    game = ask_game()
    archives = sorted(path for path in config.base_dir.iterdir() if path.suffix.lower() in ARCHIVE_SUFFIXES and path.is_file())
    console.print(f"[bold]Trovati {len(archives)} archivi[/bold] in {config.base_dir}.")
    if not archives:
        return 0
    parser = FilenameParser(Matcher(store_global, config.match_threshold), store_global, ask_entity)
    extractor, installer = ArchiveExtractor(), Installer()
    for archive in archives:
        started = time.perf_counter()
        try:
            creator, car, track, category = parser.parse(archive)
            destination = installer.destination(config.destination_root, game, creator.record["name"], car.record, track.record)
            if config.dry_run:
                console.print(f"[cyan]{archive.name}[/cyan] -> {destination} [{category}] (creator score {creator.score:.0f}, car {car.score:.0f}, track {track.score:.0f})")
            elif config.supervisor_mode and not ask_confirmation(archive, destination):
                logger.warning("Archivio rifiutato dall'operatore: %s", archive.name)
                continue
            if not config.dry_run:
                extracted = extractor.extract(archive, config.temp_dir)
                try:
                    count = installer.install(extracted.files, destination, extraction_root=extracted.root)
                finally:
                    extractor.cleanup(extracted)
                moved = move_to_archive(archive, config.archive_dir)
                logger.info("archivio=%s auto=%s pista=%s creatore=%s destinazione=%s file=%d archive=%s tempo=%.2fs", archive.name, car.record, track.record, creator.record, destination, count, moved, time.perf_counter() - started)
            else:
                logger.info("DRY-RUN archivio=%s destinazione=%s tempo=%.2fs", archive.name, destination, time.perf_counter() - started)
        except Exception as error:  # isolate one bad download from the batch
            logger.exception("Errore archivio=%s: %s", archive.name, error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
