from pathlib import Path
import hashlib
import tempfile

import streamlit as st

from analysis.checkpoints import available_runs, recover_input
from analysis.errors import AnalysisError


st.set_page_config(
    page_title="Głos AI",
    page_icon="icon/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mpeg",
    ".mpg",
    ".m4v",
}


def carregar_css() -> None:
    css_path = Path("interface.css")

    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def remover_arquivo_temporario(
    caminho: str | Path | None,
) -> None:
    if not caminho:
        return

    try:
        Path(caminho).unlink(missing_ok=True)
    except OSError:
        pass


carregar_css()


# Esconde a navegação lateral automática.
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }

        [data-testid="collapsedControl"] {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# Logo centralizada.
logo_left, logo_center, logo_right = st.columns(
    [1, 0.15, 1]
)

with logo_center:
    st.image(
        "icon/logo.png",
        width="stretch",
    )


st.markdown(
    """
    <h1 class="main-title center-title">
        Upload the video
    </h1>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <p class="hint center-text">
        Make sure the file format meets the requirements for a video.
    </p>
    """,
    unsafe_allow_html=True,
)


uploaded_file = st.file_uploader(
    "Drag & Drop",
    type=[
        extension.removeprefix(".")
        for extension in sorted(VIDEO_EXTENSIONS)
    ],
    help=(
        "Formatos aceitos: MP4, MOV, AVI, MKV, "
        "WEBM, MPEG, MPG e M4V."
    ),
    max_upload_size=10240,
)


transcribe_button = st.button(
    "Transcrever",
    disabled=uploaded_file is None,
    use_container_width=True,
)


if transcribe_button and uploaded_file is not None:
    temporary_path: Path | None = None

    try:
        video_name = Path(uploaded_file.name).name
        video_suffix = Path(video_name).suffix.lower()

        if video_suffix not in VIDEO_EXTENSIONS:
            raise ValueError(
                "O arquivo selecionado não possui "
                "uma extensão de vídeo permitida."
            )

        # Garante que a leitura começará no início.
        uploaded_file.seek(0)

        file_identity = hashlib.sha256()
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=video_suffix,
            prefix="glos_video_",
        ) as temporary_file:

            # Copia o vídeo em blocos de 1 MB.
            while True:
                chunk = uploaded_file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                temporary_file.write(chunk)
                file_identity.update(chunk)

            temporary_file.flush()
            temporary_path = Path(temporary_file.name)

        # Valida se o arquivo realmente foi gravado.
        if not temporary_path.exists():
            raise RuntimeError(
                "O arquivo temporário não foi criado."
            )

        if temporary_path.stat().st_size == 0:
            raise RuntimeError(
                "O arquivo temporário foi criado vazio."
            )

        # Remove o vídeo temporário de uma operação anterior.
        previous_video_path = st.session_state.get(
            "video_path"
        )

        if previous_video_path:
            previous_path = Path(previous_video_path)

            if previous_path != temporary_path:
                remover_arquivo_temporario(
                    previous_path
                )

        # Guarda apenas o caminho do arquivo temporário.
        st.session_state.video_path = str(
            temporary_path
        )

        st.session_state.video_name = video_name
        st.session_state.source_id = file_identity.hexdigest()

        # Limpa o resultado da transcrição anterior.
        for key in (
            "terminal_lines",
            "transcription",
            "transcription_filename",
            "transcription_finished",
            "transcription_error",
            "ai_analysis",
            "ai_analysis_finished",
            "ai_analysis_error",
            "processing_metrics",
        ):
            st.session_state.pop(key, None)

        st.switch_page(
            "pages/transcription.py"
        )

    except Exception as error:
        remover_arquivo_temporario(
            temporary_path
        )

        st.error(
            f"Não foi possível preparar o vídeo: {error}"
        )


# Recupera a transcrição já salva, sem nova cópia ou nova transcrição do vídeo.
# A compatibilidade das análises é verificada pelo pipeline ao abrir AI Analysis.
previous_runs = available_runs()
if previous_runs:
    with st.expander("Retomar processamento anterior"):
        run = st.selectbox(
            "Execução salva", previous_runs,
            format_func=lambda item: f"{item['filename']} — {item['updated_at']} — {item['status']}",
        )
        if st.button("Recuperar processamento", use_container_width=True):
            try:
                saved = recover_input(run["run_id"])
                for key in ("ai_analysis", "ai_analysis_finished", "ai_analysis_error", "transcription_error", "video_path"):
                    st.session_state.pop(key, None)
                st.session_state.transcription = saved["text"]
                st.session_state.video_name = saved["filename"]
                st.session_state.source_id = saved["identity"]["source"]
                st.session_state.transcription_filename = f"{Path(saved['filename']).stem}.txt"
                st.session_state.transcription_finished = True
                st.session_state.processing_metrics = saved["metrics"]
                st.session_state.terminal_lines = ["Transcrição recuperada do checkpoint local."]
                st.switch_page("pages/transcription.py")
            except AnalysisError as error:
                st.error(str(error))
