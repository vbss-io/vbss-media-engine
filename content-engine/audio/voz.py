import argparse
import ctypes
import os
import platform
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
import providers

CONFIG = c.AUDIO_DIR / "voz_config.json"
COLUNAS_VOZ = ("voz", "narracao", "narração", "fala")
COLUNAS_ESTILO = ("estilo", "tom")
PREFIXO_ESTILO = re.compile(r"^\[([^\]\s][^\]]*)\]\s*(.+)$")
FRASES_BENCHMARK = [
    "Como funciona o cadastro? Veja em três passos.",
    "Digite o nome do produto na busca e confira o resultado, montado com os dados mais recentes do sistema.",
    "O item entra na sua lista com nome, categoria e a data de atualização, e você confere o histórico completo de mudanças sempre que quiser.",
]
FRASE_AQUECIMENTO = "Teste de aquecimento."


def config():
    return c.config_de_voz(CONFIG)


def linhas_de_tabela(texto):
    linhas = [ln.strip() for ln in texto.splitlines()]
    for i, ln in enumerate(linhas):
        if not (ln.startswith("|") and i + 1 < len(linhas) and re.fullmatch(r"\|[\s:|-]+\|", linhas[i + 1] or "")):
            continue
        cab = [x.strip().lower() for x in ln.strip("|").split("|")]
        col = next((j for j, nome in enumerate(cab) if nome in COLUNAS_VOZ), None)
        col_estilo = next((j for j, nome in enumerate(cab) if nome in COLUNAS_ESTILO), None)
        if col is None:
            continue
        falas = []
        for n, corpo in enumerate(linhas[i + 2:], 1):
            if not corpo.startswith("|"):
                break
            celulas = [x.strip() for x in corpo.strip("|").split("|")]
            batida = int(celulas[0]) if celulas and celulas[0].isdigit() else n
            if col < len(celulas) and celulas[col] not in ("", "-"):
                estilo = celulas[col_estilo] if col_estilo is not None and col_estilo < len(celulas) and celulas[col_estilo] not in ("", "-") else None
                falas.append((batida, celulas[col], estilo))
        return falas
    return None


