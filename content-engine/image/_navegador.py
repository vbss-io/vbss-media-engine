import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import time
from pathlib import Path

import _comum as c

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

FLAGS_BASE = (
    "--headless=new",
    "--remote-debugging-port=0",
    "--hide-scrollbars",
    "--mute-audio",
    "--force-device-scale-factor=1",
    "--disable-breakpad",
    "--disable-crash-reporter",
    "--disable-extensions",
    "--disable-default-apps",
    "--disable-field-trial-config",
    "--disable-search-engine-choice-screen",
    "--no-service-autorun",
    "--password-store=basic",
)

JS_PRONTO = r"""
(async () => {
  const limite = new Promise((r) => setTimeout(() => r('tempo esgotado'), %d));
  const pronto = (async () => {
    await Promise.allSettled([...document.fonts].map((f) => f.load()));
    await document.fonts.ready;
    const imgs = [...document.images];
    await Promise.all(imgs.map((i) => i.complete ? null : new Promise((r) => {
      i.addEventListener('load', r, { once: true });
      i.addEventListener('error', r, { once: true });
    })));
    await Promise.allSettled(imgs.map((i) => (i.decode ? i.decode() : null)));
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return 'ok';
  })();
  const estado = await Promise.race([pronto, limite]);
  const faces = [...document.fonts].map((f) => ({ familia: f.family.replace(/["']/g, ''), peso: String(f.weight), status: f.status }));
  const quebradas = [...document.images].filter((i) => !i.naturalWidth).map((i) => i.getAttribute('src') || '(sem src)');
  const W = innerWidth, H = innerHeight;
  const fora = [];
  for (const el of document.body ? document.body.querySelectorAll('*') : []) {
    const temTexto = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!temTexto) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.right > W + 1 || r.bottom > H + 1 || r.left < -1 || r.top < -1) {
      fora.push(el.textContent.trim().replace(/\s+/g, ' ').slice(0, 60));
    }
  }
  return { estado, faces, quebradas, fora: fora.slice(0, 5), largura: W, altura: H };
})()
"""


