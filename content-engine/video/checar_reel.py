import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
import frames

LARGURA = 1080
ALTURA = 1920
FPS = 30
DURACAO_MIN = 5.0
DURACAO_MAX = 90.0
RUIDO_PARADO = 0.001
PARADO_MINIMO = 0.2
PARADO_AVISO = 0.6
PARADO_FALHA = 0.8
PARADO_LONGO = 0.3
PARADO_FRACAO = 0.2
LUFS_ALVO = -14.0
LUFS_FOLGA = 1.5
LUFS_FOLGA_AVISO = 3.0
PICO_MAXIMO = -1.0
PICO_AVISO = -0.5
TEXTO_MINIMO = 1.0
LISO_CARTELA = 0.8
PRETO = 16
MUSICA_ABAIXO_DB = 10.0
MUSICA_ABAIXO_AVISO_DB = 6.0
QUIQUE_FRACAO = 0.12
QUIQUE_MINIMO = 3
TOLERANCIA_PX = 2
GRADE_TOLERANCIA = 0.04
AMOSTRA = (90, 160)
QUIQUE_RE = re.compile(r"back\.(?:out|inOut|in)|elastic|bounce|E\.acento|EASE\.acento|K\.toque\(")
ANIMACAO_RE = re.compile(r"\btl\.(?:to|fromTo|from)\(|\bK\.(?!palavras|legenda|EASE|DUR)[a-zA-Z]+\(")
LEGENDA_RE = re.compile(r"K\.legenda\(([^;]*)\);")


class Relatorio:
    def __init__(self):
        self.falhas = 0
        self.avisos = 0

    def passa(self, nome, detalhe=""):
        c.linha("PASS", nome, detalhe)

    def falha(self, nome, detalhe=""):
        self.falhas += 1
        c.linha("FAIL", nome, detalhe)

    def aviso(self, nome, detalhe=""):
        self.avisos += 1
        c.linha("AVISO", nome, detalhe)

    def info(self, nome, detalhe=""):
        c.linha("INFO", nome, detalhe)


def ffmpeg(args, binario=False, timeout=600):
    return subprocess.run([str(c.ffmpeg_path()), "-hide_banner", "-nostdin", *args], capture_output=True, timeout=timeout, **({} if binario else {"text": True, "encoding": "utf-8", "errors": "replace"}))


def trechos_parados(saida, duracao):
    inicios = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", saida)]
    duracoes = [float(x) for x in re.findall(r"freeze_duration:\s*([\d.]+)", saida)]
    trechos = []
    for i, inicio in enumerate(inicios):
        d = duracoes[i] if i < len(duracoes) else max(0.0, duracao - inicio)
        trechos.append((round(inicio, 3), round(d, 3)))
    return trechos


def avaliar_parados(trechos, duracao):
    maior = max(trechos, key=lambda x: x[1]) if trechos else (0.0, 0.0)
    soma = sum(d for _, d in trechos if d >= PARADO_LONGO)
    fracao = soma / duracao if duracao else 0.0
    if maior[1] > PARADO_FALHA or fracao > PARADO_FRACAO:
        nivel = "falha"
    elif maior[1] > PARADO_AVISO:
        nivel = "aviso"
    else:
        nivel = "passa"
    return {"nivel": nivel, "maior": maior, "soma": round(soma, 3), "fracao": round(fracao, 4)}


def medir_parados(video, duracao):
    r = ffmpeg(["-i", str(video), "-vf", f"freezedetect=n={RUIDO_PARADO}:d={PARADO_MINIMO}", "-an", "-f", "null", "-"])
    return trechos_parados(r.stderr, duracao)


