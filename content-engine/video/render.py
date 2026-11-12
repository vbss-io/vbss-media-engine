import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import _comum as c
from comum import arquivos, midias
from comum.urls import urls_externas_na_pasta

PARENTS_TO_CHECK = 5


def checar_env_files(comp_dir):
    achados = []
    pastas = [comp_dir, *list(comp_dir.parents)[:PARENTS_TO_CHECK]]
    for pasta in pastas:
        for arq in pasta.glob(".env*"):
            if arq.is_file():
                achados.append(arq)
    return achados


def checar_midias(comp_dir):
    return midias.checar_composicao(comp_dir)


def checar_tipos(comp_dir):
    return arquivos.inventariar(comp_dir)


def preparar_stage(comp_dir, motor, permitidos):
    stage_root = c.sandbox_paths()["stage"]
    stage = stage_root / comp_dir.name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for rel in permitidos:
        destino = stage / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(comp_dir / rel, destino)
    motor.preparar(stage)
    return stage


def resumo_bloqueio_de_arquivo(linha):
    try:
        d = json.loads(linha)
        return f"{d.get('kind')} -> {d.get('target')}"
    except json.JSONDecodeError:
        return linha[:200]


def main():
    p = argparse.ArgumentParser(description="Renderiza uma composicao de video pelo motor local ativo (content-engine/video/motor.json).")
    p.add_argument("composicao", help="pasta da composicao (com index.html)")
    p.add_argument("saida", help="arquivo .mp4 de saida")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--qualidade", choices=["rascunho", "padrao", "final"], default="padrao")
    a = p.parse_args()

    comp_dir = Path(a.composicao).resolve()
    saida = Path(a.saida).resolve()
    if not (comp_dir / "index.html").is_file():
        c.falhar(f"{comp_dir} nao tem index.html")
    if saida.suffix.lower() != ".mp4":
        c.falhar("a saida precisa terminar em .mp4")

    c.titulo("Checagens antes do render")
    envs = checar_env_files(comp_dir)
    if envs:
        c.falhar("encontrei arquivo .env perto da composicao (o motor poderia ler chaves dele). Remova ou mova:\n  " + "\n  ".join(map(str, envs)))
    c.linha("OK", f"nenhum .env na pasta da composicao nem nas {PARENTS_TO_CHECK} pastas acima")
    urls = urls_externas_na_pasta(comp_dir)
    if urls:
        lista = "\n  ".join(f"{arq.relative_to(comp_dir)}:{ln}  {url}" for arq, ln, url in urls)
        c.falhar("a composicao aponta para endereco de internet. Fontes, GSAP e imagens precisam ser arquivos locais:\n  " + lista)
    c.linha("OK", "nenhuma URL externa nos arquivos da composicao")
    permitidos, problemas_tipos = checar_tipos(comp_dir)
    if problemas_tipos:
        c.falhar("a composicao tem arquivo que o motor nao recebe (so entram tipos conhecidos de pagina, imagem, fonte, audio e video, e nenhuma lista de reproducao):\n  " + "\n  ".join(problemas_tipos))
    c.linha("OK", f"{len(permitidos)} arquivo(s) da composicao, todos de tipo permitido e sem lista de reproducao")
    audios, problemas_midia = checar_midias(comp_dir)
    if problemas_midia:
        c.falhar("midia da composicao com problema (todo arquivo referenciado precisa existir dentro da pasta da composicao):\n  " + "\n  ".join(problemas_midia))
    c.linha("OK", f"todas as referencias de arquivo ficam dentro da composicao ({audios} <audio>)" if audios else "composicao sem <audio> (video sai mudo)")

    node = c.node_path()
    if not node:
        c.falhar("Node.js nao encontrado. Rode python content-engine/video/doctor.py")
    chrome = c.find_chrome()
    if not chrome:
        c.falhar("nenhum navegador encontrado. Rode python content-engine/video/setup.py (instala o navegador fixo)")
    if not c.ffmpeg_path().is_file():
        c.falhar("FFmpeg local ausente. Rode python content-engine/video/setup.py")

    motor = c.load_motor()
    stage = preparar_stage(comp_dir, motor, permitidos)
    paths = c.sandbox_paths()
    saida_tmp = paths["saida"] / f"{comp_dir.name}.mp4"
    if saida_tmp.exists():
        saida_tmp.unlink()
    env = c.sandbox_env(
        extra=motor.ambiente(chrome, c.versao_navegador(chrome), c.ffmpeg_path(), c.ffprobe_path(), c.SANDBOX_DIR, c.NET_GUARD_LOG),
        path_dirs=[node.parent],
    )
    raizes = c.raizes_permitidas(motor, stage, node, chrome)
    env.update(c.ambiente_de_arquivos(raizes))
    problemas = c.assert_env_isolated(env)
    if problemas:
        c.falhar("ambiente do motor nao esta isolado: " + "; ".join(problemas))
    c.linha("OK", f"motor '{motor.NOME}' isolado em {c.SANDBOX_DIR}", f"{len(env)} variaveis: {', '.join(sorted(env))}")
    if c.e_navegador_fixo(chrome):
        c.linha("OK", "navegador", c.descrever_navegador(chrome))
    else:
        c.linha("AVISO", f"{c.descrever_navegador(chrome)}; {c.AVISO_SISTEMA}")
    c.linha("OK", f"guarda de arquivos: o motor so le dentro de {len(raizes)} pastas permitidas (composicao no sandbox, pastas do motor, FFmpeg, Node, navegador)")

    cmd = motor.comando_render(node, stage, saida_tmp, a.fps, a.qualidade)
    c.titulo(f"Renderizando com {motor.NOME}")
    guard_offset = c.tamanho(c.NET_GUARD_LOG)
    arquivos_offset = c.tamanho(c.FILE_GUARD_LOG)
    inicio = time.time()
    r = subprocess.run(cmd, env=env, cwd=str(paths["cwd"]))
    duracao = time.time() - inicio
    bloqueios = c.ler_log(c.NET_GUARD_LOG, guard_offset)
    bloqueios_arquivo = c.ler_log(c.FILE_GUARD_LOG, arquivos_offset)

    c.titulo("Rede")
    if bloqueios:
        c.linha("ATENCAO", f"{len(bloqueios)} tentativa(s) de conexao externa foram BLOQUEADAS (nada saiu)", str(c.NET_GUARD_LOG))
        for b in bloqueios[:20]:
            print("   " + b)
    else:
        c.linha("OK", "nenhuma tentativa de conexao externa durante o render", str(c.NET_GUARD_LOG))

    c.titulo("Arquivos")
    if bloqueios_arquivo:
        if saida_tmp.exists():
            saida_tmp.unlink()
        lista = "\n  ".join(resumo_bloqueio_de_arquivo(b) for b in bloqueios_arquivo[:20])
        c.falhar(f"o motor tentou ler {len(bloqueios_arquivo)} arquivo(s) fora da pasta da composicao e foi BLOQUEADO; render abortado, nenhum video salvo "
                 f"({c.FILE_GUARD_LOG}). Copie o arquivo para assets/ da composicao:\n  " + lista)
    c.linha("OK", "nenhum acesso a arquivo fora da composicao e das pastas do motor", str(c.FILE_GUARD_LOG))

    if r.returncode != 0 or not saida_tmp.is_file():
        c.falhar(f"o render falhou (codigo {r.returncode}). Veja a saida acima.")
    saida.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(saida_tmp), str(saida))
    info = c.resumo_video(saida)
    c.titulo("Resultado")
    c.linha("OK", "video salvo", str(saida))
    print(f"   {info['largura']}x{info['altura']}  {info['duracao']}s  {info['fps']} fps  {info['codec']} ({info['perfil']}, {info['pix_fmt']})  audio: {info['audio']} faixa(s)  render: {duracao:.0f}s")


if __name__ == "__main__":
    main()
