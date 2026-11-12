import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c

SAFE_TOP = 0.115
SAFE_BOTTOM = 0.22
SAFE_LEFT = 0.055
SAFE_RIGHT = 0.13


def tempos_padrao(duracao, n):
    if n <= 1:
        return [0.0]
    ultimo = max(0.0, duracao - 0.05)
    return [round(ultimo * i / (n - 1), 2) for i in range(n)]


def extrair(video, t, destino, guias):
    filtros = []
    if guias:
        filtros = [
            f"drawbox=x=0:y=0:w=iw:h=ih*{SAFE_TOP}:color=red@0.28:t=fill",
            f"drawbox=x=0:y=ih*(1-{SAFE_BOTTOM}):w=iw:h=ih*{SAFE_BOTTOM}:color=red@0.28:t=fill",
            f"drawbox=x=0:y=0:w=iw*{SAFE_LEFT}:h=ih:color=red@0.18:t=fill",
            f"drawbox=x=iw*(1-{SAFE_RIGHT}):y=0:w=iw*{SAFE_RIGHT}:h=ih:color=red@0.18:t=fill",
        ]
    cmd = [str(c.ffmpeg_path()), "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1"]
    if filtros:
        cmd += ["-vf", ",".join(filtros)]
    cmd += ["-update", "1", str(destino)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not destino.is_file():
        c.falhar(f"falha ao extrair o frame em {t}s: {r.stderr.strip()}")


def main():
    p = argparse.ArgumentParser(description="Extrai frames PNG de um video para revisao, com o FFmpeg local.")
    p.add_argument("video")
    p.add_argument("pasta_saida")
    p.add_argument("--at", help="segundos separados por virgula, ex.: 0,1.5,3")
    p.add_argument("--n", type=int, default=8, help="quantidade de frames espalhados (quando nao usar --at)")
    p.add_argument("--guias", action="store_true", help="tambem salva uma copia com as faixas de interface do Reels pintadas")
    a = p.parse_args()

    video = Path(a.video).resolve()
    if not video.is_file():
        c.falhar(f"video nao encontrado: {video}")
    if not c.ffmpeg_path().is_file():
        c.falhar("FFmpeg local ausente. Rode python content-engine/video/setup.py")
    info = c.resumo_video(video)
    dur = info["duracao"]
    if a.at:
        tempos = [float(x) for x in a.at.split(",") if x.strip()]
    else:
        tempos = tempos_padrao(dur, a.n)
    tempos = [min(max(0.0, t), max(0.0, dur - 0.05)) for t in tempos]
    pasta = Path(a.pasta_saida).resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    print(f"{video.name}: {info['largura']}x{info['altura']}, {dur}s, {info['fps']} fps, {info['codec']}")
    for i, t in enumerate(tempos, 1):
        nome = f"frame-{i:02d}-{t:06.2f}s"
        destino = pasta / f"{nome}.png"
        extrair(video, t, destino, False)
        print(f"  {destino}")
        if a.guias:
            dg = pasta / f"{nome}-guias.png"
            extrair(video, t, dg, True)
            print(f"  {dg}")
    print(f"{len(tempos)} frame(s) em {pasta}. Abra cada PNG: texto legivel, nada cortado, nada importante nas faixas vermelhas (--guias).")


if __name__ == "__main__":
    main()
