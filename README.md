# vbss-media-engine

Engine local para gerar mídia a partir de HTML: vídeo (HTML + GSAP), imagem estática (HTML para PNG) e áudio (efeitos sonoros, música de fundo, narração e legenda sincronizada com a fala). Tudo roda na sua máquina, sem nuvem obrigatória: o render não acessa a internet e só lê arquivos de dentro da pasta da peça.

Serve para qualquer conteúdo que caiba numa página: vídeo explicativo, vídeo curto vertical, cartão, slide de carrossel, capa. Você cria as suas próprias marcas e projetos; o repo traz só uma marca fictícia de exemplo.

## Requisitos

- Windows 10 ou 11 (x64). Os scripts baixam binários para Windows e a prova monitorada usa PowerShell.
- Python 3 (testado com 3.11; só biblioteca padrão, e as vozes locais criam ambientes próprios, isolados).
- Node.js 22 ou mais novo (motor de vídeo).
- Git (para a voz local padrão, o VoiceStudio).
- Cerca de 12 GB livres em disco para a voz local padrão (VoiceStudio e modelos); o resto do motor ocupa bem menos.

## Instalação

Na raiz do repo:

```bash
python content-engine/video/setup.py
python content-engine/video/doctor.py
python content-engine/image/setup.py
python content-engine/image/doctor.py
```

- `video/setup.py` instala os pacotes npm fixados do motor (`npm ci --ignore-scripts`), o FFmpeg e o navegador fixo (`chrome-headless-shell`), todos com versão fixa e SHA-256 conferido. É o único momento em que há rede. Cerca de 115 MB de download do navegador, mais FFmpeg e pacotes npm.
- `image/setup.py` instala só o navegador fixo (não baixa de novo se o do vídeo já rodou).
- Os dois `doctor.py` imprimem `PASS`/`FAIL` por item e saem com código 1 se algo falhar.

Áudio:

```bash
python voicestudio/voicestudio.py instalar
python voicestudio/voicestudio.py modelos
python content-engine/audio/doctor.py
```

- Os efeitos sonoros e as músicas de fundo já estão no repo: não precisam de instalação.
- A voz padrão é a `narradora`, no VoiceStudio, que roda nesta máquina. `instalar` baixa o VoiceStudio no commit fixado com as dependências travadas e `modelos` baixa os modelos de voz e de legenda (cerca de 8 GB de download; é o único passo pesado, e só é feito uma vez). Se o download for interrompido, rode `modelos --refazer`. O `modelos` aceita em seu nome as licenças dos modelos que baixa (OmniVoice, com pesos CC-BY-NC, de uso não comercial; o tokenizador de áudio Higgs; e o Whisper, MIT): leia-as antes de rodar.
- Sem essa instalação, o `audio/doctor.py` acusa `FAIL` no VoiceStudio, porque ele é o provedor de voz padrão; efeitos, música, trilha e o render do exemplo (que já vem narrado) funcionam mesmo assim.
- Alternativa leve, sem VoiceStudio: a voz local Kokoro (`python content-engine/audio/voz_setup.py` e `VOZ_PROVEDOR=kokoro` no `.env`). É mais robótica em português.

## Quickstart (5 minutos)

Vídeo de exemplo (1080x1920, 13,5 s, com narração na voz local do VoiceStudio (a voz de exemplo `narradora`), legenda palavra a palavra, música de fundo e efeitos sonoros). A narração e a legenda já vêm geradas na pasta do exemplo, então dá para renderizar sem instalar a voz:

```bash
python content-engine/audio/trilha.py examples/hello-world examples/hello-world/trilha.json
python content-engine/video/preview.py examples/hello-world
python content-engine/video/render.py examples/hello-world output/ola-mundo.mp4
python content-engine/video/frames.py output/ola-mundo.mp4 output/frames --n 6
```

