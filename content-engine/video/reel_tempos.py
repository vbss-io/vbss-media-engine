import math
import re
import unicodedata

ATRASO_GANCHO = 0.15
ATRASO_FALA = 0.25
RESPIRO = 0.3
CAUDA_FECHO = 2.6
TEXTO_MINIMO = 1.0
AJUSTE_MAXIMO = 0.5
TOLERANCIA_GRADE = 0.03
INTERVALO_MINIMO = 0.09

EFEITOS = {
    "titulo": ("impact/impacto-cine-medio", 0.7, 1.0),
    "linha": ("impact/impacto-cine-macio", 0.6, 0.9),
    "apoio": ("pop/pop-cine-redondo", 0.4, 0.7),
    "assenta": ("whoosh/whoosh-cine-medio", 0.5, 0.8),
    "troca": ("transition/transicao-cine", 0.6, 0.9),
    "troca_leve": ("transition/transicao-cine-suave", 0.6, 0.9),
    "virada": ("transition/transicao-cine-forte", 0.65, 0.9),
    "selo": ("pop/pop-cine-grave", 0.5, 0.8),
    "camera": ("whoosh/whoosh-cine-longo", 0.4, 0.7),
    "camera_curta": ("whoosh/whoosh-cine-curto", 0.4, 0.7),
    "foco": ("tick/tique-cine-macio", 0.8, 1.0),
    "marca": ("tick/tique-cine-ficha", 0.8, 1.0),
    "toque": ("click/clique-cine-toque", 0.8, 1.0),
    "digita": ("typing/digitacao-cine-suave", 0.6, 0.8),
    "confirma": ("success/sucesso-cine-discreto", 0.5, 0.8),
    "chip": ("pop/pop-cine-redondo", 0.45, 0.7),
    "rola": ("transition/swish-cine-leve", 0.5, 0.8),
    "rola_longa": ("whoosh/whoosh-cine-longo", 0.5, 0.8),
    "midia": ("whoosh/whoosh-cine-curto", 0.45, 0.7),
    "revela": ("whoosh/whoosh-cine-medio", 0.5, 0.8),
    "resultado": ("shine/brilho-cine-curto", 0.5, 0.8),
    "sobe_logo": ("riser/reverso-cine-longo", 0.5, 0.7),
    "logo": ("impact/impacto-cine-medio", 0.75, 1.0),
    "brilho_logo": ("shine/brilho-cine-longo", 0.45, 0.7),
}


class ErroDeRoteiro(ValueError):
    pass


def normalizar(texto):
    sem_acento = "".join(ch for ch in unicodedata.normalize("NFD", str(texto).lower()) if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in sem_acento if ch.isalnum())


def para_a_voz(fala, pronuncia):
    texto = str(fala).replace("*", "")
    for escrita in sorted(pronuncia or {}, key=len, reverse=True):
        texto = re.sub(r"(?<!\w)" + re.escape(escrita) + r"(?!\w)", lambda _: str(pronuncia[escrita]), texto)
    return texto


def separar_por_fala(legenda):
    planas = [p for b in legenda.get("blocos", []) for p in b["palavras"]]
    saida = []
    cursor = 0
    for fala in legenda.get("falas", []):
        n = int(fala["palavras"])
        saida.append(planas[cursor:cursor + n])
        cursor += n
    return saida


def achar(palavras, expressao, vez=1):
    alvo = [normalizar(x) for x in str(expressao).split() if normalizar(x)]
    if not alvo:
        raise ErroDeRoteiro("momento sem palavra: preencha 'na' com uma palavra da fala")
    chaves = []
    for p in palavras:
        chaves.append([normalizar(x) for x in p["texto"].split() if normalizar(x)][:1] or [""])
    planas = [k[0] for k in chaves]
    achadas = [i for i in range(len(planas) - len(alvo) + 1) if planas[i:i + len(alvo)] == alvo]
    if len(achadas) < vez:
        fala = " ".join(p["texto"] for p in palavras)
        quantas = f"so aparece {len(achadas)} vez(es)" if achadas else "nao aparece"
        raise ErroDeRoteiro(f"\"{expressao}\" {quantas} na fala \"{fala}\"")
    return achadas[vez - 1]


def momento(palavras, ref):
    if not palavras:
        raise ErroDeRoteiro("batida sem fala nao aceita momento amarrado a palavra")
    if isinstance(ref, str):
        ref = {"na": ref}
    na = ref.get("na", "@inicio")
    ajuste = float(ref.get("ajuste", 0))
    if abs(ajuste) > AJUSTE_MAXIMO:
        raise ErroDeRoteiro(f"'ajuste' de {ajuste} s em \"{na}\": o limite e {AJUSTE_MAXIMO} s para cada lado (amarre a outra palavra)")
    if na == "@inicio":
        t = palavras[0]["inicio"]
    elif na == "@fim":
        t = palavras[-1]["fim"]
    else:
        i = achar(palavras, na, int(ref.get("vez", 1)))
        if ref.get("ponto") == "fim":
            t = palavras[i + len([x for x in na.split() if normalizar(x)]) - 1]["fim"]
        else:
            t = palavras[i]["inicio"]
    return round(max(0.0, t + ajuste), 3)


def grade(bpm):
    return 60.0 / float(bpm)


def encaixar(t, bpm, tolerancia=TOLERANCIA_GRADE):
    if not bpm:
        return round(t, 3)
    passo = grade(bpm)
    return round(math.ceil((t - tolerancia) / passo) * passo, 3)


def planejar(duracoes, bpm=None, minimos=None, cauda=CAUDA_FECHO, respiro=RESPIRO):
    batidas = []
    inicio = 0.0
    for i, dur in enumerate(duracoes):
        atraso = ATRASO_GANCHO if i == 0 else ATRASO_FALA
        fala = round(inicio + atraso, 2)
        fim_fala = round(fala + dur, 3)
        ultima = i == len(duracoes) - 1
        fim = fim_fala + (cauda if ultima else respiro)
        if minimos and minimos[i]:
            fim = max(fim, inicio + float(minimos[i]))
        fim = encaixar(fim, bpm)
        batidas.append({"inicio": round(inicio, 3), "fala": fala, "fim_fala": fim_fala, "fim": fim})
        inicio = fim
    return batidas


def ancorar(instante, ancora):
    return round(max(0.0, instante - float(ancora or 0)), 3)


def deixa(movimento, instante, ancoras, com_voz=True, duracao=None, volume=None):
    if movimento not in EFEITOS:
        raise ErroDeRoteiro(f"movimento sem efeito definido: {movimento}")
    efeito, vol_voz, vol_cheio = EFEITOS[movimento]
    d = {"t": ancorar(instante, ancoras.get(efeito, 0)), "efeito": efeito, "volume": volume if volume is not None else (vol_voz if com_voz else vol_cheio)}
    if duracao is not None:
        d["duracao"] = round(duracao, 3)
    return d


def enxugar(deixas, intervalo=INTERVALO_MINIMO):
    saida = []
    ultimo = {}
    for d in sorted(deixas, key=lambda x: (x["t"], x.get("efeito", x.get("arquivo", "")))):
        chave = d.get("efeito")
        if chave and chave in ultimo and d["t"] - ultimo[chave] < intervalo:
            continue
        if chave:
            ultimo[chave] = d["t"]
        saida.append(d)
    return saida


def segurar_texto(t, primeira_batida):
    return round(max(t, TEXTO_MINIMO), 3) if primeira_batida else round(t, 3)
