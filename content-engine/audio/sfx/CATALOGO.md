# Catálogo de efeitos sonoros

Efeitos curtos para Reels de todos os produtos, gerados por `python content-engine/audio/sfx_setup.py` a partir de pacotes CC0 (licenças em `LICENCAS.md`). Este arquivo é gerado: para mudar a seleção, edite `content-engine/audio/sfx_selecao.json` e rode o setup de novo.

- Formato: WAV PCM 16 bits, 48000 Hz, mono. Silêncio do começo cortado: o som começa no instante 0 do arquivo, então o `data-start` do `<audio>` é o momento exato do efeito.
- Nível: pico de loudness momentânea em -16 LUFS e pico real até -1 dBTP (o que vier primeiro). Efeito com pico alto e corpo curto fica um pouco abaixo do alvo, de propósito, para não saturar.
- Para ouvir todos em sequência com o nome na tela: `sfx/catalogo.mp4` (refazer com `python content-engine/audio/catalogo_audio.py`).
- Produtos: `todos` = serve para qualquer produto; os demais são sugestão, não regra.

## whoosh

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `whoosh/whoosh-rapido.wav` | 0,09 s | corte seco entre batidas, entrada rápida de texto lateral | todos | [Swishes Sound Pack](https://opengameart.org/content/swishes-sound-pack), `swish-4.wav`, CC0 |
| `whoosh/whoosh-rapido-agudo.wav` | 0,11 s | troca de batida curta, elemento que cruza a tela | todos | [Swishes Sound Pack](https://opengameart.org/content/swishes-sound-pack), `swish-9.wav`, CC0 |
| `whoosh/whoosh-sobe.wav` | 0,50 s | cresce até o corte: colocar terminando no início da batida nova | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `maximize_005.ogg`, CC0 |
| `whoosh/whoosh-desce.wav` | 0,50 s | saída de cena, elemento que encolhe ou sai | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `minimize_005.ogg`, CC0 |
| `whoosh/whoosh-portal-8bit.wav` | 0,88 s | transição com cara de videogame entre batidas | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_movement_portal5.wav`, CC0 |

## click

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `click/clique-mouse.wav` | 0,05 s | cursor clicando num botão ou campo do print | todos | [UI Audio (Kenney)](https://kenney.nl/assets/ui-audio), `mouseclick1.ogg`, CC0 |
| `click/clique-seco.wav` | 0,03 s | clique discreto em cada linha de texto que entra | todos | [UI Audio (Kenney)](https://kenney.nl/assets/ui-audio), `click3.ogg`, CC0 |
| `click/clique-interface.wav` | 0,01 s | botão do produto sendo apertado | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `click_001.ogg`, CC0 |
| `click/clique-botao-8bit.wav` | 0,15 s | botão apertado em peça com tema retrô ou game | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_button3.wav`, CC0 |

## pop

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `pop/pop-gota.wav` | 0,19 s | etiqueta, selo ou card que salta na tela | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `drop_002.ogg`, CC0 |
| `pop/pop-gota-grave.wav` | 0,13 s | elemento maior que assenta (título, moldura) | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `drop_004.ogg`, CC0 |
| `pop/pop-bolha.wav` | 0,14 s | ícone ou emoji que aparece, tom leve | todos | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx), `plop_02.ogg`, CC0 |
| `pop/pop-blip-8bit.wav` | 0,12 s | texto ou item que entra em peça retrô | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_Blip5.wav`, CC0 |

## success

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `success/sucesso-confirmacao.wav` | 0,51 s | resultado pronto, tarefa concluída | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `confirmation_002.ogg`, CC0 |
| `success/sucesso-confirmacao-curta.wav` | 0,28 s | check discreto, item marcado | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `confirmation_001.ogg`, CC0 |
| `success/sucesso-powerup-8bit.wav` | 0,74 s | conquista, nível, desbloqueio | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_powerup2.wav`, CC0 |
| `success/sucesso-fanfarra-8bit.wav` | 0,52 s | revelação do resultado (valor, prêmio) | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_fanfare1.wav`, CC0 |
| `success/sucesso-tres-tons.wav` | 0,49 s | resultado digital, geração concluída | todos | [Digital Audio (Kenney)](https://kenney.nl/assets/digital-audio), `threeTone1.ogg`, CC0 |

## coin-8bit

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `coin-8bit/moeda-8bit-simples.wav` | 0,42 s | um valor que aparece na tela | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_single1.wav`, CC0 |
| `coin-8bit/moeda-8bit-curta.wav` | 0,46 s | preço ou número pequeno destacado | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_single6.wav`, CC0 |
| `coin-8bit/moeda-8bit-dupla.wav` | 0,33 s | faixa de preço (dois valores) | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_double2.wav`, CC0 |
| `coin-8bit/moeda-8bit-chuva.wav` | 0,68 s | número que termina de contar, ganho grande | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_cluster5.wav`, CC0 |

## counter

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `counter/contador-tique.wav` | 0,06 s | um tique por passo da contagem (repetir a cada 0,08 s) | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `tick_004.ogg`, CC0 |
| `counter/contador-blip-8bit.wav` | 0,05 s | contagem com cara de game, cursor de menu | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_menu_move5.wav`, CC0 |
| `counter/contador-rolagem.wav` | 1,00 s | número rolando ou lista passando (1 s) | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `scroll_002.ogg`, CC0 |

## impact

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `impact/impacto-soco.wav` | 0,44 s | título pesado que bate na tela, gancho forte | todos | [Impact Sounds (Kenney)](https://kenney.nl/assets/impact-sounds), `impactPunch_heavy_000.ogg`, CC0 |
| `impact/impacto-macio.wav` | 0,50 s | bloco que assenta com peso, sem agressividade | todos | [Impact Sounds (Kenney)](https://kenney.nl/assets/impact-sounds), `impactSoft_heavy_000.ogg`, CC0 |
| `impact/impacto-metal.wav` | 0,36 s | ferramenta, obra, bancada | todos | [Impact Sounds (Kenney)](https://kenney.nl/assets/impact-sounds), `impactMetal_heavy_001.ogg`, CC0 |
| `impact/impacto-explosao-8bit.wav` | 0,24 s | revelação surpresa em peça retrô | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_exp_shortest_soft6.wav`, CC0 |

## typing

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `typing/digitacao-tecla.wav` | 0,15 s | uma tecla por letra que aparece (repetir) | todos | [Keyboard Soundpack #1 [Typing and Single Keystrokes]](https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes), `keypress-006.wav`, CC0 |
| `typing/digitacao-tecla-leve.wav` | 0,15 s | alternar com digitacao-tecla para não soar repetido | todos | [Keyboard Soundpack #1 [Typing and Single Keystrokes]](https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes), `keypress-004.wav`, CC0 |
| `typing/digitacao-sequencia.wav` | 1,90 s | busca ou prompt sendo digitado (2 s; usar data-duration para encurtar) | todos | [Keyboard Soundpack #1 [Typing and Single Keystrokes]](https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes), `generated-006_faster.wav`, CC0 |

## notification

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `notification/notificacao-sino.wav` | 0,36 s | alerta, aviso, chegada de mensagem | todos | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx), `bell_02.ogg`, CC0 |
| `notification/notificacao-vidro.wav` | 0,23 s | destaque discreto, dica que aparece | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `glass_001.ogg`, CC0 |
| `notification/notificacao-pergunta.wav` | 0,48 s | pergunta do gancho, lacuna aberta (R$ ???) | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `question_001.ogg`, CC0 |

## error

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `error/erro-interface.wav` | 0,20 s | o jeito errado, o antes, o problema | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `error_006.ogg`, CC0 |
| `error/erro-8bit.wav` | 0,33 s | erro ou perda em peça retrô | todos | [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_error5.wav`, CC0 |

## glitch

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `glitch/glitch-estalo.wav` | 0,03 s | corte com falha digital, troca brusca | todos | [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `glitch_002.ogg`, CC0 |
| `glitch/glitch-fase.wav` | 0,35 s | imagem que se transforma, antes e depois | todos | [Digital Audio (Kenney)](https://kenney.nl/assets/digital-audio), `phaseJump3.ogg`, CC0 |
| `glitch/glitch-ruido-digital.wav` | 0,80 s | IA processando, tela carregando (0,8 s) | todos | [Sci-fi Sounds (Kenney)](https://kenney.nl/assets/sci-fi-sounds), `computerNoise_000.ogg`, CC0 |

## jingle

| Arquivo | Duração | Uso sugerido | Produtos | Origem |
| --- | --- | --- | --- | --- |
| `jingle/jingle-8bit-fecho.wav` | 1,68 s | fecho com logo em peça retrô | todos | [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_NES00.ogg`, CC0 |
| `jingle/jingle-8bit-curto.wav` | 0,99 s | fecho curto, pedido final | todos | [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_NES13.ogg`, CC0 |
| `jingle/jingle-pizzicato.wav` | 1,14 s | fecho leve e simpático | todos | [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_PIZZI03.ogg`, CC0 |
| `jingle/jingle-steel.wav` | 1,36 s | fecho caloroso, tom de produto pronto | todos | [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_STEEL01.ogg`, CC0 |
| `jingle/jingle-sax.wav` | 1,68 s | fecho com humor | todos | [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_SAX07.ogg`, CC0 |
| `jingle/jingle-hit.wav` | 1,11 s | fecho moderno e seco | todos | [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_HIT15.ogg`, CC0 |
