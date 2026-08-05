# vrt_setup_uploader

Organizza automaticamente gli archivi di setup per LMU, ACC, Assetto Corsa EVO

## Installazione

1. Installare Python 3.13 (Windows) e, per i file RAR, WinRAR/UnRAR/7-Zip nel PATH oppure mettere `UnRAR.exe` accanto all'EXE.
2. Creare l'ambiente: `py -3.13 -m venv .venv`.
3. Attivarlo: `.venv\Scripts\activate`.
4. Installare: `python -m pip install -r requirements.txt`.
5. Copiare `.env.example` in `.env` e impostare `DESTINATION_ROOT`.

Al primo avvio, se `db/*.json` non esistono, il programma tenta una richiesta

## Utilizzo

Mettere `*.zip`, `*.rar` o `*.7z` nella stessa cartella di `main.py` (o dell'EXE),
avviare `python main.py` e selezionare il simulatore. Per ogni archivio il nome
viene analizzato; gli elementi sconosciuti vengono richiesti a video. La voce
`Nuovo record` e sempre selezionabile tramite numero e richiede tutti i campi:
produttore/modello/classi/campionato per un'auto, nome/nazione per un circuito,
nome per un creatore, oltre all'alias preciso. In esecuzione normale i file sono estratti in una
cartella temporanea, copiati in:

`DESTINATION_ROOT/<Game>/<Creator>/<Car>/<Track>`

Infine l'archivio viene spostato in `archive/`. Log e errori sono in `logs/`.

Se l'archivio contiene una sola cartella contenitore con un nome arbitrario,
questa viene rimossa dal percorso di destinazione; le sottocartelle reali dei
setup vengono invece mantenute.

Impostando `DRY_RUN=True` vengono mostrati solo gli abbinamenti e le destinazioni:
non vengono estratti, copiati o spostati file.

## Compilazione

Eseguire `build.bat`. Il risultato e `dist\vrt_setup_uploader.exe`. Per distribuire
l'EXE insieme ai database gia inizializzati, includere `db` accanto all'EXE;
`archive`, `temp` e `logs` vengono creati automaticamente.

## Struttura

- `main.py`: orchestrazione del batch e menu.
- `config.py`: configurazione `.env`.
- `database.py`: bootstrap, deduplicazione e apprendimento.
- `parser.py`, `matcher.py`: parsing e RapidFuzz.
- `extractor.py`: estrazione sicura ZIP/RAR/7Z.
- `installer.py`: copia e gerarchia di destinazione.
- `logger.py`, `utils.py`: logging e utility.
- `db/cars.json`, `db/tracks.json`, `db/creators.json`: database condivisi.

## Matching

Il nome viene convertito in minuscolo, privato degli accenti, separato su `_`,
`-`, `.`, parentesi e spazi multipli. RapidFuzz confronta il testo normalizzato
con tutti gli alias globali usando `token_set_ratio`; ogni risultato conserva
record, alias scelto e punteggio. Sotto `MATCH_THRESHOLD` viene chiesto
all'operatore. Gli alias vengono normalizzati prima di essere aggiunti e i
database rimuovono automaticamente ID, record e alias duplicati.

Se un'auto ha più categorie e il nome non contiene una categoria, il programma
chiede sempre di scegliere tra GT3, GT4, CUP o le categorie registrate.
