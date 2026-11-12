import argparse
import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode = True

BASE = Path(__file__).resolve().parent
PIN = json.loads((BASE / "pin.json").read_text(encoding="utf-8"))
REPO = BASE / "repo"
LOCAL = BASE / ".local"
DOWNLOADS = LOCAL / "downloads"
UV = LOCAL / "ferramentas" / "uv" / "uv.exe"
BUN = LOCAL / "ferramentas" / "bun" / "bun.exe"
DADOS = LOCAL / "dados"
MODELOS = LOCAL / "hf"
LOGS = LOCAL / "logs"
TMP = LOCAL / "tmp"
CACHE = LOCAL / "cache"
ENV_FILE = LOCAL / "omnivoice.env"
PREFS = DADOS / "prefs.json"
RUN = LOCAL / "run.json"
VENV_PY = REPO / ".venv" / "Scripts" / "python.exe"
FFMPEG_DIR = BASE.parent / "content-engine" / "video" / "bin"
PORTA_API = PIN["portas"]["api"]
PORTA_WEB = PIN["portas"]["web"]
PROXY_MORTO = "http://127.0.0.1:9"
LOOPBACK = "127.0.0.1,localhost,::1"
CHAVES_DE_REDE = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE", "UV_OFFLINE")
FORA_DA_PASTA = [
    Path(os.environ.get("APPDATA", "")) / "OmniVoice",
    Path(os.environ.get("APPDATA", "")) / "VoiceStudio",
    Path(os.environ.get("LOCALAPPDATA", "")) / "OmniVoice",
    Path(os.environ.get("LOCALAPPDATA", "")) / "VoiceStudio",
    Path.home() / ".config" / "omnivoice",
    Path.home() / ".omnivoice",
]

falhas = []


def titulo(texto):
    print(f"\n== {texto}")


def linha(status, nome, detalhe=""):
    print(f"  {status:<5} {nome}" + (f": {detalhe}" if detalhe else ""))


def item(nome, ok, detalhe="", aviso=False):
    status = "PASS" if ok else ("AVISO" if aviso else "FAIL")
    if not ok and not aviso:
        falhas.append(nome)
    linha(status, nome, detalhe)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_json(path, padrao=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def escrever_json(path, dados):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ambiente(online):
    env = {k: v for k, v in os.environ.items() if k.upper() not in CHAVES_DE_REDE}
    pastas = {
        "OMNIVOICE_DATA_DIR": DADOS,
        "OMNIVOICE_CACHE_DIR": MODELOS,
        "OMNIVOICE_LOG_DIR": LOGS,
        "OMNIVOICE_ENV_FILE": ENV_FILE,
        "HF_HOME": MODELOS,
        "HF_HUB_CACHE": MODELOS,
        "TORCH_HOME": MODELOS,
        "XDG_CACHE_HOME": CACHE / "xdg",
        "XDG_CONFIG_HOME": LOCAL / "config",
        "XDG_DATA_HOME": LOCAL / "share",
        "TEMP": TMP,
        "TMP": TMP,
        "UV_CACHE_DIR": CACHE / "uv",
        "UV_PYTHON_INSTALL_DIR": LOCAL / "python",
        "UV_PYTHON_BIN_DIR": LOCAL / "python" / "bin",
        "UV_TOOL_DIR": LOCAL / "uv-tools",
        "BUN_INSTALL": LOCAL / "bun-home",
        "BUN_INSTALL_CACHE_DIR": CACHE / "bun",
    }
    env.update({k: str(v) for k, v in pastas.items()})
    env.update({
        "UV_PYTHON_PREFERENCE": "only-managed",
        "UV_NO_MODIFY_PATH": "1",
        "PYTHONNOUSERSITE": "1",
        "OMNIVOICE_BIND_HOST": "127.0.0.1",
        "OMNIVOICE_PORT": str(PORTA_API),
        "OMNIVOICE_UI_PORT": str(PORTA_WEB),
        "OMNIVOICE_ANALYTICS_DISABLED": "1",
        "POSTHOG_HOST": PROXY_MORTO,
        "VITE_POSTHOG_HOST": PROXY_MORTO,
        "OMNIVOICE_HF_ENDPOINT_MODE": "manual",
        "HF_ENDPOINT": "https://huggingface.co",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "GRADIO_ANALYTICS_ENABLED": "False",
        "OMNIVOICE_MCP_DISABLE": "1",
        "OMNIVOICE_PRELOAD_WATERMARK": "0",
        "OMNIVOICE_PRELOAD_CAPTURE_ASR": "0",
        "VOICESTUDIO_DISABLE_UPDATER": "1",
        "ELECTRON_SKIP_BINARY_DOWNLOAD": "1",
    })
    extras = [str(BUN.parent), str(UV.parent)] + ([str(FFMPEG_DIR)] if FFMPEG_DIR.is_dir() else [])
    env["PATH"] = os.pathsep.join(extras + [env.get("PATH", "")])
    if not online:
        env.update({
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "UV_OFFLINE": "1",
            "HTTP_PROXY": PROXY_MORTO,
            "HTTPS_PROXY": PROXY_MORTO,
            "ALL_PROXY": PROXY_MORTO,
            "NO_PROXY": LOOPBACK,
        })
    for pasta in (DADOS, MODELOS, LOGS, TMP, CACHE):
        pasta.mkdir(parents=True, exist_ok=True)
    return env


def rodar(cmd, env, cwd=REPO):
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env)
    if r.returncode:
        raise SystemExit(f"falhou (codigo {r.returncode}): {cmd[0]} {cmd[1] if len(cmd) > 1 else ''}")


