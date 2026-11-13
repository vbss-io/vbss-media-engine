import argparse
import json
import sys
import zlib
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True

TAXA = 48000
SEMENTE = 20261112
TETO_AMOSTRA_DB = -1.5
SATURACAO_MAX_DB = 4.0
JANELA_NIVEL = 0.1
FAIXAS_HZ = (0, 100, 500, 2000, 8000, 24000)
K_PRE_B = (1.53512485958697, -2.69169618940638, 1.19839281085285)
K_PRE_A = (1.0, -1.69065929318241, 0.73248077421585)
K_RLB_B = (1.0, -2.0, 1.0)
K_RLB_A = (1.0, -1.99004745483398, 0.99007225036621)
ESCALA_BRILHO = (1.0, 1.125, 1.25, 1.5, 5 / 3, 2.0, 2.25, 2.5, 3.0, 10 / 3, 4.0, 4.5, 5.0, 6.0)

ALVOS = {}
CAMADAS = {}
PRONTOS = {}


def amostras(segundos):
    return int(round(segundos * TAXA))


def eixo(n):
    return np.arange(n) / TAXA


def ganho(decibeis):
    return 10 ** (decibeis / 20)


def fase(freq):
    return 2 * np.pi * np.cumsum(freq) / TAXA


def unitario(x):
    return x / np.sqrt(np.mean(x * x) + 1e-20)


def gerador(nome):
    return np.random.default_rng([SEMENTE, zlib.crc32(nome.encode("utf-8"))])


def filtrar(x, grave=None, agudo=None, secoes=1):
    n = len(x)
    m = n + TAXA // 2
    f = np.fft.rfftfreq(m, 1 / TAXA)
    h = np.ones(len(f), dtype=complex)
    for _ in range(secoes):
        if agudo:
            s = 1j * f / agudo
            h = h / (s * s + 1.41421356 * s + 1)
        if grave:
            s = 1j * f / grave
            h = h * (s * s) / (s * s + 1.41421356 * s + 1)
    return np.fft.irfft(np.fft.rfft(x, m) * h, m)[:n]


def varrer(x, centro, oitavas, quadro=1024, salto=128):
    n = len(x)
    janela = np.hanning(quadro + 1)[:-1]
    xp = np.concatenate((np.zeros(quadro), x, np.zeros(2 * quadro)))
    quadros = 1 + (len(xp) - quadro) // salto
    idx = np.arange(quadro)[None, :] + salto * np.arange(quadros)[:, None]
    espectro = np.fft.rfft(xp[idx] * janela, axis=1)
    f = np.fft.rfftfreq(quadro, 1 / TAXA)
    f[0] = f[1] / 4
    meio = (np.arange(quadros) * salto + quadro / 2 - quadro) / TAXA
    fc = np.interp(meio, eixo(n), centro)
    distancia = np.log2(f[None, :] / fc[:, None]) / (oitavas / 2)
    mascara = 1 / (1 + distancia * distancia)
    partes = np.fft.irfft(espectro * mascara, quadro, axis=1) * janela
    saida = np.zeros(len(xp))
    np.add.at(saida, idx, partes)
    return saida[quadro:quadro + n] / (0.375 * quadro / salto)


def sopro(n, pico, subida, queda):
    t = eixo(n)
    sobe = np.sin(0.5 * np.pi * np.clip(t / pico, 0, 1)) ** (2 * subida)
    desce = np.exp(-np.clip(t - pico, 0, None) / queda)
    return sobe * desce


def pente(x, atraso_ms, mistura):
    n = len(x)
    pos = np.arange(n) - atraso_ms * TAXA / 1000
    return x + mistura * np.interp(pos, np.arange(n), x, left=0.0)


