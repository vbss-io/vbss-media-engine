import re
import struct
import sys
from pathlib import Path

IMAGEM_DIR = Path(__file__).resolve().parent
ENGINE_DIR = IMAGEM_DIR.parent
REPO_DIR = ENGINE_DIR.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(errors="replace")

from comum import ambiente as _ambiente
from comum import navegador as navegador_fixado
from comum.chrome import AVISO_SISTEMA, descrever_navegador, e_navegador_fixo, file_version, find_chrome, flags_chrome, flags_faltando, versao_navegador
from comum.saida import falhar, linha, titulo
from comum.urls import host_of, url_local, urls_externas

SANDBOX_DIR = IMAGEM_DIR / ".sandbox"

FORMATOS = {
    "feed": (1080, 1350),
    "story": (1080, 1920),
    "quadrado": (1080, 1080),
    "og": (1200, 630),
}

DICAS_URL = {
    "api.fontshare.com": "fonte da Fontshare: confira se a licenca (ITF Free Font) permite guardar o arquivo no repo e troque pelo @font-face local; fonte remota nao renderiza.",
    "fonts.googleapis.com": "fonte do Google Fonts: troque pelo @font-face local de /_motor/fonts/ (ver content-engine/imagem/MOTOR.md, secao Fontes).",
    "fonts.gstatic.com": "arquivo de fonte do Google: troque pelo @font-face local de /_motor/fonts/.",
}

LIGADOS_RE = re.compile(r"""(?i)(?:\b(?:href|src)\s*=\s*["']([^"'#?]+\.(?:css|js|mjs|svg|json))|@import\s+(?:url\(\s*)?["']?([^"')\s;]+))""")


def sandbox_paths():
    return _ambiente.sandbox_paths(SANDBOX_DIR, extras=("perfis", "doctor", "folha"))


def sandbox_env():
    sandbox_paths()
    return _ambiente.sandbox_env(SANDBOX_DIR)


def assert_env_isolated(env):
    return _ambiente.assert_env_isolated(env, SANDBOX_DIR)


def tamanho(formato, texto):
    if texto:
        m = re.fullmatch(r"\s*(\d{2,5})\s*[xX]\s*(\d{2,5})\s*", texto)
        if not m:
            falhar(f"--tamanho invalido: {texto!r} (use LARGURAxALTURA, ex.: 1080x1350)")
        return int(m.group(1)), int(m.group(2))
    return FORMATOS[formato]


def raiz_do_produto(arquivo):
    for pasta in Path(arquivo).resolve().parents:
        pai = pasta.parent
        if pai.name == "projetos" or (pai.name == "archived" and pai.parent.name == "projetos"):
            return pasta
    return None


def png_dimensoes(caminho):
    with open(caminho, "rb") as f:
        cabecalho = f.read(24)
    if len(cabecalho) < 24 or cabecalho[:8] != b"\x89PNG\r\n\x1a\n" or cabecalho[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", cabecalho[16:24])


def arquivos_ligados(html, raiz):
    texto = Path(html).read_text(encoding="utf-8", errors="replace")
    achados = []
    for m in LIGADOS_RE.finditer(texto):
        ref = m.group(1) or m.group(2)
        if not ref or re.match(r"(?i)[a-z][a-z0-9+.-]*:", ref) or ref.startswith("//") or ref.startswith("/_motor/"):
            continue
        alvo = (Path(raiz) / ref.lstrip("/")) if ref.startswith("/") else (Path(html).parent / ref)
        if alvo.is_file():
            achados.append(alvo.resolve())
    return achados


def checar_urls(htmls, raiz):
    arquivos = []
    for html in htmls:
        arquivos.append(Path(html).resolve())
        arquivos += arquivos_ligados(html, raiz)
    return urls_externas(dict.fromkeys(arquivos))


def dica_url(url):
    return DICAS_URL.get(host_of(url), "")


__all__ = [
    "AVISO_SISTEMA", "descrever_navegador", "e_navegador_fixo", "navegador_fixado", "versao_navegador",
    "file_version", "find_chrome", "flags_chrome", "flags_faltando",
    "falhar", "linha", "titulo", "host_of", "url_local",
]