def git(*args, cwd=REPO):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} falhou:\n{r.stderr.strip()}")
    return r.stdout.strip()


def baixar_conferido(url, sha_esperado):
    destino = DOWNLOADS / url.rsplit("/", 1)[1]
    if not destino.is_file() or sha256(destino) != sha_esperado:
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_name(destino.name + ".part")
        print(f"baixando {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "vbss-media-engine-voicestudio"})
        with urllib.request.urlopen(req, timeout=300) as r, open(parcial, "wb") as f:
            shutil.copyfileobj(r, f)
        parcial.replace(destino)
    real = sha256(destino)
    if real != sha_esperado:
        destino.unlink()
        raise SystemExit(f"SHA-256 diferente do pin em {url}\n  esperado {sha_esperado}\n  recebido {real}")
    return destino


def versao(exe):
    try:
        return subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except OSError:
        return ""


def instalar_ferramenta(nome, exe):
    cfg = PIN[nome]
    if exe.is_file() and cfg["versao"] in versao(exe):
        print(f"{nome} {cfg['versao']} ja instalado")
        return
    pacote = baixar_conferido(cfg["url"], cfg["sha256"])
    with zipfile.ZipFile(pacote) as z:
        membro = next(n for n in z.namelist() if n.rsplit("/", 1)[-1] == exe.name)
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(z.read(membro))
    if cfg["versao"] not in versao(exe):
        raise SystemExit(f"{nome} instalado nao responde a versao {cfg['versao']}")
    print(f"{nome} {cfg['versao']} instalado em {exe.parent}")


def buscar_repo():
    if not (REPO / ".git").exists():
        REPO.mkdir(parents=True, exist_ok=True)
        git("init", "-q")
        git("config", "core.longpaths", "true")
        git("config", "core.autocrlf", "false")
        print(f"buscando {PIN['repo']} @ {PIN['commit'][:8]}")
        git("fetch", "-q", "--depth", "1", "--no-tags", PIN["repo"], PIN["commit"])
        git("checkout", "-q", "--detach", "FETCH_HEAD")
    for nome, ok, detalhe in estado_do_pin():
        if not ok:
            raise SystemExit(f"repo fora do pin: {nome} ({detalhe})")
    print(f"repo pinado em {PIN['commit'][:8]} ({PIN['commit_data']}), sem remote")


def estado_do_pin():
    head = git("rev-parse", "HEAD")
    remotes = git("remote")
    alterados = git("status", "--porcelain", "--untracked-files=no")
    return [
        ("commit do pin", head == PIN["commit"], head[:12]),
        ("sem remote (nada de pull/fetch por engano)", not remotes, remotes or "nenhum"),
        ("arquivos versionados intactos", not alterados, "nenhum alterado" if not alterados else alterados.replace("\n", "; ")[:300]),
    ]


def preparar_dados():
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.touch(exist_ok=True)
    prefs = ler_json(PREFS, {}) or {}
    if "watermark.invisible" not in prefs:
        prefs["watermark.invisible"] = False
        escrever_json(PREFS, prefs)


def cmd_instalar(args):
    if sys.platform != "win32":
        raise SystemExit("este script e para Windows")
    for pasta in (LOCAL, DOWNLOADS, TMP):
        pasta.mkdir(parents=True, exist_ok=True)
    instalar_ferramenta("uv", UV)
    if args.web:
        instalar_ferramenta("bun", BUN)
    buscar_repo()
    env = ambiente(online=True)
    rodar([UV, "sync", "--locked", "--no-default-groups", "--group", "cpu", "--python", PIN["python"]], env)
    if args.web:
        rodar([BUN, "install", "--frozen-lockfile", "--ignore-scripts"], env)
    preparar_dados()
    for nome, ok, detalhe in estado_do_pin():
        item(nome, ok, detalhe)
    print("\npronto. proximo passo: python voicestudio/voicestudio.py modelos")
    return 1 if falhas else 0


SEM_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))
URL_API = f"http://127.0.0.1:{PORTA_API}"


