# Motor de imagem local

Tudo que vira imagem estática (post, slide de carrossel, story, capa de vídeo, card) passa por aqui. Quem automatiza (script, skill ou agente) nunca abre navegador nem tira screenshot na mão: chama só os scripts deste contrato. Nada do projeto sai da máquina, e nenhuma fonte ou imagem vem da internet.

## Contrato

Todos rodam da raiz do repo, com Python 3 (só biblioteca padrão) e o navegador fixo instalado uma vez pelo `setup.py` (seção "Navegador fixo"):

```bash
python content-engine/image/setup.py
python content-engine/image/doctor.py
python content-engine/image/render.py <arquivo.html | pasta> <saida.png | pasta> [--formato feed|story|quadrado|og] [--tamanho LxA] [--raiz <pasta do produto>]
python content-engine/image/folha.py <pasta-com-pngs> <folha.png> [--colunas 4] [--largura 270]
```

- `setup.py`: instalação única do navegador fixo (`chrome-headless-shell`, SHA-256 conferido) em `content-engine/browser/`. É o único passo que usa a rede; rodar de novo não baixa nada. O `content-engine/video/setup.py` faz o mesmo passo.
- `doctor.py`: confere tudo e imprime `PASS`/`FAIL` por item (Python, navegador em uso com caminho e versão, que só passa quando é o navegador fixo com SHA-256 conferido e vira `AVISO` quando cai no Chrome do sistema, fontes locais com SHA-256, flags de isolamento do Chrome, ambiente sem chaves, `.gitignore`, e um render de teste que prova que as fontes carregam e que pedido para fora é bloqueado). Sai com código 1 se algo falhar.
- `render.py`: transforma HTML em PNG no tamanho exato pedido (escala 1, sem borda, sem barra de rolagem). Recebe um `.html` ou uma pasta: com pasta, renderiza todos os `.html` dela numa única abertura do Chrome e grava `<nome>.png` para cada `<nome>.html`. Antes de abrir o Chrome, recusa a peça se o HTML ou os CSS/JS locais que ele usa apontarem para endereço de internet. Espera fontes e imagens carregarem antes da foto. Aponta erro quando uma fonte não carregou, uma imagem não existe, um arquivo pedido não está na pasta do produto ou a página tentou falar com a internet; avisa quando um texto passa da borda do quadro. Sai com código 1 se alguma peça falhar.
- `folha.py`: folha de contato de um lote (miniaturas lado a lado com o nome do arquivo embaixo), feita com o mesmo Chrome. Serve para revisar carrossel e lote juntos e para o teste de miniatura de uma capa (`--largura 150`).

Formatos (`--formato`): `feed` 1080x1350 (padrão, também carrossel), `story` 1080x1920 (story, capa de vídeo vertical), `quadrado` 1080x1080, `og` 1200x630. Qualquer outro tamanho: `--tamanho 1280x640`.

O PNG gerado sempre precisa ser aberto e olhado antes de entregar. O `render.py` pega erro técnico; texto feio, cortado por dentro da caixa ou ilegível só quem olha vê.

## Como a peça é servida

- A raiz `/` é a **pasta do produto**. Sem `--raiz`, ela é descoberta pelo caminho do HTML: a pasta `projetos/<produto>/` (ou `projetos/archived/<produto>/`) que contém o arquivo. Por isso templates e cópias usam `/assets/<arquivo>` e funcionam igual em qualquer subpasta do produto.
- HTML fora de uma pasta `projetos/<produto>/` (ex.: `examples/card/`): passe `--raiz <pasta>` para o `/assets/` funcionar. Sem `--raiz`, a raiz vira a pasta do próprio HTML e o render avisa.
- `/_motor/fonts/<arquivo>` é reservado: entrega as fontes compartilhadas de `content-engine/fonts/` (seção Fontes).
- Não existe servidor HTTP nem porta aberta para a peça: o `render.py` entrega cada arquivo ao Chrome pelo próprio canal de controle (DevTools), no endereço fictício `http://motor.localhost`. Pedido para qualquer outro endereço é recusado ali mesmo e listado como erro. Arquivo começando com ponto (ex.: `.env`) nunca é entregue.
- Sem cache: trocou um asset, o próximo render já usa o arquivo novo (não precisa de parâmetro de versão na URL).

## Fontes

