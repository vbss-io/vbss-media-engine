import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c

CACHE_MUSICA = c.CACHE_DIR / "musica"
TMP = CACHE_MUSICA / "tmp"
FLAGS_SAIDA = ["-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1"]
EXTENSOES = (".m4a", ".mp3", ".ogg", ".opus", ".flac", ".wav")
TAXA_BPM = 11025
LIMITE_TOTAL_MB = 25
TENTATIVAS_DE_PICO = 4


def python_do_venv():
    pasta = "Scripts" if os.name == "nt" else "bin"
    return c.VENV_DIR / pasta / f"python{c.SUFIXO_EXE}"


def arquivo_da_fonte(chave, info):
    sufixo = Path(urllib.parse.unquote(urllib.parse.urlparse(info["url"]).path)).suffix.lower()
    return CACHE_MUSICA / f"{chave}{sufixo}"


def baixar_fontes(fontes, usadas, offline):
    c.titulo("Fontes (CC0, SHA-256 fixado)")
    for chave in sorted(usadas):
        info = fontes[chave]
        destino = arquivo_da_fonte(chave, info)
        if offline:
            if not destino.is_file() or c.sha256(destino) != info["sha256"]:
                c.falhar(f"{destino.name} ausente ou diferente no cache e --offline foi pedido")
            estado = "cache"
        else:
            estado = c.baixar_conferido(info["url"], destino, info["sha256"])
        c.linha("OK", f"{chave} ({estado})", info["sha256"][:16])


def extrair(faixa, fontes):
    origem = arquivo_da_fonte(faixa["fonte"], fontes[faixa["fonte"]])
    if "membro" not in faixa:
        return origem
    with zipfile.ZipFile(origem) as z:
        if faixa["membro"] not in z.namelist():
            c.falhar(f"{faixa['membro']} nao existe em {origem.name}")
        dados = z.read(faixa["membro"])
    saida = TMP / f"{faixa['id']}-origem{Path(faixa['membro']).suffix.lower()}"
    saida.write_bytes(dados)
    return saida


def preparar(faixa, origem, fmt):
    filtros = []
    corte = faixa.get("corte")
    if corte:
        filtros.append(f"atrim=start={corte['inicio']}:end={corte['fim']},asetpts=PTS-STARTPTS")
    filtros.append(f"aresample={fmt['taxa']}")
    filtros.append("aformat=sample_fmts=flt:channel_layouts=stereo")
    inter = TMP / f"{faixa['id']}-float.wav"
    r = c.ffmpeg(["-y", "-i", str(origem), "-af", ",".join(filtros), "-c:a", "pcm_f32le", *FLAGS_SAIDA, str(inter)])
    if r.returncode != 0 or not inter.is_file():
        c.falhar(f"ffmpeg falhou preparando {faixa['id']}: {r.stderr[-400:]}")
    return inter


