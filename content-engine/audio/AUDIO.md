# Camada de áudio

Efeitos sonoros, música de fundo, narração e legenda sincronizada dos vídeos. Quem automatiza chama só os scripts deste contrato; o áudio entra no vídeo como arquivo local dentro da composição e é misturado pelo motor de vídeo (`content-engine/video/MOTOR.md`, seção "Áudio na composição"). Nenhum dado do projeto vai para terceiro, com uma exceção explícita: o texto da narração, quando o provedor de voz escolhido é de nuvem.

## Como o áudio entra num vídeo

- **Efeitos: quase sempre.** Vídeo mudo cansa. Efeito curto marca cada movimento importante (texto que entra, troca de batida, número que fecha, botão apertado, fecho).
- **Voz: quando o roteiro pede.** Passo a passo e explicação ganham com narração; peça puramente visual costuma funcionar só com efeitos. O texto na tela continua obrigatório com ou sem voz (muita gente assiste no mudo).
- **Música de fundo: opcional.** Uma faixa da biblioteca (`music/`), baixa quando tem voz e cheia nas pausas (seção "Música de fundo"). Sem a chave `musica` no `trilha.json`, a peça sai sem música.

## Contrato

Todos rodam da raiz do repo com Python 3 (biblioteca padrão; o Kokoro roda num venv próprio, isolado):

```bash
python content-engine/audio/doctor.py
python content-engine/audio/sfx_setup.py [--offline]
python content-engine/audio/musica_setup.py [--offline]
python content-engine/audio/catalogo_audio.py [--lista lista.json --pasta <composicao> --saida <video.mp4>]
python content-engine/audio/voz_setup.py [--modelo fp32|fp16|int8]
python content-engine/audio/voz.py <voz.txt | roteiro.md> --saida <pasta> [--provedor voicestudio|kokoro|azure|azure_openai|google] [--voz <id>] [--estilo excited] [--tom "animado, de locutor"] [--altura +2st] [--velocidade 1.1]
python content-engine/audio/voz.py --listar-vozes
python content-engine/audio/comparar_vozes.py [--frase "..."] [--vozes comparacao_vozes.json] [--saida <pasta>] [--verificar]
python content-engine/audio/voz.py --benchmark [--modelo fp16]
python content-engine/audio/trilha.py <pasta-da-composicao> <trilha.json>
python content-engine/audio/legenda.py <pasta-da-composicao> [--trilha trilha.json] [--texto voz.txt]
```