class WebSocket:
    def __init__(self, host, porta, caminho, timeout=30):
        self.sock = socket.create_connection((host, porta), timeout=timeout)
        chave = base64.b64encode(os.urandom(16)).decode()
        pedido = (
            f"GET {caminho} HTTP/1.1\r\nHost: {host}:{porta}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {chave}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(pedido.encode("ascii"))
        self.buf = bytearray()
        while b"\r\n\r\n" not in self.buf:
            bloco = self.sock.recv(4096)
            if not bloco:
                raise ConnectionError("o Chrome fechou a conexao do DevTools no handshake")
            self.buf += bloco
        fim = self.buf.index(b"\r\n\r\n") + 4
        cabecalho = bytes(self.buf[:fim]).decode("latin-1")
        del self.buf[:fim]
        esperado = base64.b64encode(hashlib.sha1((chave + WS_GUID).encode()).digest()).decode()
        if " 101 " not in cabecalho.split("\r\n", 1)[0] or esperado not in cabecalho:
            raise ConnectionError(f"handshake do DevTools recusado: {cabecalho.splitlines()[0]}")

    def _ler(self, n):
        while len(self.buf) < n:
            bloco = self.sock.recv(max(65536, n - len(self.buf)))
            if not bloco:
                raise ConnectionError("conexao do DevTools fechada")
            self.buf += bloco
        dados = bytes(self.buf[:n])
        del self.buf[:n]
        return dados

    def _frame(self, opcode, payload):
        n = len(payload)
        if n < 126:
            cab = struct.pack(">BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            cab = struct.pack(">BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            cab = struct.pack(">BBQ", 0x80 | opcode, 0x80 | 127, n)
        mascara = os.urandom(4)
        if n:
            rep = (mascara * (n // 4 + 1))[:n]
            payload = (int.from_bytes(payload, "big") ^ int.from_bytes(rep, "big")).to_bytes(n, "big")
        self.sock.sendall(cab + mascara + payload)

    def enviar(self, texto):
        self._frame(0x1, texto.encode("utf-8"))

    def receber(self):
        partes = []
        while True:
            b1, b2 = self._ler(2)
            opcode, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._ler(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._ler(8))[0]
            mascara = self._ler(4) if b2 & 0x80 else None
            dados = self._ler(n)
            if mascara:
                rep = (mascara * (n // 4 + 1))[:n]
                dados = (int.from_bytes(dados, "big") ^ int.from_bytes(rep, "big")).to_bytes(n, "big")
            if opcode == 0x9:
                self._frame(0xA, dados)
                continue
            if opcode == 0x8:
                raise ConnectionError("o Chrome encerrou a conexao do DevTools")
            if opcode in (0x0, 0x1, 0x2):
                partes.append(dados)
                if b1 & 0x80:
                    return b"".join(partes).decode("utf-8")

    def fechar(self):
        try:
            self.sock.close()
        except OSError:
            pass


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.n = 0
        self.eventos = []
        self.ao_evento = None
        self.disparados = set()
        self.erros_disparo = []

    def _proxima(self, limite):
        restante = limite - time.monotonic()
        if restante <= 0:
            raise TimeoutError
        self.ws.sock.settimeout(restante)
        try:
            m = json.loads(self.ws.receber())
        except socket.timeout:
            raise TimeoutError from None
        if m.get("id") in self.disparados:
            self.disparados.discard(m["id"])
            if "error" in m:
                self.erros_disparo.append(m["error"].get("message", ""))
            return None
        if "method" in m and self.ao_evento and self.ao_evento(m):
            return None
        return m

    def disparar(self, metodo, params=None, sessao=None):
        self.n += 1
        msg = {"id": self.n, "method": metodo, "params": params or {}}
        if sessao:
            msg["sessionId"] = sessao
        self.disparados.add(self.n)
        self.ws.enviar(json.dumps(msg))

    def enviar(self, metodo, params=None, sessao=None, timeout=30):
        self.n += 1
        ident = self.n
        msg = {"id": ident, "method": metodo, "params": params or {}}
        if sessao:
            msg["sessionId"] = sessao
        self.ws.enviar(json.dumps(msg))
        limite = time.monotonic() + timeout
        while True:
            try:
                m = self._proxima(limite)
            except TimeoutError:
                raise TimeoutError(f"o Chrome nao respondeu a {metodo} em {timeout}s") from None
            if m is None:
                continue
            if m.get("id") == ident:
                if "error" in m:
                    raise RuntimeError(f"{metodo}: {m['error'].get('message')}")
                return m.get("result", {})
            if "method" in m:
                self.eventos.append(m)

    def esperar(self, metodo, sessao, timeout):
        limite = time.monotonic() + timeout
        while True:
            for i, ev in enumerate(self.eventos):
                if ev.get("method") == metodo and ev.get("sessionId") == sessao:
                    return self.eventos.pop(i)
            try:
                m = self._proxima(limite)
            except TimeoutError:
                raise TimeoutError(f"a pagina nao terminou de carregar em {timeout}s ({metodo})") from None
            if m is not None and "method" in m:
                self.eventos.append(m)

    def tirar_eventos(self, sessao):
        meus = [e for e in self.eventos if e.get("sessionId") == sessao]
        self.eventos = [e for e in self.eventos if e.get("sessionId") != sessao]
        return meus


def argumentos(chrome, perfil):
    return [str(chrome), *FLAGS_BASE, f"--user-data-dir={perfil}", *c.flags_chrome(), "about:blank"]


class Navegador:
    def __init__(self, timeout_inicio=40):
        self.chrome = c.find_chrome()
        if not self.chrome:
            c.falhar("nenhum navegador encontrado. Rode python content-engine/image/setup.py (instala o navegador fixo)")
        paths = c.sandbox_paths()
        self.perfil = paths["perfis"] / f"{os.getpid()}-{int(time.time() * 1000)}"
        self.perfil.mkdir(parents=True, exist_ok=True)
        self.env = c.sandbox_env()
        problemas = c.assert_env_isolated(self.env)
        if problemas:
            c.falhar("ambiente do Chrome nao esta isolado: " + "; ".join(problemas))
        self.args = argumentos(self.chrome, self.perfil)
        faltam = c.flags_faltando(self.args)
        if faltam:
            c.falhar("flags de isolamento do Chrome incompletas: " + ", ".join(faltam))
        self.log = open(c.SANDBOX_DIR / "chrome.log", "ab")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.proc = subprocess.Popen(self.args, env=self.env, cwd=str(paths["cwd"]), stdin=subprocess.DEVNULL,
                                     stdout=self.log, stderr=self.log, creationflags=flags)
        porta_arq = self.perfil / "DevToolsActivePort"
        limite = time.monotonic() + timeout_inicio
        while True:
            if self.proc.poll() is not None:
                self._limpar()
                c.falhar(f"o Chrome fechou ao abrir (codigo {self.proc.returncode}). Veja {c.SANDBOX_DIR / 'chrome.log'}")
            if porta_arq.is_file():
                linhas = porta_arq.read_text(encoding="ascii", errors="replace").split()
                if len(linhas) >= 2:
                    break
            if time.monotonic() > limite:
                self.fechar()
                c.falhar(f"o Chrome nao abriu o DevTools em {timeout_inicio}s")
            time.sleep(0.05)
        self.porta = int(linhas[0])
        self.cdp = CDP(WebSocket("127.0.0.1", self.porta, linhas[1]))
        self.versao = self.cdp.enviar("Browser.getVersion").get("product", "")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.fechar()

    def _abrir(self, servidor, largura, altura, bloqueados):
        alvo = self.cdp.enviar("Target.createTarget", {"url": "about:blank"})["targetId"]
        sessao = self.cdp.enviar("Target.attachToTarget", {"targetId": alvo, "flatten": True})["sessionId"]

        def interceptar(ev):
            if ev.get("method") != "Fetch.requestPaused" or ev.get("sessionId") != sessao:
                return False
            p = ev["params"]
            url = p["request"]["url"]
            if servidor.nosso(url):
                status, tipo, corpo = servidor.responder(url)
                self.cdp.disparar("Fetch.fulfillRequest", {
                    "requestId": p["requestId"],
                    "responseCode": status,
                    "responseHeaders": [{"name": "Content-Type", "value": tipo}, {"name": "Cache-Control", "value": "no-store"}],
                    "body": base64.b64encode(corpo).decode("ascii"),
                }, sessao)
            else:
                bloqueados.append(url)
                self.cdp.disparar("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"}, sessao)
            return True

        self.cdp.ao_evento = interceptar
        for metodo, params in (
            ("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]}),
            ("Page.enable", {}),
            ("Network.enable", {}),
            ("Network.setCacheDisabled", {"cacheDisabled": True}),
            ("Emulation.setDeviceMetricsOverride", {"width": largura, "height": altura, "deviceScaleFactor": 1, "mobile": False}),
        ):
            self.cdp.enviar(metodo, params, sessao)
        return alvo, sessao

    def _fechar_aba(self, alvo, sessao):
        eventos = self.cdp.tirar_eventos(sessao)
        try:
            self.cdp.enviar("Target.closeTarget", {"targetId": alvo})
        except (RuntimeError, TimeoutError, ConnectionError):
            pass
        self.cdp.ao_evento = None
        return eventos

    def _navegar(self, url, sessao, timeout):
        nav = self.cdp.enviar("Page.navigate", {"url": url}, sessao)
        if nav.get("errorText"):
            raise RuntimeError(f"nao abriu {url}: {nav['errorText']}")
        self.cdp.esperar("Page.loadEventFired", sessao, timeout)

    def capturar(self, servidor, html, largura, altura, destino, timeout=45):
        bloqueados = []
        alvo, sessao = self._abrir(servidor, largura, altura, bloqueados)
        try:
            self._navegar(servidor.url_de(html), sessao, timeout)
            r = self.cdp.enviar("Runtime.evaluate", {
                "expression": JS_PRONTO % ((timeout - 5) * 1000),
                "awaitPromise": True,
                "returnByValue": True,
            }, sessao, timeout=timeout)
            info = r.get("result", {}).get("value") or {}
            shot = self.cdp.enviar("Page.captureScreenshot", {"format": "png", "fromSurface": True, "captureBeyondViewport": False}, sessao, timeout=60)
            Path(destino).parent.mkdir(parents=True, exist_ok=True)
            Path(destino).write_bytes(base64.b64decode(shot["data"]))
        finally:
            eventos = self._fechar_aba(alvo, sessao)
        urls = {}
        for ev in eventos:
            if ev["method"] == "Network.requestWillBeSent":
                p = ev.get("params", {})
                urls[p.get("requestId")] = p.get("request", {}).get("url", "")
        info["bloqueados"] = list(dict.fromkeys(bloqueados))
        info["externos"] = [u for u in info["bloqueados"] if not c.url_local(u)]
        info["pedidos"] = len(urls)
        return info

    def avaliar(self, servidor, html, expressao, largura=200, altura=100, timeout=30):
        bloqueados = []
        alvo, sessao = self._abrir(servidor, largura, altura, bloqueados)
        try:
            self._navegar(servidor.url_de(html), sessao, timeout)
            r = self.cdp.enviar("Runtime.evaluate", {"expression": expressao, "awaitPromise": True, "returnByValue": True}, sessao, timeout=timeout)
            return r.get("result", {}).get("value"), bloqueados
        finally:
            self._fechar_aba(alvo, sessao)

    def fechar(self):
        cdp = getattr(self, "cdp", None)
        if cdp:
            try:
                cdp.enviar("Browser.close", timeout=10)
            except (RuntimeError, TimeoutError, ConnectionError, OSError):
                pass
            cdp.ws.fechar()
            self.cdp = None
        if self.proc.poll() is None:
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
                else:
                    self.proc.kill()
                self.proc.wait(timeout=15)
        self._limpar()

    def _limpar(self):
        try:
            self.log.close()
        except OSError:
            pass
        for _ in range(20):
            shutil.rmtree(self.perfil, ignore_errors=True)
            if not self.perfil.exists():
                break
            time.sleep(0.25)
