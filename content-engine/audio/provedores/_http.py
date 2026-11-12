import urllib.request


class SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    # urllib repassa os cabecalhos (inclusive a chave) para o destino de um redirecionamento.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def instalar():
    urllib.request.install_opener(urllib.request.build_opener(SemRedirecionamento))
