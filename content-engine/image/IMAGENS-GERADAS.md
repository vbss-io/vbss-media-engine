# Imagens e vídeos de fora nas peças

O motor não gera imagem nem filmagem: ele renderiza o que está na pasta da peça. Quando o vídeo ou o cartão pede uma imagem ou um clipe que não existe (fundo, ilustração, cena, textura, um trecho em movimento), ele vem de fora e entra na peça com o `importar.py`. O render continua 100% local.

A mídia pode vir de onde você quiser: gerada por IA em qualquer serviço, de um banco de imagens ou de vídeos, material seu. Uma opção pronta, e opcional, é o conector do [Imaginaria](https://www.imaginaria.vbss.io/conectores), que dá ao seu agente (Claude, ChatGPT, Codex e outros clientes MCP) acesso a vários modelos de imagem e de vídeo numa conta só, sem sair da conversa.

## Quando usar

- Fundo de abertura ou de fecho, ilustração de um conceito, cena de produto, textura.
- Não use para texto, números, logo ou tela de sistema: isso é HTML na composição, que sai nítido e editável. Imagem gerada erra letras.
- Uma ou duas imagens fortes valem mais que uma por cena.
- Clipe de vídeo gerado serve de fundo em movimento ou de cena de abertura. Custa bem mais que imagem (o preço é por segundo): prefira clipes curtos, de 3 a 6 segundos, e use imagem com movimento de câmera no resto.

## Opção: gerar pelo conector do Imaginaria

- **Claude Code:** `claude mcp add --transport http imaginaria https://imaginaria-api.vbss.io/mcp`, depois `/mcp`, escolher `imaginaria` e entrar na conta pelo navegador.
- **Claude (web e desktop):** Configurações > Conectores > conector personalizado, com a URL `https://imaginaria-api.vbss.io/mcp`.
- **Outros clientes:** veja a página de conectores.
- Conectar é grátis. Cada geração gasta créditos comprados da sua conta (os de teste grátis não valem pelo conector), e as imagens ficam privadas na sua galeria por padrão.

## Fluxo para o agente (com o conector)

1. **Escolher o modelo e avisar o custo.** `list_models` (com `kind` `image` ou `video`) e `estimate_cost` dizem quanto cada geração custa em créditos; `get_balance` mostra o saldo. Vídeo é cobrado por segundo.
2. **Gerar na proporção da peça.** `generate_image` (ou `generate_video`, com a duração em segundos) com `aspect_ratio` igual ao da área que a imagem vai ocupar (`9:16` para fundo de vídeo vertical 1080x1920; `16:9` para horizontal; `4:5` ou `3:4` para cartão 1080x1350), `max_credits` como teto e um `idempotency_key` novo por imagem.
3. **Esperar terminar.** `get_generation` até `status` ser `completed`; o resultado traz `media_url`.
4. **Trazer para a peça.**

   ```bash
   python content-engine/image/importar.py "<media_url>" <pasta-da-peca> --nome fundo-abertura --prompt "<prompt usado>" --modelo <modelo>
   python content-engine/image/importar.py <arquivo-local.png> <pasta-da-peca> --nome fundo-abertura
   ```

   A primeira linha baixa de uma URL `https`; a segunda copia um arquivo que já está na máquina (imagem de qualquer outra origem). O arquivo vai para `assets/gerado/` e a origem fica registrada em `assets/gerado/origem.json`. A origem é gravada sem o `https://` na frente, porque o render recusa qualquer endereço de internet dentro da pasta da peça.
5. **Usar na composição.** Imagem no vídeo: `<img src="assets/gerado/fundo-abertura.webp">`; na peça de imagem: `<img src="/assets/gerado/fundo-abertura.webp">`. Clipe no vídeo: `<video src="assets/gerado/abertura.mp4" muted playsinline data-start="0" data-duration="5" data-track-index="1"></video>`, direto na raiz da composição (não dentro de uma seção com tempo); os detalhes estão em `content-engine/video/engines/hyperframes/guide/core/variables-and-media.md`.
6. **Renderizar** como sempre (`preview.py` para ver, `render.py` para entregar).

## Como a mídia entra bem no vídeo

- Cubra a área com `object-fit: cover` e deixe a imagem um pouco maior que o quadro, para poder mover sem aparecer borda.
- Movimento lento e contínuo (escala de 1,00 a 1,06 ou deslocamento de poucos por cento ao longo da cena) dá vida sem distrair. Sem movimento, a cena parece slide.
- Texto por cima pede um véu: gradiente escuro atrás do texto ou a imagem escurecida, para manter contraste.
- Peça no prompt espaço vazio onde o texto vai ficar ("área livre no terço superior") e o estilo da marca (paleta, traço), para a imagem conversar com o resto.
- Mantenha um estilo só por peça: mesmo modelo e mesma descrição de estilo em todas as imagens.
- Clipe gerado entra sem som (`muted`); a trilha da peça (voz, música, efeitos) continua vindo do `trilha.py`.

## O que o `importar.py` confere

- Aceita URL `https` de qualquer site (sem usuário, senha ou porta fora da 443, e sem seguir redirecionamento) ou um arquivo local.
- O conteúdo precisa ser imagem (PNG, JPEG, WebP) ou vídeo (MP4, MOV, WebM) de verdade, conferido pelos primeiros bytes; qualquer outra coisa é recusada.
- Teto de 25 MB para imagem e 300 MB para vídeo (`--teto-mb` muda).
- Grava só em `assets/gerado/` da peça, com nome de letras minúsculas, números e hífen.

É o único passo deste fluxo que usa rede, e ele só baixa: nada da sua peça é enviado. Com arquivo local, não há rede nenhuma. O prompt vai para o serviço de geração pelo conector do agente, não pelo motor.

## Direitos de uso

O uso de cada imagem ou vídeo é responsabilidade de quem o gera ou escolhe: valem os termos do serviço e do modelo de onde ela veio. O `origem.json` guarda a origem, o modelo e o prompt de cada uma.
