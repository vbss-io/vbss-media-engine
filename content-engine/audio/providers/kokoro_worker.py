import json
import os
import sys
import time
import wave
from pathlib import Path


def gravar_wav(caminho, amostras, taxa):
    import numpy as np

    pcm = (np.clip(amostras, -1.0, 1.0) * 32767.0).round().astype("<i2")
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(pcm.tobytes())


def pico_memoria_mb():
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Contadores(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    cont = Contadores()
    cont.cb = ctypes.sizeof(Contadores)
    atual = ctypes.windll.kernel32.GetCurrentProcess
    atual.restype = wintypes.HANDLE
    info = ctypes.windll.psapi.GetProcessMemoryInfo
    info.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if not info(atual(), ctypes.byref(cont), cont.cb):
        return None
    return round(cont.PeakWorkingSetSize / (1 << 20))


def main():
    tarefa = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    inicio = time.perf_counter()
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(tarefa["modelo"], tarefa["vozes"])
    carga = time.perf_counter() - inicio
    if tarefa.get("listar"):
        print(json.dumps({"carga_s": round(carga, 3), "vozes": kokoro.get_voices()}))
        return
    itens = []
    for linha in tarefa["linhas"]:
        t0 = time.perf_counter()
        amostras, taxa = kokoro.create(linha["texto"], voice=tarefa["voz"], speed=float(tarefa["velocidade"]), lang=tarefa["idioma"])
        gasto = time.perf_counter() - t0
        gravar_wav(linha["saida"], amostras, taxa)
        itens.append({"saida": linha["saida"], "sintese_s": round(gasto, 3), "audio_s": round(len(amostras) / taxa, 3)})
    print(json.dumps({"carga_s": round(carga, 3), "pico_memoria_mb": pico_memoria_mb(), "itens": itens}))


if __name__ == "__main__":
    main()
