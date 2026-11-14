import html
import json
import math

import reel_tempos as rt

LARGURA = 1080
ALTURA = 1920
SEGURA = {"topo": 0.115, "base": 0.22, "esquerda": 0.055, "direita": 0.13}
TEXTO_X = 60
TEXTO_L = 880
TITULO_L = 800
TOPO_TITULO = 250
TELA_L = 720
TELA_A = 1448
TELA_X = 180
FONE_TOPO = 580
MIRA_Y = 900
FOLGA_DE_ROLAGEM = 700
HUD_TOPO = 236
LEGENDA_TOPO = 1270
CHIP_Y = 1215
RESPIRO_DO_CARTAO = 40
CARTAO_L_MAX = 800
VIDEOS = (".mp4", ".webm", ".mov", ".m4v")
FORMATOS = {"retrato": (520, 680), "quadrado": (640, 640), "paisagem": (820, 540)}
DESVIOS = [(-46, -3.0), (40, 2.5), (-24, -1.5), (34, 3.0), (-12, -2.0), (22, 1.5)]
TIPOS = ("abertura", "aparelho", "galeria", "comparacao", "passos", "impacto", "fecho")
ACENTOS_FRACOS_NO_PIXEL = "ÓÚÍóúí"

FONTES = {
    "Press Start 2P": ['@font-face{font-family:"Press Start 2P";src:url("_motor/fonts/press-start-2p-400.woff2") format("woff2");font-weight:400;font-style:normal}',
                       '@font-face{font-family:"Press Start 2P";src:url("_motor/fonts/press-start-2p-ext-400.woff2") format("woff2");font-weight:400;font-style:normal;unicode-range:U+0100-024F}'],
    "Inter": ['@font-face{font-family:"Inter";src:url("_motor/fonts/inter-%d.woff2") format("woff2");font-weight:%d;font-style:normal}' % (w, w) for w in (600, 800, 900)],
    "Montserrat": ['@font-face{font-family:"Montserrat";src:url("_motor/fonts/montserrat-%d.woff2") format("woff2");font-weight:%d;font-style:normal}' % (w, w) for w in (600, 800)],
}

ESTILOS = {
    "pixel": {
        "titulo_px": 62, "titulo_altura": 1.5, "titulo_largura": 1.0, "impacto_px": 66, "impacto_altura": 1.52, "aparelho_borda": 6, "aparelho_barra": 40,
        "css": """
  .tt{font-family:var(--f-titulo),monospace;font-weight:400;text-transform:uppercase}
  .tit,.imp{color:#fff;text-shadow:6px 6px 0 var(--sombra)}
  .cx{background:var(--tinta);border:5px solid var(--claro);box-shadow:12px 12px 0 var(--acento)}
  .cartao{border:6px solid var(--claro);box-shadow:16px 16px 0 var(--acento2);background:var(--tinta)}
  .fone{border:6px solid var(--claro);background:var(--tinta);box-shadow:16px 16px 0 var(--acento2)}
  .fone .barra{position:absolute;left:0;right:0;top:0;height:40px;background:var(--claro)}
  .fone .barra i{position:absolute;top:12px;width:16px;height:16px;background:var(--tinta)}
  .chip{font-family:var(--f-titulo),monospace;font-size:24px;line-height:58px;height:66px;padding:0 20px;background:var(--tinta);border:4px solid var(--claro);color:var(--claro);box-shadow:8px 8px 0 var(--sombra)}
  .chip.a{background:var(--acento);border-color:var(--acento);color:var(--tinta)}
  .pilula{font-family:var(--f-titulo),monospace;font-size:26px;line-height:60px;height:60px;background:var(--acento);color:var(--tinta);box-shadow:8px 8px 0 var(--sombra)}
  .foco{border:8px solid var(--acento);box-shadow:0 0 0 6px rgba(0,0,0,.4),0 0 38px var(--acento-luz)}
""",
    },
    "suave": {
        "titulo_px": 70, "titulo_altura": 1.06, "titulo_largura": 0.6, "impacto_px": 104, "impacto_altura": 1.06, "aparelho_borda": 4, "aparelho_barra": 0,
        "css": """
  .tt{font-family:var(--f-titulo),sans-serif;font-weight:900;letter-spacing:-.04em}
  .tit,.imp{color:#fff;text-shadow:0 4px 24px rgba(0,0,0,.5)}
  .cx{background:rgba(18,19,26,.92);border:2px solid var(--acento-luz);border-radius:30px}
  .cartao{border:8px solid #fff;border-radius:30px;box-shadow:0 26px 60px rgba(0,0,0,.35);background:#111}
  .fone{border:4px solid rgba(255,255,255,.16);border-radius:30px;background:var(--tinta);box-shadow:0 30px 80px rgba(0,0,0,.45)}
  .fone .tela{border-radius:26px}
  .chip{font-size:24px;font-weight:900;letter-spacing:.08em;line-height:54px;height:54px;padding:0 16px;border-radius:14px;background:rgba(18,19,26,.92);border:2px solid var(--acento-luz);color:#fff}
  .chip.a{background:var(--acento);border-color:var(--acento);color:var(--tinta)}
  .pilula{font-size:34px;font-weight:900;letter-spacing:-.01em;line-height:60px;height:60px;border-radius:30px;background:var(--acento);color:var(--tinta)}
  .foco{border:6px solid var(--acento);border-radius:22px;box-shadow:0 0 28px var(--acento-luz)}
""",
    },
}

