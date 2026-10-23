# Story Repost (emulador)

Bot do **Quase Nada Bots** que posta as peças disponíveis do brechó no **story**, pelo app real do
Instagram dentro de um emulador Android (MuMu Player) via `uiautomator2` — no lugar do story pela
API, que o Instagram restringiu ("restricted from uploading").

## Como fica o story

Repost **nativo** do post da peça (o card toca e abre o post, com bordas e título) em cima do
**laranja do brechó**, com a **etiqueta de preço** no canto do card e "COMENTE “FILA” PARA GARANTIR
A SUA!" embaixo. Pelo modo dá pra trocar o fundo pelo que o Instagram gera (bem mais rápido),
tirar a etiqueta, mudar o texto da chamada, pôr uma pausa entre stories e abrir com o **vídeo**
"confiram as peças disponíveis" (`assets/intro.mp4` da base).

## Como funciona

1. Escolhe as peças (rodízio por conta: não repete até postar todas) pelas peças do app do brechó.
2. Abre o post → enviar → "Adicionar à história" → toca no card (estilo com bordas). Se um toque
   cair no "republicar" do feed, ele desfaz ("Anular").
3. Fundo laranja: a chamada entra com um quadrado laranja escondido embaixo, o **conta-gotas** pega
   a cor nele e pinta o fundo. Antes de pintar, confere a cor que o conta-gotas pegou; se não pegar,
   cai no jeito antigo (imagem laranja como sticker, que depois é apagada) e salva as telas em
   `logs/conta_gotas/` pra diagnóstico.
4. Etiqueta e chamada entram como "sticker de foto" (PNG transparente) e são arrastadas pro lugar.
5. **Cada etapa é conferida pelo próprio bot**: galeria com uma imagem por vez, formato de cada
   sticker, cor do fundo, posições. Se algo não bater, descarta e tenta a peça de novo —
   **nada é publicado sem passar na conferência final**.

## Onde roda

Pasta `bots/story_mumu/` da base `quase-nada-bots-device`. Usa `story_card.py`/`etiqueta.py`
(arte da etiqueta e da chamada) e `emulador.py` da base. O story da conta do brechó roda numa
**instância própria do MuMu** (liga só na hora do story e desliga no fim) e pode rodar ao mesmo
tempo que o das outras contas: `usar_serial` vale só pra thread que chamou e o rodízio de peças
tem trava.

```python
from bots.story_mumu import story_mumu as sm
sm.usar_serial("127.0.0.1:16416")
sm.postar_lote(d, "brechoquasenadaa", 10, pasta, fundo="laranja", video_intro=True)
```

O IG precisa rodar o editor de story na mesma conexão do `uiautomator2` (reconectar no meio
descarta o rascunho) — por isso o fluxo inteiro roda num processo só.
