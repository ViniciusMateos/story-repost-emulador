# Changelog

## [1.1.0] — 2026-10-22

### Adicionado
- feat: story do brechó em paralelo com as segue (serial por thread)
- feat: story com modo (fundo laranja ou do IG, preço, chamada, pausa), vídeo de abertura e conta-gotas conferido

### Corrigido
- fix: desfaz o republicar que caía sem querer no feed

### Modificado
- perf: story mais rápido (esperas menores e galeria num shell só)

### Documentação
- docs: README com modo, vídeo de abertura e conta-gotas

## [1.0.0] — 2026-10-20

### Adicionado
- feat: story das peças do brechó pelo app real do Instagram (repost nativo do post, card tocável)
- feat: fundo no laranja do brechó pelo conta-gotas, etiqueta de preço no canto do card e chamada "COMENTE “FILA”"
- feat: conferência em cada etapa (galeria com uma imagem por vez, formato dos stickers, cor do fundo, posições) — nada publica sem passar
- feat: rodízio de peças por conta e lote com até 2 tentativas por peça
- feat: `usar_serial` pra postar numa instância própria do emulador (conta do brechó)
