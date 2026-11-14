# Motor de vídeo local

Tudo que vira vídeo passa por aqui. Quem automatiza (script, skill ou agente) nunca chama o motor direto: chama só os scripts deste contrato e lê este arquivo para saber como escrever a composição. O render não manda nada para fora da máquina e só lê arquivos de dentro da pasta da composição. A única exceção em todo o repo é o texto da narração, que pode ir, antes do render, ao provedor de voz de nuvem escolhido; se o provedor treina com esse texto é coisa a conferir nos termos dele (e evitar plano gratuito que diga que usa os dados), não uma garantia daqui (ver `content-engine/audio/AUDIO.md`). O vídeo e os arquivos da composição nunca saem. Nenhuma peça é publicada sozinha: não existe postagem automática, e toda peça é revisada por uma pessoa antes de ir ao ar.

## Motor ativo

- **HyperFrames 0.8.141** (versão auditada), adaptador em `engines/hyperframes/`.
- Escolhido em `motor.json` (`{"ativo": "hyperframes"}`).
- Navegador: **`chrome-headless-shell` 152.0.7977.30 fixado**, a mesma versão que o HyperFrames fixa, baixado uma vez pelo `setup.py` para `content-engine/browser/` e compartilhado com o motor de imagem (ver "Navegador fixo"). Sem ele, o render cai no Chrome do sistema e avisa.
- FFmpeg: build estático local em `content-engine/video/bin/` (não usa FFmpeg do sistema).
- Guia de autoria do motor ativo: `engines/hyperframes/guide/README.md`.

## Contrato

Todos rodam da raiz do repo, com Python 3 (só biblioteca padrão):

```bash
python content-engine/video/setup.py
python content-engine/video/doctor.py
python content-engine/video/render.py <pasta-da-composicao> <saida.mp4> [--fps 30] [--qualidade rascunho|padrao|final]
python content-engine/video/frames.py <video.mp4> <pasta-saida> [--at 0,1.5,3] [--n 8] [--guias]
python content-engine/video/preview.py <pasta-da-composicao> [--porta N] [--t SEG]
python content-engine/video/montar_reel.py <pasta-da-peca> [--sobrescrever] [--refazer-legenda] [--ouvida 2,4 --por "nome"]
python content-engine/video/apontar.py <print> [--largura N] [--conferir x,y,w,h --saida recorte.png]
python content-engine/video/checar_reel.py <video.mp4> [<pasta-da-peca>]
```

- `setup.py`: instalação única. Instala os pacotes npm fixados do motor dentro de `content-engine/video/engines/<motor>/node_modules` e baixa o FFmpeg e o navegador fixo (`chrome-headless-shell`), ambos com conferência de SHA-256. Rede usada só aqui. Rodar de novo não baixa o que já está conferido.
- `doctor.py`: confere tudo e imprime `PASS`/`FAIL` por item (Python, Node 22, FFmpeg, navegador em uso com caminho e versão, que só passa quando é o navegador fixo com SHA-256 conferido e vira `AVISO` quando cai no Chrome do sistema, versão fixada do motor, fontes e GSAP locais, isolamento do ambiente, auto-teste do bloqueio de rede, auto-teste do guarda de arquivos, casos de referência a arquivo fora da composição, casos de playlist e de tipo de arquivo recusados, `.gitignore`). Sai com código 1 se algo falhar.
- `render.py`: recusa renderizar, antes de abrir o navegador, se houver `.env` perto da composição, URL externa nos arquivos dela, arquivo de tipo fora da lista permitida ou lista de reprodução (ver "Tipos de arquivo aceitos"), ou qualquer referência de arquivo que não seja um arquivo existente dentro da pasta da composição (checagem estática em `content-engine/common/midias.py`, detalhada em "Garantias"), além de `<audio>` sem `id` e atributo `crossorigin`; depois renderiza num ambiente isolado, com o guarda de arquivos ligado, e salva o `.mp4`. Se o guarda bloquear qualquer leitura de arquivo fora da composição durante o render, o `render.py` aborta, apaga o vídeo parcial e lista o que foi bloqueado. Imprime resolução, duração, fps, codec, quantas faixas de áudio saíram, se houve tentativa de rede bloqueada e se houve acesso a arquivo bloqueado.
- `frames.py`: extrai PNGs do vídeo com o FFmpeg local para revisão. Sem `--at`, espalha `--n` frames do começo ao fim. `--guias` salva também uma cópia com as faixas de interface do Reels pintadas de vermelho (topo, rodapé e laterais): nada importante pode ficar nelas.
- `preview.py`: prévia no navegador, para acertar tempo e posição antes de gastar um render (ver "Pré-visualização"). Não substitui o render.
- `montar_reel.py`: monta a composição inteira de um Reel narrado a partir do `roteiro.json` da pasta da peça (ver "Montador de Reel"). É o caminho padrão para vídeo vertical narrado; escrever o `index.html` à mão fica para o que o catálogo de cenas não cobre.
- `apontar.py`: tira do print as coordenadas de um alvo, com régua no navegador ou com um recorte para conferir (ver "Apontar coordenadas no print").
- `checar_reel.py`: checagem automática de motion do vídeo renderizado, `PASS`/`FAIL` por item e código 1 em falha (ver "Checagem de motion").

O motor não decide onde as peças ficam: a pasta da composição e o caminho do `.mp4` são argumentos. Exemplos prontos para renderizar: `examples/hello-world/` (composição escrita à mão) e `examples/reel-from-script/` (montada a partir de um roteiro).

## Montador de Reel (roteiro.json)

Caminho padrão para vídeo vertical narrado. A pessoa escreve um `roteiro.json` na pasta da peça e o montador produz a composição inteira: `index.html`, `trilha.json` já aplicado, legenda e `montagem.json`. Nenhum tempo é digitado: cada movimento é amarrado a uma PALAVRA da fala.

```bash
python content-engine/video/montar_reel.py <pasta-da-peca> [--sobrescrever] [--refazer-legenda]
python content-engine/video/apontar.py <print> [--largura 884] [--conferir x,y,w,h --saida recorte.png]
python content-engine/video/render.py <pasta-da-peca> <saida>/reel.mp4
python content-engine/video/checar_reel.py <saida>/reel.mp4 <pasta-da-peca>
```

O que o `montar_reel.py` faz, na ordem:

