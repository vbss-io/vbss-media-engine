import argparse
import datetime
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
import reel_cenas as rc
import reel_tempos as rt

AUDIO_DIR = c.ENGINE_DIR / "audio"
TOKENS = c.ENGINE_DIR / "tokens.json"
MUSICA_JSON = AUDIO_DIR / "music" / "musica.json"
SFX_JSON = AUDIO_DIR / "sfx" / "sfx.json"
MUSICA_PADRAO = {"volume": 0.55, "sob_voz": 0.2, "entrada": 0.3, "saida": 1.4}
GERADOS = ("index.html", "trilha.json")
MARCA_DE_GERADO = "<!-- GERADO por content-engine/video/montar_reel.py a partir do roteiro.json. Nao edite aqui: ajuste o roteiro e monte de novo. -->"
VERSAO = 1


def sha(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def sha_do_gerado(caminho):
    return hashlib.sha256(Path(caminho).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def ler_json(caminho):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8-sig"))
    except ValueError as err:
        c.falhar(f"{caminho} nao e um JSON valido: {err}")


def escrever(caminho, texto):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    Path(caminho).write_text(texto, encoding="utf-8", newline="\n")


def escrever_json(caminho, dados):
    escrever(caminho, json.dumps(dados, ensure_ascii=False, indent=1) + "\n")


def dimensoes_da_imagem(caminho):
    with open(caminho, "rb") as f:
        cab = f.read(32)
        if cab[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", cab[16:24])
        if cab[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                marcador = f.read(4)
                if len(marcador) < 4 or marcador[0] != 0xFF:
                    break
                tamanho = struct.unpack(">H", marcador[2:4])[0]
                if 0xC0 <= marcador[1] <= 0xCF and marcador[1] not in (0xC4, 0xC8, 0xCC):
                    dados = f.read(5)
                    h, w = struct.unpack(">HH", dados[1:5])
                    return w, h
                f.seek(tamanho - 2, 1)
    info = c.resumo_video(caminho)
    if info.get("largura"):
        return info["largura"], info["altura"]
    raise rt.ErroDeRoteiro(f"nao consegui ler o tamanho de {caminho}")


def medidor(pasta):
    def medir(arquivo, video=False):
        caminho = (pasta / arquivo).resolve()
        if pasta.resolve() not in caminho.parents or not caminho.is_file():
            raise rt.ErroDeRoteiro(f"'{arquivo}' precisa ser um arquivo dentro da pasta da peca ({pasta})")
        if video:
            info = c.resumo_video(caminho)
            if not info.get("largura"):
                raise rt.ErroDeRoteiro(f"'{arquivo}' nao tem faixa de video")
            return info["largura"], info["altura"], info["duracao"]
        return dimensoes_da_imagem(caminho)

    return medir


def rodar(script, *args):
    r = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=str(script.parent))
    if r.returncode != 0:
        c.falhar(f"{script.name} falhou (codigo {r.returncode}); veja a mensagem acima")


def duracao_do_audio(caminho):
    r = subprocess.run([str(c.ffprobe_path()), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(caminho)], capture_output=True, text=True, timeout=120)
    try:
        return float(r.stdout.strip())
    except ValueError:
        c.falhar(f"nao consegui ler a duracao de {caminho}")


def validar(roteiro, tokens):
    if roteiro.get("marca") not in tokens:
        c.falhar(f"roteiro: 'marca' precisa ser uma chave do content-engine/tokens.json ({', '.join(tokens)})")
    batidas = roteiro.get("batidas")
    if not isinstance(batidas, list) or not batidas:
        c.falhar("roteiro: 'batidas' precisa ser uma lista com pelo menos uma batida")
    for i, b in enumerate(batidas, 1):
        fala = str(b.get("fala", "")).strip()
        if not fala:
            c.falhar(f"roteiro, batida {i}: toda batida tem uma 'fala' (os momentos da cena sao amarrados as palavras dela)")
        if "\n" in fala or fala.startswith("#") or fala.startswith("["):
            c.falhar(f"roteiro, batida {i}: a 'fala' fica em uma linha so e nao comeca com # nem [")
        tipo = (b.get("cena") or {}).get("tipo")
        if tipo not in rc.TIPOS:
            c.falhar(f"roteiro, batida {i}: 'cena.tipo' precisa ser um de: {', '.join(rc.TIPOS)}")
        if tipo == "fecho" and i != len(batidas):
            c.falhar(f"roteiro, batida {i}: a cena 'fecho' e sempre a ultima batida")


def garantir_voz(pasta, falas):
    escrever(pasta / "vozes" / "voz.txt", "\n".join(falas) + "\n")
    saida = pasta / "assets" / "voz"
    registro = ler_json(saida / "voz.json") if (saida / "voz.json").is_file() else {}
    feitas = {int(x["batida"]): x for x in registro.get("linhas", []) if x.get("batida") is not None}
    faltam = [i for i, fala in enumerate(falas, 1) if i not in feitas or feitas[i].get("texto") != fala or not (saida / f"voz-{i:02d}.wav").is_file()]
    if faltam:
        c.titulo(f"Voz: gerando {len(faltam)} de {len(falas)} fala(s) com a voz da casa (demora cerca de 1,5 min por fala)")
        extra = ["--batidas", ",".join(map(str, faltam))] if len(faltam) < len(falas) else []
        rodar(AUDIO_DIR / "voz.py", pasta / "vozes" / "voz.txt", "--saida", saida, *extra)
        registro = ler_json(saida / "voz.json")
        feitas = {int(x["batida"]): x for x in registro.get("linhas", [])}
    else:
        c.linha("OK", f"voz: {len(falas)} fala(s) ja gravadas com o mesmo texto", "nada foi gerado de novo")
    return [saida / f"voz-{i:02d}.wav" for i in range(1, len(falas) + 1)], [feitas[i] for i in range(1, len(falas) + 1)]


def garantir_legenda(pasta, falas, wavs, tempos, destaques, anterior, refazer):
    chave = hashlib.sha256(json.dumps([[sha(w) for w in wavs], falas, [b["fala"] for b in tempos], destaques], ensure_ascii=False).encode("utf-8")).hexdigest()
    if not refazer and anterior.get("legenda_chave") == chave and (pasta / "legenda.json").is_file() and (pasta / "legenda.js").is_file():
        c.linha("OK", "legenda: mesmas falas e mesmos tempos", "o Whisper nao rodou de novo")
        return chave
    so_voz = pasta / "trilha-da-legenda.json"
    escrever_json(so_voz, {"deixas": [{"t": b["fala"], "arquivo": f"assets/voz/voz-{i:02d}.wav", "volume": 1.0} for i, b in enumerate(tempos, 1)]})
    extra = ["--destaque", ",".join(destaques)] if destaques else []
    try:
        rodar(AUDIO_DIR / "legenda.py", pasta, "--trilha", so_voz, "--texto", pasta / "vozes" / "legenda.txt", *extra)
    finally:
        so_voz.unlink(missing_ok=True)
    return chave


def logo_da_marca(pasta, roteiro, marca):
    if roteiro.get("logo"):
        if not (pasta / roteiro["logo"]).is_file():
            c.falhar(f"roteiro: 'logo' aponta para {roteiro['logo']}, que nao existe na pasta da peca")
        return roteiro["logo"]
    origem = Path(marca.get("logo") or "")
    if not origem.is_absolute():
        origem = c.REPO_DIR / origem
    if not marca.get("logo") or not origem.is_file() or origem.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
        c.falhar("nao achei o logo da marca (campo 'logo' do tokens.json). Copie o logo para assets/ da peca e aponte em 'logo' no roteiro")
    destino = pasta / "assets" / f"logo{origem.suffix.lower()}"
    if not destino.is_file() or sha(destino) != sha(origem):
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem, destino)
    return destino.relative_to(pasta).as_posix()


def conferir_ajuste_manual(pasta, anterior, sobrescrever):
    mexidos = []
    for nome in GERADOS:
        arquivo = pasta / nome
        if not arquivo.is_file():
            continue
        esperado = (anterior.get("gerados") or {}).get(nome)
        if anterior.get("incompleta") or (nome == "trilha.json" and not anterior):
            continue
        if esperado != sha_do_gerado(arquivo):
            mexidos.append(nome)
    if not mexidos:
        return
    if not sobrescrever:
        c.falhar("estes arquivos foram alterados a mao (ou nao vieram do montador) desde a ultima montagem: " + ", ".join(mexidos)
                 + ".\n  O montador nao sobrescreve ajuste manual. Leve o ajuste para o roteiro.json (campos da cena, 'css_extra' ou 'js_extra') e monte de novo,"
                 + "\n  ou rode com --sobrescrever: a versao atual vai para a pasta ajustes-manuais/ antes de ser trocada.")
    for nome in mexidos:
        destino = pasta / "ajustes-manuais" / f"{Path(nome).stem}-{sha(pasta / nome)[:8]}.txt"
        destino.parent.mkdir(exist_ok=True)
        shutil.copyfile(pasta / nome, destino)
        c.linha("AVISO", f"{nome} tinha ajuste manual", f"copia guardada em {destino.relative_to(pasta).as_posix()}")


def falas_ouvidas(pasta, wavs, liberar=(), por=None):
    arquivo = pasta / "vozes" / "ouvidas.json"
    registro = ler_json(arquivo) if arquivo.is_file() else {}
    for n in liberar:
        if not 1 <= n <= len(wavs):
            c.falhar(f"--ouvida {n}: o roteiro tem {len(wavs)} fala(s)")
        registro[str(n)] = {"por": por, "em": datetime.date.today().isoformat(), "sha256": sha(wavs[n - 1])}
    validas = {n: r for n, r in registro.items() if n.isdigit() and 1 <= int(n) <= len(wavs) and r.get("sha256") == sha(wavs[int(n) - 1])}
    if validas != registro or liberar:
        escrever_json(arquivo, validas)
    return {int(n): r for n, r in validas.items()}


def montar(pasta, sobrescrever=False, refazer_legenda=False, ouvida=(), por=None):
    roteiro_path = pasta / "roteiro.json"
    if not roteiro_path.is_file():
        c.falhar(f"{pasta} nao tem roteiro.json (formato em content-engine/video/MOTOR.md, secao 'Montador de Reel')")
    roteiro = ler_json(roteiro_path)
    tokens = ler_json(TOKENS)
    validar(roteiro, tokens)
    marca = tokens[roteiro["marca"]]
    anterior = ler_json(pasta / "montagem.json") if (pasta / "montagem.json").is_file() else {}
    conferir_ajuste_manual(pasta, anterior, sobrescrever)
    if not c.ffprobe_path().is_file():
        c.falhar("FFmpeg local ausente. Rode python content-engine/video/setup.py")
    try:
        estilo = rc.estilo_da_marca(marca)
    except rt.ErroDeRoteiro as err:
        c.falhar(str(err))

    c.titulo(f"Montando {pasta.name} ({roteiro['marca']}, estilo {estilo['nome']}, {len(roteiro['batidas'])} batida(s))")
    falas = [str(b["fala"]).strip() for b in roteiro["batidas"]]
    grafias = {**((marca.get("motion") or {}).get("pronuncia") or {}), **(roteiro.get("pronuncia") or {})}
    wavs, registro_voz = garantir_voz(pasta, [rt.para_a_voz(f, grafias) for f in falas])
    ouvidas = falas_ouvidas(pasta, wavs, ouvida, por)
    escrever(pasta / "vozes" / "legenda.txt", "\n".join(falas) + "\n")
    duracoes = [duracao_do_audio(w) for w in wavs]

    musica = None
    bpm = None
    if roteiro.get("musica", True) is not False:
        musica = dict(MUSICA_PADRAO)
        if isinstance(roteiro.get("musica"), dict):
            musica.update(roteiro["musica"])
        if "faixa" not in musica and "arquivo" not in musica:
            if not estilo.get("musica"):
                c.falhar("roteiro sem 'musica.faixa' e a marca nao tem musica padrao no tokens.json (motion.musica). Escolha uma faixa de content-engine/audio/music/CATALOGO.md ou use \"musica\": false")
            musica["faixa"] = estilo["musica"]
        if "faixa" in musica:
            faixas = {i["id"]: i for i in ler_json(MUSICA_JSON)["itens"]}
            if musica["faixa"] not in faixas:
                c.falhar(f"musica: a faixa '{musica['faixa']}' nao existe (veja content-engine/audio/music/CATALOGO.md)")
            bpm = faixas[musica["faixa"]].get("bpm")
    cortes = roteiro.get("cortes", "compasso" if bpm else "fala")
    tempos = rt.planejar(duracoes, bpm=bpm if cortes == "compasso" else None, minimos=[b.get("minimo") for b in roteiro["batidas"]])
    total = round(tempos[-1]["fim"], 2)
    tempos[-1]["fim"] = total

    destaques = list((roteiro.get("legenda") or {}).get("destaque") or [])
    chave_legenda = garantir_legenda(pasta, falas, wavs, tempos, destaques, anterior, refazer_legenda)
    legenda = ler_json(pasta / "legenda.json")
    palavras = rt.separar_por_fala(legenda)
    if len(palavras) != len(falas):
        c.falhar("a legenda nao cobre todas as falas; rode de novo com --refazer-legenda")

    ancoras = {i["arquivo"][:-4]: i.get("ancora") or 0 for i in ler_json(SFX_JSON)["itens"]}
    peca = rc.Peca(estilo, total, ancoras, medidor(pasta))
    batidas = []
    for i, (b, t) in enumerate(zip(roteiro["batidas"], tempos), 1):
        batidas.append({"i": i, "ini": t["inicio"], "fim": t["fim"], "fala": t["fala"], "fim_fala": t["fim_fala"], "palavras": palavras[i - 1],
                        "cena": b["cena"], "primeira": i == 1, "ultima": i == len(tempos)})
    ctx = {"logo": logo_da_marca(pasta, roteiro, marca), "url": marca.get("url") if "." in str(marca.get("url", "")) and " " not in str(marca.get("url", "")) else None,
           "nome_da_marca": roteiro.get("nome_da_marca") or roteiro["marca"]}
    try:
        rc.montar(peca, roteiro, batidas, ctx)
    except rt.ErroDeRoteiro as err:
        c.falhar(f"roteiro: {err}")

    escrever_json(pasta / "montagem.json", {"versao": VERSAO, "incompleta": True, "legenda_chave": chave_legenda})
    pagina = rc.html_da_peca(peca, roteiro.get("titulo") or pasta.name, total, roteiro.get("css_extra", ""), roteiro.get("js_extra", ""))
    escrever(pasta / "index.html", pagina.replace("<html lang=\"pt-BR\">", "<html lang=\"pt-BR\">\n" + MARCA_DE_GERADO, 1))
    deixas = [{"t": t["fala"], "arquivo": f"assets/voz/voz-{i:02d}.wav", "volume": 1.0} for i, t in enumerate(tempos, 1)]
    deixas += [d for d in rt.enxugar(peca.deixas) if d["t"] < total - 0.05]
    trilha = {"volume_efeitos": 1.0, "deixas": deixas}
    if musica:
        trilha = {"volume_efeitos": 1.0, "musica": musica, "deixas": deixas}
    escrever_json(pasta / "trilha.json", trilha)
    rodar(AUDIO_DIR / "trilha.py", pasta, pasta / "trilha.json")

    pronuncia = []
    for i, (fala_leg, reg) in enumerate(zip(legenda.get("falas", []), registro_voz), 1):
        conf = fala_leg.get("pronuncia")
        pronuncia.append({"batida": i, "arquivo": f"voz-{i:02d}.wav", "conferida": conf is not None, "ok": bool(conf and conf["ok"]),
                          "divergencias": (conf or {}).get("divergencias", []), "semente": reg.get("semente"), "ouvida": ouvidas.get(i)})
    textos = sorted(peca.caixas, key=lambda x: x["de"])
    animacoes = sum(1 for linha in peca.js if "tl." in linha or "K." in linha or "selo(" in linha or "confirma(" in linha or "rola(" in linha)
    montagem = {
        "versao": VERSAO, "roteiro_sha256": sha(roteiro_path), "marca": roteiro["marca"], "estilo": estilo["nome"], "duracao": total,
        "musica": {"faixa": (musica or {}).get("faixa") or (musica or {}).get("arquivo"), "bpm": bpm, "cortes": cortes} if musica else None,
        "batidas": [{"batida": b["i"], "tipo": b["cena"]["tipo"], "inicio": b["ini"], "fala": b["fala"], "fim_fala": b["fim_fala"], "fim": b["fim"]} for b in batidas],
        "primeiro_texto": textos[0]["de"] if textos else None, "textos": textos,
        "legenda": {"base": 0.24, "largura": 800, "linhas": 2, "tamanho": 68}, "legenda_chave": chave_legenda,
        "animacoes": animacoes, "quiques": peca.quiques, "efeitos": len(deixas) - len(tempos), "pronuncia": pronuncia, "avisos": peca.avisos,
        "gerados": {nome: sha_do_gerado(pasta / nome) for nome in GERADOS},
    }
    escrever_json(pasta / "montagem.json", montagem)

    c.titulo("Resultado")
    for b in batidas:
        print(f"   batida {b['i']} ({b['cena']['tipo']}): {b['ini']:6.2f} a {b['fim']:6.2f} s, fala em {b['fala']:.2f} s")
    c.linha("OK", f"composicao pronta em {c_rel(pasta)}", f"{total} s, {len(deixas) - len(tempos)} efeito(s)" + (f", musica {montagem['musica']['faixa']}" + (f" ({bpm:g} bpm, cortes no compasso)" if bpm and cortes == "compasso" else "") if musica else ", sem musica"))
    for aviso in peca.avisos:
        c.linha("AVISO", aviso)
    apontadas = [x for x in pronuncia if x["conferida"] and not x["ok"]]
    ruins = [x for x in apontadas if not x["ouvida"]]
    nao_conferidas = [x for x in pronuncia if not x["conferida"]]
    for x in apontadas:
        if x["ouvida"]:
            c.linha("AVISO", f"PRONUNCIA: {x['arquivo']} foi apontada pela conferencia e liberada por quem ouviu ({x['ouvida']['por']}, {x['ouvida']['em']})", "; ".join(x["divergencias"]))
        else:
            c.linha("AVISO", f"PRONUNCIA: {x['arquivo']} nao disse o texto como esta escrito", "; ".join(x["divergencias"]))
    if ruins:
        numeros = ",".join(str(x["batida"]) for x in ruins)
        print("\n   >>> OUCA essas falas antes de renderizar (assets/voz/). Saiu errado, gere de novo: python content-engine/audio/voz.py "
              f"{c_rel(pasta / 'vozes' / 'voz.txt')} --saida {c_rel(pasta / 'assets' / 'voz')} --batidas {numeros} --semente 11")
        print(f"   >>> Uma pessoa ouviu e a fala esta certa: python content-engine/video/montar_reel.py {c_rel(pasta)} --ouvida {numeros} --por \"nome de quem ouviu\"")
    elif apontadas:
        c.linha("OK", "pronuncia: as falas apontadas foram ouvidas e liberadas por uma pessoa", "a liberacao vale so para este audio; fala gerada de novo volta a ser conferida")
    elif nao_conferidas:
        c.linha("AVISO", "pronuncia nao conferida (Whisper indisponivel)", "ouca as falas antes de renderizar")
    else:
        c.linha("OK", "pronuncia conferida em todas as falas", "o que o Whisper ouviu bate com o texto e nao ha chiado a mais")
    print(f"\n   Previa:  python content-engine/video/preview.py {c_rel(pasta)}")
    print(f"   Render:  python content-engine/video/render.py {c_rel(pasta)} <saida>/reel.mp4")
    print(f"   Checar:  python content-engine/video/checar_reel.py <saida>/reel.mp4 {c_rel(pasta)}")
    return montagem


def c_rel(caminho):
    try:
        return Path(caminho).resolve().relative_to(c.REPO_DIR).as_posix()
    except ValueError:
        return str(caminho)


def main():
    p = argparse.ArgumentParser(description="Monta a composicao de um Reel (index.html, trilha, legenda) a partir do roteiro.json da pasta da peca. Gera a voz que faltar, tira os tempos das palavras faladas e encaixa os cortes no compasso da musica.")
    p.add_argument("pasta", help="pasta da peca (com roteiro.json e assets/)")
    p.add_argument("--sobrescrever", action="store_true", help="troca index.html e trilha.json mesmo que tenham ajuste manual (a versao atual vai para ajustes-manuais/)")
    p.add_argument("--refazer-legenda", action="store_true", help="roda o Whisper de novo mesmo sem mudanca nas falas")
    p.add_argument("--ouvida", default="", help="numeros das falas (ex.: 2,4) que a conferencia de pronuncia apontou e que UMA PESSOA ouviu e achou certas; exige --por")
    p.add_argument("--por", help="nome de quem ouviu as falas de --ouvida")
    a = p.parse_args()
    try:
        ouvida = [int(x) for x in a.ouvida.split(",") if x.strip()]
    except ValueError:
        c.falhar("--ouvida recebe os numeros das falas separados por virgula (ex.: 2,4)")
    if ouvida and not (a.por or "").strip():
        c.falhar("--ouvida exige --por \"nome de quem ouviu\": a liberacao e de uma pessoa que ouviu o audio, nunca automatica")
    pasta = Path(a.pasta).resolve()
    if not pasta.is_dir():
        c.falhar(f"{pasta} nao e uma pasta")
    montar(pasta, a.sobrescrever, a.refazer_legenda, ouvida, (a.por or "").strip())


if __name__ == "__main__":
    main()
