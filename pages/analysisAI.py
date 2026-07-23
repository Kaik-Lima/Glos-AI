from collections.abc import Generator
from pathlib import Path

import ollama
import streamlit as st


st.set_page_config(
    page_title="Summary | Głos AI",
    page_icon="icon/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


OLLAMA_MODEL = "qwen3:8b"


def carregar_css() -> None:
    """Carrega o CSS compartilhado da aplicação."""

    css_path = Path("interface.css")

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")

        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True,
        )


def criar_prompt(transcricao: str) -> str:
    """
    Monta o prompt enviado ao modelo local.

    A resposta deve ser Markdown, pois será exibida
    formatada e disponibilizada para download.
    """

    return f"""
Você é um instrutor técnico especializado no conteúdo que a transcrição abaixo abordar.

Sua tarefa é transformar a transcrição bruta abaixo em uma aula escrita
completa, didática, direta e tecnicamente organizada.

O resultado deve ter qualidade editorial semelhante a um bom artigo técnico
publicado no Medium.

REGRAS OBRIGATÓRIAS:

1. Escreva em português brasileiro.
2. Retorne somente o artigo em Markdown.
3. Crie um título principal usando "#".
4. Depois do título, escreva uma introdução curta.
5. Organize o conteúdo usando títulos "##" e subtítulos "###".
6. Use parágrafos claros e relativamente curtos.
7. Use listas somente quando realmente ajudarem na compreensão.
8. Destaque observações importantes usando citações Markdown com ">".
9. Use negrito para conceitos importantes.
10. Preserve as informações técnicas da transcrição.
11. Remova vícios de fala, repetições, interrupções e frases incompletas.
12. Corrija erros evidentes de transcrição quando o contexto permitir.
13. Não invente procedimentos, configurações ou conclusões ausentes.
14. Explique termos técnicos antes de utilizá-los de forma aprofundada.
15. Quando existir um procedimento, apresente uma sequência lógica.
16. Termine com uma seção chamada "Conclusão".
17. Não mencione que o conteúdo veio de uma transcrição.
18. Não inclua comentários sobre estas instruções.

TRANSCRIÇÃO:

{transcricao}
""".strip()


def gerar_resposta_ollama(
    prompt: str,

    # Gera a resposta progressivamente por meio do Ollama.
) -> Generator[str, None, None]:

    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você escreve artigos técnicos completos, "
                    "precisos e didáticos em Markdown."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        stream=True,
        think=False,
        options={
            "temperature": 0.3,
            "top_p": 0.9,
        },
    )

    for chunk in stream:
        message = chunk.get("message", {})
        content = message.get("content", "")

        if content:
            yield content


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

if "ai_analysis" not in st.session_state:
    accumulated_response = ""

    try:
        prompt = criar_prompt(
            st.session_state.transcription
        )

        with st.spinner(
            "Organizando a transcrição com a IA local..."
        ):
            for token in gerar_resposta_ollama(prompt):
                accumulated_response += token

                # O cursor dá a sensação de geração em andamento.
                article_placeholder.markdown(
                    accumulated_response + " ▌"
                )

        st.session_state.ai_analysis = (
            accumulated_response.strip()
        )

        st.session_state.ai_analysis_finished = True

        # Retira o cursor ao terminar.
        article_placeholder.markdown(
            st.session_state.ai_analysis
        )

    except ollama.ResponseError as error:
        st.session_state.ai_analysis_error = str(error)

        article_placeholder.error(
            "O Ollama retornou um erro: "
            f"{error}"
        )

    except ConnectionError:
        st.session_state.ai_analysis_error = (
            "Não foi possível conectar ao Ollama."
        )

        article_placeholder.error(
            "Não foi possível conectar ao Ollama. "
            "Verifique se ele está instalado e em execução."
        )

    except Exception as error:
        st.session_state.ai_analysis_error = str(error)

        article_placeholder.error(
            f"Erro durante a análise: {error}"
        )

else:
    # Reconstrói a resposta após qualquer rerun.
    article_placeholder.markdown(
        st.session_state.ai_analysis
    )


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