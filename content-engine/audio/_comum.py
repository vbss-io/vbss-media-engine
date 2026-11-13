import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent
ENGINE_DIR = AUDIO_DIR.parent
REPO_DIR = ENGINE_DIR.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from common.saida import falhar, linha, titulo

SFX_DIR = AUDIO_DIR / "sfx"
SFX_MANIFESTO = SFX_DIR / "sfx.json"
SFX_FONTES = AUDIO_DIR / "sfx_fontes.json"
SFX_SELECAO = AUDIO_DIR / "sfx_selecao.json"
MUSICA_DIR = AUDIO_DIR / "music"
MUSICA_MANIFESTO = MUSICA_DIR / "musica.json"
MUSICA_FONTES = AUDIO_DIR / "musica_fontes.json"
CACHE_DIR = AUDIO_DIR / ".cache"
VENV_DIR = AUDIO_DIR / ".venv"
MODELOS_DIR = AUDIO_DIR / ".models"
WORK_DIR = AUDIO_DIR / ".work"
VIDEO_DIR = ENGINE_DIR / "video"
BIN_DIR = VIDEO_DIR / "bin"
SUFIXO_EXE = ".exe" if os.name == "nt" else ""

ENV_VOZ = AUDIO_DIR / ".env"


def carregar_env_voz():
    # chaves de voz de nuvem ficam so neste arquivo (ignorado pelo git); variavel ja definida no ambiente prevalece
    if not ENV_VOZ.is_file():
        return []
    carregadas = []
    for bruta in ENV_VOZ.read_text(encoding="utf-8-sig").splitlines():
        linha_env = bruta.strip()
        if not linha_env or linha_env.startswith("#") or "=" not in linha_env:
            continue
        nome, valor = linha_env.split("=", 1)
        nome = nome.strip()
        if nome.lower().startswith("export "):
            nome = nome[7:].strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", nome) or not valor or valor.startswith("<"):
            continue
        if nome not in os.environ:
            os.environ[nome] = valor
            carregadas.append(nome)
    return carregadas


ENV_PROVEDOR = "VOZ_PROVEDOR"


def env_da_voz(provedor):
    return "VOZ_" + provedor.upper()


def config_de_voz(caminho=None):
    cfg = ler_json(caminho or AUDIO_DIR / "voz_config.json")
    origem = {"provedor": "voz_config.json"}
    provedor = os.environ.get(ENV_PROVEDOR, "").strip()
    if provedor:
        cfg["provedor"] = provedor
        origem["provedor"] = ".env"
    for nome in set(cfg["vozes_padrao"]) | {cfg["provedor"]}:
        voz = os.environ.get(env_da_voz(nome), "").strip()
        origem[nome] = ".env" if voz else "voz_config.json"
        if voz:
            cfg["vozes_padrao"][nome] = voz
    cfg["origem"] = origem
    return cfg


TAXA_SFX = 48000
ALVO_SFX_LUFS_MOMENTANEO = -16.0
TETO_PICO_DBTP = -1.0
ALVO_VOZ_LUFS = -16.0
ALVO_MUSICA_LUFS = -16.0


def ffmpeg_path():
    return BIN_DIR / f"ffmpeg{SUFIXO_EXE}"


def ffprobe_path():
    return BIN_DIR / f"ffprobe{SUFIXO_EXE}"


def exigir_ffmpeg():
    if not ffmpeg_path().is_file() or not ffprobe_path().is_file():
        falhar("FFmpeg local ausente em content-engine/video/bin. Rode python content-engine/video/setup.py")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def escrever_json(path, dados):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def baixar(url, destino, agente="vbss-media-engine-audio-setup"):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": agente})
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        lido = 0
        ultimo = -1
        while True:
            bloco = resp.read(1 << 20)
            if not bloco:
                break
            out.write(bloco)
            lido += len(bloco)
            if total and total > (8 << 20):
                pct = lido * 100 // total
                if pct // 10 != ultimo:
                    ultimo = pct // 10
                    print(f"  {pct}% ({lido // (1 << 20)} MB)", flush=True)
    tmp.replace(destino)


def baixar_conferido(url, destino, sha_esperado):
    destino = Path(destino)
    if destino.is_file() and sha256(destino) == sha_esperado:
        return "cache"
    if destino.is_file():
        destino.unlink()
    print(f"Baixando {url}", flush=True)
    baixar(url, destino)
    obtido = sha256(destino)
    if obtido != sha_esperado:
        destino.unlink()
        falhar(f"SHA-256 nao confere para {url} (esperado {sha_esperado}, veio {obtido}). Arquivo apagado.")
    return "baixado"


def ffmpeg(args, timeout=600):
    r = subprocess.run([str(ffmpeg_path()), "-hide_banner", "-nostdin", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r


def duracao(arquivo):
    r = subprocess.run(
        [str(ffprobe_path()), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(arquivo)],
        capture_output=True, text=True, timeout=120,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def streams(arquivo):
    r = subprocess.run(
        [str(ffprobe_path()), "-v", "error", "-show_entries", "stream=index,codec_type,codec_name,sample_rate,channels:format=duration", "-of", "json", str(arquivo)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        return {}
    return json.loads(r.stdout)


def _ultimo_float(padrao, texto):
    achados = re.findall(padrao, texto)
    if not achados:
        return None
    try:
        return float(achados[-1])
    except ValueError:
        return None


def medir(arquivo, inicio=None, fim=None):
    filtros = "apad=pad_dur=0.5,ebur128=peak=true:framelog=info"
    args = []
    if inicio is not None:
        args += ["-ss", f"{inicio:.3f}"]
    if fim is not None:
        args += ["-to", f"{fim:.3f}"]
    r = ffmpeg([*args, "-i", str(arquivo), "-af", filtros, "-f", "null", "-"])
    texto = r.stderr
    momentaneos = [float(x) for x in re.findall(r"\bM:\s*(-?[\d.]+|-inf)", texto) if x != "-inf"]
    resumo = texto.split("Summary:")[-1] if "Summary:" in texto else ""
    return {
        "duracao": round(duracao(arquivo), 3),
        "lufs_integrado": _ultimo_float(r"I:\s*(-?[\d.]+) LUFS", resumo),
        "lufs_momentaneo_max": round(max(momentaneos), 1) if momentaneos else None,
        "pico_dbtp": _ultimo_float(r"Peak:\s*(-?[\d.]+|-inf) dBFS", resumo),
        "lra": _ultimo_float(r"LRA:\s*(-?[\d.]+) LU", resumo),
    }


def volumedetect(arquivo):
    r = ffmpeg(["-i", str(arquivo), "-af", "volumedetect", "-f", "null", "-"])
    return {
        "media_db": _ultimo_float(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr),
        "max_db": _ultimo_float(r"max_volume:\s*(-?[\d.]+) dB", r.stderr),
    }


def rel(path):
    try:
        return Path(path).resolve().relative_to(REPO_DIR).as_posix()
    except ValueError:
        return str(path)
