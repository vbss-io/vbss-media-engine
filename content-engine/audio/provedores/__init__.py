import importlib

DISPONIVEIS = ("voicestudio", "kokoro", "azure", "azure_openai", "google")


class ProvedorIndisponivel(RuntimeError):
    pass


def carregar(nome):
    if nome not in DISPONIVEIS:
        raise ValueError(f"provedor '{nome}' desconhecido (use {', '.join(DISPONIVEIS)})")
    try:
        return importlib.import_module(f"provedores.{nome}")
    except Exception as err:
        raise ProvedorIndisponivel(
            f"o adaptador do provedor '{nome}' nao carregou ({type(err).__name__}: {err}); "
            f"so ele fica desligado, os outros provedores seguem funcionando. Confira content-engine/audio/provedores/{nome}.py"
        ) from err


def tentar_carregar(nome):
    try:
        return carregar(nome), None
    except ProvedorIndisponivel as err:
        return None, str(err)


def variantes_de(nome):
    prov = carregar(nome)
    gancho = getattr(prov, "variantes", None)
    if gancho is None:
        return ()
    try:
        return tuple(gancho())
    except Exception as err:
        raise ProvedorIndisponivel(f"o provedor '{nome}' nao conseguiu listar as variantes de modelo ({type(err).__name__}: {err})") from err


def filtrar_opcoes(prov, opcoes):
    pedidas = {k: v for k, v in (opcoes or {}).items() if v not in (None, "", [])}
    aceitas = getattr(prov, "OPCOES_ACEITAS", ())
    rejeitadas = sorted(k for k in pedidas if k not in aceitas)
    return {k: v for k, v in pedidas.items() if k in aceitas}, rejeitadas


def sintetizar(prov, linhas, voz, pasta, velocidade=1.0, variante=None, opcoes=None):
    validas, _ = filtrar_opcoes(prov, opcoes)
    extra = {"opcoes": validas} if getattr(prov, "OPCOES_ACEITAS", ()) else {}
    return prov.sintetizar(linhas, voz, pasta, velocidade=velocidade, variante=variante, **extra)