def pontas(x, entrada, saida):
    x = x.copy()
    a = min(amostras(entrada), len(x) // 2)
    b = min(amostras(saida), len(x) // 2)
    if a:
        x[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    if b:
        x[-b:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(b) / b)
    return x


def sala(rng, x, rt, molhado, brilho=7000, grave=150, pre=0.008, seco=1.0):
    n = amostras(rt * 1.3)
    t = eixo(n)
    bruto = rng.standard_normal(n)
    baixo = filtrar(bruto, agudo=brilho * 0.25)
    alto = filtrar(bruto - baixo, agudo=brilho)
    resposta = baixo * 10 ** (-3 * t / rt) + alto * 10 ** (-3 * t / (rt * 0.55))
    resposta = filtrar(resposta * (1 - np.exp(-t / 0.004)), grave=grave)
    resposta = pontas(resposta, 0, rt * 0.2)
    resposta /= np.sqrt(np.sum(resposta * resposta))
    total = len(x) + n + amostras(pre)
    m = len(x) + n
    eco = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(resposta, m), m)
    saida = np.zeros(total)
    saida[:len(x)] += seco * x
    saida[amostras(pre):] += molhado * eco
    return saida


def somar(partes):
    fim = max(amostras(inicio) + len(x) for x, inicio, _ in partes)
    saida = np.zeros(fim)
    for x, inicio, db in partes:
        i = amostras(inicio)
        saida[i:i + len(x)] += x * ganho(db)
    return saida


def aparar(x, limiar_db=-45.0):
    acima = np.nonzero(np.abs(x) > np.abs(x).max() * ganho(limiar_db))[0]
    return x[acima[0]:acima[-1] + 1]


def resposta_biquad(b, a, f):
    z = np.exp(-2j * np.pi * f / TAXA)
    return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)


def nivel(x):
    m = len(x) + TAXA
    f = np.fft.rfftfreq(m, 1 / TAXA)
    h = resposta_biquad(K_PRE_B, K_PRE_A, f) * resposta_biquad(K_RLB_B, K_RLB_A, f)
    y = np.fft.irfft(np.fft.rfft(x, m) * h, m)
    janela = amostras(JANELA_NIVEL)
    soma = np.cumsum(np.concatenate(([0.0], y * y)))
    media = (soma[janela:] - soma[:-janela]) / janela
    return -0.691 + 10 * np.log10(max(float(media.max()), 1e-12))


def faixas(x):
    energia = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / TAXA)
    total = energia.sum() + 1e-20
    return [round(float(100 * energia[(f >= a) & (f < b)].sum() / total), 1) for a, b in zip(FAIXAS_HZ, FAIXAS_HZ[1:])]


def saturar(x, teto):
    joelho = 0.5 * teto
    modulo = np.abs(x)
    curva = joelho + (teto - joelho) * np.tanh((modulo - joelho) / (teto - joelho))
    return np.sign(x) * np.where(modulo <= joelho, modulo, curva)


def finalizar(x, alvo, saida=0.03, entrada=0.002):
    x = filtrar(x, grave=28)
    acima = np.nonzero(np.abs(x) > np.abs(x).max() * ganho(-60))[0]
    x = x[:min(len(x), acima[-1] + amostras(saida))]
    x = pontas(x, entrada, saida)
    db = alvo - nivel(x)
    sobra = 20 * np.log10(np.abs(x).max()) + db - TETO_AMOSTRA_DB
    if sobra <= 0:
        return x * ganho(db)
    return saturar(x * ganho(db - max(0.0, sobra - SATURACAO_MAX_DB)), ganho(TETO_AMOSTRA_DB))


def pronto(nome):
    if nome not in PRONTOS:
        if nome not in RECEITAS:
            raise SystemExit(f"receita desconhecida: {nome}")
        if nome not in ALVOS:
            raise SystemExit(f"receita {nome} sem alvo_db no pedido")
        x, ancora, saida = RECEITAS[nome](gerador(nome), CAMADAS.get(nome, []))
        PRONTOS[nome] = (finalizar(x, ALVOS[nome], saida), ancora)
    return PRONTOS[nome]


