import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True

import _comum as c
from comum.download import baixar, sha256

NODE_MIN = (22, 0, 0)


def instalar_ffmpeg():
    c.titulo("FFmpeg local")
    b = c.FFMPEG_BUILD
    ffmpeg = c.ffmpeg_path()
    if ffmpeg.is_file() and c.ffprobe_path().is_file():
        out = subprocess.run([str(ffmpeg), "-version"], capture_output=True, text=True, timeout=60).stdout
        if f"ffmpeg version {b['versao']}" in out:
            c.linha("OK", "FFmpeg ja instalado", f"{b['versao']} em {c.BIN_DIR}")
            return
    cache = c.CACHE_DIR / "ffmpeg"
    cache.mkdir(parents=True, exist_ok=True)
    zip_path = cache / b["arquivo"]
    if zip_path.is_file() and sha256(zip_path) != b["sha256"]:
        zip_path.unlink()
    if not zip_path.is_file():
        for url in b["urls"]:
            print(f"Baixando {url}", flush=True)
            try:
                baixar(url, zip_path, agente="vbss-media-engine-video-setup")
                break
            except OSError as err:
                print(f"  falhou: {err}", flush=True)
        else:
            c.falhar("nao consegui baixar o FFmpeg de nenhuma das fontes oficiais.")
    obtido = sha256(zip_path)
    if obtido != b["sha256"]:
        zip_path.unlink()
        c.falhar(f"SHA-256 do FFmpeg nao confere (esperado {b['sha256']}, veio {obtido}). Arquivo apagado.")
    c.linha("OK", "SHA-256 do FFmpeg confere", obtido)
    c.BIN_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        nomes = set(z.namelist())
        for destino, membro in b["membros"].items():
            if membro not in nomes:
                c.falhar(f"o zip do FFmpeg nao tem {membro}")
            with z.open(membro) as src, open(c.BIN_DIR / destino, "wb") as dst:
                while True:
                    bloco = src.read(1 << 20)
                    if not bloco:
                        break
                    dst.write(bloco)
    c.linha("OK", "FFmpeg extraido", str(c.BIN_DIR))


def instalar_motor(motor, node):
    c.titulo(f"Motor '{motor.NOME}' (pacotes npm fixados)")
    npm_cli = node.parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
    cmd, cwd = motor.comando_instalacao(node, npm_cli if npm_cli.is_file() else None)
    npmrc_usuario = c.SANDBOX_DIR / "npmrc-usuario-vazio"
    npmrc_global = c.SANDBOX_DIR / "npmrc-global-vazio"
    for arq in (npmrc_usuario, npmrc_global):
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text("", encoding="utf-8")
    env = c.sandbox_env(
        extra={
            "npm_config_cache": str(c.CACHE_DIR / "npm"),
            "npm_config_userconfig": str(npmrc_usuario),
            "npm_config_globalconfig": str(npmrc_global),
            "npm_config_registry": "https://registry.npmjs.org/",
            "npm_config_ignore_scripts": "true",
            "npm_config_update_notifier": "false",
            "npm_config_fund": "false",
            "npm_config_audit": "false",
        },
        path_dirs=[node.parent],
    )
    print(" ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(cwd), env=env)
    if r.returncode != 0:
        c.falhar("a instalacao dos pacotes do motor falhou (veja a saida acima).")
    instalada = motor.versao_instalada()
    if instalada != motor.VERSAO_CLI:
        c.falhar(f"versao instalada do motor ({instalada}) diferente da fixada ({motor.VERSAO_CLI}).")
    c.linha("OK", f"{motor.NOME} {instalada} instalado em", str(cwd / "node_modules"))


def main():
    print("Instalando o motor de video local do vbss-media-engine.")
    print("Rede usada: so o registro do npm (pacotes fixados) e os downloads unicos do FFmpeg e do navegador fixo, ambos com SHA-256.")
    if sys.version_info < (3, 10):
        c.falhar("precisa de Python 3.10 ou mais novo.")
    node = c.node_path()
    if not node:
        c.falhar("Node.js nao encontrado no PATH. Instale o Node 22 (o setup nao instala Node).")
    ver = c.node_version(node)
    if not ver or ver < NODE_MIN:
        c.falhar(f"Node {ver} encontrado; precisa de 22 ou mais novo.")
    c.sandbox_paths()
    motor = c.load_motor()
    instalar_motor(motor, node)
    instalar_ffmpeg()
    c.navegador_fixado.instalar(c.linha, c.titulo, c.falhar)
    chrome = c.find_chrome()
    if not c.e_navegador_fixo(chrome):
        c.linha("AVISO", "o render vai usar outro navegador", c.descrever_navegador(chrome))
    print("\nPronto. Agora rode: python content-engine/video/doctor.py")


if __name__ == "__main__":
    main()
