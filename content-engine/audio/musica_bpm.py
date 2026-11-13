import json
import sys

import numpy as np

TAXA = 11025
JANELA = 1024
PASSO = 128
BPM_MIN = 60.0
BPM_MAX = 180.0
BPM_CENTRO = 110.0
LARGURA_OITAVAS = 0.9
FRACAO_DO_MELHOR = 0.85
TOLERANCIA_BATIDAS = 0.5


def envelope_de_onsets(x):
    quadros = (len(x) - JANELA) // PASSO
    if quadros < 8:
        return None
    idx = np.arange(JANELA)[None, :] + PASSO * np.arange(quadros)[:, None]
    espectro = np.log1p(100 * np.abs(np.fft.rfft(x[idx] * np.hanning(JANELA), axis=1)))
    fluxo = np.maximum(espectro[1:] - espectro[:-1], 0).sum(axis=1)
    return fluxo - fluxo.mean()


def candidatos(env):
    qps = TAXA / PASSO
    auto = np.correlate(env, env, "full")[len(env) - 1:]
    eixo = np.arange(len(auto))
    lista = []
    for bpm in np.arange(BPM_MIN, BPM_MAX + 0.01, 0.5):
        atraso = 60 * qps / bpm
        forca = sum(float(np.interp(atraso * k, eixo, auto)) for k in (1, 2, 4)) / 3
        peso = float(np.exp(-0.5 * (np.log2(bpm / BPM_CENTRO) / LARGURA_OITAVAS) ** 2))
        lista.append((forca * peso, float(bpm)))
    return sorted(lista, reverse=True)


def medir(x, laco):
    env = envelope_de_onsets(x)
    if env is None or not np.any(env):
        return None
    lista = candidatos(env)
    melhor = lista[0]
    if melhor[0] <= 0:
        return None
    if laco:
        duracao = len(x) / TAXA
        for forca, bpm in lista:
            if forca < FRACAO_DO_MELHOR * melhor[0]:
                break
            batidas = duracao * bpm / 60
            compassos = round(batidas / 4) * 4
            if compassos and abs(batidas - compassos) <= TOLERANCIA_BATIDAS:
                return round(compassos * 60 / duracao, 1)
    return melhor[1]


def main():
    laco = "--laco" in sys.argv[1:]
    x = np.frombuffer(sys.stdin.buffer.read(), dtype="<f4")
    print(json.dumps({"bpm": medir(x, laco)}))


if __name__ == "__main__":
    main()