- **Voz.** Grava as falas em `vozes/voz.txt` (já com a grafia de pronúncia da marca, ver `pronuncia` abaixo) e em `vozes/legenda.txt` (a grafia da tela, que é a que a legenda mostra) e gera só as que faltam (ou cujo texto mudou) com a voz padrão: `voz.py --batidas N`. Fala já gravada com o mesmo texto não é gerada de novo. A geração confere a pronúncia e tenta outra semente quando acha divergência (`content-engine/audio/AUDIO.md`, seção "Conferência de pronúncia").
- **Tempos de cena.** Cada batida dura a fala mais o respiro: a fala começa 0,15 s depois do quadro 0 no gancho e 0,25 s depois do corte nas outras; sobra 0,3 s de respiro; a última batida ganha 2,6 s depois da fala para o logo. Com música, o corte sobe para a próxima batida do compasso (BPM do `musica.json`). `"cortes": "fala"` no roteiro desliga o encaixe; `"minimo": 5.0` numa batida estica a duração dela.
- **Legenda.** Roda o `legenda.py` (Whisper local) e tira dele o início e o fim de cada palavra. Rodar de novo sem mudar fala nem tempo não chama o Whisper.
- **Momentos.** Cada `{"na": "sem caixa", "faz": ...}` vira o instante em que a palavra é dita. `na` aceita uma palavra ou uma expressão seguida da fala (sem acento, caixa ou pontuação), `"@inicio"` e `"@fim"`. Opcionais: `"vez": 2` (segunda vez que a palavra aparece), `"ponto": "fim"` (fim da palavra) e `"ajuste": 0.15` (segundos, no máximo 0,5 para cada lado). Palavra que não está na fala para a montagem com a frase na mensagem.
- **Efeitos.** Um efeito do conjunto cine por tipo de movimento, com nível de peça com voz (0,4 a 0,8), e a âncora aplicada (`t = momento - âncora`). O mesmo efeito repetido a menos de 0,09 s é descartado.
- **Música, legenda e marca.** Música da marca (`motion.musica` do `tokens.json`) com volume 0,55 e 0,2 sob a voz; faixa escura atrás da legenda; cores, fontes e estilo de `motion` do `tokens.json`; logo copiado do caminho do `tokens.json` para `assets/` (ou `"logo"` no roteiro).
- **Regra do primeiro segundo.** Nenhum título, apoio, selo ou painel entra antes de 1,0 s: o montador segura o texto até lá. Só a legenda da fala aparece antes.

Garantias:

- **Determinístico e idempotente.** Mesmo roteiro e mesmas falas dão o mesmo `index.html`, `trilha.json` e `base.wav`, byte a byte.
- **Ajuste manual não é sobrescrito.** O `montagem.json` guarda o SHA-256 do `index.html` e do `trilha.json` gerados. Se um deles mudou (ou a pasta tem um `index.html` que não veio do montador), a montagem para e diz qual. O lugar do ajuste é o roteiro: campos da cena, `css_extra` e `js_extra`. `--sobrescrever` troca assim mesmo e guarda a versão anterior em `ajustes-manuais/`.
- Avisos (alvo fora da tela, momento no fim da batida, letra que a fonte pixel não tem, fecho sem chamada) saem no fim e ficam em `montagem.json`.
- **Fala apontada e ouvida por uma pessoa.** `--ouvida 2,4 --por "nome"` registra em `vozes/ouvidas.json` que alguém ouviu aquelas falas e achou certas (com o SHA-256 do áudio). A liberação entra no `montagem.json` e a checagem troca o `FAIL` de pronúncia por `AVISO`. Fala gerada de novo perde a liberação.

### Formato do roteiro.json

- `marca`: chave do `content-engine/tokens.json` (obrigatório).
- `titulo`: nome da peça (vai no `<title>`); `nome_da_marca`: texto alternativo do logo (sem ele, a chave da marca).
- `logo`: arquivo do logo dentro da pasta; sem ele, o do `tokens.json` é copiado para `assets/`.
- `musica`: `{"faixa": "synthwave-noturna"}` (mais `volume`, `sob_voz`, `entrada`, `saida` se quiser); sem a chave, usa a faixa da marca; `false` tira a música.
- `cortes`: `"compasso"` (padrão com música) ou `"fala"`.
- `fundo`: `{"textura": "assets/textura.png"}` (textura que desliza) ou `{"midia": "assets/foto.jpg"}` (imagem desfocada atrás de tudo).
- `painel`: o fio condutor. `{"titulo": "SEU PEDIDO", "itens": ["O PRODUTO", "O TAMANHO", "A ENTREGA"], "entra_na_batida": 2}`, de 1 a 4 itens. Fica no topo até o fecho e é preenchido pelas batidas.
- `legenda`: `{"destaque": ["roteiro", "comando"]}` (palavras em cor de acento).
- `pronuncia`: `{"IA": "i a"}`. Troca a palavra inteira só no texto que vai para a voz; a legenda e a tela ficam como estão escritas na fala. O padrão de cada marca fica em `motion.pronuncia` do `tokens.json`; o do roteiro soma e vence.
- `css_extra`, `js_extra`: texto livre somado ao fim do CSS e do script (ajuste fino que o roteiro não cobre).
- `batidas`: lista. Cada batida tem `fala` (uma linha, escrita para a voz) e `cena` (`tipo` mais os campos do tipo). Opcional `minimo` (segundos).
- Em qualquer cena menos `fecho`, `passos` e `impacto`: `titulo` (linhas separadas por `|`, `*palavra*` em cor de acento), `titulo_na`, `apoio`, `apoio_na`; `transicao`: `"corte"` (padrão) ou `"cortina"`.

O bloco `motion` de cada marca no `tokens.json` (todos opcionais; sem ele a marca cai no estilo `suave` com as cores dela): `estilo` (`suave` ou `pixel`), `fonte_titulo` e `fonte_texto` (famílias de `content-engine/fonts`), `acento`, `acento2`, `tinta`, `fundo` (três cores, do centro para a borda), `sombra_texto`, `apagado`, `linha`, `cortina` (três cores), `musica` (faixa padrão) e `pronuncia`.

Exemplo completo (é o roteiro de `examples/reel-from-script/roteiro.json`, com a marca fictícia `exemplo`):

```json
{
 "marca": "exemplo",
 "nome_da_marca": "Marca Exemplo",
 "titulo": "Reel a partir de um roteiro - Marca Exemplo",
 "fundo": {"midia": "assets/fundo.webp"},
 "legenda": {"destaque": ["roteiro", "comando"]},
 "batidas": [
  {
   "fala": "Este vídeo nasceu de um roteiro em texto, sem nenhum tempo digitado.",
   "cena": {
    "tipo": "abertura", "midia": "assets/fundo.webp",
    "titulo": "DO ROTEIRO|*AO VÍDEO*", "titulo_na": "roteiro",
    "apoio": "sem *nenhum tempo* digitado", "apoio_na": "sem"
   }
  },
  {
   "fala": "Você escreve a fala de cada batida e escolhe a cena que aparece com ela.",
   "cena": {
    "tipo": "passos", "rotulo": "A FALA DA BATIDA",
    "pedido": "Você escreve a fala de cada batida", "digita_na": "escreve",
    "partida": "assets/fundo.webp", "resultado": "assets/cartao.png", "resultado_na": "cena"
   }
  },
  {
   "fala": "O motor gera a voz, a legenda e a trilha, com os cortes no compasso da música.",
   "cena": {
    "tipo": "impacto",
    "linhas": [{"texto": "VOZ", "na": "voz"}, {"texto": "LEGENDA", "na": "legenda"}, {"texto": "*TRILHA*", "na": "trilha"}],
    "apoio": "cada corte *no compasso*", "apoio_na": "cortes"
   }
  },
  {
   "fala": "Monte o seu com um comando.",
   "cena": {
    "tipo": "fecho",
    "linhas": [{"texto": "MONTE", "na": "Monte"}, {"texto": "*O SEU*", "na": "seu"}],
    "apoio": "com *um comando*", "apoio_na": "comando"
   }
  }
 ]
}
```

Uma batida com a cena `aparelho`, que o exemplo acima não usa (print da tela do seu produto, câmera e destaques amarrados às palavras):