As fontes ficam uma vez só em `content-engine/fonts/` (woff2, subconjuntos latino e latino estendido, licença SIL OFL 1.1 junto, SHA-256 de cada arquivo em `fontes.json`). Os dois motores usam a mesma pasta: na imagem pelo endereço `/_motor/fonts/`, no vídeo pela pasta `_motor/fonts/` que o render monta.

- Disponíveis: `inter-{400,500,600,700,800,900}.woff2`, `press-start-2p-400.woff2`, `montserrat-{600,800}.woff2`, cada uma com a variante `-ext` (ex.: `inter-ext-600.woff2`).
- Toda família usada no CSS precisa de `@font-face` local. Modelo:

```css
@font-face{font-family:'Inter';font-style:normal;font-weight:600;font-display:swap;src:url('/_motor/fonts/inter-600.woff2') format('woff2');unicode-range:U+0000-00FF,...}
@font-face{font-family:'Inter';font-style:normal;font-weight:600;font-display:swap;src:url('/_motor/fonts/inter-ext-600.woff2') format('woff2');unicode-range:U+0100-02BA,...}
```

- Os intervalos `unicode-range` completos estão em `content-engine/fonts/fontes.json`.
- Nada de `<link>` para Google Fonts, Fontshare ou qualquer CDN: o `render.py` recusa e diz o motivo.
- Fonte nova: baixar o pacote `@fontsource/<familia>` fixado (npm, `--ignore-scripts`), copiar só os `.woff2` latino e latino estendido para `content-engine/fonts/`, a licença como `LICENCA-<familia>.txt` e registrar origem e SHA-256 no `fontes.json`. A licença precisa permitir guardar o arquivo (SIL OFL permite).

## Marcas (`content-engine/tokens.json`)

`tokens.json` guarda, por marca, cores, fontes, logo, handle, URL, idioma e tom de voz. O motor não lê esse arquivo: ele é a referência de quem escreve o HTML (pessoa ou agente). O repo traz uma marca fictícia (`exemplo`); crie uma entrada por marca sua com as mesmas chaves.

## Fluxo por peça

1. Escrever o HTML da peça (ou preencher a cópia de um template): peça única num `.html`; carrossel ou sequência numa pasta com `01.html`, `02.html`... (assim o lote sai com os nomes certos).
2. Renderizar:
   - peça única: `python content-engine/image/render.py <peca>.html <saida>/01.png`
   - carrossel ou lote: `python content-engine/image/render.py <pasta-com-htmls> <pasta-de-saida>` (gera `01.png`, `02.png`...)
   - story: o mesmo comando com `--formato story`
3. Revisar: em lote, `python content-engine/image/folha.py <pasta-de-saida> <folha.png>` e olhar a folha; depois abrir e olhar cada PNG em tamanho real.
4. Texto vazando, cortado ou ilegível: encurtar o texto ou ajustar o layout e renderizar de novo.

Exemplo pronto: `examples/card/` (ver o `README.md` da raiz).

## Dimensões de referência

- Feed e carrossel do Instagram: 1080x1350 (4:5).
- Stories, Reels e TikTok: 1080x1920 (9:16).
- OG/social card: 1200x630.
- GitHub social preview: 1280x640.

## Vídeo

Vídeo não passa por este motor: vai pelo motor de vídeo em `content-engine/video/` (contrato em `content-engine/video/MOTOR.md`). A capa de um vídeo vertical pode ser feita aqui com `--formato story`.

## Navegador fixo

- O render usa o `chrome-headless-shell` **152.0.7977.30** win64 (Chrome for Testing do Google), o mesmo navegador fixo do motor de vídeo, instalado uma vez em `content-engine/browser/` por `python content-engine/image/setup.py`. Download único de 114 MB, 270 MB no disco; SHA-256 do zip e do executável fixados em `content-engine/common/navegador.json` (registrados no primeiro download, porque o Chrome for Testing não publica SHA-256).
- Por quê: a peça sai igual em qualquer máquina e não muda quando o Chrome do PC se atualiza; o navegador fixo não tem o atualizador do Google, então o render não acorda o `GoogleUpdater`; e funciona mesmo sem Google Chrome instalado.
- Qual navegador o render usa (`content-engine/common/chrome.py`): `VBSS_BROWSER`, se apontar para um arquivo (troca manual); senão o navegador fixo instalado; senão o Chrome do sistema (e o Edge, por último), com `AVISO ... rode o setup para usar o navegador fixo` no `doctor.py` e no `render.py`.
- Flags de isolamento, casa falsa, perfil temporário e interceptação de pedidos são os mesmos com qualquer um dos navegadores. Detalhes da fixação e de como trocar de versão: seção "Navegador fixo" de `content-engine/video/MOTOR.md`.

