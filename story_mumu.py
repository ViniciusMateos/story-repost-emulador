"""Story das contas VITRINE no MuMu Player (o LDPlayer não renderiza o editor de story — fica preto).

Fluxo EM USO (opção B, aprovada pelo Vinicius 19/10/2026 — postar_repost/postar_lote, no fim do
arquivo): repost NATIVO do post do brechó (card tocável → abre o post; um toque deixa o estilo com
bordas e título) + fundo laranja do brechó (conta-gotas numa imagem laranja que depois é apagada) +
a NOSSA etiqueta de preço no canto do card + "COMENTE 'FILA' PARA GARANTIR A SUA!" embaixo. Cada
etapa é CONFERIDA pelo próprio bot (galeria com uma imagem por vez, formato do sticker, cor do
fundo, posições) e nada é publicado sem passar na conferência final.
A opção A (card pronto + sticker de link) ficou no começo do arquivo, mas foi REJEITADA.

IMPORTANTE: o fluxo TEM que rodar num processo só — reconectar o u2 no meio tira o IG do primeiro
plano e o editor DESCARTA o rascunho. Serial/adb vêm de emulador.py (MuMu = 127.0.0.1:16384).
"""
import os
import random
import re
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import emulador  # noqa: E402

ADB = emulador.ADB
# instância por THREAD: o story do brechó (instância dele) pode rodar ao mesmo tempo que o das segue
_local = threading.local()
_trava_estado = threading.RLock()


def _serial():
    return getattr(_local, "serial", None) or emulador.SERIAL


def usar_serial(serial):
    """Aponta os comandos adb (galeria, prints) DESTA thread pra outra instância — o story do
    BRECHÓ roda na instância só dele (emulador.SERIAL_BRECHO). Chame de volta com emulador.SERIAL."""
    _local.serial = serial


PASTA = "/sdcard/Pictures/QuaseNada"
R = "com.instagram.android:id/"
CTA_PADRAO = "VER PEÇA"


def _log(log, msg):
    if log:
        log(msg)


def _sleep(a, b):
    time.sleep(random.uniform(a, b))


def _adb(*args, timeout=60):
    return subprocess.run([ADB, "-s", _serial(), *args], capture_output=True, text=True, timeout=timeout)


def _centro(b):
    return (b["left"] + b["right"]) // 2, (b["top"] + b["bottom"]) // 2


def _tocar(d, sel, timeout=8):
    """Toca pelo CENTRO das bounds (o editor re-renderiza e o click do objeto dá StaleObject)."""
    if not sel.wait(timeout=timeout):
        return False
    try:
        d.click(*_centro(sel.info["bounds"]))
        return True
    except Exception:
        return False


def enviar_para_galeria(card_path, nome):
    """Limpa a pasta do bot na galeria e manda o card novo (assim ele é a 1ª miniatura)."""
    _limpar_indice()
    destino = f"{PASTA}/{nome}"
    _adb("push", card_path, destino)
    _adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
         "-d", f"file://{destino}")
    for _ in range(10):
        r = _adb("shell", "content", "query", "--uri", "content://media/external/images/media",
                 "--projection", "_display_name")
        if nome in (r.stdout or ""):
            return True
        time.sleep(1)
    return False


def limpar_galeria():
    _limpar_indice()


def _fechar_telas_extras(d, log=None):
    """Telas que o IG joga no meio (1º uso no aparelho: contatos, notificações…)."""
    for _ in range(3):
        for t in ("Ignorar", "Agora não", "Não permitir", "Agora nao"):
            if d(text=t).exists:
                _log(log, f"  tela extra do IG — '{t}'")
                _tocar(d, d(text=t), 2)
                _sleep(1.5, 2.5)
                break
        else:
            return


def desfazer_republicar(d, log=None):
    """Aviso "Republicaste a publicação de …" na tela = um toque caiu no botão de REPUBLICAR (no feed
    da conta), não no de compartilhar no story. Toca em "Anular" (desfaz) e devolve True. Aconteceu na
    segue8 em 22/10: o aviso ficou por cima e travou as 3 peças seguintes ("o post não abriu")."""
    try:
        if d(textContains="Republicaste a publica").exists or d(textContains="You reposted").exists:
            for t in ("Anular", "Undo", "Desfazer"):
                b = d(text=t)
                if b.exists:
                    b.click()
                    _log(log, "  republicar no feed caiu sem querer — desfeito (Anular)")
                    _sleep(1.0, 1.5)
                    return True
    except Exception:
        pass
    return False


def descartar_rascunho(d):
    """Sai de folha de link / editor / câmera que tenha ficado aberta, descartando o rascunho
    (apertar 'voltar' às cegas no meio disso deixava a câmera fechando e o toque caía errado)."""
    for _ in range(6):
        if d(resourceId=R + "link_sticker_list_done_button").exists:
            d.press("back")
        elif d(resourceId=R + "quick_capture_root_container").exists or \
                d(resourceId=R + "gallery_cancel_button").exists:
            sel = d(resourceId=R + "cancel_button")
            if not sel.exists:
                sel = d(resourceId=R + "gallery_cancel_button")
            if not sel.exists:
                sel = d(resourceId=R + "camera_home_button")
            if sel.exists:
                _tocar(d, sel, 2)
            else:
                d.press("back")
        else:
            for t in ("Descartar", "Rejeitar", "Eliminar"):
                if d(text=t).exists:
                    _tocar(d, d(text=t), 2)
                    break
            else:
                return
        _sleep(1.2, 1.8)
        for t in ("Descartar", "Rejeitar", "Eliminar"):
            if d(text=t).exists:
                _tocar(d, d(text=t), 2)
                _sleep(1.0, 1.5)
                break


def _abrir_galeria_pelo_perfil(d, log=None):
    """Caminho SEM câmera: Perfil → '+' no avatar ('Adicionar à história') → galeria do story.
    A câmera do IG no MuMu às vezes falha ao iniciar e o IG volta pro perfil sozinho."""
    for _ in range(5):
        if d(resourceId=R + "profile_tab").exists:
            break
        d.press("back")
        _sleep(1.0, 1.6)
    if not _tocar(d, d(resourceId=R + "profile_tab"), 5):
        return False
    _sleep(2.0, 3.0)
    return _tocar(d, d(resourceId=R + "reel_empty_badge"), 6)


