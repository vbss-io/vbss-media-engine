import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

import _comum as c
from common import arquivos, midias

WAV_MINIMO = b"RIFF\x00\x00\x00\x00WAVEfmt "
PNG_MINIMO = b"\x89PNG\r\n\x1a\n" + bytes(8)
MP4_MINIMO = b"\x00\x00\x00\x18ftypisom" + bytes(4)
WOFF2_MINIMO = b"wOF2" + bytes(12)

resultados = []


def item(nome, ok, detalhe=""):
    resultados.append(ok)
    c.linha("PASS" if ok else "FAIL", nome, detalhe)


def checar_base():
    c.titulo("Base")
    item("Python 3.10+", sys.version_info >= (3, 10), sys.version.split()[0])
    node = c.node_path()
    ver = c.node_version(node) if node else None
    item("Node.js 22+", bool(ver and ver >= (22, 0, 0)), f"{node} v{'.'.join(map(str, ver))}" if ver else "nao encontrado")
    return node


def checar_ffmpeg():
    c.titulo("FFmpeg local")
    for nome, path in (("ffmpeg", c.ffmpeg_path()), ("ffprobe", c.ffprobe_path())):
        if not path.is_file():
            item(f"{nome} em content-engine/video/bin", False, "rode python content-engine/video/setup.py")
            continue
        out = subprocess.run([str(path), "-version"], capture_output=True, text=True, timeout=60).stdout
        primeira = out.splitlines()[0] if out else ""
        item(f"{nome} em content-engine/video/bin", f"version {c.FFMPEG_BUILD['versao']}" in primeira, primeira)
    if c.ffmpeg_path().is_file():
        enc = subprocess.run([str(c.ffmpeg_path()), "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=60).stdout
        item("encoder H.264 (libx264) disponivel", "libx264" in enc)


def checar_chrome():
    c.titulo("Navegador")
    chrome = c.find_chrome()
    if chrome is None:
        item("navegador encontrado", False, "rode python content-engine/video/setup.py (instala o navegador fixo)")
        return None
    if c.e_navegador_fixo(chrome):
        problemas = c.navegador_fixado.conferir()
        item("navegador fixo em uso, com SHA-256 conferido", not problemas, "; ".join(problemas) or c.descrever_navegador(chrome))
    else:
        c.linha("AVISO", f"{c.descrever_navegador(chrome)}", c.AVISO_SISTEMA)
    return chrome


def checar_motor(node):
    motor = c.load_motor()
    c.titulo(f"Motor ativo: {motor.NOME}")
    for nome, ok, detalhe in motor.checar():
        item(nome, ok, detalhe)
    return motor


def checar_isolamento(motor, node, chrome):
    c.titulo("Isolamento (nada sai da maquina)")
    env = c.sandbox_env(
        extra=motor.ambiente(chrome or "chrome.exe", c.versao_navegador(chrome) or "", c.ffmpeg_path(), c.ffprobe_path(), c.SANDBOX_DIR, c.SANDBOX_DIR / "net-guard-selftest.log"),
        path_dirs=[node.parent] if node else [],
    )
    env.update(c.ambiente_de_arquivos(c.raizes_permitidas(motor, c.sandbox_paths()["stage"], node, chrome), c.SANDBOX_DIR / "file-guard-selftest.log"))
    problemas = c.assert_env_isolated(env)
    item("ambiente do motor sem chaves/tokens e com HOME/APPDATA/TEMP no sandbox", not problemas, "; ".join(problemas) or str(c.SANDBOX_DIR))
    desligados = {k: v for k, v in env.items() if k.endswith(("NO_TELEMETRY", "NO_UPDATE_CHECK", "NO_AUTO_INSTALL", "SKIP_SKILLS"))}
    item("telemetria e auto-update do motor desligados", env.get("DO_NOT_TRACK") == "1" and all(v == "1" for v in desligados.values()),
         ", ".join(sorted(desligados)) or "DO_NOT_TRACK")
    if not node:
        item("auto-teste do bloqueio de rede", False, "sem Node")
        return
    log = c.SANDBOX_DIR / "net-guard-selftest.log"
    if log.exists():
        log.unlink()
    r = subprocess.run(motor.comando_selftest(node), env=env, cwd=str(c.sandbox_paths()["cwd"]), capture_output=True, text=True, timeout=120)
    try:
        dados = json.loads(r.stdout)
    except json.JSONDecodeError:
        item("auto-teste do bloqueio de rede", False, (r.stdout + r.stderr)[-400:])
        return
    for d in dados:
        detalhe = d["detail"]
        item(f"bloqueio de rede: {d['name']}", d["ok"], detalhe[:140] + ("..." if len(detalhe) > 140 else ""))
    bloqueios = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    item("tentativas de teste registradas no log do guard", len(bloqueios) >= 5, f"{len(bloqueios)} linhas em {log.name}")


def checar_guarda_arquivos(motor, node, chrome):
    c.titulo("Guarda de arquivos em tempo de render (o motor so le dentro da composicao)")
    if not node or not hasattr(motor, "comando_selftest_arquivos"):
        item("auto-teste do guarda de arquivos", False, "sem Node" if not node else f"o motor '{motor.NOME}' nao tem comando_selftest_arquivos")
        return
    base = c.SANDBOX_DIR / "selftest-arquivos"
    if base.exists():
        shutil.rmtree(base)
    dentro = base / "dentro"
    fora = base / "fora"
    dentro.mkdir(parents=True)
    fora.mkdir()
    (dentro / "ok.txt").write_text("ok", encoding="utf-8")
    (fora / "segredo.txt").write_text("arquivo privado: nao pode entrar no video", encoding="utf-8")
    log = c.SANDBOX_DIR / "file-guard-selftest.log"
    if log.exists():
        log.unlink()
    env = c.sandbox_env(
        extra=motor.ambiente(chrome or "chrome.exe", c.versao_navegador(chrome) or "", c.ffmpeg_path(), c.ffprobe_path(), c.SANDBOX_DIR, c.SANDBOX_DIR / "net-guard-selftest.log"),
        path_dirs=[node.parent],
    )
    env.update(c.ambiente_de_arquivos(c.raizes_permitidas(motor, dentro, node, chrome), log))
    env["VBSS_SONDA_FORA"] = str(fora / "segredo.txt")
    env["VBSS_SONDA_DENTRO"] = str(dentro / "ok.txt")
    try:
        r = subprocess.run(motor.comando_selftest_arquivos(node), env=env, cwd=str(c.sandbox_paths()["cwd"]), capture_output=True, text=True, timeout=600)
        try:
            dados = json.loads(r.stdout)
        except json.JSONDecodeError:
            item("auto-teste do guarda de arquivos", False, (r.stdout + r.stderr)[-400:])
            return
        for d in dados:
            detalhe = d["detail"]
            item(f"guarda de arquivos: {d['name']}", d["ok"], detalhe[:140] + ("..." if len(detalhe) > 140 else ""))
        bloqueios = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        esperados = sum(1 for d in dados if d["name"].startswith("bloqueia:"))
        item("cada bloqueio registrado no log do guarda", len(bloqueios) >= esperados, f"{len(bloqueios)} linhas em {log.name} (esperado >= {esperados})")
    finally:
        shutil.rmtree(base, ignore_errors=True)


CASOS_RECUSADOS = {
    "<source> com .. para fora": '<audio id="a"><source src="../fora/tada.wav"></audio>',
    "<source> com caminho de disco": '<audio id="a"><source src="@FORA@"></audio>',
    "<source> com file:": '<audio id="a"><source src="file:///@FORA@"></audio>',
    "<source> com barra invertida": r'<audio id="a"><source src="..\fora\tada.wav"></audio>',
    "<source> com .. codificado": '<audio id="a"><source src="%2e%2e/fora/tada.wav"></audio>',
    "<audio src> absoluto": '<audio id="a" src="/fora/tada.wav"></audio>',
    "<video><source> remoto": '<video id="v"><source src="http://localhost:8080/v.mp4"></video>',
    "<track src> para fora": '<video id="v"><track src="../fora/legenda.vtt"></video>',
    "<img srcset> para fora": '<img srcset="assets/ok.wav 1x, ../fora/tada.wav 2x">',
    "<picture><source srcset> para fora": '<picture><source srcset="../fora/tada.wav"><img src="assets/ok.wav"></picture>',
    "poster para fora": '<video id="v" poster="../fora/tada.wav"></video>',
    "<link href> para fora": '<link rel="stylesheet" href="../fora/estilo.css">',
    "url() em style inline": '<div style="background:url(&quot;../fora/tada.wav&quot;)"></div>',
    "url() em bloco <style>": '<style>.a{background:url(../fora/tada.wav)}</style>',
    "url() com escape CSS": r'<style>.a{background:u\72l(../fora/tada.wav)}</style>',
    "@import em bloco <style>": '<style>@import "../fora/estilo.css";</style>',
    "<base href>": '<base href="file:///C:/">',
    "arquivo que nao existe": '<audio id="a"><source src="assets/nao-existe.wav"></audio>',
    "@import sem espaco": '<style>@import"../fora/estilo.css";</style>',
    "@import com comentario": '<style>@import/**/"../fora/estilo.css";</style>',
    "@import file: sem espaco": '<style>@import"file:///@FORA@";</style>',
    "url/**/( com comentario": '<style>.a{background:url/**/(../fora/tada.wav)}</style>',
    "data-composition-src para fora": '<div data-composition-src="../fora/cena.html"></div>',
    "sub-composicao com caminho de disco": ('<div data-composition-src="sub/cena.html"></div>', {"sub/cena.html": '<template><audio id="s" src="@FORA@"></audio></template>'}),
    "sub-composicao em compositions/ com ..": ('<div data-composition-src="compositions/a.html"></div>', {"compositions/a.html": '<img src="../../fora/tada.wav">'}),
    "<iframe srcdoc> com caminho de disco": '<iframe srcdoc="&lt;img src=&quot;@FORA@&quot;&gt;"></iframe>',
    "atributo SVG filter=url() para fora": '<svg><rect filter="url(../fora/f.svg#f)" width="1" height="1"/></svg>',
    "<meta http-equiv=refresh>": '<meta http-equiv="refresh" content="0;url=assets/ok.wav">',
    "<object data> para fora": '<object data="../fora/f.svg"></object>',
    "entidade HTML no src": '<img src="&#67;:/Windows/x.png">',
    "caminho UNC": '<img src="\\\\servidor\\x.png">',
    "script inline com caminho de disco": '<script>var a=new Audio("@FORA@");</script>',
    "script inline com escape \\x43": '<script>var a=new Audio("\\x43:/Windows/Media/tada.wav");</script>',
    "evento onload com caminho": '<img src="assets/ok.wav" onload="this.src=\'../fora/tada.wav\'">',
    "arquivo .js com ..": ('<script src="assets/a.js"></script>', {"assets/a.js": 'var a = new Audio("../../fora/tada.wav");'}),
    "data:image/svg+xml com caminho dentro": '<img src="data:image/svg+xml,%3Csvg%3E%3Cimage href=%22file:///C:/x.png%22/%3E%3C/svg%3E">',
}
CASOS_ACEITOS = {
    "arquivo dentro de assets/": '<audio id="a"><source src="assets/ok.wav"></audio>',
    "bibliotecas do motor (_motor/)": '<script src="_motor/gsap.min.js"></script><style>@font-face{src:url("_motor/fonts/inter-400.woff2")}</style>',
    "data: e ancora": '<img src="data:image/png;base64,AAAA"><svg><use href="#x"></use></svg>',
    "sub-composicao dentro da pasta": ('<div data-composition-src="sub/cena.html"></div>', {"sub/cena.html": '<template><audio id="s" src="assets/ok.wav"></audio></template>'}),
    "script inline sem caminho": '<script>const tl = gsap.timeline({paused:true}); tl.to("#a", {x: 10, ease: "power2.out"}, "+=0.5"); window.__timelines = {"x": tl};</script>',
}


def checar_midias_fora():
    c.titulo("Midia da composicao (arquivo fora da pasta e recusado)")
    base = c.SANDBOX_DIR / "selftest-midias"
    if base.exists():
        shutil.rmtree(base)
    comp = base / "comp"
    (comp / "assets").mkdir(parents=True)
    (base / "fora").mkdir()
    (comp / "assets" / "ok.wav").write_bytes(WAV_MINIMO)
    for nome in ("tada.wav", "legenda.vtt", "estilo.css"):
        (base / "fora" / nome).write_bytes(b"x")
    fora = (base / "fora" / "tada.wav").resolve().as_posix()

    def montar(caso):
        trecho, extras = caso if isinstance(caso, tuple) else (caso, {})
        for pasta in [p for p in comp.iterdir() if p.is_dir() and p.name != "assets"]:
            shutil.rmtree(pasta)
        for arq in (comp / "assets").glob("*.js"):
            arq.unlink()
        (comp / "index.html").write_text("<div id=\"root\">" + trecho.replace("@FORA@", fora) + "</div>", encoding="utf-8")
        for rel, conteudo in extras.items():
            (comp / rel).parent.mkdir(parents=True, exist_ok=True)
            (comp / rel).write_text(conteudo.replace("@FORA@", fora), encoding="utf-8")
        return midias.checar_composicao(comp)[1]

    try:
        for nome, caso in CASOS_RECUSADOS.items():
            problemas = montar(caso)
            item(f"recusa: {nome}", bool(problemas), problemas[0][:110] if problemas else "PASSOU SEM AVISO")
        for nome, caso in CASOS_ACEITOS.items():
            problemas = montar(caso)
            item(f"aceita: {nome}", not problemas, "; ".join(problemas)[:110])
        montar(f'<audio id="a"><source src="{fora}"></audio>')
        r = subprocess.run([sys.executable, str(c.VIDEO_DIR / "render.py"), str(comp), str(base / "saida.mp4")], capture_output=True, text=True, timeout=120)
        item("render.py para antes de abrir o navegador", r.returncode != 0 and "midia da composicao com problema" in r.stdout + r.stderr and "Renderizando" not in r.stdout,
             f"codigo {r.returncode}")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def hls(segmento):
    linhas = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-X-TARGETDURATION:4", "#EXT-X-MEDIA-SEQUENCE:0", "#EXTINF:4.0,", segmento, "#EXT-X-ENDLIST"]
    return "\n".join(linhas) + "\n"


def checar_tipos_de_arquivo():
    c.titulo("Tipos de arquivo da composicao (so a lista permitida chega ao motor)")
    base = c.SANDBOX_DIR / "selftest-tipos"
    if base.exists():
        shutil.rmtree(base)
    comp = base / "comp"
    (comp / "assets").mkdir(parents=True)
    (base / "fora").mkdir()
    (base / "fora" / "fora.ts").write_bytes(b"x")
    fora_ts = (base / "fora" / "fora.ts").resolve().as_posix()
    (comp / "assets" / "ok.wav").write_bytes(WAV_MINIMO)
    refusas = {
        "h01 playlist HLS de audio apontando para fora": ('<audio id="zh" src="assets/trilha.m3u8"></audio>', {"assets/trilha.m3u8": hls(fora_ts)}),
        "h03 playlist HLS de video apontando para fora": ('<video id="zv" src="assets/clip.m3u8" muted></video>', {"assets/clip.m3u8": hls(fora_ts)}),
        "playlist .m3u": ('<audio id="a" src="assets/ok.wav"></audio>', {"assets/lista.m3u": "x"}),
        "lista ffconcat": ('<audio id="a" src="assets/ok.wav"></audio>', {"assets/lista.ffconcat": f"file '{fora_ts}'"}),
        "ffconcat disfarcado de .wav": ('<audio id="a" src="assets/falso.wav"></audio>', {"assets/falso.wav": f"ffconcat version 1.0\nfile '{fora_ts}'\n"}),
        "playlist disfarcada de .txt": ('<audio id="a" src="assets/ok.wav"></audio>', {"assets/nota.txt": hls(fora_ts)}),
        "playlist com BOM e espaco": ('<audio id="a" src="assets/ok.wav"></audio>', {"assets/nota.json": "﻿  \n" + hls(fora_ts)}),
        "tipo desconhecido (.ts)": ('<audio id="a" src="assets/ok.wav"></audio>', {"assets/seg.ts": "x"}),
        "manifesto DASH disfarcado de .wav (100 quebras de linha antes)": ('<audio id="a" src="assets/fala.wav"></audio>', {"assets/fala.wav": "\n" * 100 + '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"><Period><AdaptationSet><Representation><BaseURL>../fora/fora.ts</BaseURL></Representation></AdaptationSet></Period></MPD>'}),
        "arquivo sem extensao": ('<audio id="a" src="assets/ok.wav"></audio>', {"assets/semext": "x"}),
    }
    aceitas = {
        "composicao normal (html, json, txt, png, wav, mp4, woff2)": ('<audio id="a" src="assets/ok.wav"></audio>', {"trilha.json": "{}", "voz.txt": "narracao", "assets/a.png": PNG_MINIMO, "assets/c.mp4": MP4_MINIMO, "assets/f.woff2": WOFF2_MINIMO}),
    }

    def montar(trecho, extras):
        shutil.rmtree(comp)
        (comp / "assets").mkdir(parents=True)
        (comp / "assets" / "ok.wav").write_bytes(WAV_MINIMO)
        (comp / "index.html").write_text("<div id=\"root\">" + trecho + "</div>", encoding="utf-8")
        for rel, conteudo in extras.items():
            if isinstance(conteudo, bytes):
                (comp / rel).write_bytes(conteudo)
            else:
                (comp / rel).write_text(conteudo, encoding="utf-8", newline="\n")

    try:
        for nome, (trecho, extras) in refusas.items():
            montar(trecho, extras)
            copiar, problemas = arquivos.inventariar(comp)
            item(f"recusa: {nome}", bool(problemas), problemas[0][:110] if problemas else "PASSOU SEM AVISO")
        for nome, (trecho, extras) in aceitas.items():
            montar(trecho, extras)
            copiar, problemas = arquivos.inventariar(comp)
            item(f"aceita: {nome}", not problemas and len(copiar) == len(extras) + 2, "; ".join(problemas)[:110] or f"{len(copiar)} arquivos")
        montar('<audio id="zh" src="assets/trilha.m3u8" data-start="0" data-duration="1"></audio>', {"assets/trilha.m3u8": hls(fora_ts)})
        r = subprocess.run([sys.executable, str(c.VIDEO_DIR / "render.py"), str(comp), str(base / "saida.mp4")], capture_output=True, text=True, timeout=120)
        saida = r.stdout + r.stderr
        item("render.py recusa a copia h01 antes de abrir o navegador", r.returncode != 0 and "trilha.m3u8" in saida and "Renderizando" not in saida, f"codigo {r.returncode}")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def checar_gitignore():
    c.titulo("Repositorio")
    gi = c.REPO_DIR / ".gitignore"
    texto = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    precisa = ["content-engine/video/.sandbox/", "content-engine/video/.cache/", "content-engine/video/bin/", "content-engine/video/engines/*/node_modules/", "content-engine/browser/"]
    faltam = [p for p in precisa if p not in texto]
    item(".gitignore ignora sandbox, cache, binarios, node_modules e navegador fixo", not faltam, "faltam: " + ", ".join(faltam) if faltam else str(gi))


def main():
    print("Diagnostico do motor de video local do vbss-media-engine")
    node = checar_base()
    checar_ffmpeg()
    chrome = checar_chrome()
    motor = checar_motor(node)
    checar_isolamento(motor, node, chrome)
    checar_guarda_arquivos(motor, node, chrome)
    checar_midias_fora()
    checar_tipos_de_arquivo()
    checar_gitignore()
    falhas = resultados.count(False)
    print(f"\nResultado: {len(resultados) - falhas} PASS, {falhas} FAIL")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
