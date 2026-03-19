import io
import zipfile
from pathlib import Path

import rawpy
import streamlit as st
from PIL import Image


QUALITY_PRESETS = {
    "Low": {
        "max_side": 2200,
        "colors": 192,
        "description": "File piu leggeri, con perdita visiva moderata.",
    },
    "Medium": {
        "max_side": 3600,
        "colors": None,
        "description": "Compromesso consigliato tra peso e dettaglio.",
    },
    "High": {
        "max_side": None,
        "colors": None,
        "description": "Alta qualita, senza resize forzato.",
    },
    "Maximum": {
        "max_side": None,
        "colors": None,
        "description": "Qualita massima, impatto minimo sull'immagine.",
    },
}


def apply_preset(image: Image.Image, preset_name: str) -> Image.Image:
    cfg = QUALITY_PRESETS[preset_name]
    result = image.copy()

    max_side = cfg["max_side"]
    if max_side and max(result.size) > max_side:
        result.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    colors = cfg["colors"]
    if colors:
        result = result.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)

    return result


def _tag_to_float(tag_value: object) -> float | None:
    if tag_value is None:
        return None
    if isinstance(tag_value, (int, float)):
        return float(tag_value)

    numerator = getattr(tag_value, "num", None)
    denominator = getattr(tag_value, "den", None)
    if numerator is not None and denominator:
        return float(numerator) / float(denominator)

    try:
        return float(str(tag_value))
    except (TypeError, ValueError):
        return None


def extract_source_dpi(raw_bytes: bytes, fallback_dpi: int) -> tuple[int, int]:
    try:
        import exifread
    except ImportError:
        return (fallback_dpi, fallback_dpi)

    stream = io.BytesIO(raw_bytes)
    tags = exifread.process_file(stream, details=False)

    x_tag = tags.get("Image XResolution") or tags.get("EXIF XResolution")
    y_tag = tags.get("Image YResolution") or tags.get("EXIF YResolution")

    x_value = _tag_to_float(getattr(x_tag, "values", [None])[0] if x_tag else None)
    y_value = _tag_to_float(getattr(y_tag, "values", [None])[0] if y_tag else None)

    x_dpi = int(round(x_value)) if x_value else fallback_dpi
    y_dpi = int(round(y_value)) if y_value else fallback_dpi
    return (max(x_dpi, 1), max(y_dpi, 1))


def encode_png(image: Image.Image, dpi: tuple[int, int], compress_level: int = 9) -> bytes:
    if image.mode in {"P", "L", "LA", "RGB", "RGBA"}:
        prepared = image
    else:
        prepared = image.convert("RGB")

    out_buffer = io.BytesIO()
    prepared.save(
        out_buffer,
        format="PNG",
        optimize=True,
        compress_level=compress_level,
        dpi=dpi,
    )
    return out_buffer.getvalue()


def enforce_max_size(
    png_image: Image.Image,
    preset_name: str,
    max_bytes: int | None,
    dpi: tuple[int, int],
) -> bytes:
    current = png_image.copy()
    encoded = encode_png(current, dpi=dpi)
    if not max_bytes or len(encoded) <= max_bytes:
        return encoded

    for _ in range(10):
        width, height = current.size
        if width <= 1000 or height <= 1000:
            break

        scale = 0.95 if preset_name in {"High", "Maximum"} else 0.9
        current = current.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

        if preset_name in {"Low", "Medium"} and current.mode != "P":
            colors = 192 if preset_name == "Low" else 256
            current = current.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)

        encoded = encode_png(current, dpi=dpi, compress_level=9)
        if len(encoded) <= max_bytes:
            return encoded

    return encoded


def raw_bytes_to_png(
    raw_bytes: bytes,
    preset_name: str,
    max_size_mb: float,
    keep_source_ppi: bool,
    fallback_ppi: int,
) -> tuple[bytes, tuple[int, int]]:
    dpi = extract_source_dpi(raw_bytes, fallback_ppi) if keep_source_ppi else (fallback_ppi, fallback_ppi)

    with rawpy.imread(io.BytesIO(raw_bytes)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=True,
            output_bps=8,
            output_color=rawpy.ColorSpace.sRGB,
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
        )

    image = Image.fromarray(rgb)
    processed = apply_preset(image, preset_name)
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb > 0 else None
    png_data = enforce_max_size(processed, preset_name, max_bytes, dpi=dpi)
    return png_data, dpi


def format_kb(size_bytes: int) -> str:
    return f"{size_bytes / 1024:.0f} KB"


st.set_page_config(page_title="CR2 to PNG Converter", page_icon="🖼️", layout="centered")

if "upload_results" not in st.session_state:
    st.session_state.upload_results = []

if "upload_errors" not in st.session_state:
    st.session_state.upload_errors = []

st.title("CR2 to PNG Converter")
st.write("Conversione CR2 -> PNG con modalita web o cartella locale.")

quality = st.select_slider(
    "Qualita output",
    options=["Low", "Medium", "High", "Maximum"],
    value="High",
)
st.caption(QUALITY_PRESETS[quality]["description"])

keep_source_ppi = st.checkbox(
    "Mantieni PPI originale del CR2",
    value=True,
    help="Se disponibile nei metadati del RAW, il valore PPI viene mantenuto nel PNG.",
)

