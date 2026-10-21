# Glos AI
Transforming spoken knowledge into lasting documentation.

Aplicação local para transformar vídeos em transcrição e conhecimento estruturado.

## Executar

Instale Python, FFmpeg no PATH e Ollama. Na pasta do projeto:

```powershell
python -m pip install -r requirements.txt
ollama pull qwen3:8b
python -m streamlit run app.py
```

O serviço Ollama deve estar em execução. A primeira utilização do Faster-Whisper
Small pode baixar o modelo; o Ollama também precisa do download inicial do Qwen.
Com os modelos disponíveis, transcrição e análise executam localmente.

## Fluxo v0.1

Upload MP4, MKV, MOV, AVI, WEBM, MPEG/MPG ou M4V → Faster-Whisper Small,
CPU int8, português e VAD → visualização e download TXT → Aula/Artigo com
Ollama/Qwen → um resultado final e um download Markdown.

Transcrições curtas usam uma única chamada, mantendo as instruções do artigo
existente. Transcrições longas são divididas automaticamente em partes, preferindo
parágrafos e frases; frases maiores que o limite são divididas entre palavras.
A última parte é reequilibrada quando possível. Não há overlap nem corte de palavras.
Uma palavra isolada maior que o limite gera erro explícito.

Cada parte é analisada localmente para extrair notas técnicas concisas. Essas
extrações ficam somente em memória durante a operação, sem arquivos públicos ou
exibição na tela. A interface mostra “Analisando Parte X de Y” e depois
“Consolidando conteúdo...”. Se as notas juntas ultrapassarem o limite, são
consolidadas em grupos antes da síntese final. O usuário recebe apenas um documento
coeso e um `.md`. Durante a consolidação final, somente o Markdown de saída
aparece progressivamente na tela; as extrações internas permanecem ocultas.
O texto curto também usa streaming, em uma única chamada.

A barra começa na preparação, chega a 10% após o particionamento e avança até
80% a cada parte **concluída**, acompanhada de “Parte X de Y”. Consolidações
intermediárias e final mantêm 80%, com indicador de carregamento. Não se estima
percentual por token. Textos curtos mantêm 10% durante sua única geração. Em ambos
os caminhos, 100% e o download só são liberados após a resposta completa e validada.
O relógio de tempo decorrido atualiza a cada segundo, inclusive durante esperas
sem tokens do Ollama. Os mesmos placeholders são reutilizados durante o streaming
e resultados concluídos são reaproveitados nos reruns.

Falhas de conexão, timeout, modelo ausente, resposta vazia/interrompida, limite de
geração ou falha em qualquer parte/consolidação impedem o download de um documento
incompleto. Se houver falha durante o streaming, o rascunho é removido da tela e
substituído pelo erro. A interface permite tentar novamente; a tentativa retoma as etapas pendentes e reutiliza os resultados compatíveis
validados nos checkpoints locais. Os detalhes e as causas são registrados no log do Streamlit.

## Configuração da análise

Valores centrais em `analysis/config.py`; variáveis opcionais de ambiente:

| Variável | Padrão | Uso |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen3:8b` | Modelo instalado no serviço |
| `OLLAMA_HOST` | `http://localhost:11434` | URL do serviço local |
| `GLOS_CHUNK_CHARS` | `12000` | Limite de caracteres por entrada/grupo de notas |
| `GLOS_PARTIAL_CHARS` | `4000` | Limite de cada extração, menor que metade do limite de entrada |
| `GLOS_OLLAMA_TIMEOUT` | `300` | Timeout HTTP por operação de rede, em segundos |

O timeout de leitura limita a espera entre eventos do stream, não o tempo total
de um vídeo. Parâmetros adicionais na configuração: contexto de 16384 tokens,
até 1500 tokens por extração, 3000 por consolidação intermediária e 6000 por resultado
final, temperatura 0.3 e top_p 0.9.
O limite por caracteres continua existindo, com orçamento adicional conservador por
bytes UTF-8 para o prompt completo, instruções e reserva de saída. Não há tokenização
exata; a estratégia pode produzir mais partes e verifica os contadores reais disponíveis.
O modelo recebe um limite de concisão; se o exceder, a operação falha explicitamente
em vez de cortar silenciosamente a extração. Ajuste os limites conforme conteúdo,
RAM disponível e modelo. Nenhuma parte é descartada para caber na consolidação.

Prompts e pipeline já aceitam Aula/Artigo, Resumo, Tópicos e Perguntas de revisão.
A interface continua oferecendo o modo atual Aula/Artigo. O contexto fixo do Whisper,
os formatos de upload e a página de artigo/HTML existente permanecem como estavam.

O prompt final inclui revisão de ortografia, gramática, concordância e fluidez do
português brasileiro na mesma chamada de geração. Nomes próprios, termos técnicos,
significado e incertezas devem ser preservados. Extrações e documento final são
instruídos a usar somente a transcrição e suas análises derivadas, sem exemplos
externos ou preenchimento de lacunas com conhecimento próprio. Essas instruções
orientam o modelo; não constituem garantia automática de correção editorial/factual.

## Tempos e logs locais

`observability.py` configura logs com timestamp, nível, componente e mensagem.
O console mostra início/fim de transcrição, modelo e parâmetros, duração da mídia,
RTF (tempo de transcrição dividido pela duração da mídia), segmentos, tamanhos das
partes, início/fim e duração de cada chamada e um resumo final de tempos. Quando
disponíveis no evento final do Ollama, registra tokens de entrada/saída e durações
de avaliação/geração, sem estimadores adicionais.

