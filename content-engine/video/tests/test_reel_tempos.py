import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import checar_reel
import reel_tempos as rt

ANCORAS = {"whoosh/whoosh-cine-longo": 0.6, "transition/transicao-cine": 0.75, "riser/reverso-cine-longo": 1.2, "tick/tique-cine-macio": 0.0}


def fala(texto, inicio=0.0, passo=0.3):
    palavras = []
    t = inicio
    for p in texto.split():
        palavras.append({"texto": p, "inicio": round(t, 3), "fim": round(t + passo, 3)})
        t += passo
    return palavras


class FalaParaAVoz(unittest.TestCase):
    def test_troca_so_a_palavra_inteira_e_tira_o_asterisco(self):
        mapa = {"Agil": "Ágil"}
        self.assertEqual(rt.para_a_voz("Na *Agil*, a foto vira vídeo.", mapa), "Na Ágil, a foto vira vídeo.")
        self.assertEqual(rt.para_a_voz("Agils e agil ficam como estão.", mapa), "Agils e agil ficam como estão.")

    def test_sem_mapa_a_fala_sai_igual(self):
        self.assertEqual(rt.para_a_voz("Crie o seu no site.", None), "Crie o seu no site.")
        self.assertEqual(rt.para_a_voz("Crie o seu no site.", {}), "Crie o seu no site.")

    def test_expressao_mais_longa_vence_a_mais_curta(self):
        mapa = {"IA": "i a", "IA generativa": "inteligência artificial generativa"}
        self.assertEqual(rt.para_a_voz("Vídeo com IA generativa e com IA.", mapa), "Vídeo com inteligência artificial generativa e com i a.")


class PalavraViraMomento(unittest.TestCase):
    def setUp(self):
        self.palavras = fala("Depois, a condição do seu: sem caixa, completo na caixa ou lacrado.", inicio=9.25)

    def test_palavra_ignora_acento_caixa_e_pontuacao(self):
        self.assertEqual(rt.momento(self.palavras, "CONDICAO"), 9.85)
        self.assertEqual(rt.momento(self.palavras, {"na": "seu"}), 10.45)

    def test_expressao_de_varias_palavras_usa_o_inicio_da_primeira(self):
        self.assertEqual(rt.momento(self.palavras, "sem caixa"), 10.75)

    def test_segunda_ocorrencia_e_ponto_no_fim(self):
        self.assertEqual(rt.momento(self.palavras, {"na": "caixa", "vez": 2}), 11.95)
        self.assertEqual(rt.momento(self.palavras, {"na": "sem caixa", "ponto": "fim"}), 11.35)

    def test_inicio_e_fim_da_fala(self):
        self.assertEqual(rt.momento(self.palavras, "@inicio"), 9.25)
        self.assertEqual(rt.momento(self.palavras, "@fim"), 12.85)

    def test_ajuste_pequeno_soma_e_ajuste_grande_e_recusado(self):
        self.assertEqual(rt.momento(self.palavras, {"na": "completo", "ajuste": 0.25}), 11.6)
        with self.assertRaises(rt.ErroDeRoteiro):
            rt.momento(self.palavras, {"na": "completo", "ajuste": 0.8})

    def test_palavra_que_nao_esta_na_fala_explica_o_erro(self):
        with self.assertRaises(rt.ErroDeRoteiro) as erro:
            rt.momento(self.palavras, "lacrada")
        self.assertIn("nao aparece na fala", str(erro.exception))
        with self.assertRaises(rt.ErroDeRoteiro) as erro:
            rt.momento(self.palavras, {"na": "caixa", "vez": 3})
        self.assertIn("so aparece 2 vez(es)", str(erro.exception))

    def test_separa_as_palavras_da_legenda_por_fala(self):
        legenda = {"falas": [{"palavras": 2}, {"palavras": 3}],
                   "blocos": [{"palavras": fala("Vai anunciar")}, {"palavras": fala("Antes abra", 4.0)}, {"palavras": fala("agora", 5.0)}]}
        separadas = rt.separar_por_fala(legenda)
        self.assertEqual([[p["texto"] for p in f] for f in separadas], [["Vai", "anunciar"], ["Antes", "abra", "agora"]])

    def test_texto_nao_entra_no_primeiro_segundo_da_peca(self):
        self.assertEqual(rt.segurar_texto(0.15, True), 1.0)
        self.assertEqual(rt.segurar_texto(1.77, True), 1.77)
        self.assertEqual(rt.segurar_texto(4.6, False), 4.6)