```json
{
 "fala": "Primeiro, escolha o tamanho: cada um tem a sua tabela de medidas.",
 "cena": {
  "tipo": "aparelho", "print": "assets/tela-produto.png", "largura_do_print": 884, "rolagem": 245, "painel_item": 1,
  "momentos": [
   {"na": "tamanho", "faz": "camera", "alvo": {"x": 12, "y": 358, "w": 864, "h": 388}, "zoom": 1.45},
   {"na": "cada", "faz": "foco", "alvo": {"x": 12, "y": 358, "w": 864, "h": 119}},
   {"na": "a sua", "faz": "foco", "alvo": {"x": 12, "y": 628, "w": 864, "h": 119}, "cor": "acento2"},
   {"na": "a sua", "faz": "toque"},
   {"na": "tabela", "faz": "preenche", "valor": "Tamanho M", "ajuste": 0.12},
   {"na": "medidas", "faz": "confirma", "ajuste": 0.3}
  ]
 }
}
```

### Catálogo de cenas

Todas tomam cores, fontes, bordas e sombras do estilo da marca (`motion.estilo` no `tokens.json`): `pixel` (Press Start 2P nos títulos, borda reta, sombra dura) ou `suave` (Inter 900, cantos de 30 px, sombra macia, fundo com a mídia desfocada). Marca sem `motion` cai no `suave` com as cores dela.

- **`abertura`** - o RESULTADO em tela cheia no primeiro segundo. Campos: `midia` (imagem ou clipe; cobre a tela; imagem ganha zoom lento, `zoom` e `foco: {"x": 50, "y": 40}` em %), `titulo`, `apoio`. O texto só entra depois de 1,0 s, com um véu escuro no topo. Usar: primeira batida de peça cujo resultado é uma imagem ou vídeo. Clipe com poucos quadros-chave faz o render avisar `sparse keyframes`: reencodar com um quadro-chave por segundo.
- **`aparelho`** - a tela real do produto dentro de um aparelho. Campos: `print`, `largura_do_print` (largura lógica das coordenadas; sem ele, a do arquivo), `rolagem` (y do print no topo da tela ao começar a batida), `abre_em` (alvo que enche a tela no quadro 0: é a abertura pelo resultado quando o resultado está na tela do produto), `painel_item`, `momentos`. Batidas `aparelho` seguidas usam o mesmo aparelho: print diferente entra empurrando o anterior; mesmo print com outra `rolagem` rola. Momentos (`faz`): `camera` (`alvo`, `zoom` de 1,05 a 2,2; de 1,35 a 1,5 costuma bastar), `volta`, `foco` (`alvo`, `cor: "acento2"`), `marca` (`alvo`, `cor`, `d`), `toque`, `rola` (`para` ou `alvo`), `chip` (`texto`; etiquetas acima da legenda), `preenche` (`valor`, digita na linha do painel) e `confirma`. Câmera, foco e etiquetas se recolhem sozinhos no fim da batida. Usar: mostrar onde clicar e o que ler; print em alta resolução (1300 px de largura ou mais) e com a informação que importa à vista.
- **`painel`** (chave do roteiro, não é cena) - o fio condutor. Batida com `painel_item: N` mostra um selo com o nome do item, que voa para a linha N; `preenche` digita o valor e `confirma` marca OK e soma o contador. No fecho, `"resumo": true` traz o cartão com os valores. Usar: peça que junta 2 a 4 respostas ao longo do vídeo.
- **`comparacao`** - antes e depois. Campos: `antes`, `depois`, `rotulos`, `modo` (`"cortina"`: uma imagem cobre a outra da esquerda para a direita; `"lado"`: dois cartões no mesmo fundo, diferenciados pelo acento), `revela_na`. Usar: edição, estilo, restauração.
- **`galeria`** - até 6 mídias em pilha, cada uma entrando na sua palavra. Campos: `midias: [{"arquivo": ..., "na": ...}]` (imagem ou clipe), `formato` (`retrato`, `quadrado`, `paisagem`). A imagem ganha zoom lento; a anterior recua. Usar: variações, vitrine, sequência de resultados.
- **`passos`** - pedido digitado e resultado. Campos: `rotulo`, `pedido` (texto digitado), `digita_na`, `resultado` (imagem ou clipe), `resultado_na`, `formato`, `partida` (imagem que fica no cartão enquanto o pedido é digitado, com zoom lento; para vídeo, um quadro dele). Sem `partida`, o cartão vazio mostra só um brilho passando. Usar: "escreva isto, sai isto"; com `partida`, "esta imagem vira isto" (animar, estender, editar).
- **`impacto`** - texto grande. Campos: `linhas: [{"texto": ..., "na": ...}]`, `apoio`, `apoio_na`, `topo`. Usar: virada da peça, número, promessa; no máximo uma por peça.
- **`fecho`** - sempre a última. Campos: `linhas`, `apoio`, `resumo`, `brilhos`, `chamada` (padrão: o `url` da marca). Entra com cortina; o logo bate depois da última palavra e a chamada para o site sobe em seguida. Toda peça termina aqui: sem `fecho` o montador avisa.

### Apontar coordenadas no print

O `alvo` de `camera`, `foco`, `marca` e `abre_em` é um retângulo `{"x", "y", "w", "h"}` no print. Ninguém mede no olho:

- `python content-engine/video/apontar.py <print> --largura 884` abre o print no navegador (só `127.0.0.1`) com régua a cada 100 px. Clicar e arrastar em volta do alvo gera a linha `"alvo": {...}` pronta para copiar; ela também sai no terminal.
- `--largura` é o mesmo número do `largura_do_print` da cena. Sem ele, as coordenadas são os pixels reais do arquivo.
- `--conferir x,y,w,h --saida recorte.png` grava o pedaço do print com o retângulo desenhado, para confirmar um alvo sem abrir o navegador (é como um agente confere).
- Alvo por texto ("a linha que diz Tamanho M") não existe: exigiria ler o print (OCR), que não há no motor sem pacote novo.

### Checagem de motion

`python content-engine/video/checar_reel.py <reel.mp4> [<pasta-da-peca>]` imprime `PASS`, `AVISO` ou `FAIL` por item e sai com código 1 se houver `FAIL`. Os limites vêm de uma peça de referência aprovada (maior trecho parado 0,47 s; 9% do vídeo em trechos parados de 0,3 s ou mais; -13,8 LUFS; música 14,3 dB abaixo da voz; 2 quiques em 68 animações).

Só com o vídeo:

- **formato**: 1080x1920 a 30 fps, com faixa de áudio.
- **duração**: de 5 a 90 s (fora disso, aviso).
- **trecho parado** (`freezedetect`, ruído 0,001): falha com trecho acima de 0,8 s ou com mais de 20% do vídeo em trechos de 0,3 s ou mais; aviso acima de 0,6 s.
- **loudness final**: -14 LUFS com folga de 1,5 (aviso até 3) e pico até -1 dBTP.
- **primeiro segundo (imagem)**: tela preta no quadro 0 falha; mais de 80% de área lisa nos quadros de 0, 0,5 e 0,95 s vira aviso de cartela.

Com a pasta da peça:

- **vídeo e composição**: mesma duração; aviso se o vídeo é mais antigo que o `index.html`.
- **primeiro segundo (texto)**: nenhum texto do montador antes de 1,0 s.
- **texto na zona segura**: cada bloco de texto planejado (título, apoio, selo, etiquetas, painel, resumo, logo, chamada) dentro das margens do `frames.py` (11,5% no topo, 22% no rodapé, 5,5% à esquerda, 13% à direita).
- **cortes no compasso**: cada corte de cena em múltiplo da batida da música.
- **legenda**: `legenda.json` com blocos e `K.legenda` no `index.html`; faixa da legenda dentro da zona segura; texto claro na faixa em instantes de fala do vídeo.
- **pronúncia da voz**: resultado da conferência gravado no `legenda.json`; fala apontada só deixa de reprovar com a liberação de quem ouviu (`--ouvida` do montador), e vira aviso.
- **música abaixo da voz**: música presente e pelo menos 10 dB abaixo da voz nos trechos de fala (aviso entre 6 e 10), medido nos arquivos da trilha.
- **quique nos movimentos**: `back`, `elastic`, `bounce` e `K.toque` contados no script; falha acima de 12% das animações (mínimo de 3 liberados).

O que ela não julga (precisa de olho e de ouvido): se o primeiro segundo mostra o resultado e não uma tela qualquer; se um texto transbordou a caixa planejada (a posição conferida é a planejada, não a desenhada); se cada movimento caiu na palavra certa; se a voz, a música e os efeitos soam bem. Peça escrita à mão (sem `montagem.json`) fica sem as checagens de texto. Depois dela, continuam obrigatórios os quadros do `frames.py --guias` e ouvir a peça inteira.

Testes: `python -m unittest discover -s tests` em `content-engine/video/` (palavra para momento, grafia de pronúncia para a voz, encaixe no compasso, âncora de efeito, limites da checagem e as cenas `passos` e `abertura`).

## Como escrever uma composição para o motor ativo (HyperFrames)

O `montar_reel.py` já escreve neste formato; esta seção vale para composição feita à mão e para entender o que ele gera. Resumo; o detalhe está em `engines/hyperframes/guide/`.

- Uma pasta por vídeo com **um `index.html`** (composição única, sem sub-composições) e uma subpasta `assets/` com cópias dos arquivos usados (prints, fotos, logo).
- **Todo arquivo usado mora dentro da pasta**, referenciado por caminho relativo sem `..`. Caminho absoluto, unidade de disco (`C:/`), `file:`, caminho de rede (`\\servidor\...`) e `..` são recusados em qualquer lugar: atributo, CSS, `srcdoc`, texto de `<script>` e arquivo `.js`. `<base href>` e `<meta http-equiv="refresh">` também. Se mesmo assim usar `data-composition-src`, o arquivo da sub-composição precisa estar dentro da pasta e é conferido com as mesmas regras.
- Raiz: `<div id="root" data-composition-id="<id>" data-start="0" data-width="1080" data-height="1920" data-duration="<segundos>">`.
- Cada cena é um `<section class="clip" data-start="..." data-duration="...">`. O motor mostra e esconde a cena sozinho: anime os filhos, nunca a própria `.clip`.
- Uma timeline GSAP pausada, registrada no fim: `window.__timelines["<id>"] = tl;` (mesmo id da raiz). Nada de `Date.now()`, `Math.random()` sem semente, timers, loop infinito.
- **Bibliotecas e fontes vêm de `_motor/`**, que o `render.py` monta na hora do render (não copie para a pasta):
  - `_motor/gsap.min.js` e plugins `_motor/CustomEase.min.js`, `SplitText.min.js`, `TextPlugin.min.js`, `ScrambleTextPlugin.min.js`, `DrawSVGPlugin.min.js`, `MorphSVGPlugin.min.js`, `MotionPathPlugin.min.js`, `Flip.min.js`.
  - Fontes (woff2, subset latino), copiadas de `content-engine/fonts/` (a mesma pasta do motor de imagem): `_motor/fonts/press-start-2p-400.woff2`, `_motor/fonts/inter-{400,500,600,700,800,900}.woff2`, `_motor/fonts/montserrat-{600,800}.woff2` e as variantes `-ext` (`press-start-2p-ext-400`, `inter-ext-<peso>`, `montserrat-ext-<peso>`).
  - Kit de motion (opcional): `_motor/kit/motion.js` (`<script src="_motor/kit/motion.js"></script>` depois do GSAP), cópia de `content-engine/video/kit/`. Expõe `window.MotionKit = { criar, palavras, EASE, DUR }`; `const K = MotionKit.criar(tl)` devolve as funções que agendam tweens na timeline (`bate`, `sobe`, `sai`, `camera`, `cameraVolta`, `foco`, `marca`, `toque`, `digita`, `respira`, `empurra`, `cortina`, `legenda`); `digita` exige o `_motor/TextPlugin.min.js` registrado. Composição antiga que traz o próprio `kit/motion.js` continua funcionando.
  - Toda família usada no CSS precisa de `@font-face` apontando para esses arquivos; fallback só genérico (`sans-serif`, `monospace`). Família sem `@font-face` faz o motor tentar baixar a fonte, e o bloqueio de rede corta.
- **Nenhuma URL `http://` ou `https://`** em HTML, CSS, JS, JSON ou SVG da composição (exceto `localhost`/`127.0.0.1` e os namespaces XML do tipo `xmlns="http://www.w3.org/2000/svg"`, que não são baixados). O `render.py` recusa.
- Sem `.env` na pasta da composição nem nas 5 pastas acima.
- Só tipos da lista fechada em "Tipos de arquivo aceitos" (sem playlist `.m3u8`, sem lista `ffconcat`).
- Lint do motor roda em modo estrito: erro de lint para o render. Avisos `timeline_track_too_dense`, `nested_structure_needs_subcomposition` e `duplicate_media_discovery_risk` (mesma imagem usada em duas cenas) são esperados no formato de arquivo único e não afetam o vídeo.
- **Abrir o `index.html` direto no navegador não funciona**: `_motor/` só existe durante o render e na prévia, e nada dá o play na timeline. Para ver a peça, use o `preview.py` ou o `render.py`.

## Legenda sincronizada com a fala

Os tempos por palavra vêm de `python content-engine/audio/legenda.py <pasta-da-composicao>` (`content-engine/audio/AUDIO.md`, seção "Legenda sincronizada"), que grava `legenda.json` e `legenda.js` (`window.__legenda = [...]`) na composição. O `.js` entra por `<script src>` (tipo aceito pela lista fechada); não use `fetch` do JSON.

```html
<script src="_motor/gsap.min.js"></script>
<script src="_motor/kit/motion.js"></script>
<script src="legenda.js"></script>
...
<section id="s-legenda" class="clip" data-start="0" data-duration="28.3" data-track-index="4">
  <div id="legenda"></div>
</section>
...
<script>
  const K = MotionKit.criar(tl);
  K.legenda("#legenda", window.__legenda);
</script>
```

