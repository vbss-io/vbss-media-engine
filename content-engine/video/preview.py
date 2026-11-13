import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True

import _comum as c
from common import arquivos

HOST = "127.0.0.1"
PORTA_PADRAO = 4790
TENTATIVAS_DE_PORTA = 20
PASTA_DO_MOTOR = "_motor/"
BARRA = c.VIDEO_DIR / "preview_barra.html"
HOSTS_ACEITOS = ("127.0.0.1", "localhost")
TIPOS = {
    ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8", ".vtt": "text/vtt; charset=utf-8",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".avif": "image/avif",
    ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf", ".otf": "font/otf",
    ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".oga": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".flac": "audio/flac", ".opus": "audio/ogg", ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
}
FAIXA = re.compile(r"bytes=(\d*)-(\d*)$")


def recursos_do_motor(motor):
    if not hasattr(motor, "recursos"):
        c.falhar(f"o motor '{motor.NOME}' nao expoe recursos(): a previa nao sabe montar {PASTA_DO_MOTOR}")
    return {rel: Path(origem) for rel, origem in motor.recursos().items() if Path(origem).is_file()}


def resolver(comp_dir, recursos, caminho):
    rel = unquote(urlsplit(caminho).path).replace("\\", "/").lstrip("/")
    if not rel or rel.endswith("/"):
        rel += "index.html"
    if rel.startswith(PASTA_DO_MOTOR):
        return recursos.get(rel[len(PASTA_DO_MOTOR):])
    alvo = (comp_dir / rel).resolve()
    if comp_dir not in alvo.parents or not alvo.is_file():
        return None
    if alvo.suffix.lower() not in arquivos.EXT_PERMITIDAS or alvo.name.lower().startswith(".env"):
        return None
    return alvo


def injetar(html, t):
    inicio = "<script>window.__timelines = window.__timelines || {}; window.__previa = " + json.dumps({"t": t}) + ";</script>"
    barra = BARRA.read_text(encoding="utf-8")
    achou = re.search(r"<head[^>]*>", html, flags=re.I)
    html = html[:achou.end()] + inicio + html[achou.end():] if achou else inicio + html
    fim = html.lower().rfind("</body>")
    return html[:fim] + barra + html[fim:] if fim >= 0 else html + barra


def faixa_pedida(cabecalho, total):
    achou = FAIXA.match((cabecalho or "").strip())
    if not achou or (not achou.group(1) and not achou.group(2)):
        return None
    if not achou.group(1):
        de = max(0, total - int(achou.group(2)))
        ate = total - 1
    else:
        de = int(achou.group(1))
        ate = min(int(achou.group(2)), total - 1) if achou.group(2) else total - 1
    return (de, ate) if de <= ate < total else None


def criar_handler(comp_dir, recursos, t):
    indice = (comp_dir / "index.html").resolve()

    class Previa(BaseHTTPRequestHandler):
        server_version = "vbss-media-engine-previa"
        protocol_version = "HTTP/1.1"

        def log_message(self, formato, *args):
            if args and str(args[1] if len(args) > 1 else "").startswith(("4", "5")):
                print(f"   [{args[1]}] {self.path}", flush=True)

        def recusar(self, codigo, texto):
            corpo = texto.encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(corpo)

        def responder(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in HOSTS_ACEITOS:
                return self.recusar(403, "a previa so atende em 127.0.0.1")
            alvo = resolver(comp_dir, recursos, self.path)
            if alvo is None:
                return self.recusar(404, "nao encontrado na composicao nem em _motor/")
            if alvo == indice:
                corpo = injetar(alvo.read_text(encoding="utf-8"), t).encode("utf-8")
            else:
                corpo = alvo.read_bytes()
            total = len(corpo)
            faixa = faixa_pedida(self.headers.get("Range"), total)
            if faixa:
                de, ate = faixa
                corpo = corpo[de:ate + 1]
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {de}-{ate}/{total}")
            else:
                self.send_response(200)
            self.send_header("Content-Type", TIPOS.get(alvo.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(corpo)

        def do_GET(self):
            try:
                self.responder()
            except (ConnectionError, TimeoutError):
                pass

        do_HEAD = do_GET

    return Previa


def abrir_servidor(handler, porta):
    candidatas = [porta] if porta else range(PORTA_PADRAO, PORTA_PADRAO + TENTATIVAS_DE_PORTA)
    for candidata in candidatas:
        try:
            return ThreadingHTTPServer((HOST, candidata), handler)
        except OSError:
            continue
    c.falhar(f"porta {porta} ocupada: escolha outra com --porta" if porta else f"nenhuma porta livre entre {PORTA_PADRAO} e {PORTA_PADRAO + TENTATIVAS_DE_PORTA - 1}: use --porta")


def main():
    p = argparse.ArgumentParser(description="Previa local de uma composicao de video no navegador, com _motor/ resolvido em memoria. Nao e o render: a prova final continua sendo render.py + frames.py.")
    p.add_argument("composicao", help="pasta da composicao (com index.html)")
    p.add_argument("--porta", type=int, help=f"porta em 127.0.0.1 (padrao: a primeira livre a partir de {PORTA_PADRAO})")
    p.add_argument("--t", type=float, default=0.0, help="segundo em que a previa abre")
    a = p.parse_args()

    comp_dir = Path(a.composicao).resolve()
    if not (comp_dir / "index.html").is_file():
        c.falhar(f"{comp_dir} nao tem index.html")
    motor = c.load_motor()
    recursos = recursos_do_motor(motor)
    ThreadingHTTPServer.daemon_threads = True
    servidor = abrir_servidor(criar_handler(comp_dir, recursos, max(0.0, a.t)), a.porta)
    porta = servidor.server_address[1]

    c.titulo("Previa (nao e o render)")
    c.linha("OK", "composicao", str(comp_dir))
    c.linha("OK", f"{PASTA_DO_MOTOR} servido da instalacao do motor '{motor.NOME}'", f"{len(recursos)} arquivo(s) (gsap, fontes, kit); nada e gravado na pasta da composicao")
    c.linha("AVISO", "isto e uma previa", "roda no seu navegador, com tempo e audio aproximados; a prova final e o render.py seguido do frames.py")
    print(f"\n   Abra: http://{HOST}:{porta}/" + (f"?t={a.t:g}" if a.t else ""))
    print("   Espaco toca e pausa, setas andam um quadro (Shift: 1 s). Ctrl+C encerra.\n", flush=True)
    try:
        servidor.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    print("previa encerrada.")


if __name__ == "__main__":
    main()
