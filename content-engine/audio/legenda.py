import argparse
import difflib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
import pronuncia

MODELO_WHISPER = "deepdml/faster-whisper-large-v3-turbo-ct2"
WORKER = c.AUDIO_DIR / "legenda_worker.py"
PONTUACAO_FORTE = ".!?:;…"
FECHOS = "\"'”’)]»"
MAX_PALAVRAS = 4
MAX_CARACTERES = 32
PAUSA = 0.35
LETRAS_ORFA = 2
COBERTURA_MINIMA = 0.5
SILENCIO_DB = -35
SILENCIO_S = 0.18
TEXTOS_PADRAO = ("assets/voz/voz.json", "voz.json", "voz.txt", "vozes/voz.txt")
NUMERO_DA_FALA = re.compile(r"(\d+)(?=\.[^.]+$)")


def normalizar(texto):
    sem_acento = "".join(ch for ch in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in sem_acento if ch.isalnum())


def tokens_do_roteiro(texto, destaques=()):
    alvo = {normalizar(d) for d in destaques if normalizar(d)}
    palavras = []
    marcado = False
    for bruto in texto.split():
        destaque = marcado or "*" in bruto
        if bruto.count("*") % 2:
            marcado = not marcado
        limpo = bruto.replace("*", "")
        chave = normalizar(limpo)
        if not chave:
            if palavras and limpo:
                palavras[-1]["texto"] += " " + limpo
            continue
        palavras.append({"texto": limpo, "destaque": destaque or chave in alvo})
    return palavras


def _peso(palavra):
    return max(1, len(normalizar(palavra["texto"])))


def _repartir(tempos, roteiro, i1, i2, inicio, fim):
    fim = max(fim, inicio)
    pesos = [_peso(p) for p in roteiro[i1:i2]]
    total = sum(pesos)
    cursor = inicio
    for k, peso in enumerate(pesos):
        proximo = cursor + (fim - inicio) * peso / total
        tempos[i1 + k] = (cursor, proximo)
        cursor = proximo


def alinhar(roteiro, ouvidas, duracao):
    ouvidas = [o for o in ouvidas if normalizar(o["texto"])]
    a = [normalizar(p["texto"]) for p in roteiro]
    b = [normalizar(o["texto"]) for o in ouvidas]
    tempos = [None] * len(a)
    casadas = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                tempos[i1 + k] = (ouvidas[j1 + k]["inicio"], ouvidas[j1 + k]["fim"])
            casadas += i2 - i1
        elif op == "replace":
            _repartir(tempos, roteiro, i1, i2, ouvidas[j1]["inicio"], ouvidas[j2 - 1]["fim"])
    n = len(a)
    i = 0
    while i < n:
        if tempos[i] is not None:
            i += 1
            continue
        j = i
        while j < n and tempos[j] is None:
            j += 1
        inicio = tempos[i - 1][1] if i else 0.0
        fim = tempos[j][0] if j < n else duracao
        if fim - inicio >= 0.06 * (j - i):
            _repartir(tempos, roteiro, i, j, inicio, fim)
        else:
            de = i - 1 if i else i
            ate = j + 1 if j < n else j
            inicio = tempos[de][0] if i else 0.0
            fim = tempos[ate - 1][1] if j < n else max(duracao, inicio)
            _repartir(tempos, roteiro, de, ate, inicio, fim)
        i = j
    saida = []
    anterior = 0.0
    for inicio, fim in tempos:
        inicio = max(inicio, anterior)
        fim = max(fim, inicio + 0.02)
        saida.append((round(inicio, 3), round(fim, 3)))
        anterior = fim
    return saida, casadas


def _no_tempo(pos, trechos, fechando):
    for inicio, fim in trechos:
        d = fim - inicio
        if pos < d or (fechando and pos <= d + 1e-9):
            return inicio + pos
        pos -= d
    return trechos[-1][1]