CSS_BASE = """
  body{margin:0;background:var(--tinta);color:var(--claro);font-family:var(--f-texto),sans-serif}
  #root{position:relative;width:100%;height:100%;overflow:hidden;background:var(--tinta)}
  .clip{position:absolute;inset:0}
  #fundo{position:absolute;inset:0;background:radial-gradient(ellipse 900px 1300px at 50% 45%,var(--fundo1) 0%,var(--fundo2) 60%,var(--fundo3) 100%)}
  #fundo-m{position:absolute;left:-80px;top:-80px;width:1240px;height:2080px;background-size:cover;background-position:50% 50%;filter:blur(40px) brightness(.4)}
  .textura{position:absolute;left:-60px;top:0;width:1200px;height:2300px;opacity:.16}
  .halo{position:absolute;width:900px;height:900px;border-radius:50%}
  #h1{left:-320px;top:980px;background:radial-gradient(circle,var(--halo1) 0%,rgba(0,0,0,0) 68%)}
  #h2{left:520px;top:120px;background:radial-gradient(circle,var(--halo2) 0%,rgba(0,0,0,0) 68%)}
  #leg-fundo{position:absolute;left:0;top:1270px;width:1080px;height:300px;background:linear-gradient(rgba(0,0,0,0) 0%,var(--faixa) 34%,var(--faixa) 66%,rgba(0,0,0,0) 100%)}
  .tit{position:absolute;left:140px;width:800px;text-align:center}
  .tit span.ln,.imp span.ln{display:inline-block}
  .tit em,.imp em{font-style:normal;color:var(--acento)}
  .apo{position:absolute;left:140px;width:800px;text-align:center;font-size:46px;font-weight:800;line-height:1.3;color:#fff}
  .apo em{font-style:normal;color:var(--acento);background:linear-gradient(var(--acento),var(--acento)) no-repeat 0 100%;background-size:0% 8px;padding-bottom:10px}
  .imp{position:absolute;left:140px;width:800px;text-align:center;line-height:1}
  .ab-m{position:absolute;left:0;top:0;width:1080px;height:1920px;background-size:cover;background-position:50% 50%}
  .ab-veu{position:absolute;left:0;top:0;width:1080px;height:900px;background:linear-gradient(180deg,rgba(8,9,12,.9) 0%,rgba(8,9,12,.55) 60%,rgba(8,9,12,0) 100%)}
  .cam{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0}
  .fone{position:absolute;box-sizing:border-box;overflow:hidden}
  .tela{position:absolute;left:0;width:720px;height:1448px;overflow:hidden;background:var(--tinta)}
  .pg{position:absolute;left:0;top:0;width:720px;height:1448px;overflow:hidden;background:var(--tinta)}
  .rol{position:absolute;left:0;top:0;transform-origin:0 0}
  .rol img{display:block}
  .foco{position:absolute;left:0;top:0;box-sizing:border-box}
  .mk{position:absolute;background:var(--acento-marca);border-bottom:7px solid var(--acento)}
  .mk.b{background:var(--acento2-marca);border-bottom-color:var(--acento2)}
  .veu{position:absolute;left:0;top:1120px;width:1080px;height:800px;background:linear-gradient(rgba(0,0,0,0) 0%,var(--faixa-forte) 28%,var(--faixa-forte) 100%)}
  .chip{position:absolute;box-sizing:border-box;white-space:nowrap}
  .pilula{position:absolute;box-sizing:border-box;text-align:center;white-space:nowrap}
  .cartao{position:absolute;box-sizing:border-box;overflow:hidden}
  .cartao .im{position:absolute;left:0;top:0;width:100%;height:100%;background-size:cover;background-position:50% 50%}
  .cartao video{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover}
  .cartao .rv{position:absolute;left:0;top:0;width:100%;height:100%;overflow:hidden}
  .cartao .dv{position:absolute;left:-4px;top:0;width:8px;height:100%;background:var(--acento)}
  .cartao .gr{position:absolute;left:0;top:0;width:60%;height:100%;background:linear-gradient(90deg,rgba(255,255,255,0) 0%,rgba(255,255,255,.14) 50%,rgba(255,255,255,0) 100%)}
  .cx{position:absolute;box-sizing:border-box}
  .pedido{left:60px;width:880px;padding:26px 30px 30px}
  .pedido .lb{font-size:22px;font-weight:900;letter-spacing:.12em;color:var(--acento);margin-bottom:12px}
  .pedido .tx{font-size:44px;font-weight:800;letter-spacing:-.02em;line-height:1.16;color:#fff}
  .cur{display:inline-block;width:6px;height:34px;margin-left:4px;background:var(--acento);vertical-align:-5px}
  #hud{left:60px;width:880px}
  #hud .topo{position:absolute;left:0;right:0;top:0;height:54px;background:var(--acento);color:var(--tinta);font-size:28px;font-weight:900;letter-spacing:.06em;line-height:54px;padding-left:25px}
  #cnt{position:absolute;right:22px;top:0;font-size:20px;line-height:54px;color:var(--tinta)}
  .campo{position:absolute;left:0;right:0;height:84px;border-bottom:2px solid var(--linha)}
  .campo:last-child{border-bottom:0}
  .rot{position:absolute;left:25px;top:13px;font-size:20px;color:var(--apagado);white-space:nowrap}
  .val{position:absolute;left:25px;top:38px;font-size:34px;font-weight:900;color:#fff;white-space:nowrap;line-height:40px}
  .ok{position:absolute;right:22px;top:26px;padding:9px 10px 7px;background:var(--acento2);color:var(--tinta);font-size:14px}
  .selo{position:absolute;left:90px;top:760px;transform-origin:0 0}
  .selo .in{box-sizing:border-box;padding:24px 30px 26px}
  .selo .n{font-size:28px;color:var(--acento);line-height:28px;margin-bottom:14px}
  .selo .t{font-size:44px;color:#fff;line-height:52px;white-space:nowrap}
  #f-card{left:230px;width:620px}
  #f-card .topo{height:50px;background:var(--acento);color:var(--tinta);font-size:24px;font-weight:900;letter-spacing:.06em;line-height:50px;padding-left:20px}
  #f-card .li{position:relative;height:72px;border-bottom:2px solid var(--linha);font-size:30px;font-weight:900;line-height:72px;padding-left:20px;color:#fff;white-space:nowrap}
  #f-card .li:last-child{border-bottom:0}
  #f-card .li b{position:absolute;right:16px;top:20px;padding:8px 9px 6px;background:var(--acento2);color:var(--tinta);font-size:13px;line-height:1;font-weight:400}
  #f-glow{position:absolute;left:190px;width:700px;height:380px;border-radius:50%;background:radial-gradient(ellipse,var(--acento-luz) 0%,rgba(0,0,0,0) 70%)}
  #f-logo{position:absolute;left:280px;width:520px;height:176px;object-fit:contain}
  .brilhos{position:absolute;left:0;width:1080px;height:531px}
  .fx{position:absolute;left:-310px;top:-100px;width:1700px;height:2120px;transform-origin:50% 50%}
"""

JS_BASE = """  gsap.registerPlugin(TextPlugin);
  const tl = gsap.timeline({ paused: true });
  const K = MotionKit.criar(tl);
  const E = K.EASE;
  const rola = (sel, escala, de, para, t, d, ease) =>
    tl.fromTo(sel, { y: -de * escala }, { y: -para * escala, duration: d, ease: ease || E.rolagem, immediateRender: false }, t);
  const pisca = (sel, de, ate) =>
    tl.fromTo(sel, { opacity: 1 }, { opacity: 0, duration: 0.25, ease: "steps(1)", yoyo: true, repeat: Math.max(1, Math.floor((ate - de) / 0.25)), immediateRender: false }, de);
  const selo = (n, linha, tEntra, tVira, tDigita) => {
    K.bate("#st" + n + " .in", tEntra, { de: 1.35, d: 0.34 });
    tl.set("#st" + n, { opacity: 1 }, tEntra);
    tl.to("#st" + n, { x: 44, y: linha - 20 - 760, scale: 0.4545, duration: 0.45, ease: E.troca }, tVira);
    tl.to("#st" + n, { opacity: 0, duration: 0.12 }, tVira + 0.36);
    tl.to("#l" + n, { color: ACENTO, duration: 0.15 }, tVira + 0.36);
    if (tDigita - 0.05 > tVira + 0.45) pisca("#k" + n, tVira + 0.45, tDigita - 0.05);
  };
  const confirma = (n, total, t) => {
    K.bate("#o" + n, t, { de: 1.8, d: 0.3 });
    tl.to("#l" + n, { color: ACENTO2, duration: 0.2 }, t);
    tl.set("#cnt", { text: n + "/" + total }, t);
    tl.fromTo("#cnt", { scale: 1.5 }, { scale: 1, duration: 0.3, ease: E.snap, immediateRender: false }, t);
  };
"""


class ErroDeCena(rt.ErroDeRoteiro):
    pass


def esc(texto):
    return html.escape(str(texto), quote=True)


def marcar(texto):
    partes = esc(texto).split("*")
    return "".join(f"<em>{p}</em>" if i % 2 else p for i, p in enumerate(partes))


def liso(texto):
    return str(texto).replace("*", "")


def num(x, casas=3):
    return ("%.*f" % (casas, float(x))).rstrip("0").rstrip(".") or "0"


def obj(**campos):
    partes = []
    for chave, valor in campos.items():
        if valor is None:
            continue
        partes.append(f"{chave}: {num(valor) if isinstance(valor, (int, float)) and not isinstance(valor, bool) else json.dumps(valor, ensure_ascii=False)}")
    return "{ " + ", ".join(partes) + " }"


def txt(valor):
    return json.dumps(valor, ensure_ascii=False)


def rgba(hexa, alfa):
    h = hexa.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alfa})"


def escuro(hexa):
    h = hexa.lstrip("#")
    return (int(h[0:2], 16) * 299 + int(h[2:4], 16) * 587 + int(h[4:6], 16) * 114) / 1000 < 90


def estilo_da_marca(tokens):
    m = tokens.get("motion", {})
    cores = tokens.get("cores", {})
    nome = m.get("estilo", "suave")
    if nome not in ESTILOS:
        raise ErroDeCena(f"tokens.json: motion.estilo '{nome}' nao existe (use {', '.join(ESTILOS)})")
    fundo_marca = next((cores[k] for k in ("bg", "bgDark", "surfaceDark") if cores.get(k) and escuro(cores[k])), "#14151C")
    acento = m.get("acento") or cores.get("highlight") or cores.get("secondary") or cores.get("primary") or "#FFFFFF"
    acento2 = m.get("acento2") or cores.get("secondary") or cores.get("primary") or acento
    e = dict(ESTILOS[nome])
    e.update({
        "nome": nome, "acento": acento, "acento2": acento2, "claro": m.get("claro") or cores.get("text") or "#FFFFFF",
        "tinta": m.get("tinta") or fundo_marca, "fundo": m.get("fundo") or [fundo_marca, fundo_marca, "#0B0B10"],
        "sombra": m.get("sombra_texto") or "#0B0B14", "apagado": m.get("apagado") or "#9A9AAE", "linha": m.get("linha") or "rgba(255,255,255,.14)",
        "cortina": m.get("cortina") or [acento, acento2, cores.get("primary") or acento],
        "fonte_titulo": m.get("fonte_titulo") or "Inter", "fonte_texto": m.get("fonte_texto") or "Inter", "musica": m.get("musica"),
    })
    for familia in (e["fonte_titulo"], e["fonte_texto"]):
        if familia not in FONTES:
            raise ErroDeCena(f"tokens.json: a fonte '{familia}' nao esta em content-engine/fonts (use {', '.join(FONTES)})")
    return e