class EncaixeNoCompasso(unittest.TestCase):
    def test_corte_sobe_para_a_proxima_batida_da_musica(self):
        self.assertEqual(rt.encaixar(4.304, 107), 4.486)
        self.assertEqual(rt.encaixar(4.486, 107), 4.486)
        self.assertEqual(rt.encaixar(4.50, 107), 4.486)
        self.assertEqual(rt.encaixar(4.53, 107), 5.047)

    def test_sem_bpm_o_corte_fica_onde_a_fala_pede(self):
        self.assertEqual(rt.encaixar(4.304, None), 4.304)

    def test_plano_das_falas_do_piloto_cai_nos_cortes_do_piloto(self):
        plano = rt.planejar([3.854, 3.853, 3.855, 4.188, 4.143], bpm=107)
        self.assertEqual([b["inicio"] for b in plano], [0.0, 4.486, 8.972, 13.458, 18.505])
        self.assertEqual([b["fala"] for b in plano], [0.15, 4.74, 9.22, 13.71, 18.75])
        passo = 60 / 107
        for b in plano:
            self.assertAlmostEqual(b["fim"] / passo, round(b["fim"] / passo), places=2)

    def test_cada_batida_cobre_a_fala_com_respiro_e_a_ultima_ganha_a_cauda(self):
        plano = rt.planejar([2.0, 3.0], bpm=None)
        self.assertEqual(plano[0], {"inicio": 0.0, "fala": 0.15, "fim_fala": 2.15, "fim": 2.45})
        self.assertEqual(plano[1]["fala"], 2.7)
        self.assertAlmostEqual(plano[1]["fim"], 2.7 + 3.0 + rt.CAUDA_FECHO, places=3)

    def test_minimo_visual_estica_a_batida(self):
        plano = rt.planejar([1.0, 1.0], minimos=[4.0, None])
        self.assertEqual(plano[0]["fim"], 4.0)


class AncoraDoEfeito(unittest.TestCase):
    def test_deixa_sai_antes_do_movimento_pelo_tamanho_da_ancora(self):
        self.assertEqual(rt.ancorar(6.0, 0.6), 5.4)
        d = rt.deixa("camera", 6.0, ANCORAS)
        self.assertEqual((d["t"], d["efeito"], d["volume"]), (5.4, "whoosh/whoosh-cine-longo", 0.4))

    def test_efeito_sem_ancora_cai_no_proprio_momento(self):
        self.assertEqual(rt.deixa("foco", 6.51, ANCORAS)["t"], 6.51)

    def test_ancora_maior_que_o_momento_nao_gera_tempo_negativo(self):
        self.assertEqual(rt.deixa("sobe_logo", 0.5, ANCORAS)["t"], 0.0)

    def test_nivel_com_voz_e_menor_que_sem_voz_e_duracao_apara(self):
        com = rt.deixa("troca", 4.49, ANCORAS, com_voz=True)
        sem = rt.deixa("troca", 4.49, ANCORAS, com_voz=False)
        self.assertEqual(com["t"], 3.74)
        self.assertLess(com["volume"], sem["volume"])
        self.assertEqual(rt.deixa("digita", 7.6, ANCORAS, duracao=0.7)["duracao"], 0.7)

    def test_enxugar_tira_o_mesmo_efeito_repetido_em_cima(self):
        deixas = [{"t": 1.0, "efeito": "pop/a"}, {"t": 1.05, "efeito": "pop/a"}, {"t": 1.05, "efeito": "pop/b"}, {"t": 1.3, "efeito": "pop/a"}, {"t": 0.2, "arquivo": "voz-01.wav"}]
        limpas = rt.enxugar(deixas)
        self.assertEqual([(d["t"], d.get("efeito")) for d in limpas], [(0.2, None), (1.0, "pop/a"), (1.05, "pop/b"), (1.3, "pop/a")])