- `K.legenda(sel, blocos, opcoes)`: cria um elemento por bloco dentro de `sel` e agenda tudo na timeline (nada de timer nem animação CSS). O bloco entra no seu `inicio` (0,14 s, sem overshoot) e sai no `fim` ou no corte para o próximo; a palavra falada no momento ganha a cor ativa e escala 1,08; palavra com `destaque: true` fica na cor de acento. Aceita a lista de blocos ou o objeto do `legenda.json`. Devolve os elementos criados.
- Padrão de fábrica: Inter 900 (o kit injeta o `@font-face` de `_motor/fonts/inter-900.woff2`), 68 px, contorno escuro de 10 px mais sombra, centralizada, faixa de 800 px de largura (cabe entre as margens de 5,5% e 13%), base em 24% da altura (acima da faixa de 22% do rodapé do Reels), no máximo 2 linhas (bloco que passar disso encolhe de 4 em 4 px até 44 px).
- Opções (cada uma também é variável CSS no container): `tamanho` (`--k-leg-tamanho`), `largura` (`--k-leg-largura`), `base` (`--k-leg-base`, distância do rodapé), `cor` (`--k-leg-cor`), `ativa` (`--k-leg-ativa`), `acento` (`--k-leg-acento`), `contorno` (`--k-leg-contorno`), `espessura` (`--k-leg-espessura`), `fonte` (`--k-leg-fonte`), `peso` (`--k-leg-peso`). Só por opção: `escala` (1.08), `entrada` (0.14), `antecipa` (0.05 s antes da fala), `folga` (0.12 s depois da última palavra), `emenda` (0.3 s: intervalo até o próximo bloco abaixo do qual a troca é corte seco), `linhas` (2), `tamanhoMinimo` (44).
- A seção da legenda fica acima das outras (`z-index` maior) e dura o vídeo todo. Reserve a faixa entre 68% e 76% da altura: elemento da peça ali fica atrás da legenda.
- Conferir no `preview.py` e, depois do render, com `frames.py --guias` em instantes de fala.

## Pré-visualização

`python content-engine/video/preview.py <pasta-da-composicao> [--porta N] [--t SEG]` sobe um servidor só em `127.0.0.1` (porta 4790 ou a próxima livre) e imprime o endereço; Ctrl+C encerra.

- Serve a composição com `_motor/` resolvido em memória (GSAP, fontes e kit vêm da instalação do motor): **nada é gravado na pasta da composição**. Caminhos com raiz (`/_motor/...`, `/assets/...`) também respondem.
- Injeta, só na resposta do `index.html`, uma barra com tocar/pausar, linha do tempo, tempo atual e velocidade (0,25x a 2x). Ela dirige `window.__timelines["<id>"]`, mostra e esconde as cenas por `data-start`/`data-duration`, toca os `<audio>` em sincronia aproximada (`data-start`, `data-duration`, `data-volume`) e escala o palco para caber na janela. Espaço toca e pausa; setas andam um quadro (com Shift, 1 s). `--t 12.5` ou `?t=12.5` abre naquele segundo.
- Só entrega arquivo de tipo aceito de dentro da pasta (e `_motor/`); recusa `Host` que não seja `127.0.0.1` ou `localhost`.
- **É prévia, não prova.** Roda no navegador do sistema, sem o isolamento, o lint e o relógio quadro a quadro do motor; áudio e tempo são aproximados. A prova final continua sendo `render.py` seguido de `frames.py`.

## Áudio na composição

Efeitos, música e voz vêm da camada de áudio (`content-engine/audio/AUDIO.md`): biblioteca de efeitos em `content-engine/audio/sfx/`, música de fundo CC0 em `content-engine/audio/music/` e narração gerada por `content-engine/audio/voz.py` antes do render. Aqui eles só entram como arquivos locais:

- Um `<audio>` por som, **na raiz** (filho direto do `#root`), para sobreviver aos cortes de cena: `<audio id="trilha-01" src="assets/sfx/pop-gota.wav" data-start="0.75" data-duration="0.19" data-track-index="11" data-volume="0.8"></audio>`.
- `id` obrigatório (sem `id` o motor não mistura e o vídeo sai mudo); nunca `crossorigin`; `data-track-index` alto (música 9, voz 10, efeitos 11 em diante), sem dois `<audio>` sobrepostos na mesma trilha; `data-volume` é ganho linear (1 = nível do arquivo).
- O arquivo fica dentro da pasta da composição (`assets/sfx/`, `assets/voz/`); WAV 48 kHz é o formato da camada de áudio. Nada de URL: o `render.py` recusa endereço de internet e arquivo fora da pasta.
- Não escreva os `<audio>` à mão: `python content-engine/audio/trilha.py <pasta-da-composicao> <trilha.json>` copia os efeitos e grava os elementos (substitui os anteriores marcados com `data-trilha="1"`).
- Nunca chamar `play()`, `pause()` ou mexer em `currentTime`: o motor controla a mídia. O mix é feito pelo FFmpeg local (soma linear das faixas) e sai em AAC 48 kHz estéreo.
- Níveis, volumes por tipo de som e como a voz define a duração das batidas: `content-engine/audio/AUDIO.md`, seção "Mixagem".
- Conferir depois do render: `audio: 1 faixa(s)` no fim da saída do `render.py`, e loudness com `content-engine/video/bin/ffmpeg.exe -i <video.mp4> -af ebur128=peak=true -f null -` (esperado perto de -14 LUFS integrado com voz, pico até -1 dBTP).

## Garantias de localidade e como são aplicadas