- `doctor.py`: PASS/FAIL por item (FFmpeg local, biblioteca de efeitos batendo com `sfx.json` e `CATALOGO.md`, biblioteca de música batendo com `musica.json`, `musica_fontes.json` e `CATALOGO.md`, venv e modelo do Kokoro com SHA-256, isolamento do processo de voz, `.gitignore`) e INFO de quais provedores de nuvem (`azure`, `azure_openai`, `google`) têm chave, sem mostrar a chave. Kokoro ausente é FAIL só quando ele é o provedor ativo em `voz_config.json`. Provedor ativo de nuvem sem chave é AVISO, nunca FAIL.
- `sfx_setup.py`: baixa os pacotes CC0 fixados em `sfx_fontes.json` (SHA-256 conferido) para `.cache/sfx/` e refaz `sfx/` a partir de `sfx_selecao.json`: corta silêncio, converte para WAV 48 kHz mono, normaliza e grava `sfx.json` e `CATALOGO.md`. Os efeitos do conjunto cine são gerados por `sfx_sintese.py` (síntese própria, semente fixa; ele é chamado pelo setup) e saem com `ancora`, nível e distribuição de energia por faixa no `sfx.json`. Com o FFmpeg fixado o resultado é byte a byte igual (o script avisa se algum arquivo mudar). Não precisa rodar para usar: a biblioteca curada já está no repo.
- `musica_setup.py`: baixa as fontes CC0 fixadas em `musica_fontes.json` (SHA-256 conferido) para `.cache/musica/` e refaz `music/`: corta o trecho, leva a -16 LUFS integrado (pico até -1,5 dBTP), converte para AAC `.m4a` 48 kHz estéreo, mede o BPM (usa o numpy do `.venv` do áudio; sem o venv o BPM fica nulo) e grava `musica.json` e `CATALOGO.md`. Com o FFmpeg fixado o resultado é byte a byte igual. Também não precisa rodar para usar.
- `catalogo_audio.py`: vídeo de audição pelo motor de vídeo local. Sem argumentos, toca cada efeito da biblioteca com categoria, nome do arquivo, duração, uso e a forma de onda na tela (`sfx/catalogo.mp4`). Com `--lista`, faz o mesmo com qualquer lista de áudios (comparação de vozes).
- `voz_setup.py`: cria `content-engine/audio/.venv`, instala os pacotes do `kokoro/requirements.txt` com `pip --require-hashes` (cache em `.cache/pip`, sem tocar no Python do sistema nem na pasta do usuário) e baixa o modelo com SHA-256 fixado em `kokoro/modelo.json` para `.models/`. `--gerar-lock` é manutenção: refaz o lock, recusando versão publicada há menos de 14 dias.
- `voz.py`: uma fala por batida. Entrada: `voz.txt` (uma fala por linha; `#` é comentário) ou um `roteiro.md` com tabela que tenha a coluna `Voz`. Saída na pasta pedida: `voz-01.wav`, `voz-02.wav`... numerados pela batida (coluna `#` da tabela ou ordem da linha no `.txt`; batida com `Voz` vazia ou `-` fica sem arquivo) (48 kHz mono, -16 LUFS, pico até -1,5 dBTP, silêncio das pontas cortado) e `voz.json` com duração de cada fala, provedor, voz, modelo, total de caracteres e fator de tempo real. Interpretação por batida (só nos provedores que aceitam; nos outros a opção é recusada e a coluna é avisada e ignorada): coluna `Estilo` na tabela do roteiro, ou prefixo `[estilo] fala` no `.txt`; `--estilo` é o padrão das batidas sem estilo próprio. No Azure Speech o estilo vira `<mstts:express-as>` (ex.: `excited`) e `--altura` vira `<prosody pitch>`; no `azure_openai` o estilo (ou `--tom`) vira a instrução de tom em texto livre. Com `azure_openai`, o `voz.json` guarda também a transcrição devolvida, os tokens de cada fala (`tokens`, `tokens_total`) e quantas tentativas foram necessárias.
- `comparar_vozes.py`: gera a mesma frase (padrão: a primeira fala de `examples/narration/voz.txt`, ou `--frase`) em cada voz de `comparacao_vozes.json`, todas a -16 LUFS, pula e lista as entradas cujo provedor está sem chave, e monta a composição do vídeo de comparação (um cartão por voz com o rótulo grande) mais `manifesto.json` (ordem, voz, provedor, duração, caracteres, tokens e nota de custo). Não renderiza: o render é `python content-engine/video/render.py <saida>/composicao <saida>/vozes-comparacao.mp4`. Uma entrada que falha não derruba as outras. `--verificar` só mostra quais entradas estão prontas. Saída padrão: `content-engine/audio/.work/vozes-comparacao/` (fora do git). A nota de custo usa valores de tabela fixos no código, que envelhecem: confira o preço atual na página do provedor.
- `trilha.py`: lê um `trilha.json` (`{"volume_efeitos": 0.8, "deixas": [{"t": 0.75, "efeito": "pop/pop-gota"}, {"t": 0.25, "arquivo": "assets/voz/voz-01.wav", "volume": 1.0}]}`), copia os efeitos usados para `assets/sfx/` da composição e escreve os `<audio>` na raiz do `index.html` (marcados com `data-trilha="1"`; rodar de novo substitui). Voz na trilha 10, efeitos de 11 em diante sem sobrepor na mesma trilha. Uma deixa aceita `volume` e `duracao` (corta o efeito). Com a chave opcional `musica`, gera também `assets/musica/base.wav` e o `<audio>` dela na trilha 9 (seção "Música de fundo").
- `legenda.py`: mede o tempo de cada palavra das falas e grava `legenda.json` e `legenda.js` na composição (seção "Legenda sincronizada").

## Efeito por movimento

Biblioteca em `sfx/` (catálogo completo e combinações em `sfx/CATALOGO.md`, licenças em `sfx/LICENCAS.md`). Dois conjuntos: o **cine** (nomes com `-cine`: whoosh com corpo e cauda, impacto com subgrave, riser, reverso, brilho, tudo com um pouco de sala) é o padrão para peça nova; a biblioteca clássica (interface e jogo, seca) fica para tema retrô e para as composições antigas, que seguem funcionando.

