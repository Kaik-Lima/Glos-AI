from collections.abc import Generator
from pathlib import Path

from faster_whisper import WhisperModel


def transcrever_arquivo(
    caminho_arquivo: str | Path,
) -> Generator[tuple[str, str], None, None]:

    arquivo = Path(caminho_arquivo)

    if not arquivo.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {arquivo}"
        )

    yield "Carregando modelo Whisper...", ""

    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8",
    )

    yield "Modelo carregado.", ""

    segmentos, informacoes = model.transcribe(
        str(arquivo),
        language="pt",
        vad_filter=True,
        beam_size=5,
        initial_prompt=(
            "Zara, "
            "Treinamento técnico sobre AVEVA PI System, "
            "PI Server, PI Data Archive, PI Asset Framework, "
            "PI Vision, PI Interface, PI ICU, PI SMT, "
            "PI Buffer Subsystem, PI Point, PI Mapping, "
            "PI Trust, PI Identity, OPC DA e OPC UA."
        ),
    )

    idioma = informacoes.language or "não identificado"

    yield f"Idioma detectado: {idioma}", ""
    yield "Processando segmentos...", ""

    segment_count = 0

    for segmento in segmentos:
        texto = segmento.text.strip()

        if not texto:
            continue

        segment_count += 1

        linha_terminal = (
            f"[{segmento.start:.2f} → "
            f"{segmento.end:.2f}] {texto}"
        )

        print(linha_terminal)

        yield linha_terminal, texto

    yield (
        f"Processamento finalizado. "
        f"{segment_count} segmentos transcritos.",
        "",
    )