def ler_entrada(caminho):
    texto = Path(caminho).read_text(encoding="utf-8")
    if Path(caminho).suffix.lower() == ".md":
        falas = linhas_de_tabela(texto)
        if falas is None:
            c.falhar(f"{caminho} nao tem tabela com coluna 'Voz' (ou 'Narração'). Use um .txt com uma fala por linha.")
        return falas
    validas = [ln.strip() for ln in texto.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    falas = []
    for n, ln in enumerate(validas, 1):
        achou = PREFIXO_ESTILO.match(ln)
        falas.append((n, achou.group(2), achou.group(1).strip()) if achou else (n, ln, None))
    return falas


def pos_processar(bruto, destino, cfg):
    limiar = -50
    inter = destino.with_name(destino.stem + "-float.wav")
    filtros = [
        "aformat=sample_fmts=flt",
        "pan=mono|c0=c0",
        f"aresample={cfg['taxa_saida']}",
        f"silenceremove=start_periods=1:start_threshold={limiar}dB",
        f"areverse,silenceremove=start_periods=1:start_threshold={limiar}dB,areverse",
        "acompressor=threshold=0.063:ratio=3:attack=5:release=80",
    ]
    r = c.ffmpeg(["-y", "-i", str(bruto), "-af", ",".join(filtros), "-c:a", "pcm_f32le", "-fflags", "+bitexact", "-map_metadata", "-1", str(inter)])
    if r.returncode != 0:
        c.falhar(f"ffmpeg falhou tratando {bruto}: {r.stderr[-400:]}")
    m = c.medir(inter)
    alvo = m["lufs_integrado"] if m["lufs_integrado"] is not None else m["lufs_momentaneo_max"]
    ganho = round(cfg["alvo_lufs"] - alvo, 1)
    teto = 10 ** ((cfg["teto_pico_dbtp"] - 0.5) / 20)
    r = c.ffmpeg(["-y", "-i", str(inter), "-af", f"volume={ganho}dB,alimiter=limit={teto:.4f}:attack=3:release=50:level=disabled:latency=1", "-c:a", "pcm_s16le", "-ar", str(cfg["taxa_saida"]), "-ac", "1",
                  "-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1", str(destino)])
    inter.unlink(missing_ok=True)
    if r.returncode != 0:
        c.falhar(f"ffmpeg falhou gravando {destino}: {r.stderr[-400:]}")
    final = c.medir(destino)
    return ganho, final


def escolher(a, cfg):
    nome = a.provedor or cfg["provedor"]
    try:
        prov = providers.carregar(nome)
        if a.modelo is not None:
            aceitas = providers.variantes_de(nome)
            if a.modelo not in aceitas:
                c.falhar(f"--modelo {a.modelo} nao existe no provedor {nome}" + (f" (use {', '.join(aceitas)})" if aceitas else " (ele nao tem variantes de modelo)"))
    except (providers.ProvedorIndisponivel, ValueError) as err:
        veio_do_env = not a.provedor and cfg.get("origem", {}).get("provedor") == ".env"
        c.falhar(str(err) + (f" - confira {c.ENV_PROVEDOR} no content-engine/audio/.env" if veio_do_env else ""))
    voz = a.voz or cfg["vozes_padrao"].get(nome) or prov.VOZ_PADRAO
    vel = a.velocidade if a.velocidade is not None else cfg["velocidade"]
    return nome, prov, voz, vel


def listar_vozes(cfg):
    for nome in providers.DISPONIVEIS:
        prov, erro = providers.tentar_carregar(nome)
        if prov is None:
            c.titulo(f"{nome} - indisponivel: {erro}")
            continue
        try:
            ok, motivo = prov.disponivel()
        except Exception as err:
            ok, motivo = False, f"erro ao conferir o provedor ({type(err).__name__}: {err})"
        c.titulo(f"{nome} ({'local' if prov.LOCAL else 'nuvem'}) - {'pronto' if ok else 'indisponivel'}: {motivo}")
        print(f"   {prov.DESCRICAO}")
        padrao = cfg["vozes_padrao"].get(nome)
        instaladas = None
        resumo = None
        if ok and hasattr(prov, "conferir_vozes"):
            try:
                instaladas, resumo = prov.conferir_vozes()
            except RuntimeError as err:
                print(f"   (nao consegui ler as vozes do modelo: {err})")
        grupos = None
        if ok and hasattr(prov, "listar_vozes_vivo"):
            try:
                grupos = prov.listar_vozes_vivo()
                print("   vozes pt-BR nativas lidas ao vivo no servico:")
            except RuntimeError as err:
                print(f"   (nao consegui ler a lista ao vivo: {err}; mostrando a lista curada)")
        if grupos is not None:
            for nome_grupo, vozes in grupos:
                print(f"   {nome_grupo}:")
                for v in vozes:
                    marca = " [padrao]" if v["id"] == padrao else ""
                    print(f"   - {v['id']}{marca}: {v['genero']}, {v['nota']}")
        else:
            sufixo = "" if prov.LOCAL or ok else " [sem chave]"
            if sufixo:
                print("   lista curada (nao conferida ao vivo):")
            for v in prov.VOZES:
                marca = " [padrao]" if v["id"] == padrao else ""
                conf = ""
                if instaladas is not None:
                    conf = " (no modelo)" if v["id"] in instaladas else " (NAO encontrada no modelo)"
                print(f"   - {v['id']}{marca}: {v['genero']}, {v['idioma']}, {v['nota']}{conf}{sufixo}")
        aceitas = getattr(prov, "OPCOES_ACEITAS", ())
        if aceitas:
            print(f"   opcoes de interpretacao aceitas: {', '.join('--' + x for x in aceitas if x != 'estilos')} (e coluna Estilo por batida)")
        if instaladas:
            print(f"   {resumo}")
        try:
            variantes = providers.variantes_de(nome)
        except providers.ProvedorIndisponivel as err:
            print(f"   ({err})")
            variantes = ()
        if variantes:
            print(f"   variantes de modelo (--modelo): {', '.join(variantes)}")


def memoria_gb():
    if os.name != "nt":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]

    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    return round(st.ullTotalPhys / (1 << 30), 1)


