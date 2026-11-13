# Catálogo de música de fundo

Faixas instrumentais de fundo para Reels, geradas por `python content-engine/audio/musica_setup.py` a partir de fontes CC0 (licenças em `LICENCAS.md`). Este arquivo é gerado: para mudar a seleção, edite `content-engine/audio/musica_fontes.json` e rode o setup de novo.

- Formato: AAC em `.m4a`, 48000 Hz, estéreo, 160k. O `trilha.py` lê a faixa daqui e grava na composição só o `assets/musica/base.wav` já mixado.
- Nível: -16 LUFS integrado, pico real até -1,5 dBTP (o que vier primeiro).
- Laço: `sim` = a duração fecha compassos inteiros e a faixa repete no tempo; `não` = repete com fade nas pontas.
- BPM: medido por autocorrelação dos ataques (aproximado); serve para casar corte de cena com a batida.
- Uso no `trilha.json`: `"musica": {"faixa": "<id>"}`.
- Produtos: `todos` = serve para qualquer produto; os demais são sugestão, não regra.

## chiptune discreta

- `chiptune-selecao` (21,3 s, 90 bpm, laço: sim)
  - Uso: fundo 8-bit calmo para explicação ou passo a passo com tema de jogo; laço curto e sem emenda.
  - Produtos: todos.
  - Origem: [4 Chiptunes (Adventure)](https://opengameart.org/content/4-chiptunes-adventure), de Juhani Junkala (SubspaceAudio), CC0.

## synthwave

- `synthwave-noturna` (53,8 s, 107 bpm, laço: sim)
  - Uso: fundo retrô com batida constante; bom para vitrine de coleção e antes/depois.
  - Produtos: todos.
  - Origem: [Midnight Drive](https://opengameart.org/content/midnight-drive), de congusbongus, CC0.
- `synthwave-cidade` (58,4 s, 115 bpm, laço: sim)
  - Uso: fundo de sintetizador com cara de cidade futurista; serve para produto de tecnologia e para jogo retrô.
  - Produtos: todos.
  - Origem: [Space City](https://opengameart.org/content/space-city), de MintoDog, CC0.

## lo-fi

- `lofi-tranquila` (48,6 s, 79 bpm, laço: sim)
  - Uso: fundo lento e macio para narração longa, bastidor e tutorial.
  - Produtos: todos.
  - Origem: [Chill lofi inspired [loop edit]](https://opengameart.org/content/chill-lofi-inspired-loop-edit), de omfgdude (edição em loop de qubodup), CC0.
- `lofi-batida` (56,0 s, 120 bpm, laço: sim)
  - Uso: fundo lo-fi com batida de hip hop, um pouco mais presente; passo a passo e lista.
  - Produtos: todos.
  - Origem: [Lofi Hip Hop Loop](https://opengameart.org/content/lofi-hip-hop-loop), de omfgdude, CC0.

## eletrônico leve

- `eletronica-otimista` (59,1 s, 130 bpm, laço: sim)
  - Uso: fundo eletrônico claro e positivo para novidade de produto e demonstração de recurso.
  - Produtos: todos.
  - Origem: [Optomistic Day Mastered (Loopable)](https://opengameart.org/content/optomistic-day-mastered-loopable), de Pro Sensory, CC0.

## ambiente calmo

- `ambiente-contemplacao` (60,0 s, sem pulso marcado, laço: não)
  - Uso: cama de ambiente sem melodia nem batida marcada; para peça em que só a voz importa.
  - Produtos: todos.
  - Origem: [Contemplation](https://opengameart.org/content/contemplation-0), de Joth, CC0.
- `ambiente-calma` (19,2 s, 100 bpm, laço: sim)
  - Uso: laço curto e relaxado para peça tranquila de até uns 40 s (repete a cada 19 s).
  - Produtos: todos.
  - Origem: [Calm Loop](https://opengameart.org/content/calm-loop), de wipics, CC0.

## animada

- `chiptune-aventura` (41,1 s, 140 bpm, laço: sim)
  - Uso: chiptune de fase de plataforma, alegre e grudento; para peça animada de jogo, meme e contagem.
  - Produtos: todos.
  - Origem: [4 Chiptunes (Adventure)](https://opengameart.org/content/4-chiptunes-adventure), de Juhani Junkala (SubspaceAudio), CC0.
- `animada-palmas` (17,4 s, 110,1 bpm, laço: sim)
  - Uso: laço curto e alegre para peça leve e divertida (repete a cada 17 s).
  - Produtos: todos.
  - Origem: [Happy Clappy Loop](https://opengameart.org/content/happy-clappy-loop), de OwlishMedia, CC0.