def distribuir_em_trechos(roteiro, trechos):
    trechos = [(a, b) for a, b in trechos if b > a]
    if not roteiro or not trechos:
        return []
    falado = sum(b - a for a, b in trechos)
    pesos = [_peso(p) for p in roteiro]
    total = sum(pesos)
    tempos = []
    cursor = 0.0
    for peso in pesos:
        proximo = cursor + falado * peso / total
        inicio = _no_tempo(cursor, trechos, False)
        fim = max(_no_tempo(min(proximo, falado), trechos, True), inicio)
        tempos.append((round(inicio, 3), round(fim, 3)))
        cursor = proximo
    return tempos


def _fecha_frase(texto):
    return texto.rstrip(FECHOS)[-1:] in PONTUACAO_FORTE


def _curta(palavra):
    return len(normalizar(palavra["texto"])) <= LETRAS_ORFA


def _caracteres(palavras):
    return sum(len(p["texto"]) for p in palavras) + max(0, len(palavras) - 1)


def _trechos_de_frase(palavras, pausa):
    trechos = []
    atual = []
    for i, p in enumerate(palavras):
        atual.append(p)
        ultima = i == len(palavras) - 1
        if ultima or _fecha_frase(p["texto"]) or palavras[i + 1]["inicio"] - p["fim"] > pausa:
            trechos.append(atual)
            atual = []
    return trechos


def _blocos_do_trecho(trecho, max_palavras, max_caracteres):
    blocos = []
    atual = []
    for p in trecho:
        if atual and (len(atual) >= max_palavras or _caracteres(atual + [p]) > max_caracteres):
            sobra = []
            while len(atual) > 1 and _curta(atual[-1]):
                sobra.insert(0, atual.pop())
            blocos.append(atual)
            atual = sobra
        atual.append(p)
    if atual:
        blocos.append(atual)
    if len(blocos) > 1 and len(blocos[-1]) == 1:
        anterior = blocos[-2]
        k = 1
        while k < len(anterior) - 1 and _curta(anterior[-k - 1]):
            k += 1
        cabe = k + 1 <= max_palavras and _caracteres(anterior[-k:] + blocos[-1]) <= max_caracteres
        if len(anterior) - k >= 2 and not _curta(anterior[-k - 1]) and cabe:
            blocos[-1] = anterior[-k:] + blocos[-1]
            del anterior[-k:]
    return blocos


def quebrar_em_blocos(palavras, max_palavras=MAX_PALAVRAS, pausa=PAUSA, max_caracteres=MAX_CARACTERES):
    grupos = []
    for trecho in _trechos_de_frase(palavras, pausa):
        grupos.extend(_blocos_do_trecho(trecho, max_palavras, max_caracteres))
    i = 0
    while i < len(grupos) and len(grupos) > 1:
        g = grupos[i]
        if len(g) == 1 and _curta(g[0]):
            if i + 1 < len(grupos) and not _fecha_frase(g[0]["texto"]):
                grupos[i + 1] = g + grupos[i + 1]
            elif i:
                grupos[i - 1] = grupos[i - 1] + g
            else:
                grupos[i + 1] = g + grupos[i + 1]
            grupos.pop(i)
            continue
        i += 1
    return [{"inicio": g[0]["inicio"], "fim": g[-1]["fim"], "palavras": g} for g in grupos]


def deslocar(blocos, t):
    saida = []
    for b in blocos:
        palavras = []
        for p in b["palavras"]:
            item = {"texto": p["texto"], "inicio": round(p["inicio"] + t, 3), "fim": round(p["fim"] + t, 3)}
            if p.get("destaque"):
                item["destaque"] = True
            palavras.append(item)
        saida.append({"inicio": palavras[0]["inicio"], "fim": palavras[-1]["fim"], "palavras": palavras})
    return saida


