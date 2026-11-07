"""Texturas com japones desenhado na imagem (placas, lanternas, quadros, o bilhete do album): apaga a escrita e
desenha o portugues. Portado do Issyo (tools/textures.py de la), com as entradas deste jogo.

Cada entrada (chave = nome do GIM sem pasta e extensao; vale para todo pacote que tiver esse nome) diz onde esta a
escrita (caixas e regra da tinta), com que cor preencher o lugar (ou None para recompor com os vizinhos) e os
textos novos. O texto e desenhado 4x maior e reduzido, e a imagem volta para o GIM original (gui_render.write_gim).

  "erase": lista de (caixa (x0, y0, x1, y1), regra da tinta)
      regras: ("redder", d), ("dark", v), ("light", v), ("near", (r, g, b), d), ("all",) ou funcao (r, g, b, a)
  "fill": None (recompoe com os vizinhos), "rows" (cor mais comum da linha), (r, g, b) ou (r, g, b, 0)
  "texts": lista de {"lines": [...], "box": (x0, y0, x1, y1), "color": (r, g, b)} com opcionais
      "vertical": True (letras empilhadas), "turned": 90 ou -90, "outline": (r, g, b)

Ficam como estao (texto ilegivel ate no original, ou decorativo): FLAGD01 (bandeira bordada), S01_PLATE e
S01_PLATE2 (plaquinhas de trofeu), os certificados, impressos e assinaturas do clube e da sala dos professores,
o corpo dos quadros da sala dos professores, os letreiros verticais da cidade (BGGZ_DEPARTMAKUMOJI*) e o
cardapio vertical da lojinha (BGKB_NEDAN).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from gim import to_rgba
from gui_render import FONT_PATH, write_gim
from iso_common import inner_files

SCALE = 4

# lanterna de festa com o kanji "matsuri" (festa): letras pretas de contorno branco sobre a cor da lanterna.
# O lugar das letras recebe a cor lisa da lanterna (recompor puxava o branco do contorno e das ondas)
def _not(color, d):
    """Tinta = tudo que se afasta da cor do fundo (pega tambem a borda suavizada do contorno)."""
    return lambda r, g, b, a: abs(r - color[0]) + abs(g - color[1]) + abs(b - color[2]) > d


def _lantern(color):
    return {"erase": [((19, 6, 47, 28), _not(color, 80))], "fill": color,
            "texts": [{"lines": ["FESTA"], "box": (6, 9, 58, 27), "color": (10, 10, 10), "outline": (250, 250, 250)}]}


_DAYS = ["S", "T", "Q", "Q", "S", "S"]  # iniciais de segunda a sabado, como nos calendarios

SPECS = {
    "KABE_U05": _lantern((172, 24, 0)), "KABE_U05B": _lantern((71, 66, 188)), "KABE_U05G": _lantern((78, 164, 2)),
    "KABE_U05P": _lantern((180, 65, 189)), "KABE_U05Y": _lantern((189, 180, 65)),
    # jaqueta de festa (happi) do Toro: "matsuri" vermelho de contorno branco nas costas; o "chounaikai"
    # (associacao do bairro) pequeno e vertical na manga fica
    "TORO_HAPPI": {
        "erase": [((36, 10, 90, 60), _not((51, 97, 154), 80))],
        "fill": (51, 97, 154),
        "texts": [{"lines": ["FESTA"], "box": (20, 22, 108, 54), "color": (227, 55, 27), "outline": (254, 254, 254)}]},
    # etiquetas de preco da lojinha: "80 ienes" vira "¥80"
    "BGKB_NEFUDA": {
        "erase": [((2, 3, 22, 15), ("dark", 200)), ((24, 3, 44, 15), ("dark", 200)), ((46, 3, 62, 15), ("dark", 200)),
                  ((2, 18, 22, 30), ("dark", 200)), ((24, 18, 44, 30), ("dark", 200))], "fill": None,
        "texts": [{"lines": [t], "box": box, "color": (110, 110, 105)} for t, box in
                  (("¥80", (2, 4, 22, 14)), ("¥60", (24, 4, 44, 14)), ("¥70", (46, 4, 62, 14)),
                   ("¥120", (2, 19, 22, 29)), ("¥150", (24, 19, 44, 29)))]},
    # placa vertical da lojinha: "encomendas de fantasia, aqui"
    "BGKB_TATEKAN": {
        "erase": [((4, 2, 30, 62), ("dark", 200))], "fill": None,
        "texts": [{"lines": ["FANTASIAS"], "box": (17, 2, 29, 62), "color": (90, 90, 90), "vertical": True},
                  {"lines": ["AQUI"], "box": (4, 4, 16, 40), "color": (90, 90, 90), "vertical": True}]},
    # quadro de horarios: titulo azul e dias da semana em vermelho
    "BGCL_TIMETABLE": {
        "erase": [((20, 1, 46, 8), lambda r, g, b, a: b - max(r, g) > 40)]
                 + [((12 + 8 * i, 9, 20 + 8 * i, 15), ("redder", 40)) for i in range(6)],
        "fill": (216, 213, 211),
        "texts": [{"lines": ["HORÁRIO"], "box": (14, 1, 52, 8), "color": (119, 104, 209)}]
                 + [{"lines": [d], "box": (12 + 8 * i, 9, 20 + 8 * i, 15), "color": (196, 95, 109)}
                    for i, d in enumerate(_DAYS)]},
    # bilhete do album (recado do Kuro, que tira as fotos): titulo branco e tres linhas amarelas, fundo transparente
    "TP_WORD": {
        "erase": [((60, 2, 182, 26), lambda r, g, b, a: a > 40 and min(r, g, b) > 200),
                  ((14, 38, 236, 122), lambda r, g, b, a: a > 40 and r > 200 and g > 180 and b < 100)],
        "fill": (0, 0, 0, 0),
        "texts": [{"lines": ["Do fotógrafo"], "box": (62, 3, 180, 25), "color": (245, 245, 245)},
                  {"lines": ["Foto de hoje pra vocês, miau", "Vejam com carinho, miau!", "Depois vai pro álbum, miau"],
                   "box": (16, 40, 234, 120), "color": (246, 236, 2)}]},
    # nome no armario do clube
    "BG071_LOCKER_NAME01": {
        "erase": [((4, 2, 30, 12), ("dark", 200))], "fill": None,
        "texts": [{"lines": ["Hiromi"], "box": (3, 3, 30, 12), "color": (150, 150, 150)}]},
}


def ink_rule(rule):
    if callable(rule):
        return rule
    kind = rule[0]
    if kind == "redder":
        return lambda r, g, b, a: r - max(g, b) > rule[1]
    if kind == "dark":
        return lambda r, g, b, a: max(r, g, b) < rule[1]
    if kind == "light":
        return lambda r, g, b, a: min(r, g, b) > rule[1]
    if kind == "near":
        c, d = rule[1], rule[2]
        return lambda r, g, b, a: (r - c[0]) ** 2 + (g - c[1]) ** 2 + (b - c[2]) ** 2 < d * d
    if kind == "all":
        return lambda r, g, b, a: True
    raise ValueError(rule)


def inpaint(px, mask):
    """Preenche os pixels marcados com a media dos vizinhos ja conhecidos, de fora para dentro."""
    px = px.astype(float)
    known = ~mask
    h, w = mask.shape
    while not known.all():
        acc = np.zeros_like(px)
        cnt = np.zeros((h, w))
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            sk = np.zeros_like(known)
            sp = np.zeros_like(px)
            ys, yd = (slice(max(dy, 0), h + min(dy, 0)), slice(max(-dy, 0), h + min(-dy, 0)))
            xs, xd = (slice(max(dx, 0), w + min(dx, 0)), slice(max(-dx, 0), w + min(-dx, 0)))
            sk[yd, xd] = known[ys, xs]
            sp[yd, xd] = px[ys, xs]
            acc += sp * sk[:, :, None]
            cnt += sk
        new = ~known & (cnt > 0)
        if not new.any():
            break
        px[new] = acc[new] / cnt[new][:, None]
        known = known | new
    return px.astype(np.uint8)


def fill_rows(px, mask, boxes):
    """Pinta cada pixel apagado com a cor mais comum dos pixels que ficaram na mesma linha da caixa
    (papel liso ou em degrade vertical, onde recompor pelos vizinhos borra)."""
    px = px.copy()
    h, w = mask.shape
    for x0, y0, x1, y1 in boxes:
        last = None
        for y in range(y0, min(y1, h)):
            keep = [tuple(px[y, x]) for x in range(x0, min(x1, w)) if not mask[y, x]]
            if keep:
                last = max(set(keep), key=keep.count)
            if last is not None:
                for x in range(x0, min(x1, w)):
                    if mask[y, x]:
                        px[y, x] = last
    return px


def draw_text(size, lines, box, color, vertical=False, outline=None):
    """Camada RGBA com o texto no maior tamanho que cabe na caixa, centralizado."""
    x0, y0, x1, y1 = (v * SCALE for v in box)
    bw, bh = x1 - x0, y1 - y0
    layer = Image.new("RGBA", (size[0] * SCALE, size[1] * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if vertical:
        lines = list(lines[0])
    stroke = SCALE if outline else 0
    px = bh
    while px > 4:
        font = ImageFont.truetype(FONT_PATH, px)
        boxes = [d.textbbox((0, 0), t, font=font, stroke_width=stroke) for t in lines]
        step = max(b[3] - b[1] for b in boxes) * (1.0 if vertical else 1.12)
        if max(b[2] - b[0] for b in boxes) <= bw and step * len(lines) <= bh:
            break
        px -= 1
    top = y0 + (bh - step * len(lines)) / 2
    for k, (t, b) in enumerate(zip(lines, boxes)):
        d.text((x0 + (bw - (b[2] - b[0])) / 2 - b[0], top + k * step - b[1]), t, font=font, fill=(*color[:3], 255),
               stroke_width=stroke, stroke_fill=(*(outline or color)[:3], 255))
    return layer.resize(size, Image.LANCZOS)


def text_layer(w, h, t):
    turned = t.get("turned", 0)
    if not turned:
        return draw_text((w, h), t["lines"], t["box"], t["color"], t.get("vertical", False), t.get("outline"))
    bx0, by0, bx1, by1 = t["box"]
    if turned == 90:  # tela = textura girada no sentido horario
        box = (h - by1, bx0, h - by0, bx1)
    else:
        box = (by0, w - bx1, by1, w - bx0)
    layer = draw_text((h, w), t["lines"], box, t["color"], t.get("vertical", False), t.get("outline"))
    return layer.rotate(turned, expand=True)


def translate(data, spec):
    w, h, rgba, _ = to_rgba(data)
    px = np.frombuffer(rgba, np.uint8).reshape(h, w, 4).copy()
    mask = np.zeros((h, w), bool)
    for (x0, y0, x1, y1), rule in spec["erase"]:
        ink = ink_rule(rule)
        for y in range(y0, min(y1, h)):
            for x in range(x0, min(x1, w)):
                mask[y, x] |= ink(*(int(v) for v in px[y, x]))
    fill = spec["fill"]
    if fill is None:
        px = inpaint(px, mask)
    elif fill == "rows":
        px = fill_rows(px, mask, [box for box, _ in spec["erase"]])
    else:
        px[mask] = fill if len(fill) == 4 else (*fill, 255)
    im = Image.fromarray(px, "RGBA")
    for t in spec["texts"]:
        im.alpha_composite(text_layer(w, h, t))
    return write_gim(data, im)


def load_specs():
    """SPECS daqui mais as entradas de cada textures_*.py (uma por grupo de cenarios)."""
    import importlib
    import os
    import pkgutil
    specs = dict(SPECS)
    here = os.path.dirname(os.path.abspath(__file__))
    for mod in pkgutil.iter_modules([here]):
        if mod.name.startswith("textures_"):
            specs.update(importlib.import_module(mod.name).SPECS)
    return specs


def build_all(iso, bpms, specs=None):
    """{(pacote, nome_interno): bytes}: toda textura com o nome de uma entrada, em qualquer pacote. A chave pode
    ser "NOME" ou "PACOTE.BPM:NOME" (so naquele pacote); "size": (w, h) na entrada restringe ao tamanho certo
    (o mesmo nome as vezes tem versoes de tamanhos diferentes em pacotes diferentes)."""
    specs = specs or load_specs()
    out = {}
    for pack, (off, _) in bpms.items():
        for n, o, s in inner_files(iso, off):
            if not n.endswith(".GIM"):
                continue
            key = n.replace(chr(92), "/").split("/")[-1][:-4]
            spec = specs.get(f"{pack}:{key}") or specs.get(key)
            if spec is None:
                continue
            data = iso.bp(o, s)
            if "size" in spec and tuple(to_rgba(data)[:2]) != tuple(spec["size"]):
                continue
            out[(pack, n)] = translate(data, spec)
    return out