- **Âncora.** Efeito com `ancora` no `sfx.json` (whoosh, riser, reverso, transição pronta, contagem com fecho) tem o ponto de sincronia dentro do arquivo: a deixa vai em `t = momento do movimento - âncora`. Nos demais o WAV começa no instante do som e o `t` da deixa é o próprio momento.
- Entrada de cena: `whoosh/whoosh-cine-medio` com a âncora no frame em que o elemento assenta e `impact/impacto-cine-macio` no mesmo frame; elemento pequeno: `whoosh/whoosh-cine-curto` sozinho.
- Troca de batida: `transition/transicao-cine` com a âncora no corte (riser, whoosh e impacto já alinhados; deixa em `corte - 0,75 s`); corte leve: `transition/swish-cine-leve`; virada da peça: `transition/transicao-cine-forte`.
- Número que conta: `counter/contador-cine-macio` por baixo (aparado com `duracao`) e `riser/riser-cine-1s` terminando na parada; no valor final, `impact/impacto-cine-medio` com `shine/brilho-cine-curto`. Em peça com cara de game, `coin-8bit/*` no valor final.
- Gancho: título pesado no frame 0 com `impact/impacto-cine-medio`; lacuna (pergunta, valor escondido) com `notification/notificacao-cine-limpa`.
- Toque de interface: `click/clique-cine-abafado` no aperto, `pop/pop-cine-redondo` no que aparece e `success/sucesso-cine-discreto` na resposta.
- Busca ou prompt sendo digitado: `typing/digitacao-cine-suave` (encurte com `duracao`).
- Fecho com logo: `riser/reverso-cine-longo` terminando na entrada do logo com `shine/brilho-cine-longo`, ou `success/sucesso-cine-acorde`; `jingle/*` só em peça retrô. Sempre depois da última fala (nunca por baixo dela).
- Nível do conjunto cine: nivelado por família (impacto acima de whoosh, whoosh acima de tique), então `volume` 1.0 serve sem voz; com voz, de 0.4 a 0.7. O subgrave (`impact/impacto-cine-sub` e a cauda dos impactos) quase não toca no alto-falante do celular: lá o que se ouve é a pancada e o estalo.
- Menos é mais: um efeito por movimento importante, não um por elemento. Sem efeito em cima de palavra-chave da voz.

## Música de fundo

Biblioteca em `music/` (catálogo em `music/CATALOGO.md`, licenças em `music/LICENCAS.md`): 10 faixas instrumentais CC0 de até 60 s, a -16 LUFS. No `trilha.json`:

```json
{"musica": {"faixa": "chiptune-selecao", "volume": 0.5, "sob_voz": 0.18, "inicio": 0.0, "entrada": 0.6, "saida": 1.2, "ataque": 0.25, "soltura": 0.5}}
```

- Só `faixa` é obrigatória (id do catálogo); os outros valores acima são os padrões. No lugar de `faixa`, `arquivo` aponta um áudio dentro da composição.
- O volume do `<audio>` é fixo no player, então a música não é abaixada lá: o `trilha.py` grava um arquivo já mixado, `assets/musica/base.wav` (48 kHz estéreo, duração do vídeo), e um único `<audio id="trilha-musica">` na trilha 9 com `data-volume="1.0"`.
- O que vai dentro do `base.wav`: a faixa em laço até cobrir o vídeo, começando em `inicio` (segundo do vídeo), com fade de `entrada` e de `saida`; `volume` nas pausas e `sob_voz` durante a fala.
- A descida é calculada pelas deixas de voz (`t` até `t` + duração), sem analisar o som: desce em `ataque` segundos e chega embaixo 0,05 s antes da fala; volta em `soltura` segundos depois dela. Falas com menos de 0,6 s de pausa entre si ficam num único trecho baixo (num vídeo narrado de ponta a ponta a música fica baixa quase o tempo todo, de propósito).
- Rodar de novo com a mesma entrada dá o mesmo `base.wav`, byte a byte. Tirar a chave `musica` e rodar de novo apaga o `base.wav` e o `<audio>` dela.
- Níveis de partida: `volume` 0.5 e `sob_voz` 0.18 deixam a música perto de -22 LUFS nas pausas e -31 LUFS sob a voz (9 dB de diferença; voz a -16 LUFS fica 15 dB acima). Peça sem voz: `volume` 0.5 a 0.7.
- Escolha pelo clima da peça (campo de uso no catálogo): `chiptune-*` e `synthwave-*` para tema de jogo ou retrô, `eletronica-otimista` para novidade e demonstração, `lofi-*` e `ambiente-*` para narração longa. Audição humana da faixa antes de usar em peça.
- Faixa nova: só CC0 conferida na página de origem; registrar página, URL, autor e SHA-256 em `musica_fontes.json` (`fontes` e `faixas`), rodar `python content-engine/audio/musica_setup.py` e atualizar `music/LICENCAS.md`.