## Garantias de localidade e como são aplicadas

- **Sem rede para a peça**: todo pedido da página passa pelo `render.py` (interceptação do DevTools). Arquivo da pasta do produto ou fonte do motor é entregue do disco; qualquer outro endereço é recusado antes de sair do Chrome e aparece como erro no fim do render.
- **Checagem antes de abrir o Chrome**: URL `http://`/`https://` que não seja `localhost`/`127.0.0.1` no HTML ou nos CSS/JS locais que ele usa faz o `render.py` parar com a lista (namespaces XML como `xmlns="http://www.w3.org/2000/svg"` são ignorados, não são baixados).
- **Chrome amarrado** com as mesmas flags do motor de vídeo (definidas uma vez em `content-engine/common/chrome.py`): `--proxy-server=http://127.0.0.1:9` (sumidouro local), `--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1`, `--disable-background-networking`, `--disable-component-update`, `--disable-sync`, `--disable-domain-reliability`, `--no-pings`, WebRTC sem UDP fora do proxy e os recursos que chamam serviço do Google desligados (Optimization Guide, Media Router, Safe Browsing aprimorado e outros). Mais `--disable-breakpad` e `--disable-crash-reporter` (sem envio de relatório de falha). Sem `--no-sandbox`.
- **Casa falsa**: o Chrome roda com `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP` em `content-engine/image/.sandbox/`, ambiente por lista branca (nenhuma variável com cara de chave ou token) e perfil novo a cada execução em `.sandbox/perfis/`, apagado no fim.
- **DevTools só em loopback**: porta aleatória em `127.0.0.1`, conectada só pelo `render.py`.
- Por que não um servidor HTTP local: há antivírus que injetam script próprio em toda página HTML servida por HTTP, inclusive em `127.0.0.1`. Entregando os arquivos pelo DevTools, nada passa pela pilha de rede e a peça sai exatamente como está no disco.

## Como rodar a prova

`prova-local.ps1` faz um render de verdade e, enquanto ele roda, amostra a árvore de processos do render e as conexões dela:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File content-engine\image\prova-local.ps1 -Entrada examples\card -Saida <pasta-de-saida> -Raiz examples\card
```

- Inicia o `render.py` e, até ele terminar, monta a árvore de processos a partir do PID do Python do render e guarda as conexões TCP e os endpoints UDP que pertencem a PIDs dessa árvore. Outros programas abertos na máquina não entram na conta: o filtro é pela árvore, não pelo nome do executável.
- Dados brutos em `content-engine/image/.sandbox/prova/` (fora do git): `resumo.json`, `conexoes.csv`, `processos.csv`, `render.log`.
- Resultado esperado: a única conexão TCP da árvore é o canal de controle `python -> navegador` em `127.0.0.1`, nenhum socket UDP, e a linha `[OK] nenhum pedido para fora da pasta servida` na saída do `render.py`.

## Estrutura

```text
content-engine/
  tokens.json         cores, fontes, tom, idioma, handle e URL de cada marca
  common/              o que os dois motores compartilham: navegador fixo (navegador.json, navegador.py) e escolha do navegador, flags de isolamento, ambiente isolado, checagem de URL, fontes
  browser/          chrome-headless-shell fixado, instalado pelo setup (fora do git)
  fonts/             woff2 locais + licenças + fontes.json (origem e SHA-256)
  image/
    MOTOR.md          este arquivo
    setup.py          instalação única do navegador fixo
    doctor.py         diagnóstico PASS/FAIL
    render.py         HTML para PNG (uma peça ou lote)
    folha.py          folha de contato para revisão
    prova-local.ps1   render monitorado (gera a prova)
    _comum.py         caminhos, formatos, checagens da peça
    _navegador.py     Chrome pelo DevTools (tudo que é específico do navegador fica aqui)
    _servidor.py      entrega dos arquivos da pasta do produto e das fontes
  video/              motor de vídeo (ver video/MOTOR.md)
```

Fora do git (`.gitignore` da raiz): `content-engine/image/.sandbox/`, `content-engine/browser/`.
