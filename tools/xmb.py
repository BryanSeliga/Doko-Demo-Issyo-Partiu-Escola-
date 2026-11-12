"""Arquivos que o menu do PSP mostra para o jogo (pasta PSP_GAME do disco): titulo, icone e painel de informacoes.

- PARAM.SFO: o campo TITLE (UTF-8, ate 128 bytes) e o nome que aparece na lista de jogos;
- ICON0.PNG (144x80): o logotipo sobre um degrade rosa;
- PIC0.PNG (310x180): o logotipo e quatro linhas de apresentacao sobre uma foto da escola;
- ICON1.PMF: o video do icone, com o logotipo no comeco e no fim (icon_video.py).
O logotipo novo e a arte do usuario em uma peca so (art/logo.png: a faixa e o nome juntos). Cada arquivo sai com exatamente o
tamanho do original (um bloco de texto de enchimento dentro do PNG completa o que faltar): o jogo copia esses
arquivos para o save e nada no disco muda de lugar.
"""
import io
import os
import struct
import zlib

import numpy as np
from PIL import Image, ImageFilter

from iso_common import ICON0_PNG, ICON1_PMF, PARAM_SFO, PIC0_PNG
from textures import draw_text, inpaint
from title_logo import fit

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art")
LOGO_ART = os.path.join(ART, "logo.png")
# arte pronta do usuario para o painel (qualquer tamanho na proporcao de 310x180). Ela e feita sobre a foto do
# jogo e por isso fica fora do repositorio (art/menu esta no .gitignore); sem ela, o painel e montado aqui, com o
# mesmo texto, a partir da imagem que esta na ISO
PANEL_ART = os.path.join(ART, "menu", "painel.png")

TITLE = "Doko Demo Issyo: Partiu Escola!"
# icone: caixa do logotipo (o original ocupa mais ou menos a mesma area)
ICON_LOGO = (5, 15, 139, 65)
# painel: o logotipo original fica acima da linha 86 (abaixo dela comeca o telhado da escola, da mesma cor)
PIC_LOGO_BOTTOM = 86
PIC_LOGO = (40, 3, 286, 85)
PIC_TEXT_AREA = (30, 103, 282, 163)   # onde ficam as quatro linhas em japones
PIC_TEXT_BOX = (34, 105, 278, 162)
PIC_TEXT = ["Doko Demo Issyo: A escola começou!", "Toro, Jun, Ricky, Pierre e Suzuki.",
            "Cinco alunos cheios de personalidade", "em uma divertida vida escolar! Let's School Life!",
            "Tradução de fã por BryanSeliga"]
PIC_TEXT_COLOR, PIC_TEXT_OUTLINE = (255, 255, 255), (64, 48, 40)


def param_sfo(data):
    """PARAM.SFO com o titulo novo; o arquivo fica do mesmo tamanho."""
    out = bytearray(data)
    _, _, key_off, data_off, count = struct.unpack_from("<4sIIII", data, 0)
    for i in range(count):
        entry = 20 + i * 16
        ko, _, _, max_len, do = struct.unpack_from("<HHIII", data, entry)
        key = data[key_off + ko:data.index(b"\0", key_off + ko)]
        if key == b"TITLE":
            raw = TITLE.encode("utf-8") + b"\0"
            assert len(raw) <= max_len, (len(raw), max_len)
            out[data_off + do:data_off + do + max_len] = raw + b"\0" * (max_len - len(raw))
            struct.pack_into("<I", out, entry + 4, len(raw))
            return bytes(out)
    raise ValueError("PARAM.SFO sem TITLE")


def png_exact(im, size):
    """PNG da imagem com exatamente size bytes: comprime ao maximo, tira um pouco de cor se nao couber e completa
    o que faltar com um bloco de texto (tEXt) antes do fim do arquivo."""
    pad_min = 12 + 8  # bloco vazio: tamanho, tipo, "Comment\0" e CRC
    for bits in (8, 7, 6, 5, 4):
        px = np.asarray(im).copy()
        if bits < 8:
            step = 1 << (8 - bits)
            px[:, :, :3] = px[:, :, :3] // step * step + step // 2
        buf = io.BytesIO()
        Image.fromarray(px, im.mode).save(buf, "PNG", optimize=True, compress_level=9)
        png = buf.getvalue()
        if len(png) + pad_min <= size:
            break
    else:
        raise ValueError(f"PNG nao cabe em {size} bytes")
    body = b"Comment\0" + b" " * (size - len(png) - pad_min)
    chunk = struct.pack(">I", len(body)) + b"tEXt" + body + struct.pack(">I", zlib.crc32(b"tEXt" + body))
    end = png.rindex(b"IEND") - 4
    out = png[:end] + chunk + png[end:]
    assert len(out) == size
    return out


