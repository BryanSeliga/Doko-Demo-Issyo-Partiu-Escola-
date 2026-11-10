"""Redesenha rotulos GIM em portugues, no mesmo tamanho e com as cores da imagem original."""
import collections
import os
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from gim import image_info, parse, swizzle, to_rgba, unswizzle
from gui_text import BY_PACK, COMMON, KEEP_AREA, SHAPES, STYLE
from iso_common import inner_files

# M PLUS Rounded 1c (SIL OFL, ver fonts/OFL.txt): o mesmo desenho arredondado do patch em ingles.
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "MPLUSRounded1c-ExtraBold.ttf")
TRACKING = 0.06  # espaco extra entre letras, em fracao do tamanho da fonte
SCALE = 4


def analyse(w, h, rgba):
    """Cor do texto, do contorno e do fundo da imagem original."""
    px = [tuple(rgba[i:i + 4]) for i in range(0, len(rgba), 4)]
    corners = [px[0], px[w - 1], px[(h - 1) * w], px[h * w - 1]]
    bg = None
    if sum(1 for c in corners if c[3] > 200) >= 3:
        bg = collections.Counter(c[:3] for c in corners).most_common(1)[0][0]
    solid = [p[:3] for p in px if p[3] > 110 and (bg is None or p[:3] != bg)]
    if not solid:
        return (255, 255, 255), None, bg
    lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    count = collections.Counter(solid)
    bright = sorted(count, key=lum)
    light = collections.Counter({c: n for c, n in count.items() if lum(c) >= lum(bright[len(bright) // 2])})
    dark = collections.Counter({c: n for c, n in count.items() if lum(c) < lum(bright[len(bright) // 2])})
    fill = light.most_common(1)[0][0] if light else bright[-1]
    outline = dark.most_common(1)[0][0] if dark else None
    total = sum(count.values())
    if outline is not None and (sum(dark.values()) < total * 0.05 or abs(lum(fill) - lum(outline)) < 40):
        outline = None
    return fill, outline, bg


def text_box(text, font, track, stroke):
    """Caixa (x0, y0, x1, y1) do texto desenhado letra a letra com espaco extra."""
    box = font.getbbox(text, stroke_width=stroke)
    return box[0], box[1], box[2] + track * (len(text) - 1), box[3]


def draw_tracked(d, xy, text, font, track, **kw):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, **kw)
        x += font.getlength(ch) + track


def render(text, w, h, fill, outline, bg):
    """Texto centralizado que cabe em w x h. Reduz a fonte ate caber."""
    return render_hi(text, w, h, fill, outline, bg).resize((w, h), Image.LANCZOS)


def render_hi(text, w, h, fill, outline, bg, max_w=None, area=None, left=False):
    """Como render, mas devolve a imagem em SCALE vezes o tamanho final. max_w limita a largura do texto;
    area (x0, x1) e a faixa da textura que o jogo mostra, onde o texto e centralizado (ou encostado em x0)."""
    W, H = w * SCALE, h * SCALE
    limit = W * 9 // 10 if w > 120 else W - SCALE
    x0, x1 = (0, W) if area is None else (area[0] * SCALE, area[1] * SCALE)
    limit = min(limit, x1 - x0)
    if max_w is not None:
        limit = min(limit, max_w * SCALE)
    stroke = (2 if h >= 28 else 1) * SCALE if outline else 0
    size = H
    while size > 6:
        font = ImageFont.truetype(FONT_PATH, size)
        track = size * TRACKING
        box = text_box(text, font, track, stroke)
        if box[2] - box[0] <= limit and box[3] - box[1] <= H - SCALE:
            break
        size -= 1
    im = Image.new("RGBA", (W, H), (*(bg or (0, 0, 0)), 255 if bg else 0))
    d = ImageDraw.Draw(im)
    x = x0 - box[0] if left else x0 + (x1 - x0 - (box[2] - box[0])) // 2 - box[0]
    y = (H - (box[3] - box[1])) // 2 - box[1]
    draw_tracked(d, (x, y), text, font, track, fill=(*fill, 255), stroke_width=stroke, stroke_fill=(*(outline or fill), 255))
    return im


def pack16(c, fmt):
    """Cor RGBA em paleta de 16 bits do GIM: 0 = RGB565, 1 = RGBA5551, 2 = RGBA4444."""
    r, g, b, a = c
    if fmt == 0:
        return round(r * 31 / 255) | round(g * 63 / 255) << 5 | round(b * 31 / 255) << 11
    if fmt == 1:
        return round(r * 31 / 255) | round(g * 31 / 255) << 5 | round(b * 31 / 255) << 10 | (a >= 128) << 15
    return round(r * 15 / 255) | round(g * 15 / 255) << 4 | round(b * 15 / 255) << 8 | round(a * 15 / 255) << 12


def write_gim(data, im):
    """Grava a imagem no GIM original, mantendo formato, paleta de tamanho igual e tamanho do arquivo."""
    data = bytearray(data)
    blocks = parse(bytes(data))
    img = next(b for b in blocks if b[0] == 4)
    pal = next(b for b in blocks if b[0] == 5)
    inf = image_info(bytes(data), img[1])
    pinf = image_info(bytes(data), pal[1])
    assert inf["fmt"] in (4, 5) and inf["order"] in (0, 1) and pinf["fmt"] in (0, 1, 2, 3), inf
    w, h = inf["w"], inf["h"]
    ncol = 16 if inf["fmt"] == 4 else 256
    q = im.quantize(colors=min(ncol, pinf["w"]), method=Image.FASTOCTREE, dither=Image.NONE)
    palette = q.getpalette("RGBA")
    colors = [tuple(palette[i * 4:i * 4 + 4]) for i in range(len(palette) // 4)]
    # A paleta pode vir com cor quase transparente: garante indice 0 transparente sem mudar a imagem.
    for i in range(pinf["w"]):
        c = colors[i] if i < len(colors) else (0, 0, 0, 0)
        if pinf["fmt"] == 3:
            struct.pack_into("<4B", data, pinf["pix"] + i * 4, *c)
        else:
            struct.pack_into("<H", data, pinf["pix"] + i * 2, pack16(c, pinf["fmt"]))
    stride = (w * inf["bpp"] + 7) // 8
    stride += (-stride) % 16
    size = stride * (h + (-h) % 8)
    buf = bytearray(data[inf["pix"]:inf["pix"] + size])
    if inf["order"] == 1:  # swizzle do PSP: blocos de 16 bytes x 8 linhas
        buf = bytearray(unswizzle(bytes(buf), stride, h))
    px = q.load()
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            if inf["fmt"] == 4:
                o = y * stride + x // 2
                buf[o] = (buf[o] & 0x0F) | (v << 4) if x & 1 else (buf[o] & 0xF0) | v
            else:
                buf[y * stride + x] = v
    if inf["order"] == 1:
        buf = swizzle(bytes(buf), stride, h)
    data[inf["pix"]:inf["pix"] + size] = buf
    return bytes(data)


def gim_size(data):
    w, h, _, _ = to_rgba(data)
    return w, h


def label_hi(data, text, max_w=None, keep_area=False, style=None):
    """keep_area: o texto fica na faixa do japones (a textura e maior que a parte visivel do botao).
    style: {"fill": cor, "outline": cor} no lugar das cores tiradas da imagem original."""
    w, h, rgba, _ = to_rgba(data)
    fill, outline, bg = analyse(w, h, rgba)
    if style:
        fill, outline = style.get("fill", fill), style.get("outline", outline)
    area = ink_area(data, bg)
    # titulos e rodapes deste jogo: o japones encosta na esquerda e o resto da textura fica vazio (e visivel);
    # o portugues, mais comprido, pode usar a largura toda, tambem encostado na esquerda
    left = area is not None and area[0] <= 3 and area[1] < w - 2
    if left and not keep_area:
        area = (area[0], w)
    if style and "area" in style:  # faixa fixa (x0, x1) onde o texto e centralizado
        area, left = style["area"], False
    return render_hi(text, w, h, fill, outline, bg, max_w, area, left)


def fill_holes(im, color):
    """Pinta os miolos fechados das letras (transparencia que nao se liga a borda da imagem) com color."""
    a = np.asarray(im)[:, :, 3]
    clear = Image.fromarray(np.where(a < 128, 255, 0).astype(np.uint8), "L").copy()
    w, h = clear.size
    for xy in [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]:
        if clear.getpixel(xy) == 255:
            ImageDraw.floodfill(clear, xy, 128)
    holes = np.asarray(clear) == 255
    px = np.asarray(im).copy()
    px[holes] = (*color, 255)
    return Image.fromarray(px, "RGBA")


def ink_area(data, bg):
    """Faixa horizontal ocupada pelo texto original. Muitas texturas sao maiores que a parte visivel no jogo
    (a aba vizinha ou um icone cobre o resto), e o texto japones fica so na parte visivel."""
    px = rgba_array(data)
    ink = px[:, :, 3] > 60
    if bg is not None:
        ink &= np.any(px[:, :, :3] != np.array(bg, np.uint8), axis=2)
    cols = np.nonzero(ink.any(axis=0))[0]
    if len(cols) == 0:
        return None
    return max(0, int(cols[0]) - 1), min(px.shape[1], int(cols[-1]) + 2)


def rgba_array(data):
    w, h, rgba, _ = to_rgba(data)
    return np.frombuffer(bytes(rgba), np.uint8).reshape(h, w, 4)


def relabel(data, text):
    """Rotulo com desenho (seta, placa, faixa): so as letras saem. Os pixels de letra (cor diferente da forma,
    longe da borda dela) sao recompostos com os vizinhos e o portugues e escrito na mesma area, na cor deles."""
    from title_logo import erase_mask
    px = rgba_array(data).astype(int)
    h, w = px.shape[:2]
    solid = px[:, :, 3] > 128
    inner = np.asarray(Image.fromarray((solid * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))) > 0
    if inner.sum() < 20:  # forma pequena (circulo do "novo"): a erosao comeria tudo
        inner = np.asarray(Image.fromarray((solid * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
    colors = collections.Counter(map(tuple, px[inner][:, :3]))
    shape = np.array(colors.most_common(1)[0][0])
    ink = inner & (np.abs(px[:, :, :3] - shape).sum(axis=2) > 90)
    ys, xs = np.nonzero(ink)
    color = collections.Counter(map(tuple, px[ink][:, :3])).most_common(1)[0][0]
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    grown = np.asarray(Image.fromarray((ink * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    base = erase_mask(Image.fromarray(px.astype(np.uint8), "RGBA"), grown & solid)
    layer = render_hi(text, x1 - x0, y1 - y0, color, None, None).resize((x1 - x0, y1 - y0), Image.LANCZOS)
    base.alpha_composite(layer, (int(x0), int(y0)))
    return write_gim(data, base)


def build_all(iso, bpms):
    """Devolve {(pacote, nome_interno): bytes} com todas as imagens traduzidas. bpms: {pacote: (offset, tamanho)}."""
    out = {}
    for pack, (off, size) in bpms.items():
        table = BY_PACK.get(pack, {})
        files = {n.replace(chr(92), "/").split("/")[-1][:-4]: (n, o, s) for n, o, s in inner_files(iso, off)
                 if n.endswith(".GIM")}
        for key, (name, o, s) in files.items():
            text = table.get(key, COMMON.get(key))
            if text is None:
                continue
            data = iso.bp(o, s)
            if text == "":  # pedaco que continuava o titulo japones: fica vazio
                w, h = gim_size(data)
                out[(pack, name)] = write_gim(data, Image.new("RGBA", (w, h), (0, 0, 0, 0)))
                continue
            if key in SHAPES:
                out[(pack, name)] = relabel(data, text)
                continue
            keep = key.startswith(KEEP_AREA)
            style = next((v for k, v in STYLE.items() if key.startswith(k)), None)
            # botoes do menu da escola: os de 128 px passavam da borda da tela quando nao estao escolhidos;
            # todos ficam com a largura dos de 64 px
            if style and style.get("vertical"):  # rotulo em pe: escrito deitado e girado (le-se de baixo para cima)
                w, h, rgba, _ = to_rgba(data)
                fill, outline, bg = analyse(w, h, rgba)
                out[(pack, name)] = write_gim(data, render_hi(text, h, w, fill, outline, bg).rotate(90, expand=True)
                                              .resize((w, h), Image.LANCZOS))
                continue
            hi = label_hi(data, text, max_w=56 if key.startswith("MENU_NAME") else None, keep_area=keep, style=style)
            if style and "holes" in style:
                hi = fill_holes(hi, style["holes"])
            out[(pack, name)] = write_gim(data, hi.resize(gim_size(data), Image.LANCZOS))
    return out
