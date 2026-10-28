# Changelog

## [1.3.0] — 2026-10-27

### Removido
- chore: vídeo de abertura do Story Repost (`postar_intro`, o editor de vídeo e o parâmetro `video_intro` do `postar_lote`) — o IG do emulador usava a prévia do editor como 1º quadro/capa e saía destruída pra todo seguidor; o vídeo é postado na mão

### Documentação
- docs: README sem o vídeo de abertura

## [1.2.0] — 2026-10-24

### Corrigido
- fix: etiqueta com nome único por peça (não reusa o preço do cache do IG) — antes uma conta postava tudo R$ 25
- fix: confere que o post é do brechó (e cita a peça) antes de repostar no story — não reposta o post de um estranho quando o link não abre depois de reiniciar o IG
- fix: vídeo de abertura abre pelo caminho certo e espera a prévia sair do preto (sem a piscada no começo)

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
