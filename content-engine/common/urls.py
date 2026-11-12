import re
from pathlib import Path

TEXT_EXT = {".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json", ".svg", ".xml", ".txt", ".md", ".vtt", ".srt", ".webmanifest"}
URL_RE = re.compile(r"(?i)\b(?:https?|wss?|ftp)://[^\s\"'<>)\]}]+")
PROTOCOL_RELATIVE_RE = re.compile(r"""(?i)(?:\b(?:src|href|poster|data|action)\s*=\s*["']?|url\(\s*["']?|@import\s+["'])//[a-z0-9.-]""")
XML_NAMESPACES = {"http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink", "http://www.w3.org/1999/xhtml", "http://www.w3.org/XML/1998/namespace"}
XMLNS_BEFORE_RE = re.compile(r"""xmlns(?::[\w-]+)?\s*=\s*["']$""")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


def host_of(url):
    m = re.match(r"(?i)[a-z][a-z0-9+.-]*://(\[[^\]]+\]|[^/:?#]+)", url)
    return m.group(1).lower() if m else ""


def host_local(host):
    host = (host or "").lower()
    return host in LOCAL_HOSTS or host.startswith("127.") or host.endswith(".localhost")


def url_local(url):
    if re.match(r"(?i)(data|blob|about|file):", url):
        return True
    return host_local(host_of(url))


def urls_externas_no_texto(texto):
    achados = []
    namespaces = {n.rstrip("/") for n in XML_NAMESPACES}
    for m in URL_RE.finditer(texto):
        url = m.group(0)
        if host_local(host_of(url)):
            continue
        if url.rstrip("/") in namespaces and XMLNS_BEFORE_RE.search(texto[max(0, m.start() - 40):m.start()]):
            continue
        achados.append((texto.count("\n", 0, m.start()) + 1, url))
    for m in PROTOCOL_RELATIVE_RE.finditer(texto):
        achados.append((texto.count("\n", 0, m.start()) + 1, m.group(0) + "..."))
    return achados


def urls_externas(arquivos):
    achados = []
    for arq in arquivos:
        arq = Path(arq)
        if not arq.is_file() or arq.suffix.lower() not in TEXT_EXT:
            continue
        texto = arq.read_text(encoding="utf-8", errors="replace")
        achados += [(arq, ln, url) for ln, url in urls_externas_no_texto(texto)]
    return achados


def urls_externas_na_pasta(pasta):
    return urls_externas(sorted(p for p in Path(pasta).rglob("*") if p.is_file()))
