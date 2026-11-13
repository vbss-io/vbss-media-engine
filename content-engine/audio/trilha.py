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
PASTA_MUSICA = Path("assets") / "musica"
BASE_MUSICA = PASTA_MUSICA / "base.wav"
TRILHA_MUSICA = 9
JUNTAR_FALAS = 0.6
FOLGA_FALA = 0.05
RAMPA_MINIMA = 0.01
PADRAO_MUSICA = {"volume": 0.5, "sob_voz": 0.18, "inicio": 0.0, "entrada": 0.6, "saida": 1.2, "ataque": 0.25, "soltura": 0.5}
FLAGS_SAIDA = ["-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1"]


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


def manifesto_musica():
    if not c.MUSICA_MANIFESTO.is_file():
        c.falhar("biblioteca de musica ausente: rode python content-engine/audio/musica_setup.py")
    return {i["id"]: i for i in c.ler_json(c.MUSICA_MANIFESTO)["itens"]}


def resolver_musica(cfg, comp, total):
    if not isinstance(cfg, dict):
        c.falhar("'musica' precisa ser um objeto, ex.: {\"faixa\": \"lofi-tranquila\"}")
    estranhas = sorted(set(cfg) - set(PADRAO_MUSICA) - {"faixa", "arquivo"})
    if estranhas:
        c.falhar(f"musica: chave desconhecida: {', '.join(estranhas)} (aceitas: faixa ou arquivo, {', '.join(PADRAO_MUSICA)})")
    if ("faixa" in cfg) == ("arquivo" in cfg):
        c.falhar("musica precisa de 'faixa' (id da biblioteca) ou de 'arquivo' (dentro da composicao), um dos dois")
    m = {k: float(cfg.get(k, v)) for k, v in PADRAO_MUSICA.items()}
    if "faixa" in cfg:
        biblioteca = manifesto_musica()
        if cfg["faixa"] not in biblioteca:
            c.falhar(f"faixa de musica '{cfg['faixa']}' nao existe na biblioteca (veja content-engine/audio/music/CATALOGO.md)")
        m["origem"] = c.MUSICA_DIR / biblioteca[cfg["faixa"]]["arquivo"]
        m["nome"] = cfg["faixa"]
        if not m["origem"].is_file():
            c.falhar(f"{c.rel(m['origem'])} sumiu da biblioteca: rode python content-engine/audio/musica_setup.py")
    else:
        alvo = (comp / cfg["arquivo"]).resolve()
        if comp.resolve() not in alvo.parents or not alvo.is_file() or alvo == (comp / BASE_MUSICA).resolve():
            c.falhar(f"musica: '{cfg['arquivo']}' precisa ser um arquivo dentro da composicao ({comp}) e diferente de {BASE_MUSICA.as_posix()}")
        m["origem"] = alvo
        m["nome"] = alvo.relative_to(comp.resolve()).as_posix()
    if not 0 < m["volume"] <= 1 or not 0 <= m["sob_voz"] <= m["volume"]:
        c.falhar("musica: 'volume' vai de 0 a 1 e 'sob_voz' de 0 ate o 'volume'")
    if min(m["entrada"], m["saida"], m["ataque"], m["soltura"]) < 0:
        c.falhar("musica: 'entrada', 'saida', 'ataque' e 'soltura' nao podem ser negativos")
    m["fim"] = round(total - MARGEM_FIM, 3)
    if m["inicio"] < 0 or m["inicio"] + m["entrada"] + m["saida"] > m["fim"]:
        c.falhar(f"musica: 'inicio' + 'entrada' + 'saida' nao cabem no video ({total}s)")
    for chave in ("entrada", "saida", "ataque", "soltura"):
        m[chave] = max(m[chave], RAMPA_MINIMA)
    return m


def trechos_de_voz(falas, juntar=JUNTAR_FALAS):
    trechos = []
    for inicio, fim in sorted(falas):
        if trechos and inicio - trechos[-1][1] < juntar:
            trechos[-1][1] = max(trechos[-1][1], fim)
        else:
            trechos.append([inicio, fim])
    return [(round(a, 3), round(b, 3)) for a, b in trechos]


def pontos_de_ducking(trechos, volume, sob_voz, ataque, soltura):
    if not trechos:
        return [(0.0, volume)]
    pontos = []
    for i, (inicio, fim) in enumerate(trechos):
        desce = inicio - FOLGA_FALA - ataque
        if i == 0:
            pontos.append((desce, volume))
        else:
            volta = trechos[i - 1][1]
            if volta + soltura <= desce:
                pontos += [(volta + soltura, volume), (desce, volume)]
            else:
                cruza = (1 + volta / soltura + desce / ataque) / (1 / soltura + 1 / ataque)
                pontos.append((cruza, volume - (volume - sob_voz) * (cruza - desce) / ataque))
        pontos += [(inicio - FOLGA_FALA, sob_voz), (fim, sob_voz)]
    pontos.append((trechos[-1][1] + soltura, volume))
    return pontos


def pontos_de_fade(inicio, entrada, saida, fim):
    return [(inicio, 0.0), (inicio + entrada, 1.0), (fim - saida, 1.0), (fim, 0.0)]