def css_da_marca(e):
    familias = []
    for familia in (e["fonte_titulo"], e["fonte_texto"], "Inter"):
        if familia not in familias:
            familias.append(familia)
    faces = "\n".join("  " + linha for f in familias for linha in FONTES[f])
    variaveis = {
        "--acento": e["acento"], "--acento2": e["acento2"], "--claro": e["claro"], "--tinta": e["tinta"], "--sombra": e["sombra"], "--apagado": e["apagado"],
        "--linha": e["linha"], "--fundo1": e["fundo"][0], "--fundo2": e["fundo"][1], "--fundo3": e["fundo"][2],
        "--halo1": rgba(e["cortina"][-1], 0.34), "--halo2": rgba(e["acento2"], 0.2), "--faixa": rgba(e["fundo"][2], 0.86), "--faixa-forte": rgba(e["fundo"][2], 0.94),
        "--acento-luz": rgba(e["acento"], 0.5), "--acento-marca": rgba(e["acento"], 0.34), "--acento2-marca": rgba(e["acento2"], 0.3),
        "--f-titulo": f'"{e["fonte_titulo"]}"', "--f-texto": f'"{e["fonte_texto"]}"',
    }
    raiz = "  :root{" + ";".join(f"{k}:{v}" for k, v in variaveis.items()) + "}"
    return faces + "\n" + raiz + CSS_BASE + e["css"]


class Peca:
    def __init__(self, e, total, ancoras, medir, com_voz=True):
        self.e = e
        self.total = total
        self.ancoras = ancoras
        self.medir = medir
        self.com_voz = com_voz
        self.css = []
        self.secoes = []
        self.soltos = []
        self.preparo = []
        self.js = []
        self.deixas = []
        self.caixas = []
        self.avisos = []
        self.quiques = 0
        self.cameras = 0
        self.trocas = 0
        self.titulos = 0

    def a(self, linha):
        self.js.append("  " + linha)

    def p(self, linha):
        self.preparo.append("  " + linha)

    def som(self, movimento, instante, duracao=None):
        self.deixas.append(rt.deixa(movimento, instante, self.ancoras, self.com_voz, duracao))

    def texto(self, nome, x, y, w, h, de, ate):
        self.caixas.append({"nome": nome, "x": round(x), "y": round(y), "w": round(w), "h": round(h), "de": round(de, 3), "ate": round(ate, 3)})

    def secao(self, id_, ini, fim, z, corpo, trilha):
        self.css.append(f"  #{id_}{{z-index:{z} !important}}")
        self.secoes.append(f'  <section id="{id_}" class="clip" data-start="{num(ini)}" data-duration="{num(fim - ini)}" data-track-index="{trilha}">\n{corpo}\n  </section>')

    def aviso(self, texto):
        self.avisos.append(texto)

    def cor(self, nome):
        return self.e["acento2"] if nome in ("acento2", "segunda") else self.e["acento"]


def quando(p, b, ref, padrao="@inicio", texto=False):
    t = rt.momento(b["palavras"], ref if ref is not None else padrao)
    if texto:
        t = rt.segurar_texto(t, b["primeira"])
    if t > b["fim"] - 0.15:
        p.aviso(f"batida {b['i']}: o momento em {t:.2f} s cai no fim da batida ({b['fim']:.2f} s); o movimento pode ser cortado")
    return t


def largura_do_texto(e, texto, px, titulo=True):
    fator = e["titulo_largura"] if titulo else 0.56
    return len(liso(texto)) * px * fator


def linhas_de(texto):
    return [x.strip() for x in str(texto).split("|") if x.strip()]


def conferir_pixel(p, onde, texto):
    if p.e["nome"] == "pixel" and any(ch in ACENTOS_FRACOS_NO_PIXEL for ch in texto):
        p.aviso(f"{onde}: a fonte pixel nao tem Ó, Ú e Í maiusculos; reescreva \"{liso(texto)}\" sem essas letras")


def titulo(p, b, corpo, topo=TOPO_TITULO):
    cena = b["cena"]
    if not cena.get("titulo") and not cena.get("apoio"):
        return topo
    e = p.e
    y = topo
    saem = []
    if cena.get("titulo"):
        linhas = linhas_de(cena["titulo"])
        conferir_pixel(p, f"batida {b['i']}, titulo", cena["titulo"])
        maior = max(len(liso(x)) for x in linhas)
        px = min(e["titulo_px"], math.floor(TITULO_L / (maior * e["titulo_largura"])))
        alto = round(px * e["titulo_altura"] * len(linhas))
        id_ = f"b{b['i']}-tit"
        corpo.append(f'    <div class="tit tt" id="{id_}" style="top:{y}px;font-size:{px}px;line-height:{e["titulo_altura"]}">'
                     + "<br>".join(f'<span class="ln">{marcar(x)}</span>' for x in linhas) + "</div>")
        t = quando(p, b, cena.get("titulo_na"), "@inicio", texto=True)
        p.a(f'K.bate("#{id_} .ln", {num(t)}, {obj(de=1.7, d=0.4, stagger=0.14)});')
        p.som("titulo" if not p.titulos else "selo", t)
        p.titulos += 1
        w = max(largura_do_texto(e, x, px) for x in linhas)
        p.texto(id_, 540 - w / 2, y, w, alto, t, b["fim"])
        saem.append(f"#{id_}")
        y += alto + 34
        b["t_titulo"] = t
    if cena.get("apoio"):
        id_ = f"b{b['i']}-apo"
        corpo.append(f'    <div class="apo" id="{id_}" style="top:{y}px">{marcar(cena["apoio"])}</div>')
        padrao = {"na": "@inicio", "ajuste": 0.45}
        t = quando(p, b, cena.get("apoio_na"), padrao, texto=True)
        if "t_titulo" in b:
            t = max(t, b["t_titulo"] + 0.3)
        p.a(f'K.sobe(K.palavras("#{id_}"), {num(t)}, {obj(stagger=0.08, y=30, d=0.34)});')
        if "*" in cena["apoio"]:
            p.a(f'tl.to("#{id_} em", {{ backgroundSize: "100% 8px", duration: 0.3, stagger: 0.12, ease: E.casa }}, {num(t + 0.36)});')
        p.som("apoio", t)
        w = min(TITULO_L, largura_do_texto(e, cena["apoio"], 46, titulo=False))
        linhas_apoio = max(1, math.ceil(largura_do_texto(e, cena["apoio"], 46, titulo=False) / TITULO_L))
        p.texto(id_, 540 - w / 2, y, w, 60 * linhas_apoio, t, b["fim"])
        saem.append(f"#{id_}")
        y += 60 * linhas_apoio + 30
    if not b.get("ultima"):
        p.a(f'K.sai({txt(saem)}, {num(b["fim"] - 0.41)}, {obj(stagger=0.05)});')
    return y


def fundo(p, roteiro):
    cfg = roteiro.get("fundo") or {}
    corpo = ['    <div id="fundo"></div>']
    if cfg.get("midia"):
        corpo.append(f'    <div id="fundo-m" style="background-image:url(\'{esc(cfg["midia"])}\')"></div>')
        p.a(f'tl.fromTo("#fundo-m", {{ scale: 1 }}, {{ scale: 1.08, duration: {num(p.total)}, ease: "none" }}, 0);')
    corpo += ['    <div class="halo" id="h1"></div>', '    <div class="halo" id="h2"></div>']
    if cfg.get("textura"):
        corpo.append(f'    <img class="textura" id="tx" src="{esc(cfg["textura"])}" alt="">')
        p.a(f'tl.fromTo("#tx", {{ y: 0 }}, {{ y: -380, duration: {num(p.total)}, ease: "none" }}, 0);')
    p.a(f'K.respira("#h1", 0, {num(p.total)}, {obj(x=70, y=50, periodo=4.7)});')
    p.a(f'K.respira("#h2", 0, {num(p.total)}, {obj(x=50, y=70, periodo=5.6)});')
    p.secao("s-fundo", 0, p.total, 0, "\n".join(corpo), 0)


def legenda(p, ate_faixa):
    p.secao("s-legenda", 0, p.total, 8, '    <div id="leg-fundo"></div>\n    <div id="legenda"></div>', 5)
    p.a('tl.fromTo("#leg-fundo", { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: true }, 0.1);')
    if ate_faixa < p.total:
        p.a(f'tl.to("#leg-fundo", {{ opacity: 0, duration: 0.3 }}, {num(ate_faixa)});')
    p.a(f'K.legenda("#legenda", window.__legenda, {obj(ativa=p.e["acento"], acento=p.e["acento2"])});')


def cortina(p, corte):
    faixas = "\n".join(f'    <div class="fx" id="fx{i + 1}" style="background:{cor}"></div>' for i, cor in enumerate(p.e["cortina"][:3]))
    p.secao("s-cortina", max(0, corte - 0.7), min(p.total, corte + 0.9), 9, faixas, 4)
    p.p('gsap.set(".fx", { skewX: -12 });')
    p.a(f'K.cortina(".fx", {num(corte - 0.54)}, {obj(d=0.4, passo=0.07)});')
    p.som("virada", corte)


