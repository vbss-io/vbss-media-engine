import sys


def titulo(texto):
    print(f"\n== {texto} ==", flush=True)


def linha(status, nome, detalhe=""):
    extra = f" - {detalhe}" if detalhe else ""
    print(f"[{status}] {nome}{extra}", flush=True)


def falhar(mensagem, codigo=1):
    print(f"\nERRO: {mensagem}", file=sys.stderr, flush=True)
    sys.exit(codigo)