def whoosh(rng, pico, queda, faixa, largura=2.4, subida=1.6, corpo=0.5, ar=0.25, rt=0.35, molhado=0.16):
    n = amostras(pico + 5 * queda)
    t = eixo(n)
    env = sopro(n, pico, subida, queda)
    f_ini, f_topo, f_fim = faixa
    sobe = np.clip(t / pico, 0, 1) ** 1.4
    desce = 1 - np.exp(-np.clip(t - pico, 0, None) / (1.6 * queda))
    centro = np.where(t < pico, f_ini * (f_topo / f_ini) ** sobe, f_topo * (f_fim / f_topo) ** desce)
    turbulencia = filtrar(rng.standard_normal(n), agudo=14)
    turbulencia = 1 + 0.22 * turbulencia / np.abs(turbulencia).max()
    principal = unitario(varrer(rng.standard_normal(n), centro, largura))
    baixo = unitario(varrer(rng.standard_normal(n), np.maximum(centro * 0.22, 70), 1.8))
    aereo = unitario(filtrar(rng.standard_normal(n), grave=5500, agudo=15000))
    mix = (principal * env + corpo * baixo * env ** 0.8 + ar * aereo * env ** 2) * turbulencia
    mix = pente(mix, 3.0 - 2.6 * env, 0.55)
    return sala(rng, mix, rt, molhado), pico, 0.04


def whoosh_corpo(rng, camadas):
    base = aparar(camadas[0])
    base = filtrar(base, grave=70, agudo=9000)
    pico = float(np.argmax(np.abs(filtrar(np.abs(base), agudo=30))) / TAXA)
    aereo, _, _ = whoosh(rng, pico, 0.07, (900, 4200, 1300), corpo=0.0, ar=0.4, molhado=0.0)
    mix = somar([(base / np.abs(base).max(), 0.0, 0.0), (aereo / np.abs(aereo).max(), 0.0, -9.0)])
    return sala(rng, mix, 0.5, 0.2), pico, 0.04


def swish_papel(rng, camadas):
    base = aparar(camadas[0], -40.0)
    base = filtrar(base, grave=350, agudo=10000)
    pico = float(np.argmax(np.abs(filtrar(np.abs(base), agudo=30))) / TAXA)
    return sala(rng, base, 0.3, 0.16), pico, 0.03


def impacto(rng, sub, tau, pancada, estalo, corpo, rt, molhado, saturacao, dur, camada=None, camada_db=-6.0):
    n = amostras(dur)
    t = eixo(n)
    subida = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.004, 0, 1))
    freq = sub[1] + (sub[0] - sub[1]) * np.exp(-t / 0.07)
    grave = np.sin(fase(freq)) * np.exp(-t / tau) * subida
    batida = np.sin(fase(90 + 150 * np.exp(-t / 0.03))) * np.exp(-t / 0.07) * pancada * subida
    f_grave, f_agudo, tau_estalo, nivel_estalo = estalo
    estalado = unitario(filtrar(rng.standard_normal(n), grave=f_grave, agudo=f_agudo)) * np.exp(-t / tau_estalo) * nivel_estalo
    massa = unitario(filtrar(rng.standard_normal(n), grave=70, agudo=500)) * np.exp(-t / 0.08) * corpo
    seco = grave + batida + estalado + massa
    seco = np.tanh(saturacao * seco) / np.tanh(saturacao)
    if camada is not None:
        extra = aparar(camada)[:n]
        extra = pontas(extra, 0.001, 0.5) / np.abs(extra).max()
        seco = somar([(seco, 0.0, 0.0), (extra * np.abs(seco).max(), 0.0, camada_db)])
    return sala(rng, seco, rt, molhado, brilho=3500, grave=60, pre=0.012), 0.0, 0.08


