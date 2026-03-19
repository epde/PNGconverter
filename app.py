import io
import zipfile
from pathlib import Path

import rawpy
import streamlit as st
from PIL import Image


st.set_page_config(page_title="CR2 to PNG Converter", page_icon="🖼️", layout="centered")

st.title("CR2 to PNG Converter")
st.write(
    "Carica uno o piu file .CR2, conversione automatica in PNG e download singolo o ZIP."
)

uploaded_files = st.file_uploader(
    "Seleziona file CR2",
    type=["cr2", "CR2"],
    accept_multiple_files=True,
)

if uploaded_files:
    converted = []
    for uploaded in uploaded_files:
        try:
            raw_bytes = uploaded.read()
            with rawpy.imread(io.BytesIO(raw_bytes)) as raw:
                rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False)

            image = Image.fromarray(rgb)
            out_buffer = io.BytesIO()
            image.save(out_buffer, format="PNG", optimize=True)
            out_buffer.seek(0)

            base_name = Path(uploaded.name).stem
            png_name = f"{base_name}.png"
            converted.append((png_name, out_buffer.getvalue()))

            st.success(f"Convertito: {uploaded.name} -> {png_name}")
            st.download_button(
                label=f"Scarica {png_name}",
                data=out_buffer.getvalue(),
                file_name=png_name,
                mime="image/png",
                key=f"dl_{uploaded.name}",
            )
        except Exception as exc:
            st.error(f"Errore su {uploaded.name}: {exc}")

    if converted:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, data in converted:
                zf.writestr(name, data)
        zip_buffer.seek(0)

        st.download_button(
            label="Scarica tutto in ZIP",
            data=zip_buffer.getvalue(),
            file_name="converted_png.zip",
            mime="application/zip",
            key="dl_zip",
        )
else:
    st.info("Attendi il caricamento dei file CR2 per iniziare la conversione.")