As métricas ficam em memória/sessão e nos checkpoints locais: `transcription_seconds`, `media_duration`,
`rtf`, `segments`, `chunking_seconds`, `partial_seconds`, `consolidation_seconds`,
`analysis_seconds` e `total_seconds`. Consolidação inclui reduções intermediárias.
O total soma transcrição e análise, sem contar a pausa do usuário entre páginas.
No caminho curto, a chamada única é contabilizada como geração/consolidação final.
A interface mostra o tempo da análise; o resumo completo fica no terminal.

Por padrão, os mesmos eventos são gravados em `logs/glos.log`, com rotação de
2 MiB e três backups. A pasta é ignorada pelo Git. Não há transcrição integral,
prompts, conteúdo dos chunks ou respostas nos logs. O nome do arquivo é registrado,
conforme necessário ao diagnóstico; a URL omite credenciais/caminhos/query strings.
Stack traces mantêm frames, tipos de erro, status HTTP e errno, sem mensagens
arbitrárias de exceções externas que possam reproduzir conteúdo sensível.
Se o arquivo de log não puder ser criado, o console continua disponível.

| Variável | Padrão | Uso |
| --- | --- | --- |
| `GLOS_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` |
| `GLOS_LOG_FILE` | `1` | `0` desabilita o arquivo; console continua ativo |

Configure as variáveis antes de iniciar o Streamlit. Os handlers são instalados
uma vez por processo para evitar duplicação nos reruns. Nenhum banco ou serviço
de telemetria foi adicionado. Os segmentos continuam visíveis na interface de
transcrição, mas não são mais impressos no terminal do Python.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Os testes cobrem limites, preservação de conteúdo, múltiplas partes, entradas vazias,
consolidação hierárquica, falhas de rede/modelo/geração e sessão/download no Streamlit.
As chamadas ao modelo são simuladas nessa suíte.

Teste real opcional, com FFmpeg, Whisper Small em cache e Qwen já instalados:

```powershell
python -m tests.smoke_local
```

Esse teste cria um vídeo temporário silencioso para verificar decodificação/modelo/VAD
e analisa textos curtos e particionados no Ollama. Não mede precisão da transcrição
de fala nem qualidade editorial de vídeos extensos. Não há novas dependências de teste.

Os testes de UX também observam a construção progressiva do Markdown, o relógio
antes do primeiro token, os percentuais após cada parte concluída, duas/várias
partes, erros durante o streaming, download único e reruns sem repetir a inferência.
O teste real opcional verifica deltas finais, tempos e RTF com os modelos locais.

Validação da melhoria de UX em 18/10/2026: 39 testes automatizados aprovados.
O teste real com FFmpeg/Whisper Small registrou duração/RTF; o Qwen local concluiu
uma geração curta e uma análise de duas partes com streaming da consolidação.
Os deltas finais foram comparados ao documento completo. Várias partes,
consolidação hierárquica, erros e estados da interface foram verificados com
chamadas simuladas; não foi usado um vídeo longo real para medir qualidade de fala.

Validação desta alteração em 16/10/2026: 26 testes automatizados aprovados;
FFmpeg + Whisper Small CPU/int8/VAD com vídeo silencioso e Ollama `qwen3:8b`
com texto curto e texto dividido em duas partes, seguido de consolidação real,
concluídos com sucesso. Consolidação hierárquica coberta por testes simulados.

Docker permanece no backlog. A [análise separada](docs/DOCKER_ANALYSIS.md) descreve
rede, modelos, cache, volumes e recursos para uma futura fase.


## Correção P0 de estabilidade e recuperação

O [diagnóstico e guia P0](docs/P0_STABILITY.md) detalha a causa observável, as hipóteses
restantes, configurações, testes e validação manual. A consolidação agrupa no máximo
dois nós por chamada, respeita orçamento de contexto/saída e limita os níveis de
redução. Os prompts editoriais, modelo e identidade visual foram preservados.

Resultados completos são salvos atomicamente em `checkpoints/`, associados à entrada,
modelo e assinatura de compatibilidade. **Tentar novamente** reutiliza partes e
consolidações concluídas. Depois de reiniciar o Streamlit, use **Retomar processamento
anterior → Recuperar processamento** na página inicial para recuperar a transcrição,
o TXT e continuar a análise sem reenviar o vídeo. Não há banco nem cópia persistida
do vídeo. Checkpoints contêm texto local legível e expiram após 30 dias de último uso.
A pasta é ignorada pelo Git; `GLOS_CHECKPOINT_DIR` permite escolher outro local.

Configurações de geração diferentes iniciam outra assinatura por segurança;
mudanças apenas de timeout/retry mantêm compatibilidade. Dados de execuções anteriores
à correção não podem ser reconstruídos a partir dos logs antigos. Saídas truncadas,
limites ambíguos, contexto inviável e streams incompletos continuam sendo rejeitados,
com classe de erro, contadores e parâmetros nos logs. Retry automático é limitado a
conexão antes de resposta; gerações parcialmente iniciadas exigem retomada manual.

Os cenários P0 usam dependências simuladas e incluem oito partes, falha na quinta,
falha intermediária, recuperação entre processos, integridade, retenção e não
regressão da interface. Isso não representa aprovação dos dois vídeos longos reais:
essa regressão continua necessária para validação definitiva.

Validação P0 em 21/10/2026: **62 testes automatizados aprovados**, com dependências
simuladas e teste de retomada entre processos. Uma sonda local do Qwen confirmou
o retorno de limite de saída nesta versão; os vídeos longos não foram reexecutados.
