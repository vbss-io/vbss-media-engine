import base64
import io
import json
import math
import os
import struct
import sys
import tempfile
import types
import unittest
import urllib.error
import wave
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _comum as c
import comparar_vozes
import provedores
import voz
from provedores import azure, azure_openai

CHAVE_FALSA = "CHAVE-FALSA-DE-TESTE-123"
NS = {"s": "http://www.w3.org/2001/10/synthesis", "m": "https://www.w3.org/2001/mstts"}


def wav_falso(segundos=1.2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        n = int(24000 * segundos)
        w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 220 * i / 24000))) for i in range(n)))
    return buf.getvalue()


class Resposta:
    def __init__(self, corpo):
        self.corpo = corpo

    def read(self, *_):
        return self.corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def resposta_gpt(transcricao, tokens=(120, 80, 200)):
    return Resposta(json.dumps({
        "choices": [{"message": {"audio": {"data": base64.b64encode(wav_falso()).decode(), "transcript": transcricao}}}],
        "usage": {"prompt_tokens": tokens[0], "completion_tokens": tokens[1], "total_tokens": tokens[2], "completion_tokens_details": {"audio_tokens": 70}},
    }).encode("utf-8"))


def pasta_temporaria():
    c.WORK_DIR.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=c.WORK_DIR)


class SsmlAzure(unittest.TestCase):
    def test_voz_mai_simples_sem_estilo_nem_prosodia(self):
        raiz = ET.fromstring(azure.montar_ssml("Olá, mundo.", "pt-BR-Luana:MAI-Voice-2.1"))
        voz_el = raiz.find("s:voice", NS)
        self.assertEqual(voz_el.get("name"), "pt-BR-Luana:MAI-Voice-2.1")
        self.assertEqual(raiz.get("{http://www.w3.org/XML/1998/namespace}lang"), "pt-BR")
        self.assertIsNone(voz_el.find("m:express-as", NS))
        self.assertIsNone(voz_el.find(".//s:prosody", NS))
        self.assertEqual(voz_el.text, "Olá, mundo.")

    def test_estilo_envolve_o_texto_com_express_as(self):
        for nome in ("pt-BR-Luana:MAI-Voice-2.1-Flash", "pt-BR-Thalita:DragonHDLatestNeural"):
            raiz = ET.fromstring(azure.montar_ssml("Vamos!", nome, estilo="excited"))
            estilo = raiz.find("s:voice", NS).find("m:express-as", NS)
            self.assertEqual(estilo.get("style"), "excited")
            self.assertEqual(estilo.text, "Vamos!")
            self.assertEqual(raiz.find("s:voice", NS).get("name"), nome)

    def test_taxa_e_altura_ficam_dentro_do_estilo(self):
        raiz = ET.fromstring(azure.montar_ssml("Oi", "pt-BR-FranciscaNeural", velocidade=1.1, estilo="calm", altura="+2st"))
        pros = raiz.find("s:voice", NS).find("m:express-as", NS).find("s:prosody", NS)
        self.assertEqual(pros.get("rate"), "+10%")
        self.assertEqual(pros.get("pitch"), "+2st")
        self.assertEqual(pros.text, "Oi")

    def test_escapa_xml_e_remove_controle(self):
        texto = 'Tom & Jerry <b>"aspas"</b> \'ok\'\x00\x08'
        raiz = ET.fromstring(azure.montar_ssml(texto, "pt-BR-Luana:MAI-Voice-2.1", estilo="happy"))
        lido = raiz.find("s:voice", NS).find("m:express-as", NS).text
        self.assertEqual(lido, 'Tom & Jerry <b>"aspas"</b> \'ok\'')
        self.assertNotIn("<b>", azure.montar_ssml(texto, "x"))

    def test_estilo_e_altura_invalidos_sao_recusados(self):
        for estilo in ("x' onload='1", "a b", "<x>"):
            with self.assertRaises(ValueError):
                azure.montar_ssml("oi", "v", estilo=estilo)
        with self.assertRaises(ValueError):
            azure.montar_ssml("oi", "v", altura="alto demais")


