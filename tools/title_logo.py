"""Logotipo "Partiu Escola!" da tela-titulo, a partir da arte do usuario (art/logo_partes_original.jpg).

A tela-titulo do jogo tem duas partes:
- TITLE.BPM TITLE_BG.GIM (512x512, 256 cores): o fundo, com a faixa rosa do "Doko Demo Issyo" desenhada nele;
- TITLE.BPM TITLE_LOGO.GIM (512x128, 16 cores): o nome do jogo, desenhado por cima, abaixo da faixa.
A arte nova vem nas mesmas duas partes: a faixa "DOKO DEMO ISSYO" vai para o fundo, no lugar da faixa japonesa
(que e apagada antes), e "Partiu Escola!" vai para o TITLE_LOGO, ocupando a mesma area do nome original.
As duas texturas saem em 256 cores (gim.to_gim8); o TITLE.BPM cresce e e remontado no fim do DATA.BP.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gim import to_gim8, to_rgba

HERE = os.path.dirname(os.path.abspath(__file__))
# arte do usuario: faixa "DOKO DEMO ISSYO" (com o mastro inteiro) a esquerda e "Partiu Escola!" a direita, sobre
# um xadrez cinza desenhado no proprio JPG (nao e transparencia de verdade)
ART_SRC = os.path.join(HERE, "..", "art", "logo_partes_original.jpg")
LOGO = ("TITLE.BPM", "TITLE_LOGO.GIM")
BG = ("TITLE.BPM", "TITLE_BG.GIM")
NAME_DROP = 10  # o nome desce na textura: mais espaco entre faixa e nome (pedido do usuario)


def remove_checker(path):
    """JPG com xadrez cinza no fundo -> RGBA: tira o cinza claro sem cor ligado a borda. O branco das letras
    fica, porque esta cercado pelo contorno rosa."""
    px = np.asarray(Image.open(path).convert("RGB")).astype(int)
    gray = (px.max(axis=2) - px.min(axis=2) < 24) & (px.min(axis=2) > 160)
    img = Image.fromarray(np.where(gray, 255, 0).astype(np.uint8), "L").copy()  # copy(): o floodfill grava nela
    h, w = gray.shape
    border = [(x, y) for x in range(0, w, 3) for y in (0, h - 1)] + [(x, y) for y in range(0, h, 3) for x in (0, w - 1)]
    for xy in border:
        if img.getpixel(xy) == 255:
            ImageDraw.floodfill(img, xy, 128)
    bg = np.asarray(img) == 128
    near = np.asarray(Image.fromarray(np.where(bg, 255, 0).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    # contorno suavizado (mistura do rosa com o cinza do xadrez, pouca cor) encostado no fundo: meio transparente
    soft = near & ~bg & (px.max(axis=2) - px.min(axis=2) < 60) & (px.min(axis=2) > 120)
    alpha[soft] = 96
    return Image.fromarray(np.dstack([px.astype(np.uint8), alpha]), "RGBA")


def parts():
    """(faixa, nome): as duas partes da arte, separadas pela maior coluna vazia entre elas."""
    art = remove_checker(ART_SRC)
    cols = (np.asarray(art)[:, :, 3] > 0).sum(axis=0)
    xs = np.nonzero(cols > 3)[0]
    k = int(np.argmax(np.diff(xs)))
    cut = (xs[k] + xs[k + 1]) // 2
    flag = art.crop((0, 0, cut, art.height))
    name = art.crop((cut, 0, art.width, art.height))
    return flag.crop(bbox_alpha(flag)), name.crop(bbox_alpha(name))


def fit(img, box):
    """img redimensionada para caber na caixa (x0, y0, x1, y1), centralizada; devolve (imagem, posicao)."""
    bw, bh = box[2] - box[0], box[3] - box[1]
    s = min(bw / img.width, bh / img.height)
    new = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    return new, (box[0] + (bw - new.width) // 2, box[1] + (bh - new.height) // 2)


def bbox_alpha(im):
    a = np.asarray(im)[:, :, 3] > 16
    ys, xs = np.nonzero(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def flag_box(bg):
    """Caixa da faixa rosa original no fundo (rosa forte: r alto, g baixo), na parte de cima da tela."""
    px = np.asarray(bg).astype(int)[:200, :480]
    pink = (px[:, :, 0] > 180) & (px[:, :, 1] < 120) & (px[:, :, 2] > 90)
    ys, xs = np.nonzero(pink)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def build(logo_gim, bg_gim):
    """{nome: bytes} das duas texturas novas."""
    flag, name = parts()
    # nome: mesma caixa do nome original na textura do logotipo
    w, h, rgba, _ = to_rgba(logo_gim)
    old = Image.frombytes("RGBA", (w, h), rgba)
    box = bbox_alpha(old)
    pad = 4
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(w, box[2] + pad), min(h, box[3] + pad))
    new_logo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img, pos = fit(name, box)
    new_logo.alpha_composite(img, (pos[0], pos[1] + NAME_DROP))
    # faixa: apaga a original (recompondo o ceu) e desenha a nova por cima, um pouco maior
    w2, h2, rgba2, _ = to_rgba(bg_gim)
    bg = Image.frombytes("RGBA", (w2, h2), rgba2)
    fx0, fy0, fx1, fy1 = flag_box(bg)
    grow = 0.10
    gx, gy = int((fx1 - fx0) * grow / 2), int((fy1 - fy0) * grow / 2)
    region = (fx0 - gx, fy0 - gy * 3, fx1 + gx, fy1 + gy * 3)
    bg = erase_mask(bg, old_flag_mask(bg))
    img, pos = fit(flag, region)
    bg.alpha_composite(img, pos)
    return {LOGO[1]: to_gim8(logo_gim, new_logo), BG[1]: to_gim8(bg_gim, bg)}


def old_flag_mask(bg):
    """Pixels da faixa japonesa no fundo: o rosa (faixa e mastro), as letras brancas dentro dela e a borda
    escura em volta. So eles sao apagados; o ceu e a arvore em volta ficam como estao."""
    px = np.asarray(bg).astype(int)
    h, w = px.shape[:2]
    pink = (px[:, :, 0] > 170) & (px[:, :, 1] < 130) & (px[:, :, 2] > 80)
    pink[240:] = False
    pink[:, 480:] = False
    # so o rosa ligado a faixa (as pontas vermelhas dos telhados ficam de fora)
    fx0, fy0, fx1, fy1 = flag_box(bg)
    img = Image.fromarray(np.where(pink, 255, 0).astype(np.uint8), "L").copy()
    seed = next((x, y) for y in range((fy0 + fy1) // 2, fy1) for x in range((fx0 + fx1) // 2, fx1) if pink[y, x])
    ImageDraw.floodfill(img, seed, 128)
    pink = np.asarray(img) == 128
    ys, xs = np.nonzero(pink)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    # letras: o que nao e rosa dentro da caixa e nao se liga a borda da caixa
    sub = Image.fromarray(np.where(pink[y0:y1, x0:x1], 0, 255).astype(np.uint8), "L").copy()
    for x in range(sub.width):
        for y in (0, sub.height - 1):
            if sub.getpixel((x, y)) == 255:
                ImageDraw.floodfill(sub, (x, y), 128)
    for y in range(sub.height):
        for x in (0, sub.width - 1):
            if sub.getpixel((x, y)) == 255:
                ImageDraw.floodfill(sub, (x, y), 128)
    mask = pink.copy()
    mask[y0:y1, x0:x1] |= np.asarray(sub) == 255
    grown = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
    return np.asarray(grown) > 0


def erase_mask(im, mask):
    """Recompoe os pixels da mascara com a media dos vizinhos conhecidos (de fora para dentro)."""
    px = np.asarray(im).astype(float).copy()
    known = ~mask
    while not known.all():
        acc = np.zeros_like(px)
        cnt = np.zeros(mask.shape)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            sk = np.roll(known, (dy, dx), (0, 1))
            acc += np.roll(px, (dy, dx), (0, 1)) * sk[:, :, None]
            cnt += sk
        new = ~known & (cnt > 0)
        if not new.any():
            break
        px[new] = acc[new] / cnt[new][:, None]
        known |= new
    return Image.fromarray(px.astype(np.uint8), "RGBA")


if __name__ == "__main__":
    import sys
    from iso_common import Iso, bpm_files, inner_files
    iso = Iso(sys.argv[1])
    bpms = {n: (o, s) for n, o, s in bpm_files(iso)}
    files = {n: (o, s) for n, o, s in inner_files(iso, bpms["TITLE.BPM"][0])}
    out = build(iso.bp(*files[LOGO[1]]), iso.bp(*files[BG[1]]))
    prev = sys.argv[2]
    bgw, bgh, bgr, _ = to_rgba(out[BG[1]])
    lw, lh, lr, _ = to_rgba(out[LOGO[1]])
    scr = Image.frombytes("RGBA", (bgw, bgh), bgr).crop((0, 0, 480, 272))
    # posicao do nome na tela medida no titulo original (aprox.): centro x 240, topo ~ 55
    lg = Image.frombytes("RGBA", (lw, lh), lr)
    scr.alpha_composite(lg, (240 - lw // 2, 50))
    scr.resize((960, 544)).save(prev)
    print(prev, {k: len(v) for k, v in out.items()})