def painel(p, cfg, de, ate):
    itens = cfg["itens"]
    alto = 54 + 84 * len(itens) + 10
    campos = []
    for i, item in enumerate(itens, 1):
        conferir_pixel(p, f"painel, item {i}", item)
        campos.append(f'      <div class="campo" id="c{i}" style="top:{54 + 84 * (i - 1)}px"><div class="rot tt" id="l{i}">{i:02d} {esc(item)}</div>'
                      f'<div class="val"><span id="v{i}"></span><i class="cur" id="k{i}"></i></div><div class="ok tt" id="o{i}">OK</div></div>')
    corpo = (f'    <div class="cx" id="hud" style="top:{HUD_TOPO}px;height:{alto}px">\n      <div class="topo">{esc(cfg.get("titulo", "RESUMO"))}'
             f'<span class="tt" id="cnt">0/{len(itens)}</span></div>\n' + "\n".join(campos) + "\n    </div>")
    p.secao("s-painel", 0, ate, 6, corpo, 3)
    p.p('gsap.set(["#hud .cur", "#hud .ok"], { opacity: 0 });')
    p.p('gsap.set("#hud", { y: -640 });')
    p.a(f'tl.to("#hud", {{ y: 0, duration: 0.55, ease: E.snap }}, {num(max(0, de - 0.21))});')
    p.texto("painel", TEXTO_X, HUD_TOPO, TEXTO_L, alto, de, ate)
    return alto


def _caixa(alvo, onde):
    try:
        return {k: float(alvo[k]) for k in ("x", "y", "w", "h")}
    except (KeyError, TypeError, ValueError):
        raise ErroDeCena(f"{onde}: 'alvo' precisa de x, y, w e h (use python content-engine/video/apontar.py <print> para tirar do print)") from None


