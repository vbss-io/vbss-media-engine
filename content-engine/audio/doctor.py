import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

import _comum as c
import providers
from common import ambiente as _ambiente
from providers import kokoro

resultados = []
EXTENSOES_DE_AUDIO = (".m4a", ".mp3", ".ogg", ".opus", ".flac", ".wav")
DURACAO_MAXIMA_MUSICA = 61.0
LIMITE_MUSICA_MB = 25


def item(nome, ok, detalhe="", aviso=False):
    if ok:
        status = "PASS"
    elif aviso:
        status = "AVISO"
    else:
        status = "FAIL"
    resultados.append(ok or aviso)
    c.linha(status, nome, detalhe)


def info(nome, detalhe=""):
    c.linha("INFO", nome, detalhe)


def checar_base():
    c.titulo("Base")
    item("Python 3.10+", sys.version_info >= (3, 10), sys.version.split()[0])
    for nome, path in (("ffmpeg", c.ffmpeg_path()), ("ffprobe", c.ffprobe_path())):
        if not path.is_file():
            item(f"{nome} local (content-engine/video/bin)", False, "rode python content-engine/video/setup.py")
            continue
        out = subprocess.run([str(path), "-version"], capture_output=True, text=True, timeout=60).stdout
        item(f"{nome} local (content-engine/video/bin)", bool(out), out.splitlines()[0] if out else "nao executou")
    if c.ffmpeg_path().is_file():
        filtros = subprocess.run([str(c.ffmpeg_path()), "-hide_banner", "-filters"], capture_output=True, text=True, timeout=60).stdout
        faltam = [f for f in ("ebur128", "silenceremove", "alimiter", "acompressor", "showwavespic") if f" {f} " not in filtros]
        item("filtros de audio do FFmpeg (medicao e tratamento)", not faltam, "ok" if not faltam else f"faltam: {', '.join(faltam)}")


def checar_sfx():
    c.titulo("Biblioteca de efeitos (content-engine/audio/sfx)")
    if not c.SFX_MANIFESTO.is_file():
        item("manifesto sfx.json", False, "rode python content-engine/audio/sfx_setup.py")
        return
    manifesto = c.ler_json(c.SFX_MANIFESTO)
    itens = manifesto["itens"]
    faltando, diferentes = [], []
    for it in itens:
        arq = c.SFX_DIR / it["arquivo"]
        if not arq.is_file():
            faltando.append(it["arquivo"])
        elif c.sha256(arq) != it["sha256"]:
            diferentes.append(it["arquivo"])
    item("arquivos do manifesto presentes", not faltando, f"{len(itens)} efeitos" if not faltando else "faltam: " + ", ".join(faltando[:5]))
    item("SHA-256 de cada efeito confere com sfx.json", not diferentes, "ok" if not diferentes else "diferentes: " + ", ".join(diferentes[:5]))
    esperados = {it["arquivo"] for it in itens}
    extras = sorted(p.relative_to(c.SFX_DIR).as_posix() for p in c.SFX_DIR.rglob("*.wav") if p.relative_to(c.SFX_DIR).as_posix() not in esperados)
    item("nenhum WAV fora do manifesto", not extras, "ok" if not extras else ", ".join(extras[:5]))
    catalogo = c.SFX_DIR / "CATALOGO.md"
    texto = catalogo.read_text(encoding="utf-8") if catalogo.is_file() else ""
    sem_linha = [it["arquivo"] for it in itens if f"`{it['arquivo']}`" not in texto]
    item("CATALOGO.md lista todos os efeitos", bool(texto) and not sem_linha, "ok" if texto and not sem_linha else ("CATALOGO.md ausente" if not texto else "sem linha: " + ", ".join(sem_linha[:5])))
    item("LICENCAS.md presente", (c.SFX_DIR / "LICENCAS.md").is_file(), str(c.rel(c.SFX_DIR / "LICENCAS.md")))
    fontes = c.ler_json(c.SFX_FONTES)["pacotes"]
    selecao = c.ler_json(c.SFX_SELECAO)["itens"]
    sem_fonte = sorted({ref["pacote"] for i in selecao for ref in ([i] if "pacote" in i else i.get("camadas", []))} - set(fontes))
    sem_sha = sorted(k for k, v in fontes.items() if not re.fullmatch(r"[0-9a-f]{64}", v.get("sha256", "")) or v.get("licenca") != "CC0")
    item("pacotes de origem com URL, SHA-256 e licenca CC0", not sem_fonte and not sem_sha, f"{len(fontes)} pacotes" if not (sem_fonte or sem_sha) else f"problema: {', '.join(sem_fonte + sem_sha)}")
    nomes_sel = {f"{i['categoria']}/{i['nome']}.wav" for i in selecao}
    item("sfx.json bate com sfx_selecao.json", nomes_sel == esperados, "ok" if nomes_sel == esperados else "rode python content-engine/audio/sfx_setup.py")
    fora = [it["arquivo"] for it in itens if it["pico_dbtp"] is None or it["pico_dbtp"] > c.TETO_PICO_DBTP + 0.05]
    item("nenhum efeito acima do teto de pico", not fora, f"teto {c.TETO_PICO_DBTP} dBTP" if not fora else ", ".join(fora[:5]))
    total = sum(it["bytes"] for it in itens)
    info("tamanho da biblioteca", f"{total / (1 << 20):.2f} MB em {len({it['categoria'] for it in itens})} categorias")
    cat = c.SFX_DIR / "catalogo.mp4"
    item("video-catalogo para audicao (sfx/catalogo.mp4)", cat.is_file(), c.rel(cat) if cat.is_file() else "rode python content-engine/audio/catalogo_audio.py", aviso=True)