def api(metodo, rota, json_corpo=None, corpo=None, tipo=None, timeout=60):
    dados = json.dumps(json_corpo, ensure_ascii=False).encode("utf-8") if json_corpo is not None else corpo
    cabecalhos = {"Content-Type": "application/json; charset=utf-8"} if json_corpo is not None else ({"Content-Type": tipo} if tipo else {})
    req = urllib.request.Request(URL_API + rota, data=dados, headers=cabecalhos, method=metodo)
    try:
        with SEM_PROXY.open(req, timeout=timeout) as r:
            conteudo = r.read()
            return conteudo if "json" not in r.headers.get("Content-Type", "") else json.loads(conteudo)
    except urllib.error.HTTPError as erro:
        raise SystemExit(f"{metodo} {rota} -> {erro.code}: {erro.read().decode('utf-8', 'replace')[:500]}")
    except urllib.error.URLError as erro:
        raise SystemExit(f"API fora do ar em {URL_API} ({erro.reason}): rode python voicestudio/voicestudio.py subir")


def formulario(campos, arquivo_campo, arquivo):
    limite = "----vbss-media-engine-voicestudio"
    partes = [f"--{limite}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8") for k, v in campos.items()]
    partes += [
        f"--{limite}\r\nContent-Disposition: form-data; name=\"{arquivo_campo}\"; filename=\"{arquivo.name}\"\r\nContent-Type: audio/wav\r\n\r\n".encode("utf-8"),
        arquivo.read_bytes(),
        f"\r\n--{limite}--\r\n".encode("utf-8"),
    ]
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def api_no_ar():
    try:
        with SEM_PROXY.open(URL_API + "/health", timeout=5) as r:
            return r.status == 200
    except OSError:
        return False


def iniciar_backend(online, log=None):
    env = ambiente(online=online)
    saida = open(log, "w", encoding="utf-8") if log else None
    return subprocess.Popen(
        [str(VENV_PY), "-m", "uvicorn", "main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", str(PORTA_API)],
        cwd=REPO, env=env, stdout=saida, stderr=subprocess.STDOUT if saida else None)


def esperar_api(proc, limite=300):
    fim = time.time() + limite
    while time.time() < fim:
        if proc.poll() is not None:
            raise SystemExit(f"backend saiu com codigo {proc.returncode}")
        if api_no_ar():
            return
        time.sleep(2)
    raise SystemExit("backend nao respondeu a tempo")


def aceitar_licenca(repo_id):
    estado = api("GET", f"/models/licenses/acceptance/{repo_id}")
    linha("INFO", repo_id, f"licenca: {estado.get('license')} ({estado.get('category')})")
    if not estado.get("required") or estado.get("accepted"):
        return
    api("POST", "/models/licenses/accept", {"repo_id": repo_id, "fingerprint": estado["fingerprint"], "accepted": True})
    linha("INFO", repo_id, "termos aceitos")


