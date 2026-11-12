import argparse
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
import catalogo_audio
import provedores
import voz

LISTA_PADRAO = c.AUDIO_DIR / "comparacao_vozes.json"
ENTRADA_PADRAO = c.REPO_DIR / "exemplos" / "narracao" / "voz.txt"
SAIDA_PADRAO = c.WORK_DIR / "vozes-comparacao"
TITULO_PADRAO = "Comparação de vozes"
NOMES_PROVEDOR = {"kokoro": "Kokoro local", "azure": "Azure Speech", "azure_openai": "Azure OpenAI gpt-audio", "google": "Google TTS"}


def slug(texto):
    sem = "".join(ch for ch in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", sem.lower()).strip("-") or "voz"


def primeira_fala(caminho):
    for ln in Path(caminho).read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            achou = voz.PREFIXO_ESTILO.match(ln)
            return achou.group(2) if achou else ln
    c.falhar(f"{caminho} nao tem nenhuma fala")


def custo(entrada, caracteres, tokens):
    prov, nome = entrada["provedor"], entrada.get("voz", "")
    if prov == "kokoro":
        return "zero (roda na maquina)", 0.0
    if prov == "azure":
        if "MAI-Voice" in nome:
            return "a confirmar: preco do MAI-Voice 2.1 nao publicado", None
        if "DragonHD" in nome:
            return "estimativa assumindo a faixa Neural HD, US$ 22 por 1 milhao de caracteres (preco do Dragon HD nao conferido; azure.microsoft.com/en-us/pricing/details/speech/, 2026-10-08)", round(caracteres * 22 / 1e6, 6)
        return "Neural, US$ 15 por 1 milhao de caracteres (azure.microsoft.com/en-us/pricing/details/speech/, 2026-10-08)", round(caracteres * 15 / 1e6, 6)
    if prov == "azure_openai":
        usado = f"{tokens['total']} tokens nesta fala; " if tokens and tokens.get("total") else ""
        return usado + "cobrado por tokens de audio: conferir na pagina de precos do Azure OpenAI", None
    if prov == "google":
        return "Chirp 3 HD, US$ 30 por 1 milhao de caracteres, 1 milhao gratis por mes (cloud.google.com/text-to-speech/pricing, 2026-10-08)", round(caracteres * 30 / 1e6, 6)
    return "preco nao catalogado", None


def validar_lista(dados):
    if not isinstance(dados.get("vozes"), list) or not dados["vozes"]:
        c.falhar("a lista de vozes precisa de {\"vozes\": [{\"id\", \"rotulo\", \"provedor\", \"voz\", ...}]}")
    vistos = set()
    for e in dados["vozes"]:
        for campo in ("id", "rotulo", "provedor", "voz"):
            if not e.get(campo):
                c.falhar(f"entrada sem '{campo}' na lista de vozes: {e}")
        if e["provedor"] not in provedores.DISPONIVEIS:
            c.falhar(f"entrada {e['id']}: provedor '{e['provedor']}' desconhecido (use {', '.join(provedores.DISPONIVEIS)})")
        if e["id"] in vistos:
            c.falhar(f"id repetido na lista de vozes: {e['id']}")
        vistos.add(e["id"])
    return dados["vozes"]


def avaliar(entrada, cache):
    nome = entrada["provedor"]
    if nome not in cache:
        cache[nome] = provedores.tentar_carregar(nome)
    prov, erro = cache[nome]
    if prov is None:
        return None, f"adaptador nao carregou: {erro}"
    try:
        ok, motivo = prov.disponivel(entrada.get("modelo"))
    except Exception as err:
        return None, f"erro ao conferir o provedor ({type(err).__name__}: {err})"
    return (prov, None) if ok else (None, motivo)


def gerar_uma(prov, entrada, frase, pasta_falas, bruto, numero, cfg, velocidade):
    opcoes = {"estilo": entrada.get("estilo"), "tom": entrada.get("tom"), "altura": entrada.get("altura")}
    _, rejeitadas = provedores.filtrar_opcoes(prov, opcoes)
    if rejeitadas:
        raise RuntimeError(f"o provedor {entrada['provedor']} nao aceita {', '.join(rejeitadas)}")
    pasta_bruta = bruto / f"{numero:02d}-{slug(entrada['id'])}"
    pasta_bruta.mkdir(parents=True, exist_ok=True)
    res = provedores.sintetizar(prov, [frase], entrada["voz"], pasta_bruta, velocidade=entrada.get("velocidade", velocidade), variante=entrada.get("modelo"), opcoes=opcoes)
    item = res["itens"][0]
    destino = pasta_falas / f"{numero:02d}-{slug(entrada['id'])}.wav"
    destino.parent.mkdir(parents=True, exist_ok=True)
    _, medidas = voz.pos_processar(Path(item["arquivo"]), destino, cfg)
    return destino, medidas, item, res


def principal(a):
    frase = a.frase.strip() if a.frase else primeira_fala(a.entrada)
    conf = c.ler_json(a.vozes)
    entradas = validar_lista(conf)
    titulo = conf.get("titulo", TITULO_PADRAO)
    velocidade = conf.get("velocidade", 1.0)
    saida = Path(a.saida).resolve()
    cache = {}
    disponiveis, ignoradas = [], []
    for e in entradas:
        prov, motivo = avaliar(e, cache)
        if prov is None:
            ignoradas.append({"id": e["id"], "rotulo": e["rotulo"], "provedor": e["provedor"], "motivo": motivo})
        else:
            disponiveis.append((e, prov))
    c.titulo(f"Comparacao de vozes: {len(disponiveis)} de {len(entradas)} entrada(s) com provedor pronto")
    print(f"   frase ({len(frase)} caracteres): {frase}")
    for ig in ignoradas:
        c.linha("AVISO", f"pulada: {ig['rotulo']} ({ig['provedor']})", ig["motivo"])
    if a.verificar:
        for e, _ in disponiveis:
            c.linha("OK", f"pronta: {e['rotulo']} ({e['provedor']})", e["voz"])
        return
    if not disponiveis:
        c.falhar("nenhum provedor da lista esta pronto nesta maquina; defina as variaveis de ambiente (veja AUDIO.md) ou use uma lista so com kokoro")
    c.exigir_ffmpeg()
    for sub in ("falas", "composicao"):
        shutil.rmtree(saida / sub, ignore_errors=True)
    pasta_falas = saida / "falas"
    bruto = c.WORK_DIR / "comparacao-bruto" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    cfg = voz.config()
    ordem, pares, falharam = [], [], []
    for e, prov in disponiveis:
        numero = len(ordem) + 1
        try:
            destino, medidas, item, res = gerar_uma(prov, e, frase, pasta_falas, bruto, numero, cfg, velocidade)
        except (RuntimeError, ValueError) as err:
            falharam.append({"id": e["id"], "rotulo": e["rotulo"], "provedor": e["provedor"], "motivo": str(err)})
            c.linha("FAIL", f"falhou: {e['rotulo']}", str(err)[:300])
            continue
        nota, usd = custo(e, len(frase), item.get("tokens"))
        registro = {
            "ordem": numero, "id": e["id"], "rotulo": e["rotulo"], "provedor": e["provedor"], "voz": e["voz"],
            "modelo": res["modelo"], "estilo": e.get("estilo") or item.get("estilo"), "tom": e.get("tom"), "altura": e.get("altura"),
            "arquivo": destino.relative_to(saida).as_posix(), "duracao_s": medidas["duracao"], "caracteres": len(frase),
            "lufs": medidas["lufs_integrado"], "sintese_s": item["sintese_s"], "custo_nota": nota, "custo_usd_estimado": usd,
        }
        for extra in ("transcricao", "tokens", "tentativas"):
            if item.get(extra) is not None:
                registro[extra] = item[extra]
        ordem.append(registro)
        pares.append((registro, e))
        c.linha("OK", f"{numero}. {e['rotulo']}", f"{medidas['duracao']:.2f} s  {medidas['lufs_integrado']} LUFS  -> {registro['arquivo']}")
    shutil.rmtree(bruto, ignore_errors=True)
    if not ordem:
        c.falhar("todas as entradas com provedor pronto falharam (veja as linhas FAIL acima)")

    itens = []
    for r, e in pares:
        partes = [NOMES_PROVEDOR.get(r["provedor"], r["provedor"]), r["voz"]]
        if r["estilo"]:
            partes.append(f"estilo {r['estilo']}")
        if r["tom"]:
            partes.append(f"tom {r['tom']}")
        itens.append({
            "topo": e.get("topo") or NOMES_PROVEDOR.get(r["provedor"], r["provedor"]),
            "rotulo": f"{r['ordem']}. {r['rotulo']}",
            "detalhe": e.get("detalhe") or " · ".join(partes),
            "arquivo": str(saida / r["arquivo"]),
            "texto": frase,
        })
    c.escrever_json(saida / "lista.json", {"titulo": titulo, "itens": [{**i, "arquivo": Path(i["arquivo"]).relative_to(saida).as_posix()} for i in itens]})
    total = catalogo_audio.montar(titulo, itens, saida / "composicao")
    manifesto = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "frase": frase,
        "caracteres": len(frase),
        "lista_de_vozes": c.rel(a.vozes),
        "composicao": c.rel(saida / "composicao"),
        "duracao_video_s": total,
        "custo_total_usd_estimado": round(sum(r["custo_usd_estimado"] or 0 for r in ordem), 6),
        "custo_aviso": "somente as entradas com preco publicado entram na soma; MAI-Voice 2.1 e gpt-audio ficam fora (a confirmar / por tokens)",
        "ordem": ordem,
        "ignoradas_sem_chave": ignoradas,
        "falharam": falharam,
    }
    c.escrever_json(saida / "manifesto.json", manifesto)
    c.titulo("Resultado")
    c.linha("OK", f"{len(ordem)} voz(es), composicao de {total:.1f} s", c.rel(saida / "composicao" / "index.html"))
    c.linha("OK", "manifesto", c.rel(saida / "manifesto.json"))
    if ignoradas:
        c.linha("AVISO", f"{len(ignoradas)} entrada(s) sem provedor pronto", ", ".join(i["rotulo"] for i in ignoradas))
    if falharam:
        c.linha("AVISO", f"{len(falharam)} entrada(s) falharam", ", ".join(i["rotulo"] for i in falharam))
    print(f"   renderizar: python content-engine/video/render.py {c.rel(saida / 'composicao')} {c.rel(saida / 'vozes-comparacao-natural.mp4')}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import _comum
    _comum.carregar_env_voz()
    p = argparse.ArgumentParser(description="Gera a mesma frase em varias vozes (uma lista em JSON), pula as entradas cujo provedor nao tem chave e monta a composicao do video de comparacao com o rotulo de cada voz na tela. Nao renderiza.")
    p.add_argument("--frase", help="frase a falar (padrao: primeira fala do --entrada)")
    p.add_argument("--entrada", default=str(ENTRADA_PADRAO), help="voz.txt de onde sai a primeira fala quando nao ha --frase")
    p.add_argument("--vozes", default=str(LISTA_PADRAO), help="JSON com {\"titulo\", \"velocidade\", \"vozes\": [...]}")
    p.add_argument("--saida", default=str(SAIDA_PADRAO), help="pasta de saida (falas/, composicao/, lista.json, manifesto.json)")
    p.add_argument("--verificar", action="store_true", help="so mostra quais entradas tem provedor pronto, sem gerar nada")
    principal(p.parse_args())


if __name__ == "__main__":
    main()
