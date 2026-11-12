import hashlib
import json
from pathlib import Path

FONTES_DIR = Path(__file__).resolve().parent.parent / "fontes"
MANIFESTO = FONTES_DIR / "fontes.json"


def manifesto():
    return json.loads(MANIFESTO.read_text(encoding="utf-8"))


def arquivos():
    return {nome: FONTES_DIR / nome for nome in manifesto()["arquivos"]}


def conferir():
    if not MANIFESTO.is_file():
        return [f"{MANIFESTO} ausente"]
    problemas = []
    for nome, info in manifesto()["arquivos"].items():
        arq = FONTES_DIR / nome
        if not arq.is_file():
            problemas.append(f"{nome} ausente")
        elif hashlib.sha256(arq.read_bytes()).hexdigest() != info["sha256"]:
            problemas.append(f"{nome} com SHA-256 diferente do fontes.json")
    return problemas
