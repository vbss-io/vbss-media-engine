import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _comum as c
import legenda
import pronuncia
import providers
import voz


def ouvidas(texto, passo=0.3):
    return [{"texto": p, "inicio": round(i * passo, 3), "fim": round((i + 1) * passo, 3)} for i, p in enumerate(texto.split())]


def tipos(texto, ouvido):
    return [(d["tipo"], d["esperado"], d["ouvido"]) for d in pronuncia.comparar(texto, ouvidas(ouvido))]


class TextoContraOuvido(unittest.TestCase):
    def test_pontuacao_caixa_e_acento_nao_contam(self):
        self.assertEqual(tipos("E veja como o mesmo jogo é anunciado: original, bateria nova, e por quanto.",
                               "E veja como o mesmo jogo é anunciado, original, bateria nova e por quanto."), [])
        self.assertEqual(tipos("Depois, a condição do seu: sem caixa.", "depois a condicao do seu. Sem caixa"), [])

    def test_palavra_ouvida_diferente_e_apontada(self):
        self.assertEqual(tipos("o mesmo jogo é anunciado: original", "o mesmo jogo é anunciciado, original"),
                         [("trocada", "anunciado:", "anunciciado,")])

    def test_palavra_pulada_e_palavra_a_mais(self):
        self.assertEqual(tipos("abra a página dele", "abra a dele"), [("faltou", "página", "")])
        self.assertEqual(tipos("abra a página", "abra a a página"), [("sobrou", "", "a")])

    def test_numero_em_algarismo_ou_por_extenso(self):
        self.assertEqual(tipos("custa 115 reais", "custa cento e quinze reais"), [])
        self.assertEqual(tipos("são 9 anúncios", "são nove anúncios"), [])
        self.assertEqual(tipos("são 9 anúncios", "são dez anúncios"), [("trocada", "9", "dez")])
        self.assertEqual(pronuncia.por_extenso(1294), "milduzentosenoventaequatro")
        self.assertEqual(pronuncia.por_extenso(2001), "doismileum")

    def test_nome_proprio_tolera_grafia_e_separacao(self):
        self.assertEqual(tipos("abra a página dele no FotoMural.", "abra a página dele no Foto Mural."), [])
        self.assertEqual(tipos("abra a página dele no FotoMural.", "abra a página dele no Fotomurall."), [])
        self.assertEqual(tipos("o jogo Suikoden é raro", "o jogo Suicoden é raro"), [])
        self.assertEqual(len(tipos("abra a página dele no FotoMural.", "abra a página dele no mercado.")), 1)

    def test_palavra_comum_nao_ganha_a_tolerancia_de_nome(self):
        self.assertEqual(tipos("o jogo completo na caixa", "o jogo complexo na caixa"), [("trocada", "completo", "complexo")])

    def test_inicio_de_frase_maiusculo_nao_e_nome_proprio(self):
        palavras = pronuncia.palavras_do_texto("Antes, abra. Depois veja o Mario e o FotoMural")
        self.assertEqual([p["texto"] for p in palavras if p["nome"]], ["Mario", "FotoMural"])

    def test_formas_faladas_equivalentes(self):
        self.assertEqual(tipos("isso é para você", "isso é pra você"), [])