## Mixagem

- **Níveis de fábrica.** Voz: cada fala a -16 LUFS integrado, com compressão leve e limitador (pico até -1,5 dBTP). Efeitos: pico de loudness momentânea em -16 LUFS e pico real até -1 dBTP (clique e tique ficam mais baixos na medida, mas soam presentes pelo transiente).
- **Com voz:** voz em `volume` 1.0; efeitos entre 0.3 e 0.6 (tique de contador 0.3, whoosh 0.5, pop 0.5, clique 0.6 a 0.7, jingle 0.6 depois da última fala). Referência: voz cerca de 8 dB acima dos efeitos.
- **Sem voz:** efeitos entre 0.6 e 1.0 (secundários 0.4 a 0.5).
- **Mix final esperado:** perto de -14 LUFS integrado com voz e pico real até -1 dBTP; o motor exporta AAC 48 kHz estéreo. Conferir com `ffmpeg -i <video.mp4> -af ebur128=peak=true -f null -` (FFmpeg local em `content-engine/video/bin/`).
- **Voz dita o tempo.** Com narração, cada batida dura `max(duração visual, início da fala + duração da fala em voz.json + 0,3 s)`; a fala começa 0,15 s depois do frame 0 no gancho e 0,25 s depois do início das outras batidas. A última batida ganha espaço para o jingle depois da fala. Não há duração fixa para o vídeo: ela depende da proposta, e cada batida precisa ganhar o seu tempo. Fala que arrasta pode ser encurtada ou acelerada com `--velocidade`, por decisão de ouvido.
- **Fala escrita para a voz.** Mesmos fatos da tela, frase mais curta, números por extenso ("cento e quinze reais", não "R$ 115"), sem sigla que a voz soletre errado.

## Legenda sincronizada

`python content-engine/audio/legenda.py <pasta-da-composicao> [--trilha trilha.json] [--texto voz.txt|voz.json|roteiro.md] [--destaque "preço,versão"] [--max-palavras 4] [--max-caracteres 32] [--pausa 0.35] [--sem-whisper] [--detalhe]`

- **O que faz:** para cada deixa de voz da trilha (`arquivo` + `t`), mede o início e o fim de cada palavra e grava na composição `legenda.json` (blocos com `inicio`, `fim` e `palavras: [{texto, inicio, fim, destaque}]`, em segundos do vídeo, mais um resumo por fala) e `legenda.js` (`window.__legenda = [...]`, para `<script src>`). Quem desenha é o kit de motion: `K.legenda` (`content-engine/video/MOTOR.md`, seção "Legenda sincronizada com a fala").
- **De onde vem o tempo:** Whisper local, 100% offline. O `faster-whisper` do venv do VoiceStudio roda num processo separado (`legenda_worker.py`) com o modelo `deepdml/faster-whisper-large-v3-turbo-ct2` que o `voicestudio.py modelos` já baixa, na CPU, com Hugging Face offline e proxy morto. Não sobe a API do VoiceStudio nem usa a porta dela, então pode rodar junto com uma geração de voz. Na CPU é lento: conte com algumas vezes a duração da fala.
- **O texto é o do roteiro, não o que o Whisper ouviu.** O texto de cada fala vem de `--texto` ou, sem ele, de `assets/voz/voz.json`, `voz.json`, `voz.txt` ou `vozes/voz.txt` da composição (`voz-03.wav` usa a batida 3). A sequência ouvida é alinhada à do roteiro (sem acento, caixa e pontuação); palavra sem par recebe tempo interpolado entre as vizinhas. Fala com menos de metade das palavras casadas, ou sem Whisper (VoiceStudio não instalado ou `--sem-whisper`), cai no plano B: trechos de fala achados pelo `silencedetect`, com o tempo repartido pelo número de caracteres (a saída avisa).
- **Blocos:** até 4 palavras e 32 caracteres; quebra em pontuação forte (`. ! ? : ;`) e em pausa maior que 0,35 s; palavra de 1 ou 2 letras nunca fica sozinha nem pendurada no fim de um bloco no meio da frase, e palavra sozinha no fim da frase puxa a anterior.
- **Destaque:** `--destaque "preço,versão"` ou `*palavra*` no texto (o asterisco não vai para a tela; use um arquivo de texto próprio para a legenda, não o que vai para a voz).
- Rodar de novo depois de mudar a voz, o texto ou o `t` das deixas. Testes: `python -m unittest tests.test_legenda` em `content-engine/audio/` (alinhamento e blocos com tempos sintéticos, sem Whisper).