def grupo_aparelho(p, grupo, ctx):
    e = p.e
    borda, barra = e["aparelho_borda"], e["aparelho_barra"]
    tela_y = FONE_TOPO + borda + barra
    gid = f"g{grupo[0]['i']}"
    cam, fone = f"#{gid}-cam", f"#{gid}-fone"
    ini, fim = grupo[0]["ini"], grupo[-1]["fim"]
    paginas, fora, selos, chips_html = [], [], [], []
    pagina = None
    rol = 0.0
    camera = False
    tem_painel = ctx.get("painel") is not None

    def tela_de(cy):
        return tela_y + (cy - rol) * pagina["escala"]

    def visivel(b, alvo, faz):
        y = tela_de(alvo["y"] + alvo["h"] / 2)
        if not tela_y + 40 <= y <= tela_y + TELA_A - 40:
            p.aviso(f"batida {b['i']}: o alvo do '{faz}' (y {alvo['y']:.0f}) esta fora da tela com a rolagem em {rol:.0f}; ajuste 'rolagem' ou ponha um 'rola' antes")

    for b in grupo:
        cena = b["cena"]
        arquivo = cena.get("print")
        if not arquivo:
            raise ErroDeCena(f"batida {b['i']}: a cena 'aparelho' precisa de 'print' (arquivo dentro da pasta da peca)")
        w, h = p.medir(arquivo)
        larg = float(cena.get("largura_do_print") or w)
        nova = pagina is None or pagina["arquivo"] != arquivo
        if nova:
            anterior = pagina
            n = len(paginas) + 1
            pagina = {"arquivo": arquivo, "larg": larg, "escala": TELA_L / larg, "alt": h * larg / w, "id": f"{gid}-p{n}", "rol": f"#{gid}-r{n}", "foco": f"#{gid}-f{n}", "marcas": [], "foco_visivel": False}
            paginas.append(pagina)
        maximo = max(0.0, pagina["alt"] - FOLGA_DE_ROLAGEM / pagina["escala"])
        destino = min(maximo, float(cena.get("rolagem", 0 if nova else rol)))
        if nova:
            rol = destino
            p.p(f'gsap.set("{pagina["rol"]}", {{ scale: {num(pagina["escala"], 5)}, y: {num(-rol * pagina["escala"])} }});')
            if anterior:
                p.p(f'gsap.set("#{pagina["id"]}", {{ x: {TELA_L} }});')
                p.a(f'K.empurra("#{anterior["id"]}", "#{pagina["id"]}", {num(b["ini"])});')
                p.som("troca_leve" if p.trocas % 2 else "troca", b["ini"])
                p.trocas += 1
        elif abs(destino - rol) > 1:
            d = 1.1 if abs(destino - rol) > 600 else 0.6
            p.a(f'rola("{pagina["rol"]}", {num(pagina["escala"], 5)}, {num(rol)}, {num(destino)}, {num(b["ini"] - 0.06)}, {num(d)});')
            p.som("rola_longa" if d > 1 else "rola", b["ini"] - 0.06 + d / 2)
            rol = destino
        if b is grupo[0]:
            if cena.get("abre_em"):
                alvo = _caixa(cena["abre_em"], f"batida {b['i']}, abre_em")
                s = float(cena["abre_em"].get("zoom") or min(2.2, 1000 / (alvo["w"] * pagina["escala"])))
                fy = tela_de(alvo["y"] + alvo["h"] / 2)
                p.p(f'gsap.set("{cam}", {obj(x=540 - 540 * s, y=860 - fy * s, scale=s)});')
                camera = True
                b["abre"] = True
                if maximo - rol > 160 and not any(m.get("faz") == "rola" for m in cena.get("momentos", [])):
                    p.a(f'rola("{pagina["rol"]}", {num(pagina["escala"], 5)}, {num(rol)}, {num(rol + 150)}, {num(b["ini"] + 0.2)}, {num(b["fim"] - b["ini"] - 0.4)}, E.respira);')
                    b["deriva"] = (b["ini"] + 0.2, b["fim"] - b["ini"] - 0.4, rol, rol + 150)
            else:
                p.a(f'tl.fromTo("{fone}", {{ y: 420, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.7, ease: E.snap }}, {num(b["ini"])});')
                p.som("assenta", b["ini"] + 0.3)
        topo_texto = titulo(p, b, fora) if not (tem_painel and ctx["painel_de"] <= b["ini"] + 0.01) else None
        if topo_texto is None and (cena.get("titulo") or cena.get("apoio")):
            p.aviso(f"batida {b['i']}: o painel ocupa o topo nesta batida; 'titulo' e 'apoio' foram ignorados")
        item = cena.get("painel_item")
        momentos = sorted(((quando(p, b, m), k, m) for k, m in enumerate(cena.get("momentos", []))), key=lambda x: (x[0], x[1]))
        if item:
            if not tem_painel or not 1 <= int(item) <= len(ctx["painel"]["itens"]):
                raise ErroDeCena(f"batida {b['i']}: 'painel_item' {item} nao existe no 'painel' do roteiro")
            item = int(item)
            t_digita = next((t for t, _, m in momentos if m.get("faz") == "preenche"), b["fim"] - 0.5)
            linha = HUD_TOPO + 59 + 84 * (item - 1)
            rotulo = ctx["painel"]["itens"][item - 1]
            selos.append(f'    <div class="selo tt" id="st{item}"><div class="in cx"><div class="n">{item:02d}</div><div class="t">{esc(rotulo)}</div></div></div>')
            t_selo = rt.segurar_texto(b["fala"], b["primeira"])
            p.a(f'selo({item}, {linha}, {num(t_selo)}, {num(t_selo + 0.75)}, {num(max(t_digita, t_selo + 1.3))});')
            p.som("selo", t_selo)
            p.texto(f"selo {item}", 90, 760, 70 + len(rotulo) * 44 * e["titulo_largura"], 150, t_selo, t_selo + 1.1)
        chips = []
        for t, _, m in momentos:
            faz = m.get("faz")
            onde = f"batida {b['i']}, momento '{m.get('na', '@inicio')}'"
            if faz == "camera":
                alvo = _caixa(m["alvo"], onde)
                visivel(b, alvo, faz)
                s = float(m.get("zoom", 1.4))
                if not 1.0 < s <= 2.2:
                    raise ErroDeCena(f"{onde}: 'zoom' vai de 1.05 a 2.2 (o piloto usa de 1.35 a 1.5)")
                d = 0.8 if not p.cameras else 0.7
                p.a(f'K.camera("{cam}", {num(t)}, {obj(fx=540, fy=tela_de(alvo["y"] + alvo["h"] / 2), px=540, py=MIRA_Y if tem_painel else 860, s=s, d=d)});')
                p.som("camera" if not p.cameras else "camera_curta", t + d / 2)
                p.cameras += 1
                camera = True
            elif faz == "volta":
                d = 0.9 if b.get("abre") else 0.5
                p.a(f'K.cameraVolta("{cam}", {num(t)}, {obj(d=d)});')
                p.som("assenta", t + 0.3)
                camera = False
            elif faz == "foco":
                alvo = _caixa(m["alvo"], onde)
                visivel(b, alvo, faz)
                extra = {"surge": True} if not pagina["foco_visivel"] else {}
                if m.get("cor") or extra:
                    extra["cor"] = p.cor(m.get("cor"))
                p.a(f'K.foco("{pagina["foco"]}", {num(t)}, {obj(x=alvo["x"], y=alvo["y"], w=alvo["w"], h=alvo["h"])}, {obj(**extra)});')
                p.som("foco", t)
                pagina["foco_visivel"] = True
            elif faz == "marca":
                alvo = _caixa(m["alvo"], onde)
                visivel(b, alvo, faz)
                mid = f"{gid}-m{sum(len(x['marcas']) for x in paginas) + 1}"
                classe = "mk b" if m.get("cor") in ("acento2", "segunda") else "mk"
                pagina["marcas"].append(f'<div class="{classe}" id="{mid}" style="left:{num(alvo["x"])}px;top:{num(alvo["y"])}px;width:{num(alvo["w"])}px;height:{num(alvo["h"])}px"></div>')
                p.a(f'K.marca("#{mid}", {num(t)}, {obj(d=float(m.get("d", 0.3)))});')
                p.som("marca", t)
            elif faz == "toque":
                p.a(f'K.toque("{fone}", {num(t + 0.06)});')
                p.som("toque", t + 0.02)
                p.quiques += 1
            elif faz == "rola":
                if "alvo" in m:
                    alvo = _caixa(m["alvo"], onde)
                    para = alvo["y"] + alvo["h"] / 2 - ((MIRA_Y if tem_painel else 860) - tela_y) / pagina["escala"]
                else:
                    para = float(m.get("para", rol))
                para = max(0.0, min(maximo, para))
                d = 1.0 if abs(para - rol) > 900 else 0.5
                p.a(f'rola("{pagina["rol"]}", {num(pagina["escala"], 5)}, {num(rol)}, {num(para)}, {num(t)}, {num(d)});')
                p.som("rola_longa" if d > 0.9 else "rola", t + d / 2)
                rol = para
            elif faz == "chip":
                chips.append((t, str(m.get("texto", ""))))
            elif faz == "preenche":
                if not item:
                    raise ErroDeCena(f"{onde}: 'preenche' so funciona em batida com 'painel_item'")
                valor = str(m.get("valor", ""))
                d = max(0.35, min(0.8, 0.032 * len(valor)))
                p.a(f'K.digita("#v{item}", "#k{item}", {txt(valor)}, {num(t)}, {num(d)});')
                p.som("digita", t, d)
                ctx["valores"][item] = valor
            elif faz == "confirma":
                if not item:
                    raise ErroDeCena(f"{onde}: 'confirma' so funciona em batida com 'painel_item'")
                p.a(f'confirma({item}, {len(ctx["painel"]["itens"])}, {num(t)});')
                p.som("confirma", t)
                ctx["confirmados"].append(item)
                if len(ctx["confirmados"]) == len(ctx["painel"]["itens"]):
                    p.a(f'tl.to("#hud", {{ boxShadow: "12px 12px 0 " + ACENTO2, duration: 0.2 }}, {num(t + 0.02)});' if e["nome"] == "pixel" else
                        f'tl.to("#hud", {{ borderColor: ACENTO2, duration: 0.2 }}, {num(t + 0.02)});')
                    p.a(f'K.toque("#hud", {num(t + 0.02)});')
                    p.quiques += 1
            else:
                raise ErroDeCena(f"{onde}: 'faz' desconhecido ({faz}); na cena aparelho use camera, volta, foco, marca, toque, rola, chip, preenche ou confirma")
        fecha = b["fim"] - 0.5
        if chips:
            x = 90
            veu = f"{gid}-v{b['i']}"
            chips_html.append(f'    <div class="veu" id="{veu}"></div>')
            p.p(f'gsap.set("#{veu}", {{ opacity: 0 }});')
            p.a(f'tl.to("#{veu}", {{ opacity: 1, duration: 0.35, ease: E.casa }}, {num(chips[0][0] - 0.2)});')
            p.a(f'tl.to("#{veu}", {{ opacity: 0, duration: 0.3, ease: E.sai }}, {num(fecha + 0.08)});')
            ids = []
            for k, (t, texto) in enumerate(chips):
                cid = f"{gid}-ch{b['i']}-{k + 1}"
                conferir_pixel(p, f"batida {b['i']}, chip", texto)
                larg_chip = len(texto) * (24 if e["nome"] == "pixel" else 16) + 48
                chips_html.append(f'    <div class="chip{" a" if k == 0 else ""}" id="{cid}" style="left:{x}px;top:{CHIP_Y}px">{esc(texto)}</div>')
                p.a(f'K.bate("#{cid}", {num(t)}, {obj(de=1.5, d=0.3)});')
                p.som("chip", t)
                p.texto(f"chip {texto}", x, CHIP_Y, larg_chip, 66, t, fecha + 0.3)
                ids.append(f"#{cid}")
                x += larg_chip + 18
            p.a(f'K.sai({txt(ids)}, {num(fecha + 0.08)}, {obj(y=30, stagger=0.04)});')
        if pagina["foco_visivel"]:
            p.a(f'tl.to("{pagina["foco"]}", {{ opacity: 0, duration: 0.15 }}, {num(fecha)});')
            pagina["foco_visivel"] = False
        if camera:
            p.a(f'K.cameraVolta("{cam}", {num(fecha - 0.05)}, {obj(d=0.45)});')
            camera = False

    barra_html = '<div class="barra"><i style="left:14px"></i><i style="left:40px"></i><i style="left:66px"></i></div>' if barra else ""
    pgs = []
    for pg in paginas:
        pgs.append(f'          <div class="pg" id="{pg["id"]}"><div class="rol" id="{pg["rol"][1:]}" style="width:{num(pg["larg"])}px">'
                   f'<img src="{esc(pg["arquivo"])}" alt="" style="width:{num(pg["larg"])}px"><div class="foco" id="{pg["foco"][1:]}"></div>' + "".join(pg["marcas"]) + "</div></div>")
        p.p(f'gsap.set("{pg["foco"]}", {{ opacity: 0 }});')
    corpo = (f'    <div class="cam" id="{cam[1:]}">\n      <div class="fone" id="{fone[1:]}" style="left:{TELA_X - borda}px;top:{FONE_TOPO}px;width:{TELA_L + 2 * borda}px;height:{TELA_A + barra + 2 * borda + 6}px">'
             f'{barra_html}\n        <div class="tela" style="top:{barra}px">\n' + "\n".join(pgs) + "\n        </div>\n      </div>\n    </div>\n"
             + "\n".join(chips_html + selos + fora))
    if selos:
        p.p('gsap.set(".selo", { opacity: 0 });')
    p.secao(f"s-{gid}", ini, fim, 5, corpo.rstrip("\n"), 1)


def _midia(p, id_, arquivo, ini, dur, estilo, trilha):
    if arquivo.lower().endswith(VIDEOS):
        w, h, total = p.medir(arquivo, video=True)
        return (f'<video id="{id_}" class="clip" src="{esc(arquivo)}" data-start="{num(ini)}" data-duration="{num(min(dur, total - 0.05))}" data-media-start="0" '
                f'data-track-index="{trilha}" muted playsinline style="{estilo}"></video>'), (w, h)
    return None, p.medir(arquivo)


def cena_abertura(p, b, ctx):
    cena = b["cena"]
    arquivo = cena.get("midia")
    if not arquivo:
        raise ErroDeCena(f"batida {b['i']}: a cena 'abertura' precisa de 'midia' (imagem ou video do resultado, dentro da pasta da peca)")
    dur = b["fim"] - b["ini"]
    corpo = []
    video, (w, h) = _midia(p, f"b{b['i']}-v", arquivo, b["ini"], dur, "", 6)
    if video:
        s = max(LARGURA / w, ALTURA / h)
        estilo = f"left:{num((LARGURA - w * s) / 2)}px;top:{num((ALTURA - h * s) / 2)}px;width:{num(w * s)}px;height:{num(h * s)}px;object-fit:fill;z-index:1"
        p.soltos.append("  " + video.replace('style=""', f'style="{estilo}"'))
    else:
        foco = cena.get("foco") or {}
        origem = f"{num(foco.get('x', 50))}% {num(foco.get('y', 45))}%"
        mid = f"b{b['i']}-m"
        corpo.append(f'    <div class="ab-m" id="{mid}" style="background-image:url(\'{esc(arquivo)}\');background-position:{origem};transform-origin:{origem}"></div>')
        p.a(f'tl.fromTo("#{mid}", {{ scale: 1 }}, {{ scale: {num(float(cena.get("zoom", 1.14)))}, duration: {num(dur)}, ease: "none" }}, {num(b["ini"])});')
    if cena.get("titulo") or cena.get("apoio"):
        veu = f"b{b['i']}-veu"
        corpo.append(f'    <div class="ab-veu" id="{veu}"></div>')
        p.p(f'gsap.set("#{veu}", {{ opacity: 0 }});')
        titulo(p, b, corpo)
        t = b.get("t_titulo", rt.segurar_texto(b["ini"], b["primeira"]))
        p.a(f'tl.to("#{veu}", {{ opacity: 1, duration: 0.4, ease: E.casa }}, {num(max(0, t - 0.2))});')
    p.secao(f"s-b{b['i']}", b["ini"], b["fim"], 5, "\n".join(corpo), 1 + b["i"] % 2)