- **Ambiente do motor por lista branca** (`_comum.sandbox_env`, que usa `content-engine/common/ambiente.py`, o mesmo do motor de imagem): o processo do motor recebe só variáveis de sistema (SystemRoot, PATH mínimo, processador) mais as do motor. Toda variável cujo nome parece chave ou token (`*_API_KEY`, `*TOKEN*`, `*SECRET*`, `ANTHROPIC*`, `OPENAI*`, `GEMINI*`, `GOOGLE*`, `OPENROUTER*`, `HEYGEN*`, `GITHUB*`, `AWS*`, `AZURE*` e outras) é removida, e o `render.py` aborta se sobrar alguma.
- **Casa falsa**: `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP` (e XDG) apontam para `content-engine/video/.sandbox/`. O motor não enxerga `~/.claude/.credentials.json`, não escreve em `~/.claude/skills`, `~/.cache` nem `~/.hyperframes`.
- **Telemetria e atualização desligadas**: `HYPERFRAMES_NO_TELEMETRY=1`, `DO_NOT_TRACK=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`, `HYPERFRAMES_NO_AUTO_INSTALL=1`, `HYPERFRAMES_SKIP_SKILLS=1`.
- **Bloqueio de rede no Node** (`engines/hyperframes/net-guard.cjs`, carregado por `NODE_OPTIONS=--require` e também direto na linha de comando, herdado por processos e workers filhos): bloqueia `net`/`tls` connect, `http`/`https` request, `fetch`, `WebSocket`, `dns` (lookup e resolve) e `dgram` para qualquer destino que não seja loopback. Cada tentativa vai para `content-engine/video/.sandbox/net-guard.log` e aparece no fim do `render.py`.
- **Chrome amarrado** (o mesmo guard intercepta o lançamento do navegador; a lista de flags é definida uma vez em `content-engine/common/chrome.py` e chega ao guard pela variável `VBSS_CHROME_ISOLAMENTO`; sem ela o guard recusa abrir o Chrome): acrescenta `--proxy-server=http://127.0.0.1:9` (sumidouro local) com exceção só para loopback, `--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1`, `--disable-background-networking`, `--disable-component-update`, `--disable-sync`, desativa recursos que chamam serviços (Optimization Guide, Media Router, Safe Browsing aprimorado e outros) e **remove o `--no-sandbox`** que o motor passava. O perfil do Chrome é temporário, dentro do sandbox. A sondagem `chrome.exe --version` do motor (que no Windows abriria um navegador de verdade) é respondida pelo guard com a versão lida do executável.
- **Só o subcomando `render`** do motor é chamado (`SUBCOMANDOS_PERMITIDOS` no adaptador). Nunca `init`, `usage`, `preview`, `studio`, `publish`, `cloud`, `lambda`, `skills`, `add`, `upgrade`, `telemetry`, `tts`, `transcribe`, `capture`, `snapshot`.
- **Pasta de trabalho vazia e cópia da composição**: o motor roda com diretório atual em `content-engine/video/.sandbox/cwd` (o HyperFrames lê `.env` do diretório atual: lá não existe nenhum) e renderiza uma cópia da composição em `content-engine/video/.sandbox/stage/`; ele nunca escreve na pasta do produto. O `.mp4` é movido para o destino só no fim.
- **Checagens antes do render**: `.env` na composição ou nas 5 pastas acima, e qualquer URL externa nos arquivos da composição, fazem o `render.py` parar com a lista do que achou.
- **Só o que está dentro da pasta da composição, e de tipo permitido, chega ao motor**, em quatro camadas:
  - **Lista fechada de tipos** (`content-engine/common/arquivos.py`, chamada uma vez pelo `render.py`, antes de montar a cópia): o motor só recebe a cópia, e a cópia só leva arquivo cuja extensão está na lista de "Tipos de arquivo aceitos". Lista de reprodução ou de arquivos (`.m3u`, `.m3u8`, `.ffconcat`, `.concat`, `.pls`, `.xspf`, `.cue`, ou qualquer arquivo, com qualquer extensão, que comece com `#EXTM3U` ou `ffconcat`; e arquivo com extensão de mídia que não começa com a assinatura binária real do formato, como um manifesto DASH/MPD salvo como `.wav`) e extensão desconhecida fazem o `render.py` parar, com o nome do arquivo na mensagem. Isso fecha o caso de uma playlist HLS dentro da pasta apontando para um `.ts` de fora, que as demais camadas não enxergavam por estar dentro de um arquivo de mídia. Link simbólico e junção de pasta também são recusados.
  - **Checagem estática** (`content-engine/common/midias.py`, primeira linha, rápida e com mensagem clara; é conveniência, a fronteira de verdade é o guarda abaixo). Varre todo `.html`, `.htm`, `.svg`, `.css`, `.js`, `.mjs` e `.cjs` da pasta (fora `node_modules/` e `renders/`), incluindo sub-composições, e segue cada arquivo referenciado. Confere como referência de arquivo `src`, `href` (qualquer tag), `xlink:href`, `poster`, `data`, `background`, `manifest`, `data-composition-src` (resolvido a partir da raiz, como o motor faz), `action`, `formaction`, `srcset` e `imagesrcset`; procura `url()` em todo valor de atributo (ex.: `filter="url(...)"` do SVG); lê `srcdoc` como HTML; lê CSS com escapes decodificados e comentários removidos (`@import"x"`, `@import/**/"x"`, `u\72l(`, `url/**/(`); e recusa caminho absoluto, unidade de disco, `file:`, `\\servidor`, `..` (também codificado como `%2e%2e`), `<base href>`, `<meta http-equiv="refresh">`, link simbólico ou junção que aponte para fora e arquivo inexistente. Em texto de `<script>`, atributos `on*`, strings de CSS e arquivos `.js` a regra é heurística: recusa string que pareça caminho fora (unidade de disco, `file:`, `\\servidor`, segmento `..`), mas não enxerga caminho montado por código (ex.: `"C" + ":" + "/x"`).
  - **Guarda de arquivos no Node** (`engines/hyperframes/file-guard.cjs`, carregado como o net-guard: `NODE_OPTIONS=--require` e direto na linha de comando, herdado por processos Node filhos e worker threads). O `render.py` passa a lista de pastas permitidas em `VBSS_FILE_GUARD_RAIZES`: a cópia da composição atual em `.sandbox/stage/<composicao>` (cópias de outras composições em `stage/` ficam fora da lista), as pastas de trabalho do motor no sandbox (`home`, `tmp`, `cwd`, `saida`, `fonts`, `media`, `renders`, `puppeteer`), a instalação do motor (`engines/hyperframes/`, com `node_modules`), `content-engine/video/bin/` (FFmpeg), a pasta do Node, a pasta do navegador (a do navegador fixo, ou a do Chrome do sistema quando ele é a reserva) e os dois logs dos guardas. Cobre: `fs.readFile`, `readFileSync`, `open`, `openSync`, `createReadStream`, `copyFile`, `copyFileSync`, `cp`, `cpSync`, `link`, `linkSync`, `rename`, `renameSync`, `openAsBlob` e `fs.promises.readFile`, `open`, `copyFile`, `cp`, `link`, `rename` (leitura, cópia, link físico ou movimentação de arquivo existente fora da lista é bloqueada; abertura para escrita fora da lista também; caminho que não existe segue para o sistema e dá "não encontrado"); e `child_process.spawn`, `spawnSync`, `execFile`, `execFileSync`, `exec`, `execSync` e `fork`, onde o executável precisa estar na lista ou em `System32` (nome solto resolvido pelo PATH mínimo do sandbox é aceito) e todo argumento com cara de caminho (absoluto, unidade de disco, `\\servidor`, `file:`, segmento `..`, valor de `--opcao=valor`, caminho dentro de filtro do FFmpeg como `amovie=C\:/...`, ou arquivo relativo existente) precisa cair dentro da lista; listas `concat` (`.txt`, `.ffconcat`) e scripts de filtro (`-filter_complex_script`, `-/opcao`) passados ao FFmpeg são lidos e cada caminho dentro deles é conferido. Links simbólicos e junções são resolvidos antes da conferência. Sem `VBSS_FILE_GUARD_RAIZES` o guarda falha fechado (só a instalação do motor e o Node ficam legíveis). Cada bloqueio vai para `content-engine/video/.sandbox/file-guard.log`, aparece no terminal, encerra o processo principal do motor (código 97) e faz o `render.py` parar sem salvar vídeo. Ele pega, por exemplo, a cópia que o próprio compilador do motor faz de arquivo fora do projeto (`[Compiler] Found 1 asset(s) outside project directory`, via `fs.copyFileSync`), mesmo com a checagem estática desligada.
  - **Chrome**: as páginas vêm do servidor local do motor (`http://localhost:<porta>`), que só entrega arquivos da pasta compilada e da cópia da composição (com conferência de que o caminho fica dentro delas). Página de origem `http` não consegue carregar `file:`: no teste com a checagem estática desligada, `srcset` com `C:/...` e áudio criado por script com `C:/...` deram `Not allowed to load local resource` no próprio Chrome e nada entrou no vídeo.
  - Não coberto pelo guarda de arquivos: código nativo que abre arquivo por conta própria, sem passar pelo `fs` do Node (ex.: `sharp` recebendo caminho; no render o motor passa buffers já lidos pelo `fs`); referências escondidas dentro do conteúdo de um arquivo de mídia que o FFmpeg ou o Chrome decodificam (a porta mais comum, a playlist, é barrada pela lista fechada de tipos, mas o conteúdo dos containers de mídia em si não é inspecionado); leituras internas do próprio Node que não passam pela API pública (carregador de módulos, que só lê a instalação do motor e o Node); metadados (`stat`, `readdir`, `exists`), que não leem conteúdo; e as pastas de trabalho do sandbox (`tmp`, `renders` e outras), que são compartilhadas entre renders e podem guardar sobras de renders anteriores deste motor (só cópias de composições, nunca arquivo pessoal). A cópia da composição para o sandbox é feita pelo Python antes do motor, arquivo a arquivo, só com a lista fechada de tipos.

