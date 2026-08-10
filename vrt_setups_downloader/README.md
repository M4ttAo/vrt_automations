# vrt_setups_downloader

Downloader interattivo dei setup organizzati da `vrt_setups_uploader`.

## Struttura attesa

La root viene configurata con `ROOT_DIR` nel file `.env`:

```text
ROOT_DIR/
  LMU/
    GO/
      BMW M4 GT3/
        Bahrain/
      Oreca 07/
        WEC/
          Bahrain/
```

I giochi e i creator vengono letti esclusivamente dalle cartelle presenti sul
filesystem. Il database locale fornisce i nomi canonici e gli alias per circuiti
progetto `vrt_setups_uploader/db` oppure nel `db/` della directory corrente.

## Utilizzo

1. Copiare `.env.example` in `.env` e impostare `ROOT_DIR`.
2. Avviare `python main.py` oppure `dist\vrt_setups_downloader.exe`.
3. Selezionare gioco e creator.
4. Premere Invio sui creator per selezionarli tutti.
5. Inserire un alias circuito, oppure Invio per tutti i circuiti.
6. Inserire un alias auto, oppure Invio per l'elenco completo.
7. Se necessario selezionare WEC/ELMS.
8. Selezionare i file con `3`, `3,7,10` oppure `1-5`.

I file selezionati vengono copiati nella directory corrente da cui è stato
avviato lo script o l'EXE. I nomi duplicati ricevono un suffisso numerico e non
vengono sovrascritti.

## Compilazione

Eseguire `build.bat`. Il risultato è `dist\vrt_setups_downloader.exe`.

Il database non viene incorporato nell'EXE. Distribuire il database accanto
all'EXE o configurare `DATABASE_DIR` nel `.env`.
