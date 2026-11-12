import json
import shutil
from pathlib import Path

from comum import fontes as fontes_comuns

NOME = "hyperframes"
VERSAO_CLI = "0.8.141"
DIR = Path(__file__).resolve().parent
NODE_MODULES = DIR / "node_modules"
CLI = NODE_MODULES / "hyperframes" / "bin" / "hyperframes.mjs"
NET_GUARD = DIR / "net-guard.cjs"
NET_GUARD_SELFTEST = DIR / "net-guard-selftest.cjs"
FILE_GUARD = DIR / "file-guard.cjs"
FILE_GUARD_SELFTEST = DIR / "file-guard-selftest.cjs"
GUIA = DIR / "guia" / "README.md"

SUBCOMANDOS_PERMITIDOS = frozenset({"render"})
QUALIDADES = {"rascunho": "draft", "padrao": "looks", "final": "delivery"}

VENDOR = {
    "gsap.min.js": "gsap/dist/gsap.min.js",
    "CustomEase.min.js": "gsap/dist/CustomEase.min.js",
    "SplitText.min.js": "gsap/dist/SplitText.min.js",
    "TextPlugin.min.js": "gsap/dist/TextPlugin.min.js",
    "ScrambleTextPlugin.min.js": "gsap/dist/ScrambleTextPlugin.min.js",
    "DrawSVGPlugin.min.js": "gsap/dist/DrawSVGPlugin.min.js",
    "MorphSVGPlugin.min.js": "gsap/dist/MorphSVGPlugin.min.js",
    "MotionPathPlugin.min.js": "gsap/dist/MotionPathPlugin.min.js",
    "Flip.min.js": "gsap/dist/Flip.min.js",
}
PASTA_VENDOR = "_motor"


def comando_instalacao(node, npm_cli):
    acao = "ci" if (DIR / "package-lock.json").is_file() else "install"
    base = [str(node), str(npm_cli)] if npm_cli else ["npm.cmd"]
    return base + [acao, "--ignore-scripts", "--no-audit", "--no-fund", "--no-update-notifier"], DIR


def versao_instalada():
    pkg = NODE_MODULES / "hyperframes" / "package.json"
    if not pkg.is_file():
        return None
    return json.loads(pkg.read_text(encoding="utf-8")).get("version")


def checar():
    itens = []
    lock = DIR / "package-lock.json"
    pin_lock = None
    if lock.is_file():
        data = json.loads(lock.read_text(encoding="utf-8"))
        pin_lock = data.get("packages", {}).get("node_modules/hyperframes", {}).get("version")
    itens.append(("lockfile fixa hyperframes", pin_lock == VERSAO_CLI, f"package-lock.json -> {pin_lock}"))
    instalada = versao_instalada()
    itens.append(("CLI do motor instalada na versao fixada", instalada == VERSAO_CLI, f"{instalada} (esperado {VERSAO_CLI})"))
    faltando = [k for k, v in VENDOR.items() if not (NODE_MODULES / v).is_file()]
    itens.append(("GSAP local (_motor/)", not faltando, "ok" if not faltando else f"faltando: {', '.join(faltando)}"))
    problemas = fontes_comuns.conferir()
    itens.append(("fontes locais compartilhadas (_motor/fonts/)", not problemas,
                  f"{len(fontes_comuns.arquivos())} arquivos em {fontes_comuns.FONTES_DIR}" if not problemas else "; ".join(problemas)))
    itens.append(("net-guard presente", NET_GUARD.is_file(), str(NET_GUARD)))
    itens.append(("file-guard presente", FILE_GUARD.is_file(), str(FILE_GUARD)))
    itens.append(("guia de autoria presente", GUIA.is_file(), str(GUIA)))
    return itens


def preparar(stage_dir):
    destino = Path(stage_dir) / PASTA_VENDOR
    if destino.exists():
        shutil.rmtree(destino)
    for alvo, origem in VENDOR.items():
        dst = destino / alvo
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(NODE_MODULES / origem, dst)
    for nome, origem in fontes_comuns.arquivos().items():
        dst = destino / "fonts" / nome
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem, dst)
    return destino


def ambiente(chrome, chrome_versao, ffmpeg, ffprobe, sandbox_dir, guard_log):
    return {
        "HYPERFRAMES_NO_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "HYPERFRAMES_NO_UPDATE_CHECK": "1",
        "HYPERFRAMES_NO_AUTO_INSTALL": "1",
        "HYPERFRAMES_SKIP_SKILLS": "1",
        "HYPERFRAMES_BROWSER_PATH": str(chrome),
        "VBSS_BROWSER_VERSION": chrome_versao or "",
        "FFMPEG_PATH": str(ffmpeg),
        "FFPROBE_PATH": str(ffprobe),
        "HYPERFRAMES_FFMPEG_PATH": str(ffmpeg),
        "HYPERFRAMES_FFPROBE_PATH": str(ffprobe),
        "HYPERFRAMES_FONT_CACHE_DIR": str(Path(sandbox_dir) / "fonts"),
        "HYPERFRAMES_MEDIA_HOME": str(Path(sandbox_dir) / "media"),
        "PRODUCER_RENDERS_DIR": str(Path(sandbox_dir) / "renders"),
        "PUPPETEER_SKIP_DOWNLOAD": "1",
        "PUPPETEER_CACHE_DIR": str(Path(sandbox_dir) / "puppeteer"),
        "BROWSER": "none",
        "HF_NO_BROWSER": "1",
        "CI": "1",
        "VBSS_NET_GUARD_LOG": str(guard_log),
        "NODE_OPTIONS": f'--require "{NET_GUARD.as_posix()}" --require "{FILE_GUARD.as_posix()}"',
    }


def _preloads():
    return ["--require", str(NET_GUARD), "--require", str(FILE_GUARD)]


def comando(node, subcomando, argumentos):
    if subcomando not in SUBCOMANDOS_PERMITIDOS:
        raise ValueError(f"subcomando '{subcomando}' do motor nao e permitido (so {sorted(SUBCOMANDOS_PERMITIDOS)})")
    return [str(node), *_preloads(), str(CLI), subcomando, *argumentos]


def comando_render(node, stage_dir, saida, fps, qualidade):
    args = [
        str(stage_dir),
        "--output", str(saida),
        "--format", "mp4",
        "--fps", str(fps),
        "--quality", QUALIDADES[qualidade],
        "--strict",
        "--lint-verbose",
    ]
    return comando(node, "render", args)


def comando_selftest(node):
    return [str(node), "--require", str(NET_GUARD), str(NET_GUARD_SELFTEST)]


def comando_selftest_arquivos(node):
    return [str(node), *_preloads(), str(FILE_GUARD_SELFTEST)]
