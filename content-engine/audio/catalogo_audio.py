import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c

LARGURA, ALTURA = 720, 1280
ENTRADA = 0.25
SOBRA = 0.55
MINIMO = 1.3
SEM_AUDIO = 2.4
SAIDA_PADRAO = c.SFX_DIR / "catalogo.mp4"
PASTA_PADRAO = c.WORK_DIR / "catalogo"

ESTILO = """
  @font-face{font-family:"Inter";src:url("_motor/fonts/inter-600.woff2") format("woff2");font-weight:600;font-style:normal}
  @font-face{font-family:"Inter";src:url("_motor/fonts/inter-800.woff2") format("woff2");font-weight:800;font-style:normal}
  @font-face{font-family:"Inter";src:url("_motor/fonts/inter-ext-600.woff2") format("woff2");font-weight:600;font-style:normal;unicode-range:U+0100-02BA}
  @font-face{font-family:"Inter";src:url("_motor/fonts/inter-ext-800.woff2") format("woff2");font-weight:800;font-style:normal;unicode-range:U+0100-02BA}
  body{margin:0;background:#101018;color:#F3F3F7;font-family:"Inter",sans-serif}
  #root{position:relative;width:100%;height:100%;overflow:hidden;background:#101018}
  .clip{position:absolute;inset:0}
  .cartao{position:absolute;left:56px;right:56px;top:250px}
  .topo{font-size:26px;font-weight:600;color:#3AC2D4;letter-spacing:.08em;text-transform:uppercase}
  .rotulo{margin-top:22px;font-size:46px;font-weight:800;line-height:1.15;word-break:break-word}
  .detalhe{margin-top:18px;font-size:26px;font-weight:600;color:rgba(243,243,247,.75);line-height:1.4}
  .onda{position:relative;margin-top:40px;height:150px;background:#1C1C2A;border:3px solid #34344A;overflow:hidden}
  .onda img{position:absolute;inset:0;width:100%;height:100%}
  .cursor{position:absolute;left:0;top:0;bottom:0;width:100%;background:rgba(255,203,82,.28);transform-origin:0 50%}
  .texto{margin-top:34px;font-size:28px;font-weight:600;line-height:1.45;color:#FFCB52}
  .contagem{position:absolute;left:56px;bottom:260px;font-size:24px;font-weight:600;color:rgba(243,243,247,.5)}
"""


def esc(texto):
    return html.escape(str(texto or ""), quote=True)


def onda_png(wav, destino):
    r = c.ffmpeg(["-y", "-i", str(wav), "-filter_complex", "apad=whole_dur=0.3,showwavespic=s=1216x300:colors=#FFCB52:scale=sqrt", "-frames:v", "1", str(destino)])
    if r.returncode != 0 or not destino.is_file():
        c.falhar(f"nao consegui desenhar a onda de {wav}: {r.stderr[-300:]}")


def itens_da_biblioteca():
    manifesto = c.ler_json(c.SFX_MANIFESTO)
    itens = []
    for it in manifesto["itens"]:
        dur = f"{it['duracao']:.2f}".replace(".", ",")
        itens.append({
            "topo": it["categoria"],
            "rotulo": Path(it["arquivo"]).name,
            "detalhe": f"{dur} s · {it['uso']}",
            "arquivo": str(c.SFX_DIR / it["arquivo"]),
        })
    return "Catálogo de efeitos", itens


