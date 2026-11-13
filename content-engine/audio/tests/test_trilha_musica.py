import array
import contextlib
import io
import json
import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _comum as c
import trilha

TOTAL = 12.0
INDEX = (
    "<!doctype html>\n<html><body>\n"
    f'<div id="root" data-composition-id="teste" data-start="0" data-duration="{TOTAL}">\n'
    "  <div class=\"cena\"></div>\n</div>\n</body></html>\n"
)
FALAS = [{"t": 2.0, "arquivo": "assets/voz/voz-01.wav"}, {"t": 3.3, "arquivo": "assets/voz/voz-02.wav"}, {"t": 8.0, "arquivo": "assets/voz/voz-03.wav"}]
MUSICA = {"arquivo": "assets/fonte.wav", "volume": 0.5, "sob_voz": 0.1, "entrada": 0.5, "saida": 1.0, "ataque": 0.2, "soltura": 0.4}
TEM_FFMPEG = c.ffmpeg_path().is_file() and c.ffprobe_path().is_file()


def gravar_seno(destino, segundos, amplitude=0.5, taxa=48000):
    destino.parent.mkdir(parents=True, exist_ok=True)
    quadros = int(taxa * segundos)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(b"".join(struct.pack("<h", int(32767 * amplitude * math.sin(2 * math.pi * 400 * i / taxa))) for i in range(quadros)))


def composicao(pasta):
    comp = Path(pasta) / "comp"
    comp.mkdir()
    (comp / "index.html").write_text(INDEX, encoding="utf-8", newline="\n")
    for nome in ("voz-01.wav", "voz-02.wav", "voz-03.wav"):
        gravar_seno(comp / "assets" / "voz" / nome, 1.0, 0.2, 24000)
    gravar_seno(comp / "assets" / "fonte.wav", 3.0)
    return comp


def rodar(comp, cfg):
    arquivo = comp.parent / "trilha.json"
    arquivo.write_text(json.dumps(cfg), encoding="utf-8")
    saida, erro = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", ["trilha.py", str(comp), str(arquivo)]), contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
        trilha.main()
    return saida.getvalue()


def rms(wav, inicio, fim):
    with wave.open(str(wav), "rb") as w:
        taxa = w.getframerate()
        w.setpos(int(inicio * taxa))
        amostras = array.array("h", w.readframes(int((fim - inicio) * taxa)))
    return math.sqrt(sum(a * a for a in amostras) / (len(amostras) or 1)) / 32767


def pasta_temporaria():
    c.WORK_DIR.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=c.WORK_DIR)


class TrechosDeVoz(unittest.TestCase):
    def test_falas_com_pausa_menor_que_o_limite_viram_um_trecho(self):
        self.assertEqual(trilha.trechos_de_voz([(2.0, 3.0), (3.3, 4.3), (8.0, 9.0)]), [(2.0, 4.3), (8.0, 9.0)])

    def test_pausa_igual_ao_limite_separa(self):
        self.assertEqual(trilha.trechos_de_voz([(1.0, 2.0), (2.6, 3.0)]), [(1.0, 2.0), (2.6, 3.0)])

    def test_ordem_de_entrada_nao_importa_e_fala_contida_nao_encurta(self):
        self.assertEqual(trilha.trechos_de_voz([(5.0, 5.5), (1.0, 6.0), (0.2, 0.9)]), [(0.2, 6.0)])

    def test_sem_fala_nao_ha_trecho(self):
        self.assertEqual(trilha.trechos_de_voz([]), [])


