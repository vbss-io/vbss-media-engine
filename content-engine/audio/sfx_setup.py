import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c

CACHE_SFX = c.CACHE_DIR / "sfx"
TMP = CACHE_SFX / "tmp"
FLAGS_SAIDA = ["-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1"]
SINTESE = c.AUDIO_DIR / "sfx_sintese.py"
CONJUNTOS = {"cine": "Conjunto cine (pós-produção)"}


def arquivo_da_fonte(chave, info):
    sufixo = Path(info["url"]).suffix.lower() if info.get("tipo") == "arquivo" else ".zip"
    return CACHE_SFX / f"{chave}{sufixo}"


def pacotes_do_item(item):
    if "pacote" in item:
        return [item["pacote"]]
    return [camada["pacote"] for camada in item.get("camadas", [])]


def baixar_pacotes(fontes, usados, offline):
    c.titulo("Pacotes de origem (CC0, SHA-256 fixado)")
    for chave in sorted(usados):
        info = fontes[chave]
        destino = arquivo_da_fonte(chave, info)
        if offline:
            if not destino.is_file() or c.sha256(destino) != info["sha256"]:
                c.falhar(f"{destino.name} ausente ou diferente no cache e --offline foi pedido")
            estado = "cache"
        else:
            estado = c.baixar_conferido(info["url"], destino, info["sha256"])
        c.linha("OK", f"{chave} ({estado})", info["sha256"][:16])


def ler_membro(fontes, pacote, membro):
    caminho = arquivo_da_fonte(pacote, fontes[pacote])
    if fontes[pacote].get("tipo") == "arquivo":
        return caminho.read_bytes()
    with zipfile.ZipFile(caminho) as z:
        if membro not in z.namelist():
            c.falhar(f"{membro} nao existe em {caminho.name}")
        return z.read(membro)


def extrair(item, fontes):
    sufixo = Path(item["membro"]).suffix.lower()
    origem = TMP / f"{item['nome']}-origem{sufixo}"
    origem.write_bytes(ler_membro(fontes, item["pacote"], item["membro"]))
    return origem


def python_com_numpy():
    candidatos = [Path(sys.executable), c.VENV_DIR / "Scripts" / "python.exe", c.VENV_DIR / "bin" / "python"]
    for py in candidatos:
        if py.is_file() and subprocess.run([str(py), "-I", "-c", "import numpy"], capture_output=True).returncode == 0:
            return py
    return None


def sintetizar(itens, fontes, fmt):
    py = python_com_numpy()
    if py is None:
        return None
    c.titulo(f"Sintese propria ({len(itens)} efeitos, sfx_sintese.py)")
    pedido = {"alvos": {i["sintese"]: i["alvo_db"] for i in itens}, "itens": [], "resultado": str(TMP / "sintese.json")}
    for item in itens:
        camadas = []
        for n, camada in enumerate(item.get("camadas", []), 1):
            origem = TMP / f"{item['nome']}-camada-{n}{Path(camada['membro']).suffix.lower()}"
            origem.write_bytes(ler_membro(fontes, camada["pacote"], camada["membro"]))
            bruto = TMP / f"{item['nome']}-camada-{n}.f32"
            r = c.ffmpeg(["-y", "-i", str(origem), "-ac", "1", "-ar", str(fmt["taxa"]), "-f", "f32le", *FLAGS_SAIDA, str(bruto)])
            if r.returncode != 0 or not bruto.is_file():
                c.falhar(f"ffmpeg falhou lendo a camada {camada['membro']}: {r.stderr[-400:]}")
            camadas.append(str(bruto))
        pedido["itens"].append({"nome": item["nome"], "receita": item["sintese"], "camadas": camadas, "saida": str(TMP / f"{item['nome']}-sintese.f32")})
    c.escrever_json(TMP / "pedido.json", pedido)
    r = subprocess.run([str(py), "-I", "-B", str(SINTESE), str(TMP / "pedido.json")], cwd=str(c.AUDIO_DIR))
    if r.returncode != 0:
        c.falhar("a sintese dos efeitos falhou (veja a saida acima)")
    return c.ler_json(TMP / "sintese.json")


