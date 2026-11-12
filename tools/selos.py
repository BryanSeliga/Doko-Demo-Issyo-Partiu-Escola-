"""Selos de avaliacao do quadro de resultado das aulas e dos clubes (PICTURE017.BPM, 1.GIM a 5.GIM, da melhor nota
para a pior): uma coroa de louros numa cor so, com a avaliacao escrita dentro em kana, na vertical.

A coroa e a mesma nos cinco selos, mas em dois deles o kana encosta nela e nao da para separar. Por isso a coroa
limpa sai do selo 5 (a maior peca ligada da imagem, sem o texto) e vale para todos: cada selo novo e essa coroa
na cor do selo, com o texto em portugues no meio.
"""
import numpy as np
from PIL import Image

from gim import to_rgba
from gui_render import write_gim
from iso_common import inner_files
from textures import draw_text

PACK = "PICTURE017.BPM"
SIZE = 128
CLEAN = "5.GIM"                 # selo de onde sai a coroa
TEXT_BOX = (37, 41, 91, 85)     # miolo livre da coroa (o raio interno dela e 35, com centro em 63,5 x 62)
TEXTS = {
    "1.GIM": ["Muito", "bem!"],
    "2.GIM": ["Bem", "feito"],
    "3.GIM": ["Na", "média"],
    "4.GIM": ["Quase", "lá"],
    "5.GIM": ["Tente", "mais"],
}


def largest_piece(mask):
    """Mascara da maior peca ligada (vizinhanca de 8) de uma mascara booleana."""
    h, w = mask.shape
    seen = np.zeros((h, w), bool)
    best = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0, x0] or seen[y0, x0]:
                continue
            seen[y0, x0] = True
            stack, piece = [(y0, x0)], []
            while stack:
                y, x = stack.pop()
                piece.append((y, x))
                for yy in range(max(y - 1, 0), min(y + 2, h)):
                    for xx in range(max(x - 1, 0), min(x + 2, w)):
                        if mask[yy, xx] and not seen[yy, xx]:
                            seen[yy, xx] = True
                            stack.append((yy, xx))
            if len(piece) > len(best):
                best = piece
    out = np.zeros((h, w), bool)
    for y, x in best:
        out[y, x] = True
    return out


def pixels(data):
    w, h, rgba, _ = to_rgba(data)
    assert (w, h) == (SIZE, SIZE), (w, h)
    return np.frombuffer(rgba, np.uint8).reshape(h, w, 4)


def wreath_alpha(data):
    """Alfa da coroa sem o texto, tirado do selo limpo."""
    px = pixels(data)
    piece = largest_piece(px[:, :, 3] > 0)
    yy, xx = np.nonzero(piece)
    inner = np.hypot(yy - 63.5, xx - 63.5).min()
    assert piece.sum() > 4000 and inner > 30, (int(piece.sum()), float(inner))  # coroa inteira e nada do miolo
    return np.where(piece, px[:, :, 3], 0).astype(np.uint8)


def build_all(iso, bpms):
    """{(pacote, nome_interno): bytes} dos cinco selos com o texto em portugues."""
    files = {n: (o, s) for n, o, s in inner_files(iso, bpms[PACK][0])}
    assert set(TEXTS) <= set(files), sorted(files)
    alpha = wreath_alpha(iso.bp(*files[CLEAN]))
    out = {}
    for name, lines in TEXTS.items():
        data = iso.bp(*files[name])
        px = pixels(data)
        colors = {tuple(int(v) for v in p[:3]) for p in px.reshape(-1, 4) if p[3]}
        assert len(colors) == 1, (name, len(colors))  # uma cor so, em varios niveis de transparencia
        color = colors.pop()
        new = np.zeros((SIZE, SIZE, 4), np.uint8)
        new[:, :, :3] = color
        new[:, :, 3] = alpha
        im = Image.fromarray(new, "RGBA")
        im.alpha_composite(draw_text((SIZE, SIZE), lines, TEXT_BOX, color))
        out[(PACK, name)] = write_gim(data, im)
    return out