class PontosDeDucking(unittest.TestCase):
    def test_desce_antes_da_fala_e_volta_depois(self):
        pontos = trilha.pontos_de_ducking([(2.0, 4.0)], 0.5, 0.1, 0.2, 0.4)
        esperado = [(1.75, 0.5), (1.95, 0.1), (4.0, 0.1), (4.4, 0.5)]
        self.assertEqual(len(pontos), len(esperado))
        for (t, g), (te, ge) in zip(pontos, esperado):
            self.assertAlmostEqual(t, te, places=6)
            self.assertAlmostEqual(g, ge, places=6)

    def test_trechos_distantes_voltam_ao_volume_cheio_no_meio(self):
        pontos = trilha.pontos_de_ducking([(2.0, 4.0), (8.0, 9.0)], 0.5, 0.1, 0.2, 0.4)
        self.assertIn((4.4, 0.5), [(round(t, 6), g) for t, g in pontos])
        self.assertIn((7.75, 0.5), [(round(t, 6), g) for t, g in pontos])

    def test_rampas_que_se_cruzam_nao_chegam_ao_volume_cheio(self):
        pontos = trilha.pontos_de_ducking([(2.0, 4.0), (4.7, 6.0)], 0.5, 0.1, 0.3, 0.6)
        tempos = [t for t, _ in pontos]
        self.assertEqual(tempos, sorted(tempos))
        meio = [g for t, g in pontos if 4.0 < t < 4.65]
        self.assertEqual(len(meio), 1)
        self.assertTrue(0.1 < meio[0] < 0.5)

    def test_sem_voz_o_volume_fica_constante(self):
        self.assertEqual(trilha.pontos_de_ducking([], 0.5, 0.1, 0.2, 0.4), [(0.0, 0.5)])

    def test_expressao_e_constante_fora_das_rampas(self):
        expr = trilha.expressao(trilha.pontos_de_ducking([(2.0, 4.0)], 0.5, 0.1, 0.2, 0.4))
        self.assertTrue(expr.startswith("0.500000"))
        self.assertEqual(expr.count("max(t-("), 4)


@unittest.skipUnless(TEM_FFMPEG, "FFmpeg local ausente (content-engine/video/bin)")
class BaseDeMusica(unittest.TestCase):
    def test_base_cobre_o_video_em_loop_e_abaixa_so_nos_trechos_de_voz(self):
        with pasta_temporaria() as tmp:
            comp = composicao(tmp)
            rodar(comp, {"musica": MUSICA, "deixas": FALAS})
            base = comp / trilha.BASE_MUSICA
            self.assertAlmostEqual(c.duracao(base), TOTAL, places=2)
            cheio = rms(base, 5.5, 6.5)
            sob_voz = rms(base, 2.5, 4.0)
            pausa_curta = rms(base, 3.05, 3.25)
            segunda_fala = rms(base, 8.2, 8.9)
            self.assertAlmostEqual(cheio, 0.5 * 0.5 / math.sqrt(2), delta=0.01)
            self.assertAlmostEqual(sob_voz / cheio, 0.1 / 0.5, delta=0.02)
            self.assertAlmostEqual(pausa_curta / cheio, 0.1 / 0.5, delta=0.02)
            self.assertAlmostEqual(segunda_fala / cheio, 0.1 / 0.5, delta=0.02)
            self.assertLess(rms(base, 0.0, 0.05), cheio * 0.15)
            self.assertLess(rms(base, TOTAL - 0.1, TOTAL), cheio * 0.15)
            self.assertAlmostEqual(rms(base, 1.0, 1.5), cheio, delta=0.01)

    def test_audio_da_musica_entra_uma_vez_na_trilha_fixa(self):
        with pasta_temporaria() as tmp:
            comp = composicao(tmp)
            rodar(comp, {"musica": MUSICA, "deixas": FALAS})
            html = (comp / "index.html").read_text(encoding="utf-8")
            self.assertEqual(html.count('id="trilha-musica"'), 1)
            self.assertIn(f'src="assets/musica/base.wav" data-start="0" data-duration="{TOTAL - trilha.MARGEM_FIM}" data-track-index="{trilha.TRILHA_MUSICA}" data-volume="1.0" data-trilha="1"', html)
            self.assertEqual(html.count('data-track-index="10"'), 3)

    def test_rodar_de_novo_e_idempotente(self):
        with pasta_temporaria() as tmp:
            comp = composicao(tmp)
            cfg = {"musica": MUSICA, "deixas": FALAS}
            rodar(comp, cfg)
            antes = (c.sha256(comp / trilha.BASE_MUSICA), (comp / "index.html").read_bytes())
            rodar(comp, cfg)
            self.assertEqual(antes, (c.sha256(comp / trilha.BASE_MUSICA), (comp / "index.html").read_bytes()))

    def test_sem_a_chave_musica_o_resultado_e_o_de_antes_e_a_base_antiga_some(self):
        with pasta_temporaria() as tmp:
            comp = composicao(tmp)
            rodar(comp, {"deixas": FALAS})
            sem_musica = (comp / "index.html").read_bytes()
            self.assertNotIn(b"trilha-musica", sem_musica)
            self.assertFalse((comp / trilha.PASTA_MUSICA).exists())
            rodar(comp, {"musica": MUSICA, "deixas": FALAS})
            self.assertTrue((comp / trilha.BASE_MUSICA).is_file())
            rodar(comp, {"deixas": FALAS})
            self.assertEqual((comp / "index.html").read_bytes(), sem_musica)
            self.assertFalse((comp / trilha.PASTA_MUSICA).exists())

    def test_inicio_atrasa_a_entrada_da_musica(self):
        with pasta_temporaria() as tmp:
            comp = composicao(tmp)
            rodar(comp, {"musica": {**MUSICA, "inicio": 5.0}, "deixas": []})
            base = comp / trilha.BASE_MUSICA
            self.assertEqual(rms(base, 0.0, 4.9), 0.0)
            self.assertAlmostEqual(rms(base, 6.0, 7.0), 0.5 * 0.5 / math.sqrt(2), delta=0.01)

    @unittest.skipUnless(c.MUSICA_MANIFESTO.is_file(), "biblioteca de musica ausente")
    def test_faixa_da_biblioteca_gera_a_base(self):
        faixa = c.ler_json(c.MUSICA_MANIFESTO)["itens"][0]["id"]
        with pasta_temporaria() as tmp:
            comp = composicao(tmp)
            saida = rodar(comp, {"musica": {"faixa": faixa}, "deixas": FALAS})
            self.assertIn(f"musica '{faixa}'", saida)
            self.assertGreater(rms(comp / trilha.BASE_MUSICA, 5.5, 6.5), 0.01)


