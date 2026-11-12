import base64
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, unquote_to_bytes

EXT_HTML = {".html", ".htm", ".svg"}
EXT_CSS = {".css"}
EXT_JS = {".js", ".mjs", ".cjs"}
ARQUIVOS_VARRIDOS = EXT_HTML | EXT_CSS | EXT_JS
PASTAS_IGNORADAS = {"node_modules", "renders"}
PREFIXOS_DO_MOTOR = ("_motor/",)
ATRIBUTOS_DE_ARQUIVO = {
    "src", "href", "xlink:href", "poster", "data", "background", "manifest", "data-composition-src",
    "action", "formaction", "codebase", "archive", "longdesc", "lowsrc", "dynsrc", "icon", "ping",
}
ATRIBUTOS_SRCSET = {"srcset", "imagesrcset"}
ESQUEMA_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
CSS_COMENTARIO_RE = re.compile(r"/\*.*?(?:\*/|$)", re.DOTALL)
CSS_URL_RE = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)\s'"]*))\s*\)""", re.IGNORECASE)
CSS_IMPORT_RE = re.compile(r"""@import\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
CSS_IMAGE_SET_RE = re.compile(r"""(?:-webkit-)?image-set\(([^;{}]*)\)""", re.IGNORECASE)
CSS_SRC_FN_RE = re.compile(r"""(?<![\w-])src\(\s*(?:"([^"]*)"|'([^']*)')\s*\)""", re.IGNORECASE)
CSS_STRING_RE = re.compile(r""""([^"]*)"|'([^']*)'""")
CSS_ESCAPE_RE = re.compile(r"\\(?:([0-9a-fA-F]{1,6})[ \t\r\n\f]?|(.))", re.DOTALL)
DATA_TEXTO_RE = re.compile(r"(?i)data:\s*(?:text/|image/svg|application/(?:xhtml|xml|javascript|json|ecmascript)|[^,;]*\+xml)")
JS_ESCAPE_RE = re.compile(r"\\(?:x([0-9a-fA-F]{2})|u\{([0-9a-fA-F]{1,6})\}|u([0-9a-fA-F]{4})|\r?\n|(.))", re.DOTALL)
SUSPEITO_RE = re.compile(
    r"""(?<![a-z0-9+.\-])file:"""
    r"""|(?<![a-z0-9])[a-z]:[\\/]"""
    r"""|(?<![\w\\])\\\\[^\\/\s'"]+[\\/]"""
    r"""|(?:^|[\\/\s"'(=,:;])\.\.(?:[\\/]|$|[\s"')?#;,])""",
    re.IGNORECASE,
)


def _decodificar_css(texto):
    def troca(m):
        if m.group(1):
            try:
                return chr(int(m.group(1), 16))
            except (ValueError, OverflowError):
                return "\ufffd"
        return m.group(2)

    return CSS_ESCAPE_RE.sub(troca, texto)


def _decodificar_js(texto):
    def troca(m):
        hexa = m.group(1) or m.group(2) or m.group(3)
        if hexa:
            try:
                return chr(int(hexa, 16))
            except (ValueError, OverflowError):
                return "\ufffd"
        return m.group(4) or ""

    return JS_ESCAPE_RE.sub(troca, texto)


def trecho_suspeito(texto):
    for candidato in (texto, unquote(texto)):
        m = SUSPEITO_RE.search(candidato.replace("\x00", ""))
        if m:
            inicio = max(0, m.start() - 10)
            return candidato[inicio:m.end() + 40].strip()
    return None


def _sem_comentarios_css(texto):
    return CSS_COMENTARIO_RE.sub(lambda m: "\n" * m.group(0).count("\n"), texto)


