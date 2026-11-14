import argparse
import array
import difflib
import math
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c

TAXA = 32000
QUADRO = 320
LIMIAR_CHIADO_DB = -6.0
PISO_CHIADO_DB = -38.0
MINIMO_QUADROS = 6
EMENDA_QUADROS = 1
BEIRA_DA_PALAVRA = 0.12
SEMELHANCA_NOME = 0.6
UNIDADES = ["zero", "um", "dois", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze", "treze", "quatorze",
            "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
DEZENAS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
CENTENAS = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]
EQUIVALENTES = [{"pra", "para"}, {"pro", "parao"}, {"ta", "esta"}, {"to", "estou"}, {"catorze", "quatorze"}, {"uma", "um"}, {"duas", "dois"}]
CHIADO_RE = re.compile(r"ss|sc(?=[ei])|xc(?=[ei])|ch|ç|c(?=[ei])|s|z|x|j|g(?=[ei])|[td](?=i)|[td](?=es?$)")
SOPRO_RE = re.compile(r"ff|f|v")


def sem_acento(texto):
    return "".join(ch for ch in unicodedata.normalize("NFD", texto) if unicodedata.category(ch) != "Mn")


def normalizar(texto):
    return "".join(ch for ch in sem_acento(texto.lower()) if ch.isalnum())


