import json
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from common.download import baixar, sha256

COMUM_DIR = Path(__file__).resolve().parent
FIXACAO = COMUM_DIR / "navegador.json"
NAVEGADOR_DIR = COMUM_DIR.parent / "browser"
CACHE_DIR = NAVEGADOR_DIR / ".cache"
EXTRAINDO_DIR = NAVEGADOR_DIR / ".extraindo"
MARCA = NAVEGADOR_DIR / "instalado.json"


def fixado():
    return json.loads(FIXACAO.read_text(encoding="utf-8"))


def executavel(pin=None):
    pin = pin or fixado()
    return NAVEGADOR_DIR / pin["executavel"]


def _marca():
    try:
        return json.loads(MARCA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def instalado():
    try:
        pin = fixado()
    except (OSError, ValueError):
        return None
    marca = _marca()
    if not marca or marca.get("versao") != pin["versao"] or marca.get("sha256") != pin["sha256"]:
        return None
    exe = executavel(pin)
    if not exe.is_file() or exe.stat().st_size != pin["executavel_bytes"]:
        return None
    return exe


def conferir():
    pin = fixado()
    exe = executavel(pin)
    marca = _marca()
    if not marca:
        return [f"{MARCA.name} ausente: rode o setup"]
    problemas = []
    if marca.get("versao") != pin["versao"] or marca.get("sha256") != pin["sha256"]:
        problemas.append(f"instalado {marca.get('versao')}, fixado {pin['versao']}: rode o setup")
    if not exe.is_file():
        problemas.append(f"{exe} ausente: rode o setup")
    elif sha256(exe) != pin["executavel_sha256"]:
        problemas.append(f"SHA-256 de {exe.name} diferente do navegador.json: rode o setup")
    return problemas


def _membro_seguro(nome, pasta):
    p = PurePosixPath(nome)
    return (
        "\\" not in nome and ":" not in nome and not p.is_absolute()
        and ".." not in p.parts and p.parts[:1] == (pasta,)
    )


def _extrair(zip_path, pin, falhar):
    if EXTRAINDO_DIR.exists():
        shutil.rmtree(EXTRAINDO_DIR)
    EXTRAINDO_DIR.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        ruins = [i.filename for i in z.infolist() if not _membro_seguro(i.filename, pin["pasta"])]
        if ruins:
            falhar(f"o zip do navegador tem caminho fora de {pin['pasta']}/: {ruins[:3]}")
        z.extractall(EXTRAINDO_DIR)
    exe = EXTRAINDO_DIR / pin["executavel"]
    obtido = sha256(exe) if exe.is_file() else "ausente"
    if obtido != pin["executavel_sha256"]:
        shutil.rmtree(EXTRAINDO_DIR, ignore_errors=True)
        falhar(f"SHA-256 de {exe.name} nao confere (esperado {pin['executavel_sha256']}, veio {obtido}).")
    destino = NAVEGADOR_DIR / pin["pasta"]
    if destino.exists():
        shutil.rmtree(destino)
    (EXTRAINDO_DIR / pin["pasta"]).replace(destino)
    shutil.rmtree(EXTRAINDO_DIR, ignore_errors=True)
    return destino


def instalar(linha, titulo, falhar):
    pin = fixado()
    titulo(f"Navegador fixo ({pin['nome']} {pin['versao']} {pin['plataforma']})")
    if instalado() and not conferir():
        linha("OK", "navegador fixo ja instalado e com SHA-256 conferido", str(executavel(pin)))
        return executavel(pin)
    if MARCA.exists():
        MARCA.unlink()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = CACHE_DIR / pin["arquivo"]
    if zip_path.is_file() and sha256(zip_path) != pin["sha256"]:
        zip_path.unlink()
    if not zip_path.is_file():
        print(f"Baixando {pin['url']} ({pin['bytes'] // (1 << 20)} MB)", flush=True)
        try:
            baixar(pin["url"], zip_path, agente="vbss-media-engine-navegador-setup")
        except OSError as err:
            falhar(f"nao consegui baixar o navegador fixo: {err}")
    obtido = sha256(zip_path)
    if obtido != pin["sha256"]:
        zip_path.unlink()
        falhar(f"SHA-256 do navegador nao confere (esperado {pin['sha256']}, veio {obtido}). Arquivo apagado.")
    linha("OK", "SHA-256 do zip do navegador confere", obtido)
    destino = _extrair(zip_path, pin, falhar)
    MARCA.write_text(json.dumps({"versao": pin["versao"], "sha256": pin["sha256"], "executavel_sha256": pin["executavel_sha256"]}, indent=2) + "\n", encoding="utf-8")
    zip_path.unlink()
    if not any(CACHE_DIR.iterdir()):
        CACHE_DIR.rmdir()
    linha("OK", "navegador fixo extraido (zip apagado depois de conferido)", str(destino))
    return executavel(pin)