def braam(rng):
    n = amostras(1.5)
    t = eixo(n)
    env = np.clip(t / 0.06, 0, 1) ** 1.5 * np.exp(-np.clip(t - 0.5, 0, None) / 0.3)
    corte = 400 + 2200 * np.sin(np.pi * np.clip(t / 1.1, 0, 1)) ** 2
    tom = np.zeros(n)
    for base, peso in ((55.0, 1.0), (110.0, 0.5)):
        for desvio in (-0.005, 0.0, 0.0046):
            f = base * (1 + desvio)
            for k in range(1, 33):
                tom += peso * np.sin(2 * np.pi * f * k * t + rng.uniform(0, 2 * np.pi)) / k / np.sqrt(1 + (f * k / corte) ** 4)
    tom = unitario(tom) * 0.5 + 0.3 * np.sin(2 * np.pi * 55.0 * t)
    seco = np.tanh(2.2 * tom * env) / np.tanh(2.2)
    return sala(rng, seco, 1.3, 0.3, brilho=4500, grave=80, pre=0.015), 0.0, 0.1


def riser(rng, dur, faixa=(200, 3200), tom=(110, 440)):
    n = amostras(dur)
    u = eixo(n) / dur
    env = (np.exp(4.2 * u) - 1) / (np.exp(4.2) - 1)
    centro = faixa[0] * (faixa[1] / faixa[0]) ** (u ** 1.2)
    vento = unitario(varrer(rng.standard_normal(n), centro, 2.2))
    giro = fase(tom[0] * (tom[1] / tom[0]) ** (u ** 1.6))
    tonal = np.zeros(n)
    for desvio in (-0.006, 0.0, 0.007):
        for k in range(1, 6):
            tonal += np.sin(k * giro * (1 + desvio)) / k
    tremor = 0.65 + 0.35 * np.sin(fase(5 + 13 * u ** 2))
    aereo = unitario(filtrar(rng.standard_normal(n), grave=6000, agudo=15000)) * u ** 3
    mix = (vento + 0.6 * unitario(tonal) * tremor + 0.2 * aereo) * env
    return sala(rng, mix, 0.45, 0.2)[:n + amostras(0.045)], dur, 0.04


def reverso(rng, dur):
    n = amostras(0.5)
    t = eixo(n)
    golpe = unitario(filtrar(rng.standard_normal(n), grave=500, agudo=9000)) * np.exp(-t / 0.02)
    for f in (587.33, 880.0, 1174.66, 1760.0):
        golpe += 0.25 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.12)
    cauda = sala(rng, golpe, dur * 1.6, 1.0, brilho=9000, pre=0.0, seco=0.0)[:amostras(dur)]
    cauda = pontas(cauda, 0, dur * 0.35)
    return np.concatenate((cauda[::-1], np.zeros(amostras(0.015)))), dur, 0.012


def brilho(rng, dur, espalha, taus, partes, rt, base=2093.0, sobe=False):
    n = amostras(dur)
    t = eixo(n)
    x = np.zeros(n)
    for i in range(partes):
        if sobe:
            razao = ESCALA_BRILHO[i % len(ESCALA_BRILHO)]
            inicio = espalha * i / (partes - 1)
            amp = (0.5 + 0.5 * i / (partes - 1)) / razao ** 0.5
        else:
            razao = ESCALA_BRILHO[int(rng.integers(len(ESCALA_BRILHO)))]
            inicio = espalha * rng.uniform(0, 1) ** 1.5
            amp = rng.uniform(0.55, 1.0) / razao ** 0.4
        f = base * razao * (1 + rng.uniform(-0.002, 0.002))
        tau = rng.uniform(*taus) / razao ** 0.35
        tl = np.clip(t - inicio, 0, None)
        env = (1 - np.exp(-tl / 0.003)) * np.exp(-tl / tau) * (t >= inicio)
        tremor = 1 + 0.3 * np.sin(2 * np.pi * rng.uniform(4, 9) * t + rng.uniform(0, 2 * np.pi))
        x += amp * env * tremor * (np.sin(2 * np.pi * f * tl) + 0.6 * np.sin(2 * np.pi * f * 1.003 * tl + 1.0))
    aereo = unitario(filtrar(rng.standard_normal(n), grave=7000, agudo=16000))
    x += 0.05 * np.abs(x).max() * aereo * (1 - np.exp(-t / 0.05)) * np.exp(-t / (dur / 4))
    return sala(rng, x, rt, 0.35, brilho=11000, grave=400), espalha if sobe else 0.0, 0.12


