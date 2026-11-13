# Licenças dos efeitos sonoros

Os efeitos de `content-engine/audio/sfx/` têm duas origens, as duas livres para peça comercial, sem pedir permissão e sem obrigação de crédito:

- **Pacotes CC0 1.0 Universal** (dedicação ao domínio público): podem ser usados, editados, cortados e redistribuídos. A licença de cada pacote foi conferida na página de origem (selo "CC0" na página e, nos pacotes da Kenney, o `License.txt` dentro do zip): os pacotes da biblioteca clássica em 08/10/2026, os dois acrescentados para o conjunto cine em 12/11/2026.
- **Síntese própria**: som gerado do zero por `content-engine/audio/sfx_sintese.py` (ruído, senoides, filtros e sala calculados em código, semente fixa). Não há material de terceiros nem licença de terceiros; o resultado é do repositório. Algumas receitas tratam uma gravação CC0 como camada, e essa gravação está registrada na origem do efeito.

Texto legal da CC0 1.0: <https://creativecommons.org/publicdomain/zero/1.0/legalcode> (resumo em português: <https://creativecommons.org/publicdomain/zero/1.0/deed.pt-br>).

## Pacotes usados

- **Kenney** (Kenney Vleugels, kenney.nl), CC0, conforme o `License.txt` de cada zip ("This content is free to use in personal, educational and commercial projects"; crédito opcional):
  - Interface Sounds: <https://kenney.nl/assets/interface-sounds>
  - UI Audio: <https://kenney.nl/assets/ui-audio>
  - Digital Audio: <https://kenney.nl/assets/digital-audio>
  - Impact Sounds: <https://kenney.nl/assets/impact-sounds>
  - Music Jingles: <https://kenney.nl/assets/music-jingles>
  - Sci-fi Sounds: <https://kenney.nl/assets/sci-fi-sounds>
  - Casino Audio: <https://kenney.nl/assets/casino-audio> (camada de `swish-cine-papel`, `tique-cine-ficha` e `clique-cine-toque`)
  - RPG Audio (<https://kenney.nl/assets/rpg-audio>): fixado em `sfx_fontes.json` com SHA-256, sem efeito na seleção atual (o setup só baixa pacotes usados; fica pronto para a próxima curadoria).
- **512 Sound Effects (8-bit style)**, de Juhani Junkala, publicado por SubspaceAudio no OpenGameArt, CC0: <https://opengameart.org/content/512-sound-effects-8-bit-style>. O `INFO.txt` do pacote diz: "These sound effects have been released under CC0 creative commons license. You can do anything you want with these sounds."
- **Swishes Sound Pack**, de artisticdude, OpenGameArt, CC0: <https://opengameart.org/content/swishes-sound-pack>
- **Keyboard Soundpack #1 [Typing and Single Keystrokes]**, de unicaegames, OpenGameArt, CC0: <https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes>. O `readme.txt` do pacote diz: "Free to use however you like."
- **100 CC0 SFX**, de rubberduck, OpenGameArt, CC0: <https://opengameart.org/content/100-cc0-sfx>
- **Muffled Distant Explosion**, de NenadSimic, OpenGameArt, CC0: <https://opengameart.org/content/muffled-distant-explosion> (camada de cauda do `impacto-cine-forte`)
- **Wind, hit, time morph**, de qubodup, OpenGameArt, CC0: <https://opengameart.org/content/wind-hit-time-morph> (camada do `whoosh-cine-corpo`)

URL exata de cada arquivo e o SHA-256 conferido no download: `content-engine/audio/sfx_fontes.json`. Origem de cada efeito (pacote e arquivo, ou receita de síntese e camadas): `sfx.json` e `CATALOGO.md`.

## Síntese própria

Os efeitos do conjunto cine marcados como "síntese própria" no catálogo saem de `sfx_sintese.py` e de mais nada. Os marcados como "síntese própria sobre gravação de ..." partem de uma gravação CC0 dos pacotes acima (Casino Audio, Keyboard Soundpack #1, Muffled Distant Explosion, Wind, hit, time morph), tratada e somada a camadas sintetizadas.

## Crédito (opcional)

CC0 não exige crédito. Quando houver espaço (descrição de vídeo longo, página de créditos), a forma curta é: "Efeitos sonoros: Kenney (kenney.nl), Juhani Junkala, artisticdude, unicaegames, rubberduck, NenadSimic e qubodup (OpenGameArt), CC0."

## Regra para efeito novo

Só entra efeito de síntese própria ou de pacote com licença CC0 conferida na página de origem, baixado de URL fixa com SHA-256 registrado em `sfx_fontes.json`. Licença com exigência de atribuição (CC-BY), uso não comercial (NC) ou "royalty free" sem texto claro fica de fora.
