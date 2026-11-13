import argparse
import hashlib
import json
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True

import _comum as c

PASTA = Path("assets") / "gerado"
MANIFESTO = "origem.json"
TETO_MB = 25
TEMPO_LIMITE_S = 60
NOME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")


class SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def tipo_e_tamanho(dados):
    if dados[:8] == b"\x89PNG\r\n\x1a\n" and dados[12:16] == b"IHDR":
        largura, altura = struct.unpack(">II", dados[16:24])
        return "png", largura, altura
    if dados[:3] == b"\xff\xd8\xff":
        return ("jpg", *dimensoes_jpeg(dados))
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return ("webp", *dimensoes_webp(dados))
    return None, 0, 0


def dimensoes_jpeg(dados):
    i = 2
    while i + 9 < len(dados):
        if dados[i] != 0xFF:
            i += 1
            continue
        marca = dados[i + 1]
        if marca in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            altura, largura = struct.unpack(">HH", dados[i + 5:i + 9])
            return largura, altura
        if marca in (0xD8, 0x01) or 0xD0 <= marca <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack(">H", dados[i + 2:i + 4])[0]
    return 0, 0


def dimensoes_webp(dados):
    bloco = dados[12:16]
    if bloco == b"VP8X":
        largura = 1 + int.from_bytes(dados[24:27], "little")
        altura = 1 + int.from_bytes(dados[27:30], "little")
        return largura, altura
    if bloco == b"VP8 ":
        largura, altura = struct.unpack("<HH", dados[26:30])
        return largura & 0x3FFF, altura & 0x3FFF
    if bloco == b"VP8L":
        bits = int.from_bytes(dados[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return 0, 0


def conferir_url(url):
    partes = urlsplit(url)
    if partes.scheme != "https":
        c.falhar("a URL precisa ser https (ou passe o caminho de um arquivo local)")
    if partes.username or partes.password or partes.port not in (None, 443):
        c.falhar("a URL nao pode ter usuario, senha nem porta diferente da 443")
    return (partes.hostname or "").lower()


def ler_local(caminho, teto_bytes):
    arquivo = Path(caminho).expanduser()
    if not arquivo.is_file():
        c.falhar(f"{caminho} nao e uma URL https nem um arquivo existente")
    if arquivo.stat().st_size > teto_bytes:
        c.falhar(f"arquivo maior que {teto_bytes // (1024 * 1024)} MB: recusado")
    return arquivo.read_bytes()


def baixar(url, teto_bytes):
    abridor = urllib.request.build_opener(SemRedirecionamento)
    pedido = urllib.request.Request(url, headers={"User-Agent": "media-engine-importar"})
    try:
        with abridor.open(pedido, timeout=TEMPO_LIMITE_S) as resposta:
            dados = resposta.read(teto_bytes + 1)
    except urllib.error.HTTPError as erro:
        c.falhar(f"o servidor respondeu {erro.code} (redirecionamento nao e seguido; link expirado ou privado?)")
    except (urllib.error.URLError, TimeoutError) as erro:
        c.falhar(f"nao consegui baixar: {getattr(erro, 'reason', erro)}")
    if len(dados) > teto_bytes:
        c.falhar(f"arquivo maior que {teto_bytes // (1024 * 1024)} MB: recusado")
    return dados


def main():
    p = argparse.ArgumentParser(description="Traz uma imagem de fora (gerada por IA, banco de imagens, foto sua) para dentro da composicao, em assets/gerado/, conferindo tipo e tamanho e registrando a origem. Aceita URL https ou arquivo local. E o unico passo com rede: o render continua local.")
    p.add_argument("origem", help="URL https da imagem (ex.: o media_url devolvido pela geracao) ou caminho de um arquivo local")
    p.add_argument("composicao", help="pasta da composicao ou da peca")
    p.add_argument("--nome", required=True, help="nome do arquivo sem extensao (letras minusculas, numeros e hifen), ex.: fundo-abertura")
    p.add_argument("--prompt", help="prompt usado na geracao, guardado no origem.json")
    p.add_argument("--modelo", help="modelo usado na geracao, guardado no origem.json")
    p.add_argument("--teto-mb", type=int, default=TETO_MB, help=f"tamanho maximo aceito (padrao {TETO_MB} MB)")
    a = p.parse_args()

    comp = Path(a.composicao).resolve()
    if not comp.is_dir():
        c.falhar(f"{comp} nao e uma pasta")
    if not NOME_RE.fullmatch(a.nome):
        c.falhar("--nome: so letras minusculas, numeros e hifen (ex.: fundo-abertura)")
    teto = a.teto_mb * 1024 * 1024
    if re.match(r"^[a-z][a-z0-9+.-]*://", a.origem, re.IGNORECASE):
        host = conferir_url(a.origem)
        c.titulo(f"Importar imagem de {host}")
        dados = baixar(a.origem, teto)
        origem = a.origem
    else:
        c.titulo("Importar imagem de arquivo local")
        dados = ler_local(a.origem, teto)
        origem = "arquivo local: " + Path(a.origem).name
    tipo, largura, altura = tipo_e_tamanho(dados)
    if not tipo:
        c.falhar("o conteudo nao e PNG, JPEG nem WebP (conferido pelos primeiros bytes, nao pela extensao): recusado")

    pasta = comp / PASTA
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob(f"{a.nome}.*"):
        if antigo.suffix.lstrip(".") in ("png", "jpg", "webp"):
            antigo.unlink()
    destino = pasta / f"{a.nome}.{tipo}"
    destino.write_bytes(dados)

    manifesto = pasta / MANIFESTO
    registro = json.loads(manifesto.read_text(encoding="utf-8")) if manifesto.is_file() else {}
    item = {
        "arquivo": destino.name,
        "origem": origem,
        "sha256": hashlib.sha256(dados).hexdigest(),
        "bytes": len(dados),
        "largura": largura,
        "altura": altura,
        "importado_em": time.strftime("%Y-%m-%d"),
    }
    if a.prompt:
        item["prompt"] = a.prompt
    if a.modelo:
        item["modelo"] = a.modelo
    registro[a.nome] = item
    manifesto.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    rel = (PASTA / destino.name).as_posix()
    c.linha("OK", rel, f"{tipo.upper()} {largura}x{altura}, {len(dados) / 1024:.0f} KB, sha256 {item['sha256'][:12]}")
    print(f"   Na composicao de video: <img src=\"{rel}\">   Na peca de imagem: <img src=\"/{rel}\">")
    print(f"   Origem registrada em {(PASTA / MANIFESTO).as_posix()}")


if __name__ == "__main__":
    main()
