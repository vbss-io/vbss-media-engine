import threading
import urllib.parse
from pathlib import Path

import _comum as c
from common import fontes as fontes_comuns

ORIGEM = "http://motor.localhost"
ROTA_FONTES = "/_motor/fonts/"
ROTA_PAGINA = "/_pagina/"
IGNORAR_FALTANDO = {"/favicon.ico"}

TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}


class Servidor:
    def __init__(self, raiz, paginas=()):
        self.raiz = Path(raiz).resolve()
        self.paginas = []
        self.pedidos = []
        self._trava = threading.Lock()
        for p in paginas:
            self._indice_pagina(Path(p).resolve())
        self.fontes = {nome: arq.resolve() for nome, arq in fontes_comuns.arquivos().items()}

    def _indice_pagina(self, pasta):
        if pasta not in self.paginas:
            self.paginas.append(pasta)
        return self.paginas.index(pasta)

    def nosso(self, url):
        partes = urllib.parse.urlsplit(url)
        return f"{partes.scheme}://{partes.netloc}".lower() == ORIGEM

    def url_de(self, arquivo):
        arquivo = Path(arquivo).resolve()
        if arquivo.is_relative_to(self.raiz):
            return f"{ORIGEM}/{urllib.parse.quote(arquivo.relative_to(self.raiz).as_posix())}"
        i = self._indice_pagina(arquivo.parent)
        return f"{ORIGEM}{ROTA_PAGINA}{i}/{urllib.parse.quote(arquivo.name)}"

    def resolver(self, url):
        caminho = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
        partes = [p for p in caminho.split("/") if p]
        if any(p.startswith(".") or "\\" in p or ":" in p for p in partes):
            return None
        if caminho.startswith(ROTA_FONTES):
            return self.fontes.get(partes[-1]) if len(partes) == 3 else None
        if caminho.startswith(ROTA_PAGINA):
            if len(partes) < 3 or not partes[1].isdigit() or int(partes[1]) >= len(self.paginas):
                return None
            base, resto = self.paginas[int(partes[1])], partes[2:]
        else:
            base, resto = self.raiz, partes
        alvo = base.joinpath(*resto).resolve() if resto else base / "index.html"
        if not alvo.is_relative_to(base) or not alvo.is_file():
            return None
        return alvo

    def responder(self, url):
        alvo = self.resolver(url)
        caminho = urllib.parse.urlsplit(url).path
        with self._trava:
            self.pedidos.append((200 if alvo else 404, caminho))
        if alvo is None:
            return 404, "text/plain; charset=utf-8", b""
        return 200, TIPOS.get(alvo.suffix.lower(), "application/octet-stream"), alvo.read_bytes()

    def faltando_desde(self, inicio):
        with self._trava:
            return [cam for status, cam in self.pedidos[inicio:] if status != 200 and cam not in IGNORAR_FALTANDO]

    def total_pedidos(self):
        with self._trava:
            return len(self.pedidos)


def raiz_e_paginas(htmls, raiz_pedida):
    if raiz_pedida:
        raiz = Path(raiz_pedida).resolve()
        if not raiz.is_dir():
            c.falhar(f"--raiz nao e uma pasta: {raiz}")
        return raiz, None
    raiz = c.raiz_do_produto(htmls[0])
    if raiz:
        return raiz, None
    return Path(htmls[0]).resolve().parent, (
        "o HTML nao esta dentro de projetos/<produto>/: /assets/... nao vai achar os arquivos do produto. "
        "Use --raiz <pasta do produto> se a peca usa assets."
    )