def benchmark(a, cfg):
    nome, prov, voz, vel = escolher(a, cfg)
    ok, motivo = prov.disponivel(a.modelo)
    if not ok:
        c.falhar(f"{nome} indisponivel: {motivo}")
    pasta = c.WORK_DIR / "benchmark" / datetime.now().strftime("%Y%m%d-%H%M%S")
    pasta.mkdir(parents=True, exist_ok=True)
    c.titulo(f"Benchmark {nome} ({motivo}), voz {voz}")
    maquina = {
        "cpu": os.environ.get("PROCESSOR_IDENTIFIER") or platform.processor(),
        "nucleos_logicos": os.cpu_count(),
        "ram_gb": memoria_gb(),
        "sistema": platform.platform(),
    }
    print(f"   maquina: {maquina['cpu']}, {maquina['nucleos_logicos']} nucleos logicos, {maquina['ram_gb']} GB RAM")
    t0 = time.perf_counter()
    res = prov.sintetizar([FRASE_AQUECIMENTO, *FRASES_BENCHMARK], voz, pasta, velocidade=vel, variante=a.modelo)
    total = time.perf_counter() - t0
    medidos = res["itens"][1:]
    for it in medidos:
        if it["audio_s"] is None:
            it["audio_s"] = c.duracao(it["arquivo"])
    sint = sum(it["sintese_s"] for it in medidos)
    aud = sum(it["audio_s"] for it in medidos)
    rtf = sint / aud if aud else None
    print(f"   carga do modelo (import + leitura do arquivo): {res['carga_s']:.2f} s   (processo inteiro, com abertura do Python: {total:.2f} s)")
    if res.get("pico_memoria_mb"):
        print(f"   pico de memoria do processo de voz: {res['pico_memoria_mb']} MB")
    print(f"   aquecimento: {res['itens'][0]['sintese_s']:.2f} s para {res['itens'][0]['audio_s'] or 0:.2f} s de audio (fora da media)")
    for frase, it in zip(FRASES_BENCHMARK, medidos):
        print(f"   {len(frase):4d} caracteres: {it['sintese_s']:.2f} s para {it['audio_s']:.2f} s de audio (RTF {it['sintese_s'] / it['audio_s']:.3f})")
    print(f"   fator de tempo real (sintese / duracao do audio): {rtf:.3f}  ({'mais rapido' if rtf < 1 else 'mais lento'} que o tempo real)")
    c.escrever_json(pasta / "benchmark.json", {
        "provedor": nome, "modelo": res["modelo"], "voz": voz, "velocidade": vel, "maquina": maquina,
        "carga_modelo_s": res["carga_s"], "pico_memoria_mb": res.get("pico_memoria_mb"), "processo_total_s": round(total, 3), "fator_tempo_real": round(rtf, 4) if rtf else None,
        "frases": [{"texto": f, **{k: v for k, v in it.items() if k != "arquivo"}} for f, it in zip(FRASES_BENCHMARK, medidos)],
    })
    c.linha("OK", "resultado salvo", c.rel(pasta / "benchmark.json"))


