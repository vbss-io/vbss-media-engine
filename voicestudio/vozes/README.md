# Vozes do VoiceStudio

Esta pasta nasce vazia: o repo não traz nenhuma voz. Cada voz guardada aqui é um WAV de referência mais uma entrada em `vozes.json` (texto falado, origem e data), e cada máquina recria o perfil dela ao subir a API.

Antes: `python voicestudio/voicestudio.py instalar` e `python voicestudio/voicestudio.py modelos`.

## Criar uma voz por atributos (design)

```bash
python voicestudio/voicestudio.py voz --genero feminina --idade jovem --tom medio --seed 7
python voicestudio/voicestudio.py voz --genero feminina --idade jovem --tom medio --seed 7 --salvar narradora
```

O primeiro comando gera uma amostra para ouvir; cada `--seed` é uma pessoa diferente com os mesmos atributos. O segundo guarda a amostra aprovada com o nome escolhido.

## Clonar a partir de uma gravação

```bash
python voicestudio/voicestudio.py subir
python voicestudio/voicestudio.py clonar --audio <gravacao.wav> --texto "exatamente o que foi falado" --nome narradora --guardar
python voicestudio/voicestudio.py parar
```

Gravação de 3 a 20 segundos (ideal 8 a 12). Só clone a voz de quem autorizou.

## Usar

```bash
python voicestudio/voicestudio.py voz --listar
python content-engine/audio/voz.py <voz.txt> --saida <pasta> --provedor voicestudio --voz narradora
```

Para virar a voz padrão: `VOZ_PROVEDOR=voicestudio` e `VOZ_VOICESTUDIO=narradora` em `content-engine/audio/.env`.

Os pesos do modelo OmniVoice são CC-BY-NC: uso comercial da voz gerada não é permitido.
