import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
from common import ambiente as _ambiente

KOKORO_DIR = c.AUDIO_DIR / "kokoro"
REQUISITOS = KOKORO_DIR / "requirements.txt"
MODELO_JSON = KOKORO_DIR / "modelo.json"
PACOTE_RAIZ = "kokoro-onnx==0.6.1"
PYTHONS_LOCK = ("3.11", "3.12", "3.13")
PLATAFORMA = "win_amd64"
IDADE_MINIMA_DIAS = 14
SANDBOX_PIP = c.CACHE_DIR / "pip-sandbox"


def venv_python():
    if os.name == "nt":
        return c.VENV_DIR / "Scripts" / "python.exe"
    return c.VENV_DIR / "bin" / "python"


def ambiente_pip():
    vazio = SANDBOX_PIP / "pip-vazio.ini"
    vazio.parent.mkdir(parents=True, exist_ok=True)
    vazio.write_text("", encoding="utf-8")
    extra = {
        "PIP_CACHE_DIR": str(c.CACHE_DIR / "pip"),
        "PIP_CONFIG_FILE": str(vazio),
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PIP_INDEX_URL": "https://pypi.org/simple",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return _ambiente.sandbox_env(SANDBOX_PIP, extra=extra, path_dirs=[venv_python().parent, Path(sys.executable).parent])


# O venv do Python da Microsoft Store sai sem python.exe quando PATH/LOCALAPPDATA estao isolados; criar o venv nao usa rede.
def ambiente_venv():
    tmp = c.CACHE_DIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    vazio = SANDBOX_PIP / "pip-vazio.ini"
    vazio.parent.mkdir(parents=True, exist_ok=True)
    vazio.write_text("", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not _ambiente.SECRET_NAME.search(k) and not k.startswith(("PIP_", "PYTHON"))}
    env.update({"TEMP": str(tmp), "TMP": str(tmp), "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": str(vazio),
                "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PYTHONNOUSERSITE": "1"})
    return env


def rodar(cmd, env=None, cwd=None):
    print("$ " + " ".join(str(x) for x in cmd), flush=True)
    r = subprocess.run([str(x) for x in cmd], env=env, cwd=str(cwd or c.AUDIO_DIR))
    if r.returncode != 0:
        c.falhar(f"comando falhou (codigo {r.returncode})")


def criar_venv():
    c.titulo("Ambiente Python isolado (content-engine/audio/.venv)")
    py = venv_python()
    if py.is_file():
        c.linha("OK", "venv ja existe", str(py))
        return py
    rodar([sys.executable, "-m", "venv", c.VENV_DIR], env=ambiente_venv())
    if not py.is_file():
        c.falhar(f"venv nao criado em {c.VENV_DIR}")
    c.linha("OK", "venv criado", str(py))
    return py


def instalar(py):
    c.titulo("Pacotes fixados com SHA-256 (pip --require-hashes)")
    if not REQUISITOS.is_file():
        c.falhar(f"{REQUISITOS} nao existe. Quem mantem o motor gera com: python content-engine/audio/voz_setup.py --gerar-lock")
    rodar([py, "-m", "pip", "install", "--require-hashes", "--no-deps", "--only-binary=:all:", "-r", REQUISITOS], env=ambiente_pip())
    r = subprocess.run([str(py), "-c", "import kokoro_onnx, onnxruntime, numpy; print(onnxruntime.__version__, numpy.__version__)"],
                       capture_output=True, text=True, env=ambiente_pip())
    if r.returncode != 0:
        c.falhar("import do kokoro_onnx falhou no venv:\n" + r.stderr[-800:])
    c.linha("OK", "kokoro_onnx importa no venv", f"onnxruntime {r.stdout.split()[0]}, numpy {r.stdout.split()[1]}")


def baixar_modelo(variante):
    c.titulo(f"Modelo Kokoro ({variante})")
    cfg = c.ler_json(MODELO_JSON)
    nomes = [cfg["variantes"][variante], cfg["vozes"]]
    for nome in nomes:
        info = cfg["arquivos"][nome]
        destino = c.MODELOS_DIR / nome
        estado = c.baixar_conferido(info["url"], destino, info["sha256"])
        c.linha("OK", f"{nome} ({estado})", f"{info['bytes'] / (1 << 20):.1f} MB, SHA-256 {info['sha256'][:16]}")


def wheel_id(whl):
    dist, versao = whl.name.split("-")[:2]
    return re.sub(r"[-_.]+", "-", dist).lower(), versao


def pypi_json(nome, versao):
    url = f"https://pypi.org/pypi/{nome}/{versao}/json"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "vbss-media-engine-audio-setup"}), timeout=60) as r:
        return json.load(r)


