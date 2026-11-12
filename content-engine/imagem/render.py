import argparse
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
from _navegador import Navegador
from _servidor import ORIGEM, Servidor, raiz_e_paginas


def entradas(origem, saida):
    origem = Path(origem).resolve()
    saida = Path(saida).resolve()
    if origem.is_dir():
        htmls = sorted(p for p in origem.glob("*.html") if p.is_file())
        if not htmls:
            c.falhar(f"nenhum .html em {origem}")
        if saida.suffix.lower() == ".png":
            c.falhar("para uma pasta de HTMLs a saida precisa ser uma pasta, nao um .png")
        return [(h, saida / f"{h.stem}.png") for h in htmls]
    if not origem.is_file() or origem.suffix.lower() not in (".html", ".htm"):
        c.falhar(f"entrada precisa ser um .html ou uma pasta com .html: {origem}")
    if saida.suffix.lower() == ".png":
        return [(origem, saida)]
    return [(origem, saida / f"{origem.stem}.png")]


def resumo_fontes(faces):
    carregadas = {}
    for f in faces:
        if f.get("status") == "loaded":
            carregadas.setdefault(f["familia"], set()).add(f["peso"])
    return ", ".join(f"{fam} {'/'.join(sorted(pesos))}" for fam, pesos in sorted(carregadas.items())) or "nenhuma @font-face (so fontes do sistema)"


def main():
    p = argparse.ArgumentParser(description="Renderiza HTML em PNG com o navegador fixo (chrome-headless-shell), isolado e sem rede externa (content-engine/imagem).")
    p.add_argument("entrada", help="arquivo .html ou pasta com varios .html (lote)")
    p.add_argument("saida", help="arquivo .png (uma peca) ou pasta (lote: <nome>.png para cada <nome>.html)")
    p.add_argument("--formato", choices=sorted(c.FORMATOS), default="feed", help="feed 1080x1350, story 1080x1920, quadrado 1080x1080, og 1200x630")
    p.add_argument("--tamanho", help="tamanho livre LARGURAxALTURA (ex.: 1280x640); vence o --formato")
    p.add_argument("--raiz", help="pasta servida como / (padrao: a pasta do produto onde o HTML esta)")
    a = p.parse_args()

    largura, altura = c.tamanho(a.formato, a.tamanho)
    pares = entradas(a.entrada, a.saida)
    htmls = [h for h, _ in pares]
    raiz, aviso_raiz = raiz_e_paginas(htmls, a.raiz)

    c.titulo("Checagens antes do render")
    if aviso_raiz:
        c.linha("ATENCAO", aviso_raiz)
    c.linha("OK", "pasta servida como /", str(raiz))
    urls = c.checar_urls(htmls, raiz)
    if urls:
        linhas = []
        for arq, ln, url in urls:
            dica = c.dica_url(url)
            linhas.append(f"{arq}:{ln}  {url}" + (f"\n      -> {dica}" if dica else ""))
        c.falhar("a peca aponta para endereco de internet (BLOQUEADO). Fontes e imagens precisam ser locais:\n  " + "\n  ".join(linhas))
    c.linha("OK", "nenhuma URL externa no HTML nem nos CSS/JS locais que ele usa")

    erros = 0
    externos = []
    inicio = time.time()
    srv = Servidor(raiz)
    with Navegador() as nav:
        if c.e_navegador_fixo(nav.chrome):
            c.linha("OK", "navegador fixo isolado", f"{nav.versao} em {nav.chrome}; perfil e casa em {c.SANDBOX_DIR}")
        else:
            c.linha("AVISO", f"{c.descrever_navegador(nav.chrome)}; {c.AVISO_SISTEMA}", f"perfil e casa em {c.SANDBOX_DIR}")
        c.linha("OK", "arquivos entregues ao Chrome pelo proprio render (sem servidor, sem porta aberta)", f"{ORIGEM} -> {raiz}")
        c.titulo(f"Renderizando {len(pares)} peca(s) em {largura}x{altura}")
        for i, (html, destino) in enumerate(pares, 1):
            antes = srv.total_pedidos()
            info = nav.capturar(srv, html, largura, altura, destino)
            faltando = srv.faltando_desde(antes)
            dims = c.png_dimensoes(destino) if destino.is_file() else None
            problemas = []
            if info.get("estado") != "ok":
                problemas.append(f"fontes/imagens nao terminaram de carregar ({info.get('estado')})")
            if dims != (largura, altura):
                problemas.append(f"PNG saiu com {dims}, esperado {(largura, altura)}")
            ruins = [f"{f['familia']} {f['peso']}" for f in info.get("faces", []) if f.get("status") == "error"]
            if ruins:
                problemas.append("fonte nao carregou: " + ", ".join(ruins))
            if info.get("quebradas"):
                problemas.append("imagem quebrada: " + ", ".join(info["quebradas"]))
            if faltando:
                problemas.append("arquivo nao encontrado no servidor local: " + ", ".join(faltando))
            if info.get("bloqueados"):
                externos += info["bloqueados"]
                problemas.append("pedido para fora da pasta servida BLOQUEADO: " + ", ".join(info["bloqueados"]))
            status = "FALHOU" if problemas else "OK"
            c.linha(status, f"peca {i} de {len(pares)}: {destino}", f"{dims[0]}x{dims[1]}" if dims else "sem PNG")
            print(f"   fontes: {resumo_fontes(info.get('faces', []))}; pedidos: {info.get('pedidos', 0)}", flush=True)
            for prob in problemas:
                print(f"   ERRO: {prob}", flush=True)
            if info.get("fora"):
                print("   ATENCAO: texto passando da borda do quadro: " + " | ".join(info["fora"]), flush=True)
            if problemas:
                erros += 1

    c.titulo("Rede")
    if externos:
        c.linha("ATENCAO", f"{len(set(externos))} pedido(s) para fora foram bloqueados (nada saiu)", ", ".join(sorted(set(externos))))
    else:
        c.linha("OK", "nenhum pedido para fora da pasta servida durante o render")
    c.titulo("Resultado")
    print(f"{len(pares) - erros} de {len(pares)} PNG(s) ok em {time.time() - inicio:.1f}s. Abra e olhe cada imagem antes de entregar.")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
