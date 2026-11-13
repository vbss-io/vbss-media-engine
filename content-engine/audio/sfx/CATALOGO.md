# Catálogo de efeitos sonoros

Efeitos curtos para Reels de todos os produtos, gerados por `python content-engine/audio/sfx_setup.py` (licenças em `LICENCAS.md`). Este arquivo é gerado: para mudar a seleção, edite `content-engine/audio/sfx_selecao.json` e rode o setup de novo.

- Formato: WAV PCM 16 bits, 48000 Hz, mono, pico real até -1 dBTP, sem clique nas pontas.
- Dois conjuntos: o **cine** (pós-produção: corpo, cauda, subgrave e um pouco de sala) é o padrão para peça nova; a **biblioteca clássica** (interface e jogo, seca) continua valendo para tema retrô e para as composições antigas.
- Âncora: o instante, dentro do arquivo, que cai em cima do movimento (pico do whoosh, fim do riser, impacto da transição pronta). A deixa vai em `t = momento do movimento - âncora`. Efeito sem âncora começa no instante 0: a deixa é o próprio momento.
- Nível do conjunto cine: fixado por família para `volume` 1.0 já servir sem voz (impacto mais alto que whoosh, whoosh mais alto que tique). Com voz, use de 0.4 a 0.7. Medidas de cada arquivo em `sfx.json`.
- Nível da biblioteca clássica: pico de loudness momentânea em -16 LUFS e pico real até -1 dBTP (o que vier primeiro).
- Para ouvir todos em sequência com o nome na tela: `sfx/catalogo.mp4` (refazer com `python content-engine/audio/catalogo_audio.py`).
- Produtos: sem indicação = serve para qualquer produto; os listados são sugestão, não regra.

## Conjunto cine (pós-produção)

### whoosh

