import argparse
import shutil
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c

CACHE_SFX = c.CACHE_DIR / "sfx"
TMP = CACHE_SFX / "tmp"
FLAGS_SAIDA = ["-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1"]


def baixar_pacotes(fontes, usados, offline):
    c.titulo("Pacotes de origem (CC0, SHA-256 fixado)")
    for chave in sorted(usados):
        info = fontes[chave]
        destino = CACHE_SFX / f"{chave}.zip"
        if offline:
            if not destino.is_file() or c.sha256(destino) != info["sha256"]:
                c.falhar(f"{destino.name} ausente ou diferente no cache e --offline foi pedido")
            estado = "cache"
        else:
            estado = c.baixar_conferido(info["url"], destino, info["sha256"])
        c.linha("OK", f"{chave} ({estado})", info["sha256"][:16])


def extrair(item):
    zip_path = CACHE_SFX / f"{item['pacote']}.zip"
    with zipfile.ZipFile(zip_path) as z:
        if item["membro"] not in z.namelist():
            c.falhar(f"{item['membro']} nao existe em {zip_path.name}")
        dados = z.read(item["membro"])
    sufixo = Path(item["membro"]).suffix.lower()
    origem = TMP / f"{item['nome']}-origem{sufixo}"
    origem.write_bytes(dados)
    return origem


def canais(arquivo):
    info = c.streams(arquivo)
    st = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})
    return int(st.get("channels") or 1)


def preparar(item, origem, fmt):
    filtros = []
    corte = item.get("corte")
    if corte:
        filtros.append(f"atrim=start={corte['inicio']}:end={corte['fim']},asetpts=PTS-STARTPTS")
    ch = canais(origem)
    if ch == 1:
        filtros.append("aformat=sample_fmts=flt")
    else:
        mistura = "+".join(f"{1 / ch:.6f}*c{i}" for i in range(ch))
        filtros.append(f"aformat=sample_fmts=flt,pan=mono|c0={mistura}")
    filtros.append(f"aresample={fmt['taxa']}")
    limiar = fmt["limiar_silencio_db"]
    filtros.append(f"silenceremove=start_periods=1:start_threshold={limiar}dB")
    filtros.append(f"areverse,silenceremove=start_periods=1:start_threshold={limiar}dB,areverse")
    if corte:
        dur = corte["fim"] - corte["inicio"]
        filtros.append(f"afade=t=out:st={max(0.0, dur - 0.08):.3f}:d=0.08")
    inter = TMP / f"{item['nome']}-float.wav"
    r = c.ffmpeg(["-y", "-i", str(origem), "-af", ",".join(filtros), "-c:a", "pcm_f32le", *FLAGS_SAIDA, str(inter)])
    if r.returncode != 0 or not inter.is_file():
        c.falhar(f"ffmpeg falhou preparando {item['nome']}: {r.stderr[-400:]}")
    return inter


def normalizar(item, inter, destino, fmt):
    m = c.medir(inter)
    if m["lufs_momentaneo_max"] is None or m["pico_dbtp"] is None:
        c.falhar(f"nao consegui medir {item['nome']}: {m}")
    ganho = min(fmt["alvo_lufs_momentaneo_max"] - m["lufs_momentaneo_max"], fmt["teto_pico_dbtp"] - m["pico_dbtp"])
    ganho = round(ganho, 1)
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = c.ffmpeg(["-y", "-i", str(inter), "-af", f"volume={ganho}dB", "-c:a", fmt["codec"], "-ar", str(fmt["taxa"]), "-ac", str(fmt["canais"]), *FLAGS_SAIDA, str(destino)])
    if r.returncode != 0 or not destino.is_file():
        c.falhar(f"ffmpeg falhou gravando {destino.name}: {r.stderr[-400:]}")
    return ganho


def montar_catalogo(manifesto, fontes):
    linhas = [
        "# Catálogo de efeitos sonoros",
        "",
        "Efeitos curtos para Reels de todos os produtos, gerados por `python content-engine/audio/sfx_setup.py` a partir de pacotes CC0 (licenças em `LICENCAS.md`). Este arquivo é gerado: para mudar a seleção, edite `content-engine/audio/sfx_selecao.json` e rode o setup de novo.",
        "",
        f"- Formato: WAV PCM 16 bits, {manifesto['formato']['taxa']} Hz, mono. Silêncio do começo cortado: o som começa no instante 0 do arquivo, então o `data-start` do `<audio>` é o momento exato do efeito.",
        f"- Nível: pico de loudness momentânea em {manifesto['formato']['alvo_lufs_momentaneo_max']:.0f} LUFS e pico real até {manifesto['formato']['teto_pico_dbtp']:.0f} dBTP (o que vier primeiro). Efeito com pico alto e corpo curto fica um pouco abaixo do alvo, de propósito, para não saturar.",
        "- Para ouvir todos em sequência com o nome na tela: `sfx/catalogo.mp4` (refazer com `python content-engine/audio/catalogo_audio.py`).",
        "- Produtos: `todos` = serve para qualquer produto; os demais são sugestão, não regra.",
        "",
    ]
    por_cat = {}
    for item in manifesto["itens"]:
        por_cat.setdefault(item["categoria"], []).append(item)
    for cat, itens in por_cat.items():
        linhas += [f"## {cat}", "", "| Arquivo | Duração | Uso sugerido | Produtos | Origem |", "| --- | --- | --- | --- | --- |"]
        for it in itens:
            pac = fontes[it["origem"]["pacote"]]
            origem = f"[{pac['nome']}]({pac['pagina']}), `{Path(it['origem']['membro']).name}`, {pac['licenca']}"
            dur = f"{it['duracao']:.2f}".replace(".", ",")
            linhas.append(f"| `{it['arquivo']}` | {dur} s | {it['uso']} | {', '.join(it['produtos'])} | {origem} |")
        linhas.append("")
    (c.SFX_DIR / "CATALOGO.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")


