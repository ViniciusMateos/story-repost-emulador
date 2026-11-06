# Story Repost (emulador)

Bot do **Quase Nada Bots** que posta as peças disponíveis do brechó no **story**, pelo app real do
Instagram dentro de um emulador Android (MuMu Player) via `uiautomator2` — no lugar do story pela
API, que o Instagram restringiu ("restricted from uploading").

## Como fica o story

Repost **nativo** do post da peça (o card toca e abre o post, com bordas e título) em cima do
**laranja do brechó**, com a **etiqueta de preço** no canto do card e "COMENTE “FILA” PARA GARANTIR
A SUA!" embaixo. Pelo modo dá pra trocar o fundo pelo que o Instagram gera (bem mais rápido),
tirar a etiqueta, mudar o texto da chamada e pôr uma pausa entre stories.

O vídeo de abertura ("confiram as peças disponíveis") **saiu do bot**: o editor de story do IG no
emulador recodifica o vídeo e usa a imagem da prévia como 1º quadro/capa, lida com o formato de cor
errado — sai destruída pra todo seguidor. Ele é postado na mão.

## Como funciona

1. Escolhe as peças do app do brechó: rodízio por conta (não repete até postar todas) ou, no modo
   **drop**, só as disponíveis do último drop postado, na ordem do `#p`. No modo drop a arte
   **"DROP ON!"** (`assets/abertura_drop.jpg`) sai antes das peças, uma vez por drop em cada conta;
   se ela não sair, a conta para, pra nenhuma peça entrar sem a abertura. Cada conta lembra o que já
   postou daquele drop (`story_mumu_state.json`), e rodar de novo completa só o que faltou.
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
6. **Sticker de foto conferido pela imagem**, não só pelo XML: antes de tocar, espera a miniatura
   da galeria ser desenhada (com as duas instâncias ligadas ela às vezes fica em branco e o toque não
   faz nada); depois de entrar, compara a região do sticker com o print de antes, porque ele pode
   entrar **invisível** (imagem que não carregou), e aí o story sairia sem o preço ou sem a chamada.
   Em branco ou invisível → fecha e reabre a galeria (apaga o invisível), até 3 vezes. Prints das
   falhas em `logs/sticker_falha/`.
7. Ao publicar, responde a janela **"Partilhar em"** (história do Instagram/Facebook) tocando em
   "Partilhar", só no Instagram. Depois vigia alguns segundos pelos avisos que chegam atrasados: o do
   mapa ("Quando mencionas um negócio…", sempre **Agora não**) e o de 1ª vez com "OK" + "Gerir
   definições".
8. **Galeria na ordem certa**: ela ordena pelo `date_added` do índice de fotos, que tem resolução de
   1 s. As imagens entram uma por vez, esperando cada uma ser indexada, senão duas no mesmo segundo
   trocam de lugar.
9. No fim da conta **fecha e abre o Instagram** e vai pro perfil: cada peça abre o post dela por cima
   do anterior, com a folha de compartilhar aberta, e a troca de conta seguinte não achava o seletor.

## Onde roda

Pasta `bots/story_mumu/` da base `quase-nada-bots-device`. Usa `story_card.py`/`etiqueta.py`
(arte da etiqueta e da chamada) e `emulador.py` da base. O story da conta do brechó roda numa
**instância própria do MuMu** (liga só na hora do story e desliga no fim) e pode rodar ao mesmo
tempo que o das outras contas: `usar_serial` vale só pra thread que chamou e o rodízio de peças
tem trava.

```python
from bots.story_mumu import story_mumu as sm
sm.usar_serial("127.0.0.1:16416")
sm.postar_lote(d, "brechoquasenadaa", 10, pasta, fundo="laranja")
```

O IG precisa rodar o editor de story na mesma conexão do `uiautomator2` (reconectar no meio
descarta o rascunho) — por isso o fluxo inteiro roda num processo só.