def pop(rng, tons, tau):
    n = amostras(0.4)
    t = eixo(n)
    giro = fase(tons[1] + (tons[0] - tons[1]) * np.exp(-t / (tau * 0.6)))
    corpo = (np.sin(giro) + 0.18 * np.sin(2 * giro)) * (1 - np.exp(-t / 0.0015)) * np.exp(-t / tau)
    estalo = unitario(filtrar(rng.standard_normal(n), grave=800, agudo=3500)) * np.exp(-t / 0.006) * 0.1
    return sala(rng, corpo + estalo, 0.25, 0.1), 0.0, 0.03


def clique_abafado(rng):
    n = amostras(0.15)
    t = eixo(n)
    estalo = unitario(filtrar(rng.standard_normal(n), grave=500, agudo=2600, secoes=2)) * np.exp(-t / 0.005) * 0.6
    baque = np.sin(2 * np.pi * 420 * t) * np.exp(-t / 0.008) * (1 - np.exp(-t / 0.001))
    return sala(rng, estalo + baque, 0.2, 0.08), 0.0, 0.02


def clique_toque(rng, camadas):
    base = aparar(camadas[0], -40.0)
    base = filtrar(base, grave=120, agudo=2600, secoes=2)
    return sala(rng, base, 0.22, 0.1), 0.0, 0.03


def tique_seco(rng, afinacao=1.0, dur=0.12):
    n = amostras(dur)
    t = eixo(n)
    tom = np.sin(2 * np.pi * 1700 * afinacao * t) * np.exp(-t / 0.009) + 0.5 * np.sin(2 * np.pi * 2550 * afinacao * t) * np.exp(-t / 0.006)
    estalo = unitario(filtrar(rng.standard_normal(n), grave=1500, agudo=5000)) * np.exp(-t / 0.003) * 0.12
    return (tom + estalo) * (1 - np.exp(-t / 0.0008))


def tique_macio(rng):
    return sala(rng, tique_seco(rng), 0.18, 0.08), 0.0, 0.02


def tique_ficha(rng, camadas):
    base = aparar(camadas[0], -40.0)
    base = filtrar(base, grave=400, agudo=6500)
    return sala(rng, base, 0.2, 0.1), 0.0, 0.03


def nota(n, f, tau):
    t = eixo(n)
    ataque = 1 - np.exp(-t / 0.002)
    return ataque * (
        np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
        + 0.22 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / (tau * 0.5))
        + 0.1 * np.sin(2 * np.pi * 4.01 * f * t) * np.exp(-t / (tau * 0.15))
    )


def notas(rng, sequencia, rt, molhado, dur):
    n = amostras(dur)
    partes = [(nota(n - amostras(inicio), f, tau), inicio, db) for f, inicio, tau, db in sequencia]
    return sala(rng, somar(partes), rt, molhado, brilho=9000, grave=250), 0.0, 0.1


def sucesso_acorde(rng):
    acorde = [(261.63, 0.0, 0.55, -8.0), (523.25, 0.0, 0.5, 0.0), (659.25, 0.035, 0.5, -1.0), (783.99, 0.07, 0.5, -1.0), (1174.66, 0.105, 0.45, -3.0)]
    base, _, _ = notas(rng, acorde, 1.2, 0.3, 1.2)
    cintila, _, _ = brilho(rng, 1.0, 0.25, (0.15, 0.4), 8, 1.0, base=2637.0)
    mix = somar([(base / np.abs(base).max(), 0.0, 0.0), (cintila / np.abs(cintila).max(), 0.1, -16.0)])
    return mix, 0.0, 0.15


