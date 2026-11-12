import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from . import _http

_http.instalar()

NOME = "google"
DESCRICAO = "Google Cloud Text-to-Speech (REST, vozes Chirp 3 HD). O texto vai para o Google Cloud (nao verificado que o dado do cliente nao treina modelo: conferir nos termos ao criar o projeto)."
LOCAL = False
ENV_CHAVE = "GOOGLE_TTS_API_KEY"
URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
TAXA = 24000
VOZES = [
    {"id": "pt-BR-Chirp3-HD-Kore", "genero": "feminina", "idioma": "pt-BR", "nota": "Chirp 3 HD"},
    {"id": "pt-BR-Chirp3-HD-Aoede", "genero": "feminina", "idioma": "pt-BR", "nota": "Chirp 3 HD"},
    {"id": "pt-BR-Chirp3-HD-Charon", "genero": "masculina", "idioma": "pt-BR", "nota": "Chirp 3 HD"},
]
VOZ_PADRAO = "pt-BR-Chirp3-HD-Kore"


def disponivel(variante=None):
    if not os.environ.get(ENV_CHAVE):
        return False, f"sem chave ({ENV_CHAVE} nao definida no ambiente)"
    return True, "chave presente"


def sintetizar(linhas, voz, pasta, velocidade=1.0, variante=None):
    ok, motivo = disponivel()
    if not ok:
        raise RuntimeError(motivo)
    chave = os.environ[ENV_CHAVE]
    itens = []
    for i, texto in enumerate(linhas, 1):
        audio = {"audioEncoding": "LINEAR16", "sampleRateHertz": TAXA}
        if abs(velocidade - 1.0) > 1e-6:
            audio["speakingRate"] = velocidade
        corpo = json.dumps({"input": {"text": texto}, "voice": {"languageCode": "pt-BR", "name": voz}, "audioConfig": audio}).encode("utf-8")
        req = urllib.request.Request(URL, data=corpo, method="POST", headers={
            "X-Goog-Api-Key": chave,
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "vbss-media-engine-voz",
        })
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resposta = json.load(r)
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"Google TTS respondeu HTTP {err.code} na linha {i} (confira voz, API habilitada e chave)") from None
        except urllib.error.URLError as err:
            raise RuntimeError(f"sem conexao com o Google TTS ({err.reason})") from None
        destino = Path(pasta) / f"bruto-{i:02d}.wav"
        destino.write_bytes(base64.b64decode(resposta["audioContent"]))
        itens.append({"arquivo": str(destino), "sintese_s": round(time.perf_counter() - t0, 3), "audio_s": None})
    return {"modelo": "Google Cloud TTS (LINEAR16 24 kHz)", "carga_s": 0.0, "itens": itens}
