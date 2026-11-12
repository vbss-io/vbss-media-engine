import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
from . import _http

_http.instalar()

NOME = "azure"
DESCRICAO = "Azure AI Speech (REST, SSML). Vozes naturais pt-BR: MAI-Voice 2.1 (aceita estilo por batida), Dragon HD e Neural. O texto vai para a Microsoft (nao verificado que o dado do cliente nao treina modelo: conferir nos termos do Azure)."
LOCAL = False
ENV_CHAVE = "AZURE_SPEECH_KEY"
ENV_REGIAO = "AZURE_SPEECH_REGION"
REGIAO_PADRAO = "eastus"
FORMATO = "riff-24khz-16bit-mono-pcm"
OPCOES_ACEITAS = ("estilo", "estilos", "altura")
NS_SSML = "http://www.w3.org/2001/10/synthesis"
NS_MSTTS = "https://www.w3.org/2001/mstts"
ESTILOS_MAI = "excited, happy, joyful, hopeful, determined, confused, embarrassed, regretful, relieved"
_ESTILO = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,40}$")
_ALTURA = re.compile(r"^([+-]?\d+(\.\d+)?(%|st|Hz)|x-low|low|medium|high|x-high)$")
_REGIAO = re.compile(r"^[a-z0-9]{3,30}$")
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
VOZES = [
    {"id": "pt-BR-Luana:MAI-Voice-2.1", "genero": "feminina", "idioma": "pt-BR", "nota": f"MAI-Voice 2.1 (NeuralHD), primeira candidata; estilos: {ESTILOS_MAI}, outros conforme a voz; testada com excited"},
    {"id": "pt-BR-Caio:MAI-Voice-2.1", "genero": "masculina", "idioma": "pt-BR", "nota": "MAI-Voice 2.1 (NeuralHD); estilos como a Luana; nao testada"},
    {"id": "pt-BR-Pedro:MAI-Voice-2.1", "genero": "masculina", "idioma": "pt-BR", "nota": f"MAI-Voice 2.1 (NeuralHD); estilos: {ESTILOS_MAI}; nao testada"},
    {"id": "pt-BR-Rafael:MAI-Voice-2.1", "genero": "masculina", "idioma": "pt-BR", "nota": "MAI-Voice 2.1 (NeuralHD); estilos como a Luana; nao testada"},
    {"id": "pt-BR-Luana:MAI-Voice-2.1-Flash", "genero": "feminina", "idioma": "pt-BR", "nota": "MAI-Voice 2.1 Flash, mais rapida e mais leve; nao testada"},
    {"id": "pt-BR-Caio:MAI-Voice-2.1-Flash", "genero": "masculina", "idioma": "pt-BR", "nota": "MAI-Voice 2.1 Flash; nao testada"},
    {"id": "pt-BR-Pedro:MAI-Voice-2.1-Flash", "genero": "masculina", "idioma": "pt-BR", "nota": "MAI-Voice 2.1 Flash; nao testada"},
    {"id": "pt-BR-Rafael:MAI-Voice-2.1-Flash", "genero": "masculina", "idioma": "pt-BR", "nota": "MAI-Voice 2.1 Flash; nao testada"},
    {"id": "pt-BR-Thalita:DragonHDLatestNeural", "genero": "feminina", "idioma": "pt-BR", "nota": "Dragon HD, sem estilos"},
    {"id": "pt-BR-Macerio:DragonHDLatestNeural", "genero": "masculina", "idioma": "pt-BR", "nota": "Dragon HD; nao testada"},
    {"id": "pt-BR-Francisca:DragonLatestNeural", "genero": "feminina", "idioma": "pt-BR", "nota": "Dragon (sem HD); nao testada"},
    {"id": "pt-BR-Macerio:DragonLatestNeural", "genero": "masculina", "idioma": "pt-BR", "nota": "Dragon (sem HD); nao testada"},
    {"id": "pt-BR-FranciscaNeural", "genero": "feminina", "idioma": "pt-BR", "nota": "Neural padrao, estavel; estilo calm"},
    {"id": "pt-BR-AntonioNeural", "genero": "masculina", "idioma": "pt-BR", "nota": "Neural padrao, estavel"},
    {"id": "pt-BR-ThalitaNeural", "genero": "feminina", "idioma": "pt-BR", "nota": "Neural padrao"},
    {"id": "pt-BR-ThalitaMultilingualNeural", "genero": "feminina", "idioma": "pt-BR", "nota": "Neural multilingue, mais expressiva"},
    {"id": "pt-BR-MacerioMultilingualNeural", "genero": "masculina", "idioma": "pt-BR", "nota": "Neural multilingue"},
]
VOZ_PADRAO = "pt-BR-Luana:MAI-Voice-2.1"


def regiao():
    return (os.environ.get(ENV_REGIAO) or REGIAO_PADRAO).strip().lower()


def disponivel(variante=None):
    if not os.environ.get(ENV_CHAVE):
        return False, f"sem chave ({ENV_CHAVE} nao definida no ambiente)"
    r = regiao()
    if not _REGIAO.match(r):
        return False, f"{ENV_REGIAO} invalida (esperado algo como eastus ou westeurope)"
    return True, f"chave presente, regiao {r}" + ("" if os.environ.get(ENV_REGIAO) else f" (padrao; {ENV_REGIAO} nao definida)")


