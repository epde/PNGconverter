# CR2 to PNG WebApp

Webapp semplice per caricare foto `CR2` da locale e convertirle in `PNG` automaticamente.

## Requisiti

- Python 3.10+

## Avvio locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy pubblico con GitHub + Streamlit Community Cloud

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
- Salvataggio PNG con `Pillow`.
- Download singolo file o archivio ZIP con tutti i PNG convertiti.
