import ctypes
import json
import os
from pathlib import Path

from comum import navegador as _fixo

PROXY_SUMIDOURO = "http://127.0.0.1:9"

RECURSOS_DESLIGADOS = (
    "OptimizationHints", "OptimizationGuideModelDownloading", "MediaRouter", "DialMediaRouteProvider",
    "AutofillServerCommunication", "CertificateTransparencyComponentUpdater", "InterestFeedContentSuggestions",
    "NetworkTimeServiceQuerying", "SafeBrowsingEnhancedProtection",
)

FLAGS_ISOLAMENTO = (
    f"--proxy-server={PROXY_SUMIDOURO}",
    "--proxy-bypass-list=localhost;127.0.0.1;[::1]",
    "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1",
    "--disable-background-networking",
    "--disable-client-side-phishing-detection",
    "--disable-component-update",
    "--disable-domain-reliability",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-pings",
    "--no-first-run",
    "--no-default-browser-check",
    "--safebrowsing-disable-auto-update",
    "--webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--force-webrtc-ip-handling-policy",
)

FLAGS_PROIBIDAS = ("--no-sandbox", "--disable-setuid-sandbox", "--no-zygote")
ENV_ISOLAMENTO = "VBSS_CHROME_ISOLAMENTO"
AVISO_SISTEMA = "rode o setup para usar o navegador fixo (python content-engine/imagem/setup.py ou python content-engine/video/setup.py)"


def flags_chrome():
    return [*FLAGS_ISOLAMENTO, f"--disable-features={','.join(RECURSOS_DESLIGADOS)}"]


def isolamento_env():
    dados = {"flags": list(FLAGS_ISOLAMENTO), "recursos_desligados": list(RECURSOS_DESLIGADOS)}
    return {ENV_ISOLAMENTO: json.dumps(dados, separators=(",", ":"))}


def flags_faltando(args):
    args = list(args)
    faltam = [f for f in FLAGS_ISOLAMENTO if f not in args]
    recursos = next((a for a in args if a.startswith("--disable-features=")), "")
    ligados = recursos.split("=", 1)[-1].split(",")
    faltam += [f"--disable-features:{r}" for r in RECURSOS_DESLIGADOS if r not in ligados]
    faltam += [f"(remover) {f}" for f in FLAGS_PROIBIDAS if f in args]
    return faltam


def chrome_candidates():
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    cands = [
        Path(pf) / "Google/Chrome/Application/chrome.exe",
        Path(pf86) / "Google/Chrome/Application/chrome.exe",
    ]
    if local:
        cands.append(Path(local) / "Google/Chrome/Application/chrome.exe")
    cands += [
        Path(pf86) / "Microsoft/Edge/Application/msedge.exe",
        Path(pf) / "Microsoft/Edge/Application/msedge.exe",
    ]
    return cands


def navegador_fixo():
    return _fixo.instalado()


def find_chrome():
    for var in ("VBSS_BROWSER", "VBSS_VIDEO_BROWSER"):
        override = os.environ.get(var)
        if override and Path(override).is_file():
            return Path(override)
    fixo = navegador_fixo()
    if fixo:
        return fixo
    for cand in chrome_candidates():
        if cand.is_file():
            return cand
    return None


def file_version(path):
    if os.name != "nt" or path is None:
        return None
    try:
        ver = ctypes.windll.version
        size = ver.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        ver.GetFileVersionInfoW(str(path), 0, size, buf)
        ptr = ctypes.c_void_p()
        length = ctypes.c_uint()
        ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length))
        fixed = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32 * 13)).contents
        ms, ls = fixed[4], fixed[5]
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except OSError:
        return None


def e_navegador_fixo(path):
    fixo = navegador_fixo()
    return bool(path and fixo and Path(path).resolve() == fixo.resolve())


def versao_navegador(path):
    if path is None:
        return None
    if e_navegador_fixo(path):
        return file_version(path) or _fixo.fixado()["versao"]
    return file_version(path)


def descrever_navegador(path):
    if path is None:
        return "nenhum navegador encontrado"
    tipo = f"navegador fixo {_fixo.fixado()['nome']}" if e_navegador_fixo(path) else "navegador do sistema (nao fixado)"
    return f"{tipo} {versao_navegador(path) or '(versao desconhecida)'} em {path}"