def instalar_modelo(repo_id):
    instalados = {m["repo_id"] for m in api("GET", "/models").get("models", []) if m.get("installed")}
    if repo_id in instalados:
        linha("PASS", repo_id, "ja baixado")
        return
    api("POST", "/models/install", {"repo_id": repo_id})
    print(f"  baixando {repo_id}...", flush=True)
    while any(j["repo_id"] == repo_id for j in api("GET", "/models/install/status").get("jobs", [])):
        time.sleep(5)
    instalados = {m["repo_id"] for m in api("GET", "/models").get("models", []) if m.get("installed")}
    item(repo_id, repo_id in instalados, "baixado" if repo_id in instalados else "falhou, veja .local/logs")


def cmd_modelos(args):
    if not VENV_PY.is_file():
        raise SystemExit("rode instalar antes")
    if api_no_ar():
        raise SystemExit("ja tem VoiceStudio rodando: python voicestudio/voicestudio.py parar")
    titulo("Modelos do pin.json (backend temporario ONLINE)")
    proc = iniciar_backend(online=True, log=LOGS / "modelos.log")
    try:
        esperar_api(proc)
        for repo_id in PIN["modelos"]:
            aceitar_licenca(repo_id)
            instalar_modelo(repo_id)
        criadas = sincronizar_vozes()
        linha("INFO", "vozes da casa", ", ".join(criadas) + " criada(s)" if criadas else "ja estavam criadas")
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    print("\nbackend temporario encerrado. suba com: python voicestudio/voicestudio.py subir")
    return 1 if falhas else 0


def para_wav(origem, destino):
    ffmpeg = FFMPEG_DIR / "ffmpeg.exe"
    if not ffmpeg.is_file():
        raise SystemExit("ffmpeg local ausente: rode python content-engine/video/setup.py")
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(ffmpeg), "-y", "-v", "error", "-i", str(origem), "-ac", "1", "-ar", "24000", str(destino)], check=True)
    info = subprocess.run([str(FFMPEG_DIR / "ffprobe.exe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(destino)],
                          capture_output=True, text=True).stdout.strip()
    return float(info or 0)


VOZES_DIR = BASE / "vozes"
VOZES_JSON = VOZES_DIR / "vozes.json"
SEED = 7
FRASE_PADRAO = "Oi! Hoje eu vou te mostrar um jeito simples de organizar as suas tarefas da semana e acompanhar o que já foi feito. Bora começar?"
GENEROS = {"feminina": "female", "masculina": "male"}
IDADES = {"crianca": "child", "adolescente": "teenager", "jovem": "young adult", "adulta": "middle-aged", "idosa": "elderly"}
TONS = {"muito-grave": "very low pitch", "grave": "low pitch", "medio": "moderate pitch", "agudo": "high pitch", "muito-agudo": "very high pitch"}


def vozes_da_casa():
    return ler_json(VOZES_JSON, {}) or {}


def perfis():
    return {p["name"]: p for p in api("GET", "/profiles")}


def criar_perfil(nome, referencia, texto):
    campos = {"name": nome, "ref_text": texto, "language": "pt", "kind": "clone"}
    corpo, tipo = formulario(campos, "ref_audio", referencia)
    return api("POST", "/profiles", corpo=corpo, tipo=tipo, timeout=600)


def sincronizar_vozes():
    existentes = perfis()
    criadas = []
    for nome, voz in vozes_da_casa().items():
        if nome not in existentes:
            criar_perfil(nome, VOZES_DIR / voz["arquivo"], voz["texto"])
            criadas.append(nome)
    return criadas


def validar_nome_novo(nome):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,30}", nome):
        raise SystemExit("nome da voz: so letras minusculas, numeros e hifen (ex.: casa, narradora, locutora-2)")
    if nome in vozes_da_casa() or nome in perfis():
        raise SystemExit(f"ja existe uma voz '{nome}': escolha outro nome")


def guardar_voz(nome, referencia, texto, origem):
    VOZES_DIR.mkdir(exist_ok=True)
    destino = VOZES_DIR / f"{nome}.wav"
    shutil.copyfile(referencia, destino)
    vozes = vozes_da_casa()
    vozes[nome] = {"arquivo": destino.name, "texto": texto, "origem": origem, "criada": time.strftime("%Y-%m-%d")}
    escrever_json(VOZES_JSON, vozes)
    criar_perfil(nome, destino, texto)
    return destino


@contextmanager
def sessao_api():
    if api_no_ar():
        sincronizar_vozes()
        yield False
        return
    for nome, ok, detalhe in estado_do_pin():
        if not ok:
            raise SystemExit(f"repo fora do pin, recusando subir: {nome} ({detalhe})")
    print("subindo a API local (uns 20 s)...", flush=True)
    proc = iniciar_backend(online=False, log=LOGS / "sessao.log")
    try:
        esperar_api(proc)
        sincronizar_vozes()
        yield True
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)