def _abrir_galeria_pelo_criar(d, log=None):
    """Reserva: Criar (câmera) → HISTÓRIA → botão Galeria."""
    if not _tocar(d, d(resourceId=R + "creation_tab"), 5):
        return False
    # o Criar já abre no modo HISTÓRIA; tocar em "HISTÓRIA" de novo trocava o modo
    if not d(resourceId=R + "gallery_preview_button").wait(timeout=8):
        sel = d(resourceId=R + "cam_dest_story")
        if not sel.exists:
            sel = d(text="HISTÓRIA")
        _tocar(d, sel, 3)
        _sleep(1.5, 2.2)
    return _tocar(d, d(resourceId=R + "gallery_preview_button"), 8)


def abrir_editor_com_card(d, log=None, shot=None):
    """Abre a galeria do story (pelo '+' do avatar; reserva = Criar) e escolhe a 1ª miniatura (o
    card recém-enviado). Até 2 tentativas por caminho. True se o editor abriu."""
    for tentativa, caminho in enumerate((_abrir_galeria_pelo_perfil, _abrir_galeria_pelo_criar,
                                         _abrir_galeria_pelo_perfil)):
        _fechar_telas_extras(d, log)
        descartar_rascunho(d)
        if not caminho(d, log):
            continue
        if not _tocar(d, d(resourceId=R + "gallery_grid_item_thumbnail"), 10):
            _log(log, f"  galeria não abriu (tentativa {tentativa + 1})")
            if shot:
                shot(f"falha_galeria_{tentativa + 1}")
            continue
        if d(resourceId=R + "your_story_share_shortcut_button").wait(timeout=15):
            return True
    return False


def adicionar_link(d, url, cta=CTA_PADRAO, log=None, shot=None):
    """Sticker de ligação com a URL do post e texto personalizado. True se entrou no story."""
    # abre a bandeja de stickers (o editor ainda pode estar montando → confere e repete)
    for _ in range(3):
        _sleep(1.5, 2.2)
        st = d(resourceId=R + "asset_button")
        if st.exists:
            _tocar(d, st, 3)
        else:
            d.click(849, 129)   # posição do botão Stickers na barra lateral do editor
        if d(description="Sticker de ligação").wait(timeout=6):
            break
        if d(resourceId=R + "row_search_edit_text").exists:   # bandeja aberta, link mais abaixo
            d.swipe(450, 1200, 450, 700, 0.3)
            if d(description="Sticker de ligação").wait(timeout=3):
                break
            d.press("back")
    if not _tocar(d, d(description="Sticker de ligação"), 3):
        _log(log, "  não achei o sticker de link")
        if shot:
            shot("falha_sticker")
        return False
    url_ed = d(resourceId=R + "link_sticker_list_web_url_edit_text")
    if not url_ed.wait(timeout=10):
        return False
    url_ed.set_text(url)
    _sleep(0.8, 1.2)
    if cta:
        # "Personalizar texto do sticker" abre um 2º EditText (o de baixo). Tocar antes da folha
        # carregar não abria nada e o CTA ficava de fora ("INSTAGRAM.COM") → espera os 2 campos.
        eds = d(className="android.widget.EditText")
        for _ in range(3):
            _tocar(d, d(resourceId=R + "link_sticker_custom_cta_row_title"), 5)
            for _ in range(10):
                if eds.count >= 2:
                    break
                time.sleep(0.5)
            if eds.count >= 2:
                break
        campos = sorted((eds[i] for i in range(eds.count)), key=lambda e: e.info["bounds"]["top"])
        if len(campos) >= 2:
            campos[-1].set_text(cta)
            _sleep(0.6, 1.0)
        else:
            _log(log, "  não abriu o campo do texto do sticker — vai com o texto padrão do IG")
    try:
        eds = d(className="android.widget.EditText")
        topo = min((eds[i] for i in range(eds.count)), key=lambda e: e.info["bounds"]["top"])
        ok_url = "instagram.com/p/" in (topo.get_text() or "")
    except Exception:
        ok_url = False
    if not ok_url:
        _log(log, "  a URL do link não ficou no campo certo — desisto deste story")
        return False
    if not _tocar(d, d(resourceId=R + "link_sticker_list_done_button"), 5):
        return False
    _sleep(2.0, 3.0)
    # se o Concluído não fechou a folha (URL recusada), não segue
    return not d(resourceId=R + "link_sticker_list_done_button").exists


def _bounds_sticker(d):
    """Bounds do sticker de link no editor (content-desc 'Sticker. Pressiona para reposicionar…',
    pequeno — o card/fundo são enormes). None se não achou."""
    try:
        W, H = d.window_size()
    except Exception:
        W, H = 900, 1600
    melhor = None
    for m in re.finditer(r"<node[^>]*/?>", d.dump_hierarchy()):
        t = m.group(0)
        desc = (re.search(r'content-desc="([^"]*)"', t) or [0, ""])[1]
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
        if not b or not desc.startswith("Sticker"):
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        if (y2 - y1) < H * 0.15 and (x2 - x1) < W * 0.8:
            melhor = (x1, y1, x2, y2)
    return melhor