def normalizar(faixa, inter, destino, fmt):
    m = c.medir(inter)
    if m["lufs_integrado"] is None or m["pico_dbtp"] is None:
        c.falhar(f"nao consegui medir {faixa['id']}: {m}")
    ganho = round(min(fmt["alvo_lufs_integrado"] - m["lufs_integrado"], fmt["teto_pico_dbtp"] - m["pico_dbtp"]), 1)
    fades = []
    entrada = float(faixa.get("fade_entrada", 0))
    saida = float(faixa.get("fade_saida", 0))
    if entrada > 0:
        fades.append(f"afade=t=in:st=0:d={entrada}")
    if saida > 0:
        fades.append(f"afade=t=out:st={max(0.0, m['duracao'] - saida):.3f}:d={saida}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(TENTATIVAS_DE_PICO):
        r = c.ffmpeg(["-y", "-i", str(inter), "-af", ",".join([f"volume={ganho}dB", *fades]), "-c:a", fmt["codec"], "-b:a", fmt["taxa_bits"],
                      "-ar", str(fmt["taxa"]), "-ac", str(fmt["canais"]), *FLAGS_SAIDA, str(destino)])
        if r.returncode != 0 or not destino.is_file():
            c.falhar(f"ffmpeg falhou gravando {destino.name}: {r.stderr[-400:]}")
        pico = c.medir(destino)["pico_dbtp"]
        if pico is None or pico <= fmt["teto_pico_dbtp"]:
            return ganho
        ganho = round(ganho - (pico - fmt["teto_pico_dbtp"]) - 0.1, 1)
    c.falhar(f"{destino.name} continua acima do teto de pico depois de {TENTATIVAS_DE_PICO} tentativas")


def medir_bpm(arquivo, laco):
    py = python_do_venv()
    if not py.is_file():
        return None
    pcm = subprocess.run(
        [str(c.ffmpeg_path()), "-hide_banner", "-nostdin", "-v", "error", "-i", str(arquivo), "-ac", "1", "-ar", str(TAXA_BPM), "-f", "f32le", "-"],
        capture_output=True, timeout=300,
    )
    if pcm.returncode != 0 or not pcm.stdout:
        return None
    args = [str(py), "-I", str(c.AUDIO_DIR / "musica_bpm.py")] + (["--laco"] if laco else [])
    r = subprocess.run(args, input=pcm.stdout, capture_output=True, timeout=300)
    try:
        return json.loads(r.stdout.decode("utf-8"))["bpm"]
    except (ValueError, KeyError):
        return None


def virgula(numero):
    return f"{numero:g}".replace(".", ",")


def texto_bpm(bpm):
    return "sem pulso marcado" if bpm is None else f"{virgula(bpm)} bpm"


def montar_catalogo(manifesto):
    fmt = manifesto["formato"]
    linhas = [
        "# Catálogo de música de fundo",
        "",
        "Faixas instrumentais de fundo para Reels, geradas por `python content-engine/audio/musica_setup.py` a partir de fontes CC0 (licenças em `LICENCAS.md`). Este arquivo é gerado: para mudar a seleção, edite `content-engine/audio/musica_fontes.json` e rode o setup de novo.",
        "",
        f"- Formato: {fmt['codec'].upper()} em `.{fmt['extensao']}`, {fmt['taxa']} Hz, estéreo, {fmt['taxa_bits']}. O `trilha.py` lê a faixa daqui e grava na composição só o `assets/musica/base.wav` já mixado.",
        f"- Nível: {fmt['alvo_lufs_integrado']:.0f} LUFS integrado, pico real até {virgula(fmt['teto_pico_dbtp'])} dBTP (o que vier primeiro).",
        "- Laço: `sim` = a duração fecha compassos inteiros e a faixa repete no tempo; `não` = repete com fade nas pontas.",
        "- BPM: medido por autocorrelação dos ataques (aproximado); serve para casar corte de cena com a batida.",
        "- Uso no `trilha.json`: `\"musica\": {\"faixa\": \"<id>\"}`.",
        "- Produtos: `todos` = serve para qualquer produto; os demais são sugestão, não regra.",
        "",
    ]
    por_clima = {}
    for item in manifesto["itens"]:
        por_clima.setdefault(item["clima"], []).append(item)
    for clima, itens in por_clima.items():
        linhas += [f"## {clima}", ""]
        for it in itens:
            dur = f"{it['duracao']:.1f}".replace(".", ",")
            linhas += [
                f"- `{it['id']}` ({dur} s, {texto_bpm(it['bpm'])}, laço: {'sim' if it['laco'] else 'não'})",
                f"  - Uso: {it['uso']}.",
                f"  - Produtos: {', '.join(it['produtos'])}.",
                f"  - Origem: [{it['origem']['nome']}]({it['pagina']}), de {it['autor']}, {it['licenca']}.",
            ]
        linhas.append("")
    (c.MUSICA_DIR / "CATALOGO.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")


def main():
    p = argparse.ArgumentParser(description="Baixa as fontes CC0 fixadas e refaz a biblioteca de musica de fundo em content-engine/audio/music/.")
    p.add_argument("--offline", action="store_true", help="usa so o cache (.cache/musica), sem rede")
    a = p.parse_args()

    c.exigir_ffmpeg()
    cfg = c.ler_json(c.MUSICA_FONTES)
    fontes, fmt, faixas = cfg["fontes"], cfg["formato"], cfg["faixas"]
    ids = [f["id"] for f in faixas]
    if len(set(ids)) != len(ids):
        c.falhar("musica_fontes.json tem ids repetidos")
    faltam = sorted({f["fonte"] for f in faixas} - set(fontes))
    if faltam:
        c.falhar(f"faixas sem fonte em musica_fontes.json: {', '.join(faltam)}")
    nao_cc0 = sorted(k for k in {f["fonte"] for f in faixas} if fontes[k].get("licenca") != "CC0")
    if nao_cc0:
        c.falhar(f"fonte sem licenca CC0: {', '.join(nao_cc0)}")

    anterior = {}
    if c.MUSICA_MANIFESTO.is_file():
        anterior = {i["arquivo"]: i["sha256"] for i in c.ler_json(c.MUSICA_MANIFESTO).get("itens", [])}

    baixar_fontes(fontes, {f["fonte"] for f in faixas}, a.offline)
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)

    c.titulo(f"Biblioteca ({len(faixas)} faixas)")
    if not python_do_venv().is_file():
        c.linha("AVISO", "venv de audio ausente: bpm fica nulo", "rode python content-engine/audio/voz_setup.py para medir o bpm")
    itens = []
    mudaram = 0
    for faixa in faixas:
        nome = f"{faixa['id']}.{fmt['extensao']}"
        destino = c.MUSICA_DIR / nome
        inter = preparar(faixa, extrair(faixa, fontes), fmt)
        ganho = normalizar(faixa, inter, destino, fmt)
        m = c.medir(destino)
        sha = c.sha256(destino)
        bpm = medir_bpm(destino, faixa["laco"]) if faixa.get("pulso", True) else None
        estado = "novo" if nome not in anterior else ("igual" if anterior[nome] == sha else "MUDOU")
        mudaram += estado == "MUDOU"
        c.linha("OK", nome, f"{m['duracao']:.2f}s  I {m['lufs_integrado']} LUFS  pico {m['pico_dbtp']} dBTP  ganho {ganho:+.1f} dB  {texto_bpm(bpm)}  {estado}")
        fonte = fontes[faixa["fonte"]]
        origem = {"fonte": faixa["fonte"], "nome": fonte["nome"], "url": fonte["url"], "sha256": fonte["sha256"]}
        for chave in ("membro", "corte"):
            if faixa.get(chave):
                origem[chave] = faixa[chave]
        itens.append({
            "id": faixa["id"],
            "arquivo": nome,
            "sha256": sha,
            "bytes": destino.stat().st_size,
            "duracao": m["duracao"],
            "bpm": bpm,
            "laco": faixa["laco"],
            "clima": faixa["clima"],
            "uso": faixa["uso"],
            "produtos": faixa["produtos"],
            "lufs_integrado": m["lufs_integrado"],
            "pico_dbtp": m["pico_dbtp"],
            "ganho_db": ganho,
            "autor": fonte["autor"],
            "pagina": fonte["pagina"],
            "licenca": fonte["licenca"],
            "origem": origem,
        })

    esperados = {i["arquivo"] for i in itens}
    for arq in sorted(p for p in c.MUSICA_DIR.iterdir() if p.suffix.lower() in EXTENSOES):
        if arq.name not in esperados:
            arq.unlink()
            c.linha("OK", f"removido (fora da selecao): {arq.name}")

    manifesto = {"formato": fmt, "itens": itens}
    c.escrever_json(c.MUSICA_MANIFESTO, manifesto)
    montar_catalogo(manifesto)
    shutil.rmtree(TMP, ignore_errors=True)
    total = sum(i["bytes"] for i in itens) / (1 << 20)
    c.titulo("Resultado")
    c.linha("OK", f"{len(itens)} faixas em {c.rel(c.MUSICA_DIR)}", f"{total:.2f} MB; manifesto musica.json e CATALOGO.md atualizados")
    if total > LIMITE_TOTAL_MB:
        c.linha("ATENCAO", f"biblioteca acima de {LIMITE_TOTAL_MB} MB", "encurte cortes ou tire faixas em musica_fontes.json")
    if anterior and mudaram:
        c.linha("ATENCAO", f"{mudaram} arquivo(s) mudaram em relacao ao manifesto anterior", "o FFmpeg fixado deveria repetir os mesmos bytes; confira a versao em content-engine/video/bin")


if __name__ == "__main__":
    main()
