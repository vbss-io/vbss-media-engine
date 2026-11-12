import sys

sys.dont_write_bytecode = True

import _comum as c


def main():
    print("Preparando o motor de imagem local do vbss-media-engine.")
    print("Rede usada: so o download unico do navegador fixo, com SHA-256 conferido. Nada e instalado fora de content-engine/.")
    if sys.version_info < (3, 10):
        c.falhar("precisa de Python 3.10 ou mais novo.")
    c.navegador_fixado.instalar(c.linha, c.titulo, c.falhar)
    chrome = c.find_chrome()
    if not c.e_navegador_fixo(chrome):
        c.linha("AVISO", "o render vai usar outro navegador", c.descrever_navegador(chrome))
    print("\nPronto. Agora rode: python content-engine/image/doctor.py")


if __name__ == "__main__":
    main()
