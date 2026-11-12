import argparse
import html
import os
import shutil
import sys
import time
import urllib.parse
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
from _navegador import Navegador
from _servidor import Servidor

MARGEM = 24
CABECALHO = 64
LEGENDA = 48


def main():
    p = argparse.ArgumentParser(description="Folha de contato: miniaturas de todos os PNG de uma pasta numa imagem so, para revisar o lote lado a lado.")
    p.add_argument("pasta", help="pasta com os PNG (ex.: <pasta do produto>/out/<slug>)")
    p.add_argument("saida", help="arquivo .png da folha")
    p.add_argument("--colunas", type=int, default=4)
    p.add_argument("--largura", type=int, default=270, help="largura de cada miniatura em px (150 para o teste de miniatura da capa)")
    a = p.parse_args()

    pasta = Path(a.pasta).resolve()
    saida = Path(a.saida).resolve()
    if not pasta.is_dir():
        c.falhar(f"pasta nao encontrada: {pasta}")
    if saida.suffix.lower() != ".png":
        c.falhar("a saida precisa terminar em .png")
    if a.colunas < 1 or a.largura < 60:
        c.falhar("--colunas precisa ser 1 ou mais e --largura 60 ou mais")
    pngs = []
    for arq in sorted(pasta.glob("*.png")):
        if arq.resolve() == saida:
            continue
        dims = c.png_dimensoes(arq)
        if dims:
            pngs.append((arq, dims))
    if not pngs:
        c.falhar(f"nenhum PNG em {pasta}")

    colunas = min(a.colunas, len(pngs))
    linhas = [pngs[i:i + colunas] for i in range(0, len(pngs), colunas)]
    alturas = [max(round(a.largura * h / w) for _, (w, h) in linha) for linha in linhas]
    largura_total = colunas * a.largura + (colunas + 1) * MARGEM
    altura_total = CABECALHO + sum(h + LEGENDA + MARGEM for h in alturas) + MARGEM

    celulas = []
    for linha, h in zip(linhas, alturas):
        for arq, (w, hh) in linha:
            nome = html.escape(arq.name)
            src = "/" + urllib.parse.quote(arq.name)
            celulas.append(
                f'<figure><div class="img" style="height:{round(a.largura * hh / w)}px">'
                f'<img src="{src}" alt="{nome}"></div><figcaption><b>{nome}</b><span>{w}x{hh}</span></figcaption></figure>'
            )
    titulo = html.escape(f"{pasta.name}: {len(pngs)} imagem(ns)")
    pagina = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Inter';font-weight:600;src:url('/_motor/fonts/inter-600.woff2') format('woff2')}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:100vw;height:100vh;overflow:hidden;background:#2a2a2e;color:#f2f2f2;font-family:Inter,sans-serif;font-weight:600}}
header{{height:{CABECALHO}px;display:flex;align-items:center;padding:0 {MARGEM}px;font-size:22px}}
main{{display:grid;grid-template-columns:repeat({colunas},{a.largura}px);gap:{MARGEM}px;padding:0 {MARGEM}px {MARGEM}px}}
.img{{width:{a.largura}px;display:flex;align-items:flex-start;justify-content:center}}
img{{max-width:100%;max-height:100%;outline:1px solid #55555c}}
figcaption{{height:{LEGENDA}px;padding-top:6px;font-size:{min(15, a.largura // 13)}px;line-height:1.3}}
figcaption b{{display:block;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
figcaption span{{display:block;color:#a0a0a8}}
</style></head><body><header>{titulo}</header><main>{''.join(celulas)}</main></body></html>
"""
    trabalho = c.sandbox_paths()["folha"] / f"{os.getpid()}-{int(time.time() * 1000)}"
    trabalho.mkdir(parents=True, exist_ok=True)
    indice = trabalho / "index.html"
    indice.write_text(pagina, encoding="utf-8")
    try:
        srv = Servidor(pasta)
        with Navegador() as nav:
            info = nav.capturar(srv, indice, largura_total, altura_total, saida)
    finally:
        shutil.rmtree(trabalho, ignore_errors=True)
    problemas = info.get("quebradas") or info.get("bloqueados") or srv.faltando_desde(0)
    if problemas or info.get("estado") != "ok":
        c.falhar(f"a folha saiu incompleta: {problemas or info.get('estado')}")
    c.linha("OK", f"folha com {len(pngs)} miniatura(s) em {colunas} coluna(s)", f"{saida} ({largura_total}x{altura_total})")
    print("Abra a folha e olhe o lote junto: silhueta, cor dominante, texto legivel na miniatura. Depois olhe cada PNG em tamanho real.")


if __name__ == "__main__":
    main()