def checar_musica():
    c.titulo("Biblioteca de musica de fundo (content-engine/audio/music)")
    if not c.MUSICA_MANIFESTO.is_file():
        item("manifesto musica.json", False, "rode python content-engine/audio/musica_setup.py")
        return
    manifesto = c.ler_json(c.MUSICA_MANIFESTO)
    itens = manifesto["itens"]
    fmt = manifesto["formato"]
    faltando, diferentes = [], []
    for it in itens:
        arq = c.MUSICA_DIR / it["arquivo"]
        if not arq.is_file():
            faltando.append(it["arquivo"])
        elif c.sha256(arq) != it["sha256"]:
            diferentes.append(it["arquivo"])
    item("arquivos do manifesto presentes", not faltando, f"{len(itens)} faixas" if not faltando else "faltam: " + ", ".join(faltando[:5]))
    item("SHA-256 de cada faixa confere com musica.json", not diferentes, "ok" if not diferentes else "diferentes: " + ", ".join(diferentes[:5]))
    esperados = {it["arquivo"] for it in itens}
    extras = sorted(p.name for p in c.MUSICA_DIR.iterdir() if p.suffix.lower() in EXTENSOES_DE_AUDIO and p.name not in esperados)
    item("nenhum audio fora do manifesto", not extras, "ok" if not extras else ", ".join(extras[:5]))
    catalogo = c.MUSICA_DIR / "CATALOGO.md"
    texto = catalogo.read_text(encoding="utf-8") if catalogo.is_file() else ""
    sem_linha = [it["id"] for it in itens if f"`{it['id']}`" not in texto]
    item("CATALOGO.md lista todas as faixas", bool(texto) and not sem_linha, "ok" if texto and not sem_linha else ("CATALOGO.md ausente" if not texto else "sem linha: " + ", ".join(sem_linha[:5])))
    item("LICENCAS.md presente", (c.MUSICA_DIR / "LICENCAS.md").is_file(), str(c.rel(c.MUSICA_DIR / "LICENCAS.md")))
    cfg = c.ler_json(c.MUSICA_FONTES)
    fontes = cfg["fontes"]
    sem_fonte = sorted({f["fonte"] for f in cfg["faixas"]} - set(fontes))
    ruins = sorted(k for k, v in fontes.items() if not re.fullmatch(r"[0-9a-f]{64}", v.get("sha256", "")) or v.get("licenca") != "CC0" or not v.get("pagina") or not v.get("url"))
    item("fontes com pagina, URL, SHA-256 e licenca CC0", not sem_fonte and not ruins, f"{len(fontes)} fontes" if not (sem_fonte or ruins) else f"problema: {', '.join(sem_fonte + ruins)}")
    ids = {f["id"] for f in cfg["faixas"]}
    item("musica.json bate com musica_fontes.json", ids == {it["id"] for it in itens}, "ok" if ids == {it["id"] for it in itens} else "rode python content-engine/audio/musica_setup.py")
    fora = [it["id"] for it in itens if it["pico_dbtp"] is None or it["pico_dbtp"] > fmt["teto_pico_dbtp"] + 0.05 or it["lufs_integrado"] is None or it["lufs_integrado"] > fmt["alvo_lufs_integrado"] + 0.5]
    item("nenhuma faixa acima do alvo de nivel ou do teto de pico", not fora, f"alvo {fmt['alvo_lufs_integrado']} LUFS, teto {fmt['teto_pico_dbtp']} dBTP" if not fora else ", ".join(fora[:5]))
    longas = [it["id"] for it in itens if it["duracao"] > DURACAO_MAXIMA_MUSICA]
    item(f"cada faixa com ate {DURACAO_MAXIMA_MUSICA:.0f} s", not longas, "ok" if not longas else ", ".join(longas[:5]))
    total = sum(it["bytes"] for it in itens) / (1 << 20)
    item(f"biblioteca abaixo de {LIMITE_MUSICA_MB} MB", total < LIMITE_MUSICA_MB, f"{total:.2f} MB em {len(itens)} faixas")
    sem_bpm = [it["id"] for it in itens if it["bpm"] is None]
    info("faixas sem bpm (ambiente sem pulso ou venv de audio ausente no setup)", ", ".join(sem_bpm) or "nenhuma")