def analisar_css(texto):
    texto = _sem_comentarios_css(_decodificar_css(texto))
    refs = []
    suspeitos = []

    def linha(pos):
        return texto.count("\n", 0, pos) + 1

    for rx in (CSS_URL_RE, CSS_IMPORT_RE, CSS_SRC_FN_RE):
        for m in rx.finditer(texto):
            refs.append((linha(m.start()), next((g for g in m.groups() if g is not None), "")))
    for m in CSS_IMAGE_SET_RE.finditer(texto):
        for s in CSS_STRING_RE.finditer(m.group(1)):
            refs.append((linha(m.start()), s.group(1) if s.group(1) is not None else s.group(2)))
    for m in CSS_STRING_RE.finditer(texto):
        valor = m.group(1) if m.group(1) is not None else m.group(2)
        t = trecho_suspeito(valor)
        if t:
            suspeitos.append((linha(m.start()), t))
    return refs, suspeitos


def referencias_de_css(texto):
    return analisar_css(texto)[0]


def strings_de_js(texto):
    achados = []
    i, n, linha = 0, len(texto), 1
    while i < n:
        ch = texto[i]
        if ch == "\n":
            linha += 1
            i += 1
        elif texto.startswith("//", i):
            j = texto.find("\n", i)
            i = n if j < 0 else j
        elif texto.startswith("/*", i):
            j = texto.find("*/", i + 2)
            fim = n if j < 0 else j + 2
            linha += texto.count("\n", i, fim)
            i = fim
        elif ch in "'\"`":
            j = i + 1
            while j < n and texto[j] != ch:
                if texto[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if texto[j] == "\n" and ch != "`":
                    break
                j += 1
            achados.append((linha, _decodificar_js(texto[i + 1:j])))
            linha += texto.count("\n", i, j)
            i = j + 1
        else:
            i += 1
    return achados


def suspeitos_de_js(texto):
    achados = []
    for ln, valor in strings_de_js(texto):
        t = trecho_suspeito(valor)
        if t:
            achados.append((ln, t))
    return achados


def referencias_de_srcset(valor):
    urls = []
    i, n = 0, len(valor)
    while i < n:
        while i < n and (valor[i].isspace() or valor[i] == ","):
            i += 1
        j = i
        while j < n and not valor[j].isspace():
            j += 1
        if j > i:
            urls.append(valor[i:j].rstrip(","))
        i = j
        while i < n and valor[i] != ",":
            i += 1
    return urls


class _Varredor(HTMLParser):
    def __init__(self, linha_base=1, rotulo=""):
        super().__init__(convert_charrefs=False)
        self.refs = []
        self.suspeitos = []
        self.tags = []
        self._linha_base = linha_base
        self._rotulo = rotulo
        self._em_estilo = None
        self._em_script = None

    def _linha(self):
        return self._linha_base + self.getpos()[0] - 1

    def _onde(self, texto):
        return f"{self._rotulo}{texto}"

    def _absorver(self, outro):
        self.refs += outro.refs
        self.suspeitos += outro.suspeitos
        self.tags += outro.tags

    def _atributo(self, tag, nome, valor, linha):
        if nome in ATRIBUTOS_DE_ARQUIVO:
            self.refs.append((linha, self._onde(f"<{tag} {nome}>"), valor))
            return
        if nome in ATRIBUTOS_SRCSET:
            for u in referencias_de_srcset(valor):
                self.refs.append((linha, self._onde(f"<{tag} {nome}>"), u))
            return
        if nome == "srcdoc":
            interno = _Varredor(linha, self._onde(f"<{tag} srcdoc> "))
            interno.feed(valor)
            interno.close()
            self._absorver(interno)
            return
        refs, suspeitos = analisar_css(valor)
        for _, u in refs:
            self.refs.append((linha, self._onde(f"<{tag} {nome}> url()"), u))
        for _, t in suspeitos:
            self.suspeitos.append((linha, self._onde(f"<{tag} {nome}>"), t))
        if nome.startswith("on"):
            for _, t in suspeitos_de_js(valor):
                self.suspeitos.append((linha, self._onde(f"<{tag} {nome}> (script)"), t))
        t = trecho_suspeito(valor)
        if t and not suspeitos:
            self.suspeitos.append((linha, self._onde(f"<{tag} {nome}>"), t))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        linha = self._linha()
        mapa = {k.lower(): (v if v is not None else "") for k, v in attrs}
        self.tags.append((tag, mapa, linha, self._rotulo))
        for nome, valor in mapa.items():
            self._atributo(tag, nome, valor, linha)
        if tag == "style":
            self._em_estilo = (linha, [])
        elif tag == "script":
            self._em_script = (linha, [])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() == "style":
            self._em_estilo = None
        elif tag.lower() == "script":
            self._em_script = None

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "style" and self._em_estilo is not None:
            self._fechar_estilo()
        elif tag == "script" and self._em_script is not None:
            self._fechar_script()

    def handle_data(self, data):
        if self._em_estilo is not None:
            self._em_estilo[1].append(data)
        elif self._em_script is not None:
            self._em_script[1].append(data)

    def _fechar_estilo(self):
        linha, partes = self._em_estilo
        self._em_estilo = None
        refs, suspeitos = analisar_css("".join(partes))
        for ln, u in refs:
            self.refs.append((linha + ln - 1, self._onde("<style> url() ou @import"), u))
        for ln, t in suspeitos:
            self.suspeitos.append((linha + ln - 1, self._onde("<style> texto"), t))

    def _fechar_script(self):
        linha, partes = self._em_script
        self._em_script = None
        for ln, t in suspeitos_de_js("".join(partes)):
            self.suspeitos.append((linha + ln - 1, self._onde("<script> texto"), t))

    def close(self):
        super().close()
        if self._em_estilo is not None:
            self._fechar_estilo()
        if self._em_script is not None:
            self._fechar_script()


def caminho_normalizado(valor):
    bruto = re.sub(r"[\t\r\n]", "", valor).strip().replace("\\", "/")
    caminho = unquote(re.split(r"[?#]", bruto, maxsplit=1)[0]).replace("\\", "/")
    return "/".join(p for p in caminho.split("/") if p not in ("", "."))


def _conteudo_de_data_uri(bruto):
    cabecalho, _, dados = bruto.partition(",")
    if not DATA_TEXTO_RE.match(cabecalho):
        return ""
    try:
        conteudo = base64.b64decode(unquote(dados), validate=False) if ";base64" in cabecalho.lower() else unquote_to_bytes(dados)
    except (ValueError, TypeError):
        return ""
    return conteudo.decode("utf-8", errors="replace")


def _problema_em_uma_base(valor, base_dir, raiz, prefixos_do_motor):
    bruto = re.sub(r"[\t\r\n]", "", valor).strip()
    if not bruto or bruto.startswith("#"):
        return None
    if re.match(r"(?i)data:", bruto):
        t = trecho_suspeito(_conteudo_de_data_uri(bruto))
        return f"data: com caminho de arquivo dentro ({t[:60]})" if t else None
    if ESQUEMA_RE.match(bruto):
        return f"esquema ou unidade de disco ({bruto[:60]}): so arquivo dentro da pasta da composicao"
    caminho = bruto.replace("\\", "/")
    if caminho.startswith("/"):
        return f"caminho absoluto ou de rede ({bruto[:60]}); copie o arquivo para assets/"
    caminho = re.split(r"[?#]", caminho, maxsplit=1)[0]
    if not caminho:
        return None
    caminho = unquote(caminho).replace("\\", "/")
    if "\x00" in caminho or ":" in caminho or caminho.startswith("/"):
        return f"caminho invalido ({bruto[:60]})"
    partes = caminho.split("/")
    if ".." in partes:
        return f"sobe para fora da pasta ({bruto[:60]}); copie o arquivo para assets/"
    normal = "/".join(p for p in partes if p not in ("", "."))
    if normal.lower().startswith(prefixos_do_motor) and base_dir == raiz:
        return None
    alvo = (base_dir / normal).resolve()
    if alvo == raiz or raiz not in alvo.parents:
        return f"aponta para fora da pasta da composicao ({bruto[:60]}); copie o arquivo para assets/"
    if not alvo.is_file():
        return f"aponta para arquivo que nao existe ({bruto[:60]})"
    return None


def problema_de_referencia(valor, base_dir, raiz, prefixos_do_motor=PREFIXOS_DO_MOTOR, bases_extras=()):
    primeiro = None
    for base in (base_dir, *bases_extras):
        p = _problema_em_uma_base(valor, base, raiz, prefixos_do_motor)
        if p is None:
            return None
        primeiro = primeiro or p
    return primeiro


def _ignorado(p, raiz):
    return bool(PASTAS_IGNORADAS & set(p.relative_to(raiz).parts))


def _links_para_fora(raiz):
    problemas = []
    for p in sorted(raiz.rglob("*")):
        if _ignorado(p, raiz):
            continue
        try:
            real = p.resolve()
        except OSError:
            real = None
        if p.is_symlink() or real is None or (real != raiz and raiz not in real.parents):
            problemas.append(f"{p.relative_to(raiz).as_posix()}: link simbolico ou juncao para fora da pasta da composicao; copie o arquivo de verdade para assets/")
    return problemas


def _varrer_texto(arq, texto):
    sufixo = arq.suffix.lower()
    if sufixo in EXT_CSS:
        refs, suspeitos = analisar_css(texto)
        return ([(ln, "css url() ou @import", u) for ln, u in refs],
                [(ln, "css texto", t) for ln, t in suspeitos], [])
    if sufixo in EXT_JS:
        return [], [(ln, "script texto", t) for ln, t in suspeitos_de_js(texto)], []
    v = _Varredor()
    v.feed(texto)
    v.close()
    return v.refs, v.suspeitos, v.tags


def _alvo_varrivel(valor, bases, raiz):
    normal = caminho_normalizado(valor)
    if not normal:
        return None
    for base in bases:
        alvo = (base / normal).resolve()
        if alvo.is_file() and alvo.suffix.lower() in ARQUIVOS_VARRIDOS and raiz in alvo.parents:
            return alvo
    return None


def checar_composicao(comp_dir):
    comp_dir = Path(comp_dir)
    raiz = comp_dir.resolve()
    problemas = _links_para_fora(raiz)
    audios = 0
    entrada = raiz / "index.html"
    fila = [entrada]
    fila += [p for p in sorted(raiz.rglob("*")) if p.is_file() and p.suffix.lower() in ARQUIVOS_VARRIDOS and not _ignorado(p, raiz)]
    vistos = set()
    while fila:
        arq = fila.pop(0)
        if arq in vistos or not arq.is_file():
            continue
        vistos.add(arq)
        texto = arq.read_text(encoding="utf-8", errors="replace")
        nome = arq.relative_to(raiz).as_posix()
        base = arq.parent
        extras = () if base == raiz else (raiz,)
        referencias, suspeitos, tags = _varrer_texto(arq, texto)
        for ln, onde, valor in referencias:
            if "data-composition-src" in onde:
                p = problema_de_referencia(valor, raiz, raiz)
                bases = (raiz,)
            else:
                p = problema_de_referencia(valor, base, raiz, bases_extras=extras)
                bases = (base, *extras)
            if p:
                problemas.append(f"{nome}:{ln}: {onde} {p}")
                continue
            alvo = _alvo_varrivel(valor, bases, raiz)
            if alvo is not None:
                fila.append(alvo)
        for ln, onde, t in suspeitos:
            problemas.append(f"{nome}:{ln}: {onde} parece caminho de arquivo fora da composicao ({t[:60]}); copie o arquivo para assets/ e use caminho relativo sem ..")
        for tag, attrs, ln, rotulo in tags:
            if tag == "base" and "href" in attrs:
                problemas.append(f"{nome}:{ln}: {rotulo}<base href> muda onde todos os caminhos apontam; remova")
            if tag == "meta" and attrs.get("http-equiv", "").strip().lower() == "refresh":
                problemas.append(f"{nome}:{ln}: {rotulo}<meta http-equiv=refresh> navega a pagina para outro endereco; remova")
            if tag in ("audio", "video"):
                if tag == "audio":
                    audios += 1
                    if not attrs.get("id"):
                        problemas.append(f"{nome}:{ln}: {rotulo}<audio> sem id (o motor nao mistura audio sem id e o video sai mudo)")
                if "crossorigin" in attrs:
                    problemas.append(f"{nome}:{ln}: {rotulo}<{tag}> com crossorigin (o lint do motor recusa)")
    return audios, problemas