### Tipos de arquivo aceitos

- Lista fechada, por extensão (sem diferenciar maiúscula): `html`, `htm`, `css`, `js`, `mjs`, `json`, `svg`, `txt`, `vtt`; imagens `png`, `jpg`, `jpeg`, `webp`, `gif`, `avif`; fontes `woff`, `woff2`, `ttf`, `otf`; áudio `wav`, `mp3`, `ogg`, `oga`, `m4a`, `aac`, `flac`, `opus`; vídeo `mp4`, `m4v`, `webm`, `mov`.
- `txt` fica na lista porque é comum a composição guardar o texto da narração em `voz.txt`; vale a mesma regra de conteúdo de todos os arquivos: se começar com `#EXTM3U` ou `ffconcat` (mesmo depois de espaços ou BOM), é recusado.
- Recusados com mensagem em português que cita o arquivo: lista de reprodução ou de arquivos (`m3u`, `m3u8`, `ffconcat`, `concat`, `pls`, `xspf`, `cue`, ou conteúdo que comece como uma), extensão fora da lista (a mensagem traz a lista dos tipos permitidos), arquivo sem extensão, link simbólico e junção de pasta.
- Assinatura real do formato: todo arquivo de imagem, fonte, áudio ou vídeo precisa começar com a assinatura binária do seu formato (ex.: `RIFF`/`RF64` + `WAVE` no `.wav`, `ftyp` no `.mp4`/`.m4a`/`.mov`, `PNG` no `.png`, `ID3` ou cabeçalho de quadro no `.mp3`). Se não bater, o arquivo é recusado: é assim que um manifesto (DASH/MPD, SMIL, HLS) salvo com extensão de mídia fica de fora.
- Fora da cópia, sem erro: `.env*`, e as pastas `renders/`, `node_modules/` e `.git/`.
- **Link físico (hard link)**: é um arquivo de verdade dentro da pasta, equivalente a uma cópia, e é tratado como tal (passa se o tipo for permitido). Não há detecção de link físico: quem põe um arquivo na composição está, de propósito, escolhendo esse conteúdo.

## Como rodar a prova

`prova-local.ps1` faz um render de verdade e, enquanto ele roda, amostra a árvore de processos do render e as conexões dela:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File content-engine\video\prova-local.ps1 -Composicao examples\hello-world -Saida <saida.mp4>
```

- Inicia o `render.py` e, a cada ~100 ms até ele terminar, monta a árvore de processos a partir do PID do Python do render (`Get-CimInstance Win32_Process`, seguindo `ParentProcessId`) e guarda as conexões TCP (`Get-NetTCPConnection`) e os endpoints UDP (`Get-NetUDPEndpoint`) que pertencem a PIDs dessa árvore. Outros programas abertos na máquina não entram na conta: o filtro é pela árvore, não pelo nome do executável.
- No fim confere: conexões TCP com destino fora de loopback, UDP fora de loopback, processos inesperados na árvore, linhas novas no `net-guard.log` e as flags de isolamento na linha de comando do navegador (proxy sumidouro, `--host-resolver-rules`, ausência de `--no-sandbox`, perfil dentro do sandbox).
- Dados brutos em `content-engine/video/.sandbox/prova/` (fora do git): `resumo.json`, `conexoes.csv`, `processos.csv`, `render.log`.
- Resultado esperado: só loopback (o canal de controle do navegador, o servidor local do motor e o proxy sumidouro `127.0.0.1:9`), nenhum processo inesperado e nenhum `updater.exe` quando o navegador é o fixo.

## Instalação fixada

- Pacotes npm (versões exatas em `engines/hyperframes/package.json`, árvore completa travada em `engines/hyperframes/package-lock.json`): `hyperframes@0.8.141`, `gsap@3.15.0`, `@fontsource/press-start-2p@5.3.0`, `@fontsource/inter@5.3.0` (os dois `@fontsource` seguem no lockfile, mas o render usa a cópia das fontes em `content-engine/fonts/`). Instalados com `npm ci --ignore-scripts`, cache em `content-engine/video/.cache/npm`, `.npmrc` do usuário ignorado, registro `https://registry.npmjs.org/`.
- FFmpeg 9.0.2 essentials (Windows x64, gyan.dev):
  - URL: `https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip`
  - Espelho oficial do mesmo arquivo: `https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip`
  - SHA-256 (de `https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip.sha256`): `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`
  - Só `ffmpeg.exe`, `ffprobe.exe` e a licença são extraídos para `content-engine/video/bin/`.
- Navegador: `chrome-headless-shell` 152.0.7977.30, detalhado na seção abaixo.
- Fora do git (`.gitignore` da raiz): `content-engine/video/.sandbox/`, `content-engine/video/.cache/`, `content-engine/video/bin/`, `content-engine/video/engines/*/node_modules/`, `content-engine/browser/`.

## Navegador fixo (compartilhado com o motor de imagem)

- **O quê**: `chrome-headless-shell` **152.0.7977.30** win64, do Chrome for Testing do Google. É a mesma versão que o HyperFrames 0.8.141 fixa no próprio código (`CHROME_VERSION`), ou seja, a versão com que o motor é testado. Fixação em `content-engine/common/navegador.json`; instalado em `content-engine/browser/` (fora do git), usado pelos dois motores.
  - URL: `https://storage.googleapis.com/chrome-for-testing-public/152.0.7977.30/win64/chrome-headless-shell-win64.zip` (localizada no índice `https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json`)
  - SHA-256 do zip: `5d7df999a6e4a65a1b16b25b61064f7337b8aa8ee2ed1b4e07bfdd24f6e4275e` (119.527.247 bytes)
  - SHA-256 do `chrome-headless-shell.exe`: `909fa4a0d2866f5b5b6cabd0a3b3545edeaf84db361148dbc8e992e25e61e7e6` (209.170.944 bytes)
  - Tamanho: download único de 114 MB; 270 MB no disco depois de extraído (o zip é apagado depois de conferido).
  - O Chrome for Testing não publica SHA-256. O valor foi registrado no primeiro download, como o do modelo do Kokoro; o MD5 do arquivo bateu com o `x-goog-hash` e o `ETag` que o Google Cloud Storage devolveu, e o tamanho com o `Content-Length`.
- **Por quê**:
  - Render reproduzível: a mesma versão de navegador em qualquer máquina, que não muda quando o Chrome do PC se atualiza sozinho.
  - Sem atualizador: o `chrome-headless-shell` não tem o atualizador do Google. Com o Chrome do sistema, toda execução acorda o `GoogleUpdater\updater.exe --wake-all --system`; com o navegador fixo, nenhum `updater.exe` aparece na árvore do render (dá para conferir com a prova monitorada).
  - Não depende do Chrome do PC: funciona mesmo sem Google Chrome instalado.
  - Mais leve: o `chrome-headless-shell` captura os quadros mais rápido que o Chrome completo do sistema, com vídeo visualmente equivalente e áudio idêntico.