def checar_kokoro(ativo):
    c.titulo(f"Voz local Kokoro ({'provedor ativo' if ativo else 'opcional: o provedor ativo e outro'})")
    py = kokoro.venv_python()
    item("venv isolado em content-engine/audio/.venv", py.is_file(), str(py) if py.is_file() else "rode python content-engine/audio/voz_setup.py", aviso=not ativo)
    if py.is_file():
        req = (kokoro.KOKORO_DIR / "requirements.txt").read_text(encoding="utf-8")
        fixados = dict(re.findall(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", req, re.M))
        r = subprocess.run([str(py), "-I", "-m", "pip", "list", "--format=json", "--disable-pip-version-check"], capture_output=True, text=True,
                           env=kokoro.ambiente(), timeout=120)
        try:
            instalados = {re.sub(r"[-_.]+", "-", p["name"]).lower(): p["version"] for p in json.loads(r.stdout)}
        except json.JSONDecodeError:
            instalados = {}
        divergem = [f"{n}=={v} (instalado {instalados.get(n)})" for n, v in fixados.items() if instalados.get(n) != v]
        item("pacotes do venv nas versoes do lock (kokoro/requirements.txt)", not divergem, f"{len(fixados)} pacotes" if not divergem else "; ".join(divergem[:4]))
    cfg = kokoro.config_modelo()
    for variante, nome in cfg["variantes"].items():
        info_arq = cfg["arquivos"][nome]
        arq = c.MODELOS_DIR / nome
        padrao = variante == cfg["padrao"]
        if not arq.is_file():
            if padrao:
                item(f"modelo {variante} (padrao) presente", False, f"rode python content-engine/audio/voz_setup.py", aviso=not ativo)
            else:
                info(f"modelo {variante} nao baixado", f"opcional: voz_setup.py --modelo {variante}")
            continue
        ok = c.sha256(arq) == info_arq["sha256"]
        item(f"modelo {variante}{' (padrao)' if padrao else ''} com SHA-256 fixado", ok, nome if ok else "SHA-256 diferente: apague o arquivo e rode voz_setup.py")
    vozes = c.MODELOS_DIR / cfg["vozes"]
    if vozes.is_file():
        item("arquivo de vozes com SHA-256 fixado", c.sha256(vozes) == cfg["arquivos"][cfg["vozes"]]["sha256"], cfg["vozes"])
    else:
        item("arquivo de vozes presente", False, "rode python content-engine/audio/voz_setup.py", aviso=not ativo)
    env = kokoro.ambiente()
    problemas = _ambiente.assert_env_isolated(env, kokoro.SANDBOX)
    item("processo de voz local sem chaves/tokens e com HOME/TEMP isolados", not problemas, "; ".join(problemas) or c.rel(kokoro.SANDBOX))
    if py.is_file() and all((c.MODELOS_DIR / n).is_file() for n in (cfg["variantes"][cfg["padrao"]], cfg["vozes"])):
        try:
            res = kokoro.vozes_instaladas()
            pt = sorted(v for v in res["vozes"] if v.startswith("p"))
            esperadas = {v["id"] for v in kokoro.VOZES}
            item("vozes pt-BR no modelo (pf_dora, pm_alex, pm_santa)", esperadas <= set(pt), f"{', '.join(pt)}; carga {res['carga_s']:.1f} s")
        except RuntimeError as err:
            item("Kokoro carrega o modelo", False, str(err)[:200])


def checar_voicestudio(ativo):
    c.titulo("Voz local VoiceStudio (voicestudio/, offline)")
    prov, erro = providers.tentar_carregar("voicestudio")
    if prov is None:
        item("voicestudio: adaptador carrega", False, erro[:200])
        return
    ok, motivo = prov.disponivel()
    item("VoiceStudio pronto" + (" (provedor ativo)" if ativo else ""), ok, motivo, aviso=not ativo)
    info("vozes guardadas em voicestudio/voices", ", ".join(v["id"] for v in prov.VOZES) or "nenhuma")


def checar_nuvem(ativo=None):
    c.titulo("Vozes na nuvem (chave no content-engine/audio/.env ou no ambiente; valor nunca e mostrado)")
    for nome in ("azure", "azure_openai", "google"):
        prov, erro = providers.tentar_carregar(nome)
        if prov is None:
            item(f"{nome}: adaptador carrega", False, erro[:200])
            continue
        ok, motivo = prov.disponivel()
        if nome == ativo and not ok:
            item(f"{nome} (provedor ativo) com chave", False, f"{motivo}; veja a secao 'Voz de nuvem: chaves no arquivo .env' do AUDIO.md. Sem chave, use --provedor kokoro (voz local)", aviso=True)
            continue
        info(f"{nome}: {'chave presente' if ok else 'sem chave'}", motivo if not ok else "pronto para voz.py --provedor " + nome)


def checar_gitignore():
    c.titulo("Repositorio")
    gi = c.REPO_DIR / ".gitignore"
    texto = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    precisa = ["content-engine/audio/.venv/", "content-engine/audio/.cache/", "content-engine/audio/.models/", "content-engine/audio/.work/"]
    faltam = [p for p in precisa if p not in texto]
    item(".gitignore ignora venv, caches, modelos e area de trabalho do audio", not faltam, "faltam: " + ", ".join(faltam) if faltam else str(gi))
    item("sfx/ curado fica no git (nao ignorado)", "content-engine/audio/sfx" not in texto, "ok")
    item("music/ curada fica no git (nao ignorada)", "content-engine/audio/music" not in texto, "ok")


def main():
    print("Diagnostico da camada de audio do vbss-media-engine")
    carregadas = c.carregar_env_voz()
    if c.ENV_VOZ.is_file():
        c.linha("OK", "arquivo de chaves de voz encontrado (content-engine/audio/.env)", f"{len(carregadas)} variavel(is) carregada(s), valores nao exibidos")
    else:
        c.linha("AVISO", "sem content-engine/audio/.env", "copie .env.example para .env e preencha as suas chaves, so se for usar voz de nuvem (veja o AUDIO.md)")
    cfg = c.config_de_voz()
    checar_base()
    checar_sfx()
    checar_musica()
    checar_voicestudio(cfg.get("provedor") == "voicestudio")
    checar_kokoro(cfg.get("provedor") == "kokoro")
    checar_nuvem(cfg.get("provedor"))
    checar_gitignore()
    falhas = resultados.count(False)
    voz_da_casa = cfg["vozes_padrao"].get(cfg["provedor"], "padrao do provedor")
    print(f"\nResultado: {len(resultados) - falhas} PASS/AVISO, {falhas} FAIL (voz da casa: {cfg['provedor']} / {voz_da_casa}, definida no {cfg['origem'].get(cfg['provedor'], 'voz_config.json')})")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
