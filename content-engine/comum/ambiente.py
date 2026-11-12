import os
import re
from pathlib import Path

SECRET_NAME = re.compile(
    r"(API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|SESSION|COOKIE|AUTH"
    r"|^ANTHROPIC|^CLAUDE|^OPENAI|^GEMINI|^GOOGLE|^GCLOUD|^GCS|^OPENROUTER|^HEYGEN|^GITHUB|^GH_|^GITLAB"
    r"|^AWS|^AZURE|^ARM_|^ELEVENLABS|^FIGMA|^HUGGING|^CODEX|^GROK|^XAI|^MISTRAL|^COHERE|^DEEPSEEK"
    r"|^NPM_CONFIG__AUTH|^NODE_AUTH|^SSH_|^MONGO|^DATABASE_URL|^STRIPE)",
    re.IGNORECASE,
)

ENV_ALLOWLIST = (
    "SystemRoot", "SYSTEMROOT", "windir", "SystemDrive", "ComSpec", "PATHEXT",
    "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
    "PROCESSOR_LEVEL", "PROCESSOR_REVISION", "OS",
    "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432",
    "CommonProgramFiles", "CommonProgramFiles(x86)", "CommonProgramW6432",
)


def sandbox_paths(sandbox_dir, extras=()):
    sandbox_dir = Path(sandbox_dir)
    paths = {
        "home": sandbox_dir / "home",
        "appdata": sandbox_dir / "home" / "AppData" / "Roaming",
        "localappdata": sandbox_dir / "home" / "AppData" / "Local",
        "temp": sandbox_dir / "tmp",
        "cwd": sandbox_dir / "cwd",
    }
    for nome in extras:
        paths[nome] = sandbox_dir / nome
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def sandbox_env(sandbox_dir, extra=None, path_dirs=()):
    paths = sandbox_paths(sandbox_dir)
    env = {k: os.environ[k] for k in ENV_ALLOWLIST if k in os.environ}
    system_root = env.get("SystemRoot") or env.get("SYSTEMROOT") or r"C:\Windows"
    home = str(paths["home"])
    env.update({
        "HOME": home,
        "USERPROFILE": home,
        "HOMEDRIVE": home[:2],
        "HOMEPATH": home[2:],
        "APPDATA": str(paths["appdata"]),
        "LOCALAPPDATA": str(paths["localappdata"]),
        "TEMP": str(paths["temp"]),
        "TMP": str(paths["temp"]),
        "TMPDIR": str(paths["temp"]),
        "XDG_CACHE_HOME": str(paths["home"] / ".cache"),
        "XDG_CONFIG_HOME": str(paths["home"] / ".config"),
        "XDG_DATA_HOME": str(paths["home"] / ".local" / "share"),
        "XDG_STATE_HOME": str(paths["home"] / ".local" / "state"),
        "DO_NOT_TRACK": "1",
    })
    dirs = [str(d) for d in path_dirs] + [
        os.path.join(system_root, "System32"),
        system_root,
        os.path.join(system_root, "System32", "Wbem"),
        os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0"),
    ]
    env["PATH"] = os.pathsep.join(dict.fromkeys(dirs))
    if extra:
        env.update(extra)
    for key in list(env):
        if SECRET_NAME.search(key):
            del env[key]
    return env


def assert_env_isolated(env, sandbox_dir):
    problemas = [k for k in env if SECRET_NAME.search(k)]
    base = str(sandbox_dir)
    for k in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"):
        if not env.get(k, "").startswith(base):
            problemas.append(f"{k} fora do sandbox")
    return problemas