def gerar(a, cfg):
    nome, prov, voz, vel = escolher(a, cfg)
    if a.texto:
        falas = [(1, a.texto.strip(), None)]
        origem = "--texto"
    elif a.entrada:
        falas = ler_entrada(a.entrada)
        origem = c.rel(a.entrada)
    else:
        c.falhar("diga o que falar: um arquivo (voz.txt com uma fala por linha, ou roteiro.md com coluna 'Voz') ou --texto")
    if not falas:
        c.falhar("nenhuma fala encontrada na entrada")
    if not a.saida:
        c.falhar("diga a pasta de saida com --saida")
    ok, motivo = prov.disponivel(a.modelo)
    if not ok:
        c.falhar(f"provedor {nome} indisponivel: {motivo}")
    opcoes = {"estilo": a.estilo, "tom": a.tom, "altura": a.altura}
    _, rejeitadas = providers.filtrar_opcoes(prov, opcoes)
    if rejeitadas:
        c.falhar(f"o provedor {nome} nao aceita {', '.join('--' + x for x in rejeitadas)}" + (f" (aceita: {', '.join('--' + x for x in prov.OPCOES_ACEITAS if x != 'estilos')})" if getattr(prov, "OPCOES_ACEITAS", ()) else " (ele nao tem opcoes de interpretacao)"))
    estilos = [e for _, _, e in falas]
    if any(estilos):
        opcoes["estilos"] = estilos
        if "estilos" not in getattr(prov, "OPCOES_ACEITAS", ()):
            c.linha("AVISO", f"coluna Estilo ignorada: o provedor {nome} nao tem estilo por batida")
    c.exigir_ffmpeg()
    saida = Path(a.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    for antigo in saida.glob("voz-*.wav"):
        antigo.unlink()
    bruto = c.WORK_DIR / "voz-bruto" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    bruto.mkdir(parents=True, exist_ok=True)

    c.titulo(f"Voz: {nome} ({'local' if prov.LOCAL else 'nuvem'}), voz {voz}, velocidade {vel}, {len(falas)} fala(s)")
    t0 = time.perf_counter()
    try:
        res = providers.sintetizar(prov, [t for _, t, _ in falas], voz, bruto, velocidade=vel, variante=a.modelo, opcoes=opcoes)
    except RuntimeError as err:
        c.falhar(str(err))
    gasto = time.perf_counter() - t0
    linhas = []
    for (batida, fala, _), it in zip(falas, res["itens"]):
        destino = saida / f"voz-{batida:02d}.wav"
        ganho, m = pos_processar(Path(it["arquivo"]), destino, cfg)
        linha = {"batida": batida, "texto": fala, "caracteres": len(fala), "arquivo": destino.name, "duracao_s": m["duracao"],
                 "lufs": m["lufs_integrado"], "pico_dbtp": m["pico_dbtp"], "ganho_db": ganho}
        for extra in ("estilo", "tom", "transcricao", "tokens", "tentativas"):
            if it.get(extra) is not None:
                linha[extra] = it[extra]
        linhas.append(linha)
        c.linha("OK", destino.name, f"{m['duracao']:.2f} s  {m['lufs_integrado']} LUFS  pico {m['pico_dbtp']} dBTP  \"{fala[:60]}\"")
    shutil.rmtree(bruto, ignore_errors=True)
    dur = round(sum(x["duracao_s"] for x in linhas), 3)
    sintese = sum(it["sintese_s"] for it in res["itens"])
    dados = {
        "provedor": nome,
        "local": prov.LOCAL,
        "voz": voz,
        "modelo": res["modelo"],
        "idioma": "pt-BR",
        "velocidade": vel,
        "opcoes": {k: v for k, v in {"estilo": a.estilo, "tom": a.tom, "altura": a.altura}.items() if v},
        "entrada": origem,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "total_caracteres": sum(x["caracteres"] for x in linhas),
        "duracao_total_s": dur,
        "carga_modelo_s": res["carga_s"],
        "sintese_s": round(sintese, 3),
        "processo_total_s": round(gasto, 3),
        "fator_tempo_real": round(sintese / dur, 4) if dur else None,
        "alvo_lufs": cfg["alvo_lufs"],
        "linhas": linhas,
    }
    if any(x.get("tokens") for x in linhas):
        dados["tokens_total"] = sum((x.get("tokens") or {}).get("total") or 0 for x in linhas)
    c.escrever_json(saida / "voz.json", dados)
    c.titulo("Resultado")
    c.linha("OK", f"{len(linhas)} arquivo(s) em {c.rel(saida)}", f"{dur:.2f} s de fala, {dados['total_caracteres']} caracteres, RTF {dados['fator_tempo_real']}")


def main():
    c.carregar_env_voz()
    p = argparse.ArgumentParser(description="Gera narracao (um WAV por batida + voz.json) pelo provedor escolhido (" + ", ".join(providers.DISPONIVEIS) + "). Chave de nuvem no content-engine/audio/.env (ignorado pelo git) ou em variavel de ambiente.")
    p.add_argument("entrada", nargs="?", help="voz.txt (uma fala por linha) ou roteiro.md com coluna 'Voz'")
    p.add_argument("--texto", help="uma fala direta, no lugar do arquivo")
    p.add_argument("--saida", help="pasta onde ficam voz-01.wav, voz-02.wav... e voz.json")
    p.add_argument("--provedor", choices=providers.DISPONIVEIS, help="padrao: VOZ_PROVEDOR no content-engine/audio/.env ou voz_config.json")
    p.add_argument("--voz", help="id da voz (veja --listar-vozes; padrao: VOZ_<PROVEDOR> no .env, como VOZ_AZURE, ou voz_config.json)")
    p.add_argument("--velocidade", type=float, help="1.0 = normal; 1.1 = 10%% mais rapido")
    p.add_argument("--modelo", help="variante do modelo, so para provedor que tem variantes (veja --listar-vozes; padrao definido pelo provedor)")
    p.add_argument("--estilo", help="estilo da fala, so nos provedores que aceitam (ex.: excited, happy, calm); uma coluna Estilo na batida vale so para ela")
    p.add_argument("--tom", help="instrucao de tom em texto livre, so nos provedores que aceitam (ex.: \"animado, de locutor de Reels\")")
    p.add_argument("--altura", help="altura da voz, so nos provedores que aceitam (ex.: +2st, -5%%, high)")
    p.add_argument("--listar-vozes", action="store_true", help="lista provedores, vozes e o que esta pronto nesta maquina")
    p.add_argument("--benchmark", action="store_true", help="mede carga do modelo e fator de tempo real nesta maquina")
    a = p.parse_args()
    cfg = config()
    if a.listar_vozes:
        listar_vozes(cfg)
    elif a.benchmark:
        benchmark(a, cfg)
    else:
        gerar(a, cfg)


if __name__ == "__main__":
    main()
