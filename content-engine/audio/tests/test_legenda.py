import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import legenda


def ouvidas(*itens):
    return [{"texto": t, "inicio": i, "fim": f} for t, i, f in itens]


def em_sequencia(texto, passo=0.3, pausas=None):
    pausas = pausas or {}
    palavras = legenda.tokens_do_roteiro(texto)
    t = 0.0
    saida = []
    for n, p in enumerate(palavras):
        t += pausas.get(n, 0.0)
        saida.append({**p, "inicio": round(t, 3), "fim": round(t + passo, 3)})
        t += passo
    return saida


def textos(blocos):
    return [" ".join(p["texto"] for p in b["palavras"]) for b in blocos]


class Roteiro(unittest.TestCase):
    def test_normaliza_acento_caixa_e_pontuacao(self):
        self.assertEqual(legenda.normalizar("Página,"), "pagina")
        self.assertEqual(legenda.normalizar("FotoMural."), "fotomural")
        self.assertEqual(legenda.normalizar("-"), "")

    def test_marca_destaque_por_asterisco_e_por_lista(self):
        palavras = legenda.tokens_do_roteiro("Veja o *preço* e a *versão exata* do jogo", destaques=["Jogo"])
        marcadas = [p["texto"] for p in palavras if p["destaque"]]
        self.assertEqual(marcadas, ["preço", "versão", "exata", "jogo"])
        self.assertTrue(all("*" not in p["texto"] for p in palavras))

    def test_pontuacao_solta_gruda_na_palavra_anterior(self):
        palavras = legenda.tokens_do_roteiro("Antes - abra a página")
        self.assertEqual([p["texto"] for p in palavras], ["Antes -", "abra", "a", "página"])


class Alinhamento(unittest.TestCase):
    def test_casamento_exato_mantem_a_grafia_do_roteiro(self):
        roteiro = legenda.tokens_do_roteiro("Abra a página dele.")
        tempos, casadas = legenda.alinhar(roteiro, ouvidas(("abra", 0.1, 0.4), ("a", 0.4, 0.5), ("pagina", 0.5, 1.0), ("dele", 1.0, 1.3)), 1.5)
        self.assertEqual(casadas, 4)
        self.assertEqual(tempos, [(0.1, 0.4), (0.4, 0.5), (0.5, 1.0), (1.0, 1.3)])

    def test_palavra_ouvida_errada_recebe_o_tempo_do_trecho_trocado(self):
        roteiro = legenda.tokens_do_roteiro("abra no FotoMural agora")
        tempos, casadas = legenda.alinhar(roteiro, ouvidas(("abra", 0.0, 0.3), ("no", 0.3, 0.4), ("foto", 0.4, 0.7), ("mural", 0.7, 1.0), ("agora", 1.1, 1.5)), 1.6)
        self.assertEqual(casadas, 3)
        self.assertEqual(tempos[2], (0.4, 1.0))
        self.assertEqual(tempos[3], (1.1, 1.5))

    def test_palavra_sem_par_e_interpolada_no_vao(self):
        roteiro = legenda.tokens_do_roteiro("um jogo muito antigo")
        tempos, casadas = legenda.alinhar(roteiro, ouvidas(("um", 0.0, 0.2), ("jogo", 0.2, 0.6), ("antigo", 1.0, 1.5)), 1.6)
        self.assertEqual(casadas, 3)
        self.assertEqual(tempos[2], (0.6, 1.0))

    def test_palavra_sem_par_e_sem_vao_divide_o_tempo_das_vizinhas(self):
        roteiro = legenda.tokens_do_roteiro("um jogo muito antigo")
        tempos, _ = legenda.alinhar(roteiro, ouvidas(("um", 0.0, 0.2), ("jogo", 0.2, 0.6), ("antigo", 0.6, 1.2)), 1.3)
        self.assertEqual(tempos[1][0], 0.2)
        self.assertEqual(tempos[3][1], 1.2)
        self.assertGreater(tempos[2][1] - tempos[2][0], 0.1)

    def test_tempos_nunca_voltam(self):
        roteiro = legenda.tokens_do_roteiro("a versão exata de cada uma tem preço")
        tempos, _ = legenda.alinhar(roteiro, ouvidas(("a", 0.0, 0.1), ("versao", 0.1, 0.5), ("cada", 0.9, 1.1), ("tem", 1.4, 1.6)), 2.0)
        anterior = 0.0
        for inicio, fim in tempos:
            self.assertGreaterEqual(inicio, anterior)
            self.assertGreater(fim, inicio)
            anterior = fim
        self.assertLessEqual(tempos[-1][1], 2.0)

    def test_sem_nada_ouvido_nao_casa_nada(self):
        roteiro = legenda.tokens_do_roteiro("abra a página")
        tempos, casadas = legenda.alinhar(roteiro, [], 1.2)
        self.assertEqual(casadas, 0)
        self.assertEqual(len(tempos), 3)
        self.assertEqual(tempos[-1][1], 1.2)