def gerar(texto, voz, destino, seed=SEED, instrucoes="", velocidade=1.0):
    corpo = {"model": "omnivoice", "input": texto, "voice": voz, "language": "pt", "response_format": "wav", "seed": seed}
    if instrucoes:
        corpo["instructions"] = instrucoes
    if abs(velocidade - 1.0) > 1e-6:
        corpo["speed"] = velocidade
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(api("POST", "/v1/audio/speech", corpo, timeout=900))
    return destino


def tocar(arquivo):
    try:
        os.startfile(str(arquivo))
    except OSError:
        pass


def cmd_clonar(args):
    origem = Path(args.audio).resolve()
    if not origem.is_file():
        raise SystemExit(f"arquivo nao encontrado: {origem}")
    referencia = LOCAL / "referencias" / f"{args.nome}.wav"
    segundos = para_wav(origem, referencia)
    if not 3 <= segundos <= 20:
        raise SystemExit(f"referencia com {segundos:.1f}s: grave entre 3 e 20 segundos (ideal 8 a 12)")
    with sessao_api():
        validar_nome_novo(args.nome)
        if args.guardar:
            guardar_voz(args.nome, referencia, args.texto, f"clone de {origem.name}")
        else:
            criar_perfil(args.nome, referencia, args.texto)
    print(f"voz '{args.nome}' criada a partir de {segundos:.1f}s de referencia" + (" e guardada em voicestudio/vozes (vai pro git)" if args.guardar else " (so neste PC)"))
    print(f'teste: python voicestudio/voicestudio.py falar "Ola, este e um teste de voz." --voz {args.nome}')
    return 0


def cmd_falar(args):
    saida = Path(args.saida) if args.saida else LOCAL / "saida" / f"{args.voz}-{time.strftime('%Y%m%d-%H%M%S')}.wav"
    with sessao_api():
        inicio = time.time()
        gerar(args.texto, args.voz, saida, seed=args.seed, instrucoes=args.instrucoes)
    print(f"{saida} ({time.time() - inicio:.0f}s pra gerar)")
    if args.tocar:
        tocar(saida)
    return 0


def cmd_voz(args):
    if args.listar:
        vozes = vozes_da_casa()
        for nome, voz in vozes.items():
            print(f"  {nome}: {voz['origem']} (criada {voz['criada']})")
        if not vozes:
            print("  nenhuma voz guardada ainda")
        return 0
    atributos = [GENEROS[args.genero], IDADES[args.idade], TONS[args.tom]] + (["whisper"] if args.sussurro else [])
    rotulo = f"{args.genero}-{args.idade}-{args.tom}{'-sussurro' if args.sussurro else ''}-seed{args.seed}"
    amostra = LOCAL / "saida" / "vozes-teste" / f"{rotulo}.wav"
    receita = amostra.with_suffix(".json")
    pedido = {"frase": args.frase, "atributos": atributos, "seed": args.seed}
    with sessao_api():
        if args.salvar:
            validar_nome_novo(args.salvar)
        if not (amostra.is_file() and ler_json(receita) == pedido):
            print(f"gerando {rotulo} (30 a 80 s na CPU)...", flush=True)
            gerar(args.frase, "alloy", amostra, seed=args.seed, instrucoes=", ".join(atributos))
            escrever_json(receita, pedido)
        if args.salvar:
            guardar_voz(args.salvar, amostra, args.frase, f"design: {args.genero}, {args.idade}, tom {args.tom}{', sussurro' if args.sussurro else ''}, seed {args.seed}")
    print(f"amostra: {amostra}")
    if args.salvar:
        print(f"voz '{args.salvar}' guardada em voicestudio/vozes. Para virar a voz da casa: VOZ_VOICESTUDIO={args.salvar} no content-engine/audio/.env")
    else:
        print("gostou? rode o mesmo comando com --salvar <nome>. Nao gostou? mude --tom, --idade ou --seed (cada seed e uma pessoa diferente)")
        tocar(amostra)
    return 0