def medir_som(arquivo, inicio=None, fim=None):
    args = []
    if inicio is not None:
        args += ["-ss", f"{inicio:.3f}", "-to", f"{fim:.3f}"]
    r = ffmpeg([*args, "-i", str(arquivo), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    resumo = r.stderr.split("Summary:")[-1] if "Summary:" in r.stderr else ""
    lufs = re.search(r"I:\s*(-?[\d.]+) LUFS", resumo)
    pico = re.search(r"Peak:\s*(-?[\d.]+) dBFS", resumo)
    return (float(lufs.group(1)) if lufs else None, float(pico.group(1)) if pico else None)


def avaliar_som(lufs, pico):
    if lufs is None:
        return "falha"
    desvio = abs(lufs - LUFS_ALVO)
    if desvio > LUFS_FOLGA_AVISO or (pico is not None and pico > PICO_AVISO):
        return "falha"
    if desvio > LUFS_FOLGA or (pico is not None and pico > PICO_MAXIMO):
        return "aviso"
    return "passa"


def quadro_cinza(video, t, recorte=None):
    filtro = (f"crop=iw*{recorte[2]}:ih*{recorte[3]}:iw*{recorte[0]}:ih*{recorte[1]}," if recorte else "") + f"scale={AMOSTRA[0]}:{AMOSTRA[1]},format=gray"
    r = ffmpeg(["-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", filtro, "-f", "rawvideo", "-"], binario=True)
    return r.stdout if len(r.stdout) == AMOSTRA[0] * AMOSTRA[1] else None


def area_lisa(cinza, largura=AMOSTRA[0], limiar=6):
    altura = len(cinza) // largura
    lisos = 0
    total = 0
    for y in range(altura - 1):
        base = y * largura
        for x in range(largura - 1):
            v = cinza[base + x]
            if abs(v - cinza[base + x + 1]) + abs(v - cinza[base + largura + x]) < limiar:
                lisos += 1
            total += 1
    return lisos / total if total else 1.0


def fracao_clara(cinza, limiar=215):
    return sum(1 for v in cinza if v >= limiar) / len(cinza) if cinza else 0.0


def zona_segura():
    return {"x0": LARGURA * frames.SAFE_LEFT, "x1": LARGURA * (1 - frames.SAFE_RIGHT), "y0": ALTURA * frames.SAFE_TOP, "y1": ALTURA * (1 - frames.SAFE_BOTTOM)}


def fora_da_zona(caixa, zona=None, tolerancia=TOLERANCIA_PX):
    z = zona or zona_segura()
    lados = []
    if caixa["x"] < z["x0"] - tolerancia:
        lados.append("esquerda")
    if caixa["x"] + caixa["w"] > z["x1"] + tolerancia:
        lados.append("direita")
    if caixa["y"] < z["y0"] - tolerancia:
        lados.append("topo")
    if caixa["y"] + caixa["h"] > z["y1"] + tolerancia:
        lados.append("rodape")
    return lados


def contar_quiques(script):
    quiques = len(QUIQUE_RE.findall(script))
    animacoes = len(ANIMACAO_RE.findall(script))
    limite = max(QUIQUE_MINIMO, int(animacoes * QUIQUE_FRACAO))
    return quiques, animacoes, limite


def falas_liberadas(montagem, pasta):
    saida = {}
    for x in (montagem or {}).get("pronuncia", []):
        ouvida = x.get("ouvida")
        wav = Path(pasta) / "assets" / "voz" / str(x.get("arquivo"))
        if ouvida and wav.is_file() and hashlib.sha256(wav.read_bytes()).hexdigest() == ouvida.get("sha256"):
            saida[x["arquivo"]] = f"{ouvida.get('por')}, {ouvida.get('em')}"
    return saida


def geometria_da_legenda(html):
    achou = LEGENDA_RE.search(html)
    if not achou:
        return None
    opcoes = achou.group(1)
    base = re.search(r"\bbase:\s*[\"']?([\d.]+)(%|px)?", opcoes)
    largura = re.search(r"\blargura:\s*[\"']?([\d.]+)", opcoes)
    tamanho = re.search(r"\btamanho:\s*[\"']?([\d.]+)", opcoes)
    linhas = re.search(r"\blinhas:\s*(\d+)", opcoes)
    base_px = ALTURA * 0.24
    if base:
        base_px = float(base.group(1)) if base.group(2) == "px" else ALTURA * float(base.group(1)) / 100
    w = float(largura.group(1)) if largura else 800.0
    px = float(tamanho.group(1)) if tamanho else 68.0
    n = int(linhas.group(1)) if linhas else 2
    return {"x": (LARGURA - w) / 2, "w": w, "y": ALTURA - base_px - px * 1.14 * n, "h": px * 1.14 * n}


def no_compasso(inicios, bpm, tolerancia=GRADE_TOLERANCIA):
    passo = 60.0 / bpm
    return [t for t in inicios if abs(t / passo - round(t / passo)) * passo > tolerancia]


def gerado_mudou(montagem, index):
    registrado = (montagem.get("gerados") or {}).get("index.html")
    return bool(registrado) and registrado != hashlib.sha256(Path(index).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def checar_video(r, video):
    info = c.resumo_video(video)
    dur = info["duracao"]
    c.titulo(f"Video: {video.name} ({info.get('largura')}x{info.get('altura')}, {dur} s, {info.get('fps')} fps, {info.get('audio')} faixa(s) de audio)")
    if info.get("largura") == LARGURA and info.get("altura") == ALTURA and abs((info.get("fps") or 0) - FPS) < 0.1:
        r.passa("formato", "1080x1920 a 30 fps")
    else:
        r.falha("formato", f"esperado 1080x1920 a 30 fps, veio {info.get('largura')}x{info.get('altura')} a {info.get('fps')} fps")
    if DURACAO_MIN <= dur <= DURACAO_MAX:
        r.passa("duracao", f"{dur:.1f} s (aceito de {DURACAO_MIN:g} a {DURACAO_MAX:g} s)")
    else:
        r.aviso("duracao", f"{dur:.1f} s esta fora de {DURACAO_MIN:g} a {DURACAO_MAX:g} s")

    trechos = medir_parados(video, dur)
    p = avaliar_parados(trechos, dur)
    detalhe = (f"maior trecho parado {p['maior'][1]:.2f} s em {p['maior'][0]:.2f} s; soma dos trechos de {PARADO_LONGO} s ou mais: {p['soma']:.1f} s ({p['fracao'] * 100:.0f}% do video). "
               f"Limites: falha acima de {PARADO_FALHA} s ou de {PARADO_FRACAO * 100:.0f}%, aviso acima de {PARADO_AVISO} s (piloto: 0,47 s e 9%)")
    {"passa": r.passa, "aviso": r.aviso, "falha": r.falha}[p["nivel"]]("trecho parado", detalhe)

    if not info.get("audio"):
        r.falha("som", "o video saiu sem faixa de audio")
    else:
        lufs, pico = medir_som(video)
        nivel = avaliar_som(lufs, pico)
        detalhe = f"{lufs} LUFS integrado, pico {pico} dBTP (alvo {LUFS_ALVO:g} LUFS com folga de {LUFS_FOLGA:g}; pico ate {PICO_MAXIMO:g} dBTP)"
        {"passa": r.passa, "aviso": r.aviso, "falha": r.falha}[nivel]("loudness final", detalhe)

    lisos = []
    escuro = False
    for t in (0.0, 0.5, 0.95):
        cinza = quadro_cinza(video, min(t, max(0.0, dur - 0.1)))
        if cinza is None:
            continue
        lisos.append(area_lisa(cinza))
        if t == 0.0 and sum(cinza) / len(cinza) < PRETO:
            escuro = True
    if escuro:
        r.falha("primeiro quadro", "o video abre em tela preta")
    elif lisos and min(lisos) > LISO_CARTELA:
        r.aviso("primeiro segundo (imagem)", f"{min(lisos) * 100:.0f}% da tela e area lisa no primeiro segundo: parece cartela de titulo, nao o resultado em tela cheia (limite {LISO_CARTELA * 100:.0f}%)")
    elif lisos:
        r.passa("primeiro segundo (imagem)", f"a tela tem conteudo desde o quadro 0 ({min(lisos) * 100:.0f}% de area lisa; cartela costuma passar de {LISO_CARTELA * 100:.0f}%)")
    return info


def checar_composicao(r, video, pasta, info):
    c.titulo(f"Composicao: {pasta.name}")
    index = pasta / "index.html"
    if not index.is_file():
        r.falha("composicao", f"{pasta} nao tem index.html")
        return
    html = index.read_text(encoding="utf-8")
    montagem = json.loads((pasta / "montagem.json").read_text(encoding="utf-8")) if (pasta / "montagem.json").is_file() else None
    dur_comp = re.search(r'data-composition-id="[^"]+"[^>]*\bdata-duration="([\d.]+)"', html)
    if dur_comp and abs(float(dur_comp.group(1)) - info["duracao"]) <= 0.2:
        r.passa("video e composicao", f"mesma duracao ({dur_comp.group(1)} s)")
    else:
        r.falha("video e composicao", f"a composicao tem {dur_comp.group(1) if dur_comp else '?'} s e o video {info['duracao']} s: renderize de novo")
    if video.stat().st_mtime < index.stat().st_mtime:
        r.aviso("video e composicao", "o video e mais antigo que o index.html: renderize de novo antes de confiar nesta checagem")

    if montagem and not montagem.get("incompleta"):
        primeiro = montagem.get("primeiro_texto")
        tipo = (montagem.get("batidas") or [{}])[0].get("tipo")
        if primeiro is not None and primeiro < TEXTO_MINIMO:
            r.falha("primeiro segundo (texto)", f"um texto entra em {primeiro:.2f} s; nada de titulo ou cartela antes de {TEXTO_MINIMO:g} s")
        else:
            r.passa("primeiro segundo (texto)", f"primeiro texto da peca entra em {primeiro if primeiro is not None else '-'} s (cena de abertura: {tipo}); so a legenda da fala aparece antes")
        ruins = [(t["nome"], fora_da_zona(t)) for t in montagem.get("textos", [])]
        ruins = [(n, lados) for n, lados in ruins if lados]
        if ruins:
            r.falha("texto na zona segura", "; ".join(f"{n} passa da margem ({', '.join(lados)})" for n, lados in ruins))
        else:
            r.passa("texto na zona segura", f"{len(montagem.get('textos', []))} bloco(s) de texto dentro das margens do Reels (posicao planejada pelo montador)")
        if gerado_mudou(montagem, index):
            r.aviso("ajuste manual", "o index.html mudou depois da montagem: as posicoes de texto acima podem nao valer")
        bpm = (montagem.get("musica") or {}).get("bpm")
        if bpm and (montagem.get("musica") or {}).get("cortes") == "compasso":
            fora = no_compasso([b["inicio"] for b in montagem["batidas"]], bpm)
            if fora:
                r.aviso("cortes no compasso", f"corte(s) fora da batida da musica ({bpm:g} bpm): " + ", ".join(f"{t:.2f} s" for t in fora))
            else:
                r.passa("cortes no compasso", f"{len(montagem['batidas']) - 1} corte(s) de cena em multiplos de {60 / bpm:.3f} s ({bpm:g} bpm)")
    else:
        r.info("primeiro segundo (texto) e texto na zona segura", "sem montagem.json (peca escrita a mao): nao da para conferir; olhe os quadros do frames.py --guias")

    geo = geometria_da_legenda(html)
    legenda_json = json.loads((pasta / "legenda.json").read_text(encoding="utf-8")) if (pasta / "legenda.json").is_file() else None
    if not geo or not legenda_json or not legenda_json.get("blocos"):
        r.falha("legenda", "a peca nao tem legenda sincronizada (legenda.json + K.legenda no index.html)")
    else:
        lados = fora_da_zona(geo)
        if lados:
            r.falha("legenda na zona segura", f"a faixa da legenda passa da margem ({', '.join(lados)}): x {geo['x']:.0f} a {geo['x'] + geo['w']:.0f}, y {geo['y']:.0f} a {geo['y'] + geo['h']:.0f}")
        else:
            r.passa("legenda na zona segura", f"faixa de {geo['w']:.0f} px, de y {geo['y']:.0f} a {geo['y'] + geo['h']:.0f} (rodape do Reels comeca em {zona_segura()['y1']:.0f})")
        blocos = legenda_json["blocos"]
        amostras = [blocos[i] for i in sorted({0, len(blocos) // 2, len(blocos) - 1})]
        recorte = (geo["x"] / LARGURA, geo["y"] / ALTURA, geo["w"] / LARGURA, geo["h"] / ALTURA)
        vistos = 0
        for b in amostras:
            cinza = quadro_cinza(video, min((b["inicio"] + b["fim"]) / 2, info["duracao"] - 0.1), recorte)
            if cinza is not None and fracao_clara(cinza) >= 0.01:
                vistos += 1
        if vistos >= max(1, len(amostras) - 1):
            r.passa("legenda no video", f"{len(blocos)} bloco(s); texto claro na faixa da legenda em {vistos} de {len(amostras)} instantes de fala")
        else:
            r.falha("legenda no video", f"so {vistos} de {len(amostras)} instantes de fala tem texto claro na faixa da legenda")
        falas = legenda_json.get("falas", [])
        apontadas = [f for f in falas if f.get("pronuncia") and not f["pronuncia"]["ok"]]
        liberadas = falas_liberadas(montagem, pasta)
        ruins = [f for f in apontadas if Path(f["arquivo"]).name not in liberadas]
        if ruins:
            r.falha("pronuncia da voz", "; ".join(f"{Path(f['arquivo']).name}: " + " / ".join(f["pronuncia"]["divergencias"]) for f in ruins))
        elif apontadas:
            r.aviso("pronuncia da voz", "a conferencia apontou e uma pessoa ouviu e liberou: " + "; ".join(f"{Path(f['arquivo']).name} ({liberadas[Path(f['arquivo']).name]})" for f in apontadas))
        elif falas and all(f.get("pronuncia") for f in falas):
            r.passa("pronuncia da voz", f"{len(falas)} fala(s): o que o Whisper ouviu bate com o texto e nao ha chiado a mais")
        else:
            r.aviso("pronuncia da voz", "nao conferida (rode python content-engine/audio/legenda.py ou pronuncia.py na pasta da peca)")

    trilha = json.loads((pasta / "trilha.json").read_text(encoding="utf-8")) if (pasta / "trilha.json").is_file() else {}
    vozes = [d for d in trilha.get("deixas", []) if d.get("arquivo")]
    base = pasta / "assets" / "musica" / "base.wav"
    if not trilha.get("musica") or not base.is_file():
        r.aviso("musica", "a peca nao tem musica de fundo (chave 'musica' da trilha); so vale se quem publica vai por um audio da propria rede ao subir")
    elif not vozes:
        r.passa("musica", "presente; peca sem voz")
    else:
        niveis_voz, niveis_musica = [], []
        for d in vozes:
            wav = pasta / d["arquivo"]
            dur = float(c.probe(wav)["format"]["duration"])
            niveis_voz.append(medir_som(wav)[0])
            if dur >= 1.0:
                niveis_musica.append(medir_som(base, float(d["t"]) + 0.3, float(d["t"]) + dur)[0])
        niveis_voz = [x for x in niveis_voz if x is not None]
        niveis_musica = [x for x in niveis_musica if x is not None]
        if not niveis_voz or not niveis_musica:
            r.aviso("musica abaixo da voz", "nao consegui medir (fala curta demais ou musica muda sob a voz)")
        else:
            voz = sum(niveis_voz) / len(niveis_voz)
            mus = max(niveis_musica)
            dif = voz - mus
            detalhe = f"voz {voz:.1f} LUFS, musica sob a voz ate {mus:.1f} LUFS: {dif:.1f} dB abaixo (minimo {MUSICA_ABAIXO_DB:g} dB), medido nos arquivos da trilha"
            if dif >= MUSICA_ABAIXO_DB:
                r.passa("musica abaixo da voz", detalhe)
            elif dif >= MUSICA_ABAIXO_AVISO_DB:
                r.aviso("musica abaixo da voz", detalhe)
            else:
                r.falha("musica abaixo da voz", detalhe)

    script = "\n".join(re.findall(r"<script>(.*?)</script>", html, flags=re.S))
    quiques, animacoes, limite = contar_quiques(script)
    detalhe = f"{quiques} animacao(oes) com quique (back, elastic, bounce, toque) em {animacoes}; limite {limite}"
    if quiques > limite:
        r.falha("quique nos movimentos", detalhe + ". Troque por expo.out ou power3.out (EASE.snap e EASE.casa do kit)")
    else:
        r.passa("quique nos movimentos", detalhe)


def main():
    p = argparse.ArgumentParser(description="Checagem automatica de motion de um Reel renderizado: trecho parado, primeiro segundo, legenda, musica, loudness, duracao, texto na zona segura e quique. PASS/FAIL em portugues; sai com codigo 1 se algo falhar.")
    p.add_argument("video", help="reel.mp4 renderizado")
    p.add_argument("pasta", nargs="?", help="pasta da peca (com index.html e, se veio do montador, montagem.json)")
    a = p.parse_args()
    video = Path(a.video).resolve()
    if not video.is_file():
        c.falhar(f"video nao encontrado: {video}")
    if not c.ffmpeg_path().is_file():
        c.falhar("FFmpeg local ausente. Rode python content-engine/video/setup.py")
    r = Relatorio()
    info = checar_video(r, video)
    if a.pasta:
        pasta = Path(a.pasta).resolve()
        if not pasta.is_dir():
            c.falhar(f"{pasta} nao e uma pasta")
        checar_composicao(r, video, pasta, info)
    else:
        c.linha("INFO", "sem a pasta da peca", "legenda, musica, texto na zona segura, quique e pronuncia nao foram conferidos")
    c.titulo("Resultado")
    print("   Nao da para checar por aqui: se o primeiro segundo mostra o RESULTADO (e nao uma tela qualquer do site), se o texto transbordou a caixa planejada,")
    print("   se cada movimento caiu na palavra certa, e como a voz, a musica e os efeitos soam. Olhe os quadros (frames.py --guias) e ouca a peca inteira.")
    if r.falhas:
        c.linha("FAIL", f"{r.falhas} item(ns) reprovado(s)" + (f" e {r.avisos} aviso(s)" if r.avisos else ""), "corrija no roteiro, monte, renderize e cheque de novo")
        sys.exit(1)
    c.linha("PASS", "checagem de motion aprovada" + (f" com {r.avisos} aviso(s)" if r.avisos else ""))


if __name__ == "__main__":
    main()
