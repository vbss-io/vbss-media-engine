import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import checar_reel
import montar_reel

WORK = Path(__file__).resolve().parents[1] / ".cache" / "testes"


def peca(raiz, falas=3):
    pasta = Path(raiz)
    (pasta / "assets" / "voz").mkdir(parents=True)
    (pasta / "vozes").mkdir()
    wavs = []
    for i in range(1, falas + 1):
        wav = pasta / "assets" / "voz" / f"voz-{i:02d}.wav"
        wav.write_bytes(f"audio {i}".encode("utf-8"))
        wavs.append(wav)
    return pasta, wavs


class FalaOuvidaPorUmaPessoa(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=WORK)
        self.pasta, self.wavs = peca(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_liberacao_guarda_quem_ouviu_e_o_audio_ouvido(self):
        ouvidas = montar_reel.falas_ouvidas(self.pasta, self.wavs, [2], "Maria")
        self.assertEqual(list(ouvidas), [2])
        self.assertEqual(ouvidas[2]["por"], "Maria")
        self.assertEqual(ouvidas[2]["sha256"], montar_reel.sha(self.wavs[1]))
        gravado = json.loads((self.pasta / "vozes" / "ouvidas.json").read_text(encoding="utf-8"))
        self.assertEqual(list(gravado), ["2"])

    def test_liberacao_continua_valendo_na_montagem_seguinte(self):
        montar_reel.falas_ouvidas(self.pasta, self.wavs, [2], "Maria")
        self.assertEqual(list(montar_reel.falas_ouvidas(self.pasta, self.wavs)), [2])

    def test_fala_gerada_de_novo_perde_a_liberacao(self):
        montar_reel.falas_ouvidas(self.pasta, self.wavs, [2], "Maria")
        self.wavs[1].write_bytes(b"audio novo")
        self.assertEqual(montar_reel.falas_ouvidas(self.pasta, self.wavs), {})
        self.assertEqual(json.loads((self.pasta / "vozes" / "ouvidas.json").read_text(encoding="utf-8")), {})

    def test_sem_liberacao_nada_e_gravado(self):
        self.assertEqual(montar_reel.falas_ouvidas(self.pasta, self.wavs), {})
        self.assertFalse((self.pasta / "vozes" / "ouvidas.json").exists())

    def test_checagem_so_aceita_liberacao_do_mesmo_audio(self):
        ouvidas = montar_reel.falas_ouvidas(self.pasta, self.wavs, [2], "Maria")
        montagem = {"pronuncia": [{"arquivo": "voz-01.wav", "ouvida": None}, {"arquivo": "voz-02.wav", "ouvida": ouvidas[2]}]}
        liberadas = checar_reel.falas_liberadas(montagem, self.pasta)
        self.assertEqual(list(liberadas), ["voz-02.wav"])
        self.assertIn("Maria", liberadas["voz-02.wav"])
        self.wavs[1].write_bytes(b"audio novo")
        self.assertEqual(checar_reel.falas_liberadas(montagem, self.pasta), {})

    def test_checagem_sem_montagem_nao_libera_nada(self):
        self.assertEqual(checar_reel.falas_liberadas(None, self.pasta), {})


class GeradoComOutraQuebraDeLinha(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=WORK)
        self.pasta = Path(self.tmp.name)
        self.gerado = b"<html>\n<body>\n</body>\n</html>\n"
        self.anterior = {"gerados": {"index.html": hashlib.sha256(self.gerado).hexdigest()}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_checkout_com_crlf_nao_conta_como_ajuste_manual(self):
        (self.pasta / "index.html").write_bytes(self.gerado.replace(b"\n", b"\r\n"))
        self.assertIsNone(montar_reel.conferir_ajuste_manual(self.pasta, self.anterior, False))
        self.assertFalse(checar_reel.gerado_mudou(self.anterior, self.pasta / "index.html"))

    def test_gerado_sem_mudanca_registra_o_mesmo_sha_de_antes(self):
        (self.pasta / "index.html").write_bytes(self.gerado)
        self.assertEqual(montar_reel.sha_do_gerado(self.pasta / "index.html"), self.anterior["gerados"]["index.html"])

    def test_mudanca_de_conteudo_continua_barrada(self):
        (self.pasta / "index.html").write_bytes(self.gerado.replace(b"<body>", b"<body class=\"x\">").replace(b"\n", b"\r\n"))
        with self.assertRaises(SystemExit):
            montar_reel.conferir_ajuste_manual(self.pasta, self.anterior, False)
        self.assertTrue(checar_reel.gerado_mudou(self.anterior, self.pasta / "index.html"))

    def test_montagem_sem_registro_nao_acusa_mudanca_na_checagem(self):
        (self.pasta / "index.html").write_bytes(self.gerado)
        self.assertFalse(checar_reel.gerado_mudou({}, self.pasta / "index.html"))


if __name__ == "__main__":
    unittest.main()