def expressao(pontos):
    termos = [f"{pontos[0][1]:.6f}"]
    inclinacao = 0.0
    ultimo = pontos[0][0]
    for (t0, g0), (t1, g1) in zip(pontos, pontos[1:]):
        if t1 <= t0:
            continue
        nova = (g1 - g0) / (t1 - t0)
        if abs(nova - inclinacao) > 1e-9:
            termos.append(f"{nova - inclinacao:+.9f}*max(t-({t0:.6f}),0)")
        inclinacao = nova
        ultimo = t1
    if abs(inclinacao) > 1e-9:
        termos.append(f"{-inclinacao:+.9f}*max(t-({ultimo:.6f}),0)")
    return "".join(termos)


def gerar_base(comp, m, falas, total):
    trechos = trechos_de_voz(falas)
    fade = expressao(pontos_de_fade(m["inicio"], m["entrada"], m["saida"], m["fim"]))
    ducking = expressao(pontos_de_ducking(trechos, m["volume"], m["sob_voz"], m["ataque"], m["soltura"]))
    ganho = f"clip({fade},0,1)*clip({ducking},{m['sob_voz']:.6f},{m['volume']:.6f})"
    amostras = int(c.duracao(m["origem"]) * c.TAXA_SFX) + c.TAXA_SFX
    audio = next((s for s in c.streams(m["origem"]).get("streams", []) if s.get("codec_type") == "audio"), {})
    mono = int(audio.get("channels") or 2) == 1
    filtros = [
        f"aresample={c.TAXA_SFX}",
        "aformat=sample_fmts=flt,pan=stereo|c0=c0|c1=c0" if mono else "aformat=sample_fmts=flt:channel_layouts=stereo",
        f"aloop=loop=-1:size={amostras}",
        "asetpts=N/SR/TB",
        f"atrim=duration={m['fim'] - m['inicio']:.3f}",
    ]
    if m["inicio"] > 0:
        filtros.append(f"adelay={round(m['inicio'] * 1000)}:all=1")
    filtros += [f"aeval=exprs='val(ch)*{ganho}':c=same", f"apad=whole_dur={total}", f"atrim=end={total}"]
    destino = comp / BASE_MUSICA
    destino.parent.mkdir(parents=True, exist_ok=True)
    c.exigir_ffmpeg()
    r = c.ffmpeg(["-y", "-i", str(m["origem"]), "-af", ",".join(filtros), "-c:a", "pcm_s16le", "-ar", str(c.TAXA_SFX), "-ac", "2", *FLAGS_SAIDA, str(destino)])
    if r.returncode != 0 or not destino.is_file():
        c.falhar(f"ffmpeg falhou gerando {BASE_MUSICA.as_posix()}: {r.stderr[-400:]}")
    return trechos


def remover_base(comp):
    base = comp / BASE_MUSICA
    if base.is_file():
        base.unlink()
    if base.parent.is_dir() and not any(base.parent.iterdir()):
        base.parent.rmdir()


def aplicar(index, resolvidas, musica=None):
    html = index.read_text(encoding="utf-8")
    html = AUDIO_TRILHA_RE.sub("", html)
    m = RAIZ_RE.search(html)
    if not m:
        c.falhar(f"{index} nao tem o elemento raiz com data-composition-id")
    linhas = []
    if musica:
        linhas.append(
            f'  <audio id="trilha-musica" src="{BASE_MUSICA.as_posix()}" data-start="0" data-duration="{musica["fim"]}" '
            f'data-track-index="{TRILHA_MUSICA}" data-volume="1.0" data-trilha="1"></audio>\n'
        )
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
    p.add_argument("trilha", help="trilha.json: {\"volume_efeitos\": 0.8, \"musica\": {\"faixa\": \"lofi-tranquila\"}, \"deixas\": [{\"t\": 0.75, \"efeito\": \"pop/pop-gota\"}, {\"t\": 0.2, \"arquivo\": \"assets/voz/voz-01.wav\"}]}")
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
    musica = resolver_musica(cfg["musica"], comp, total) if cfg.get("musica") else None
    trechos = []
    if musica:
        trechos = gerar_base(comp, musica, [(r["t"], r["t"] + r["dur"]) for r in resolvidas if r["tipo"] == "voz"], total)
    else:
        remover_base(comp)
    aplicar(index, resolvidas, musica)
    limpar_sfx(comp, resolvidas)
    c.titulo(f"Trilha aplicada em {c.rel(index)} ({total}s)")
    for r in resolvidas:
        print(f"   {r['t']:6.2f}s  {r['dur']:5.2f}s  vol {r['volume']:<5}  trilha {r['trilha']:<3} {r['src']}")
    c.linha("OK", f"{len(resolvidas) + bool(musica)} <audio> na raiz", "voz na trilha 10, efeitos de 11 em diante sem sobrepor na mesma trilha")
    if musica:
        baixos = ", ".join(f"{a:.2f}-{b:.2f}s" for a, b in trechos) or "nenhum (sem voz)"
        c.linha("OK", f"musica '{musica['nome']}' em {BASE_MUSICA.as_posix()} (trilha {TRILHA_MUSICA})", f"volume {musica['volume']:g}, {musica['sob_voz']:g} sob a voz em: {baixos}")


if __name__ == "__main__":
    main()