- **Como é instalado**: `python content-engine/video/setup.py` (ou `python content-engine/image/setup.py`, que só instala o navegador) baixa o zip uma vez, confere o SHA-256, recusa zip com caminho fora da pasta do navegador, extrai, confere o SHA-256 do executável, grava `content-engine/browser/instalado.json` e apaga o zip. Rodar de novo não baixa nada. Nada é gravado na pasta do usuário. Código em `content-engine/common/navegador.py`.
- **Qual navegador o render usa** (`content-engine/common/chrome.py`, mesma regra nos dois motores): `VBSS_BROWSER` ou `VBSS_VIDEO_BROWSER`, se apontarem para um arquivo (troca manual); senão o navegador fixo instalado; senão o Chrome do sistema (e o Edge, por último). Fora do navegador fixo, o `doctor.py` e o `render.py` mostram `AVISO ... rode o setup para usar o navegador fixo`. No vídeo ele chega ao motor por `HYPERFRAMES_BROWSER_PATH`.
- **O que não mudou**: as mesmas flags de isolamento, o perfil temporário no sandbox, o net-guard, o file-guard e a lista de pastas permitidas (a pasta do navegador fixo entra no lugar da pasta do Chrome). O `doctor.py` dá `PASS` no navegador só quando ele é o fixo e o SHA-256 do executável confere; o render confere só a versão instalada e o tamanho do executável, para não gastar tempo a cada peça.
- **Trocar de versão** (ao atualizar o HyperFrames, acompanhar o `CHROME_VERSION` dele): mudar `versao`, `url` e `arquivo` em `navegador.json`, baixar o zip uma vez, registrar `sha256` e `bytes` do zip e `executavel_sha256` e `executavel_bytes` do executável, rodar o setup, os dois `doctor.py` e refazer a prova com `prova-local.ps1`.

## Limites conhecidos

- **O que é garantido**: o motor recebe apenas arquivos que estão fisicamente dentro da pasta da composição e de tipo permitido; a rede do motor e do Chrome está bloqueada; o motor só lê dentro da cópia, das pastas dele e das ferramentas. **O que não é**: código nativo que abre arquivo por conta própria e conteúdo referenciado de dentro de containers de mídia não são inspecionados (ver "Não coberto pelo guarda de arquivos"). O desenho assume que toda peça é revisada por uma pessoa antes de ser publicada e que não existe postagem automática; acidente raro que escape dessas camadas aparece na revisão.
- Com o navegador fixo, o atualizador do Google não aparece na árvore do render. Se o setup não rodou e o render cai no Chrome do sistema, esse Chrome acorda o atualizador (`GoogleUpdater\updater.exe --wake-all --system`): não é tráfego do projeto, é a checagem de atualização do próprio Chrome; a prova monitorada mostra se ele abriu conexão externa dentro da árvore do render.
- A prova por amostragem (a cada ~100 ms) pode não ver conexão que abre e fecha entre duas amostras; por isso o bloqueio é feito antes (guard e flags do Chrome) e a amostragem é só evidência.
- Resolução de DNS no Windows é feita pelo serviço DNS Client, fora da árvore do render; o guard e o `--host-resolver-rules` impedem que o motor e o Chrome peçam nomes externos.

## Como trocar de motor

Trocar de motor não muda o contrato dos scripts:

1. Criar `content-engine/video/engines/<novo>/` com `package.json`/lockfile (ou o equivalente), `adapter.py` e `guide/README.md`.
2. O `adapter.py` expõe o mesmo contrato do atual: `NOME`, `VERSAO_CLI`, `comando_instalacao(node, npm_cli)`, `versao_instalada()`, `checar()`, `recursos()` (mapa do que entra em `_motor/`, usado pelo `preparar` e pelo `preview.py`), `preparar(stage_dir)`, `ambiente(chrome, chrome_versao, ffmpeg, ffprobe, sandbox_dir, guard_log)`, `comando_render(node, stage_dir, saida, fps, qualidade)`, `comando_selftest(node)` e `comando_selftest_arquivos(node)`. O motor precisa respeitar a lista de pastas permitidas que o `render.py` passa em `VBSS_FILE_GUARD_RAIZES` (log em `VBSS_FILE_GUARD_LOG`) e recusar leitura fora dela, como faz o `file-guard.cjs`. Se o motor não for Node, o adaptador adapta (o `render.py` só executa o comando que ele devolve).
3. Trocar `motor.json` para `{"ativo": "<novo>"}`.
4. Reescrever a seção "Como escrever uma composição" deste arquivo e o `guide/` do novo motor.
5. Rodar `setup.py`, `doctor.py`, e um render real com `prova-local.ps1` (seção "Como rodar a prova").
6. Composições antigas continuam no formato do motor antigo; reaproveitar é reescrever pela regra nova.

## Estrutura

```text
content-engine/video/
  MOTOR.md            este arquivo
  motor.json          qual motor está ativo
  setup.py            instalação única
  doctor.py           diagnóstico PASS/FAIL
  render.py           render com checagens e isolamento
  frames.py           frames PNG para revisão
  preview.py          prévia no navegador (servidor local, _motor/ em memória)
  preview_barra.html  barra de controle que a prévia injeta no index.html
  montar_reel.py      monta o Reel a partir do roteiro.json (voz, tempos, legenda, efeitos, musica, marca)
  reel_tempos.py      calculo puro: palavra para momento, encaixe no compasso, ancora e escolha de efeito
  reel_cenas.py       catalogo de cenas e estilos por marca (gera o HTML, o CSS e a timeline)
  apontar.py          coordenadas do alvo no print (regua no navegador ou recorte para conferir)
  checar_reel.py      checagem automatica de motion do video renderizado
  tests/              test_reel_tempos.py (tempos, pronuncia, compasso, ancora e limites da checagem), test_reel_cenas.py (cenas passos e abertura), test_reel_ouvidas.py (liberacao de fala ouvida por uma pessoa)
  prova-local.ps1     render monitorado (gera a prova)
  kit/motion.js       kit de motion (montado em _motor/kit/ pelo render e pela prévia)
  _comum.py           funções do vídeo (caminhos, FFmpeg, motor ativo, ffprobe) sobre content-engine/common/
  engines/hyperframes/
    package.json, package-lock.json, .npmrc
    adapter.py        tudo que é específico do HyperFrames
    net-guard.cjs     bloqueio de rede do Node e aplicação das flags do Chrome
    net-guard-selftest.cjs
    file-guard.cjs    guarda de arquivos: o motor só lê dentro da composição e das pastas do motor
    file-guard-selftest.cjs
    guide/             conhecimento de autoria (adaptado das skills do HyperFrames, Apache-2.0; ver guide/NOTICE.md)
```

Compartilhado com o motor de imagem (`content-engine/image/MOTOR.md`): `content-engine/common/` (navegador fixo e escolha do navegador, flags de isolamento, ambiente isolado, checagem de URL externa, lista fechada de tipos de arquivo da composição) e `content-engine/fonts/` (fontes locais com SHA-256).
