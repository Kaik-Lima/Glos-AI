import html
import logging
from pathlib import Path

import streamlit as st

from transcription import transcrever_arquivo
from observability import configure_logging

configure_logging()
logger = logging.getLogger("glos.UI")


st.set_page_config(
    page_title="Transcribing Video | Głos AI",
    page_icon="icon/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def carregar_css() -> None:
    """
    Carrega o arquivo CSS compartilhado da aplicação.
    """

    css_path = Path("interface.css")

    if css_path.exists():
        css_content = css_path.read_text(
            encoding="utf-8"
        )

        st.markdown(
            f"<style>{css_content}</style>",
            unsafe_allow_html=True,
        )


def montar_terminal(linhas: list[str]) -> str:
    """
    Monta o HTML da área de logs.

    html.escape evita que partes da transcrição sejam
    interpretadas como código HTML.
    """

    if not linhas:
        conteudo = "Preparing transcription..."
    else:
        linhas_seguras = []

        for linha in linhas:
            if linha is None:
                continue

            linhas_seguras.append(
                html.escape(str(linha))
            )

        conteudo = "<br>".join(linhas_seguras)

    return f"""
        <div class="terminal-content">
            {conteudo}
        </div>
    """


def remover_arquivo_temporario(
    caminho: str | Path | None,
) -> None:
    """
    Remove o vídeo temporário após o processamento.
    """

    if not caminho:
        return

    arquivo = Path(caminho)

    try:
        arquivo.unlink(missing_ok=True)
    except PermissionError:
        # Pode ocorrer no Windows se algum processo ainda
        # estiver finalizando o acesso ao arquivo.
        pass
    except OSError:
        pass


carregar_css()

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


# ---------------------------------------------------------
# VALIDAÇÃO DE ACESSO
# ---------------------------------------------------------

transcription_finished = st.session_state.get(
    "transcription_finished",
    False,
)

video_path_value = st.session_state.get("video_path")


# Se a transcrição já terminou, o vídeo temporário pode
# ter sido removido. Por isso, só exigimos video_path
# enquanto a transcrição ainda não foi concluída.
if not transcription_finished and not video_path_value:
    st.warning("Nenhum vídeo foi selecionado.")

    if st.button(
        "Voltar para o upload",
        use_container_width=True,
    ):
        st.switch_page("app.py")

    st.stop()


# ---------------------------------------------------------
# INTERFACE
# ---------------------------------------------------------

st.markdown(
    """
    <h1 class="transcribing-title">
        Transcribing Video
    </h1>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <p class="transcribing-subtitle">
        Please wait for the transcription to complete.
    </p>
    """,
    unsafe_allow_html=True,
)


terminal_placeholder = st.empty()
status_placeholder = st.empty()
download_placeholder = st.empty()
analysis_placeholder = st.empty()


# ---------------------------------------------------------
# VALORES INICIAIS DA SESSÃO
# ---------------------------------------------------------

if "terminal_lines" not in st.session_state:
    st.session_state.terminal_lines = []

if "transcription_finished" not in st.session_state:
    st.session_state.transcription_finished = False


# ---------------------------------------------------------
# TRANSCRIÇÃO
# ---------------------------------------------------------

if not st.session_state.transcription_finished:
    terminal_lines: list[str] = []
    transcription_parts: list[str] = []

    video_name = st.session_state.get(
        "video_name",
        "video.mp4",
    )

    video_path = Path(
        st.session_state.video_path
    )

    try:
        if not video_path.exists():
            raise FileNotFoundError(
                "O arquivo temporário do vídeo não foi encontrado."
            )

        terminal_lines.append(
            f"Arquivo recebido: {video_name}"
        )

        terminal_lines.append(
            f"Tamanho: "
            f"{video_path.stat().st_size / (1024 * 1024):.2f} MB"
        )

        terminal_lines.append(
            "Iniciando transcrição..."
        )

        terminal_placeholder.markdown(
            montar_terminal(terminal_lines),
            unsafe_allow_html=True,
        )

        metrics = {}
        transcription_generator = transcrever_arquivo(
            video_path, metrics=metrics, display_name=video_name
        )

        if transcription_generator is None:
            raise RuntimeError(
                "A função transcrever_arquivo retornou None. "
                "Ela precisa usar yield para retornar os segmentos."
            )

        for result in transcription_generator:
            if result is None:
                continue

            if not isinstance(result, tuple):
                raise TypeError(
                    "A função transcrever_arquivo deve retornar "
                    "uma tupla: (linha_terminal, texto)."
                )

            if len(result) != 2:
                raise ValueError(
                    "A função transcrever_arquivo retornou uma "
                    "tupla com quantidade incorreta de valores."
                )

            linha_terminal, texto = result

            if linha_terminal:
                terminal_lines.append(
                    str(linha_terminal)
                )

            if texto:
                transcription_parts.append(
                    str(texto).strip()
                )

            terminal_placeholder.markdown(
                montar_terminal(terminal_lines),
                unsafe_allow_html=True,
            )

        transcription = " ".join(
            transcription_parts
        ).strip()

        if not transcription:
            raise RuntimeError(
                "A transcrição foi processada, mas nenhum "
                "texto foi identificado no arquivo."
            )

        terminal_lines.append(
            "Transcrição finalizada com sucesso."
        )

        st.session_state.terminal_lines = (
            terminal_lines
        )

        st.session_state.transcription = (
            transcription
        )

        st.session_state.transcription_filename = (
            f"{Path(video_name).stem}.txt"
        )

        st.session_state.transcription_finished = True
        st.session_state.processing_metrics = metrics

        terminal_placeholder.markdown(
            montar_terminal(terminal_lines),
            unsafe_allow_html=True,
        )

    except Exception as error:
        logger.exception("Falha na página de transcrição | Tipo=%s", type(error).__name__)
        error_message = (
            f"Erro durante a transcrição: {error}"
        )

        terminal_lines.append(error_message)

        st.session_state.terminal_lines = (
            terminal_lines
        )

        st.session_state.transcription_finished = False
        st.session_state.transcription_error = str(error)

        terminal_placeholder.markdown(
            montar_terminal(terminal_lines),
            unsafe_allow_html=True,
        )

        status_placeholder.error(
            "Não foi possível concluir a transcrição."
        )

        # O arquivo também é removido em caso de erro.
        remover_arquivo_temporario(video_path)

        st.session_state.pop("video_path", None)

        st.stop()

    else:
        # Executado somente quando não ocorre erro.
        remover_arquivo_temporario(video_path)

        # O caminho não é mais necessário depois da transcrição.
        st.session_state.pop("video_path", None)


# ---------------------------------------------------------
# RECONSTRUÇÃO DA INTERFACE APÓS RERUN
# ---------------------------------------------------------

terminal_placeholder.markdown(
    montar_terminal(
        st.session_state.get(
            "terminal_lines",
            [],
        )
    ),
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# CONCLUSÃO E DOWNLOAD
# ---------------------------------------------------------

if st.session_state.get(
    "transcription_finished",
    False,
):
    status_placeholder.markdown(
        """
        <p class="completion-text">
            Transcription complete.
        </p>
        """,
        unsafe_allow_html=True,
    )

    with download_placeholder.container():
        st.download_button(
            label="Download transcription",
            data=st.session_state.transcription.encode(
                "utf-8"
            ),
            file_name=st.session_state.transcription_filename,
            mime="text/plain; charset=utf-8",
            use_container_width=True,
        )

    with analysis_placeholder.container():
        if st.button(
            "AI Analysis",
            key="open_result",
            use_container_width=True,
        ):
            st.switch_page("pages/analysisAI.py")