- `whoosh/whoosh-cine-curto.wav` - 0,49 s, âncora 0,12 s. Quando usar: elemento que entra rápido (texto, card, ícone); âncora no instante em que ele assenta. Origem: síntese própria.
- `whoosh/whoosh-cine-medio.wav` - 0,75 s, âncora 0,26 s. Quando usar: troca de batida ou painel que desliza; o padrão para entrada de cena. Origem: síntese própria.
- `whoosh/whoosh-cine-longo.wav` - 1,35 s, âncora 0,60 s. Quando usar: movimento longo: zoom, câmera ou cena que atravessa a tela. Origem: síntese própria.
- `whoosh/whoosh-cine-grave.wav` - 0,93 s, âncora 0,34 s. Quando usar: objeto grande ou título pesado passando; aparece inteiro em fone ou caixa. Origem: síntese própria.
- `whoosh/whoosh-cine-agudo.wav` - 0,54 s, âncora 0,17 s. Quando usar: detalhe leve e veloz (ícone, linha, cursor); cabe por cima da voz em volume baixo. Origem: síntese própria.
- `whoosh/whoosh-cine-cauda.wav` - 1,26 s, âncora 0,20 s. Quando usar: último movimento antes de uma pausa: a sala segura o silêncio depois. Origem: síntese própria.
- `whoosh/whoosh-cine-corpo.wav` - 0,71 s, âncora 0,19 s. Quando usar: passada com peso de objeto real: print ou produto que cruza a tela. Origem: síntese própria sobre gravação de [Wind, hit, time morph](https://opengameart.org/content/wind-hit-time-morph), `qubodup-megaswosh1.wav`, CC0.

### transition

- `transition/swish-cine-leve.wav` - 0,32 s, âncora 0,08 s. Quando usar: corte leve entre dois planos parecidos, troca de aba, item de lista. Origem: síntese própria.
- `transition/swish-cine-papel.wav` - 0,42 s, âncora 0,12 s. Quando usar: card, foto ou página que desliza; som de papel real, discreto. Origem: síntese própria sobre gravação de [Casino Audio (Kenney)](https://kenney.nl/assets/casino-audio), `card-slide-4.ogg`, CC0.
- `transition/transicao-cine.wav` - 1,69 s, âncora 0,75 s. Quando usar: corte principal entre batidas, pronto: sobe, passa e assenta no corte. Origem: síntese própria.
- `transition/transicao-cine-forte.wav` - 2,57 s, âncora 1,20 s. Quando usar: virada do Reel (do gancho para a revelação): reverso, riser, impacto e brilho já alinhados. Origem: síntese própria.
- `transition/transicao-cine-suave.wav` - 0,75 s, âncora 0,26 s. Quando usar: corte calmo: passada com um toque grave no ponto, sem subgrave. Origem: síntese própria.

### impact

- `impact/impacto-cine-macio.wav` - 0,94 s. Quando usar: elemento que assenta, título no frame 0, ponto final de um whoosh. Origem: síntese própria.
- `impact/impacto-cine-medio.wav` - 1,37 s. Quando usar: revelação de número ou título forte; o padrão para o corte principal. Origem: síntese própria.
- `impact/impacto-cine-forte.wav` - 2,21 s. Quando usar: um por Reel: o momento de maior peso (resultado, antes e depois). Origem: síntese própria sobre gravação de [Muffled Distant Explosion](https://opengameart.org/content/muffled-distant-explosion), `NenadSimic - Muffled Distant Explosion.wav`, CC0.
- `impact/impacto-cine-sub.wav` - 1,85 s. Quando usar: peso por baixo de outro efeito; sozinho quase some no alto-falante do celular. Origem: síntese própria.
- `impact/braam-cine-leve.wav` - 2,28 s. Quando usar: abertura ou virada dramática, tom de trailer; no máximo um por peça. Origem: síntese própria.

### riser

- `riser/riser-cine-meio.wav` - 0,55 s, âncora 0,50 s. Quando usar: meio segundo de tensão antes do corte; termina no corte. Origem: síntese própria.
- `riser/riser-cine-1s.wav` - 1,04 s, âncora 1,00 s. Quando usar: preparar a revelação (número, resultado) por um segundo. Origem: síntese própria.
- `riser/riser-cine-2s.wav` - 2,04 s, âncora 2,00 s. Quando usar: espera longa antes do ponto alto da peça. Origem: síntese própria.
- `riser/reverso-cine-curto.wav` - 0,51 s, âncora 0,50 s. Quando usar: puxada rápida para dentro do corte; antes de impacto ou pop. Origem: síntese própria.
- `riser/reverso-cine-longo.wav` - 1,21 s, âncora 1,20 s. Quando usar: entrada do logo ou do fecho: cresce e para no ponto. Origem: síntese própria.

### tick

- `tick/tique-cine-macio.wav` - 0,15 s. Quando usar: passo de contagem ou item de lista que marca, um por vez (0,08 s ou mais entre eles). Origem: síntese própria.
- `tick/tique-cine-ficha.wav` - 0,14 s. Quando usar: tique com textura real: seleção, alternância, passo de carrossel. Origem: síntese própria sobre gravação de [Casino Audio (Kenney)](https://kenney.nl/assets/casino-audio), `chip-lay-1.ogg`, CC0.

### click

- `click/clique-cine-abafado.wav` - 0,16 s. Quando usar: botão ou campo tocado no print; não compete com a voz. Origem: síntese própria.
- `click/clique-cine-toque.wav` - 0,28 s. Quando usar: dedo tocando a tela ou um card; mais corpo que o clique. Origem: síntese própria sobre gravação de [Casino Audio (Kenney)](https://kenney.nl/assets/casino-audio), `chip-lay-3.ogg`, CC0.

### pop

- `pop/pop-cine-redondo.wav` - 0,35 s. Quando usar: selo, etiqueta, emoji ou balão que salta. Origem: síntese própria.
- `pop/pop-cine-grave.wav` - 0,43 s. Quando usar: elemento maior que salta (card, moldura, foto). Origem: síntese própria.

### shine

- `shine/brilho-cine-curto.wav` - 1,14 s. Quando usar: destaque que acende: preço, selo, palavra-chave revelada. Origem: síntese própria.
- `shine/brilho-cine-longo.wav` - 2,32 s. Quando usar: revelação com respiro: resultado final, logo, antes e depois. Origem: síntese própria.
- `shine/brilho-cine-sobe.wav` - 1,58 s, âncora 0,45 s. Quando usar: número ou imagem que se forma aos poucos; a âncora é a última nota. Origem: síntese própria.

### success

- `success/sucesso-cine-discreto.wav` - 1,29 s. Quando usar: tarefa concluída, check, resposta do produto, sem cara de jogo. Origem: síntese própria.
- `success/sucesso-cine-acorde.wav` - 2,07 s. Quando usar: fecho da peça com logo ou chamada, depois da última fala. Origem: síntese própria.

### counter

- `counter/contador-cine-macio.wav` - 1,41 s. Quando usar: número contando por baixo; aparar com `duracao` no tamanho da contagem. Origem: síntese própria.
- `counter/contador-cine-fecho.wav` - 1,99 s, âncora 0,98 s. Quando usar: contagem que desacelera e para numa nota; âncora no valor final. Origem: síntese própria.

### typing

- `typing/digitacao-cine-suave.wav` - 1,98 s. Quando usar: busca ou prompt sendo digitado; aparar com `duracao`. Origem: síntese própria sobre gravação de [Keyboard Soundpack #1 [Typing and Single Keystrokes]](https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes), `human_vel-003.wav`, CC0.

### notification

- `notification/notificacao-cine-limpa.wav` - 0,89 s. Quando usar: aviso, mensagem ou alerta que chega no print. Origem: síntese própria.

## Combinações recomendadas

- **Entrada de cena:** `whoosh/whoosh-cine-medio` com a âncora no frame em que o elemento assenta e `impact/impacto-cine-macio` no mesmo frame (volume 0.7). Elemento pequeno: `whoosh/whoosh-cine-curto` sozinho. Título pesado: troque o impacto por `impact/impacto-cine-medio`.
- **Corte:** `transition/transicao-cine` com a âncora no corte (deixa em `corte - 0,75`). Montado à mão: `riser/riser-cine-meio` terminando no corte, `whoosh/whoosh-cine-curto` e `impact/impacto-cine-macio` no corte. Corte leve: `transition/swish-cine-leve` ou `transition/transicao-cine-suave`.
- **Revelar número:** `counter/contador-cine-macio` enquanto conta (volume 0.5, aparado com `duracao`), `riser/riser-cine-1s` terminando na parada, e no valor final `impact/impacto-cine-medio` com `shine/brilho-cine-curto`. Versão curta: `counter/contador-cine-fecho` com a âncora no valor final.
- **Toque de UI:** `click/clique-cine-abafado` no aperto, `pop/pop-cine-redondo` no elemento que aparece e `success/sucesso-cine-discreto` na resposta do produto. Lista que marca: `tick/tique-cine-macio` em cada item.
- **Fecho:** `riser/reverso-cine-longo` terminando na entrada do logo, `impact/impacto-cine-macio` e `shine/brilho-cine-longo` no logo; ou só `success/sucesso-cine-acorde` depois da última fala (nunca por baixo dela).

## Biblioteca clássica (interface e jogo)

### whoosh

- `whoosh/whoosh-rapido.wav` - 0,09 s. Quando usar: corte seco entre batidas, entrada rápida de texto lateral. Origem: [Swishes Sound Pack](https://opengameart.org/content/swishes-sound-pack), `swish-4.wav`, CC0.
- `whoosh/whoosh-rapido-agudo.wav` - 0,11 s. Quando usar: troca de batida curta, elemento que cruza a tela. Origem: [Swishes Sound Pack](https://opengameart.org/content/swishes-sound-pack), `swish-9.wav`, CC0.
- `whoosh/whoosh-sobe.wav` - 0,50 s. Quando usar: cresce até o corte: colocar terminando no início da batida nova. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `maximize_005.ogg`, CC0.
- `whoosh/whoosh-desce.wav` - 0,50 s. Quando usar: saída de cena, elemento que encolhe ou sai. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `minimize_005.ogg`, CC0.
- `whoosh/whoosh-portal-8bit.wav` - 0,88 s. Quando usar: transição com cara de videogame entre batidas. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_movement_portal5.wav`, CC0.

### click

- `click/clique-mouse.wav` - 0,05 s. Quando usar: cursor clicando num botão ou campo do print. Origem: [UI Audio (Kenney)](https://kenney.nl/assets/ui-audio), `mouseclick1.ogg`, CC0.
- `click/clique-seco.wav` - 0,03 s. Quando usar: clique discreto em cada linha de texto que entra. Origem: [UI Audio (Kenney)](https://kenney.nl/assets/ui-audio), `click3.ogg`, CC0.
- `click/clique-interface.wav` - 0,01 s. Quando usar: botão do produto sendo apertado. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `click_001.ogg`, CC0.
- `click/clique-botao-8bit.wav` - 0,15 s. Quando usar: botão apertado em peça com tema retrô ou game. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_button3.wav`, CC0.

### pop

- `pop/pop-gota.wav` - 0,19 s. Quando usar: etiqueta, selo ou card que salta na tela. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `drop_002.ogg`, CC0.
- `pop/pop-gota-grave.wav` - 0,13 s. Quando usar: elemento maior que assenta (título, moldura). Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `drop_004.ogg`, CC0.
- `pop/pop-bolha.wav` - 0,14 s. Quando usar: ícone ou emoji que aparece, tom leve. Origem: [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx), `plop_02.ogg`, CC0.
- `pop/pop-blip-8bit.wav` - 0,12 s. Quando usar: texto ou item que entra em peça retrô. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_Blip5.wav`, CC0.

### success

- `success/sucesso-confirmacao.wav` - 0,51 s. Quando usar: resultado pronto, tarefa concluída. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `confirmation_002.ogg`, CC0.
- `success/sucesso-confirmacao-curta.wav` - 0,28 s. Quando usar: check discreto, item marcado. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `confirmation_001.ogg`, CC0.
- `success/sucesso-powerup-8bit.wav` - 0,74 s. Quando usar: conquista, nível, desbloqueio. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_powerup2.wav`, CC0.
- `success/sucesso-fanfarra-8bit.wav` - 0,52 s. Quando usar: revelação do resultado (valor, prêmio). Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_fanfare1.wav`, CC0.
- `success/sucesso-tres-tons.wav` - 0,49 s. Quando usar: resultado digital, geração concluída. Origem: [Digital Audio (Kenney)](https://kenney.nl/assets/digital-audio), `threeTone1.ogg`, CC0.

### coin-8bit

- `coin-8bit/moeda-8bit-simples.wav` - 0,42 s. Quando usar: um valor que aparece na tela. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_single1.wav`, CC0.
- `coin-8bit/moeda-8bit-curta.wav` - 0,46 s. Quando usar: preço ou número pequeno destacado. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_single6.wav`, CC0.
- `coin-8bit/moeda-8bit-dupla.wav` - 0,33 s. Quando usar: faixa de preço (dois valores). Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_double2.wav`, CC0.
- `coin-8bit/moeda-8bit-chuva.wav` - 0,68 s. Quando usar: número que termina de contar, ganho grande. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_coin_cluster5.wav`, CC0.

### counter

- `counter/contador-tique.wav` - 0,06 s. Quando usar: um tique por passo da contagem (repetir a cada 0,08 s). Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `tick_004.ogg`, CC0.
- `counter/contador-blip-8bit.wav` - 0,05 s. Quando usar: contagem com cara de game, cursor de menu. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_menu_move5.wav`, CC0.
- `counter/contador-rolagem.wav` - 1,00 s. Quando usar: número rolando ou lista passando (1 s). Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `scroll_002.ogg`, CC0.

### impact

- `impact/impacto-soco.wav` - 0,44 s. Quando usar: título pesado que bate na tela, gancho forte. Origem: [Impact Sounds (Kenney)](https://kenney.nl/assets/impact-sounds), `impactPunch_heavy_000.ogg`, CC0.
- `impact/impacto-macio.wav` - 0,50 s. Quando usar: bloco que assenta com peso, sem agressividade. Origem: [Impact Sounds (Kenney)](https://kenney.nl/assets/impact-sounds), `impactSoft_heavy_000.ogg`, CC0.
- `impact/impacto-metal.wav` - 0,36 s. Quando usar: ferramenta, obra, bancada. Origem: [Impact Sounds (Kenney)](https://kenney.nl/assets/impact-sounds), `impactMetal_heavy_001.ogg`, CC0.
- `impact/impacto-explosao-8bit.wav` - 0,24 s. Quando usar: revelação surpresa em peça retrô. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_exp_shortest_soft6.wav`, CC0.

### typing

- `typing/digitacao-tecla.wav` - 0,15 s. Quando usar: uma tecla por letra que aparece (repetir). Origem: [Keyboard Soundpack #1 [Typing and Single Keystrokes]](https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes), `keypress-006.wav`, CC0.
- `typing/digitacao-tecla-leve.wav` - 0,15 s. Quando usar: alternar com digitacao-tecla para não soar repetido. Origem: [Keyboard Soundpack #1 [Typing and Single Keystrokes]](https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes), `keypress-004.wav`, CC0.
- `typing/digitacao-sequencia.wav` - 1,90 s. Quando usar: busca ou prompt sendo digitado (2 s; usar data-duration para encurtar). Origem: [Keyboard Soundpack #1 [Typing and Single Keystrokes]](https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes), `generated-006_faster.wav`, CC0.

### notification

- `notification/notificacao-sino.wav` - 0,36 s. Quando usar: alerta, aviso, chegada de mensagem. Origem: [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx), `bell_02.ogg`, CC0.
- `notification/notificacao-vidro.wav` - 0,23 s. Quando usar: destaque discreto, dica que aparece. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `glass_001.ogg`, CC0.
- `notification/notificacao-pergunta.wav` - 0,48 s. Quando usar: pergunta do gancho, lacuna aberta (R$ ???). Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `question_001.ogg`, CC0.

### error

- `error/erro-interface.wav` - 0,20 s. Quando usar: o jeito errado, o antes, o problema. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `error_006.ogg`, CC0.
- `error/erro-8bit.wav` - 0,33 s. Quando usar: erro ou perda em peça retrô. Origem: [512 Sound Effects (8-bit style)](https://opengameart.org/content/512-sound-effects-8-bit-style), `sfx_sounds_error5.wav`, CC0.

### glitch

- `glitch/glitch-estalo.wav` - 0,03 s. Quando usar: corte com falha digital, troca brusca. Origem: [Interface Sounds (Kenney)](https://kenney.nl/assets/interface-sounds), `glitch_002.ogg`, CC0.
- `glitch/glitch-fase.wav` - 0,35 s. Quando usar: imagem que se transforma, antes e depois. Origem: [Digital Audio (Kenney)](https://kenney.nl/assets/digital-audio), `phaseJump3.ogg`, CC0.
- `glitch/glitch-ruido-digital.wav` - 0,80 s. Quando usar: IA processando, tela carregando (0,8 s). Origem: [Sci-fi Sounds (Kenney)](https://kenney.nl/assets/sci-fi-sounds), `computerNoise_000.ogg`, CC0.

### jingle

- `jingle/jingle-8bit-fecho.wav` - 1,68 s. Quando usar: fecho com logo em peça retrô. Origem: [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_NES00.ogg`, CC0.
- `jingle/jingle-8bit-curto.wav` - 0,99 s. Quando usar: fecho curto, pedido final. Origem: [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_NES13.ogg`, CC0.
- `jingle/jingle-pizzicato.wav` - 1,14 s. Quando usar: fecho leve e simpático. Origem: [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_PIZZI03.ogg`, CC0.
- `jingle/jingle-steel.wav` - 1,36 s. Quando usar: fecho caloroso, tom de produto pronto. Origem: [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_STEEL01.ogg`, CC0.
- `jingle/jingle-sax.wav` - 1,68 s. Quando usar: fecho com humor. Origem: [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_SAX07.ogg`, CC0.
- `jingle/jingle-hit.wav` - 1,11 s. Quando usar: fecho moderno e seco. Origem: [Music Jingles (Kenney)](https://kenney.nl/assets/music-jingles), `jingles_HIT15.ogg`, CC0.