def main():
    p = argparse.ArgumentParser(description="Baixa os pacotes CC0 fixados e refaz a biblioteca de efeitos em content-engine/audio/sfx/.")
    p.add_argument("--offline", action="store_true", help="usa so o cache (.cache/sfx), sem rede")
    a = p.parse_args()

    c.exigir_ffmpeg()
    fontes = c.ler_json(c.SFX_FONTES)["pacotes"]
    selecao = c.ler_json(c.SFX_SELECAO)
    fmt = selecao["formato"]
    itens = selecao["itens"]
    nomes = [i["nome"] for i in itens]
    if len(set(nomes)) != len(nomes):
        c.falhar("sfx_selecao.json tem nomes repetidos")
    faltam = sorted({i["pacote"] for i in itens} - set(fontes))
    if faltam:
        c.falhar(f"pacotes sem fonte em sfx_fontes.json: {', '.join(faltam)}")

    anterior = {}
    if c.SFX_MANIFESTO.is_file():
        anterior = {i["arquivo"]: i["sha256"] for i in c.ler_json(c.SFX_MANIFESTO).get("itens", [])}

    baixar_pacotes(fontes, {i["pacote"] for i in itens}, a.offline)
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)

    c.titulo(f"Biblioteca ({len(itens)} efeitos)")
    manifesto_itens = []
    mudaram = 0
    for item in itens:
        rel = f"{item['categoria']}/{item['nome']}.wav"
        destino = c.SFX_DIR / rel
        origem = extrair(item)
        inter = preparar(item, origem, fmt)
        ganho = normalizar(item, inter, destino, fmt)
        m = c.medir(destino)
        sha = c.sha256(destino)
        estado = "novo" if rel not in anterior else ("igual" if anterior[rel] == sha else "MUDOU")
        mudaram += estado == "MUDOU"
        c.linha("OK", rel, f"{m['duracao']:.2f}s  M max {m['lufs_momentaneo_max']}  pico {m['pico_dbtp']} dBTP  ganho {ganho:+.1f} dB  {estado}")
        registro = {
            "arquivo": rel,
            "categoria": item["categoria"],
            "nome": item["nome"],
            "duracao": m["duracao"],
            "lufs_momentaneo_max": m["lufs_momentaneo_max"],
            "pico_dbtp": m["pico_dbtp"],
            "ganho_db": ganho,
            "sha256": sha,
            "bytes": destino.stat().st_size,
            "uso": item["uso"],
            "produtos": item["produtos"],
            "origem": {"pacote": item["pacote"], "membro": item["membro"]},
        }
        if item.get("corte"):
            registro["origem"]["corte"] = item["corte"]
        manifesto_itens.append(registro)

    esperados = {i["arquivo"] for i in manifesto_itens}
    for wav in sorted(c.SFX_DIR.rglob("*.wav")):
        rel = wav.relative_to(c.SFX_DIR).as_posix()
        if rel not in esperados:
            wav.unlink()
            c.linha("OK", f"removido (fora da selecao): {rel}")
    for pasta in sorted((p for p in c.SFX_DIR.iterdir() if p.is_dir()), reverse=True):
        if not any(pasta.iterdir()):
            pasta.rmdir()

    manifesto = {"formato": fmt, "itens": manifesto_itens}
    c.escrever_json(c.SFX_MANIFESTO, manifesto)
    montar_catalogo(manifesto, fontes)
    shutil.rmtree(TMP, ignore_errors=True)
    total = sum(i["bytes"] for i in manifesto_itens)
    c.titulo("Resultado")
    c.linha("OK", f"{len(manifesto_itens)} efeitos em {c.rel(c.SFX_DIR)}", f"{total / (1 << 20):.2f} MB; manifesto sfx.json e CATALOGO.md atualizados")
    if anterior and mudaram:
        c.linha("ATENCAO", f"{mudaram} arquivo(s) mudaram em relacao ao manifesto anterior", "o FFmpeg fixado deveria repetir os mesmos bytes; confira a versao em content-engine/video/bin")


if __name__ == "__main__":
    main()