class SinteseAzure(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": CHAVE_FALSA}, clear=False)
        self.env.start()
        os.environ.pop("AZURE_SPEECH_REGION", None)
        self.addCleanup(self.env.stop)

    def test_requisicao_regiao_padrao_cabecalhos_e_estilo_por_batida(self):
        pedidos = []

        def falso(req, timeout=0):
            pedidos.append(req)
            return Resposta(wav_falso())

        with pasta_temporaria() as tmp, mock.patch("urllib.request.urlopen", falso):
            res = azure.sintetizar(["Primeira.", "Segunda & final."], "pt-BR-Luana:MAI-Voice-2.1", tmp, opcoes={"estilo": "happy", "estilos": ["excited", None]})
            self.assertTrue(all(Path(i["arquivo"]).is_file() for i in res["itens"]))
        self.assertEqual(pedidos[0].full_url, "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1")
        self.assertEqual(pedidos[0].get_header("Ocp-apim-subscription-key"), CHAVE_FALSA)
        self.assertEqual(pedidos[0].get_header("Content-type"), "application/ssml+xml")
        self.assertEqual(pedidos[0].get_header("X-microsoft-outputformat"), "riff-24khz-16bit-mono-pcm")
        estilos = [ET.fromstring(p.data).find("s:voice", NS).find("m:express-as", NS).get("style") for p in pedidos]
        self.assertEqual(estilos, ["excited", "happy"])
        self.assertIn("&amp;", pedidos[1].data.decode("utf-8"))
        self.assertEqual([i["estilo"] for i in res["itens"]], ["excited", "happy"])

    def test_regiao_do_ambiente_e_validada(self):
        with mock.patch.dict(os.environ, {"AZURE_SPEECH_REGION": "westeurope"}):
            self.assertEqual(azure.disponivel()[0], True)
        with mock.patch.dict(os.environ, {"AZURE_SPEECH_REGION": "evil.com/x"}):
            self.assertEqual(azure.disponivel()[0], False)

    def test_erro_http_nao_vaza_a_chave(self):
        def falha(req, timeout=0):
            raise urllib.error.HTTPError(req.full_url, 401, "negado", {}, io.BytesIO(b"Access denied"))

        with pasta_temporaria() as tmp, mock.patch("urllib.request.urlopen", falha):
            with self.assertRaises(RuntimeError) as ctx:
                azure.sintetizar(["x"], "pt-BR-FranciscaNeural", tmp)
        self.assertIn("401", str(ctx.exception))
        self.assertNotIn(CHAVE_FALSA, str(ctx.exception))

    def test_lista_ao_vivo_filtra_ptbr_e_agrupa_por_tipo(self):
        amostra = [
            {"ShortName": "en-US-JennyNeural", "Locale": "en-US", "Gender": "Female", "VoiceType": "Neural"},
            {"ShortName": "pt-BR-Luana:MAI-Voice-2.1", "Locale": "pt-BR", "Gender": "Female", "VoiceType": "NeuralHD", "StyleList": ["excited", "happy"]},
            {"ShortName": "pt-BR-Luana:MAI-Voice-2.1-Flash", "Locale": "pt-BR", "Gender": "Female", "VoiceType": "NeuralHD"},
            {"ShortName": "pt-BR-Thalita:DragonHDLatestNeural", "Locale": "pt-BR", "Gender": "Female", "VoiceType": "NeuralHD"},
            {"ShortName": "pt-BR-FranciscaNeural", "Locale": "pt-BR", "Gender": "Female", "VoiceType": "Neural", "StyleList": ["calm"]},
            {"ShortName": "pt-PT-RaquelNeural", "Locale": "pt-PT", "Gender": "Female", "VoiceType": "Neural"},
        ]
        grupos = azure.agrupar_vozes_ptbr(amostra)
        self.assertEqual([g for g, _ in grupos], ["MAI-Voice 2.1", "MAI-Voice 2.1 Flash", "Dragon HD", "Neural"])
        todos = [v["id"] for _, vs in grupos for v in vs]
        self.assertNotIn("en-US-JennyNeural", todos)
        self.assertNotIn("pt-PT-RaquelNeural", todos)
        self.assertIn("excited, happy", grupos[0][1][0]["nota"])
        with mock.patch("urllib.request.urlopen", lambda req, timeout=0: Resposta(json.dumps(amostra).encode())) as _:
            self.assertEqual(len(azure.listar_vozes_vivo()), 4)

    def test_sem_chave_a_lista_vem_curada_e_marcada(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AZURE_SPEECH_KEY")
            ok, motivo = azure.disponivel()
        self.assertFalse(ok)
        ids = [v["id"] for v in azure.VOZES]
        for esperado in ("pt-BR-Luana:MAI-Voice-2.1", "pt-BR-Luana:MAI-Voice-2.1-Flash", "pt-BR-Thalita:DragonHDLatestNeural", "pt-BR-FranciscaNeural"):
            self.assertIn(esperado, ids)


class NormalizacaoEVerbatim(unittest.TestCase):
    def test_normaliza_acento_caixa_e_pontuacao(self):
        self.assertTrue(azure_openai.igual_ao_texto("Três passos: cento e quinze reais!", "tres passos, cento e quinze reais"))
        self.assertTrue(azure_openai.igual_ao_texto("pop-up de oferta", "pop up de oferta"))

    def test_parafrase_e_diferente(self):
        self.assertFalse(azure_openai.igual_ao_texto("Quanto vale o seu jogo?", "Claro! Quanto vale o seu jogo?"))
        self.assertFalse(azure_openai.igual_ao_texto("cento e quinze reais", "R$ 115"))


class SinteseGptAudio(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AZURE_OPENAI_KEY": CHAVE_FALSA, "AZURE_OPENAI_ENDPOINT": "https://meu-recurso.services.ai.azure.com/"})
        self.env.start()
        os.environ.pop("AZURE_OPENAI_API_VERSION", None)
        os.environ.pop("AZURE_OPENAI_AUDIO_DEPLOYMENT", None)
        self.addCleanup(self.env.stop)

    def test_leitura_identica_corpo_url_e_registro(self):
        pedidos = []

        def falso(req, timeout=0):
            pedidos.append(req)
            return resposta_gpt("quanto vale o seu jogo")

        with pasta_temporaria() as tmp, mock.patch("urllib.request.urlopen", falso):
            res = azure_openai.sintetizar(["Quanto vale o seu jogo?"], "marin", tmp, opcoes={"tom": "animado, de locutor de Reels"})
            self.assertTrue(Path(res["itens"][0]["arquivo"]).is_file())
        self.assertEqual(len(pedidos), 1)
        self.assertEqual(pedidos[0].full_url, "https://meu-recurso.services.ai.azure.com/openai/deployments/gpt-audio-1.5/chat/completions?api-version=2025-04-01-preview")
        self.assertEqual(pedidos[0].get_header("Api-key"), CHAVE_FALSA)
        corpo = json.loads(pedidos[0].data)
        self.assertEqual(corpo["audio"], {"voice": "marin", "format": "wav"})
        self.assertEqual(corpo["modalities"], ["text", "audio"])
        self.assertIn("animado, de locutor de Reels", corpo["messages"][0]["content"])
        self.assertIn("exatamente o texto", corpo["messages"][0]["content"])
        self.assertEqual(corpo["messages"][1], {"role": "user", "content": "Quanto vale o seu jogo?"})
        item = res["itens"][0]
        self.assertEqual(item["transcricao"], "quanto vale o seu jogo")
        self.assertEqual(item["tokens"]["total"], 200)
        self.assertEqual(item["tentativas"], 1)

    def test_divergencia_refaz_uma_vez_e_aceita_se_a_segunda_confere(self):
        respostas = iter([resposta_gpt("Claro! Quanto vale o seu jogo?"), resposta_gpt("Quanto vale o seu jogo?")])
        with pasta_temporaria() as tmp, mock.patch("urllib.request.urlopen", lambda req, timeout=0: next(respostas)):
            res = azure_openai.sintetizar(["Quanto vale o seu jogo?"], "cedar", tmp)
        self.assertEqual(res["itens"][0]["tentativas"], 2)
        self.assertIn("gpt-audio-1.5", res["modelo"])

    def test_divergencia_nas_duas_tentativas_falha_com_mensagem_clara(self):
        chamadas = []

        def parafraseia(req, timeout=0):
            chamadas.append(1)
            return resposta_gpt("Claro, o seu jogo vale bastante")

        with pasta_temporaria() as tmp, mock.patch("urllib.request.urlopen", parafraseia):
            with self.assertRaises(RuntimeError) as ctx:
                azure_openai.sintetizar(["Ok.", "Quanto vale o seu jogo?"], "marin", tmp)
            self.assertFalse(list(Path(tmp).glob("bruto-*.wav")))
        msg = str(ctx.exception)
        self.assertEqual(len(chamadas), 2)
        self.assertIn("linha 1", msg)
        self.assertIn("nunca aceito parafrase", msg)
        self.assertIn("Claro, o seu jogo vale bastante", msg)
        self.assertNotIn(CHAVE_FALSA, msg)

    def test_endpoint_so_aceita_host_azure_com_https(self):
        for ruim in ("http://aif.services.ai.azure.com", "https://evil.example.com", "https://azure.com.evil.io"):
            with mock.patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": ruim}):
                self.assertFalse(azure_openai.disponivel()[0], ruim)
        with mock.patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "https://x.openai.azure.com"}):
            self.assertTrue(azure_openai.disponivel()[0])

    def test_resposta_sem_audio_e_erro_claro(self):
        with pasta_temporaria() as tmp, mock.patch("urllib.request.urlopen", lambda req, timeout=0: Resposta(b'{"choices":[{"message":{"content":"oi"}}]}')):
            with self.assertRaises(RuntimeError) as ctx:
                azure_openai.sintetizar(["Oi."], "marin", tmp)
        self.assertIn("sem audio", str(ctx.exception))

    def test_ritmo_vira_instrucao_aproximada(self):
        self.assertIn("mais rápido", azure_openai.montar_prompt(None, 1.1))
        self.assertNotIn("Ritmo", azure_openai.montar_prompt(None, 1.0))


class VozJsonEFluxo(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AZURE_OPENAI_KEY": CHAVE_FALSA, "AZURE_OPENAI_ENDPOINT": "https://meu-recurso.services.ai.azure.com"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def rodar_voz(self, argv):
        with mock.patch.object(sys, "argv", ["voz.py", *argv]):
            voz.main()

    def test_voz_json_registra_transcricao_tokens_e_nunca_a_chave(self):
        with pasta_temporaria() as tmp:
            entrada = Path(tmp) / "voz.txt"
            entrada.write_text("# comentario\n[animado] Quanto vale o seu jogo?\nDois: leia a faixa.\n", encoding="utf-8")
            respostas = iter([resposta_gpt("quanto vale o seu jogo"), resposta_gpt("Dois, leia a faixa")])
            with mock.patch("urllib.request.urlopen", lambda req, timeout=0: next(respostas)):
                self.rodar_voz([str(entrada), "--saida", str(Path(tmp) / "out"), "--provedor", "azure_openai", "--voz", "cedar", "--tom", "calmo"])
            bruto = (Path(tmp) / "out" / "voz.json").read_text(encoding="utf-8")
            dados = json.loads(bruto)
            self.assertNotIn(CHAVE_FALSA, bruto)
            self.assertEqual(dados["provedor"], "azure_openai")
            self.assertEqual(dados["voz"], "cedar")
            self.assertEqual(dados["opcoes"], {"tom": "calmo"})
            self.assertEqual([x["transcricao"] for x in dados["linhas"]], ["quanto vale o seu jogo", "Dois, leia a faixa"])
            self.assertEqual(dados["linhas"][0]["tom"], "animado")
            self.assertEqual(dados["linhas"][1]["tom"], "calmo")
            self.assertEqual(dados["linhas"][0]["tokens"]["total"], 200)
            self.assertEqual(dados["tokens_total"], 400)
            self.assertTrue((Path(tmp) / "out" / "voz-01.wav").is_file())
            self.assertGreater(dados["linhas"][0]["duracao_s"], 0.5)

    def test_azure_estilo_por_coluna_do_roteiro_chega_ao_ssml(self):
        pedidos = []

        def falso(req, timeout=0):
            pedidos.append(req)
            return Resposta(wav_falso())

        with pasta_temporaria() as tmp, mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": CHAVE_FALSA}), mock.patch("urllib.request.urlopen", falso):
            roteiro = Path(tmp) / "roteiro.md"
            roteiro.write_text("| # | Voz | Estilo |\n| --- | --- | --- |\n| 1 | Olá & bem-vindo | excited |\n| 2 | Segundo passo | - |\n", encoding="utf-8")
            self.rodar_voz([str(roteiro), "--saida", str(Path(tmp) / "out"), "--provedor", "azure", "--voz", "pt-BR-Luana:MAI-Voice-2.1", "--estilo", "happy", "--altura", "+1st"])
            dados = json.loads((Path(tmp) / "out" / "voz.json").read_text(encoding="utf-8"))
        corpos = [ET.fromstring(p.data).find("s:voice", NS).find("m:express-as", NS) for p in pedidos]
        self.assertEqual([x.get("style") for x in corpos], ["excited", "happy"])
        self.assertEqual(corpos[0].find("s:prosody", NS).get("pitch"), "+1st")
        self.assertEqual(dados["voz"], "pt-BR-Luana:MAI-Voice-2.1")
        self.assertEqual([x["estilo"] for x in dados["linhas"]], ["excited", "happy"])

    def test_opcao_que_o_provedor_nao_tem_e_recusada(self):
        with pasta_temporaria() as tmp:
            with self.assertRaises(SystemExit):
                self.rodar_voz(["--texto", "Oi", "--saida", str(Path(tmp) / "o"), "--provedor", "azure_openai", "--altura", "+2st"])


class ComparacaoDeVozes(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": CHAVE_FALSA, "AZURE_OPENAI_KEY": CHAVE_FALSA, "AZURE_OPENAI_ENDPOINT": "https://meu-recurso.services.ai.azure.com"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def lista(self, tmp):
        caminho = Path(tmp) / "vozes.json"
        caminho.write_text(json.dumps({"titulo": "Teste", "vozes": [
            {"id": "mai", "rotulo": "Luana MAI 2.1 animada", "provedor": "azure", "voz": "pt-BR-Luana:MAI-Voice-2.1", "estilo": "excited"},
            {"id": "dragon", "rotulo": "Thalita Dragon HD", "provedor": "azure", "voz": "pt-BR-Thalita:DragonHDLatestNeural"},
            {"id": "gpt", "rotulo": "gpt-audio marin", "provedor": "azure_openai", "voz": "marin", "modelo": "gpt-audio-1.5", "tom": "animado"},
            {"id": "goog", "rotulo": "Google Kore", "provedor": "google", "voz": "pt-BR-Chirp3-HD-Kore"},
        ]}, ensure_ascii=False), encoding="utf-8")
        return caminho

    def executar(self, tmp, resposta_gpt_texto):
        def falso(req, timeout=0):
            if "tts.speech" in req.full_url:
                return Resposta(wav_falso())
            return resposta_gpt(resposta_gpt_texto)

        saida = Path(tmp) / "saida"
        args = comparar_vozes.argparse.Namespace(frase="Quanto vale o seu jogo?", entrada=None, vozes=str(self.lista(tmp)), saida=str(saida), verificar=False)
        with mock.patch.dict(os.environ, {}, clear=False), mock.patch("urllib.request.urlopen", falso):
            os.environ.pop("GOOGLE_TTS_API_KEY", None)
            comparar_vozes.principal(args)
        return saida, json.loads((saida / "manifesto.json").read_text(encoding="utf-8"))

    def test_gera_pula_sem_chave_e_monta_composicao_rotulada(self):
        with pasta_temporaria() as tmp:
            saida, m = self.executar(tmp, "quanto vale o seu jogo")
            self.assertEqual([r["rotulo"] for r in m["ordem"]], ["Luana MAI 2.1 animada", "Thalita Dragon HD", "gpt-audio marin"])
            self.assertEqual([r["ordem"] for r in m["ordem"]], [1, 2, 3])
            self.assertEqual([i["id"] for i in m["ignoradas_sem_chave"]], ["goog"])
            self.assertEqual(m["ordem"][0]["estilo"], "excited")
            self.assertIn("a confirmar", m["ordem"][0]["custo_nota"])
            self.assertIsNone(m["ordem"][0]["custo_usd_estimado"])
            self.assertIn("estimativa", m["ordem"][1]["custo_nota"])
            self.assertAlmostEqual(m["ordem"][1]["custo_usd_estimado"], 22 * len("Quanto vale o seu jogo?") / 1e6, places=7)
            self.assertEqual(m["ordem"][2]["tokens"]["total"], 200)
            self.assertIn("Azure OpenAI", m["ordem"][2]["custo_nota"])
            for r in m["ordem"]:
                self.assertTrue((saida / r["arquivo"]).is_file())
                self.assertGreater(r["duracao_s"], 0.5)
            html = (saida / "composicao" / "index.html").read_text(encoding="utf-8")
            for rotulo in ("1. Luana MAI 2.1 animada", "2. Thalita Dragon HD", "3. gpt-audio marin"):
                self.assertIn(rotulo, html)
            self.assertEqual(html.count("<audio "), 3)
            self.assertNotIn(CHAVE_FALSA, (saida / "manifesto.json").read_text(encoding="utf-8"))
            self.assertTrue((saida / "lista.json").is_file())

    def test_entrada_que_falha_nao_derruba_as_outras(self):
        with pasta_temporaria() as tmp:
            saida, m = self.executar(tmp, "o jogo vale bastante")
            self.assertEqual([r["id"] for r in m["ordem"]], ["mai", "dragon"])
            self.assertEqual([f["id"] for f in m["falharam"]], ["gpt"])
            self.assertIn("nunca aceito parafrase", m["falharam"][0]["motivo"])
            html = (saida / "composicao" / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("gpt-audio marin", html)

    def test_so_kokoro_sem_chaves_ou_mock_de_provedor(self):
        class Falso:
            NOME = "kokoro"
            LOCAL = True
            VOZES = []

            @staticmethod
            def disponivel(variante=None):
                return True, "falso"

            @staticmethod
            def sintetizar(linhas, voz_id, pasta, velocidade=1.0, variante=None):
                destino = Path(pasta) / "bruto-01.wav"
                destino.write_bytes(wav_falso())
                return {"modelo": "falso", "carga_s": 0.0, "itens": [{"arquivo": str(destino), "sintese_s": 0.01, "audio_s": None}]}

        with pasta_temporaria() as tmp:
            caminho = Path(tmp) / "k.json"
            caminho.write_text(json.dumps({"vozes": [{"id": "k", "rotulo": "Falso", "provedor": "kokoro", "voz": "pf_dora"}]}), encoding="utf-8")
            args = comparar_vozes.argparse.Namespace(frase="Oi.", entrada=None, vozes=str(caminho), saida=str(Path(tmp) / "s"), verificar=False)
            with mock.patch.object(provedores, "tentar_carregar", lambda nome: (Falso, None)):
                comparar_vozes.principal(args)
            m = json.loads((Path(tmp) / "s" / "manifesto.json").read_text(encoding="utf-8"))
        self.assertEqual(m["ordem"][0]["custo_nota"], "zero (roda na maquina)")




class TesteSemRedirecionamento(unittest.TestCase):
    def test_chave_nao_segue_redirecionamento_ponta_a_ponta(self):
        import http.server
        import threading
        import urllib.error
        import urllib.request
        from provedores import azure  # noqa: F401  (instala o opener sem redirecionamento)
        recebidos = []

        class Alvo(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                recebidos.append(self.headers.get("Ocp-Apim-Subscription-Key"))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        alvo = http.server.HTTPServer(("127.0.0.1", 0), Alvo)
        porta_alvo = alvo.server_address[1]

        class Redireciona(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{porta_alvo}/roubo")
                self.end_headers()

            def log_message(self, *a):
                pass

        origem = http.server.HTTPServer(("127.0.0.1", 0), Redireciona)
        for s in (alvo, origem):
            threading.Thread(target=s.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{origem.server_address[1]}/tts", headers={"Ocp-Apim-Subscription-Key": "chave-falsa"})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(ctx.exception.code, 302)
            self.assertEqual(recebidos, [], "o destino do redirecionamento nao pode receber a chave")
        finally:
            for s in (origem, alvo):
                s.shutdown()
                s.server_close()


def ambiente_de_voz(**variaveis):
    base = {k: v for k, v in os.environ.items() if not k.startswith("VOZ_")}
    base.update(variaveis)
    return mock.patch.dict(os.environ, base, clear=True)


def pedido(**campos):
    return types.SimpleNamespace(**{"provedor": None, "voz": None, "velocidade": None, "modelo": None, **campos})


class VozDaCasaPeloEnv(unittest.TestCase):
    def setUp(self):
        self.json = json.loads(voz.CONFIG.read_text(encoding="utf-8"))

    def test_sem_env_vale_o_voz_config(self):
        with ambiente_de_voz():
            cfg = voz.config()
            nome, _, escolhida, _ = voz.escolher(pedido(), cfg)
        self.assertEqual(nome, self.json["provedor"])
        self.assertEqual(escolhida, self.json["vozes_padrao"][nome])
        self.assertEqual((cfg["origem"]["provedor"], cfg["origem"][nome]), ("voz_config.json", "voz_config.json"))

    def test_env_troca_provedor_e_voz(self):
        with ambiente_de_voz(VOZ_PROVEDOR="azure", VOZ_AZURE="pt-BR-Macerio:DragonHDLatestNeural"):
            cfg = voz.config()
            nome, _, escolhida, _ = voz.escolher(pedido(), cfg)
        self.assertEqual((nome, escolhida), ("azure", "pt-BR-Macerio:DragonHDLatestNeural"))
        self.assertEqual((cfg["origem"]["provedor"], cfg["origem"]["azure"]), (".env", ".env"))

    def test_linha_de_comando_continua_mandando(self):
        with ambiente_de_voz(VOZ_PROVEDOR="azure_openai", VOZ_AZURE="pt-BR-Macerio:DragonHDLatestNeural"):
            nome, _, escolhida, _ = voz.escolher(pedido(provedor="azure", voz="pt-BR-Luana:MAI-Voice-2.1"), voz.config())
        self.assertEqual((nome, escolhida), ("azure", "pt-BR-Luana:MAI-Voice-2.1"))

    def test_voz_de_um_provedor_nao_vaza_para_outro(self):
        with ambiente_de_voz(VOZ_AZURE="pt-BR-Macerio:DragonHDLatestNeural"):
            _, _, escolhida, _ = voz.escolher(pedido(provedor="azure_openai"), voz.config())
        self.assertEqual(escolhida, self.json["vozes_padrao"]["azure_openai"])

    def test_provedor_errado_no_env_para_com_mensagem(self):
        with ambiente_de_voz(VOZ_PROVEDOR="azur"), mock.patch("sys.stderr", io.StringIO()) as erro, mock.patch("sys.stdout", io.StringIO()) as saida:
            with self.assertRaises(SystemExit):
                voz.escolher(pedido(), voz.config())
        self.assertIn("VOZ_PROVEDOR", erro.getvalue() + saida.getvalue())

    def test_linhas_de_voz_saem_do_arquivo_env(self):
        with pasta_temporaria() as tmp, ambiente_de_voz():
            arquivo = Path(tmp) / ".env"
            arquivo.write_text('AZURE_SPEECH_KEY=<chave>\nVOZ_PROVEDOR=azure\nVOZ_AZURE="pt-BR-Thalita:DragonHDLatestNeural"\n', encoding="utf-8")
            with mock.patch.object(c, "ENV_VOZ", arquivo):
                carregadas = c.carregar_env_voz()
            cfg = voz.config()
        self.assertEqual(sorted(carregadas), ["VOZ_AZURE", "VOZ_PROVEDOR"])
        self.assertEqual(cfg["vozes_padrao"]["azure"], "pt-BR-Thalita:DragonHDLatestNeural")


if __name__ == "__main__":
    unittest.main(verbosity=2)