## Provedores de voz

Escolha em `voz_config.json` (`provedor`, voz padrão por provedor, velocidade) ou por `--provedor`. Chave só no `content-engine/audio/.env` (ignorado pelo git) ou numa variável de ambiente já definida, que prevalece sobre o arquivo; nunca em arquivo versionado, log ou `voz.json`. A voz é gerada antes do render, e o render do vídeo roda num ambiente que remove essas variáveis e não alcança essa pasta.

- **Padrão do repo: `kokoro` com a voz `pf_dora`.** É o caminho local que funciona sem voz própria e sem chave: basta `python content-engine/audio/voz_setup.py`. Para fixar outra voz (a "voz da casa"), use `VOZ_PROVEDOR` e `VOZ_<PROVEDOR>` no `.env` ou edite o `voz_config.json`.
- **Kokoro-82M, local: `--provedor kokoro`.** Licença Apache-2.0, via `kokoro-onnx` 0.6.1 (MIT) e onnxruntime na CPU. Nada sai da máquina. Vozes pt-BR: `pf_dora` (feminina), `pm_alex` e `pm_santa` (masculinas). O suporte a português é descrito pelo próprio projeto como limitado e a fala pode soar robótica: a qualidade é decisão de quem ouve. Modelo `fp16` por padrão (em x86 fica próximo do `fp32` em velocidade, com menos memória; `int8` é bem mais lento em x86). Em máquina fraca, rode `voz.py --benchmark` (e `--modelo fp32` para comparar) antes de decidir.
- **VoiceStudio, local: `--provedor voicestudio`.** App de voz open source (AGPL-3.0) clonado em `voicestudio/repo` no commit fixado em `voicestudio/pin.json`, rodando só a API em `127.0.0.1`, offline (proxy morto, Hugging Face offline, analytics e marca d'água desligados). O adaptador sobe a API, gera e derruba no fim; `python voicestudio/voicestudio.py checar --vigiar 60` mostra as conexões abertas pelo processo. Modelo OmniVoice, cujos pesos são **CC-BY-NC (não comercial)**: uso comercial da voz gerada por ele não é permitido; para uso comercial, troque de modelo ou de provedor. Não há voz padrão: o repo não traz nenhuma voz, e o provedor só fica disponível depois de criar a sua (`python voicestudio/voicestudio.py voz ... --salvar <nome>` ou `clonar ... --guardar`, ver `voicestudio/voices/README.md`) e apontar `VOZ_VOICESTUDIO=<nome>` no `.env` (ou `--voz <nome>`). Vozes guardadas ficam em `voicestudio/voices/` (wav de referência + texto falado); cada máquina recria os perfis delas ao subir a API. Geração na CPU é lenta (dezenas de segundos por fala curta) e usa alguns GB de RAM com a API no ar. Variantes por `--modelo`: `qualidade` (32 passos de geração, padrão) e `rapido` (16 passos, menos tempo por fala; compare de ouvido antes de adotar). Instalação: `python voicestudio/voicestudio.py instalar` e depois `modelos`. Sem estilos: a coluna `Estilo` fica vazia e a entonação vem do texto.
- **Azure AI Speech, nuvem: `--provedor azure`.** REST com SSML; aceita qualquer `ShortName` da região, inclusive os com sufixo (`pt-BR-Luana:MAI-Voice-2.1`). Vozes pt-BR da lista curada: MAI-Voice 2.1 (`pt-BR-Luana`, `-Caio`, `-Pedro`, `pt-BR-Rafael:MAI-Voice-2.1`, todas com sufixo `:MAI-Voice-2.1`, e as variantes `:MAI-Voice-2.1-Flash`), com estilos como `excited`, `happy`, `joyful`, `hopeful`, `determined`, `confused`, `embarrassed`, `regretful`, `relieved`; Dragon HD (`pt-BR-Thalita:DragonHDLatestNeural`, `pt-BR-Macerio:DragonHDLatestNeural`); Neural (`pt-BR-FranciscaNeural`, `-AntonioNeural`, `pt-BR-ThalitaNeural`, `pt-BR-ThalitaMultilingualNeural`, `-MacerioMultilingualNeural`). A lista vem do catálogo do serviço e a maior parte não foi ouvida: qual soa melhor é decisão de quem ouve (`comparar_vozes.py`). `voz.py --listar-vozes` com a chave no ambiente lê a lista ao vivo e mostra só as pt-BR nativas agrupadas por tipo; sem chave mostra a lista curada marcada "sem chave". Estilo por batida: `--estilo excited` ou coluna `Estilo`. Ritmo e altura: `--velocidade` e `--altura` (SSML `<prosody>`, que só entra no pedido quando usado, porque o suporte a `prosody` nas vozes MAI e Dragon HD não foi testado). Texto escapado em XML. Variáveis: `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` (padrão `eastus` quando ausente; use a região do seu recurso). Que o texto enviado não treina modelo é afirmação não verificada aqui: conferir nos termos do Azure antes de enviar texto real.
- **Azure OpenAI gpt-audio, nuvem: `--provedor azure_openai`.** O modelo de chat com saída de áudio fala o texto como um locutor e aceita instrução de tom em texto livre (`--tom "animado, de locutor"`). Deployment padrão: `gpt-audio-1.5`; outro nome de deployment entra por `AZURE_OPENAI_AUDIO_DEPLOYMENT`. Vozes: `marin` (padrão) e `cedar`, testadas com `gpt-audio-1.5` (transcrição idêntica ao texto), mais `alloy`, `ash`, `ballad`, `coral`, `echo`, `sage`, `shimmer`, `verse` (não testadas). O modelo é generativo e pode parafrasear, então cada fala é conferida: o adaptador normaliza (minúsculas, sem acento, sem pontuação) a transcrição devolvida e o texto de entrada; se diferem, refaz uma vez; se diferem de novo, a geração para, com a fala, o esperado e a última transcrição na mensagem. Nunca aceita paráfrase em silêncio. O modelo não tem velocidade: `--velocidade` vira uma instrução de ritmo no prompt (aproximada). A chave só vai para o endpoint configurado, que precisa ser `*.azure.com`, e nenhum provedor com chave segue redirecionamento (a biblioteca repassaria a chave ao destino). Variáveis: `AZURE_OPENAI_ENDPOINT` (host, ex.: `https://<recurso>.services.ai.azure.com`), `AZURE_OPENAI_KEY`, e opcionais `AZURE_OPENAI_API_VERSION` (padrão `2025-04-01-preview`) e `AZURE_OPENAI_AUDIO_DEPLOYMENT`. Mesma ressalva de privacidade do Azure Speech.
- **Google Cloud Text-to-Speech, nuvem: `--provedor google`.** REST, vozes Chirp 3 HD pt-BR (`pt-BR-Chirp3-HD-Kore`, `-Aoede`, `-Charon`). Chave em `GOOGLE_TTS_API_KEY`. Adaptador pronto, ainda não testado contra o serviço real. Que o dado enviado não treina modelo é afirmação não verificada aqui: conferir nos termos do Google Cloud antes de enviar texto real.
- **Nunca:** camada gratuita que treina com o texto enviado, site de voz sem contrato de dados, ou clonagem de voz de pessoa real sem autorização dela.

Custo: Kokoro e VoiceStudio rodam na máquina, sem cobrança. Os provedores de nuvem cobram por caractere ou por token de áudio; os preços mudam e não fazem parte da engine: confira a página de preços do provedor antes de decidir. O `voz.json` e o `manifesto.json` do `comparar_vozes.py` guardam caracteres e tokens de cada fala para a conta.

## Voz de nuvem: chaves no arquivo `.env`

Opcional: só para quem vai usar provedor de nuvem ou fixar a voz padrão. As chaves ficam num arquivo só, `content-engine/audio/.env`, que o git ignora. O modelo é o `content-engine/audio/.env.example`: copiar para `.env` na mesma pasta e trocar os valores entre `<>` (linha com valor entre `<>` é ignorada). A chave é a do seu próprio recurso; o valor não entra em conversa, chat de assistente ou outro arquivo.

```ini
AZURE_SPEECH_KEY=<chave do seu recurso>
AZURE_SPEECH_REGION=<regiao>
AZURE_OPENAI_ENDPOINT=<endpoint do seu recurso>
AZURE_OPENAI_KEY=<chave do seu recurso>
VOZ_PROVEDOR=azure
VOZ_AZURE=pt-BR-Luana:MAI-Voice-2.1
```

- `voz.py`, `comparar_vozes.py` e `doctor.py` leem esse arquivo ao começar; não precisa reabrir terminal. Variável já definida no ambiente prevalece sobre o arquivo. `AZURE_SPEECH_REGION` e `AZURE_OPENAI_API_VERSION` são opcionais (padrões: `eastus` e `2025-04-01-preview`).
- **Trocar a voz padrão:** mudar `VOZ_PROVEDOR` e a linha `VOZ_<PROVEDOR>` (`VOZ_KOKORO`, `VOZ_VOICESTUDIO`, `VOZ_AZURE`, `VOZ_AZURE_OPENAI`, `VOZ_GOOGLE`) no `.env`; vale na próxima geração, sem mexer em código. Os ids saem de `python content-engine/audio/voz.py --listar-vozes`. Sem essas linhas vale o `voz_config.json`; `--provedor` e `--voz` na linha de comando ainda mandam. Cada máquina tem o seu `.env`. O `doctor.py` mostra no fim qual é a voz padrão e de onde ela veio.
- O arquivo fica fora das pastas de composição, então o render de vídeo (que recusa `.env` perto da composição e não lê nada fora dela) nunca o alcança.
- Conferir sem expor nada: `python content-engine/audio/doctor.py` mostra "chave presente" ou "sem chave" por provedor, e `python content-engine/audio/voz.py --listar-vozes` lê a lista ao vivo do Azure.
- Escolher a voz de ouvido: `python content-engine/audio/comparar_vozes.py` gera a mesma frase em todas as vozes de `comparacao_vozes.json` (as sem chave são puladas e listadas); depois o vídeo de comparação é renderizado.
- O render do vídeo roda num ambiente que remove essas variáveis (o prefixo `AZURE_` está no filtro de segredos).

## Como adicionar um provedor de voz

A troca não mexe no motor de vídeo:

1. Criar `content-engine/audio/providers/<nome>.py` com `NOME`, `DESCRICAO`, `LOCAL` (bool), `VOZES` (lista de `{"id", "genero", "idioma", "nota"}`), `VOZ_PADRAO`, `disponivel(variante=None)` devolvendo `(bool, motivo)` sem nunca imprimir a chave, e `sintetizar(linhas, voz, pasta, velocidade=1.0, variante=None)` gravando `bruto-01.wav`... em `pasta` e devolvendo `{"modelo", "carga_s", "itens": [{"arquivo", "sintese_s", "audio_s"}]}`.
2. Registrar o nome em `providers/__init__.py` (`DISPONIVEIS`) e a voz padrão em `voz_config.json`. Se o adaptador aceita interpretação (estilo, tom, altura), declarar `OPCOES_ACEITAS` (subconjunto de `estilo`, `estilos`, `tom`, `altura`) e receber `opcoes=None` em `sintetizar`; quem não declara recebe a opção recusada pelo `voz.py` em vez de ignorá-la. Hook opcional `listar_vozes_vivo()` devolvendo `[(grupo, [{id, genero, nota}])]` para o `--listar-vozes` mostrar a lista real do serviço.
3. Chave lida do `content-engine/audio/.env` ou do ambiente, com nome que o filtro `SECRET_NAME` de `content-engine/common/ambiente.py` já remove do render (contém `API_KEY`, `TOKEN` ou `SECRET`, ou começa com prefixo de provedor como `AZURE_` e `GOOGLE_`). Se o prefixo for novo, o nome precisa conter `API_KEY`.
4. Rodar `voz.py --listar-vozes`, gerar a frase de comparação com `comparar_vozes.py`, ouvir e atualizar a lista de provedores acima com privacidade e qualidade ouvida.

Ganchos opcionais, também dentro do adaptador: `variantes()` devolvendo as variantes de modelo aceitas por `--modelo` e `conferir_vozes()` devolvendo `(ids instalados, resumo)` para o `--listar-vozes` conferir as vozes contra o modelo local. O `voz.py` descobre ambos pelo registro, sem citar provedor. O registro só carrega um adaptador quando ele é usado (geração, `--modelo` ou `--listar-vozes`): adaptador quebrado, ou `modelo.json` ilegível, desliga só aquele provedor, com a mensagem do erro, e os outros seguem funcionando.

Toda dependência de fornecedor fica dentro do adaptador. `voz.py` só conhece o contrato acima e faz o tratamento comum (corte de silêncio, nível, WAV 48 kHz, `voz.json`).

## Como mudar a biblioteca de efeitos

1. Fonte nova: só CC0 conferido na página de origem; registrar URL fixa, página, autor e SHA-256 em `sfx_fontes.json` (zip de pacote; arquivo de som solto leva `"tipo": "arquivo"`).
2. Editar `sfx_selecao.json`. Efeito tirado de pacote: categoria, nome descritivo, pacote, arquivo dentro do zip, `corte` opcional, uso, produtos. Efeito de síntese (conjunto cine): `sintese` com o nome da receita em `sfx_sintese.py`, `conjunto`, `alvo_db` (nível da família), `camadas` opcionais (gravações CC0 que a receita trata), uso, produtos. Nunca renomear nem apagar um efeito já usado em composição.
3. Receita nova: uma função em `sfx_sintese.py` registrada em `RECEITAS`, que devolve o som, a âncora em segundos e o fade final. A síntese é determinística (semente fixa) e usa o numpy do `.venv` do `voz_setup.py`; sem numpy, o setup mantém os WAVs de síntese que já estão no git.
4. `python content-engine/audio/sfx_setup.py`, depois `python content-engine/audio/catalogo_audio.py` e audição humana do `sfx/catalogo.mp4` antes de usar em peça. Combinações do catálogo: lista `combinacoes` do `sfx_selecao.json`.

## Estrutura

```text
content-engine/audio/
  AUDIO.md            este arquivo
  doctor.py           diagnostico PASS/FAIL
  sfx_setup.py        refaz a biblioteca a partir dos pacotes fixados
  sfx_sintese.py      sintese propria do conjunto cine (chamado pelo sfx_setup.py)
  sfx_fontes.json     pacotes CC0: URL, pagina, autor, SHA-256
  sfx_selecao.json    a curadoria (o que entra em sfx/ e como)
  musica_setup.py     refaz a biblioteca de musica a partir das fontes fixadas
  musica_fontes.json  fontes CC0 (URL, pagina, autor, SHA-256) e a curadoria das faixas
  musica_bpm.py       mede o BPM (roda no .venv, com numpy)
  catalogo_audio.py   video de audicao (catalogo e comparacao de vozes)
  voz.py              narracao: um WAV por batida + voz.json
  voz_config.json     provedor e voz padrao
  comparar_vozes.py   mesma frase em varias vozes + composicao do video de comparacao + manifesto.json
  comparacao_vozes.json  lista de vozes comparadas (editavel)
  voz_setup.py        venv do Kokoro com hashes e modelo com SHA-256
  trilha.py           escreve os <audio> na composicao e gera a base de musica com ducking
  legenda.py          tempos por palavra da narracao: legenda.json e legenda.js (+ legenda_worker.py, Whisper local)
  _comum.py           caminhos, FFmpeg local, medicao de loudness, download conferido
  providers/         voicestudio.py (usa voicestudio/voicestudio.py), kokoro.py (+ kokoro_worker.py, roda no venv), azure.py, azure_openai.py, google.py
  tests/             test_vozes_nuvem.py (SSML, estilo, escape, conferencia literal, voz.json; sem rede), test_trilha_musica.py (trechos de ducking, base.wav, idempotencia, erros), test_legenda.py (alinhamento e blocos)
  kokoro/             requirements.txt (lock com SHA-256) e modelo.json (arquivos e SHA-256)
  sfx/                efeitos curados (no git), sfx.json, CATALOGO.md, LICENCAS.md, catalogo.mp4
  music/              faixas de fundo curadas (no git), musica.json, CATALOGO.md, LICENCAS.md
  .venv/ .cache/ .models/ .work/   fora do git
```