def paste_logo(im, box):
    img, pos = fit(Image.open(LOGO_ART).convert("RGBA"), box)
    im.alpha_composite(img, pos)


def icon0(data):
    """Icone: o degrade rosa do original (a cor de cada linha vem das bordas, onde nao ha logotipo) e o logotipo."""
    old = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
    h, w = old.shape[:2]
    rows = np.median(old[:, :3], axis=1)  # borda esquerda (a direita tem a marca TM)
    # o brilho do logotipo chega ate a borda em algumas linhas: mediana movel ao longo da altura
    rows = np.array([np.median(rows[max(0, y - 6):y + 7], axis=0) for y in range(h)]).astype(np.uint8)
    bg = np.repeat(rows[:, None, :], w, axis=1)
    im = Image.fromarray(bg, "RGB").convert("RGBA")
    paste_logo(im, ICON_LOGO)
    return png_exact(im.convert("RGB"), len(data))


def grow(mask, n):
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * n + 1))) > 0


def pic0(data):
    """Painel: apaga o logotipo e as quatro linhas em japones (recompondo a foto com os vizinhos) e desenha o
    logotipo novo e o texto em portugues. A moldura e a linha de copyright ficam."""
    old = Image.open(io.BytesIO(data)).convert("RGBA")
    if os.path.exists(PANEL_ART):  # so entra no tamanho e nos cantos arredondados do original
        art = Image.open(PANEL_ART).convert("RGB").resize(old.size, Image.LANCZOS)
        ready = np.dstack([np.asarray(art), np.asarray(old)[:, :, 3]])
        return png_exact(Image.fromarray(ready, "RGBA"), len(data))
    px = np.asarray(old).copy()
    r, g, b = (px[:, :, k].astype(int) for k in range(3))
    h, w = r.shape
    yy, xx = np.mgrid[0:h, 0:w]
    inside = (xx > 8) & (xx < w - 8)
    # logotipo: rosa, vermelho e laranja fortes (o ceu e azul, as nuvens brancas), mais o branco preso dentro dele
    strong = (r > 140) & (r - g > 25) & (yy > 2) & (yy < PIC_LOGO_BOTTOM) & inside
    logo = grow(strong, 3) & (yy > 2) & (yy < PIC_LOGO_BOTTOM + 2) & inside
    # texto: letras brancas de contorno escuro sobre a grama e as arvores
    x0, y0, x1, y1 = PIC_TEXT_AREA
    area = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    white = np.minimum(np.minimum(r, g), b) > 200
    dark = np.maximum(np.maximum(r, g), b) < 110
    # letra = branco colado em contorno escuro e o contorno colado nela (as flores claras nao tem contorno), mais
    # tudo que destoa muito da vizinhanca (tracos finos e suavizados que escapam da regra das cores)
    letters = (white & grow(dark, 2)) | (dark & grow(white, 2))
    gray = (r + g + b) / 3
    around = np.asarray(Image.fromarray(gray.astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(float)
    text = grow((letters | (np.abs(gray - around) > 30)) & area, 2) & area
    mask = logo | text
    rgb = inpaint(px[:, :, :3], mask)
    # a recomposicao sai em manchas chapadas: suaviza so os pixels recompostos
    soft = np.asarray(Image.fromarray(rgb, "RGB").filter(ImageFilter.GaussianBlur(2.5)))
    rgb = np.where(mask[:, :, None], soft, rgb)
    im = Image.fromarray(np.dstack([rgb, px[:, :, 3]]), "RGBA")
    paste_logo(im, PIC_LOGO)
    im.alpha_composite(draw_text((w, h), PIC_TEXT, PIC_TEXT_BOX, PIC_TEXT_COLOR, outline=PIC_TEXT_OUTLINE))
    out = np.asarray(im).copy()
    out[:, :, 3] = px[:, :, 3]  # cantos arredondados da moldura como no original
    return png_exact(Image.fromarray(out, "RGBA"), len(data))


def build(iso):
    """{(lba, tamanho): bytes} para build_iso.build(loose=...)."""
    import icon_video  # aqui dentro: ele usa o logotipo e a caixa do icone deste modulo
    out = {PARAM_SFO: param_sfo(iso.read(*PARAM_SFO)),
           ICON0_PNG: icon0(iso.read(*ICON0_PNG)),
           PIC0_PNG: pic0(iso.read(*PIC0_PNG))}
    video = icon_video.build(iso.read(*ICON1_PMF))  # None sem ffmpeg: o video original fica
    if video is not None:
        out[ICON1_PMF] = video
    return out
