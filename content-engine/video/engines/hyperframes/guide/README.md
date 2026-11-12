# Guia de autoria do motor HyperFrames

Conhecimento para escrever composições de vídeo para o motor ativo. São adaptações das skills oficiais do HyperFrames (em inglês; Copyright 2026 HeyGen, Inc., licença Apache-2.0), modificadas: sem nada de login, nuvem, publicação, telemetria, catálogo remoto, Studio/preview, TTS ou instalação. Origem, licença e lista de modificações em `NOTICE.md`; texto da licença em `LICENSE-APACHE-2.0.txt`. Onde o original mandava rodar o CLI, aqui vale o contrato do repo:

```bash
python content-engine/video/render.py <pasta-da-composicao> <saida.mp4>
python content-engine/video/frames.py <video.mp4> <pasta-saida> --at <tempos>
```

Antes de tudo, leia `content-engine/video/MOTOR.md` (seção "Como escrever uma composição"): ela tem as regras da casa que valem por cima destes arquivos (arquivo único, `_motor/` para GSAP e fontes, nenhuma URL externa, sem `.env`).

## Por onde começar

- `core/core.md`: o contrato da composição (raiz, clips, timeline pausada, armadilhas do lint).
- `core/minimal-composition.md`: o esqueleto mínimo que renderiza.
- `core/determinism-rules.md`: o que quebra o render quadro a quadro (relógio, aleatório, timers, loops infinitos).

## Composição e tempo (`core/`)

- `data-attributes.md`: todos os `data-*` da raiz e dos clips.
- `tracks-and-clips.md`: como os clips se sobrepõem no tempo e em camadas.
- `composition-patterns.md`: arquivo único x sub-composições (aqui usamos arquivo único).
- `full-screen-motion.md`: fundo compartilhado e movimento de tela cheia.
- `variables-and-media.md`: variáveis e `<video>`/`<audio>` (vídeo e áudio locais).

## Animação (`animation/`)

- `adapters/gsap.md`: o adaptador GSAP (o runtime padrão daqui).
- `adapters/gsap-timeline-and-labels.md`, `gsap-easing-and-stagger.md`, `gsap-transforms-and-perf.md`: timeline, curvas, escalonamento e desempenho.
- `adapters/css-animations.md`: quando a animação é só CSS.
- Receitas para vídeo curto (`blueprints/`):
  - `kinetic-type-beats.md`: frase que muda batida a batida (gancho em texto).
  - `titlecard-reveal.md`: cartela de título.
  - `dataviz-countup.md`: número que conta até o valor (preço, quantidade).
  - `device-surface-showcase.md`: tela do produto em destaque.
  - `cta-morph-press.md`: botão de chamada sendo "apertado".
  - `logo-assemble-lockup.md`: fecho com logo.
  - `grid-card-assemble.md`: cartões que se montam em grade.

## Câmera e poses (`keyframes/`)

- `keyframes.md`: zoom, panorâmica, Ken Burns, recorte e máscara com keyframes que aguentam o seek.
- `keyframe-patterns.md`: qual mecanismo usar para cada tipo de movimento.

## Direção (`creative/`)

- `beat-direction.md`: como dirigir cada batida (verbo de movimento, transição, camadas, ritmo).
- `design-adherence.md`: conferir se a composição respeitou cores, fontes e espaçamentos da marca.
- `composition-patterns.md`: padrões de quadro (vídeo dentro de moldura, cartela de título, seções com cabeçalho).

## Avisos de leitura

- Nomes entre crases como `spring-pop-entrance`, `avatar-cloud-network`, `techniques.md` ou `rules/<id>.md` vêm da biblioteca de receitas do HyperFrames, que **não** foi copiada. Leia como descrição do movimento e escreva o tween você mesmo.
- Menções a Anime.js, Lottie, Three.js, transições com shader, áudio narrado e legendas automáticas são contexto: essas bibliotecas não estão instaladas e não podem ser baixadas.
- Toda menção a "editor" ou "lane" é sobre a interface visual do HyperFrames, que não usamos.