def processos_e_conexoes():
    script = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
        "$p=@(Get-CimInstance Win32_Process|Select-Object ProcessId,ParentProcessId,Name,ExecutablePath);"
        "$t=@(Get-NetTCPConnection -ErrorAction SilentlyContinue|Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,@{n='State';e={[string]$_.State}},OwningProcess);"
        "$u=@(Get-NetUDPEndpoint -ErrorAction SilentlyContinue|Select-Object LocalAddress,LocalPort,OwningProcess);"
        "@{p=$p;t=$t;u=$u}|ConvertTo-Json -Depth 3 -Compress"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, timeout=120)
    return json.loads(r.stdout.decode("utf-8-sig"))


def pids_do_voicestudio(snapshot):
    raizes = {int(p) for p in (ler_json(RUN, {}) or {}).get("pids", {}).values()}
    base = str(BASE).lower()
    filhos = {}
    nomes = {}
    pids = set()
    for p in snapshot["p"]:
        filhos.setdefault(p["ParentProcessId"], []).append(p["ProcessId"])
        nomes[p["ProcessId"]] = p["Name"]
        if (p.get("ExecutablePath") or "").lower().startswith(base):
            pids.add(p["ProcessId"])
    fila = [pid for pid in raizes if pid in nomes] + list(pids)
    while fila:
        pid = fila.pop()
        pids.add(pid)
        fila.extend(f for f in filhos.get(pid, []) if f not in pids)
    return pids, nomes


def endereco_local(endereco):
    try:
        ip = ipaddress.ip_address(endereco.split("%")[0])
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_unspecified


def analisar_rede(snapshot):
    pids, nomes = pids_do_voicestudio(snapshot)
    escutas, externas, udp = [], [], []
    for c in snapshot["t"]:
        if c["OwningProcess"] not in pids:
            continue
        quem = f"{nomes.get(c['OwningProcess'], '?')} pid {c['OwningProcess']}"
        if c["State"] == "Listen":
            escutas.append((c["LocalAddress"], c["LocalPort"], quem))
        elif not endereco_local(c["RemoteAddress"]):
            externas.append((c["RemoteAddress"], c["RemotePort"], c["State"], quem))
    for u in snapshot["u"]:
        if u["OwningProcess"] in pids:
            udp.append((u["LocalAddress"], u["LocalPort"], f"{nomes.get(u['OwningProcess'], '?')} pid {u['OwningProcess']}"))
    return pids, escutas, externas, udp


def checar_rede(vigiar):
    titulo("Processos e rede")
    snapshot = processos_e_conexoes()
    pids, escutas, externas, udp = analisar_rede(snapshot)
    estado = ler_json(RUN, {}) or {}
    if not pids:
        linha("INFO", "nada rodando", "suba com: python voicestudio/voicestudio.py subir")
        return
    linha("INFO", "processos do VoiceStudio", str(len(pids)))
    linha("INFO", "modo", "ONLINE (downloads liberados)" if estado.get("online") else "offline (proxy morto + HF offline)")
    expostas = [e for e in escutas if not ipaddress.ip_address(e[0].split("%")[0]).is_loopback]
    item("portas escutando so em loopback", not expostas, "; ".join(f"{a}:{p} ({q})" for a, p, q in (expostas or escutas)) or "nenhuma porta aberta")
    udp_abertos = [u for u in udp if not ipaddress.ip_address(u[0].split("%")[0]).is_loopback]
    item("UDP so em loopback", not udp_abertos, "; ".join(f"{a}:{p} ({q})" for a, p, q in udp_abertos) or "ok", aviso=True)
    vistas = {(a, p, q): s for a, p, s, q in externas}
    fim = time.time() + vigiar
    if vigiar:
        print(f"  vigiando conexoes por {vigiar}s (gere audio na tela agora)...")
    while time.time() < fim:
        time.sleep(1)
        for a, p, s, q in analisar_rede(processos_e_conexoes())[2]:
            if (a, p, q) not in vistas:
                vistas[(a, p, q)] = s
                print(f"    nova conexao externa: {a}:{p} {s} ({q})")
    lista = "; ".join(f"{a}:{p} {s} ({q})" for (a, p, q), s in vistas.items())
    item("nenhuma conexao pra fora da maquina", not vistas, lista or "zero conexoes externas", aviso=bool(estado.get("online")))


