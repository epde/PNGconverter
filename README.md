# CR2 to PNG WebApp

Webapp per convertire foto `CR2` in `PNG` con controllo su qualita e peso finale.

## Funzionalita

- Selezione multipla file CR2 tramite upload web.
- Modalita locale con percorso sorgente e percorso destinazione su disco.
- Preset qualita output: `Low`, `Medium`, `High`, `Maximum`.
- Preservazione PPI originale del CR2 (con fallback configurabile).
- Limite opzionale sul peso massimo per PNG (in MB).
- Report finale con confronto peso input/output.
- Gestione batch robusta: limite file per batch, paginazione report e output temporaneo su disco.

## Requisiti

- Python 3.10+

## Avvio locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Uso rapido

1. Scegli la qualita output (`Low`, `Medium`, `High`, `Maximum`).
2. Lascia attivo `Mantieni PPI originale del CR2` per non cambiare la densita dell'immagine.
2. Opzionale: imposta `Peso massimo per PNG (MB)`.
3. Scegli la modalita:
   - `Upload web`: carica file CR2 e scarica PNG/ZIP.
   - `Percorsi locali`: imposta cartella sorgente CR2 e cartella output PNG, poi converti su disco.

Nota: la modalita con percorsi locali funziona solo quando l'app gira sul tuo PC.
Su un deploy pubblico cloud non puo accedere ai percorsi locali del tuo computer.

## Deploy pubblico always-on (consigliato)

Per evitare che l'app vada in sleep durante la notte, usa un hosting container always-on.

### Opzione A: Render (consigliata)

1. Crea account su Render e collega GitHub.
2. Clicca `New` -> `Blueprint`.
3. Seleziona il repository `epde/PNGconverter`.
4. Render usera automaticamente `render.yaml` e `Dockerfile`.
5. Scegli piano `Starter` (always-on).

### Opzione B: Railway

1. Crea account su Railway e collega GitHub.
2. `New Project` -> `Deploy from GitHub repo`.
3. Seleziona `epde/PNGconverter`.
4. Railway usera il `Dockerfile` e pubblichera un URL condivisibile.

Nota: per garantire disponibilita continua serve un piano senza sleep automatico.

## Deploy Streamlit Community Cloud (con sleep)

1. Crea un repository pubblico su GitHub (es. `pngconverter`).
2. Esegui i comandi git nella root del progetto:

```bash
git init
git add .
git commit -m "Initial CR2 to PNG webapp"
git branch -M main
git remote add origin https://github.com/<tuo-username>/pngconverter.git
git push -u origin main
```

3. Vai su Streamlit Community Cloud e collega il repository GitHub pubblico.
4. Imposta:
   - Branch: `main`
   - Main file path: `app.py`
5. Pubblica l'app e condividi l'URL pubblico generato.

## Note tecniche

- Conversione RAW con `rawpy`.
- PPI letto dai metadati CR2 con `exifread` e scritto nel PNG.
- Ottimizzazione PNG con `Pillow` (`optimize` + `compress_level`).
- Preset `High`/`Maximum` pensati per minima perdita visiva.
- Riduzione peso (se richiesta) tramite resize progressivo e quantizzazione solo nei preset piu compressi.
- Download singolo file o archivio ZIP in modalita upload.
- In modalita upload i PNG vengono salvati in una cartella temporanea server-side per ridurre il consumo RAM su batch grandi.
