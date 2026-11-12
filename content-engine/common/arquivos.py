import os
from pathlib import Path

EXT_PERMITIDAS = {
    ".html", ".htm", ".css", ".js", ".mjs", ".json", ".svg", ".txt", ".vtt",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif",
    ".woff", ".woff2", ".ttf", ".otf",
    ".wav", ".mp3", ".ogg", ".oga", ".m4a", ".aac", ".flac", ".opus",
    ".mp4", ".m4v", ".webm", ".mov",
}
EXT_LISTA = {".m3u", ".m3u8", ".ffconcat", ".concat", ".pls", ".xspf", ".cue"}
ASSINATURAS_DE_LISTA = (b"#extm3u", b"ffconcat")
_MOV = ("ftyp", "moov", "mdat", "free", "wide", "skip", "pnot")
ASSINATURAS_DE_MIDIA = {
    ".png": [(0, b"\x89PNG\r\n\x1a\n")],
    ".jpg": [(0, b"\xff\xd8\xff")],
    ".jpeg": [(0, b"\xff\xd8\xff")],
    ".gif": [(0, b"GIF87a"), (0, b"GIF89a")],
    ".webp": [(0, b"RIFF", 8, b"WEBP")],
    ".avif": [(4, b"ftyp")],
    ".woff": [(0, b"wOFF")],
    ".woff2": [(0, b"wOF2")],
    ".ttf": [(0, b"\x00\x01\x00\x00"), (0, b"true")],
    ".otf": [(0, b"OTTO")],
    ".wav": [(0, b"RIFF", 8, b"WAVE"), (0, b"RF64", 8, b"WAVE"), (0, b"BW64", 8, b"WAVE")],
    ".mp3": [(0, b"ID3"), (0, b"\xff\xfb"), (0, b"\xff\xfa"), (0, b"\xff\xf3"), (0, b"\xff\xf2"), (0, b"\xff\xe3"), (0, b"\xff\xe2")],
    ".ogg": [(0, b"OggS")],
    ".oga": [(0, b"OggS")],
    ".opus": [(0, b"OggS")],
    ".flac": [(0, b"fLaC")],
    ".aac": [(0, b"\xff\xf1"), (0, b"\xff\xf9"), (0, b"ADIF"), (0, b"ID3")],
    ".m4a": [(4, b"ftyp")],
    ".mp4": [(4, b"ftyp")],
    ".m4v": [(4, b"ftyp")],
    ".mov": [(4, nome.encode()) for nome in _MOV],
    ".webm": [(0, b"\x1a\x45\xdf\xa3")],
}
PASTAS_FORA_DA_COPIA = {"renders", "node_modules", ".git"}
TIPOS_TEXTO = ", ".join(sorted(e.lstrip(".") for e in EXT_PERMITIDAS))


def _e_lista_por_conteudo(arq):
    try:
        with open(arq, "rb") as f:
            inicio = f.read(64)
    except OSError:
        return False
    inicio = inicio.lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    return inicio.startswith(ASSINATURAS_DE_LISTA)


def _midia_sem_assinatura(arq, ext):
    # identificacao positiva: arquivo de midia precisa comecar com a assinatura binaria real do formato;
    # um manifesto (DASH/MPD, SMIL, HLS, JSON) salvo com extensao de midia nunca bate e e recusado
    regras = ASSINATURAS_DE_MIDIA.get(ext)
    if not regras:
        return False
    try:
        with open(arq, "rb") as f:
            cab = f.read(16)
    except OSError:
        return True
    for regra in regras:
        pares = list(zip(regra[0::2], regra[1::2]))
        if all(cab[pos:pos + len(sig)] == sig for pos, sig in pares):
            return False
    return True


def _e_ligacao(caminho):
    if os.path.islink(caminho):
        return True
    junction = getattr(os.path, "isjunction", None)
    return bool(junction and junction(caminho))


def inventariar(comp_dir):
    comp_dir = Path(comp_dir)
    copiar = []
    problemas = []
    for raiz, pastas, arquivos in os.walk(comp_dir):
        raiz = Path(raiz)
        restantes = []
        for p in sorted(pastas):
            if p in PASTAS_FORA_DA_COPIA:
                continue
            if _e_ligacao(raiz / p):
                problemas.append(f"{(raiz / p).relative_to(comp_dir).as_posix()}: link simbolico ou juncao de pasta nao entra na composicao")
                continue
            restantes.append(p)
        pastas[:] = restantes
        for nome in sorted(arquivos):
            if nome.lower().startswith(".env"):
                continue
            arq = raiz / nome
            rel = arq.relative_to(comp_dir).as_posix()
            ext = arq.suffix.lower()
            if _e_ligacao(arq):
                problemas.append(f"{rel}: link simbolico nao entra na composicao")
            elif ext in EXT_LISTA or _e_lista_por_conteudo(arq):
                problemas.append(f"{rel}: lista de reproducao ou de arquivos (m3u, m3u8, ffconcat, concat, pls, xspf, cue) nao e aceita, pois pode apontar para arquivo fora da composicao")
            elif _midia_sem_assinatura(arq, ext):
                problemas.append(f"{rel}: tem extensao de midia mas nao comeca com a assinatura real desse formato (pode ser manifesto ou lista, como DASH/MPD, que aponta para arquivo fora da composicao)")
            elif ext not in EXT_PERMITIDAS:
                problemas.append(f"{rel}: tipo '{ext or 'sem extensao'}' nao e permitido na composicao (permitidos: {TIPOS_TEXTO})")
            else:
                copiar.append(rel)
    return copiar, problemas
