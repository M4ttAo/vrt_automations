"""Interactive entry point for downloading setup files."""
from __future__ import annotations

from pathlib import Path

import orjson
from rich.console import Console
from rich.table import Table

from config import Config
from database import DatabaseStore
from search import SetupFile, SetupSearch
from utils import copy_to_current, normalize

console = Console()


def choose_numbered(title: str, options: list[Path]) -> list[Path]:
    """Select one directory by number."""
    console.print(f"\n[bold]{title}[/bold]")
    for index, option in enumerate(options, 1):
        console.print(f"{index}. {option.name}")
    while True:
        value = input("Selezione: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(options):
            return [options[int(value) - 1]]
        console.print("Selezione non valida.", style="red")


def choose_creators(options: list[Path]) -> tuple[list[Path], bool]:
    """Select one creator or all creators, preserving the all-selection state."""
    console.print("\n[bold]Creatore setup[/bold]")
    for index, option in enumerate(options, 1):
        console.print(f"{index}. {option.name}")
    console.print("Invio. Tutti")
    while True:
        value = input("Selezione: ").strip()
        if not value:
            return options, True
        if value.isdigit() and 1 <= int(value) <= len(options):
            return [options[int(value) - 1]], False
        console.print("Selezione non valida.", style="red")


def choose_track(search: SetupSearch, database: DatabaseStore, creators: list[Path]) -> dict:
    """Resolve a circuit alias against folders belonging to selected creators."""
    available = search.available_tracks(creators)
    query = input("Circuito (invio per elenco): ").strip()
    if not query:
        tracks = available
        console.print("\nCircuiti disponibili:")
        for index, name in enumerate(tracks, 1):
            console.print(f"{index}. {name}")
        while True:
            value = input("Seleziona circuito: ").strip()
            if value.isdigit() and 1 <= int(value) <= len(tracks):
                folder_name = tracks[int(value) - 1]
                record = database.find_track(folder_name) or {"name": folder_name, "aliases": [folder_name]}
                return {**record, "_folder_name": folder_name}
            console.print("Selezione non valida.", style="red")
    track = database.find_track(query)
    if track:
        track_names = [track.get("name", ""), *track.get("aliases", [])]
        folder_name = next((name for name in available if any(normalize(name) == normalize(alias) for alias in track_names)), None)
        if folder_name:
            return {**track, "_folder_name": folder_name}
    console.print(f"La folder per il circuito '{query}' non esiste.", style="yellow")
    return choose_track(search, database, creators)


def choose_series(car: dict, query: str) -> str | None:
    """Select a car series when more than one applies."""
    series = list(dict.fromkeys(str(value) for value in car.get("series", []) if str(value).strip()))
    mentioned = [value for value in series if normalize(value) in normalize(query)]
    if len(series) <= 1 or mentioned:
        selected = mentioned[0] if mentioned else (series[0] if series else None)
        return selected if selected and normalize(selected) in {"wec", "elms"} else None
    console.print("\nCampionato/versione:")
    for index, value in enumerate(series, 1):
        console.print(f"{index}. {value}")
    while True:
        choice = input("Seleziona campionato: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(series):
            selected = series[int(choice) - 1]
            return selected if normalize(selected) in {"wec", "elms"} else None
        console.print("Selezione non valida.", style="red")


def choose_files(files: list[SetupFile], all_creators: bool, search_description: str) -> list[SetupFile]:
    """Display results and parse single, comma-separated or range selection."""
    if not files:
        console.print("Nessun setup trovato per i parametri selezionati.", style="yellow")
        return []
    console.print(f"\n[bold]Ecco i setup presenti con la ricerca: {search_description}[/bold]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("N")
    if all_creators:
        table.add_column("Creator")
    table.add_column("File")
    table.add_column("Ultima modifica")
    for index, item in enumerate(files, 1):
        values = [str(index)]
        if all_creators:
            values.append(item.creator)
        values.extend([item.path.stem, item.modified.strftime("%Y-%m-%d %H:%M")])
        table.add_row(*values)
    console.print(table)
    while True:
        raw = input("File da scaricare (es. 3 oppure 3,7,10 oppure 1-5): ").strip()
        try:
            indexes = parse_selection(raw, len(files))
            return [files[index - 1] for index in indexes]
        except ValueError as error:
            console.print(str(error), style="red")


def parse_selection(value: str, maximum: int) -> list[int]:
    """Parse the documented single, list and inclusive range syntax."""
    if not value:
        raise ValueError("Seleziona almeno un file.")
    selected: set[int] = set()
    for token in value.replace(" ", "").split(","):
        if "-" in token:
            parts = token.split("-")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise ValueError("Intervallo non valido.")
            start, end = map(int, parts)
            selected.update(range(start, end + 1))
        elif token.isdigit():
            selected.add(int(token))
        else:
            raise ValueError("Selezione non valida.")
    if not selected or min(selected) < 1 or max(selected) > maximum:
        raise ValueError(f"I numeri devono essere compresi tra 1 e {maximum}.")
    return sorted(selected)


def main() -> int:
    """Run the interactive downloader."""
    config = Config.load()
    if not config.root_dir.is_dir():
        console.print(f"ROOT_DIR non trovata: {config.root_dir}", style="red")
        return 1
    try:
        database = DatabaseStore(config.database_dir)
        search = SetupSearch(config.root_dir, database)
        available_games = search.games()
        if not available_games:
            console.print(f"Nessuna cartella gioco trovata in {config.root_dir}.", style="red")
            return 1
        games = choose_numbered("Gioco", available_games)
        available_creators = search.creators(games[0])
        if not available_creators:
            console.print(f"Nessun creator trovato in {games[0]}.", style="red")
            return 1
        creators, all_creators = choose_creators(available_creators)
        track = choose_track(search, database, creators)
        query = input("Auto (invio per elenco): ").strip()
        available_cars = search.available_cars(creators, track["_folder_name"])
        cars = available_cars if not query else [car for car in database.find_cars(query) if car in available_cars]
        if not cars:
            console.print("Nessuna auto corrisponde alla ricerca.", style="yellow")
            return 1
        if query:
            console.print("\nAuto trovate:")
            for index, car in enumerate(cars, 1):
                console.print(f"{index}. {database.car_label(car)}")
            cars = [cars[choose_numbered_index(len(cars)) - 1]]
        else:
            console.print("\nElenco auto:")
            for index, car in enumerate(cars, 1):
                console.print(f"{index}. {database.car_label(car)}")
            cars = [cars[choose_numbered_index(len(cars)) - 1]]
        car = cars[0]
        series = choose_series(car, query)
        roots = search.car_roots(creators, car, series)
        files = search.files(roots, track)
        selected = choose_files(files, all_creators, f"gioco={games[0].name}, creator={'tutti' if all_creators else creators[0].name}, circuito={track['name']}, auto={database.car_label(car)}")
        if config.dry_run:
            console.print(f"DRY_RUN attivo: nessun file copiato. File selezionati: {len(selected)}", style="yellow")
            return 0
        if config.supervisor_mode:
            answer = input(f"Sto copiando {len(selected)} file nella cartella corrente. Procedo? (s/n): ").strip().lower()
            if answer not in {"s", "si", "sì", "y", "yes"}:
                console.print("Copia annullata.", style="yellow")
                return 0
        copied = copy_to_current([item.path for item in selected])
        console.print(f"Scaricati {len(copied)} file nella cartella corrente: {Path.cwd()}")
        return 0
    except (OSError, ValueError, orjson.JSONDecodeError) as error:
        console.print(f"Errore: {error}", style="red")
        return 1


def choose_numbered_index(maximum: int) -> int:
    """Read a numbered auto selection."""
    while True:
        value = input("Seleziona auto: ").strip()
        if value.isdigit() and 1 <= int(value) <= maximum:
            return int(value)
        console.print("Selezione non valida.", style="red")


if __name__ == "__main__":
    exit_code = main()
    input("Premi invio per terminare...")
    raise SystemExit(exit_code)