def gerar_lock():
    c.titulo("Gerando o lock (resolve, baixa wheels e registra SHA-256)")
    wheels = c.CACHE_DIR / "wheels"
    if wheels.exists():
        shutil.rmtree(wheels)
    env = ambiente_pip()
    base = wheels / PYTHONS_LOCK[0]
    rodar([sys.executable, "-m", "pip", "download", PACOTE_RAIZ, "--only-binary=:all:", "--platform", PLATAFORMA,
           "--python-version", PYTHONS_LOCK[0], "-d", base], env=env)
    versoes = dict(wheel_id(whl) for whl in sorted(base.glob("*.whl")))
    limite = datetime.now(timezone.utc) - timedelta(days=IDADE_MINIMA_DIAS)
    hashes = {}
    for nome, versao in sorted(versoes.items()):
        dados = pypi_json(nome, versao)
        enviado = min(datetime.fromisoformat(u["upload_time_iso_8601"].replace("Z", "+00:00")) for u in dados["urls"])
        if enviado > limite:
            c.falhar(f"{nome}=={versao} foi publicado em {enviado:%Y-%m-%d}, ha menos de {IDADE_MINIMA_DIAS} dias. Fixe uma versao anterior.")
        alvo = {f"{nome}=={versao}"}
        hashes[nome] = {"versao": versao, "publicado": f"{enviado:%Y-%m-%d}", "hashes": set()}
        for py in PYTHONS_LOCK:
            pasta = wheels / py
            pasta.mkdir(parents=True, exist_ok=True)
            r = subprocess.run([sys.executable, "-m", "pip", "download", *alvo, "--no-deps", "--only-binary=:all:", "--platform", PLATAFORMA,
                                "--python-version", py, "-d", str(pasta)], env=env, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"  sem wheel de {nome}=={versao} para Python {py} ({PLATAFORMA})", flush=True)
        for whl in wheels.rglob("*.whl"):
            if wheel_id(whl) == (nome, versao):
                hashes[nome]["hashes"].add(c.sha256(whl))
    linhas = [f"# gerado por voz_setup.py --gerar-lock em {datetime.now():%Y-%m-%d}; raiz {PACOTE_RAIZ}; wheels {PLATAFORMA} para Python {', '.join(PYTHONS_LOCK)}"]
    for nome, info in sorted(hashes.items()):
        if not info["hashes"]:
            c.falhar(f"nenhum wheel encontrado para {nome}")
        partes = [f"{nome}=={info['versao']}"] + [f"--hash=sha256:{h}" for h in sorted(info["hashes"])]
        linhas.append(" \\\n    ".join(partes))
    REQUISITOS.parent.mkdir(parents=True, exist_ok=True)
    REQUISITOS.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    for nome, info in sorted(hashes.items()):
        c.linha("OK", f"{nome}=={info['versao']}", f"publicado {info['publicado']}, {len(info['hashes'])} wheel(s)")
    c.linha("OK", "lock gravado", c.rel(REQUISITOS))


def main():
    p = argparse.ArgumentParser(description="Prepara a voz local Kokoro: venv isolado em content-engine/audio/.venv, pacotes fixados com SHA-256 e o modelo com SHA-256.")
    p.add_argument("--modelo", choices=["fp32", "fp16", "int8"], help="variante do modelo (padrao: a de kokoro/modelo.json)")
    p.add_argument("--gerar-lock", action="store_true", help="manutencao: resolve as dependencias e regrava kokoro/requirements.txt com SHA-256")
    a = p.parse_args()
    if f"{sys.version_info.major}.{sys.version_info.minor}" not in PYTHONS_LOCK:
        c.falhar(f"o lock do Kokoro tem wheels para Python {', '.join(PYTHONS_LOCK)} ({PLATAFORMA}); este e {sys.version.split()[0]}")
    print("Rede usada: so o PyPI (pacotes fixados) e o GitHub Releases do kokoro-onnx (modelo com SHA-256). Nada e instalado fora de content-engine/audio/.")
    if a.gerar_lock:
        gerar_lock()
        return
    py = criar_venv()
    instalar(py)
    variante = a.modelo or c.ler_json(MODELO_JSON)["padrao"]
    baixar_modelo(variante)
    print("\nPronto. Confira com: python content-engine/audio/doctor.py")


if __name__ == "__main__":
    main()
