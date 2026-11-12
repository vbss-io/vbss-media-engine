import hashlib
import urllib.request


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(url, destino, agente="vbss-media-engine-setup"):
    req = urllib.request.Request(url, headers={"User-Agent": agente})
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        lido = 0
        ultimo = -1
        while True:
            bloco = resp.read(1 << 20)
            if not bloco:
                break
            out.write(bloco)
            lido += len(bloco)
            if total:
                pct = lido * 100 // total
                if pct // 10 != ultimo:
                    ultimo = pct // 10
                    print(f"  {pct}% ({lido // (1 << 20)} MB)", flush=True)
    tmp.replace(destino)