def trechos_de_fala(arquivo, duracao):
    r = c.ffmpeg(["-i", str(arquivo), "-af", f"silencedetect=noise={SILENCIO_DB}dB:d={SILENCIO_S}", "-f", "null", "-"])
    inicios = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", r.stderr)]
    fins = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", r.stderr)]
    trechos = []
    cursor = 0.0
    for k, inicio in enumerate(inicios):
        inicio = max(0.0, inicio)
        if inicio > cursor:
            trechos.append((cursor, inicio))
        cursor = fins[k] if k < len(fins) else duracao
    if cursor < duracao:
        trechos.append((cursor, duracao))
    return trechos or [(0.0, duracao)]


def _voicestudio():
    from providers import voicestudio

    return voicestudio._vs()


def whisper_disponivel():
    try:
        vs = _voicestudio()
    except Exception as err:
        return None, f"voicestudio/voicestudio.py nao carregou ({type(err).__name__}: {err})"
    if not vs.VENV_PY.is_file():
        return None, "VoiceStudio nao instalado (python voicestudio/voicestudio.py instalar)"
    pasta = vs.MODELOS / f"models--{MODELO_WHISPER.replace('/', '--')}" / "snapshots"
    modelos = sorted(p for p in pasta.glob("*") if (p / "model.bin").is_file()) if pasta.is_dir() else []
    if not modelos:
        return None, f"modelo {MODELO_WHISPER} nao baixado (python voicestudio/voicestudio.py modelos)"
    return (vs, modelos[-1]), f"faster-whisper do venv do VoiceStudio, modelo {MODELO_WHISPER} ({modelos[-1].name[:8]})"


def transcrever(arquivos, threads=4):
    achado, motivo = whisper_disponivel()
    if not achado:
        raise RuntimeError(motivo)
    vs, modelo = achado
    env = vs.ambiente(False)
    env.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "CT2_VERBOSE": "0"})
    tarefa = {"modelo": str(modelo), "idioma": "pt", "threads": threads, "itens": [{"arquivo": str(a)} for a in arquivos]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=str(vs.TMP), encoding="utf-8") as f:
        json.dump(tarefa, f, ensure_ascii=False)
        caminho = f.name
    try:
        r = subprocess.run([str(vs.VENV_PY), "-I", "-B", str(WORKER), caminho], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, cwd=str(vs.TMP), timeout=3600)
    finally:
        Path(caminho).unlink(missing_ok=True)
    linhas = [ln for ln in r.stdout.splitlines() if ln.strip().startswith("{")]
    if r.returncode != 0 or not linhas:
        raise RuntimeError("o Whisper local falhou:\n" + (r.stderr or r.stdout)[-1500:])
    return json.loads(linhas[-1])


def achar_texto(comp_dir, informado):
    if informado:
        caminho = Path(informado)
        if not caminho.is_file():
            caminho = comp_dir / informado
        if not caminho.is_file():
            c.falhar(f"texto das falas nao encontrado: {informado}")
        return caminho.resolve()
    for rel in TEXTOS_PADRAO:
        if (comp_dir / rel).is_file():
            return (comp_dir / rel).resolve()
    c.falhar("nao achei o texto das falas. Passe --texto <voz.txt | voz.json | roteiro.md> (procurei: " + ", ".join(TEXTOS_PADRAO) + ")")


def ler_textos(caminho):
    if caminho.suffix.lower() == ".json":
        dados = c.ler_json(caminho)
        linhas = dados.get("linhas") if isinstance(dados, dict) else None
        if not linhas:
            c.falhar(f"{caminho} nao tem a lista 'linhas' do voz.json")
        por_arquivo = {Path(x["arquivo"]).name: x["texto"] for x in linhas if x.get("arquivo") and x.get("texto")}
        por_batida = {int(x["batida"]): x["texto"] for x in linhas if x.get("batida") is not None and x.get("texto")}
        return por_arquivo, por_batida
    import voz

    return {}, {int(batida): fala for batida, fala, _ in voz.ler_entrada(caminho)}


def texto_da_deixa(arquivo, ordem, por_arquivo, por_batida):
    nome = Path(arquivo).name
    if nome in por_arquivo:
        return por_arquivo[nome]
    achou = NUMERO_DA_FALA.search(nome)
    if achou and nome.lower().startswith("voz") and int(achou.group(1)) in por_batida:
        return por_batida[int(achou.group(1))]
    if not achou and ordem in por_batida:
        return por_batida[ordem]
    return None