def cena_galeria(p, b, ctx):
    cena = b["cena"]
    itens = cena.get("midias") or []
    if not itens:
        raise ErroDeCena(f"batida {b['i']}: a cena 'galeria' precisa de 'midias' (lista de {{arquivo, na}})")
    if len(itens) > len(DESVIOS):
        raise ErroDeCena(f"batida {b['i']}: a galeria aceita ate {len(DESVIOS)} midias por batida")
    lw, la = FORMATOS.get(cena.get("formato", "retrato"), FORMATOS["retrato"])
    corpo = []
    y0 = titulo(p, b, corpo)
    cy = max(910, y0 + la / 2 + 10) if (cena.get("titulo") or cena.get("apoio")) else 880
    anteriores = []
    for k, item in enumerate(itens):
        arquivo = item["arquivo"] if isinstance(item, dict) else item
        t = quando(p, b, item if isinstance(item, dict) and item.get("na") else None, {"na": "@inicio", "ajuste": 0.0}) if k or (isinstance(item, dict) and item.get("na")) else b["ini"]
        dx, giro = DESVIOS[k]
        cid = f"b{b['i']}-c{k + 1}"
        esquerda, topo = round(540 - lw / 2 + dx), round(cy - la / 2 + (k % 2) * 18)
        estilo = f"left:{esquerda}px;top:{topo}px;width:{lw}px;height:{la}px"
        video, _ = _midia(p, f"{cid}-v", arquivo, t, b["fim"] - t, "", 6)
        if video:
            p.soltos.append(f'  <div class="cartao" id="{cid}" style="{estilo};z-index:5">\n    {video.replace(chr(32) + "style=" + chr(34) + chr(34), "")}\n  </div>')
            giro = 0
        else:
            corpo.append(f'    <div class="cartao" id="{cid}" style="{estilo}"><div class="im" id="{cid}-i" style="background-image:url(\'{esc(arquivo)}\')"></div></div>')
            p.a(f'tl.fromTo("#{cid}-i", {{ scale: 1 }}, {{ scale: 1.1, duration: {num(b["fim"] - t)}, ease: "none", immediateRender: false }}, {num(t)});')
        p.p(f'gsap.set("#{cid}", {obj(rotation=giro)});')
        p.a(f'K.bate("#{cid}", {num(t)}, {obj(de=1.22, d=0.42)});')
        if anteriores:
            p.a(f'tl.to({txt(anteriores)}, {{ scale: 0.94, duration: 0.4, ease: E.casa }}, {num(t)});')
        p.som("midia", t + 0.1)
        anteriores.append(f"#{cid}")
    if not b.get("ultima"):
        p.a(f'K.sai({txt(anteriores)}, {num(b["fim"] - 0.3)}, {obj(y=-60, stagger=0.04)});')
    p.secao(f"s-b{b['i']}", b["ini"], b["fim"], 5, "\n".join(corpo), 1 + b["i"] % 2)


def cena_comparacao(p, b, ctx):
    cena = b["cena"]
    if not cena.get("antes") or not cena.get("depois"):
        raise ErroDeCena(f"batida {b['i']}: a cena 'comparacao' precisa de 'antes' e 'depois' (imagens dentro da pasta da peca)")
    rotulos = cena.get("rotulos") or ["ANTES", "DEPOIS"]
    for r in rotulos:
        conferir_pixel(p, f"batida {b['i']}, rotulo", r)
    modo = cena.get("modo", "cortina")
    corpo = []
    y0 = titulo(p, b, corpo)
    topo = max(590, y0 + 20)
    t = quando(p, b, cena.get("revela_na"), {"na": "@inicio", "ajuste": 0.5})
    pre = f"b{b['i']}"
    larg_rot = [len(r) * (24 if p.e["nome"] == "pixel" else 16) + 48 for r in rotulos]
    if modo == "cortina":
        lw, la = 860, 640
        corpo.append(f'    <div class="cartao" id="{pre}-cmp" style="left:110px;top:{topo}px;width:{lw}px;height:{la}px">'
                     f'<div class="im" style="background-image:url(\'{esc(cena["antes"])}\')"></div>'
                     f'<div class="rv" id="{pre}-rv"><div class="im" id="{pre}-rvi" style="background-image:url(\'{esc(cena["depois"])}\')"></div></div>'
                     f'<div class="dv" id="{pre}-dv"></div>'
                     f'<div class="chip a" id="{pre}-ra" style="left:20px;top:20px">{esc(rotulos[0])}</div>'
                     f'<div class="chip" id="{pre}-rd" style="left:{lw - 110 - larg_rot[1]}px;top:20px">{esc(rotulos[1])}</div></div>')
        p.p(f'gsap.set("#{pre}-rv", {{ x: {-lw} }});')
        p.p(f'gsap.set("#{pre}-rvi", {{ x: {lw} }});')
        p.p(f'gsap.set("#{pre}-dv", {{ opacity: 0 }});')
        p.a(f'K.sobe("#{pre}-cmp", {num(b["ini"])}, {obj(y=90, d=0.6)});')
        p.a(f'tl.to(["#{pre}-rv", "#{pre}-rvi"], {{ x: 0, duration: 0.9, ease: E.troca }}, {num(t)});')
        p.a(f'tl.fromTo("#{pre}-dv", {{ x: 0, opacity: 1 }}, {{ x: {lw}, opacity: 1, duration: 0.9, ease: E.troca, immediateRender: false }}, {num(t)});')
        p.a(f'tl.to("#{pre}-dv", {{ opacity: 0, duration: 0.15 }}, {num(t + 0.9)});')
        p.a(f'K.bate("#{pre}-rd", {num(t + 0.75)}, {obj(de=1.5, d=0.3)});')
        p.a(f'tl.to("#{pre}-ra", {{ opacity: 0, duration: 0.2 }}, {num(t + 0.2)});')
        p.a(f'K.respira("#{pre}-cmp", {num(b["ini"] + 0.6)}, {num(b["fim"] - b["ini"] - 0.9)}, {obj(y=7, periodo=2.6)});')
        p.texto(f"rotulo {rotulos[0]}", 130, topo + 20, larg_rot[0], 66, b["ini"], t + 0.4)
        p.texto(f"rotulo {rotulos[1]}", 110 + lw - 110 - larg_rot[1], topo + 20, larg_rot[1], 66, t + 0.75, b["fim"])
        saem = [f"#{pre}-cmp"]
    elif modo == "lado":
        lw, la = 410, 600
        topo += 70
        for k, (lado, arq, x) in enumerate((("a", cena["antes"], 110), ("d", cena["depois"], 560))):
            corpo.append(f'    <div class="chip{" a" if k else ""}" id="{pre}-r{lado}" style="left:{x}px;top:{topo - 78}px">{esc(rotulos[k])}</div>')
            corpo.append(f'    <div class="cartao" id="{pre}-c{lado}" style="left:{x}px;top:{topo}px;width:{lw}px;height:{la}px"><div class="im" id="{pre}-i{lado}" style="background-image:url(\'{esc(arq)}\')"></div></div>')
            p.texto(f"rotulo {rotulos[k]}", x, topo - 78, larg_rot[k], 66, b["ini"] if not k else t, b["fim"])
        p.a(f'K.sobe(["#{pre}-ra", "#{pre}-ca"], {num(b["ini"])}, {obj(y=80, d=0.55, stagger=0.06)});')
        p.a(f'K.bate(["#{pre}-cd", "#{pre}-rd"], {num(t)}, {obj(de=1.3, d=0.42, stagger=0.1)});')
        p.a(f'tl.to("#{pre}-ca", {{ scale: 0.95, duration: 0.4, ease: E.casa }}, {num(t)});')
        for lado in "ad":
            p.a(f'tl.fromTo("#{pre}-i{lado}", {{ scale: 1 }}, {{ scale: 1.1, duration: {num(b["fim"] - b["ini"])}, ease: "none" }}, {num(b["ini"])});')
        saem = [f"#{pre}-ca", f"#{pre}-cd", f"#{pre}-ra", f"#{pre}-rd"]
    else:
        raise ErroDeCena(f"batida {b['i']}: 'modo' da comparacao e 'cortina' ou 'lado'")
    p.som("assenta", b["ini"] + 0.3)
    p.som("revela", t + 0.45)
    if not b.get("ultima"):
        p.a(f'K.sai({txt(saem)}, {num(b["fim"] - 0.3)}, {obj(y=-60, stagger=0.04)});')
    p.secao(f"s-b{b['i']}", b["ini"], b["fim"], 5, "\n".join(corpo), 1 + b["i"] % 2)