def contador(rng, intervalos, fecho=None):
    partes = []
    momento = 0.0
    for i, passo in enumerate(intervalos):
        partes.append((tique_seco(rng, 1 + 0.03 * np.sin(1.7 * i)), momento, -3.0 * (i % 2) + 4.0 * i / len(intervalos) - 4.0))
        momento += passo
    ancora = 0.0
    if fecho:
        n = amostras(0.9)
        sino = nota(n, fecho, 0.3) + 0.5 * nota(n, fecho * 1.5, 0.25)
        partes.append((sino / np.abs(sino).max(), momento, -7.0))
        ancora = round(momento, 3)
    return sala(rng, somar(partes), 0.3, 0.12, brilho=9000, grave=250), ancora, 0.05


def digitacao_suave(rng, camadas):
    base = aparar(camadas[0], -40.0)[:amostras(1.8)]
    base = filtrar(base, grave=160, agudo=3600, secoes=2)
    base = np.tanh(3 * base / np.abs(base).max()) / np.tanh(3)
    return sala(rng, pontas(base, 0.001, 0.08), 0.3, 0.14), 0.0, 0.05


def transicao(rng, ancora, partes):
    montagem = []
    for nome, db, recuo in partes:
        x, ponto = pronto(nome)
        montagem.append((x, ancora - ponto - recuo, db))
    return somar(montagem), ancora, 0.1


