import json
import os
import subprocess
import tempfile
from pathlib import Path

import _comum as c
from comum import ambiente as _ambiente

NOME = "kokoro"
DESCRICAO = "Kokoro-82M (Apache-2.0) rodando nesta maquina via kokoro-onnx e onnxruntime (CPU). Nada sai do computador."
LOCAL = True
IDIOMA = "pt-br"
VOZES = [
    {"id": "pf_dora", "genero": "feminina", "idioma": "pt-BR", "nota": "unica voz feminina pt-BR do Kokoro v1.0"},
    {"id": "pm_alex", "genero": "masculina", "idioma": "pt-BR", "nota": "voz masculina pt-BR"},
    {"id": "pm_santa", "genero": "masculina", "idioma": "pt-BR", "nota": "voz masculina pt-BR, timbre mais grave"},
]
VOZ_PADRAO = "pf_dora"
KOKORO_DIR = c.AUDIO_DIR / "kokoro"
WORKER = Path(__file__).resolve().parent / "kokoro_worker.py"
SANDBOX = c.CACHE_DIR / "kokoro-sandbox"


def venv_python():
    if os.name == "nt":
        return c.VENV_DIR / "Scripts" / "python.exe"
    return c.VENV_DIR / "bin" / "python"


def config_modelo():
    return c.ler_json(KOKORO_DIR / "modelo.json")


def arquivos_modelo(variante=None):
    cfg = config_modelo()
    variante = variante or cfg["padrao"]
    if variante not in cfg["variantes"]:
        raise ValueError(f"variante '{variante}' desconhecida (use {', '.join(cfg['variantes'])})")
    return variante, c.MODELOS_DIR / cfg["variantes"][variante], c.MODELOS_DIR / cfg["vozes"]


def variantes():
    return tuple(config_modelo()["variantes"])


def conferir_vozes():
    ids = set(vozes_instaladas()["vozes"])
    pt = sorted(x for x in ids if x.startswith("p"))
    return ids, f"vozes pt-BR no arquivo de vozes: {', '.join(pt)} (total de vozes no arquivo: {len(ids)})"


def disponivel(variante=None):
    if not venv_python().is_file():
        return False, "venv ausente: rode python content-engine/audio/voz_setup.py"
    try:
        variante, modelo, vozes = arquivos_modelo(variante)
    except ValueError as err:
        return False, str(err)
    faltam = [p.name for p in (modelo, vozes) if not p.is_file()]
    if faltam:
        return False, f"modelo ausente ({', '.join(faltam)}): rode python content-engine/audio/voz_setup.py --modelo {variante}"
    return True, f"modelo {variante} ({modelo.name})"


def ambiente():
    env = _ambiente.sandbox_env(SANDBOX, extra={"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                                path_dirs=[venv_python().parent])
    return env


def _rodar(tarefa):
    SANDBOX.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SANDBOX, encoding="utf-8") as f:
        json.dump(tarefa, f, ensure_ascii=False)
        caminho = f.name
    try:
        r = subprocess.run([str(venv_python()), "-I", "-B", str(WORKER), caminho], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=ambiente(), cwd=str(SANDBOX), timeout=3600)
    finally:
        Path(caminho).unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError("o Kokoro falhou:\n" + r.stderr[-1500:])
    ultima = [ln for ln in r.stdout.splitlines() if ln.strip().startswith("{")]
    if not ultima:
        raise RuntimeError("o Kokoro nao devolveu resultado:\n" + (r.stdout + r.stderr)[-1500:])
    return json.loads(ultima[-1])


def vozes_instaladas(variante=None):
    _, modelo, vozes = arquivos_modelo(variante)
    return _rodar({"listar": True, "modelo": str(modelo), "vozes": str(vozes)})


def sintetizar(linhas, voz, pasta, velocidade=1.0, variante=None):
    variante, modelo, vozes = arquivos_modelo(variante)
    tarefa = {
        "modelo": str(modelo),
        "vozes": str(vozes),
        "voz": voz,
        "idioma": IDIOMA,
        "velocidade": velocidade,
        "linhas": [{"texto": t, "saida": str(Path(pasta) / f"bruto-{i:02d}.wav")} for i, t in enumerate(linhas, 1)],
    }
    res = _rodar(tarefa)
    return {
        "modelo": f"Kokoro-82M v1.0 {variante} ({modelo.name})",
        "carga_s": res["carga_s"],
        "pico_memoria_mb": res.get("pico_memoria_mb"),
        "itens": [{"arquivo": it["saida"], "sintese_s": it["sintese_s"], "audio_s": it["audio_s"]} for it in res["itens"]],
    }