- `trilha.py` copia os efeitos usados para `examples/hello-world/assets/sfx/`, mixa a música escolhida na chave `musica` em `assets/musica/base.wav` (abaixando sob a voz, quando há) e escreve os `<audio>` no `index.html` (o exemplo já vem com a trilha aplicada; rodar de novo dá o mesmo resultado).
- `preview.py` abre uma prévia no navegador (`http://127.0.0.1:4790`, Ctrl+C encerra) com tocar/pausar e linha do tempo, para acertar tempo e posição antes do render. É opcional e não substitui o render.
- `render.py` confere a composição, renderiza isolado e imprime resolução, duração, quantas faixas de áudio saíram e se houve tentativa de rede ou de leitura de arquivo bloqueada.
- `frames.py` extrai PNGs do vídeo para revisão.

> **Abrir o `index.html` direto no navegador não funciona:** as bibliotecas, as fontes e o kit de motion vêm de `_motor/`, que só existe na prévia e no render. Use o `preview.py` ou o `render.py`.

Imagem de exemplo (1080x1350):

```bash
python content-engine/image/render.py examples/card/cartao.html output/cartao.png --raiz examples/card
```

Narração de exemplo (depois do `voz_setup.py`):

```bash
python content-engine/audio/voz.py examples/narration/voz.txt --saida output/voz
```

Para criar a sua peça, copie `examples/hello-world/` e leia `content-engine/video/MOTOR.md` (seção "Como escrever uma composição"). Peça narrada ganha legenda palavra a palavra com `content-engine/audio/legenda.py` e `K.legenda` do kit de motion (seções "Legenda sincronizada" do `AUDIO.md` e do `MOTOR.md`).

## Mapa das pastas

```text
content-engine/
  video/      motor de vídeo: setup.py, doctor.py, render.py, frames.py, preview.py, MOTOR.md
    engines/hyperframes/   adaptador do HyperFrames, guardas de rede e de arquivos, guia de autoria
    kit/motion.js          kit de motion (chega à composição como _motor/kit/motion.js)
  image/     motor de imagem: setup.py, doctor.py, render.py, folha.py, MOTOR.md
  audio/      voz (voz.py, providers/), efeitos (sfx/), música (music/), trilha.py, legenda.py, AUDIO.md
  common/      o que os motores compartilham: navegador fixo, flags de isolamento, checagens
  fonts/     fontes woff2 locais (SIL OFL) com licenças e SHA-256
  tokens.json marcas: cores, fontes, logo, tom (vem com uma marca fictícia)
voicestudio/  instalador e wrapper da voz local VoiceStudio; voices/ traz só a voz de exemplo `narradora`
examples/     hello-world (vídeo), card (imagem), narration (texto de voz)
```

Documentação de contrato, por motor:

- Vídeo: `content-engine/video/MOTOR.md`
- Imagem: `content-engine/image/MOTOR.md`
- Áudio: `content-engine/audio/AUDIO.md`
- Autoria de composições: `content-engine/video/engines/hyperframes/guide/README.md`

## Garantias de localidade (resumo)

O detalhe e os limites estão nos `MOTOR.md`.

- O render de vídeo e de imagem roda sem rede: guarda de rede no Node, navegador com proxy sumidouro e resolução de nomes bloqueada, e checagem de URL externa antes de abrir o navegador.
- O motor só lê arquivos de dentro da pasta da peça, e só de tipos de uma lista fechada; um guarda de arquivos aborta o render se algo tentar ler fora.
- O processo do motor roda com ambiente filtrado (sem variáveis com cara de chave ou token) e com pasta de usuário falsa dentro do repo.
- Navegador, FFmpeg e pacotes npm têm versão fixa e SHA-256 conferido; telemetria e atualização automática desligadas.
- Dá para conferir: `prova-local.ps1` de cada motor renderiza monitorando processos e conexões.
- Nada é publicado nem enviado a lugar nenhum: a engine só gera arquivos locais.

## Voz