with st.expander("Impostazioni avanzate output", expanded=False):
    fallback_ppi = st.number_input(
        "PPI di fallback",
        min_value=72,
        max_value=1200,
        value=300,
        step=1,
        help="Usato quando il CR2 non contiene il PPI o se disattivi il mantenimento originale.",
    )

    max_size_mb = st.number_input(
        "Peso massimo per PNG (MB, opzionale)",
        min_value=0.0,
        max_value=500.0,
        value=0.0,
        step=1.0,
        help="0 = nessun limite. Se impostato, la conversione prova a stare sotto il valore.",
    )

mode = st.radio(
    "Modalita",
    options=["Upload web", "Percorsi locali (solo esecuzione locale)"],
    horizontal=True,
)

if mode == "Upload web":
    uploaded_files = st.file_uploader(
        "Seleziona uno o piu file CR2",
        type=["cr2", "CR2"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.info("Dopo aver selezionato i file, premi Converti file caricati.")

        if st.button("Converti file caricati", type="primary"):
            st.session_state.upload_results = []
            st.session_state.upload_errors = []

            for uploaded in uploaded_files:
                try:
                    raw_data = uploaded.read()
                    png_data, dpi = raw_bytes_to_png(
                        raw_data,
                        quality,
                        max_size_mb,
                        keep_source_ppi,
                        int(fallback_ppi),
                    )

                    base_name = Path(uploaded.name).stem
                    png_name = f"{base_name}.png"
                    st.session_state.upload_results.append(
                        {
                            "source_name": uploaded.name,
                            "png_name": png_name,
                            "raw_size": len(raw_data),
                            "png_size": len(png_data),
                            "dpi": dpi,
                            "png_data": png_data,
                        }
                    )
                except Exception as exc:
                    st.session_state.upload_errors.append(f"Errore su {uploaded.name}: {exc}")

    else:
        st.info("Carica almeno un file CR2 per iniziare.")

    if st.session_state.upload_errors:
        for err in st.session_state.upload_errors:
            st.error(err)

    if st.session_state.upload_results:
        report_rows = [
            {
                "File": item["source_name"],
                "Input": format_kb(item["raw_size"]),
                "Output": format_kb(item["png_size"]),
                "PPI": f"{item['dpi'][0]}x{item['dpi'][1]}",
            }
            for item in st.session_state.upload_results
        ]

        st.subheader("Report conversione")
        st.dataframe(report_rows, use_container_width=True, hide_index=True)

        for idx, item in enumerate(st.session_state.upload_results):
            st.download_button(
                label=f"Scarica {item['png_name']}",
                data=item["png_data"],
                file_name=item["png_name"],
                mime="image/png",
                key=f"dl_upload_{idx}_{item['png_name']}",
            )

        show_zip_download = st.checkbox(
            "Mostra anche download ZIP",
            value=False,
            help="Lascia disattivato se vuoi scaricare solo file singoli.",
        )

        if show_zip_download:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for item in st.session_state.upload_results:
                    zf.writestr(item["png_name"], item["png_data"])
            zip_buffer.seek(0)

            st.download_button(
                label="Scarica tutto in ZIP",
                data=zip_buffer.getvalue(),
                file_name="converted_png.zip",
                mime="application/zip",
                key="dl_zip",
            )

else:
    st.warning(
        "La selezione tramite percorso locale funziona solo quando l'app gira sul tuo PC, "
        "non su un deploy pubblico cloud."
    )

    input_dir = st.text_input("Cartella sorgente CR2", value="")
    output_dir = st.text_input("Cartella destinazione PNG", value="")
    recursive_search = st.checkbox("Includi sottocartelle", value=False)

    available_files = []
    input_path = Path(input_dir) if input_dir else None
    if input_path and input_path.exists() and input_path.is_dir():
        if recursive_search:
            files_upper = list(input_path.rglob("*.CR2"))
            files_lower = list(input_path.rglob("*.cr2"))
        else:
            files_upper = list(input_path.glob("*.CR2"))
            files_lower = list(input_path.glob("*.cr2"))

        available_files = sorted(files_upper + files_lower, key=lambda p: p.name.lower())

    if input_dir and not available_files:
        st.info("Nessun file CR2 trovato nella cartella indicata.")

    selected_names = st.multiselect(
        "File da convertire",
        options=[p.name for p in available_files],
        default=[p.name for p in available_files],
    )

    if st.button("Converti e salva su disco", type="primary"):
        if not input_dir or not output_dir:
            st.error("Specifica sia cartella sorgente sia cartella destinazione.")
        elif not selected_names:
            st.error("Seleziona almeno un file CR2 da convertire.")
        else:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            selected_paths = [p for p in available_files if p.name in selected_names]
            report_rows = []

            for source_path in selected_paths:
                try:
                    raw_data = source_path.read_bytes()
                    png_data, dpi = raw_bytes_to_png(
                        raw_data,
                        quality,
                        max_size_mb,
                        keep_source_ppi,
                        int(fallback_ppi),
                    )

                    destination = output_path / f"{source_path.stem}.png"
                    destination.write_bytes(png_data)

                    report_rows.append(
                        {
                            "File": source_path.name,
                            "Input": format_kb(source_path.stat().st_size),
                            "Output": format_kb(destination.stat().st_size),
                            "PPI": f"{dpi[0]}x{dpi[1]}",
                            "Destinazione": str(destination),
                        }
                    )
                except Exception as exc:
                    st.error(f"Errore su {source_path.name}: {exc}")

            if report_rows:
                st.success(f"Conversione completata. File salvati in: {output_path}")
                st.dataframe(report_rows, use_container_width=True, hide_index=True)
