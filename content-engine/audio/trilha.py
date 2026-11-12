import argparse
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c

RAIZ_RE = re.compile(r"<div\b[^>]*\bdata-composition-id=\"[^\"]+\"[^>]*>")
DURACAO_RE = re.compile(r"\bdata-duration=\"([\d.]+)\"")
AUDIO_TRILHA_RE = re.compile(r"[ \t]*<audio\b[^>]*\bdata-trilha=\"1\"[^>]*></audio>\n?")
PASTA_SFX = Path("assets") / "sfx"
TRILHA_VOZ = 10
TRILHA_EFEITOS = 11
MARGEM_FIM = 0.02


def manifesto_sfx():
    if not c.SFX_MANIFESTO.is_file():
        c.falhar("biblioteca de efeitos ausente: rode python content-engine/audio/sfx_setup.py")
    return {i["arquivo"][:-4]: i for i in c.ler_json(c.SFX_MANIFESTO)["itens"]}


def resolver(deixa, comp, sfx, padrao_volume):
    if "efeito" in deixa:
        chave = deixa["efeito"].removesuffix(".wav")
        if chave not in sfx:
            c.falhar(f"efeito '{deixa['efeito']}' nao existe na biblioteca (veja content-engine/audio/sfx/CATALOGO.md)")
        origem = c.SFX_DIR / sfx[chave]["arquivo"]
        rel = (PASTA_SFX / Path(sfx[chave]["arquivo"]).name).as_posix()
        destino = comp / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not destino.is_file() or c.sha256(destino) != sfx[chave]["sha256"]:
            shutil.copyfile(origem, destino)
        return rel, sfx[chave]["duracao"], "efeito", deixa.get("volume", padrao_volume)
    if "arquivo" in deixa:
        alvo = (comp / deixa["arquivo"]).resolve()
        if comp.resolve() not in alvo.parents or not alvo.is_file():
            c.falhar(f"'{deixa['arquivo']}' precisa ser um arquivo dentro da composicao ({comp})")
        return alvo.relative_to(comp.resolve()).as_posix(), c.duracao(alvo), "voz", deixa.get("volume", 1.0)
    c.falhar(f"deixa sem 'efeito' nem 'arquivo': {deixa}")


def montar(deixas, comp, sfx, total, padrao_volume):
    resolvidas = []
    for d in sorted(deixas, key=lambda x: float(x["t"])):
        rel, dur, tipo, vol = resolver(d, comp, sfx, padrao_volume)
        t = round(float(d["t"]), 3)
        if t < 0 or t >= total:
            c.falhar(f"deixa em {t}s fora do video (0 a {total}s): {rel}")
        dur = min(float(d.get("duracao", dur)), dur, total - t - MARGEM_FIM)
        resolvidas.append({"t": t, "src": rel, "dur": round(dur, 3), "tipo": tipo, "volume": round(float(vol), 3)})
    ocupado = {}
    for r in resolvidas:
        if r["tipo"] == "voz":
            r["trilha"] = TRILHA_VOZ
            continue
        trilha = TRILHA_EFEITOS
        while ocupado.get(trilha, -1.0) > r["t"]:
            trilha += 1
        ocupado[trilha] = r["t"] + r["dur"]
        r["trilha"] = trilha
    return resolvidas


def aplicar(index, resolvidas):
    html = index.read_text(encoding="utf-8")
    html = AUDIO_TRILHA_RE.sub("", html)
    m = RAIZ_RE.search(html)
    if not m:
        c.falhar(f"{index} nao tem o elemento raiz com data-composition-id")
    linhas = []
    for i, r in enumerate(resolvidas, 1):
        linhas.append(
            f'  <audio id="trilha-{i:02d}" src="{r["src"]}" data-start="{r["t"]}" data-duration="{r["dur"]}" '
            f'data-track-index="{r["trilha"]}" data-volume="{r["volume"]}" data-trilha="1"></audio>\n'
        )
    html = html[:m.end()] + "\n" + "".join(linhas) + html[m.end():].lstrip("\n")
    index.write_text(html, encoding="utf-8", newline="\n")


def limpar_sfx(comp, resolvidas):
    usados = {r["src"] for r in resolvidas}
    pasta = comp / PASTA_SFX
    if not pasta.is_dir():
        return
    for wav in pasta.glob("*.wav"):
        if (PASTA_SFX / wav.name).as_posix() not in usados:
            wav.unlink()


def main():
    p = argparse.ArgumentParser(description="Coloca efeitos e voz numa composicao de video como <audio> locais na raiz (data-trilha=1), a partir de um trilha.json.")
    p.add_argument("composicao", help="pasta da composicao (com index.html)")
    p.add_argument("trilha", help="trilha.json: {\"volume_efeitos\": 0.8, \"deixas\": [{\"t\": 0.75, \"efeito\": \"pop/pop-gota\"}, {\"t\": 0.2, \"arquivo\": \"assets/voz/voz-01.wav\"}]}")
    a = p.parse_args()
    comp = Path(a.composicao).resolve()
    index = comp / "index.html"
    if not index.is_file():
        c.falhar(f"{comp} nao tem index.html")
    cfg = c.ler_json(a.trilha)
    html = index.read_text(encoding="utf-8")
    raiz = RAIZ_RE.search(html)
    dur_m = DURACAO_RE.search(raiz.group(0)) if raiz else None
    if not dur_m:
        c.falhar("nao achei data-duration no elemento raiz da composicao")
    total = float(dur_m.group(1))
    resolvidas = montar(cfg.get("deixas", []), comp, manifesto_sfx(), total, cfg.get("volume_efeitos", 0.8))
    aplicar(index, resolvidas)
    limpar_sfx(comp, resolvidas)
    c.titulo(f"Trilha aplicada em {c.rel(index)} ({total}s)")
    for r in resolvidas:
        print(f"   {r['t']:6.2f}s  {r['dur']:5.2f}s  vol {r['volume']:<5}  trilha {r['trilha']:<3} {r['src']}")
    c.linha("OK", f"{len(resolvidas)} <audio> na raiz", "voz na trilha 10, efeitos de 11 em diante sem sobrepor na mesma trilha")


if __name__ == "__main__":
    main()