def cena_passos(p, b, ctx):
    cena = b["cena"]
    if not cena.get("pedido") or not cena.get("resultado"):
        raise ErroDeCena(f"batida {b['i']}: a cena 'passos' precisa de 'pedido' (texto digitado) e 'resultado' (imagem ou video)")
    pre = f"b{b['i']}"
    pedido = str(cena["pedido"])
    linhas = max(1, math.ceil(len(pedido) * 44 * 0.56 / 800))
    alto = 26 + 38 + linhas * 52 + 34
    t_dig = quando(p, b, cena.get("digita_na"), "@inicio", texto=True)
    t_res = quando(p, b, cena.get("resultado_na"), "@fim")
    d = max(0.5, min(2.2, 0.035 * len(pedido), t_res - t_dig - 0.3))
    lw, la = FORMATOS.get(cena.get("formato", "retrato"), FORMATOS["retrato"])
    area_topo = TOPO_TITULO + alto + RESPIRO_DO_CARTAO
    area_alta = LEGENDA_TOPO - RESPIRO_DO_CARTAO - area_topo
    escala = min(area_alta / la, CARTAO_L_MAX / lw)
    lw, la = round(lw * escala), round(la * escala)
    topo = round(area_topo + (area_alta - la) / 2)
    estilo = f"left:{round(540 - lw / 2)}px;top:{topo}px;width:{lw}px;height:{la}px"
    partida = ""
    if cena.get("partida"):
        if str(cena["partida"]).lower().endswith(VIDEOS):
            raise ErroDeCena(f"batida {b['i']}: 'partida' da cena 'passos' e uma imagem (para video, use um quadro dele)")
        p.medir(cena["partida"])
        partida = f'<div class="im" id="{pre}-pi" style="background-image:url(\'{esc(cena["partida"])}\')"></div>'
        p.a(f'tl.fromTo("#{pre}-pi", {{ scale: 1 }}, {{ scale: 1.08, duration: {num(t_res + 0.4 - b["ini"])}, ease: "none", immediateRender: false }}, {num(b["ini"])});')
    corpo = [f'    <div class="cx pedido" id="{pre}-cx" style="top:{TOPO_TITULO}px;height:{alto}px"><div class="lb">{esc(cena.get("rotulo", "O PEDIDO"))}</div>'
             f'<div class="tx"><span id="{pre}-q"></span><i class="cur" id="{pre}-k"></i></div></div>',
             f'    <div class="cartao" id="{pre}-esp" style="{estilo}">{partida}<div class="gr" id="{pre}-gr"></div></div>']
    video, _ = _midia(p, f"{pre}-rv", cena["resultado"], t_res, b["fim"] - t_res, "", 6)
    if video:
        p.soltos.append(f'  <div class="cartao" id="{pre}-res" style="{estilo};z-index:5">\n    {video.replace(chr(32) + "style=" + chr(34) + chr(34), "")}\n  </div>')
    else:
        corpo.append(f'    <div class="cartao" id="{pre}-res" style="{estilo}"><div class="im" id="{pre}-ri" style="background-image:url(\'{esc(cena["resultado"])}\')"></div></div>')
        p.a(f'tl.fromTo("#{pre}-ri", {{ scale: 1.12 }}, {{ scale: 1, duration: {num(b["fim"] - t_res)}, ease: E.casa, immediateRender: false }}, {num(t_res)});')
    t_cx = rt.segurar_texto(b["ini"], b["primeira"])
    p.p(f'gsap.set("#{pre}-k", {{ opacity: 0 }});')
    p.a(f'K.sobe("#{pre}-cx", {num(t_cx)}, {obj(y=-60, d=0.5)});')
    p.a(f'K.sobe("#{pre}-esp", {num(b["ini"])}, {obj(y=90, d=0.6)});')
    p.a(f'K.digita("#{pre}-q", "#{pre}-k", {txt(pedido)}, {num(max(t_dig, t_cx + 0.3))}, {num(d)});')
    p.a(f'tl.fromTo("#{pre}-gr", {{ x: {-lw} }}, {{ x: {lw * 2}, duration: 1.1, ease: "none", repeat: {max(1, round((t_res - b["ini"]) / 1.1))} }}, {num(b["ini"])});')
    p.a(f'K.bate("#{pre}-res", {num(t_res)}, {obj(de=1.14, d=0.45)});')
    p.a(f'tl.to("#{pre}-esp", {{ opacity: 0, duration: 0.2 }}, {num(t_res + 0.2)});')
    p.som("digita", max(t_dig, t_cx + 0.3), d)
    p.som("resultado", t_res)
    p.som("midia", t_res + 0.1)
    p.texto("pedido", TEXTO_X, TOPO_TITULO, TEXTO_L, alto, t_cx, b["fim"])
    if not b.get("ultima"):
        p.a(f'K.sai(["#{pre}-cx", "#{pre}-res"], {num(b["fim"] - 0.3)}, {obj(y=-60, stagger=0.05)});')
    p.secao(f"s-b{b['i']}", b["ini"], b["fim"], 5, "\n".join(corpo), 1 + b["i"] % 2)


def _linhas_de_impacto(p, b, corpo, linhas, topo, prefixo):
    e = p.e
    maior = max(len(liso(x["texto"])) for x in linhas)
    px = min(e["impacto_px"], math.floor(TITULO_L / (maior * e["titulo_largura"])))
    passo = round(px * e["impacto_altura"])
    y = topo
    ids = []
    for k, linha in enumerate(linhas):
        conferir_pixel(p, f"batida {b['i']}, linha", linha["texto"])
        id_ = f"{prefixo}{k + 1}"
        corpo.append(f'    <div class="imp tt" id="{id_}" style="top:{y}px;font-size:{px}px"><span class="ln">{marcar(linha["texto"])}</span></div>')
        padrao = {"na": "@inicio", "ajuste": min(0.5, 0.25 * k)}
        t = quando(p, b, linha if linha.get("na") else None, padrao, texto=True)
        p.a(f'K.bate("#{id_}", {num(t)}, {obj(de=1.7 + 0.2 * (k % 2), d=0.38)});')
        if k:
            p.a(f'tl.fromTo("#{ids[-1]}", {{ y: 0 }}, {{ y: -10, duration: 0.12, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }}, {num(t)});')
        p.som("linha" if not k else "titulo", t)
        w = largura_do_texto(e, linha["texto"], px)
        p.texto(id_, 540 - w / 2, y, w, px, t, b["fim"])
        ids.append(id_)
        y += passo
    return y, ids


def _linhas(cena, onde):
    bruto = cena.get("linhas")
    if not bruto:
        raise ErroDeCena(f"{onde}: faltou 'linhas' (lista de {{texto, na}})")
    return [x if isinstance(x, dict) else {"texto": x} for x in bruto]


def cena_impacto(p, b, ctx):
    cena = b["cena"]
    corpo = []
    linhas = _linhas(cena, f"batida {b['i']}, cena impacto")
    y, ids = _linhas_de_impacto(p, b, corpo, linhas, int(cena.get("topo", 600)), f"b{b['i']}-l")
    saem = [f"#{x}" for x in ids]
    if cena.get("apoio"):
        b["cena"] = {"apoio": cena["apoio"], "apoio_na": cena.get("apoio_na")}
        b["ultima_real"], b["ultima"] = b.get("ultima"), True
        titulo(p, b, corpo, topo=y + 40)
        b["ultima"] = b["ultima_real"]
        b["cena"] = cena
        saem.append(f"#b{b['i']}-apo")
    if not b.get("ultima"):
        p.a(f'K.sai({txt(saem)}, {num(b["fim"] - 0.35)}, {obj(stagger=0.05)});')
    p.secao(f"s-b{b['i']}", b["ini"], b["fim"], 5, "\n".join(corpo), 1 + b["i"] % 2)