class ChiadoAMais(unittest.TestCase):
    def test_conta_os_chiados_que_a_grafia_pede(self):
        self.assertEqual(pronuncia.chiados_esperados("anunciado:"), 1)
        self.assertEqual(pronuncia.chiados_esperados("condição"), 2)
        self.assertEqual(pronuncia.chiados_esperados("antigo?"), 1)
        self.assertEqual(pronuncia.chiados_esperados("Antes,"), 2)
        self.assertEqual(pronuncia.chiados_esperados("página"), 1)
        self.assertEqual(pronuncia.chiados_esperados("bateria"), 0)
        self.assertEqual(pronuncia.chiados_esperados("sucesso"), 3)

    def test_f_e_v_podem_soar_como_chiado_sem_acusar(self):
        self.assertEqual(pronuncia.chiados_esperados("foto."), 0)
        self.assertEqual(pronuncia.sopros_tolerados("foto."), 1)
        self.assertEqual(pronuncia.sopros_tolerados("vivo"), 2)
        self.assertEqual(pronuncia.sopros_tolerados("anunciado"), 0)
        palavras = ouvidas("era uma foto")
        self.assertEqual(pronuncia.chiados_a_mais(palavras, [(0.62, 0.7)]), [])
        fazer = [{"texto": "deve", "inicio": 0.0, "fim": 0.3}, {"texto": "fazer.", "inicio": 0.3, "fim": 0.8}]
        self.assertEqual(pronuncia.chiados_a_mais(fazer, [(0.1, 0.17), (0.32, 0.4), (0.5, 0.6)]), [])

    def test_f_nao_esconde_silaba_repetida_alem_do_sopro(self):
        fazer = [{"texto": "fazer.", "inicio": 0.3, "fim": 0.9}]
        suspeitas = pronuncia.chiados_a_mais(fazer, [(0.32, 0.4), (0.5, 0.6), (0.7, 0.8)])
        self.assertEqual([s["esperado"] for s in suspeitas], ["fazer."])

    def test_acha_trechos_de_chiado_pela_razao_entre_agudo_e_grave(self):
        grave = [1e-3] * 60
        agudo = [1e-6] * 60
        for i in list(range(10, 19)) + list(range(30, 33)) + list(range(40, 50)):
            agudo[i] = 1e-2
        self.assertEqual(pronuncia.achar_chiados(agudo, grave), [(0.1, 0.19), (0.4, 0.5)])

    def test_silaba_repetida_aparece_como_chiado_a_mais(self):
        palavras = ouvidas("jogo é anunciado, original")
        chiados = [(0.1, 0.2), (0.7, 0.78), (0.8, 0.88), (1.0, 1.1)]
        suspeitas = pronuncia.chiados_a_mais(palavras, chiados)
        self.assertEqual([(s["posicao"], s["esperado"]) for s in suspeitas], [(3, "anunciado,")])
        self.assertIn("silaba repetida", pronuncia.descrever(suspeitas[0]))

    def test_chiado_que_escorrega_para_a_palavra_vizinha_nao_acusa(self):
        palavras = ouvidas("onde o seu jogo")
        chiados = [(0.48, 0.58), (1.0, 1.1)]
        self.assertEqual(pronuncia.chiados_a_mais(palavras, chiados), [])

    def test_vizinha_sem_chiado_nao_esconde_a_silaba_repetida_no_meio_da_palavra(self):
        palavras = [{"texto": "é", "inicio": 1.06, "fim": 1.22}, {"texto": "anunciado.", "inicio": 1.22, "fim": 1.84}, {"texto": "Original,", "inicio": 1.96, "fim": 2.4}]
        suspeitas = pronuncia.chiados_a_mais(palavras, [(1.35, 1.43), (1.48, 1.58)])
        self.assertEqual([s["esperado"] for s in suspeitas], ["anunciado."])

    def test_fala_sem_divergencia_passa(self):
        resultado = pronuncia.conferir_fala("nao-usado.wav", "Abra a página dele.", ouvidas("abra a página dele"), acustica=False)
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["divergencias"], [])


class ProvedorComSemente:
    NOME = "voicestudio"
    LOCAL = True
    VOZ_PADRAO = "narradora"
    ACEITA_SEMENTE = True
    SEMENTES = (7, 11, 23)

    def __init__(self):
        self.chamadas = []

    def disponivel(self, variante=None):
        return True, "pronto"

    def sintetizar(self, linhas, voz, pasta, velocidade=1.0, variante=None, sementes=None):
        self.chamadas.append((list(linhas), list(sementes or [])))
        itens = []
        for i, _ in enumerate(linhas, 1):
            destino = Path(pasta) / f"bruto-{i:02d}.wav"
            destino.write_bytes(b"RIFF")
            itens.append({"arquivo": str(destino), "sintese_s": 1.0, "audio_s": 2.0, "semente": sementes[i - 1]})
        return {"modelo": "falso", "carga_s": 0.1, "itens": itens}