- **Local por padrão: VoiceStudio com a voz `narradora`.** Roda na CPU, offline, sem chave, na qualidade de 32 passos. A `narradora` é uma voz de exemplo criada por atributos (sem clonar ninguém), a mesma da narração do `examples/hello-world`. Para criar a sua (design por atributos ou clone de uma gravação autorizada), veja `voicestudio/voices/README.md`.
- **Kokoro (local, opcional).** Mais leve e de uso comercial livre (Apache-2.0), mas mais robótico em português: `voz_setup.py` e `VOZ_PROVEDOR=kokoro`.
- **Nuvem (opcional, com chave própria).** Azure AI Speech, Azure OpenAI gpt-audio e Google Cloud Text-to-Speech. As chaves ficam só em `content-engine/audio/.env` (modelo em `.env.example`, ignorado pelo git). Com provedor de nuvem, o texto da narração sai da máquina; o vídeo e os arquivos da peça não.

Detalhes em `content-engine/audio/AUDIO.md`.

## Licenças e terceiros

A licença do código próprio deste repo ainda não foi definida: veja `LICENCA-PENDENTE.md`. Componentes de terceiros:

- **HyperFrames** (motor de vídeo, pacote npm instalado pelo setup): Apache-2.0, Copyright HeyGen, Inc. O guia de autoria em `content-engine/video/engines/hyperframes/guide/` é uma adaptação modificada da documentação de skills do HyperFrames, redistribuída sob Apache-2.0 com atribuição (`guide/NOTICE.md` e `guide/LICENSE-APACHE-2.0.txt`).
- **GSAP** (instalado pelo setup, não incluído no repo): licença padrão "no charge" da GSAP (<https://gsap.com/standard-license>), que não é uma licença open source OSI. Leia os termos antes de usar.
- **Fontes** Inter, Montserrat e Press Start 2P (`content-engine/fonts/`): SIL Open Font License 1.1, textos em `LICENCA-*.txt`.
- **Efeitos sonoros** (`content-engine/audio/sfx/`): pacotes CC0 1.0 e síntese própria, origem de cada um em `sfx/LICENCAS.md`.
- **Música de fundo** (`content-engine/audio/music/`): 10 faixas CC0 1.0, origem de cada uma em `music/LICENCAS.md`.
- **FFmpeg** (baixado pelo setup, build essentials da gyan.dev): GPLv3.
- **chrome-headless-shell** (baixado pelo setup, Chrome for Testing do Google): termos do Chromium/Google.
- **Kokoro-82M** (voz local, baixado pelo `voz_setup.py`): modelo Apache-2.0; `kokoro-onnx` MIT.
- **VoiceStudio** (clonado pelo `voicestudio.py instalar`, não incluído no repo): AGPL-3.0.
- **Pesos do OmniVoice** (modelo usado pelo VoiceStudio): **CC-BY-NC, não comercial**.

> **Atenção, uso comercial:** a voz local do VoiceStudio usa os pesos do OmniVoice, cuja licença não permite uso comercial. Para peça comercial, use outro modelo ou provedor (por exemplo o Kokoro, Apache-2.0, ou um provedor de nuvem com chave própria e termos que permitam).

## Limites conhecidos

- Só Windows x64: os pins de navegador, FFmpeg e ferramentas são para Windows.
- O guarda de arquivos cobre a API `fs` do Node e os processos filhos; código nativo que abre arquivo por conta própria e referências dentro de containers de mídia não são inspecionados (ver "Limites conhecidos" em `content-engine/video/MOTOR.md`).
- A prova monitorada amostra conexões a cada ~100 ms: é evidência, não a barreira (a barreira são os guardas e as flags do navegador).
- O motor de imagem descobre a raiz dos assets pela convenção `projetos/<produto>/`; fora dela, passe `--raiz`.
- Voz local: o Kokoro em português pode soar robótico; o VoiceStudio na CPU é lento (dezenas de segundos por fala) e não pode ser usado comercialmente por causa dos pesos do OmniVoice.
- Provedores de nuvem não foram todos testados contra o serviço real (o adaptador do Google, por exemplo), e preços não fazem parte da engine.
- O guia de autoria do HyperFrames está em inglês e cita receitas que não acompanham o repo.
- A legenda sincronizada usa o Whisper do venv do VoiceStudio; sem ele, cai num modo aproximado (tempo repartido pelos trechos de fala).
- A engine não publica nem agenda: só gera arquivos locais.
