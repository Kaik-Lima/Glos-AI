from datetime import datetime
from pathlib import Path

import markdown
import streamlit as st


st.set_page_config(
    page_title="Article | Głos AI",
    page_icon="icon/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


ARTICLE_CSS = """
<style>
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none;
    }

    .stApp {
        background: #fafafa;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    #MainMenu,
    footer {
        visibility: hidden;
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 820px;
        padding-top: 64px;
        padding-bottom: 100px;
    }

    .article-header {
        margin-bottom: 42px;
    }

    .article-brand {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 54px;
        padding-bottom: 18px;
        border-bottom: 1px solid #e7e7e7;
    }

    .article-brand-name {
        color: #202124;
        font-family: Arial, sans-serif;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.3px;
    }

    .article-category {
        color: #6b6b6b;
        font-family: Arial, sans-serif;
        font-size: 14px;
    }

    .article-title {
        margin: 0 0 18px;
        color: #242424;
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(42px, 6vw, 62px);
        font-weight: 700;
        line-height: 1.05;
        letter-spacing: -1.8px;
    }

    .article-subtitle {
        max-width: 720px;
        margin: 0 0 30px;
        color: #6b6b6b;
        font-family: Arial, sans-serif;
        font-size: 22px;
        line-height: 1.45;
    }

    .article-meta {
        display: flex;
        align-items: center;
        gap: 12px;
        color: #6b6b6b;
        font-family: Arial, sans-serif;
        font-size: 14px;
    }

    .article-meta-separator {
        color: #b0b0b0;
    }

    .article-divider {
        margin: 34px 0 46px;
        border: 0;
        border-top: 1px solid #e7e7e7;
    }

    .article-content {
        color: #242424;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 21px;
        font-weight: 400;
        line-height: 1.75;
    }

    .article-content h1 {
        display: none;
    }

    .article-content h2 {
        margin: 58px 0 20px;
        color: #242424;
        font-family: Arial, sans-serif;
        font-size: 30px;
        font-weight: 750;
        line-height: 1.2;
        letter-spacing: -0.7px;
    }

    .article-content h3 {
        margin: 42px 0 16px;
        color: #242424;
        font-family: Arial, sans-serif;
        font-size: 24px;
        font-weight: 700;
        line-height: 1.3;
    }

    .article-content p {
        margin: 0 0 30px;
    }

    .article-content strong {
        font-weight: 700;
    }

    .article-content em {
        color: #3f3f3f;
    }

    .article-content a {
        color: inherit;
        text-decoration-thickness: 1px;
        text-underline-offset: 3px;
    }

    .article-content ul,
    .article-content ol {
        margin: 6px 0 32px;
        padding-left: 34px;
    }

    .article-content li {
        margin-bottom: 12px;
        padding-left: 4px;
    }

    .article-content blockquote {
        margin: 42px 0;
        padding: 3px 0 3px 28px;
        border-left: 3px solid #242424;
        color: #454545;
        font-size: 25px;
        font-style: italic;
        line-height: 1.55;
    }

    .article-content blockquote p {
        margin: 0;
    }

    .article-content code {
        padding: 2px 6px;
        border-radius: 4px;
        background: #eeeeee;
        font-family: Consolas, monospace;
        font-size: 0.84em;
    }

    .article-content pre {
        margin: 36px 0;
        padding: 24px;
        overflow-x: auto;
        border-radius: 8px;
        background: #1f1f1f;
        color: #eeeeee;
    }

    .article-content pre code {
        padding: 0;
        background: transparent;
        color: inherit;
        font-size: 15px;
    }

    .article-actions {
        margin-top: 70px;
        padding-top: 30px;
        border-top: 1px solid #e7e7e7;
    }

    .stDownloadButton > button,
    .stButton > button {
        min-height: 46px;
        border: 1px solid #242424;
        border-radius: 24px;
        background: #242424;
        color: white;
        font-family: Arial, sans-serif;
        font-size: 15px;
    }

    .stDownloadButton > button:hover,
    .stButton > button:hover {
        border-color: #000000;
        background: #000000;
        color: white;
    }

    @media (max-width: 720px) {
        [data-testid="stMainBlockContainer"] {
            padding: 34px 22px 70px;
        }

        .article-brand {
            margin-bottom: 38px;
        }

        .article-title {
            font-size: 42px;
        }

        .article-subtitle {
            font-size: 19px;
        }

        .article-content {
            font-size: 19px;
            line-height: 1.7;
        }

        .article-content h2 {
            font-size: 27px;
        }
    }

    @media print {
        header,
        .article-actions,
        [data-testid="stToolbar"] {
            display: none !important;
        }

        .stApp {
            background: white;
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 760px;
            padding-top: 0;
        }
    }
</style>
"""


def converter_markdown_para_html(markdown_content: str) -> str:
    return markdown.markdown(
        markdown_content,
        extensions=[
            "fenced_code",
            "tables",
            "sane_lists",
        ],
    )


def obter_titulo(markdown_content: str) -> str:
    for line in markdown_content.splitlines():
        cleaned_line = line.strip()

        if cleaned_line.startswith("# "):
            return cleaned_line.removeprefix("# ").strip()

    return "Technical Training"


def remover_titulo_principal(markdown_content: str) -> str:
    lines = markdown_content.splitlines()
    result = []
    title_removed = False

    for line in lines:
        if not title_removed and line.strip().startswith("# "):
            title_removed = True
            continue

        result.append(line)

    return "\n".join(result).strip()


def calcular_tempo_leitura(text: str) -> int:
    word_count = len(text.split())
    return max(1, round(word_count / 220))


def criar_documento_html(
    title: str,
    subtitle: str,
    article_html: str,
    reading_time: int,
) -> str:
    current_date = datetime.now().strftime("%d/%m/%Y")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>{title}</title>

    {ARTICLE_CSS.replace("<style>", "<style>").replace("</style>", "</style>")}
</head>

<body>
    <main style="max-width: 760px; margin: 60px auto; padding: 0 24px;">
        <header class="article-header">
            <div class="article-brand">
                <span class="article-brand-name">Głos AI</span>
                <span class="article-category">AVEVA PI System</span>
            </div>

            <h1 class="article-title">{title}</h1>

            <p class="article-subtitle">
                {subtitle}
            </p>

            <div class="article-meta">
                <span>Głos AI</span>
                <span class="article-meta-separator">·</span>
                <span>{reading_time} min de leitura</span>
                <span class="article-meta-separator">·</span>
                <span>{current_date}</span>
            </div>

            <hr class="article-divider">
        </header>

        <article class="article-content">
            {article_html}
        </article>
    </main>
</body>
</html>
"""


st.markdown(
    ARTICLE_CSS,
    unsafe_allow_html=True,
)


if "ai_analysis" not in st.session_state:
    st.warning("Nenhum artigo foi gerado.")

    if st.button(
        "Voltar para análise",
        use_container_width=True,
    ):
        st.switch_page("pages/analysisAI.py")

    st.stop()


article_markdown = st.session_state.ai_analysis

title = st.session_state.get(
    "article_title",
    obter_titulo(article_markdown),
)

subtitle = st.session_state.get(
    "article_subtitle",
    (
        "Uma aula técnica organizada a partir da transcrição "
        "do treinamento."
    ),
)

article_without_title = remover_titulo_principal(
    article_markdown
)

article_html = converter_markdown_para_html(
    article_without_title
)

reading_time = calcular_tempo_leitura(
    article_markdown
)

current_date = datetime.now().strftime(
    "%d/%m/%Y"
)


st.markdown(
    f"""
    <header class="article-header">
        <div class="article-brand">
            <span class="article-brand-name">
                Głos AI
            </span>

            <span class="article-category">
                AVEVA PI System
            </span>
        </div>

        <h1 class="article-title">
            {title}
        </h1>

        <p class="article-subtitle">
            {subtitle}
        </p>

        <div class="article-meta">
            <span>Głos AI</span>

            <span class="article-meta-separator">
                ·
            </span>

            <span>{reading_time} min de leitura</span>

            <span class="article-meta-separator">
                ·
            </span>

            <span>{current_date}</span>
        </div>

        <hr class="article-divider">
    </header>

    <article class="article-content">
        {article_html}
    </article>
    """,
    unsafe_allow_html=True,
)


standalone_html = criar_documento_html(
    title=title,
    subtitle=subtitle,
    article_html=article_html,
    reading_time=reading_time,
)


st.markdown(
    '<div class="article-actions"></div>',
    unsafe_allow_html=True,
)

download_html_column, download_md_column = st.columns(2)

with download_html_column:
    st.download_button(
        label="Download formatted article",
        data=standalone_html.encode("utf-8"),
        file_name=f"{Path(title).stem}.html",
        mime="text/html; charset=utf-8",
        use_container_width=True,
    )

with download_md_column:
    st.download_button(
        label="Download Markdown",
        data=article_markdown.encode("utf-8"),
        file_name=f"{Path(title).stem}.md",
        mime="text/markdown; charset=utf-8",
        use_container_width=True,
    )