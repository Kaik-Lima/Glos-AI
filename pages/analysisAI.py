import logging
from pathlib import Path
from time import perf_counter

import streamlit as st

from analysis.config import load_config
from analysis.pipeline import analyze
from analysis.ollama_client import AnalysisError
from analysis.progress import progress_message, progress_value
from observability import configure_logging, format_time
from processing_feedback import processing_events


st.set_page_config(
    page_title="Summary | Głos AI",
    page_icon="icon/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


configure_logging()
logger = logging.getLogger("glos.UI")


def carregar_css() -> None:
    """Carrega o CSS compartilhado da aplicação."""

    css_path = Path("interface.css")

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")

        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True,
        )


def limpar_sessao() -> None:
    """
    Limpa os dados do fluxo atual antes de retornar ao início.
    """

    keys_to_remove = (
        "video_path",
        "video_name",
        "terminal_lines",
        "transcription",
        "transcription_filename",
        "transcription_finished",
        "transcription_error",
        "ai_analysis",
        "ai_analysis_finished",
        "ai_analysis_error",
        "processing_metrics",
        "source_id",
    )

    for key in keys_to_remove:
        st.session_state.pop(key, None)


carregar_css()


# ---------------------------------------------------------
# VALIDAÇÃO
# ---------------------------------------------------------

if "transcription" not in st.session_state:
    st.warning(
        "Nenhuma transcrição está disponível para análise."
    )

    if st.button(
        "Voltar para o início",
        use_container_width=True,
    ):
        limpar_sessao()
        st.switch_page("app.py")

    st.stop()


# ---------------------------------------------------------
# CABEÇALHO
# ---------------------------------------------------------

st.markdown(
    """
    <h1 class="summary-title">
        Summary
    </h1>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <p class="summary-subtitle">
        Some notes on the video
    </p>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# CAIXA DA RESPOSTA
# ---------------------------------------------------------

article_container = st.container(
    key="ai_article_container",
    border=True,
    height=450,
)

with article_container:
    article_placeholder = st.empty()


# ---------------------------------------------------------
# GERAÇÃO DA ANÁLISE
# ---------------------------------------------------------

def executar_analise() -> None:
    started = perf_counter()
    metrics = dict(st.session_state.get("processing_metrics", {}))
    metrics.setdefault("filename", st.session_state.get("video_name", "não informado"))
    progress_bar = st.progress(0.02, text="Preparando análise...")
    elapsed_placeholder = st.empty()
    last_second = -1
    last_render = 0.0
    draft = ""
    result = None
    st.session_state.ai_analysis_finished = False
    st.session_state.pop("ai_analysis_error", None)

    try:
        config = load_config()
        text = st.session_state.transcription
        source_id = st.session_state.get("source_id")
        # Copia entradas da sessão antes de iniciar o worker. Somente este
        # escopo, na thread Streamlit, atualiza elementos e session_state.
        def operation(progress, on_token):
            return analyze(text, config=config, progress=progress,
                           on_token=on_token, metrics=metrics, source_id=source_id)

        with st.spinner("Processamento local em andamento..."):
            for kind, value in processing_events(operation):
                now = perf_counter()
                second = int(now - started)
                if second != last_second:
                    elapsed_placeholder.caption(f"Tempo decorrido: {format_time(second)}")
                    last_second = second
                if kind == "progress":
                    stage, current, total = value
                    # 100% é publicado junto do resultado validado abaixo.
                    if stage != "complete":
                        progress_bar.progress(progress_value(stage, current, total),
                                              text=progress_message(stage, current, total))
                elif kind == "token":
                    draft += value
                    if now - last_render >= 0.1:
                        article_placeholder.markdown(draft + " ▌")
                        last_render = now
                elif kind == "result":
                    result = value

        st.session_state.ai_analysis = result
        st.session_state.ai_analysis_finished = True
        st.session_state.processing_metrics = metrics
        article_placeholder.markdown(result)
        progress_bar.progress(1.0, text="Documento concluído.")
        elapsed_placeholder.caption(
            f"Processamento da análise concluído em {format_time(metrics['analysis_seconds'])}"
        )
    except Exception as error:
        if not isinstance(error, AnalysisError):
            logger.exception("Falha ao concluir a análise | Tipo=%s", type(error).__name__)
        st.session_state.ai_analysis_error = str(error)
        st.session_state.pop("ai_analysis", None)
        st.session_state.processing_metrics = metrics
        progress_bar.empty()
        # Substitui qualquer rascunho transmitido. Não salva nem libera download.
        article_placeholder.error(f"Não foi possível concluir a análise: {error}")
        if st.button("Tentar novamente", use_container_width=True):
            st.rerun()


if "ai_analysis" not in st.session_state:
    executar_analise()
else:
    article_placeholder.markdown(st.session_state.ai_analysis)
    st.progress(1.0, text="Documento concluído.")
    elapsed = st.session_state.get("processing_metrics", {}).get("analysis_seconds", 0)
    st.caption(f"Processamento da análise concluído em {format_time(elapsed)}")


# ---------------------------------------------------------
# DOWNLOAD E NAVEGAÇÃO
# ---------------------------------------------------------

if st.session_state.get(
    "ai_analysis_finished",
    False,
):
    st.markdown(
        """
        <p class="summary-actions-title">
            Download Markdown
        </p>
        """,
        unsafe_allow_html=True,
    )

    download_column, home_column = st.columns(2)

    with download_column:
        video_name = st.session_state.get(
            "video_name",
            "transcricao",
        )

        markdown_filename = (
            f"{Path(video_name).stem}_article.md"
        )

        st.download_button(
            label="Download Markdown",
            data=st.session_state.ai_analysis.encode(
                "utf-8"
            ),
            file_name=markdown_filename,
            mime="text/markdown; charset=utf-8",
            use_container_width=True,
        )

    with home_column:
        if st.button(
            "INÍCIO",
            key="return_home",
            use_container_width=True,
        ):
            limpar_sessao()
            st.switch_page("app.py")
