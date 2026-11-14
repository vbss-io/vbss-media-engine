import importlib.util
import json
import time
from pathlib import Path

NOME = "voicestudio"
DESCRICAO = "VoiceStudio local (OmniVoice, commit pinado em voicestudio/pin.json). Roda na CPU desta maquina, offline; nada sai dela. Vozes guardadas em voicestudio/voices (clone ou design). Os pesos do OmniVoice sao CC-BY-NC: uso comercial nao e permitido."
LOCAL = True
SCRIPT = Path(__file__).resolve().parents[3] / "voicestudio" / "voicestudio.py"
VOZES_JSON = SCRIPT.parent / "voices" / "vozes.json"
MODELO_TTS = "k2-fsa/OmniVoice"
PASSOS = {"qualidade": 32, "rapido": 16}
VARIANTE_PADRAO = "qualidade"
ACEITA_SEMENTE = True
FILA_TENTATIVAS = 30
FILA_ESPERA = 10
SEMENTES = (7, 11, 23, 42, 101)
_modulo = None


def _vozes_guardadas():
    try:
        return json.loads(VOZES_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


VOZES = [{"id": nome, "genero": "", "idioma": "pt-BR", "nota": voz.get("origem", "")} for nome, voz in _vozes_guardadas().items()]
VOZ_PADRAO = "narradora"


def _vs():
    global _modulo
    if _modulo is None:
        spec = importlib.util.spec_from_file_location("vbss_voicestudio", SCRIPT)
        _modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_modulo)
    return _modulo


def variantes():
    return tuple(PASSOS)


def disponivel(variante=None):
    if not SCRIPT.is_file():
        return False, "voicestudio/voicestudio.py ausente"
    vs = _vs()
    if not vs.VENV_PY.is_file():
        return False, "VoiceStudio nao instalado: python voicestudio/voicestudio.py instalar"
    if not (vs.MODELOS / f"models--{MODELO_TTS.replace('/', '--')}").is_dir():
        return False, "modelo de voz nao baixado: python voicestudio/voicestudio.py modelos"
    try:
        fora = [nome for nome, ok, _ in vs.estado_do_pin() if not ok]
    except SystemExit as err:
        return False, f"repo do VoiceStudio ilegivel ({err})"
    if fora:
        return False, f"repo fora do pin ({', '.join(fora)}): python voicestudio/voicestudio.py checar"
    if not _vozes_guardadas():
        return False, "nenhuma voz em voicestudio/voices: python voicestudio/voicestudio.py voz"
    return True, "instalado, pinado e com modelo; a API sobe sozinha na geracao e desce no fim"


def _gerar_esperando(vs, texto, voz, destino, semente, velocidade, passos):
    for tentativa in range(1, FILA_TENTATIVAS + 1):
        try:
            return vs.gerar(texto, voz, destino, seed=semente, velocidade=velocidade, passos=passos)
        except SystemExit as err:
            if "-> 429" not in str(err) or tentativa == FILA_TENTATIVAS:
                raise
            print(f"motor de voz ocupado (fila cheia), esperando {FILA_ESPERA} s ({tentativa} de {FILA_TENTATIVAS - 1})...", flush=True)
            time.sleep(FILA_ESPERA)


def sintetizar(linhas, voz, pasta, velocidade=1.0, variante=None, sementes=None):
    ok, motivo = disponivel()
    if not ok:
        raise RuntimeError(motivo)
    if voz not in _vozes_guardadas():
        raise RuntimeError(f"voz '{voz}' nao esta em voicestudio/voices (existem: {', '.join(_vozes_guardadas())})")
    vs = _vs()
    variante = variante or VARIANTE_PADRAO
    passos = PASSOS[variante]
    t0 = time.perf_counter()
    itens = []
    try:
        with vs.sessao_api():
            carga = time.perf_counter() - t0
            for i, texto in enumerate(linhas, 1):
                destino = Path(pasta) / f"bruto-{i:02d}.wav"
                t = time.perf_counter()
                semente = sementes[i - 1] if sementes and sementes[i - 1] is not None else vs.SEED
                _gerar_esperando(vs, texto, voz, destino, semente, velocidade, passos)
                itens.append({"arquivo": str(destino), "sintese_s": round(time.perf_counter() - t, 3), "audio_s": None, "semente": semente})
    except SystemExit as err:
        raise RuntimeError(f"VoiceStudio: {err}") from None
    return {"modelo": f"VoiceStudio {vs.PIN['commit'][:8]} / OmniVoice (local, CPU, seed {'por fala' if sementes else vs.SEED}, {passos} passos, variante {variante})", "carga_s": round(carga, 3), "itens": itens}