class ChecagemDeMotion(unittest.TestCase):
    def test_trecho_parado_le_a_saida_do_freezedetect(self):
        saida = "lavfi.freezedetect.freeze_start: 4.9\nlavfi.freezedetect.freeze_duration: 0.33\nlavfi.freezedetect.freeze_start: 24.0\n"
        self.assertEqual(checar_reel.trechos_parados(saida, 25.4), [(4.9, 0.33), (24.0, 1.4)])

    def test_limites_do_trecho_parado(self):
        self.assertEqual(checar_reel.avaliar_parados([(1.0, 0.47), (5.0, 0.33)], 25.4)["nivel"], "passa")
        self.assertEqual(checar_reel.avaliar_parados([(1.0, 0.7)], 25.4)["nivel"], "aviso")
        self.assertEqual(checar_reel.avaliar_parados([(1.0, 1.2)], 25.4)["nivel"], "falha")
        self.assertEqual(checar_reel.avaliar_parados([(float(i), 0.5) for i in range(12)], 25.0)["nivel"], "falha")

    def test_loudness(self):
        self.assertEqual(checar_reel.avaliar_som(-14.0, -1.5), "passa")
        self.assertEqual(checar_reel.avaliar_som(-16.2, -1.5), "aviso")
        self.assertEqual(checar_reel.avaliar_som(-14.0, -0.2), "falha")
        self.assertEqual(checar_reel.avaliar_som(-19.0, -3.0), "falha")

    def test_texto_fora_da_zona_segura(self):
        self.assertEqual(checar_reel.fora_da_zona({"x": 60, "y": 236, "w": 880, "h": 316}), [])
        self.assertEqual(checar_reel.fora_da_zona({"x": 60, "y": 1450, "w": 880, "h": 80}), ["rodape"])
        self.assertEqual(checar_reel.fora_da_zona({"x": 20, "y": 100, "w": 1000, "h": 80}), ["esquerda", "direita", "topo"])

    def test_quique_em_excesso(self):
        calmo = "tl.to(\"#a\", { y: 0, ease: \"expo.out\" }, 1);\n" * 30 + "K.toque(\"#fone\", 7.3);\n"
        quiques, animacoes, limite = checar_reel.contar_quiques(calmo)
        self.assertEqual((quiques, animacoes), (1, 31))
        self.assertLessEqual(quiques, limite)
        pulando = "tl.fromTo(\"#a\", { y: 26 }, { y: 0, ease: \"back.out(2)\" }, 1);\n" * 10 + "tl.to(\"#b\", { x: 0 }, 2);\n" * 10
        quiques, animacoes, limite = checar_reel.contar_quiques(pulando)
        self.assertEqual(quiques, 10)
        self.assertGreater(quiques, limite)

    def test_legenda_padrao_fica_acima_do_rodape(self):
        geo = checar_reel.geometria_da_legenda("K.legenda(\"#legenda\", window.__legenda, { ativa: \"#FFCB52\" });")
        self.assertEqual(checar_reel.fora_da_zona(geo), [])
        baixa = checar_reel.geometria_da_legenda("K.legenda(\"#legenda\", window.__legenda, { base: \"12%\" });")
        self.assertEqual(checar_reel.fora_da_zona(baixa), ["rodape"])
        self.assertIsNone(checar_reel.geometria_da_legenda("tl.to(\"#a\", {});"))

    def test_cortes_fora_do_compasso(self):
        self.assertEqual(checar_reel.no_compasso([0.0, 4.486, 8.972, 18.505], 107), [])
        self.assertEqual(checar_reel.no_compasso([0.0, 4.2], 107), [4.2])


if __name__ == "__main__":
    unittest.main()
