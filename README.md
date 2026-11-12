# vbss-media-engine

Engine local para gerar mídia a partir de HTML: vídeo (HTML + GSAP), imagem estática (HTML para PNG) e áudio (efeitos sonoros e narração). Tudo roda na sua máquina, sem nuvem obrigatória: o render não acessa a internet e só lê arquivos de dentro da pasta da peça.

Serve para qualquer conteúdo que caiba numa página: vídeo explicativo, vídeo curto vertical, cartão, slide de carrossel, capa. Você cria as suas próprias marcas e projetos; o repo traz só uma marca fictícia de exemplo.

## Requisitos

- Windows 10 ou 11 (x64). Os scripts baixam binários para Windows e a prova monitorada usa PowerShell.
- Python 3 (testado com 3.11; só biblioteca padrão, e a voz local Kokoro cria um venv próprio).
- Node.js 22 ou mais novo (motor de vídeo).
- Git (só para a voz local VoiceStudio, opcional).

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
python content-engine/audio/voz_setup.py
python content-engine/audio/doctor.py
```

- Os efeitos sonoros já estão no repo: não precisam de instalação.
- `voz_setup.py` só é necessário para narração com a voz local Kokoro (cria o venv e baixa o modelo, com hashes fixados).
- Sem o `voz_setup.py`, o `audio/doctor.py` acusa `FAIL` nos itens do Kokoro, porque ele é o provedor de voz padrão; efeitos e trilha funcionam mesmo assim.

## Quickstart (5 minutos)

Vídeo de exemplo (1080x1920, 8 s, com efeitos sonoros, sem voz):

```bash
python content-engine/audio/trilha.py examples/hello-world examples/hello-world/trilha.json
python content-engine/video/render.py examples/hello-world output/ola-mundo.mp4
python content-engine/video/frames.py output/ola-mundo.mp4 output/frames --n 6
```

- `trilha.py` copia os efeitos usados para `examples/hello-world/assets/sfx/` e escreve os `<audio>` no `index.html` (o exemplo já vem com a trilha aplicada; rodar de novo dá o mesmo resultado).
- `render.py` confere a composição, renderiza isolado e imprime resolução, duração, quantas faixas de áudio saíram e se houve tentativa de rede ou de leitura de arquivo bloqueada.
- `frames.py` extrai PNGs do vídeo para revisão.

Imagem de exemplo (1080x1350):

```bash
python content-engine/image/render.py examples/card/cartao.html output/cartao.png --raiz examples/card
```

Narração de exemplo (depois do `voz_setup.py`):

```bash
python content-engine/audio/voz.py examples/narration/voz.txt --saida output/voz
```

Para criar a sua peça, copie `examples/hello-world/` e leia `content-engine/video/MOTOR.md` (seção "Como escrever uma composição").

## Mapa das pastas

```text
content-engine/
  video/      motor de vídeo: setup.py, doctor.py, render.py, frames.py, MOTOR.md
    engines/hyperframes/   adaptador do HyperFrames, guardas de rede e de arquivos, guia de autoria
    kit/motion.js          kit de motion opcional (copiar para dentro da composição)
  image/     motor de imagem: setup.py, doctor.py, render.py, folha.py, MOTOR.md
  audio/      voz (voz.py, providers/), efeitos (sfx/), trilha.py, AUDIO.md
  common/      o que os motores compartilham: navegador fixo, flags de isolamento, checagens
  fonts/     fontes woff2 locais (SIL OFL) com licenças e SHA-256
  tokens.json marcas: cores, fontes, logo, tom (vem com uma marca fictícia)
voicestudio/  instalador e wrapper da voz local VoiceStudio; voices/ nasce vazia
examples/     ola-mundo (vídeo), cartao (imagem), narracao (texto de voz)
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

- **Local por padrão.** O provedor padrão é o Kokoro (`pf_dora`, pt-BR), que roda na CPU e funciona sem voz própria e sem chave.
- **VoiceStudio (local, opcional).** Voz mais natural, com voz criada por você (design por atributos ou clone de uma gravação autorizada). O repo não traz nenhuma voz: veja `voicestudio/voices/README.md`.
- **Nuvem (opcional, com chave própria).** Azure AI Speech, Azure OpenAI gpt-audio e Google Cloud Text-to-Speech. As chaves ficam só em `content-engine/audio/.env` (modelo em `.env.example`, ignorado pelo git). Com provedor de nuvem, o texto da narração sai da máquina; o vídeo e os arquivos da peça não.

Detalhes em `content-engine/audio/AUDIO.md`.

## Licenças e terceiros

A licença do código próprio deste repo ainda não foi definida: veja `LICENCA-PENDENTE.md`. Componentes de terceiros:

- **HyperFrames** (motor de vídeo, pacote npm instalado pelo setup): Apache-2.0, Copyright HeyGen, Inc. O guia de autoria em `content-engine/video/engines/hyperframes/guide/` é uma adaptação modificada da documentação de skills do HyperFrames, redistribuída sob Apache-2.0 com atribuição (`guide/NOTICE.md` e `guide/LICENSE-APACHE-2.0.txt`).
- **GSAP** (instalado pelo setup, não incluído no repo): licença padrão "no charge" da GSAP (<https://gsap.com/standard-license>), que não é uma licença open source OSI. Leia os termos antes de usar.
- **Fontes** Inter, Montserrat e Press Start 2P (`content-engine/fonts/`): SIL Open Font License 1.1, textos em `LICENCA-*.txt`.
- **Efeitos sonoros** (`content-engine/audio/sfx/`): CC0 1.0, origem de cada pacote em `sfx/LICENCAS.md`.
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
- A engine não publica, não agenda e não escolhe música.