def montar(titulo, itens, pasta):
    if pasta.exists():
        for sub in ("assets",):
            shutil.rmtree(pasta / sub, ignore_errors=True)
    (pasta / "assets" / "audio").mkdir(parents=True, exist_ok=True)
    secoes, audios, tweens = [], [], []
    t = 0.0
    for n, it in enumerate(itens, 1):
        arquivo = Path(it["arquivo"]) if it.get("arquivo") else None
        if arquivo is not None:
            if not arquivo.is_file():
                c.falhar(f"arquivo de audio nao existe: {arquivo}")
            dur_audio = c.duracao(arquivo)
            nome = f"{n:02d}-{arquivo.stem}{arquivo.suffix.lower()}"
            shutil.copyfile(arquivo, pasta / "assets" / "audio" / nome)
            onda = f"assets/audio/{n:02d}-onda.png"
            onda_png(arquivo, pasta / onda)
            dur = round(max(MINIMO, ENTRADA + dur_audio + SOBRA), 3)
            audios.append(f'  <audio id="a-{n:02d}" src="assets/audio/{nome}" data-start="{round(t + ENTRADA, 3)}" '
                          f'data-duration="{round(dur_audio, 3)}" data-track-index="{10 + n % 2}" data-volume="{it.get("volume", 1.0)}"></audio>')
            tweens.append(f'  tl.fromTo("#cur-{n:02d}", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {round(dur_audio, 3)}, ease: "none" }}, {round(t + ENTRADA, 3)});')
            bloco_onda = f'<div class="onda"><img src="{onda}" alt=""><div class="cursor" id="cur-{n:02d}"></div></div>'
        else:
            dur = SEM_AUDIO
            bloco_onda = ""
        texto = f'<div class="texto">{esc(it["texto"])}</div>' if it.get("texto") else ""
        secoes.append(
            f'  <section id="c-{n:02d}" class="clip" data-start="{round(t, 3)}" data-duration="{dur}" data-track-index="1">\n'
            f'    <div class="cartao"><div class="topo">{esc(it.get("topo"))}</div><div class="rotulo">{esc(it["rotulo"])}</div>'
            f'<div class="detalhe">{esc(it.get("detalhe"))}</div>{bloco_onda}{texto}</div>\n'
            f'    <div class="contagem">{esc(titulo)} · {n} de {len(itens)}</div>\n'
            f'  </section>'
        )
        t = round(t + dur, 3)
    total = round(t, 3)
    pagina = (
        '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n'
        f"<title>{esc(titulo)}</title>\n"
        '<script src="_motor/gsap.min.js"></script>\n'
        f"<style>{ESTILO}</style>\n</head>\n<body>\n"
        f'<div id="root" data-composition-id="audicao" data-start="0" data-width="{LARGURA}" data-height="{ALTURA}" data-duration="{total}">\n'
        + "\n".join(audios) + "\n" + "\n".join(secoes) + "\n</div>\n<script>\n  const tl = gsap.timeline({ paused: true });\n"
        + "\n".join(tweens) + '\n  window.__timelines["audicao"] = tl;\n</script>\n</body>\n</html>\n'
    )
    (pasta / "index.html").write_text(pagina, encoding="utf-8", newline="\n")
    return total


def renderizar(pasta, saida):
    cmd = [sys.executable, str(c.VIDEO_DIR / "render.py"), str(pasta), str(saida)]
    r = subprocess.run(cmd, cwd=str(c.REPO_DIR))
    if r.returncode != 0:
        c.falhar("o render do video de audicao falhou (veja a saida acima)")


def main():
    p = argparse.ArgumentParser(description="Video de audicao: cada som toca em sequencia com nome e categoria na tela, renderizado pelo motor de video local.")
    p.add_argument("--lista", help="JSON com {\"titulo\": ..., \"itens\": [{\"topo\", \"rotulo\", \"detalhe\", \"arquivo\", \"texto\"}]}; sem isso, usa a biblioteca de efeitos")
    p.add_argument("--pasta", help=f"pasta da composicao gerada (padrao: {c.rel(PASTA_PADRAO)})")
    p.add_argument("--saida", help=f"video .mp4 (padrao: {c.rel(SAIDA_PADRAO)})")
    p.add_argument("--so-montar", action="store_true", help="gera a composicao sem renderizar")
    a = p.parse_args()
    c.exigir_ffmpeg()
    if a.lista:
        dados = c.ler_json(a.lista)
        base = Path(a.lista).resolve().parent
        titulo, itens = dados["titulo"], dados["itens"]
        for it in itens:
            if it.get("arquivo"):
                it["arquivo"] = str((base / it["arquivo"]).resolve())
    else:
        titulo, itens = itens_da_biblioteca()
    pasta = Path(a.pasta).resolve() if a.pasta else PASTA_PADRAO
    saida = Path(a.saida).resolve() if a.saida else SAIDA_PADRAO
    total = montar(titulo, itens, pasta)
    c.linha("OK", f"composicao de audicao com {len(itens)} item(ns), {total:.1f} s", c.rel(pasta / "index.html"))
    if not a.so_montar:
        renderizar(pasta, saida)


if __name__ == "__main__":
    main()