def cena_fecho(p, b, ctx):
    cena = b["cena"]
    corpo = []
    if cena.get("brilhos"):
        corpo.append(f'    <img class="brilhos" id="br1" src="{esc(cena["brilhos"])}" alt="" style="top:160px">')
        corpo.append(f'    <img class="brilhos" id="br2" src="{esc(cena["brilhos"])}" alt="" style="top:1180px;transform:scale(-1,-1)">')
        for sel, t in (("#br1", b["ini"] + 0.1), ("#br2", b["ini"] + 0.4)):
            p.a(f'tl.fromTo("{sel}", {{ opacity: 0.25 }}, {{ opacity: 0.9, duration: 0.35, ease: E.respira, yoyo: true, repeat: {max(1, round((b["fim"] - t) / 0.35) - 1)} }}, {num(t)});')
    y = int(cena.get("topo", 420))
    if cena.get("linhas"):
        y, _ = _linhas_de_impacto(p, b, corpo, _linhas(cena, f"batida {b['i']}, fecho"), y, "f")
    if cena.get("apoio"):
        b["cena"] = {"apoio": cena["apoio"], "apoio_na": cena.get("apoio_na")}
        b["ultima"] = True
        y = titulo(p, b, corpo, topo=y + 52) - 30
        b["cena"] = cena
    valores = [ctx["valores"][k] for k in sorted(ctx["valores"])]
    if cena.get("resumo") and valores:
        alto = 50 + 72 * len(valores) + 10
        topo = y + 88
        itens = "".join(f'<div class="li">{esc(v)}<b class="tt">OK</b></div>' for v in valores)
        corpo.append(f'    <div class="cx" id="f-card" style="top:{topo}px;height:{alto}px"><div class="topo">{esc(ctx["painel"].get("titulo", "RESUMO"))}</div>{itens}</div>')
        p.p('gsap.set("#f-card", { rotation: -2 });')
        p.a(f'K.sobe("#f-card", {num(b["ini"] + 0.2)}, {obj(y=120, d=0.6)});')
        p.a(f'K.respira("#f-card", {num(b["ini"] + 0.8)}, {num(b["fim"] - b["ini"] - 0.9)}, {obj(y=8, periodo=2.8)});')
        p.texto("resumo", 230, topo, 620, alto, b["ini"] + 0.2, b["fim"])
        y = topo + alto
    elif cena.get("resumo"):
        p.aviso("fecho: 'resumo' pede um 'painel' com valores preenchidos (momentos 'preenche'); o cartao ficou de fora")
    com_resumo = bool(cena.get("resumo") and valores)
    logo_a = 176 if com_resumo else 300
    logo_y = min(max(y + 56, 0 if com_resumo else 960), 1230 if com_resumo else 1080)
    t_logo = round(max(b["fim_fala"] + 0.36, b["ini"] + 0.6), 3)
    if b["fim"] - t_logo < 1.8:
        p.aviso(f"fecho: o logo fica so {b['fim'] - t_logo:.1f} s na tela; a ultima fala esta comprida para o fecho")
    corpo.append(f'    <div id="f-glow" style="top:{logo_y + logo_a // 2 - 190}px"></div>')
    corpo.append(f'    <img id="f-logo" src="{esc(ctx["logo"])}" alt="{esc(ctx["nome_da_marca"])}" style="top:{logo_y}px;height:{logo_a}px">')
    p.p('gsap.set(["#f-glow", "#f-logo"], { opacity: 0 });')
    p.a(f'tl.to("#f-glow", {{ opacity: 1, duration: 0.6, ease: E.casa }}, {num(t_logo - 0.14)});')
    p.a(f'K.bate("#f-logo", {num(t_logo)}, {obj(de=1.3, d=0.42)});')
    p.a(f'tl.to("#f-logo", {{ scale: 1.04, duration: {num(max(0.6, b["fim"] - t_logo - 0.5))}, ease: E.respira }}, {num(t_logo + 0.46)});')
    p.som("sobe_logo", t_logo)
    p.som("logo", t_logo)
    p.som("brilho_logo", t_logo)
    chamada = cena.get("chamada", ctx.get("url"))
    if chamada:
        px_letra = 26 if p.e["nome"] == "pixel" else 19
        w = min(TEXTO_L, len(chamada) * px_letra + 64)
        cy = logo_y + logo_a + 24
        corpo.append(f'    <div class="pilula" id="f-site" style="left:{round(540 - w / 2)}px;top:{cy}px;width:{round(w)}px">{esc(chamada)}</div>')
        p.a(f'K.sobe("#f-site", {num(t_logo + 0.3)}, {obj(y=40, d=0.4)});')
        p.a(f'tl.fromTo("#f-site", {{ scale: 1 }}, {{ scale: 1.05, duration: 0.5, ease: E.respira, yoyo: true, repeat: {max(1, round((b["fim"] - t_logo - 0.8) / 0.5))}, immediateRender: false }}, {num(t_logo + 0.75)});')
        p.som("apoio", t_logo + 0.3)
        p.texto("chamada para o site", 540 - w / 2, cy, w, 60, t_logo + 0.3, b["fim"])
    else:
        p.aviso("fecho sem chamada para o site: preencha 'url' da marca no tokens.json ou 'chamada' na cena")
    p.texto("logo", 280, logo_y, 520, logo_a, t_logo, b["fim"])
    p.secao("s-fim", b["ini"], b["fim"], 6, "\n".join(corpo), 2)


CENAS = {"abertura": cena_abertura, "galeria": cena_galeria, "comparacao": cena_comparacao, "passos": cena_passos, "impacto": cena_impacto, "fecho": cena_fecho}


def montar(p, roteiro, batidas, ctx):
    fundo(p, roteiro)
    cfg_painel = roteiro.get("painel")
    fecho = batidas[-1] if batidas[-1]["cena"]["tipo"] == "fecho" else None
    antes_do_fecho = fecho["ini"] if fecho else p.total
    ctx.update({"painel": None, "valores": {}, "confirmados": []})
    if cfg_painel:
        if not cfg_painel.get("itens") or len(cfg_painel["itens"]) > 4:
            raise ErroDeCena("painel: 'itens' precisa ter de 1 a 4 linhas")
        primeira = next((b for b in batidas if b["cena"].get("painel_item")), None)
        n = int(cfg_painel.get("entra_na_batida") or (primeira["i"] if primeira else 1))
        if not 1 <= n <= len(batidas):
            raise ErroDeCena(f"painel: 'entra_na_batida' {n} nao existe (o roteiro tem {len(batidas)} batidas)")
        de = rt.segurar_texto(batidas[n - 1]["ini"], n == 1)
        ctx["painel"] = cfg_painel
        ctx["painel_de"] = de
        painel(p, cfg_painel, de, antes_do_fecho)
    i = 0
    while i < len(batidas):
        b = batidas[i]
        tipo = b["cena"]["tipo"]
        corte = b["ini"]
        transicao = b["cena"].get("transicao", "cortina" if tipo == "fecho" and i else "corte")
        if i and transicao == "cortina":
            cortina(p, corte)
        elif i and tipo != "aparelho" or (i and tipo == "aparelho" and batidas[i - 1]["cena"]["tipo"] != "aparelho"):
            p.som("troca_leve" if p.trocas % 2 else "troca", corte)
            p.trocas += 1
        if tipo == "aparelho":
            j = i
            while j + 1 < len(batidas) and batidas[j + 1]["cena"]["tipo"] == "aparelho":
                j += 1
            grupo_aparelho(p, batidas[i:j + 1], ctx)
            i = j + 1
            continue
        CENAS[tipo](p, b, ctx)
        i += 1
    legenda(p, antes_do_fecho - 0.6 if fecho else p.total)
    if not fecho:
        p.aviso("a ultima batida nao e 'fecho': toda peca termina com logo e chamada para o site")


def html_da_peca(p, titulo_da_peca, total, css_extra="", js_extra=""):
    estilo = css_da_marca(p.e) + "\n".join(p.css) + ("\n" + css_extra if css_extra else "")
    script = (f'  const ACENTO = {txt(p.e["acento"])};\n  const ACENTO2 = {txt(p.e["acento2"])};\n' + JS_BASE + "\n".join(p.preparo) + "\n\n" + "\n".join(p.js)
              + ("\n\n" + js_extra if js_extra else "") + '\n\n  window.__timelines["reel"] = tl;')
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{esc(titulo_da_peca)}</title>
<script src="_motor/gsap.min.js"></script>
<script src="_motor/TextPlugin.min.js"></script>
<script src="_motor/kit/motion.js"></script>
<script src="legenda.js"></script>
<style>
{estilo}
</style>
</head>
<body>
<div id="root" data-composition-id="reel" data-start="0" data-width="{LARGURA}" data-height="{ALTURA}" data-duration="{num(total)}">
{chr(10).join(p.secoes + p.soltos)}
</div>
<script>
{script}
</script>
</body>
</html>
"""