def checar(args):
    titulo(f"Pin ({PIN['repo']})")
    if not (REPO / ".git").exists():
        item("repo clonado", False, "rode: python voicestudio/voicestudio.py instalar")
        return 1
    for nome, ok, detalhe in estado_do_pin():
        item(nome, ok, detalhe)

    titulo("Ferramentas (tudo dentro de voicestudio/.local)")
    for nome, exe in (("uv", UV), ("bun", BUN)):
        v = versao(exe) if exe.is_file() else ""
        item(f"{nome} {PIN[nome]['versao']}", PIN[nome]["versao"] in v, v or "nao instalado", aviso=nome == "bun")
    if VENV_PY.is_file():
        base = subprocess.run([str(VENV_PY), "-I", "-c", "import sys;print(sys.base_prefix);print(sys.version.split()[0])"], capture_output=True, text=True).stdout.split()
        dentro = bool(base) and Path(base[0]).resolve().is_relative_to(LOCAL.resolve())
        item("Python dedicado (nao e o do sistema)", dentro, " ".join(base))
    else:
        item("venv do backend", False, "rode instalar")

    titulo("Dados e privacidade")
    prefs = ler_json(PREFS, {}) or {}
    item("marca d'agua invisivel desligada", prefs.get("watermark.invisible") is False, f"watermark.invisible={prefs.get('watermark.invisible')}", aviso=True)
    item("analytics sem consentimento", not prefs.get("analytics_enabled"), f"analytics_enabled={prefs.get('analytics_enabled', False)} (e o host aponta pra {PROXY_MORTO})", aviso=True)
    sobrescritas = [l.split("=", 1)[0] for l in ENV_FILE.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#")] if ENV_FILE.is_file() else []
    item("arquivo de env do app sem sobrescrita", not sobrescritas, ", ".join(sobrescritas) or f"{ENV_FILE.relative_to(BASE)} vazio", aviso=True)
    vazados = [str(p) for p in FORA_DA_PASTA if p.exists()]
    item("nada gravado fora de voicestudio/", not vazados, "; ".join(vazados) or "nenhuma pasta do app em AppData/home", aviso=True)
    modelos = sorted(p.name.removeprefix("models--").replace("--", "/") for p in MODELOS.glob("models--*")) if MODELOS.is_dir() else []
    linha("INFO", "modelos baixados", ", ".join(modelos) or "nenhum")

    checar_rede(args.vigiar)
    print(f"\n{'OK' if not falhas else 'FALHOU'}: {len(falhas)} falha(s)")
    return 1 if falhas else 0


def processo_vivo(pid):
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
    return str(pid) in r.stdout


def cmd_subir(args):
    if not VENV_PY.is_file():
        raise SystemExit("backend nao instalado: rode python voicestudio/voicestudio.py instalar")
    web = args.web
    if web and not (REPO / "node_modules").is_dir():
        raise SystemExit("interface nao instalada: rode instalar --web")
    estado = ler_json(RUN, {}) or {}
    if any(processo_vivo(p) for p in estado.get("pids", {}).values()) or api_no_ar():
        raise SystemExit("ja esta rodando: python voicestudio/voicestudio.py parar")
    for nome, ok, detalhe in estado_do_pin():
        if not ok:
            raise SystemExit(f"repo fora do pin, recusando subir: {nome} ({detalhe})")
    procs = {"api": iniciar_backend(online=args.online)}
    if web:
        procs["web"] = subprocess.Popen([str(BUN), "run", "--cwd", "electron", "dev:web"], cwd=REPO, env=ambiente(online=args.online))
    escrever_json(RUN, {"pids": {k: p.pid for k, p in procs.items()}, "online": args.online, "inicio": time.strftime("%Y-%m-%d %H:%M:%S")})
    esperar_api(procs["api"])
    criadas = sincronizar_vozes()
    if criadas:
        print(f"vozes da casa criadas: {', '.join(criadas)}")
    print(f"\nAPI: http://127.0.0.1:{PORTA_API}  (OpenAI: POST /v1/audio/speech)")
    if web:
        print(f"Tela: http://localhost:{PORTA_WEB}")
    print("Modo: " + ("ONLINE - downloads de modelo liberados, suba sem --online depois" if args.online else "offline - proxy morto e Hugging Face offline"))
    print("Ctrl+C para parar. Em outro terminal: python voicestudio/voicestudio.py checar --vigiar 60\n")
    try:
        while all(p.poll() is None for p in procs.values()):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cmd_parar(None)
    return 0


def cmd_parar(args):
    estado = ler_json(RUN, {}) or {}
    for pid in estado.get("pids", {}).values():
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    restos = [p for p in processos_e_conexoes()["p"] if (p.get("ExecutablePath") or "").lower().startswith(str(BASE).lower())]
    for p in restos:
        subprocess.run(["taskkill", "/PID", str(p["ProcessId"]), "/T", "/F"], capture_output=True)
    RUN.unlink(missing_ok=True)
    print("VoiceStudio parado" + (f" ({len(restos)} processo(s) sobrando encerrados)" if restos else ""))
    return 0


def main():
    parser = argparse.ArgumentParser(description="VoiceStudio local, pinado e sem rede (teste).")
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("instalar", help="baixa uv com SHA-256, clona no commit do pin e instala as dependencias travadas")
    p.add_argument("--web", action="store_true", help="instala tambem bun e a interface web")
    p.set_defaults(func=cmd_instalar)
    p = sub.add_parser("modelos", help="aceita as licencas e baixa os modelos do pin.json (sobe um backend online temporario)")
    p.set_defaults(func=cmd_modelos)
    p = sub.add_parser("subir", help="sobe a API em 127.0.0.1; offline por padrao")
    p.add_argument("--online", action="store_true", help="libera rede; o normal e baixar modelos pelo comando modelos")
    p.add_argument("--web", action="store_true", help="sobe tambem a tela em localhost")
    p.set_defaults(func=cmd_subir)
    p = sub.add_parser("clonar", help="cria uma voz clonada a partir de uma gravacao (API precisa estar no ar)")
    p.add_argument("--audio", required=True, help="gravacao de 3 a 20s (wav, m4a, mp3)")
    p.add_argument("--texto", required=True, help="exatamente o que foi falado na gravacao")
    p.add_argument("--nome", required=True, help="nome da voz, usado depois em --voz")
    p.add_argument("--guardar", action="store_true", help="guarda em voicestudio/vozes (vai pro git e os outros PCs recriam)")
    p.set_defaults(func=cmd_clonar)
    p = sub.add_parser("voz", help="monta uma voz por atributos, ouve e salva com nome")
    p.add_argument("--genero", choices=list(GENEROS), default="feminina")
    p.add_argument("--idade", choices=list(IDADES), default="jovem")
    p.add_argument("--tom", choices=list(TONS), default="medio")
    p.add_argument("--sussurro", action="store_true")
    p.add_argument("--seed", type=int, default=SEED, help="cada numero e uma pessoa diferente com os mesmos atributos")
    p.add_argument("--frase", default=FRASE_PADRAO, help="frase da amostra (vira a referencia da voz)")
    p.add_argument("--salvar", metavar="NOME", help="guarda a amostra como voz da casa com esse nome")
    p.add_argument("--listar", action="store_true", help="lista as vozes guardadas")
    p.set_defaults(func=cmd_voz)
    p = sub.add_parser("falar", help="gera um wav pela API")
    p.add_argument("texto")
    p.add_argument("--voz", default="alloy", help="nome da voz clonada ou alloy (voz padrao)")
    p.add_argument("--instrucoes", default="", help="design: ex. 'female, young adult, moderate pitch'")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--saida", default="", help="arquivo wav de saida (padrao: .local/saida)")
    p.add_argument("--tocar", action="store_true", help="abre o audio no player ao terminar")
    p.set_defaults(func=cmd_falar)
    p = sub.add_parser("checar", help="pin, ferramentas, privacidade e conexoes abertas")
    p.add_argument("--vigiar", type=int, default=0, metavar="SEG", help="fica olhando conexoes por SEG segundos")
    p.set_defaults(func=checar)
    p = sub.add_parser("parar", help="encerra tudo que roda de dentro de voicestudio/")
    p.set_defaults(func=cmd_parar)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
