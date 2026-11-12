import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

VIDEO_DIR = Path(__file__).resolve().parent
ENGINE_DIR = VIDEO_DIR.parent
REPO_DIR = ENGINE_DIR.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from common import ambiente as _ambiente
from common import navegador as navegador_fixado
from common.chrome import AVISO_SISTEMA, descrever_navegador, e_navegador_fixo, file_version, find_chrome, isolamento_env, versao_navegador
from common.saida import falhar, linha, titulo

SANDBOX_DIR = VIDEO_DIR / ".sandbox"
CACHE_DIR = VIDEO_DIR / ".cache"
BIN_DIR = VIDEO_DIR / "bin"
ENGINES_DIR = VIDEO_DIR / "engines"
MOTOR_CONFIG = VIDEO_DIR / "motor.json"
NET_GUARD_LOG = SANDBOX_DIR / "net-guard.log"
FILE_GUARD_LOG = SANDBOX_DIR / "file-guard.log"
ENV_RAIZES = "VBSS_FILE_GUARD_RAIZES"
ENV_LOG_ARQUIVOS = "VBSS_FILE_GUARD_LOG"
PASTAS_DO_MOTOR_NO_SANDBOX = ("home", "tmp", "cwd", "saida", "fonts", "media", "renders", "puppeteer")
SECRET_NAME = _ambiente.SECRET_NAME


FFMPEG_BUILD = {
    "versao": "9.0.2",
    "arquivo": "ffmpeg-9.0.2-essentials_build.zip",
    "urls": [
        "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip",
        "https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip",
    ],
    "sha256": "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba",
    "membros": {
        "ffmpeg.exe": "ffmpeg-9.0.2-essentials_build/bin/ffmpeg.exe",
        "ffprobe.exe": "ffmpeg-9.0.2-essentials_build/bin/ffprobe.exe",
        "LICENSE-ffmpeg.txt": "ffmpeg-9.0.2-essentials_build/LICENSE",
    },
}


def ffmpeg_path():
    return BIN_DIR / "ffmpeg.exe"


def ffprobe_path():
    return BIN_DIR / "ffprobe.exe"


def node_path():
    found = shutil.which("node")
    return Path(found) if found else None


def node_version(node):
    out = subprocess.run([str(node), "--version"], capture_output=True, text=True, timeout=30)
    m = re.match(r"v(\d+)\.(\d+)\.(\d+)", out.stdout.strip())
    return tuple(int(x) for x in m.groups()) if m else None


def load_motor():
    if not MOTOR_CONFIG.is_file():
        falhar(f"{MOTOR_CONFIG} nao existe: nao ha motor de video configurado.")
    cfg = json.loads(MOTOR_CONFIG.read_text(encoding="utf-8"))
    nome = cfg.get("ativo")
    if not nome or not re.fullmatch(r"[a-z0-9-]+", nome):
        falhar(f"motor.json invalido: campo 'ativo' = {nome!r}")
    adapter = ENGINES_DIR / nome / "adapter.py"
    if not adapter.is_file():
        falhar(f"o motor ativo '{nome}' nao tem {adapter}")
    spec = importlib.util.spec_from_file_location(f"motor_{nome.replace('-', '_')}", adapter)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sandbox_paths():
    return _ambiente.sandbox_paths(SANDBOX_DIR, extras=("stage", "saida"))


def sandbox_env(extra=None, path_dirs=()):
    sandbox_paths()
    tudo = dict(isolamento_env())
    if extra:
        tudo.update(extra)
    return _ambiente.sandbox_env(SANDBOX_DIR, extra=tudo, path_dirs=[BIN_DIR, *path_dirs])


def raizes_permitidas(motor, stage, node, chrome, extras=()):
    pastas = [SANDBOX_DIR / nome for nome in PASTAS_DO_MOTOR_NO_SANDBOX]
    fixas = [Path(motor.__file__).resolve().parent, BIN_DIR, NET_GUARD_LOG, FILE_GUARD_LOG]
    programas = [Path(p).resolve().parent for p in (node, chrome) if p]
    return [str(Path(p)) for p in (stage, *pastas, *fixas, *programas, *extras)]


def ambiente_de_arquivos(raizes, log=FILE_GUARD_LOG):
    return {ENV_RAIZES: json.dumps([str(r) for r in raizes]), ENV_LOG_ARQUIVOS: str(log)}


def ler_log(log, offset):
    if not log.is_file():
        return []
    with open(log, "rb") as f:
        f.seek(offset)
        return [ln for ln in f.read().decode("utf-8", errors="replace").splitlines() if ln.strip()]


def tamanho(log):
    return log.stat().st_size if log.is_file() else 0


def assert_env_isolated(env):
    return _ambiente.assert_env_isolated(env, SANDBOX_DIR)


def probe(video):
    out = subprocess.run(
        [str(ffprobe_path()), "-v", "error", "-show_entries",
         "format=duration:stream=index,codec_type,codec_name,profile,width,height,r_frame_rate,avg_frame_rate,pix_fmt,nb_frames",
         "-of", "json", str(video)],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout)


def resumo_video(video):
    data = probe(video)
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    dur = float(data.get("format", {}).get("duration", 0))
    if not v:
        return {"duracao": dur, "video": None, "audio": len(a)}
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    return {
        "duracao": round(dur, 3),
        "largura": v.get("width"),
        "altura": v.get("height"),
        "fps": round(fps, 3),
        "codec": v.get("codec_name"),
        "perfil": v.get("profile"),
        "pix_fmt": v.get("pix_fmt"),
        "frames": v.get("nb_frames"),
        "audio": len(a),
    }