class ErrosDeMusica(unittest.TestCase):
    def falha(self, musica):
        with pasta_temporaria() as tmp:
            comp = composicao(tmp)
            arquivo = comp.parent / "trilha.json"
            arquivo.write_text(json.dumps({"musica": musica, "deixas": FALAS}), encoding="utf-8")
            erro = io.StringIO()
            with mock.patch.object(sys, "argv", ["trilha.py", str(comp), str(arquivo)]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(erro):
                with self.assertRaises(SystemExit) as saida:
                    trilha.main()
            self.assertEqual(saida.exception.code, 1)
            self.assertFalse((comp / trilha.BASE_MUSICA).exists())
            self.assertNotIn("trilha-musica", (comp / "index.html").read_text(encoding="utf-8"))
            return erro.getvalue()

    @unittest.skipUnless(c.MUSICA_MANIFESTO.is_file(), "biblioteca de musica ausente")
    def test_faixa_inexistente_cita_o_id_e_o_catalogo(self):
        mensagem = self.falha({"faixa": "faixa-que-nao-existe"})
        self.assertIn("faixa de musica 'faixa-que-nao-existe' nao existe na biblioteca", mensagem)
        self.assertIn("content-engine/audio/music/CATALOGO.md", mensagem)

    def test_arquivo_fora_da_composicao_e_recusado(self):
        self.assertIn("precisa ser um arquivo dentro da composicao", self.falha({"arquivo": "../fora.wav"}))

    def test_faixa_e_arquivo_juntos_ou_nenhum_dos_dois(self):
        self.assertIn("um dos dois", self.falha({"faixa": "x", "arquivo": "assets/fonte.wav"}))
        self.assertIn("um dos dois", self.falha({"volume": 0.4}))

    def test_chave_desconhecida_e_volume_invalido(self):
        self.assertIn("chave desconhecida: sobvoz", self.falha({"arquivo": "assets/fonte.wav", "sobvoz": 0.1}))
        self.assertIn("'sob_voz' de 0 ate o 'volume'", self.falha({"arquivo": "assets/fonte.wav", "volume": 0.3, "sob_voz": 0.5}))


if __name__ == "__main__":
    unittest.main()