class NovaTentativaComOutraSemente(unittest.TestCase):
    def rodar(self, ruins_por_semente, extra=()):
        prov = ProvedorComSemente()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pasta = Path(tmp.name)
        entrada = pasta / "voz.txt"
        entrada.write_text("Abra a página dele.\nO jogo é anunciado assim.\n", encoding="utf-8")
        rodada = {"n": 0}

        def conferir(itens, threads=4):
            semente = prov.chamadas[-1][1][0]
            rodada["n"] += 1
            saida = []
            for it in itens:
                ruim = it["texto"] in ruins_por_semente.get(semente, ())
                saida.append({"ok": not ruim, "ouvido": it["texto"], "divergencias": [{"tipo": "trocada", "posicao": 4, "esperado": "anunciado", "ouvido": "anunciciado"}] if ruim else []})
            return saida

        def tratar(bruto, destino, cfg):
            Path(destino).write_bytes(Path(bruto).read_bytes())
            return 0.0, {"duracao": 2.0, "lufs_integrado": -16.0, "pico_dbtp": -2.0}

        cfg = {"provedor": "voicestudio", "vozes_padrao": {"voicestudio": "narradora"}, "velocidade": 1.0, "alvo_lufs": -16.0, "teto_pico_dbtp": -1.5, "taxa_saida": 48000, "origem": {}}
        saida = io.StringIO()
        with mock.patch.object(providers, "carregar", return_value=prov), mock.patch.object(voz, "config", return_value=cfg), \
                mock.patch.object(voz, "pos_processar", side_effect=tratar), mock.patch.object(pronuncia, "conferir_arquivos", side_effect=conferir), \
                mock.patch.object(legenda, "whisper_disponivel", return_value=(("vs", "modelo"), "ok")), mock.patch.object(c, "exigir_ffmpeg"), \
                mock.patch.object(sys, "argv", ["voz.py", str(entrada), "--saida", str(pasta / "voz"), *extra]), contextlib.redirect_stdout(saida):
            voz.main()
        return prov, c.ler_json(pasta / "voz" / "voz.json"), saida.getvalue()

    def test_fala_divergente_e_refeita_so_ela_com_a_semente_seguinte(self):
        prov, dados, texto = self.rodar({7: ("O jogo é anunciado assim.",)})
        self.assertEqual(prov.chamadas, [(["Abra a página dele.", "O jogo é anunciado assim."], [7, 7]), (["O jogo é anunciado assim."], [11])])
        primeira, segunda = dados["linhas"]
        self.assertEqual((primeira["semente"], primeira["pronuncia"]["ok"], primeira["pronuncia"]["tentativas"]), (7, True, 1))
        self.assertEqual((segunda["semente"], segunda["pronuncia"]["ok"], segunda["pronuncia"]["tentativas"]), (11, True, 2))
        self.assertIn("pronuncia conferida em todas as falas", texto)

    def test_para_no_limite_de_tentativas_e_avisa_o_que_sobrou(self):
        ruim = ("O jogo é anunciado assim.",)
        prov, dados, texto = self.rodar({7: ruim, 11: ruim, 23: ruim}, extra=("--tentativas", "2"))
        self.assertEqual([s for _, s in prov.chamadas], [[7, 7], [11]])
        segunda = dados["linhas"][1]
        self.assertFalse(segunda["pronuncia"]["ok"])
        self.assertEqual(segunda["pronuncia"]["tentativas"], 2)
        self.assertEqual(segunda["semente"], 7)
        self.assertIn("OUCA antes de usar: voz-02.wav", texto)
        self.assertIn("anunciciado", texto)

    def test_sem_conferencia_gera_uma_vez_so(self):
        prov, dados, _ = self.rodar({7: ("O jogo é anunciado assim.",)}, extra=("--sem-conferencia",))
        self.assertEqual(len(prov.chamadas), 1)
        self.assertNotIn("pronuncia", dados["linhas"][1])

    def test_batidas_gera_so_a_pedida_e_mantem_a_outra(self):
        prov = ProvedorComSemente()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pasta = Path(tmp.name)
        (pasta / "voz").mkdir()
        (pasta / "voz" / "voz-01.wav").write_bytes(b"RIFF")
        c.escrever_json(pasta / "voz" / "voz.json", {"linhas": [{"batida": 1, "texto": "Abra a página dele.", "caracteres": 19, "arquivo": "voz-01.wav", "duracao_s": 1.5}]})
        entrada = pasta / "voz.txt"
        entrada.write_text("Abra a página dele.\nO jogo é anunciado assim.\n", encoding="utf-8")
        cfg = {"provedor": "voicestudio", "vozes_padrao": {"voicestudio": "narradora"}, "velocidade": 1.0, "alvo_lufs": -16.0, "teto_pico_dbtp": -1.5, "taxa_saida": 48000, "origem": {}}
        medida = (0.0, {"duracao": 2.0, "lufs_integrado": -16.0, "pico_dbtp": -2.0})

        def tratar(bruto, destino, _cfg):
            Path(destino).write_bytes(b"RIFF")
            return medida

        with mock.patch.object(providers, "carregar", return_value=prov), mock.patch.object(voz, "config", return_value=cfg), \
                mock.patch.object(voz, "pos_processar", side_effect=tratar), mock.patch.object(c, "exigir_ffmpeg"), \
                mock.patch.object(sys, "argv", ["voz.py", str(entrada), "--saida", str(pasta / "voz"), "--batidas", "2", "--sem-conferencia"]), \
                contextlib.redirect_stdout(io.StringIO()):
            voz.main()
        self.assertEqual(prov.chamadas, [(["O jogo é anunciado assim."], [7])])
        dados = c.ler_json(pasta / "voz" / "voz.json")
        self.assertEqual([(x["batida"], x["arquivo"]) for x in dados["linhas"]], [(1, "voz-01.wav"), (2, "voz-02.wav")])
        self.assertTrue((pasta / "voz" / "voz-01.wav").is_file())


if __name__ == "__main__":
    unittest.main()