def escrever_js(destino, blocos):
    corpo = json.dumps(blocos, ensure_ascii=False, separators=(",", ":"))
    Path(destino).write_text(f"window.__legenda = {corpo};\n", encoding="utf-8", newline="\n")


def main():
    p = argparse.ArgumentParser(description="Gera a legenda sincronizada com a fala (legenda.json e legenda.js na composicao) com o Whisper local do VoiceStudio. Nada sai da maquina.")
    p.add_argument("composicao", help="pasta da composicao (com index.html e os WAVs de voz)")
    p.add_argument("--trilha", help="trilha.json com as deixas de voz (padrao: <composicao>/trilha.json)")
    p.add_argument("--texto", help="texto das falas: voz.json do voz.py, voz.txt (uma fala por linha) ou roteiro.md; *palavra* marca destaque")
    p.add_argument("--destaque", default="", help="palavras de destaque separadas por virgula, ex.: \"preço,versão\"")
    p.add_argument("--max-palavras", type=int, default=MAX_PALAVRAS)
    p.add_argument("--max-caracteres", type=int, default=MAX_CARACTERES)
    p.add_argument("--pausa", type=float, default=PAUSA, help="pausa (s) entre palavras que fecha o bloco")
    p.add_argument("--threads", type=int, default=4, help="threads de CPU do Whisper")
    p.add_argument("--sem-whisper", action="store_true", help="usa so o plano B (trechos de fala por silencio, tempo proporcional aos caracteres)")
    p.add_argument("--detalhe", action="store_true", help="mostra o tempo de cada palavra")
    a = p.parse_args()

    comp_dir = Path(a.composicao).resolve()
    if not comp_dir.is_dir():
        c.falhar(f"{comp_dir} nao e uma pasta")
    c.exigir_ffmpeg()
    trilha = Path(a.trilha).resolve() if a.trilha else comp_dir / "trilha.json"
    if not trilha.is_file():
        c.falhar(f"trilha nao encontrada: {trilha}")
    origem_texto = achar_texto(comp_dir, a.texto)
    por_arquivo, por_batida = ler_textos(origem_texto)
    destaques = [d.strip() for d in a.destaque.split(",") if d.strip()]

    falas = []
    com_arquivo = sorted((d for d in c.ler_json(trilha).get("deixas", []) if d.get("arquivo")), key=lambda d: float(d.get("t", 0)))
    for ordem, deixa in enumerate(com_arquivo, 1):
        texto = texto_da_deixa(deixa["arquivo"], ordem, por_arquivo, por_batida)
        if texto is None:
            c.linha("INFO", f"{deixa['arquivo']} sem texto correspondente", "fica fora da legenda")
            continue
        wav = comp_dir / deixa["arquivo"]
        if not wav.is_file():
            c.falhar(f"arquivo de voz ausente: {wav}")
        falas.append({"arquivo": deixa["arquivo"], "t": float(deixa.get("t", 0)), "wav": wav, "texto": texto,
                      "roteiro": tokens_do_roteiro(texto, destaques), "duracao": c.duracao(wav)})
    if not falas:
        c.falhar("nenhuma deixa de voz com texto correspondente na trilha")

    c.titulo(f"Legenda: {len(falas)} fala(s), texto de {c.rel(origem_texto)}")
    ouvidas = {}
    if a.sem_whisper:
        c.linha("INFO", "Whisper desligado (--sem-whisper)", "tempos pelo plano B")
    else:
        _, motivo = whisper_disponivel()
        try:
            res = transcrever([f["wav"] for f in falas], threads=a.threads)
            ouvidas = {Path(it["arquivo"]): it["palavras"] for it in res["itens"]}
            c.linha("OK", "Whisper local", f"{motivo}; carga {res['carga_s']} s, transcricao {sum(it['transcricao_s'] for it in res['itens']):.1f} s")
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as err:
            c.linha("AVISO", "Whisper local indisponivel, tempos pelo plano B", str(err).strip().splitlines()[-1] if str(err).strip() else type(err).__name__)

    blocos = []
    relato = []
    for f in falas:
        palavras_ouvidas = ouvidas.get(f["wav"], [])
        metodo = "silencio"
        casadas = 0
        tempos = []
        if palavras_ouvidas:
            tempos, casadas = alinhar(f["roteiro"], palavras_ouvidas, f["duracao"])
            if casadas / len(f["roteiro"]) >= COBERTURA_MINIMA:
                metodo = "whisper"
        if metodo == "silencio":
            tempos = distribuir_em_trechos(f["roteiro"], trechos_de_fala(f["wav"], f["duracao"]))
        palavras = [{**p, "inicio": ini, "fim": fim} for p, (ini, fim) in zip(f["roteiro"], tempos)]
        da_fala = deslocar(quebrar_em_blocos(palavras, a.max_palavras, a.pausa, a.max_caracteres), f["t"])
        blocos.extend(da_fala)
        relato.append({"arquivo": f["arquivo"], "t": f["t"], "duracao_s": round(f["duracao"], 3), "texto": f["texto"].replace("*", ""),
                       "metodo": metodo, "palavras": len(palavras), "casadas_com_o_whisper": casadas,
                       "ouvido": " ".join(o["texto"] for o in palavras_ouvidas) or None})
        status = "OK" if metodo == "whisper" else "AVISO"
        c.linha(status, f["arquivo"], f"{metodo}: {casadas}/{len(palavras)} palavras casadas, {len(da_fala)} bloco(s): " + " | ".join(" ".join(x["texto"] for x in b["palavras"]) for b in da_fala))
        if palavras_ouvidas:
            conferida = pronuncia.conferir_fala(f["wav"], f["texto"], palavras_ouvidas)
            relato[-1]["pronuncia"] = {"ok": conferida["ok"], "divergencias": [pronuncia.descrever(d) for d in conferida["divergencias"]]}
            for d in relato[-1]["pronuncia"]["divergencias"]:
                c.linha("AVISO", f"PRONUNCIA em {f['arquivo']}", d)
        if a.detalhe:
            for b in da_fala:
                for x in b["palavras"]:
                    print(f"     {x['inicio']:7.3f} - {x['fim']:7.3f}  {x['texto']}{'  *' if x.get('destaque') else ''}")

    dados = {"versao": 1, "origem_do_texto": c.rel(origem_texto), "max_palavras": a.max_palavras, "pausa_s": a.pausa,
             "duracao_s": round(max(b["fim"] for b in blocos), 3), "falas": relato, "blocos": blocos}
    c.escrever_json(comp_dir / "legenda.json", dados)
    escrever_js(comp_dir / "legenda.js", blocos)
    c.titulo("Resultado")
    c.linha("OK", f"{len(blocos)} bloco(s), {sum(len(b['palavras']) for b in blocos)} palavra(s)", f"{c.rel(comp_dir / 'legenda.json')} e legenda.js (window.__legenda)")
    divergentes = [r["arquivo"] for r in relato if r.get("pronuncia") and not r["pronuncia"]["ok"]]
    if divergentes:
        c.linha("AVISO", f"a voz nao disse o texto como esta escrito em {len(divergentes)} fala(s)", "OUCA e gere de novo antes do render (voz.py --batidas N): " + ", ".join(divergentes))
    elif any(r.get("pronuncia") for r in relato):
        c.linha("OK", "pronuncia conferida", "o que o Whisper ouviu bate com o texto em todas as falas")
    if any(r["metodo"] != "whisper" for r in relato):
        c.linha("AVISO", "fala(s) com tempo estimado pelo plano B", "confira a legenda no preview antes do render")
    print('   Na composicao: <script src="legenda.js"></script> e K.legenda("#legenda", window.__legenda)')


if __name__ == "__main__":
    main()