def montar_ssml(texto, voz, velocidade=1.0, estilo=None, altura=None):
    if estilo is not None and not _ESTILO.match(str(estilo)):
        raise ValueError(f"estilo invalido: {estilo!r} (use algo como excited, happy, calm)")
    if altura is not None and not _ALTURA.match(str(altura)):
        raise ValueError(f"altura invalida: {altura!r} (use +2st, -5%, +10Hz, high...)")
    corpo = escape(_CONTROLE.sub("", texto))
    atributos = []
    if abs(velocidade - 1.0) > 1e-6:
        atributos.append(f"rate={quoteattr(f'{(velocidade - 1) * 100:+.0f}%')}")
    if altura is not None:
        atributos.append(f"pitch={quoteattr(str(altura))}")
    if atributos:
        corpo = f"<prosody {' '.join(atributos)}>{corpo}</prosody>"
    if estilo:
        corpo = f"<mstts:express-as style={quoteattr(str(estilo))}>{corpo}</mstts:express-as>"
    return (
        f"<speak version='1.0' xml:lang='pt-BR' xmlns={quoteattr(NS_SSML)} xmlns:mstts={quoteattr(NS_MSTTS)}>"
        f"<voice name={quoteattr(voz)}>{corpo}</voice>"
        "</speak>"
    )


def _requisitar(req, rotulo):
    for tentativa in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as err:
            if err.code in (429, 500, 502, 503) and tentativa == 1:
                time.sleep(2)
                continue
            detalhe = ""
            try:
                detalhe = err.read(300).decode("utf-8", "replace").strip()
            except Exception:
                pass
            raise RuntimeError(f"Azure respondeu HTTP {err.code} em {rotulo} (confira voz, regiao e chave){': ' + detalhe if detalhe else ''}") from None
        except urllib.error.URLError as err:
            raise RuntimeError(f"sem conexao com o Azure Speech ({err.reason})") from None


def sintetizar(linhas, voz, pasta, velocidade=1.0, variante=None, opcoes=None):
    ok, motivo = disponivel()
    if not ok:
        raise RuntimeError(motivo)
    opcoes = opcoes or {}
    estilos = opcoes.get("estilos") or []
    chave = os.environ[ENV_CHAVE]
    url = f"https://{regiao()}.tts.speech.microsoft.com/cognitiveservices/v1"
    itens = []
    for i, texto in enumerate(linhas, 1):
        estilo = (estilos[i - 1] if i - 1 < len(estilos) else None) or opcoes.get("estilo")
        try:
            corpo = montar_ssml(texto, voz, velocidade, estilo=estilo, altura=opcoes.get("altura")).encode("utf-8")
        except ValueError as err:
            raise RuntimeError(f"linha {i}: {err}") from None
        req = urllib.request.Request(url, data=corpo, method="POST", headers={
            "Ocp-Apim-Subscription-Key": chave,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": FORMATO,
            "User-Agent": "vbss-media-engine-voz",
        })
        t0 = time.perf_counter()
        dados = _requisitar(req, f"linha {i}")
        destino = Path(pasta) / f"bruto-{i:02d}.wav"
        destino.write_bytes(dados)
        itens.append({"arquivo": str(destino), "sintese_s": round(time.perf_counter() - t0, 3), "audio_s": None, "estilo": estilo})
    return {"modelo": f"Azure AI Speech ({FORMATO})", "carga_s": 0.0, "itens": itens}


def grupo_da_voz(curto, tipo=""):
    if ":MAI-Voice" in curto:
        versao = re.search(r":MAI-Voice-([\d.]+)(-Flash)?", curto)
        return "MAI-Voice " + (versao.group(1) + (" Flash" if versao.group(2) else "") if versao else "")
    if ":DragonHD" in curto:
        return "Dragon HD"
    if ":Dragon" in curto:
        return "Dragon"
    return "Neural HD" if "HD" in str(tipo) else "Neural"


def agrupar_vozes_ptbr(lista):
    grupos = {}
    for v in lista:
        if v.get("Locale") != "pt-BR":
            continue
        curto = v.get("ShortName", "")
        estilos = v.get("StyleList") or []
        nota = (f"estilos: {', '.join(estilos)}" if estilos else "sem estilos") + (f"; tipo {v['VoiceType']}" if v.get("VoiceType") else "")
        genero = {"Female": "feminina", "Male": "masculina"}.get(v.get("Gender"), "n/d")
        grupos.setdefault(grupo_da_voz(curto, v.get("VoiceType", "")), []).append({"id": curto, "genero": genero, "idioma": "pt-BR", "nota": nota})
    def ordem(nome):
        for posicao, prefixo in enumerate(("MAI-Voice", "Dragon HD", "Dragon", "Neural HD", "Neural")):
            if nome.startswith(prefixo):
                return (posicao, nome)
        return (99, nome)

    return [(nome, sorted(grupos[nome], key=lambda x: x["id"])) for nome in sorted(grupos, key=ordem)]


def listar_vozes_vivo():
    ok, motivo = disponivel()
    if not ok:
        raise RuntimeError(motivo)
    url = f"https://{regiao()}.tts.speech.microsoft.com/cognitiveservices/voices/list"
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": os.environ[ENV_CHAVE], "User-Agent": "vbss-media-engine-voz"})
    return agrupar_vozes_ptbr(json.loads(_requisitar(req, "a lista de vozes").decode("utf-8")))
