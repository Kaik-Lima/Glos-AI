from collections.abc import Generator
from pathlib import Path
import logging
from time import perf_counter

from observability import configure_logging, format_time, safe_name

from faster_whisper import WhisperModel

logger = logging.getLogger("glos.TRANSCRIPTION")


def transcrever_arquivo(
    caminho_arquivo: str | Path,
    *,
    metrics: dict | None = None,
    display_name: str | None = None,
) -> Generator[tuple[str, str], None, None]:

    configure_logging()
    started = perf_counter()
    metrics = metrics if metrics is not None else {}
    try:
        arquivo = Path(caminho_arquivo)

        if not arquivo.exists():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {arquivo}"
            )

        logger.info(
            "Iniciando transcrição | Arquivo=%s | Tamanho=%.2f MB | Modelo=small "
            "device=cpu compute_type=int8 Idioma=auto VAD=True",
            safe_name(display_name or arquivo.name), arquivo.stat().st_size / (1024 * 1024),
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
            language=None,
            task="transcribe",
            vad_filter=True,
            beam_size=5,
            initial_prompt=None,
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

            yield linha_terminal, texto

        yield (
            f"Processamento finalizado. "
            f"{segment_count} segmentos transcritos.",
            "",
        )
        elapsed = perf_counter() - started
        duration = informacoes.duration or 0.0
        rtf = elapsed / duration if duration > 0 else None
        metrics.update(
            filename=safe_name(display_name or arquivo.name),
            media_duration=duration, transcription_seconds=elapsed,
            segments=segment_count, rtf=rtf,
        )
        logger.info("Concluída | Mídia=%s | Tempo=%s | RTF=%s | Segmentos=%s",
                    format_time(duration), format_time(elapsed),
                    f"{rtf:.3f}" if rtf is not None else "indisponível", segment_count)
        if not segment_count:
            logger.warning("Nenhum segmento de fala identificado.")
    except Exception:
        logger.exception("Falha na transcrição | Arquivo=%s | Tempo=%s",
                         safe_name(display_name or str(caminho_arquivo)),
                         format_time(perf_counter() - started))
        raise
