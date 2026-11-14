import json
import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reel_cenas as rc

TOKENS = json.loads((Path(__file__).resolve().parents[2] / "tokens.json").read_text(encoding="utf-8"))


def palavras(texto, inicio, passo=0.3):
    saida = []
    t = inicio
    for p in texto.split():
        saida.append({"texto": p, "inicio": round(t, 3), "fim": round(t + passo, 3)})
        t += passo
    return saida


def medir(arquivo, video=False):
    return (816, 1104, 6.0) if video else (816, 1088)


def peca(total=12.0):
    return rc.Peca(rc.estilo_da_marca(TOKENS["exemplo"]), total, {}, medir)


def batida(i, ini, fim, fala, cena, primeira=False, ultima=False):
    return {"i": i, "ini": ini, "fim": fim, "fala": ini + 0.25, "fim_fala": fim - 0.3, "palavras": palavras(fala, ini + 0.25), "cena": cena, "primeira": primeira, "ultima": ultima}


class CenaPassos(unittest.TestCase):
    def cena(self, **extra):
        return {"tipo": "passos", "pedido": "pisca e olha para a câmera", "digita_na": "escrever", "resultado": "assets/v1.mp4", "resultado_na": "fazer", **extra}

    def montar(self, cena):
        p = peca()
        rc.cena_passos(p, batida(2, 4.0, 9.0, "é só escrever o que ela deve fazer agora", cena), {})
        return p

    def test_partida_fica_no_cartao_ate_o_resultado_chegar(self):
        p = self.montar(self.cena(partida="assets/foto.jpg"))
        secao = chr(10).join(p.secoes)
        self.assertIn("id=\"b2-pi\" style=\"background-image:url('assets/foto.jpg')\"", secao)
        self.assertLess(secao.index('id="b2-pi"'), secao.index('id="b2-gr"'))
        self.assertTrue(any('"#b2-pi"' in linha for linha in p.js))

    def test_sem_partida_o_cartao_fica_so_com_o_brilho(self):
        p = self.montar(self.cena())
        self.assertNotIn("b2-pi", chr(10).join(p.secoes))
        self.assertIn('id="b2-gr"', chr(10).join(p.secoes))

    def caixa_do_cartao(self, p):
        estilo = re.search(r'id="b2-esp" style="left:(\d+)px;top:(\d+)px;width:(\d+)px;height:(\d+)px"', chr(10).join(p.secoes))
        return [int(x) for x in estilo.groups()]

    def test_cartao_ocupa_o_espaco_entre_o_pedido_e_a_legenda(self):
        esquerda, topo, largura, altura = self.caixa_do_cartao(self.montar(self.cena()))
        pedido = next(c for c in self.montar(self.cena()).caixas if c["nome"] == "pedido")
        self.assertEqual(topo, pedido["y"] + pedido["h"] + rc.RESPIRO_DO_CARTAO)
        self.assertEqual(topo + altura, rc.LEGENDA_TOPO - rc.RESPIRO_DO_CARTAO)
        self.assertGreater(altura, 760)
        self.assertEqual(esquerda * 2 + largura, rc.LARGURA)

    def test_cartao_largo_respeita_a_largura_maxima_e_fica_centrado_na_area(self):
        esquerda, topo, largura, altura = self.caixa_do_cartao(self.montar(self.cena(formato="paisagem")))
        self.assertEqual(largura, rc.CARTAO_L_MAX)
        pedido_base = 250 + 150
        self.assertAlmostEqual(topo - pedido_base, rc.LEGENDA_TOPO - (topo + altura), delta=1)

    def test_partida_em_video_e_recusada_com_explicacao(self):
        with self.assertRaises(rc.ErroDeCena) as erro:
            self.montar(self.cena(partida="assets/v1.mp4"))
        self.assertIn("quadro", str(erro.exception))

    def test_resultado_em_video_vai_para_a_raiz_dentro_do_cartao(self):
        p = self.montar(self.cena())
        self.assertEqual(len(p.soltos), 1)
        self.assertIn('<video id="b2-rv"', p.soltos[0])
        self.assertIn('class="cartao" id="b2-res"', p.soltos[0])


class PrimeiroSegundo(unittest.TestCase):
    def test_titulo_da_abertura_so_entra_depois_de_um_segundo(self):
        p = peca()
        cena = {"tipo": "abertura", "midia": "assets/v2.mp4", "titulo": "ERA SÓ|*UMA FOTO*", "titulo_na": "Essa"}
        rc.cena_abertura(p, batida(1, 0.0, 4.0, "Essa capivara era só uma foto", cena, primeira=True), {})
        self.assertTrue(p.caixas)
        self.assertTrue(all(caixa["de"] >= 1.0 for caixa in p.caixas))


if __name__ == "__main__":
    unittest.main()
