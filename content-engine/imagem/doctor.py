import sys

sys.dont_write_bytecode = True

import _comum as c
from _navegador import Navegador, argumentos
from _servidor import Servidor
from comum import fontes as fontes_comuns
from comum.urls import urls_externas_no_texto

resultados = []

CANARIOS = ("https://vbss-canario.invalid/x.png", "http://192.0.2.1/teste")

PAGINA_TESTE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><style>
@font-face{font-family:'Press Start 2P';font-weight:400;src:url('/_motor/fonts/press-start-2p-400.woff2') format('woff2')}
@font-face{font-family:'Inter';font-weight:600;src:url('/_motor/fonts/inter-600.woff2') format('woff2')}
html,body{margin:0;width:100vw;height:100vh;background:#1B1240;color:#fff}
.px{font-family:'Press Start 2P';font-size:16px;padding:12px}
.tx{font-family:Inter,sans-serif;font-weight:600;font-size:18px;padding:0 12px}
</style></head><body>
<div class="px">AUTO-TESTE</div><div class="tx">Coleção ótima, ação já</div>
<img src="%s" alt="" style="display:none">
<script>fetch('%s').catch(() => null)</script>
</body></html>
"""


def item(nome, ok, detalhe=""):
    resultados.append(ok)
    c.linha("PASS" if ok else "FAIL", nome, detalhe)


def checar_base():
    c.titulo("Base")
    item("Python 3.10+", sys.version_info >= (3, 10), sys.version.split()[0])
    return checar_navegador()


def checar_navegador():
    c.titulo("Navegador")
    chrome = c.find_chrome()
    if chrome is None:
        item("navegador encontrado", False, "rode python content-engine/imagem/setup.py (instala o navegador fixo)")
        return None
    if c.e_navegador_fixo(chrome):
        problemas = c.navegador_fixado.conferir()
        item("navegador fixo em uso, com SHA-256 conferido", not problemas, "; ".join(problemas) or c.descrever_navegador(chrome))
    else:
        c.linha("AVISO", c.descrever_navegador(chrome), c.AVISO_SISTEMA)
    return chrome


def checar_fontes():
    c.titulo("Fontes locais (content-engine/fontes)")
    problemas = fontes_comuns.conferir()
    item("arquivos de fonte presentes e com SHA-256 do fontes.json", not problemas,
         f"{len(fontes_comuns.arquivos())} arquivos" if not problemas else "; ".join(problemas))
    licencas = sorted(p.name for p in fontes_comuns.FONTES_DIR.glob("LICENCA-*.txt"))
    item("licencas das fontes junto dos arquivos", len(licencas) >= 3, ", ".join(licencas) or "nenhuma")


def checar_isolamento(chrome):
    c.titulo("Isolamento (nada sai da maquina)")
    env = c.sandbox_env()
    problemas = c.assert_env_isolated(env)
    item("ambiente do Chrome sem chaves/tokens e com HOME/APPDATA/TEMP no sandbox", not problemas, "; ".join(problemas) or str(c.SANDBOX_DIR))
    args = argumentos(chrome or "chrome.exe", c.SANDBOX_DIR / "perfis" / "x")
    faltam = c.flags_faltando(args)
    item("flags de isolamento do Chrome (proxy sumidouro, DNS bloqueado, sem telemetria)", not faltam, ", ".join(faltam) or "completas")
    item("DevTools so em 127.0.0.1 (porta aleatoria, sem --remote-debugging-address)",
         "--remote-debugging-port=0" in args and not any(a.startswith("--remote-debugging-address") for a in args))
    lint = urls_externas_no_texto('<link href="https://fonts.googleapis.com/x"><svg xmlns="http://www.w3.org/2000/svg"></svg><img src="http://127.0.0.1/a.png">')
    item("checagem de URL externa pega Google Fonts e ignora localhost/xmlns", [u for _, u in lint] == ["https://fonts.googleapis.com/x"], str([u for _, u in lint]))


def checar_gitignore():
    c.titulo("Repositorio")
    gi = c.REPO_DIR / ".gitignore"
    texto = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    precisa = ["content-engine/imagem/.sandbox/", "content-engine/navegador/"]
    faltam = [p for p in precisa if p not in texto]
    item(".gitignore ignora content-engine/imagem/.sandbox/ e content-engine/navegador/", not faltam, "faltam: " + ", ".join(faltam) if faltam else str(gi))


def checar_render(chrome):
    c.titulo("Auto-teste de render")
    if not chrome:
        item("render de teste", False, "sem Chrome")
        return
    pasta = c.sandbox_paths()["doctor"]
    html = pasta / "teste.html"
    png = pasta / "teste.png"
    html.write_text(PAGINA_TESTE % CANARIOS, encoding="utf-8")
    if png.exists():
        png.unlink()
    with Navegador() as nav:
        info = nav.capturar(Servidor(pasta), html, 320, 120, png)
    dims = c.png_dimensoes(png) if png.is_file() else None
    item("PNG no tamanho exato pedido (320x120, escala 1)", dims == (320, 120), str(dims))
    item("render esperou fontes e imagens", info.get("estado") == "ok", str(info.get("estado")))
    carregadas = {(f["familia"], f["peso"]) for f in info.get("faces", []) if f.get("status") == "loaded"}
    item("fontes locais carregadas pelo Chrome", {("Press Start 2P", "400"), ("Inter", "600")} <= carregadas, str(sorted(carregadas)))
    bloqueados = info.get("bloqueados", [])
    item("pedidos de teste para fora bloqueados pelo render", all(any(b.startswith(cn) for b in bloqueados) for cn in CANARIOS), ", ".join(bloqueados) or "nenhum bloqueio registrado")


def main():
    print("Diagnostico do motor de imagem local do vbss-media-engine")
    chrome = checar_base()
    checar_fontes()
    checar_isolamento(chrome)
    checar_gitignore()
    checar_render(chrome)
    falhas = resultados.count(False)
    print(f"\nResultado: {len(resultados) - falhas} PASS, {falhas} FAIL")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