RECEITAS = {
    "whoosh-cine-curto": lambda r, c: whoosh(r, 0.12, 0.05, (350, 2200, 600), corpo=0.8),
    "whoosh-cine-medio": lambda r, c: whoosh(r, 0.26, 0.09, (220, 1800, 400), corpo=0.8),
    "whoosh-cine-longo": lambda r, c: whoosh(r, 0.6, 0.14, (150, 1500, 300), corpo=0.8),
    "whoosh-cine-grave": lambda r, c: whoosh(r, 0.34, 0.1, (90, 700, 140), largura=2.0, corpo=0.9, ar=0.05),
    "whoosh-cine-agudo": lambda r, c: whoosh(r, 0.17, 0.06, (1500, 7000, 2500), corpo=0.1, ar=0.5),
    "whoosh-cine-cauda": lambda r, c: whoosh(r, 0.2, 0.07, (250, 2000, 500), corpo=0.7, rt=1.1, molhado=0.45),
    "whoosh-cine-corpo": whoosh_corpo,
    "swish-cine-leve": lambda r, c: whoosh(r, 0.08, 0.035, (2000, 6000, 3000), largura=1.6, corpo=0.0, ar=0.4, rt=0.25, molhado=0.12),
    "swish-cine-papel": swish_papel,
    "impacto-cine-macio": lambda r, c: impacto(r, (75, 42), 0.16, 0.5, (60, 900, 0.012, 0.3), 0.35, 0.5, 0.2, 1.2, 0.7),
    "impacto-cine-medio": lambda r, c: impacto(r, (90, 40), 0.26, 1.0, (800, 5000, 0.01, 0.5), 0.6, 0.8, 0.25, 1.8, 1.0),
    "impacto-cine-forte": lambda r, c: impacto(r, (100, 36), 0.42, 1.3, (600, 8000, 0.012, 0.7), 0.8, 1.2, 0.3, 2.6, 1.6, camada=c[0]),
    "impacto-cine-sub": lambda r, c: impacto(r, (70, 35), 0.6, 0.15, (60, 600, 0.01, 0.1), 0.05, 0.6, 0.12, 1.5, 1.5),
    "braam-cine-leve": lambda r, c: braam(r),
    "riser-cine-meio": lambda r, c: riser(r, 0.5, faixa=(300, 3200), tom=(165, 440)),
    "riser-cine-1s": lambda r, c: riser(r, 1.0),
    "riser-cine-2s": lambda r, c: riser(r, 2.0, faixa=(140, 3200), tom=(82.5, 440)),
    "reverso-cine-curto": lambda r, c: reverso(r, 0.5),
    "reverso-cine-longo": lambda r, c: reverso(r, 1.2),
    "tique-cine-macio": lambda r, c: tique_macio(r),
    "tique-cine-ficha": tique_ficha,
    "clique-cine-abafado": lambda r, c: clique_abafado(r),
    "clique-cine-toque": clique_toque,
    "pop-cine-redondo": lambda r, c: pop(r, (620, 300), 0.045),
    "pop-cine-grave": lambda r, c: pop(r, (300, 130), 0.07),
    "brilho-cine-curto": lambda r, c: brilho(r, 0.7, 0.08, (0.12, 0.3), 10, 0.9),
    "brilho-cine-longo": lambda r, c: brilho(r, 1.6, 0.35, (0.3, 0.8), 16, 1.5),
    "brilho-cine-sobe": lambda r, c: brilho(r, 1.1, 0.45, (0.12, 0.35), 12, 1.1, sobe=True),
    "sucesso-cine-discreto": lambda r, c: notas(r, [(783.99, 0.0, 0.22, 0.0), (1174.66, 0.11, 0.3, 0.0)], 0.7, 0.22, 0.9),
    "sucesso-cine-acorde": lambda r, c: sucesso_acorde(r),
    "contador-cine-macio": lambda r, c: contador(r, [0.06] * 20),
    "contador-cine-fecho": lambda r, c: contador(r, [0.05 + 0.09 * (i / 11) ** 2 for i in range(12)], fecho=1567.98),
    "digitacao-cine-suave": digitacao_suave,
    "notificacao-cine-limpa": lambda r, c: notas(r, [(1318.51, 0.0, 0.16, 0.0), (1046.5, 0.1, 0.2, 0.0)], 0.4, 0.15, 0.6),
    "transicao-cine": lambda r, c: transicao(r, 0.75, [("riser-cine-meio", -5.0, 0.0), ("whoosh-cine-medio", -2.0, 0.02), ("impacto-cine-macio", 0.0, 0.0)]),
    "transicao-cine-forte": lambda r, c: transicao(r, 1.2, [("reverso-cine-longo", -6.0, 0.0), ("riser-cine-1s", -5.0, 0.0), ("whoosh-cine-longo", -3.0, 0.02), ("impacto-cine-medio", 0.0, 0.0), ("brilho-cine-curto", -8.0, 0.0)]),
    "transicao-cine-suave": lambda r, c: transicao(r, 0.26, [("whoosh-cine-medio", 0.0, 0.0), ("pop-cine-grave", -3.0, 0.0)]),
}


def main():
    p = argparse.ArgumentParser(description="Sintese propria dos efeitos do conjunto cine (deterministica, semente fixa). Chamado pelo sfx_setup.py com um pedido em JSON.")
    p.add_argument("pedido", help="JSON com {\"alvos\": {receita: dB}, \"itens\": [{\"nome\", \"receita\", \"camadas\", \"saida\"}], \"resultado\": caminho}")
    a = p.parse_args()
    pedido = json.loads(Path(a.pedido).read_text(encoding="utf-8"))
    ALVOS.update(pedido["alvos"])
    for item in pedido["itens"]:
        CAMADAS[item["receita"]] = [np.fromfile(c, dtype="<f4").astype(np.float64) for c in item.get("camadas", [])]
    resultado = {}
    for item in pedido["itens"]:
        x, ancora = pronto(item["receita"])
        x.astype("<f4").tofile(item["saida"])
        resultado[item["nome"]] = {
            "ancora": round(float(ancora), 3),
            "nivel_db": round(nivel(x), 1),
            "faixas_pct": faixas(x),
            "semente": SEMENTE,
        }
        print(f"[OK] sintese {item['nome']} - {len(x) / TAXA:.2f}s  ancora {ancora:.2f}s  nivel {nivel(x):.1f} dB", flush=True)
    Path(pedido["resultado"]).write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