def por_extenso(n):
    if n < 20:
        return UNIDADES[n]
    if n < 100:
        return DEZENAS[n // 10] + ("e" + UNIDADES[n % 10] if n % 10 else "")
    if n == 100:
        return "cem"
    if n < 1000:
        return CENTENAS[n // 100] + ("e" + por_extenso(n % 100) if n % 100 else "")
    if n < 1000000:
        milhar = "mil" if n // 1000 == 1 else por_extenso(n // 1000) + "mil"
        resto = n % 1000
        if not resto:
            return milhar
        liga = "e" if resto < 100 or resto % 100 == 0 else ""
        return milhar + liga + por_extenso(resto)
    return str(n)


def chave(palavra):
    base = normalizar(palavra)
    if base.isdigit() and len(base) <= 6:
        base = por_extenso(int(base))
    for grupo in EQUIVALENTES:
        if base in grupo:
            return sorted(grupo)[0]
    return base


def nome_proprio(palavra, primeira):
    limpa = palavra.strip("\"'“”‘’([{«*")
    if not limpa or not limpa[0].isalpha():
        return False
    if any(ch.isupper() for ch in limpa[1:]):
        return True
    return limpa[0].isupper() and not primeira


def palavras_do_texto(texto):
    saida = []
    inicio_de_frase = True
    for bruta in texto.replace("*", "").split():
        if not normalizar(bruta):
            continue
        saida.append({"texto": bruta, "chave": chave(bruta), "nome": nome_proprio(bruta, inicio_de_frase)})
        inicio_de_frase = bruta.rstrip("\"'”’)]»")[-1:] in ".!?:;…"
    return saida


def _parecidas(esperadas, ouvidas, nomes):
    a = "".join(esperadas)
    b = "".join(ouvidas)
    if a == b:
        return True
    return bool(nomes) and difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= SEMELHANCA_NOME


def comparar(texto, ouvidas):
    roteiro = palavras_do_texto(texto)
    ouvido = [{"texto": o["texto"], "chave": chave(o["texto"])} for o in ouvidas if normalizar(o["texto"])]
    a = [p["chave"] for p in roteiro]
    b = [o["chave"] for o in ouvido]
    divergencias = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        esperado = " ".join(p["texto"] for p in roteiro[i1:i2])
        escutado = " ".join(o["texto"] for o in ouvido[j1:j2])
        if op == "replace":
            if _parecidas(a[i1:i2], b[j1:j2], all(p["nome"] for p in roteiro[i1:i2])):
                continue
            divergencias.append({"tipo": "trocada", "posicao": i1 + 1, "esperado": esperado, "ouvido": escutado})
        elif op == "delete":
            divergencias.append({"tipo": "faltou", "posicao": i1 + 1, "esperado": esperado, "ouvido": ""})
        else:
            divergencias.append({"tipo": "sobrou", "posicao": i1 + 1, "esperado": "", "ouvido": escutado})
    return divergencias


def _letras(palavra):
    base = "".join(ch for ch in unicodedata.normalize("NFC", palavra.lower()) if ch.isalpha())
    return "".join("ç" if ch == "ç" else sem_acento(ch) for ch in base)


def chiados_esperados(palavra):
    return len(CHIADO_RE.findall(_letras(palavra)))


def sopros_tolerados(palavra):
    return len(SOPRO_RE.findall(_letras(palavra)))


def _energias(bruto):
    amostras = array.array("h")
    amostras.frombytes(bruto[: len(bruto) // 2 * 2])
    if sys.byteorder == "big":
        amostras.byteswap()
    return [sum(v * v for v in amostras[i:i + QUADRO]) / QUADRO / (32768.0 ** 2) for i in range(0, len(amostras) - QUADRO + 1, QUADRO)]


def _faixa(arquivo, filtro):
    cmd = [str(c.ffmpeg_path()), "-v", "error", "-nostdin", "-i", str(arquivo), "-af", f"aresample={TAXA},pan=mono|c0=c0,{filtro}", "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou lendo {arquivo}: {r.stderr.decode('utf-8', 'replace')[-300:]}")
    return _energias(r.stdout)


def medir_chiados(arquivo):
    agudo = _faixa(arquivo, "highpass=f=4500,highpass=f=4500")
    grave = _faixa(arquivo, "highpass=f=200,lowpass=f=3000,lowpass=f=3000")
    return achar_chiados(agudo, grave)


def achar_chiados(agudo, grave):
    n = min(len(agudo), len(grave))
    if not n:
        return []
    teto = max(agudo[:n]) or 1e-12
    ativo = []
    for i in range(n):
        razao = 10 * math.log10((agudo[i] + 1e-12) / (grave[i] + 1e-12))
        nivel = 10 * math.log10((agudo[i] + 1e-12) / teto)
        ativo.append(razao >= LIMIAR_CHIADO_DB and nivel >= PISO_CHIADO_DB)
    trechos = []
    i = 0
    while i < n:
        if not ativo[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and (ativo[j + 1] or (j + 1 + EMENDA_QUADROS < n and any(ativo[j + 2:j + 2 + EMENDA_QUADROS]))):
            j += 1
        if j - i + 1 >= MINIMO_QUADROS:
            trechos.append((round(i * QUADRO / TAXA, 3), round((j + 1) * QUADRO / TAXA, 3)))
        i = j + 1
    return trechos


def chiados_a_mais(palavras, chiados):
    centros = [[] for _ in palavras]
    for inicio, fim in chiados:
        centro = (inicio + fim) / 2
        dono = None
        for i, p in enumerate(palavras):
            if p["inicio"] <= centro < p["fim"]:
                dono = i
                break
        if dono is None and palavras:
            dono = min(range(len(palavras)), key=lambda i: min(abs(centro - palavras[i]["inicio"]), abs(centro - palavras[i]["fim"])))
        if dono is not None:
            centros[dono].append(centro)
    esperados = [chiados_esperados(p["texto"]) for p in palavras]
    falta = [max(0, esperados[i] - len(centros[i])) for i in range(len(palavras))]
    suspeitas = []
    for i, p in enumerate(palavras):
        sobra = len(centros[i]) - esperados[i] - sopros_tolerados(p["texto"])
        if sobra <= 0:
            continue
        for centro in centros[i]:
            if sobra and i and falta[i - 1] and centro - p["inicio"] <= BEIRA_DA_PALAVRA:
                falta[i - 1] -= 1
                sobra -= 1
            elif sobra and i + 1 < len(palavras) and falta[i + 1] and p["fim"] - centro <= BEIRA_DA_PALAVRA:
                falta[i + 1] -= 1
                sobra -= 1
        if sobra > 0:
            suspeitas.append({"tipo": "chiado a mais", "posicao": i + 1, "esperado": p["texto"], "ouvido": f"{len(centros[i])} chiado(s) onde a palavra tem {esperados[i]}",
                              "inicio": p["inicio"]})
    return suspeitas


def conferir_fala(arquivo, texto, ouvidas, acustica=True):
    divergencias = comparar(texto, ouvidas)
    if acustica and ouvidas and not divergencias:
        validas = [o for o in ouvidas if normalizar(o["texto"])]
        try:
            divergencias += chiados_a_mais(validas, medir_chiados(arquivo))
        except (RuntimeError, OSError, subprocess.TimeoutExpired):
            pass
    return {"ok": not divergencias, "ouvido": " ".join(o["texto"] for o in ouvidas), "divergencias": divergencias}


def descrever(d):
    if d["tipo"] == "trocada":
        return f"palavra {d['posicao']}: o texto diz \"{d['esperado']}\" e a voz disse \"{d['ouvido']}\""
    if d["tipo"] == "faltou":
        return f"palavra {d['posicao']}: a voz pulou \"{d['esperado']}\""
    if d["tipo"] == "sobrou":
        return f"perto da palavra {d['posicao']}: a voz disse \"{d['ouvido']}\", que nao esta no texto"
    return f"palavra {d['posicao']} (\"{d['esperado']}\"): {d['ouvido']} - pode ter silaba repetida (ex.: \"anunciciado\")"


def conferir_arquivos(itens, threads=4):
    import legenda

    res = legenda.transcrever([it["arquivo"] for it in itens], threads=threads)
    ouvidas = {Path(x["arquivo"]): x["palavras"] for x in res["itens"]}
    return [conferir_fala(it["arquivo"], it["texto"], ouvidas.get(Path(it["arquivo"]), [])) for it in itens]


def relatar(nome, resultado):
    if resultado["ok"]:
        c.linha("PASS", nome, f"ouvido igual ao texto: \"{resultado['ouvido']}\"")
        return
    c.linha("FAIL", nome, "a voz NAO disse o texto como esta escrito")
    for d in resultado["divergencias"]:
        print(f"       {descrever(d)}")
    print(f"       ouvido: \"{resultado['ouvido']}\"")


def main():
    p = argparse.ArgumentParser(description="Confere a pronuncia da narracao: compara o que o Whisper local ouviu em cada fala com o texto do voz.json e procura chiado a mais (silaba repetida). Nada sai da maquina.")
    p.add_argument("pasta", help="pasta com voz.json e os voz-NN.wav (ou a pasta da composicao, que tem assets/voz)")
    p.add_argument("--threads", type=int, default=4)
    a = p.parse_args()
    pasta = Path(a.pasta).resolve()
    if not (pasta / "voz.json").is_file() and (pasta / "assets" / "voz" / "voz.json").is_file():
        pasta = pasta / "assets" / "voz"
    if not (pasta / "voz.json").is_file():
        c.falhar(f"nao achei voz.json em {pasta}")
    c.exigir_ffmpeg()
    itens = [{"arquivo": pasta / x["arquivo"], "texto": x["texto"]} for x in c.ler_json(pasta / "voz.json").get("linhas", []) if (pasta / x["arquivo"]).is_file()]
    if not itens:
        c.falhar("voz.json sem falas com arquivo")
    c.titulo(f"Pronuncia: {len(itens)} fala(s) de {c.rel(pasta)}")
    try:
        resultados = conferir_arquivos(itens, a.threads)
    except RuntimeError as err:
        c.falhar(f"nao deu para conferir: {str(err).strip().splitlines()[-1]}")
    for it, r in zip(itens, resultados):
        relatar(it["arquivo"].name, r)
    ruins = sum(1 for r in resultados if not r["ok"])
    c.titulo("Resultado")
    if ruins:
        c.linha("FAIL", f"{ruins} fala(s) com divergencia", "gere de novo essas falas (voz.py --batidas N tenta outras sementes) ou reescreva a frase; ouca antes de renderizar")
        sys.exit(1)
    c.linha("PASS", "todas as falas conferem com o texto", "a conferencia nao substitui ouvir a peca: ela nao julga entonacao nem silaba repetida sem chiado")


if __name__ == "__main__":
    main()