class PlanoB(unittest.TestCase):
    def test_distribui_proporcional_aos_caracteres_pulando_o_silencio(self):
        roteiro = legenda.tokens_do_roteiro("abcd ef abcdef")
        tempos = legenda.distribuir_em_trechos(roteiro, [(0.0, 0.6), (1.0, 1.6)])
        self.assertEqual(tempos[0], (0.0, 0.4))
        self.assertEqual(tempos[1], (0.4, 0.6))
        self.assertEqual(tempos[2], (1.0, 1.6))

    def test_sem_trecho_devolve_vazio(self):
        self.assertEqual(legenda.distribuir_em_trechos(legenda.tokens_do_roteiro("oi"), []), [])


class Blocos(unittest.TestCase):
    def test_no_maximo_quatro_palavras(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("uma duas tres quatro cinco seis sete oito nove dez onze doze"), max_caracteres=99)
        self.assertEqual([len(b["palavras"]) for b in blocos], [4, 4, 4])

    def test_quebra_em_pontuacao_forte(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("Vai anunciar? Antes, abra aqui."))
        self.assertEqual(textos(blocos), ["Vai anunciar?", "Antes, abra aqui."])

    def test_quebra_em_pausa_longa(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("sem caixa completo lacrado", pausas={2: 0.5}))
        self.assertEqual(textos(blocos), ["sem caixa", "completo lacrado"])

    def test_pausa_curta_nao_quebra(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("sem caixa completo lacrado", pausas={2: 0.2}))
        self.assertEqual(textos(blocos), ["sem caixa completo lacrado"])

    def test_palavra_curta_nao_fica_no_fim_do_bloco(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("abra logo esta página de avaliação completa hoje"), max_caracteres=99)
        self.assertEqual(textos(blocos), ["abra logo esta página", "de avaliação completa hoje"])
        blocos = legenda.quebrar_em_blocos(em_sequencia("veja como anuncia o mesmo jogo antigo"), max_caracteres=99)
        self.assertEqual(textos(blocos), ["veja como anuncia", "o mesmo jogo antigo"])

    def test_palavra_sozinha_no_fim_puxa_companhia(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("Vai anunciar um jogo antigo?"))
        self.assertEqual(textos(blocos), ["Vai anunciar", "um jogo antigo?"])
        blocos = legenda.quebrar_em_blocos(em_sequencia("primeiro segundo terceiro quarto quinto"), max_caracteres=99)
        self.assertEqual(textos(blocos), ["primeiro segundo terceiro", "quarto quinto"])

    def test_bloco_de_uma_palavra_curta_se_junta_ao_vizinho(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("E veja como anunciam", pausas={1: 0.6}))
        self.assertEqual(textos(blocos), ["E veja como anunciam"])
        blocos = legenda.quebrar_em_blocos(em_sequencia("abra a página já", pausas={3: 0.6}))
        self.assertEqual(textos(blocos), ["abra a página já"])

    def test_limite_de_caracteres(self):
        blocos = legenda.quebrar_em_blocos(em_sequencia("extraordinariamente inconstitucional paralelepipedo magnifico"), max_caracteres=32)
        for b in blocos:
            self.assertLessEqual(len(b["palavras"]), 2)

    def test_tempos_do_bloco_e_deslocamento_absoluto(self):
        blocos = legenda.deslocar(legenda.quebrar_em_blocos(em_sequencia("abra a *página* dele")), 5.05)
        self.assertEqual(blocos[0]["inicio"], 5.05)
        self.assertEqual(blocos[0]["fim"], 6.25)
        self.assertEqual(blocos[0]["palavras"][2], {"texto": "página", "inicio": 5.65, "fim": 5.95, "destaque": True})
        self.assertNotIn("destaque", blocos[0]["palavras"][0])

    def test_nenhuma_palavra_se_perde(self):
        texto = "Com a página aberta, você anuncia sabendo onde o seu jogo está no mercado."
        blocos = legenda.quebrar_em_blocos(em_sequencia(texto))
        self.assertEqual(" ".join(textos(blocos)), texto)
        for b in blocos[:-1]:
            self.assertLessEqual(len(b["palavras"]), 4)
            self.assertFalse(len(b["palavras"]) > 1 and legenda._curta(b["palavras"][-1]))


if __name__ == "__main__":
    unittest.main()