def posicionar_sticker(d, y_destino, log=None):
    """Arrasta o sticker de link até y_destino (centro). Arrasto LENTO (o drag rápido o IG ignora)
    e em ciclo: mede onde parou e corrige (o IG não acompanha o dedo 1:1). Até 4 ajustes."""
    try:
        W, _H = d.window_size()
    except Exception:
        W = 900
    for _ in range(4):
        b = _bounds_sticker(d)
        if not b:
            _log(log, "  não localizei o sticker pra posicionar")
            return False
        cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
        if abs(cy - y_destino) < 18 and abs(cx - W // 2) < 30:
            return True
        # o IG anda ~80% do arrasto → compensa pra não ficar sempre aquém
        alvo_y = cy + (y_destino - cy) / 0.8
        alvo_x = cx + (W // 2 - cx) / 0.8
        d.swipe(cx, cy, int(alvo_x), int(alvo_y), 1.2)
        _sleep(1.2, 1.8)
    return _bounds_sticker(d) is not None


def publicar(d, log=None):
    """Toca 'A tua história' e espera sair do editor. True se saiu."""
    if not _tocar(d, d(resourceId=R + "your_story_share_shortcut_button"), 8):
        return False
    for _ in range(30):
        _sleep(0.6, 0.8)
        if not d(resourceId=R + "quick_capture_root_container").exists:
            _fechar_telas_extras(d, log)
            return True
    return False


def postar_card(d, card_path, code, log=None, cta=CTA_PADRAO, enviar=True, shot=None):
    """Posta UM card como story com link pro post `code`. enviar=False para antes de publicar
    (e descarta). `shot(nome)` opcional pra salvar print de conferência. Devolve 'ok'|motivo."""
    nome = f"qn_{code}.jpg"
    if not enviar_para_galeria(card_path, nome):
        return "galeria"
    if not abrir_editor_com_card(d, log, shot):
        return "editor"
    if not adicionar_link(d, f"https://www.instagram.com/p/{code}/", cta, log, shot):
        return "link"
    # vão entre o fim do card e o "COMENTE FILA" (card 1080x1920 → tela 900x1600: ~79% da altura)
    try:
        _W, H = d.window_size()
    except Exception:
        H = 1600
    posicionar_sticker(d, H * 0.79, log)
    if shot:
        shot("story_antes_de_publicar")
    if not enviar:
        _tocar(d, d(resourceId=R + "cancel_button"), 3)
        _sleep(1.0, 1.5)
        for t in ("Descartar", "Rejeitar", "Eliminar"):
            if d(text=t).exists:
                _tocar(d, d(text=t), 2)
                break
        limpar_galeria()
        return "simulado"
    ok = publicar(d, log)
    limpar_galeria()
    return "ok" if ok else "publicar"


# ═══════════════ OPÇÃO B: repost NATIVO do post + personalização nossa ═══════════════
# (aprovada pelo Vinicius 19/10: card nativo do IG, tocável → abre o post; fundo laranja; etiqueta de
# preço e "COMENTE 'FILA'" com a NOSSA arte por cima, como "Sticker de foto" — o IG mantém a
# transparência do PNG). Fundo laranja = ferramenta Desenhar + segurar o dedo no fundo (pinta a tela
# toda; stickers ficam por cima). O "Segundo plano" do IG NÃO tem laranja liso (o que parecia laranja
# era um degradê arco-íris).
COR_BRECHO = (255, 130, 52)
STICKERS = ("Sticker. Pressiona",)


CHAMADA_PADRAO = ["COMENTE “FILA” PARA", "GARANTIR A SUA!"]


def _linhas_chamada(chamada):
    """Texto da chamada do modo → linhas em MAIÚSCULAS (até 3, ~20 letras cada). Vazio = padrão."""
    import textwrap
    t = " ".join(str(chamada or "").split())
    if not t:
        return list(CHAMADA_PADRAO)
    return textwrap.wrap(t.upper(), 20)[:3] or list(CHAMADA_PADRAO)


LUPA_ABAIXO_DO_DEDO = 43   # px: o conta-gotas lê a cor no circulinho abaixo da gota, não no dedo


def gerar_stickers(peca, pasta, mostrar_preco=True, chamada="", bloco=False):
    """PNGs transparentes da etiqueta (preço/tamanho, inclinada) e do CTA, na arte do story_card.
    O CTA ganha margem transparente: o sticker de foto recorta imagem muito larga (5:1 cortava).
    `mostrar_preco=False` → sem etiqueta; `chamada` = texto do modo (vazio = o padrão).
    `bloco=True` → um QUADRADO LARANJA na faixa transparente de baixo da chamada: o conta-gotas pega
    a cor nele e, com o fundo pintado da mesma cor, ele some. Devolve (tag, cta, bloco_rel) —
    bloco_rel = centro do quadrado em fração da imagem (ou None)."""
    import etiqueta
    import story_card as sc
    from PIL import Image, ImageDraw
    os.makedirs(pasta, exist_ok=True)
    # NOME ÚNICO por peça (24/10/2026): com o mesmo "qn_tag.png" toda vez, o IG reaproveitava a
    # imagem do cache e as etiquetas da conta saíam com o preço da 1ª peça (uma conta postou tudo
    # a R$ 25). Apaga as velhas da pasta pra não acumular.
    for velho in os.listdir(pasta):
        if velho.startswith(("qn_tag", "qn_cta")) and velho.endswith(".png"):
            try:
                os.remove(os.path.join(pasta, velho))
            except Exception:
                pass
    sufixo = f"{peca.get('num') or peca.get('code') or 'x'}_{int(time.time() * 1000)}"
    linhas = etiqueta.linhas(peca, peca.get("template") or peca.get("observacao") or "")
    tag_path = None
    if linhas and mostrar_preco:
        tag = sc._etiqueta(linhas)
        tag_path = os.path.join(pasta, f"qn_tag_{sufixo}.png")
        tag.save(tag_path)
    f = sc._fonte_mao(68)
    W = 1080
    textos = _linhas_chamada(chamada)
    alt = f.size + 18
    im = Image.new("RGBA", (W, alt * len(textos) + 40), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for i, t in enumerate(textos):
        sc._linha_mao(dr, W / 2, 20 + alt * i + alt / 2, t, f)
    im = im.crop(im.getbbox())
    # margem transparente até ~1,5:1 (proporção que o sticker de foto mostra inteira); com o
    # quadrado, garante uma faixa de baixo de pelo menos 35% da altura do texto (texto centrado)
    alvo_h = int(im.width / 1.5)
    if bloco:
        alvo_h = max(alvo_h, int(im.height * 1.7))
    bloco_rel = None
    if alvo_h > im.height:
        fundo = Image.new("RGBA", (im.width, alvo_h), (0, 0, 0, 0))
        topo = (alvo_h - im.height) // 2
        fundo.paste(im, (0, topo), im)
        if bloco:
            faixa = alvo_h - (topo + im.height)            # faixa transparente de baixo
            bw, bh = int(im.width * 0.2), int(faixa * 0.7)
            x0, y0 = (im.width - bw) // 2, topo + im.height + (faixa - bh) // 2
            ImageDraw.Draw(fundo).rectangle([x0, y0, x0 + bw, y0 + bh], fill=COR_BRECHO + (255,))
            bloco_rel = ((x0 + bw / 2) / im.width, (y0 + bh / 2) / alvo_h)
        im = fundo
    cta_path = os.path.join(pasta, f"qn_cta_{sufixo}.png")   # nome único (mesmo motivo da etiqueta)
    im.save(cta_path)
    return tag_path, cta_path, bloco_rel


def _adb_bytes(*args):
    return subprocess.run([ADB, "-s", _serial(), *args], capture_output=True, timeout=60).stdout


def _limpar_indice():
    """Apaga do ÍNDICE de fotos (MediaStore) tudo da pasta do bot — isso também apaga os arquivos.
    Só 'rm' deixava entrada FANTASMA: a galeria do sticker ordena pelo índice (não pela data) e a
    1ª miniatura virava um arquivo apagado → sticker invisível (19/10). O MuMu imprime um
    'Segmentation fault' depois, mas o delete acontece."""
    _adb("shell", "content delete --uri content://media/external/images/media "
                  "--where \"relative_path='Pictures/QuaseNada/'\"; "
                  "content delete --uri content://media/external/video/media "
                  "--where \"relative_path='Pictures/QuaseNada/'\"; "
                  f"rm -f {PASTA}/*; mkdir -p {PASTA}")


def _push_galeria(caminhos):
    """Manda os PNGs pra galeria; o ÚLTIMO da lista fica como o mais recente (1ª miniatura)."""
    _limpar_indice()
    for c in caminhos:
        destino = f"{PASTA}/{os.path.basename(c)}"
        _adb("push", c, destino)
        _adb("shell", "touch", destino)   # o push preserva a data do arquivo → força 'agora'
        _adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
             "-d", f"file://{destino}")
        time.sleep(0.3)


def _stickers_na_tela(d):
    out = []
    for m in re.finditer(r"<node[^>]*/?>", d.dump_hierarchy()):
        t = m.group(0)
        desc = (re.search(r'content-desc="([^"]*)"', t) or [0, ""])[1]
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
        if b and desc.startswith(STICKERS):
            out.append(tuple(map(int, b.groups())))
    return out


def _mover(d, ident, destino, log=None, outros=()):
    """Arrasta o sticker de bounds `ident` até o centro `destino`, em ciclo (arrasto LENTO; o IG
    anda ~80% do gesto). `outros` = bounds dos stickers que NÃO são este (o card…). Perto da
    borda as bounds saem cortadas, então o sticker é achado pelo centro, não pelo tamanho."""
    atual = ident
    for _ in range(4):
        cx, cy = (atual[0] + atual[2]) // 2, (atual[1] + atual[3]) // 2
        if abs(cx - destino[0]) < 30 and abs(cy - destino[1]) < 30:
            return atual
        try:
            _W, H = d.window_size()
        except Exception:
            H = 1600
        # pega o sticker num ponto deslocado CONTRA o movimento vertical: o dedo termina mais
        # longe da borda — descendo, não chega na lixeira e não precisa de 2ª correção (20/10)
        h = atual[3] - atual[1]
        off = int(h * 0.3) if destino[1] > cy + 30 else (-int(h * 0.3) if destino[1] < cy - 30 else 0)
        gx, gy = cx, cy - off
        ex = int(gx + (destino[0] - cx) / 0.8)
        ey = int(gy + (destino[1] - cy) / 0.8)
        # o dedo NUNCA desce até a lixeira (rodapé): passou de ~86% da tela, o IG apaga o sticker
        # (a mensagem sumiu assim — 19/10)
        if destino[1] > cy:
            ey = min(ey, int(H * 0.86))
        # ~550px/s: devagar demais (ajuste curto lento) o IG lê como "segurar" e não move; rápido
        # demais (flick) ele ignora
        dist = ((ex - gx) ** 2 + (ey - gy) ** 2) ** 0.5
        d.swipe(gx, gy, ex, ey, max(0.25, min(1.0, dist / 550)))
        _sleep(0.4, 0.5)
        cands = [b for b in _stickers_na_tela(d) if b not in outros]
        if not cands:
            _log(log, "  perdi o sticker de vista ao mover")
            return None
        atual = min(cands, key=lambda b: abs((b[0] + b[2]) // 2 - destino[0])
                    + abs((b[1] + b[3]) // 2 - destino[1]))
        _log(log, f"    ajuste: centro agora {((atual[0] + atual[2]) // 2, (atual[1] + atual[3]) // 2)} "
                  f"→ alvo {destino}")
    return atual


def _apagar_sticker(d, b):
    """Arrasta o sticker DIRETO (sem segurar parado — segurar abre outro modo) até a lixeira, que
    aparece embaixo no centro durante o arrasto."""
    cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    d.touch.down(cx, cy)
    for y in range(cy + 20, 1500, 40):
        d.touch.move(450, y)
        time.sleep(0.03)
    time.sleep(0.4)
    d.touch.up(450, 1490)
    _sleep(0.5, 0.7)
    return b not in _stickers_na_tela(d)


def _abrir_bandeja_stickers(d, alvo_desc):
    for _ in range(3):
        st = d(resourceId=R + "asset_button")
        if st.exists:
            _tocar(d, st, 3)
        else:
            d.click(849, 129)
        if d(description=alvo_desc).wait(timeout=6):
            _sleep(0.25, 0.35)
            return _tocar(d, d(description=alvo_desc), 4)
        _sleep(1.2, 1.8)
    return False


def _add_sticker_foto(d, indice, log=None):
    """Stickers → Sticker de foto → miniatura `indice` (0 = mais recente). Devolve as bounds do
    sticker novo (o que não existia antes)."""
    antes = set(_stickers_na_tela(d))
    if not _abrir_bandeja_stickers(d, "Sticker de foto"):
        _log(log, "  não abri o sticker de foto")
        return None
    th = d(resourceId=R + "gallery_sticker_grid_item_thumbnail")
    if not th.wait(timeout=8):
        return None
    _sleep(0.3, 0.4)
    if th.count <= indice:
        return None
    d.click(*_centro(th[indice].info["bounds"]))
    for _ in range(14):
        _sleep(0.3, 0.4)
        novos = [s for s in _stickers_na_tela(d) if s not in antes]
        if novos:
            return novos[-1]
    return None


def _fundo_laranja(d, log=None, alvo=None, segurar=0.35):
    """Fundo com a cor EXATA do brechó: Desenhar → conta-gotas (a lupa nasce no centro da tela, em
    cima da imagem laranja que já foi posta como sticker) → segura no fundo (pinta a tela toda) →
    Concluído. NÃO tocar em pincel depois do conta-gotas: isso zera a cor (19/10)."""
    for _ in range(3):
        des = d(description="Desenhar")
        if des.exists:
            break
        ov = d(resourceId=R + "overflow_button")
        if ov.exists:
            d.click(*_centro(ov.info["bounds"]))
        else:
            d.click(849, 429)
        d(description="Desenhar").wait(timeout=3)
    if not d(description="Desenhar").exists:
        _log(log, "  não achei o Desenhar")
        return False
    d.click(*_centro(d(description="Desenhar").info["bounds"]))
    eye = d(resourceId=R + "eyedropper_color_picker_tool")
    if not eye.wait(timeout=5):
        _log(log, "  sem conta-gotas")
        return False
    eb = eye.info["bounds"]
    try:
        W, H = d.window_size()
    except Exception:
        W, H = 900, 1600
    # (tempos testados: encurtar aqui faz o conta-gotas não pegar a cor — 20/10)
    # arrasta a lupa SEGURANDO e para um instante antes de soltar: soltar no fim de um swipe
    # rápido não deixa o conta-gotas registrar a cor do ponto final (20/10)
    ax, ay = alvo if alvo else (W // 2, int(H * 0.47))
    x0, y0 = W // 2, int(H * 0.5)
    # `segurar` maior = arrasto mais lento e pausa maior no alvo
    passo = 0.03 if segurar <= 0.5 else 0.06
    # CONFERE A COR ANTES DE PINTAR (21/10): depois de soltar, o botão do conta-gotas fica com a cor
    # pega. Com as duas instâncias ligadas o modo conta-gotas às vezes não ativa a tempo e o bot
    # pintava às cegas (29% caíam no caminho da imagem, +30s). Não pegou → toca de novo, espera
    # mais o modo ativar e arrasta outra vez (só no quadrado; a imagem já confere depois).
    for tent in range(3 if alvo else 1):
        _sleep(0.5, 0.7)
        d.click(*_centro(eb))
        _sleep(0.8 + 0.7 * tent, 1.0 + 0.7 * tent)
        d.touch.down(x0, y0)
        for k in range(1, 9):
            d.touch.move(int(x0 + (ax - x0) * k / 8), int(y0 + (ay - y0) * k / 8))
            time.sleep(passo)
        time.sleep(segurar)
        d.touch.up(int(ax), int(ay))
        if not alvo:
            break
        try:
            _sleep(0.3, 0.4)
            tela = _print_tela()
            _local.ultimo_cg = (tela.copy(), (int(ax), int(ay)))   # vai pro diagnóstico se falhar
            if _cor_no_conta_gotas(tela, eb):
                if tent:
                    _log(log, f"  conta-gotas pegou o laranja na {tent + 1}ª tentativa")
                break
        except Exception:
            break
        _log(log, "  conta-gotas não pegou o laranja — tentando de novo")
    _sleep(0.5, 0.7)
    d.long_click(W // 2, int(H * 0.105), 1.3)                   # segura no fundo → pinta tudo
    _sleep(0.7, 0.9)
    pronto = d(resourceId=R + "done_button")
    if pronto.exists:
        d.click(*_centro(pronto.info["bounds"]))
    _sleep(0.9, 1.1)
    return True


def _cor_no_conta_gotas(tela, eb):
    """O botão do conta-gotas (canto de baixo) fica pintado com a cor que a lupa pegou: confere se é
    o laranja do brechó em 4 pontos do círculo (o ícone branco fica no meio)."""
    cx, cy = (eb["left"] + eb["right"]) // 2, (eb["top"] + eb["bottom"]) // 2
    r = max(6, (eb["right"] - eb["left"]) // 2)
    pts = [(cx - r * 0.55, cy), (cx + r * 0.55, cy), (cx, cy - r * 0.55), (cx, cy + r * 0.55)]
    return sum(_perto(_cor_px(tela, x, y)) for x, y in pts) >= 2


MARCA_BRECHO = "brechoquasenadaa"


def _norm(s):
    import html
    import unicodedata
    s = unicodedata.normalize("NFKD", html.unescape(str(s or "")).replace("’", "'"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(s.split())


def _post_do_brecho(d, nome=None):
    """O post ABERTO na tela é do brechó (e, se veio `nome`, é a peça certa)? Devolve as bounds do
    botão de enviar DESSE post (o 1º de cima), ou None. 23/10: depois de reiniciar o IG o link não
    abriu o post, a tela ficou no feed e o bot compartilhou o 1º post do feed (@aasafe__) — o
    botão de enviar da tela anterior também "passava" na espera. (O post aberto pelo link aparece
    DENTRO da aba do feed, com o mesmo logo "Feed inicial" — então quem decide é o autor do 1º
    post + o nome da peça na legenda dele, não a tela.)"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        return None
    autores, shares, legendas = [], [], []
    for m in re.finditer(r"<node[^>]*>", xml):
        t = m.group(0)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
        if not b:
            continue
        bb = tuple(map(int, b.groups()))
        rid = re.search(r'resource-id="([^"]*)"', t)
        rid = rid.group(1) if rid else ""
        tx = re.search(r'text="([^"]*)"', t)
        txt = _norm(tx.group(1) if tx else "")
        if rid.endswith(":id/row_feed_photo_profile_name"):
            autores.append((bb, txt))
        elif rid.endswith(":id/row_feed_button_share"):
            shares.append(bb)
        elif txt.startswith(MARCA_BRECHO + " |"):
            legendas.append((bb, txt))
    if not autores:
        return None
    topo, quem = min(autores, key=lambda a: a[0][1])
    if not quem.startswith(MARCA_BRECHO):
        return None
    if nome:
        alvo = _norm(nome)[:12]
        # a legenda do MESMO post (a 1ª abaixo do cabeçalho) tem que citar a peça
        leg = sorted((lg for lg in legendas if lg[0][1] > topo[1]), key=lambda lg: lg[0][1])
        if alvo and leg and alvo not in leg[0][1]:
            return None
    abaixo = [s for s in shares if s[1] > topo[1]]
    return min(abaixo, key=lambda s: s[1]) if abaixo else None


def abrir_repost(d, code, log=None, _de_novo=False, nome=None):
    """Post do brechó → enviar → 'Adicionar à história'. True se o editor abriu. Só compartilha
    depois de CONFERIR que o post aberto é do brechó e é a peça certa (`nome`)."""
    desfazer_republicar(d, log)
    descartar_rascunho(d)
    # sai de qualquer tela com botão de enviar (feed/post anterior): senão a espera "acha" o botão
    # velho antes do link abrir o post novo
    if d(resourceId=R + "row_feed_button_share").exists and d(resourceId=R + "profile_tab").exists:
        d(resourceId=R + "profile_tab").click()
        _sleep(1.0, 1.5)
    _adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
         "-d", f"https://www.instagram.com/p/{code}/", "-p", "com.instagram.android")
    alvo = None
    fim = time.time() + 20
    while time.time() < fim and alvo is None:
        time.sleep(1.0)
        alvo = _post_do_brecho(d, nome)
    if alvo is None:
        if desfazer_republicar(d, log) and not _de_novo:   # o aviso por cima impedia o post de aparecer
            return abrir_repost(d, code, log, _de_novo=True, nome=nome)
        if not _de_novo:
            _log(log, "  o link não abriu o post da peça (a tela mostrava outra coisa) — tentando de novo")
            d.press("back")
            _sleep(1.0, 1.5)
            return abrir_repost(d, code, log, _de_novo=True, nome=nome)
        _log(log, "  o post da peça não abriu (a tela mostrava outro post) — pulo, NÃO compartilho")
        return False
    _sleep(0.5, 0.7)
    # a folha de enviar às vezes demora a mostrar a fileira de baixo ("Adicionar à história") —
    # espera mais e, se não vier, fecha e abre de novo (no lote de 10, 2 peças caíram aqui)
    for tent in range(2):
        if tent:
            alvo = _post_do_brecho(d, nome)
            if alvo is None:
                _log(log, "  depois de reabrir a folha o post não confere mais — pulo")
                return False
        d.click((alvo[0] + alvo[2]) // 2, (alvo[1] + alvo[3]) // 2)   # o enviar DESTE post, não o 1º da tela
        if _tocar(d, d(description="Adicionar à história"), 14):
            break
        _log(log, "  folha de enviar sem 'Adicionar à história' — reabrindo")
        desfazer_republicar(d, log)
        d.press("back")
        _sleep(1.0, 1.5)
    else:
        return False
    ok = d(resourceId=R + "your_story_share_shortcut_button").wait(timeout=15)
    _sleep(0.8, 1.0)
    return ok


def gerar_fundo(pasta):
    """Imagem laranja lisa (cor exata do brechó) só pro conta-gotas pegar a cor; é apagada depois."""
    from PIL import Image
    p = os.path.join(pasta, "qn_fundo.png")
    Image.new("RGB", (540, 960), COR_BRECHO).save(p)
    return p


# ─────────────── lote: N stories numa conta, com rodízio de peças ───────────────
_ESTADO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "story_mumu_state.json")


def _estado():
    import json
    try:
        with open(_ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_estado(est):
    import json
    tmp = _ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _ESTADO)


def escolher_pecas(conta, n, pecas):
    """Sorteia n peças (com post no IG) que ESTA conta ainda não postou no ciclo atual; quando o
    ciclo acaba (postou todas), recomeça. Mesmo rodízio do story antigo."""
    with _trava_estado:
        est = _estado()
        feitas = set((est.get(conta) or {}).get("ciclo", []))
        disp = [p for p in pecas if p.get("code")]
        novas = [p for p in disp if p["code"] not in feitas]
        if len(novas) < n:   # ciclo acabou → recomeça (sem repetir as que já vão agora)
            est.setdefault(conta, {})["ciclo"] = []
            _salvar_estado(est)
            novas = disp
    random.shuffle(novas)
    return novas[:n]


def marcar_postada(conta, code):
    with _trava_estado:   # brechó e segue podem postar ao mesmo tempo (threads) → um de cada vez
        est = _estado()
        c = est.setdefault(conta, {})
        c.setdefault("ciclo", []).append(code)
        c["ultimo"] = time.time()
        _salvar_estado(est)


# ═══════════ FLUXO VERIFICADO (19/10, depois do lote de 10 com 5 stories errados) ═══════════
# Problemas que apareceram publicados: etiqueta e mensagem TROCADAS (a galeria não segue a ordem de
# envio), fundo CINZA (preenchimento falhou), imagem laranja NÃO apagada. Regras agora:
#   1) a galeria tem UMA imagem por vez (a do sticker que vai entrar) → não tem como pegar a errada;
#   2) cada sticker que entra é conferido pelo formato (proporção) da imagem que mandamos;
#   3) o fundo é conferido pela COR (cantos) depois de pintar — se não for o laranja, repete;
#   4) depois de apagar a imagem laranja confere que ela sumiu E que o card continua;
#   5) antes de publicar, confere TUDO (fundo, etiqueta no canto do card, mensagem embaixo, card).
#      Qualquer falha → NÃO publica, descarta e devolve o motivo (o lote tenta de novo a peça).


def _galeria_so(caminho):
    """Deixa a galeria do bot com UMA imagem só (a que vai virar sticker agora). Limpa, manda e
    espera o índice de fotos ter a imagem — tudo num shell só depois do push (cada `content`/`am`
    sobe uma JVM de ~1s no Android, então juntar economiza)."""
    _limpar_indice()
    destino = f"{PASTA}/{os.path.basename(caminho)}"
    nome = os.path.basename(caminho)
    _adb("push", caminho, destino)
    r = _adb("shell", f"touch {destino}; am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE "
                      f"-d file://{destino} >/dev/null; for i in 1 2 3 4 5 6 7 8 9 10 11 12; do "
                      f"content query --uri content://media/external/images/media --projection "
                      f"_display_name | grep -q '{nome}' && echo INDEXADO && break; sleep 0.3; done")
    return "INDEXADO" in (r.stdout or "")


def _proporcao_png(caminho):
    from PIL import Image
    with Image.open(caminho) as im:
        return im.width / im.height


def _add_sticker_conferido(d, caminho, log=None):
    """Põe `caminho` como sticker de foto e CONFERE pelo formato. Devolve bounds ou None."""
    if not _galeria_so(caminho):
        _log(log, f"  galeria não indexou {os.path.basename(caminho)}")
        return None
    s = _add_sticker_foto(d, 0, log)
    if not s:
        return None
    prop = (s[2] - s[0]) / max(1, (s[3] - s[1]))
    esperado = _proporcao_png(caminho)
    if abs(prop - esperado) / esperado > 0.18:
        _log(log, f"  sticker com formato errado ({prop:.2f} ≠ {esperado:.2f}) — apagando")
        _apagar_sticker(d, s)
        return None
    return s


def _cor_px(im, x, y):
    return im.getpixel((int(x), int(y)))


def _perto(c, alvo=COR_BRECHO, tol=28):
    return all(abs(a - b) <= tol for a, b in zip(c, alvo))


def _print_tela():
    import io
    from PIL import Image
    return Image.open(io.BytesIO(_adb_bytes("exec-out", "screencap", "-p"))).convert("RGB")


def _fundo_ok(W, H):
    """Fundo laranja de verdade? Confere 4 pontos fora do card (topo, laterais e embaixo)."""
    im = _print_tela()
    pts = [(W * 0.3, H * 0.1), (W * 0.03, H * 0.5), (W * 0.97, H * 0.62), (W * 0.06, H * 0.86)]
    return all(_perto(_cor_px(im, x, y)) for x, y in pts)


_DIAG_CG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs", "conta_gotas")


def _salvar_diag_cg(W, H):
    """Conta-gotas não pegou: salva a tela logo depois de soltar a lupa (com o alvo marcado) e a
    tela já pintada, em logs/conta_gotas/ (mantém só as 20 últimas)."""
    try:
        from PIL import ImageDraw
        os.makedirs(_DIAG_CG, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        ult = getattr(_local, "ultimo_cg", None)
        if ult:
            im, (ax, ay) = ult
            dr = ImageDraw.Draw(im)
            sy = ay + LUPA_ABAIXO_DO_DEDO
            dr.ellipse([ax - 8, sy - 8, ax + 8, sy + 8], outline=(0, 255, 0), width=3)
            im.save(os.path.join(_DIAG_CG, f"{ts}_{_serial().split(':')[-1]}_lupa.png"))
        _print_tela().save(os.path.join(_DIAG_CG, f"{ts}_{_serial().split(':')[-1]}_pintado.png"))
        arqs = sorted(os.listdir(_DIAG_CG))
        for a in arqs[:-40]:
            os.remove(os.path.join(_DIAG_CG, a))
    except Exception:
        pass


def _card_atual(d):
    """O card do post = o MAIOR sticker (largura > 60% da tela)."""
    try:
        W, _H = d.window_size()
    except Exception:
        W = 900
    st = [b for b in _stickers_na_tela(d) if (b[2] - b[0]) > W * 0.6]
    return max(st, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if st else None


def postar_repost(d, peca, pasta, log=None, enviar=True, shot=None, fundo="laranja",
                  mostrar_preco=True, chamada=""):
    """Story da peça com verificação em cada etapa. 'ok' | 'simulado' | motivo (NÃO publicou).
    `fundo`: 'laranja' (conta-gotas, o padrão) ou 'instagram' (o fundo que o IG gera — bem mais
    rápido); `mostrar_preco`/`chamada` vêm do modo."""
    code = peca.get("code")
    if not code:
        return "sem_code"
    laranja = fundo != "instagram"
    tag_png, cta_png, bloco_rel = gerar_stickers(peca, pasta, mostrar_preco, chamada, bloco=laranja)
    fundo_png = None
    try:
        W, H = d.window_size()
    except Exception:
        W, H = 900, 1600

    def falha(motivo):
        _log(log, f"  ✗ {motivo} — descartando (não publica)")
        if shot:
            shot("falha_" + motivo.split(":")[0])
        descartar_rascunho(d)
        _limpar_indice()
        return motivo

    if not abrir_repost(d, code, log, nome=peca.get("nome")):   # confere autor + peça antes de compartilhar
        return falha("editor")
    card = _card_atual(d)
    if not card:
        return falha("sem_card")
    d.click((card[0] + card[2]) // 2, (card[1] + card[3]) // 2)      # estilo com bordas/título
    _sleep(0.7, 0.9)

    # fundo laranja, CAMINHO RÁPIDO: a chamada entra já (com o quadrado laranja escondido), o
    # conta-gotas pega a cor no quadrado e pinta. Não pegou → caminho antigo (imagem laranja).
    cta = None
    pintado = False
    if laranja and bloco_rel:
        cta = _add_sticker_conferido(d, cta_png, log)
        if not cta:
            return falha("mensagem")
        bx = cta[0] + bloco_rel[0] * (cta[2] - cta[0])
        by = cta[1] + bloco_rel[1] * (cta[3] - cta[1])
        # o conta-gotas lê ~43px ABAIXO do dedo (o circulinho debaixo da gota — medido 20/10)
        _fundo_laranja(d, log, alvo=(bx, by - LUPA_ABAIXO_DO_DEDO))
        pintado = _fundo_ok(W, H)
        if not pintado:
            # 21/10: só acontece com as DUAS instâncias ligadas (29% no lote; 0 de 7 com o brechó
            # desligado). Segurar mais na 2ª tentativa NÃO resolveu (0/2) → sem causa ainda: guarda
            # a tela da lupa + a pintada pra diagnosticar no próximo caso real
            _salvar_diag_cg(W, H)
            _log(log, "  cor não pegou pelo quadrado — usando a imagem laranja")
    # fundo laranja: imagem → conta-gotas → pinta → confere cor (até 2 tentativas) → apaga a imagem
    if laranja and not pintado:
        fundo_png = gerar_fundo(pasta)
        fundo = _add_sticker_conferido(d, fundo_png, log)
        if not fundo:
            return falha("fundo_img")
        for _t in range(2):
            _fundo_laranja(d, log)
            if _fundo_ok(W, H):
                break
            _log(log, "  fundo não ficou laranja — repetindo o conta-gotas")
        else:
            return falha("fundo_cor")
        if not _apagar_sticker(d, fundo) or any(
                abs((b[2] - b[0]) - (fundo[2] - fundo[0])) < 20 and abs((b[3] - b[1]) - (fundo[3] - fundo[1])) < 20
                for b in _stickers_na_tela(d)):
            return falha("fundo_nao_apagou")
        card = _card_atual(d)
        if not card:
            return falha("card_apagado")

    # sobe o card ~60px pra caber a mensagem embaixo
    yh = card[1] + 35
    d.touch.down(W // 2, yh)
    for y in range(yh - 4, yh - 70, -6):
        d.touch.move(W // 2, y)
        time.sleep(0.04)
    d.touch.up(W // 2, yh - 68)
    _sleep(0.4, 0.5)
    card = _card_atual(d)
    if not card:
        return falha("card_sumiu")

    alvo_tag = (card[2] - 110, card[1] + 30)
    alvo_cta = (W // 2, min(card[3] + 95, int(H * 0.86)))
    tag = None
    if tag_png:
        tag = _add_sticker_conferido(d, tag_png, log)
        if not tag:
            return falha("etiqueta")
        tag = _mover(d, tag, alvo_tag, log, outros=(card,))
    if cta:
        # a chamada já entrou (caminho rápido): acha ela de novo (o card subiu e a etiqueta entrou)
        maior = (cta[2] - cta[0], cta[3] - cta[1])
        cands = [b for b in _stickers_na_tela(d) if b not in (card, tag)
                 and abs((b[2] - b[0]) - maior[0]) < 30 and abs((b[3] - b[1]) - maior[1]) < 30]
        cta = cands[0] if cands else None
    if not cta:
        cta = _add_sticker_conferido(d, cta_png, log)
    if not cta:
        return falha("mensagem")
    cta = _mover(d, cta, alvo_cta, log, outros=tuple(b for b in (card, tag) if b))

    # ── conferência final: nada sai sem passar aqui ──
    card = _card_atual(d)
    if not card:
        return falha("final:card")
    if laranja and not _fundo_ok(W, H):
        return falha("final:fundo")
    stk = [b for b in _stickers_na_tela(d) if b != card]
    def perto_de(alvo, tol=70):
        return any(abs((b[0] + b[2]) // 2 - alvo[0]) < tol and abs((b[1] + b[3]) // 2 - alvo[1]) < tol
                   for b in stk)
    if tag_png and not perto_de(alvo_tag):
        return falha("final:etiqueta_fora")
    if not perto_de(alvo_cta):
        return falha("final:mensagem_fora")
    if len(stk) != (2 if tag_png else 1):
        return falha(f"final:{len(stk)}_stickers")
    if shot:
        shot("repost_antes_de_publicar")
    if not enviar:
        descartar_rascunho(d)
        _limpar_indice()
        return "simulado"
    ok = publicar(d, log)
    return "ok" if ok else "publicar"


def postar_lote(d, conta, n, pasta, log=None, enviar=True, parar=None, tentativas=2,
                pausa_story=(0, 0), fundo="laranja", mostrar_preco=True, chamada=""):
    """n stories na conta ATIVA; cada peça tem até `tentativas` (o fluxo só publica se passar na
    conferência). `pausa_story` = respiro entre um story e outro; `fundo`/`mostrar_preco`/`chamada`
    vêm do modo. Devolve {ok, postados, falhas}."""
    import random
    tentativas = max(1, int(tentativas or 1))
    import story_card as sc
    pecas = sc.fetch_pecas()
    escolhidas = escolher_pecas(conta, n, pecas)
    _log(log, f"Conta: @{conta} — {len(escolhidas)} peça(s) pro story: "
              + ", ".join((p.get("nome") or p["code"])[:24] for p in escolhidas))
    postados, falhas = 0, 0
    for i, p in enumerate(escolhidas, start=1):
        if parar and parar():
            break
        nome = p.get("nome") or p["code"]
        _log(log, f"[progress] {i - 1} {len(escolhidas)} {nome}")
        t0 = time.time()
        r = "?"
        for tent in range(1, tentativas + 1):
            try:
                r = postar_repost(d, p, pasta, log, enviar=enviar, fundo=fundo,
                                  mostrar_preco=mostrar_preco, chamada=chamada)
            except Exception as e:
                r = f"erro:{e}"
                descartar_rascunho(d)
            if r in ("ok", "simulado"):
                break
            _log(log, f"  tentativa {tent} de {nome} não passou ({r})")
        dt = time.time() - t0
        if r in ("ok", "simulado"):
            postados += 1
            if enviar:
                marcar_postada(conta, p["code"])
            _log(log, f"✓ story {i}/{len(escolhidas)}: {nome} ({int(dt)}s, conferido)")
        else:
            falhas += 1
            _log(log, f"! story {i}/{len(escolhidas)} NÃO publicado ({r}) — {nome}")
        if i < len(escolhidas) and pausa_story and pausa_story[1] > 0:
            seg = random.uniform(*pausa_story)
            _log(log, f"próximo story em {int(seg)}s…")
            fim = time.time() + seg
            while time.time() < fim:
                if parar and parar():
                    break
                time.sleep(max(0.0, min(1.0, fim - time.time())))   # nunca negativo
    _log(log, f"[progress] {len(escolhidas)} {len(escolhidas)} concluído")
    return {"ok": falhas == 0, "postados": postados, "falhas": falhas}
