import json
import sys
import time


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        tarefa = json.load(f)
    from faster_whisper import WhisperModel

    t0 = time.perf_counter()
    modelo = WhisperModel(tarefa["modelo"], device="cpu", compute_type=tarefa.get("computacao", "int8"),
                          cpu_threads=tarefa.get("threads", 4), local_files_only=True)
    carga = time.perf_counter() - t0
    itens = []
    for item in tarefa["itens"]:
        t = time.perf_counter()
        segmentos, _ = modelo.transcribe(item["arquivo"], language=tarefa.get("idioma", "pt"), word_timestamps=True,
                                         condition_on_previous_text=False, vad_filter=False, beam_size=5, temperature=0.0)
        palavras = []
        for seg in segmentos:
            for w in seg.words or []:
                palavras.append({"texto": w.word.strip(), "inicio": round(float(w.start), 3), "fim": round(float(w.end), 3),
                                 "prob": round(float(w.probability), 3)})
        itens.append({"arquivo": item["arquivo"], "palavras": palavras, "transcricao_s": round(time.perf_counter() - t, 3)})
    print(json.dumps({"carga_s": round(carga, 3), "itens": itens}), flush=True)


if __name__ == "__main__":
    main()