def preparar_sintese(item, fmt):
    inter = TMP / f"{item['nome']}-float.wav"
    bruto = TMP / f"{item['nome']}-sintese.f32"
    r = c.ffmpeg(["-y", "-f", "f32le", "-ar", str(fmt["taxa"]), "-ac", "1", "-i", str(bruto), "-c:a", "pcm_f32le", *FLAGS_SAIDA, str(inter)])
    if r.returncode != 0 or not inter.is_file():
        c.falhar(f"ffmpeg falhou preparando {item['nome']}: {r.stderr[-400:]}")
    return inter


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
    if "sintese" in item:
        ganho = min(0.0, fmt["teto_pico_dbtp"] - m["pico_dbtp"])
    else:
        ganho = min(fmt["alvo_lufs_momentaneo_max"] - m["lufs_momentaneo_max"], fmt["teto_pico_dbtp"] - m["pico_dbtp"])
    ganho = round(ganho, 1)
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = c.ffmpeg(["-y", "-i", str(inter), "-af", f"volume={ganho}dB", "-c:a", fmt["codec"], "-ar", str(fmt["taxa"]), "-ac", str(fmt["canais"]), *FLAGS_SAIDA, str(destino)])
    if r.returncode != 0 or not destino.is_file():
        c.falhar(f"ffmpeg falhou gravando {destino.name}: {r.stderr[-400:]}")
    return ganho


def segundos(valor):
    return f"{valor:.2f}".replace(".", ",")


def origem_legivel(it, fontes):
    def citar(ref):
        pac = fontes[ref["pacote"]]
        return f"[{pac['nome']}]({pac['pagina']}), `{Path(ref['membro']).name}`, {pac['licenca']}"

    origem = it["origem"]
    if "sintese" not in origem:
        return citar(origem)
    if origem.get("camadas"):
        return "síntese própria sobre gravação de " + "; ".join(citar(camada) for camada in origem["camadas"])
    return "síntese própria"


def linha_do_catalogo(it, fontes):
    medida = f"{segundos(it['duracao'])} s"
    if it.get("ancora"):
        medida += f", âncora {segundos(it['ancora'])} s"
    produtos = "" if it["produtos"] == ["todos"] else f" Produtos: {', '.join(it['produtos'])}."
    return f"- `{it['arquivo']}` - {medida}. Quando usar: {it['uso']}.{produtos} Origem: {origem_legivel(it, fontes)}."


def secao_do_catalogo(itens, fontes):
    linhas = []
    por_cat = {}
    for item in itens:
        por_cat.setdefault(item["categoria"], []).append(item)
    for cat, grupo in por_cat.items():
        linhas += [f"### {cat}", ""]
        linhas += [linha_do_catalogo(it, fontes) for it in grupo]
        linhas.append("")
    return linhas


def montar_catalogo(manifesto, fontes, combinacoes):
    fmt = manifesto["formato"]
    linhas = [
        "# Catálogo de efeitos sonoros",
        "",
        "Efeitos curtos para Reels de todos os produtos, gerados por `python content-engine/audio/sfx_setup.py` (licenças em `LICENCAS.md`). Este arquivo é gerado: para mudar a seleção, edite `content-engine/audio/sfx_selecao.json` e rode o setup de novo.",
        "",
        f"- Formato: WAV PCM 16 bits, {fmt['taxa']} Hz, mono, pico real até {fmt['teto_pico_dbtp']:.0f} dBTP, sem clique nas pontas.",
        "- Dois conjuntos: o **cine** (pós-produção: corpo, cauda, subgrave e um pouco de sala) é o padrão para peça nova; a **biblioteca clássica** (interface e jogo, seca) continua valendo para tema retrô e para as composições antigas.",
        "- Âncora: o instante, dentro do arquivo, que cai em cima do movimento (pico do whoosh, fim do riser, impacto da transição pronta). A deixa vai em `t = momento do movimento - âncora`. Efeito sem âncora começa no instante 0: a deixa é o próprio momento.",
        "- Nível do conjunto cine: fixado por família para `volume` 1.0 já servir sem voz (impacto mais alto que whoosh, whoosh mais alto que tique). Com voz, use de 0.4 a 0.7. Medidas de cada arquivo em `sfx.json`.",
        f"- Nível da biblioteca clássica: pico de loudness momentânea em {fmt['alvo_lufs_momentaneo_max']:.0f} LUFS e pico real até {fmt['teto_pico_dbtp']:.0f} dBTP (o que vier primeiro).",
        "- Para ouvir todos em sequência com o nome na tela: `sfx/catalogo.mp4` (refazer com `python content-engine/audio/catalogo_audio.py`).",
        "- Produtos: sem indicação = serve para qualquer produto; os listados são sugestão, não regra.",
        "",
    ]
    for chave, titulo in CONJUNTOS.items():
        linhas += [f"## {titulo}", ""]
        linhas += secao_do_catalogo([i for i in manifesto["itens"] if i.get("conjunto") == chave], fontes)
    linhas += ["## Combinações recomendadas", ""]
    for combinacao in combinacoes:
        linhas.append(f"- **{combinacao['nome']}:** {combinacao['receita']}")
    linhas += ["", "## Biblioteca clássica (interface e jogo)", ""]
    linhas += secao_do_catalogo([i for i in manifesto["itens"] if not i.get("conjunto")], fontes)
    (c.SFX_DIR / "CATALOGO.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")


