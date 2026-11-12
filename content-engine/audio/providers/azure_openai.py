import base64
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from . import _http

_http.instalar()

NOME = "azure_openai"
DESCRICAO = "Azure OpenAI gpt-audio (chat completions com saida de audio): fala com entonacao de locutor e aceita instrucao de tom em texto livre (--tom). O modelo e generativo, entao cada fala e conferida palavra por palavra contra a transcricao devolvida (parafrase = nova tentativa, depois erro). O texto vai para a Microsoft (nao verificado que o dado do cliente nao treina modelo: conferir nos termos do Azure)."
LOCAL = False
ENV_CHAVE = "AZURE_OPENAI_KEY"
ENV_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
ENV_VERSAO = "AZURE_OPENAI_API_VERSION"
ENV_DEPLOYMENT = "AZURE_OPENAI_AUDIO_DEPLOYMENT"
VERSAO_PADRAO = "2025-04-01-preview"
DEPLOYMENTS = ("gpt-audio-1.5",)
DEPLOYMENT_PADRAO = "gpt-audio-1.5"
OPCOES_ACEITAS = ("estilo", "estilos", "tom")
TENTATIVAS = 2
VOZES = [
    {"id": "marin", "genero": "nao informado", "idioma": "pt-BR", "nota": "testada com gpt-audio-1.5 (transcricao identica ao texto)"},
    {"id": "cedar", "genero": "nao informado", "idioma": "pt-BR", "nota": "recomendada pela OpenAI para qualidade; testada em 2026-10-08 (reel completo, transcricao identica)"},
    {"id": "alloy", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
    {"id": "ash", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
    {"id": "ballad", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
    {"id": "coral", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
    {"id": "echo", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
    {"id": "sage", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
    {"id": "shimmer", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
    {"id": "verse", "genero": "nao informado", "idioma": "pt-BR", "nota": "nao testada"},
]
VOZ_PADRAO = "marin"
PROMPT_BASE = (
    "Você é locutor de vídeos curtos em português do Brasil. Leia exatamente o texto do usuário, "
    "sem acrescentar, omitir nem trocar nenhuma palavra, e sem responder ao texto: apenas leia em voz alta, "
    "com energia e naturalidade."
)


def deployment_padrao():
    return os.environ.get(ENV_DEPLOYMENT) or DEPLOYMENT_PADRAO


def variantes():
    nomes = list(DEPLOYMENTS)
    extra = os.environ.get(ENV_DEPLOYMENT)
    if extra and extra not in nomes:
        nomes.append(extra)
    return tuple(nomes)


def endpoint():
    bruto = (os.environ.get(ENV_ENDPOINT) or "").strip().rstrip("/")
    if not bruto:
        return None, f"{ENV_ENDPOINT} nao definida no ambiente"
    p = urllib.parse.urlparse(bruto)
    if p.scheme != "https" or not p.hostname or not p.hostname.endswith(".azure.com"):
        return None, f"{ENV_ENDPOINT} deve ser https://<recurso>.services.ai.azure.com (ou .openai.azure.com): a chave so e enviada para hosts azure.com"
    return f"https://{p.hostname}", None


def disponivel(variante=None):
    faltam = [v for v in (ENV_CHAVE, ENV_ENDPOINT) if not os.environ.get(v)]
    if faltam:
        return False, f"sem chave ({' e '.join(faltam)} nao definida no ambiente)"
    host, erro = endpoint()
    if erro:
        return False, erro
    return True, f"chave presente, {host}, deployment {variante or deployment_padrao()}"


def normalizar(texto):
    sem_acento = "".join(ch for ch in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", sem_acento.lower())


def igual_ao_texto(texto, transcricao):
    return normalizar(texto) == normalizar(transcricao)


def montar_prompt(tom=None, velocidade=1.0):
    partes = [PROMPT_BASE]
    if tom:
        partes.append(f"Tom da leitura: {tom}.")
    if velocidade >= 1.05:
        partes.append("Ritmo: um pouco mais rápido que o normal, sem atropelar palavras.")
    elif velocidade <= 0.95:
        partes.append("Ritmo: um pouco mais lento que o normal.")
    return " ".join(partes)


def montar_corpo(texto, voz, tom=None, velocidade=1.0):
    return {
        "modalities": ["text", "audio"],
        "audio": {"voice": voz, "format": "wav"},
        "messages": [
            {"role": "system", "content": montar_prompt(tom, velocidade)},
            {"role": "user", "content": texto},
        ],
    }


def _chamar(url, chave, corpo, rotulo):
    req = urllib.request.Request(url, data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"), method="POST", headers={
        "api-key": chave,
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "vbss-media-engine-voz",
    })
    for tentativa in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as err:
            if err.code in (429, 500, 502, 503) and tentativa == 1:
                time.sleep(3)
                continue
            detalhe = ""
            try:
                detalhe = err.read(300).decode("utf-8", "replace").strip()
            except Exception:
                pass
            raise RuntimeError(f"Azure OpenAI respondeu HTTP {err.code} em {rotulo} (confira deployment, endpoint e chave){': ' + detalhe if detalhe else ''}") from None
        except urllib.error.URLError as err:
            raise RuntimeError(f"sem conexao com o Azure OpenAI ({err.reason})") from None


def _extrair(resposta, rotulo):
    try:
        audio = resposta["choices"][0]["message"]["audio"]
        wav = base64.b64decode(audio["data"])
        transcricao = audio.get("transcript") or ""
    except (KeyError, IndexError, TypeError, ValueError):
        raise RuntimeError(f"{rotulo}: a resposta do Azure OpenAI veio sem audio (o deployment e um modelo gpt-audio e a api-version aceita audio?)") from None
    uso = resposta.get("usage") or {}
    detalhe = uso.get("completion_tokens_details") or {}
    tokens = {
        "entrada": uso.get("prompt_tokens"),
        "saida": uso.get("completion_tokens"),
        "total": uso.get("total_tokens"),
        "audio_saida": detalhe.get("audio_tokens"),
    }
    return wav, transcricao, tokens


def sintetizar(linhas, voz, pasta, velocidade=1.0, variante=None, opcoes=None):
    ok, motivo = disponivel(variante)
    if not ok:
        raise RuntimeError(motivo)
    opcoes = opcoes or {}
    estilos = opcoes.get("estilos") or []
    host, _ = endpoint()
    deployment = variante or deployment_padrao()
    versao = os.environ.get(ENV_VERSAO) or VERSAO_PADRAO
    url = f"{host}/openai/deployments/{urllib.parse.quote(deployment, safe='')}/chat/completions?api-version={urllib.parse.quote(versao, safe='')}"
    chave = os.environ[ENV_CHAVE]
    itens = []
    for i, texto in enumerate(linhas, 1):
        tom = (estilos[i - 1] if i - 1 < len(estilos) else None) or opcoes.get("tom") or opcoes.get("estilo")
        corpo = montar_corpo(texto, voz, tom, velocidade)
        t0 = time.perf_counter()
        recusadas = []
        wav = transcricao = tokens = None
        for tentativa in range(1, TENTATIVAS + 1):
            wav, transcricao, tokens = _extrair(_chamar(url, chave, corpo, f"linha {i}"), f"linha {i}")
            if igual_ao_texto(texto, transcricao):
                break
            recusadas.append(transcricao)
            wav = None
        if wav is None:
            raise RuntimeError(
                f"linha {i}: o gpt-audio nao leu o texto exato em {TENTATIVAS} tentativas (nunca aceito parafrase). "
                f"Esperado: \"{texto}\". Ultima transcricao: \"{recusadas[-1]}\". Simplifique a fala (sem sigla, numero por extenso) ou tente outra voz/deployment."
            )
        destino = Path(pasta) / f"bruto-{i:02d}.wav"
        destino.write_bytes(wav)
        itens.append({"arquivo": str(destino), "sintese_s": round(time.perf_counter() - t0, 3), "audio_s": None,
                      "transcricao": transcricao, "tokens": tokens, "tentativas": len(recusadas) + 1, "tom": tom})
    return {"modelo": f"Azure OpenAI {deployment} (api-version {versao})", "carga_s": 0.0, "itens": itens}
