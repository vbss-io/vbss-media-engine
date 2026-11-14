import argparse
import json
import mimetypes
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
import montar_reel

PORTA = 4795
MARGEM = 140
PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Apontar no print</title>
<style>
  body{margin:0;background:#15161c;color:#eee;font-family:Segoe UI,Arial,sans-serif}
  #topo{position:fixed;left:0;right:0;top:0;z-index:5;background:#22242e;padding:10px 16px;border-bottom:1px solid #3a3d4d;font-size:15px}
  #topo b{color:#ffcb52}
  #lista{position:fixed;right:0;top:86px;bottom:0;width:430px;overflow:auto;background:#1b1c24;border-left:1px solid #3a3d4d;padding:12px;box-sizing:border-box;font-size:14px}
  #lista .it{background:#262836;border:1px solid #3a3d4d;border-radius:8px;padding:8px 10px;margin-bottom:8px}
  #lista code{display:block;font-family:Consolas,monospace;font-size:14px;color:#9be7c4;margin:4px 0;user-select:all}
  #lista button{background:#ffcb52;border:0;border-radius:6px;padding:5px 10px;font-weight:700;cursor:pointer;margin-right:6px}
  #palco{position:absolute;left:46px;top:112px;cursor:crosshair;user-select:none}
  #palco img{display:block;-webkit-user-drag:none}
  .lin{position:absolute;background:rgba(255,203,82,.28);pointer-events:none}
  .num{position:absolute;font:12px Consolas,monospace;color:#ffcb52;pointer-events:none}
  .cx{position:absolute;box-sizing:border-box;border:2px solid #3ac2d4;background:rgba(58,194,212,.18);pointer-events:none}
  .cx span{position:absolute;left:0;top:-18px;font:12px Consolas,monospace;background:#3ac2d4;color:#10212a;padding:1px 5px}
  #mira{position:fixed;left:16px;bottom:10px;z-index:6;background:#22242e;border:1px solid #3a3d4d;border-radius:6px;padding:4px 10px;font:14px Consolas,monospace}
</style>
</head>
<body>
<div id="topo"><b>__NOME__</b> - coordenadas na largura <b>__LARGURA__</b> px (o mesmo numero que vai em <code>largura_do_print</code>; sem esse campo, e a largura real do arquivo).<br>
Clique e arraste em volta do alvo. Cada retangulo vira uma linha pronta para colar no <code>"alvo"</code> do roteiro. A linha amarela marca cada 100 px.</div>
<div id="palco"><img id="img" src="/print" alt=""></div>
<div id="lista"><div id="vazio">Nenhum alvo marcado ainda.</div></div>
<div id="mira">x 0, y 0</div>
<script>
  const LOGICA = __LARGURA__;
  const img = document.getElementById("img");
  const palco = document.getElementById("palco");
  const lista = document.getElementById("lista");
  const mira = document.getElementById("mira");
  let fator = 1;
  let inicio = null;
  let atual = null;
  let n = 0;
  img.onload = () => {
    const cabe = Math.min(1, (window.innerWidth - 46 - 450) / img.naturalWidth);
    img.style.width = Math.round(img.naturalWidth * cabe) + "px";
    fator = LOGICA / img.clientWidth;
    const alto = img.clientHeight;
    for (let v = 0; v * 100 / fator < alto; v++) {
      const y = v * 100 / fator;
      const l = document.createElement("div");
      l.className = "lin";
      l.style.cssText = "left:0;width:100%;height:1px;top:" + y + "px";
      palco.appendChild(l);
      const t = document.createElement("div");
      t.className = "num";
      t.style.cssText = "left:-42px;top:" + (y - 7) + "px";
      t.textContent = v * 100;
      palco.appendChild(t);
    }
    for (let v = 0; v * 100 / fator < img.clientWidth; v++) {
      const x = v * 100 / fator;
      const l = document.createElement("div");
      l.className = "lin";
      l.style.cssText = "top:0;height:100%;width:1px;left:" + x + "px";
      palco.appendChild(l);
      const t = document.createElement("div");
      t.className = "num";
      t.style.cssText = "top:-16px;left:" + (x - 10) + "px";
      t.textContent = v * 100;
      palco.appendChild(t);
    }
  };
  const ponto = (ev) => {
    const r = img.getBoundingClientRect();
    return { x: Math.max(0, Math.min(r.width, ev.clientX - r.left)), y: Math.max(0, Math.min(r.height, ev.clientY - r.top)) };
  };
  palco.addEventListener("mousedown", (ev) => {
    inicio = ponto(ev);
    atual = document.createElement("div");
    atual.className = "cx";
    palco.appendChild(atual);
    ev.preventDefault();
  });
  window.addEventListener("mousemove", (ev) => {
    const p = ponto(ev);
    mira.textContent = "x " + Math.round(p.x * fator) + ", y " + Math.round(p.y * fator);
    if (!inicio) return;
    atual.style.left = Math.min(inicio.x, p.x) + "px";
    atual.style.top = Math.min(inicio.y, p.y) + "px";
    atual.style.width = Math.abs(p.x - inicio.x) + "px";
    atual.style.height = Math.abs(p.y - inicio.y) + "px";
  });
  window.addEventListener("mouseup", (ev) => {
    if (!inicio) return;
    const p = ponto(ev);
    const caixa = { x: Math.round(Math.min(inicio.x, p.x) * fator), y: Math.round(Math.min(inicio.y, p.y) * fator), w: Math.round(Math.abs(p.x - inicio.x) * fator), h: Math.round(Math.abs(p.y - inicio.y) * fator) };
    inicio = null;
    if (caixa.w < 4 || caixa.h < 4) { atual.remove(); return; }
    n += 1;
    const rotulo = document.createElement("span");
    rotulo.textContent = n;
    atual.appendChild(rotulo);
    const texto = '"alvo": ' + JSON.stringify(caixa).replace(/"(\\w)":/g, '"$1": ').replace(/,/g, ", ");
    document.getElementById("vazio").style.display = "none";
    const item = document.createElement("div");
    item.className = "it";
    const caixaDesenhada = atual;
    item.innerHTML = "<b>Alvo " + n + "</b><code></code><button>copiar</button><button>apagar</button>";
    item.querySelector("code").textContent = texto;
    const [copiar, apagar] = item.querySelectorAll("button");
    copiar.onclick = () => { navigator.clipboard.writeText(texto); copiar.textContent = "copiado"; };
    apagar.onclick = () => { item.remove(); caixaDesenhada.remove(); };
    lista.appendChild(item);
    fetch("/marcar", { method: "POST", body: JSON.stringify(caixa) });
  });
</script>
</body>
</html>
"""


def conferir(imagem, largura, caixa, saida):
    w, h = montar_reel.dimensoes_da_imagem(imagem)
    f = w / largura
    x, y, cw, ch = (round(v * f) for v in caixa)
    if cw <= 0 or ch <= 0 or x < 0 or y < 0 or x + cw > w or y + ch > h:
        c.falhar(f"o alvo {caixa} nao cabe no print ({largura:g} x {h / f:.0f} na largura informada)")
    m = round(MARGEM * f)
    rx, ry = max(0, x - m), max(0, y - m)
    rw, rh = min(w, x + cw + m) - rx, min(h, y + ch + m) - ry
    borda = max(3, round(4 * f))
    filtro = f"drawbox=x={x}:y={y}:w={cw}:h={ch}:color=yellow@0.9:t={borda},crop={rw}:{rh}:{rx}:{ry}"
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(c.ffmpeg_path()), "-v", "error", "-y", "-i", str(imagem), "-vf", filtro, "-frames:v", "1", "-update", "1", str(saida)], capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not Path(saida).is_file():
        c.falhar(f"nao consegui gravar o recorte: {r.stderr.strip()[-300:]}")
    c.linha("OK", "recorte gravado", f"{saida} - abra a imagem: o retangulo amarelo tem de cercar o alvo certo")


def servir(imagem, largura, porta, abrir=True):
    pagina = PAGINA.replace("__NOME__", imagem.name).replace("__LARGURA__", f"{largura:g}").encode("utf-8")
    tipo = mimetypes.guess_type(imagem.name)[0] or "image/png"

    class Tratador(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _local(self):
            return (self.headers.get("Host") or "").split(":")[0] in ("127.0.0.1", "localhost")

        def do_GET(self):
            if not self._local():
                self.send_error(403)
                return
            if self.path == "/":
                corpo, cabecalho = pagina, "text/html; charset=utf-8"
            elif self.path == "/print":
                corpo, cabecalho = imagem.read_bytes(), tipo
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", cabecalho)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_POST(self):
            if not self._local() or self.path != "/marcar":
                self.send_error(403)
                return
            try:
                caixa = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 400)))
                print('   "alvo": ' + json.dumps({k: int(caixa[k]) for k in ("x", "y", "w", "h")}), flush=True)
            except (ValueError, KeyError, TypeError):
                pass
            self.send_response(204)
            self.end_headers()

    servidor = None
    for tentativa in range(20):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", porta + tentativa), Tratador)
            break
        except OSError:
            continue
    if servidor is None:
        c.falhar(f"nenhuma porta livre entre {porta} e {porta + 19}")
    endereco = f"http://127.0.0.1:{servidor.server_address[1]}/"
    c.titulo(f"Apontar em {imagem.name} (coordenadas na largura {largura:g})")
    print(f"   Abra {endereco} , arraste em volta de cada alvo e copie a linha para o roteiro. Ctrl+C encerra.")
    if abrir:
        webbrowser.open(endereco)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


def main():
    p = argparse.ArgumentParser(description="Tira do print as coordenadas de um alvo (foco, marca, camera) sem medir pixel no olho: abre o print com regua no navegador e devolve a linha \"alvo\" do roteiro. Com --conferir, grava o recorte de um alvo para olhar.")
    p.add_argument("print", help="imagem do print (png ou jpg)")
    p.add_argument("--largura", type=float, help="largura logica das coordenadas (o 'largura_do_print' da cena); padrao: a largura real do arquivo")
    p.add_argument("--conferir", help="x,y,w,h de um alvo: grava o recorte com o retangulo desenhado em vez de abrir o navegador")
    p.add_argument("--saida", help="arquivo PNG do recorte (com --conferir)")
    p.add_argument("--porta", type=int, default=PORTA)
    p.add_argument("--sem-abrir", action="store_true", help="nao abre o navegador sozinho; so mostra o endereco")
    a = p.parse_args()
    imagem = Path(a.print).resolve()
    if not imagem.is_file():
        c.falhar(f"print nao encontrado: {imagem}")
    largura = a.largura or montar_reel.dimensoes_da_imagem(imagem)[0]
    if a.conferir:
        try:
            caixa = [float(v) for v in a.conferir.split(",")]
            assert len(caixa) == 4
        except (ValueError, AssertionError):
            c.falhar("--conferir pede quatro numeros: x,y,w,h")
        if not a.saida:
            c.falhar("--conferir pede --saida <arquivo.png>")
        conferir(imagem, largura, caixa, Path(a.saida).resolve())
        return
    servir(imagem, largura, a.porta, not a.sem_abrir)


if __name__ == "__main__":
    main()