def main():
    p = argparse.ArgumentParser(description="Baixa os pacotes CC0 fixados, roda a sintese propria (sfx_sintese.py) e refaz a biblioteca de efeitos em content-engine/audio/sfx/.")
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
    usados = {p for i in itens for p in pacotes_do_item(i)}
    faltam = sorted(usados - set(fontes))
    if faltam:
        c.falhar(f"pacotes sem fonte em sfx_fontes.json: {', '.join(faltam)}")

    registros = {}
    if c.SFX_MANIFESTO.is_file():
        registros = {i["arquivo"]: i for i in c.ler_json(c.SFX_MANIFESTO).get("itens", [])}
    anterior = {arquivo: registro["sha256"] for arquivo, registro in registros.items()}

    baixar_pacotes(fontes, usados, a.offline)
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    de_sintese = [i for i in itens if "sintese" in i]
    sintese = sintetizar(de_sintese, fontes, fmt) if de_sintese else {}

    c.titulo(f"Biblioteca ({len(itens)} efeitos)")
    manifesto_itens = []
    mudaram = 0
    for item in itens:
        rel = f"{item['categoria']}/{item['nome']}.wav"
        destino = c.SFX_DIR / rel
        if "sintese" in item and sintese is None:
            if rel not in registros or not destino.is_file() or c.sha256(destino) != anterior[rel]:
                c.falhar(f"{rel} e de sintese e precisa do numpy: rode python content-engine/audio/voz_setup.py (cria o .venv) e repita")
            manifesto_itens.append({**registros[rel], "uso": item["uso"], "produtos": item["produtos"]})
            c.linha("OK", rel, "mantido (sem numpy para refazer a sintese)")
            continue
        if "sintese" in item:
            inter = preparar_sintese(item, fmt)
        else:
            inter = preparar(item, extrair(item, fontes), fmt)
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
        }
        if "sintese" in item:
            feito = sintese[item["nome"]]
            registro["conjunto"] = item["conjunto"]
            registro["ancora"] = feito["ancora"]
            registro["alvo_db"] = item["alvo_db"]
            registro["nivel_db"] = round(feito["nivel_db"] + ganho, 1)
            registro["faixas_pct"] = feito["faixas_pct"]
            registro["origem"] = {"sintese": SINTESE.name, "receita": item["sintese"], "semente": feito["semente"]}
            if item.get("camadas"):
                registro["origem"]["camadas"] = item["camadas"]
        else:
            registro["origem"] = {"pacote": item["pacote"], "membro": item["membro"]}
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
    montar_catalogo(manifesto, fontes, selecao.get("combinacoes", []))
    shutil.rmtree(TMP, ignore_errors=True)
    total = sum(i["bytes"] for i in manifesto_itens)
    c.titulo("Resultado")
    c.linha("OK", f"{len(manifesto_itens)} efeitos em {c.rel(c.SFX_DIR)}", f"{total / (1 << 20):.2f} MB; manifesto sfx.json e CATALOGO.md atualizados")
    if anterior and mudaram:
        c.linha("ATENCAO", f"{mudaram} arquivo(s) mudaram em relacao ao manifesto anterior", "o FFmpeg fixado deveria repetir os mesmos bytes; confira a versao em content-engine/video/bin")


if __name__ == "__main__":
    main()
