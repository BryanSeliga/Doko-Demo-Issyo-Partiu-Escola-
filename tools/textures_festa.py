"""Texturas do festival cultural e do bon-odori (placas de barraca, cartazes, portao, casa assombrada): apaga o
japones e desenha o portugues. Mesmo formato de textures.py. Toda entrada tem "size" porque o mesmo nome de
textura existe em outros pacotes com outro tamanho. Chaves "PACOTE.BPM:NOME".

Fica como esta: letras miudas e ilegiveis dos cartazes (SAI_POS_IMAKAWA, SAI_POS_SHODO, SAI_POS_YAKISOBA).
"""
from textures import _not


def _far(colors, d):
    """Tinta = tudo que se afasta de todas as cores do fundo (fundos com duas ou mais cores)."""
    return lambda r, g, b, a: min(abs(r - c[0]) + abs(g - c[1]) + abs(b - c[2]) for c in colors) > d


def _s(size, spec):
    spec = dict(spec)
    spec["size"] = size
    return spec


def _t(lines, box, color, **kw):
    return dict({"lines": lines, "box": box, "color": color}, **kw)


# placa de takoyaki: fundo rosado liso entre duas faixas; letras vermelhas de contorno amarelo e
# um texto pequeno vertical verde-agua na esquerda
_TAKO_BG = (236, 224, 225)
_TAKOYAKI = {
    "erase": [((0, 7, 128, 52), _not(_TAKO_BG, 25))], "fill": _TAKO_BG,
    "texts": [_t(["TAKOYAKI"], (26, 13, 125, 47), (242, 73, 84), outline=(227, 220, 20)),
              _t(["QUENTE"], (4, 9, 24, 50), (35, 133, 136), vertical=True)]}

# banner escuro com "sabor tradicional" pequeno em cima e "imagawayaki" (bolinho recheado) grande
_IMA_BG = (94, 64, 82)
_IMAGAWA = {
    "erase": [((6, 3, 250, 105), _not(_IMA_BG, 45))], "fill": _IMA_BG,
    "texts": [_t(["SABOR TRADICIONAL"], (48, 7, 214, 24), (227, 226, 226)),
              _t(["BOLINHO"], (26, 34, 230, 104), (227, 226, 226))]}

_LULA_BG = [(122, 172, 110), (232, 121, 135)]  # listra verde (coluna par) e rosa (coluna impar)

# madeira entalhada: "queda de braco" (ude-zumo); letras escuras sobre veios de madeira, recompoe com os vizinhos
_BRACO_WOOD = lambda r, g, b, a: max(r, g, b) < 105

SPECS = {
    # --- palco da banda: barracas do festival
    "BANDSTAGE.BPM:BGBON_YATAIKANBAN1": _s((128, 64), _TAKOYAKI),
    # maca do amor (ringo-ame): letras azuis de contorno branco e texto verde pequeno vertical, fundo vermelho
    "BANDSTAGE.BPM:BGBON_YATAIKANBAN2": _s((128, 64), {
        "erase": [((0, 2, 128, 51), _not((236, 49, 49), 25))], "fill": (236, 49, 49),
        "texts": [_t(["MAÇÃ", "DOCE"], (32, 6, 124, 48), (47, 53, 147), outline=(250, 240, 245)),
                  _t(["SUPER"], (6, 8, 26, 50), (60, 150, 60), vertical=True)]}),
    # algodao-doce (watagashi): letras vermelhas, "doce" e "fofo" brancos pequenos nas laterais
    "BANDSTAGE.BPM:BGBON_YATAIKANBAN3": _s((128, 64), {
        "erase": [((0, 7, 128, 53), _not((213, 108, 166), 25))], "fill": (213, 108, 166),
        "texts": [_t(["ALGODÃO"], (22, 12, 94, 48), (187, 6, 21), outline=(250, 235, 240)),
                  _t(["DOCE"], (3, 10, 16, 48), (250, 240, 245), vertical=True),
                  _t(["FOFO"], (98, 10, 112, 48), (250, 240, 245), vertical=True)]}),
    # milho (tomorokoshi): fundo amarelo manchado; letras vermelhas de contorno claro e circulo claro na esquerda
    "BANDSTAGE.BPM:BGBON_YATAIKANBAN5": _s((128, 64), {
        "erase": [((0, 0, 128, 52), _not((230, 210, 58), 50))], "fill": (230, 210, 58),
        "texts": [_t(["MILHO"], (34, 7, 125, 48), (198, 25, 45), outline=(250, 235, 225)),
                  _t(["ASSADO"], (7, 8, 24, 48), (250, 250, 250), vertical=True, outline=(198, 25, 45))]}),
    # damasco (anzu-ame): fundo azul arroxeado liso; letras brancas de contorno vermelho e linha pequena amarela
    "BANDSTAGE.BPM:BGBON_YATAIKANBAN6": _s((128, 64), {
        "erase": [((0, 0, 128, 63), _not((82, 83, 147), 30))], "fill": (82, 83, 147),
        "texts": [_t(["SABOR MARCANTE"], (8, 3, 122, 12), (225, 235, 120)),
                  _t(["DAMASCO"], (4, 16, 124, 60), (253, 253, 253), outline=(204, 35, 37))]}),
    "BANDSTAGE.BPM:BGBON_YATAIKANBAN8": _s((256, 128), _IMAGAWA),
    # queda de braco (ude-zumo): letras entalhadas na madeira
    "BANDSTAGE.BPM:BGBON_YATAIKANBAN9": _s((128, 64), {
        "erase": [((1, 1, 127, 63), _BRACO_WOOD)], "fill": None,
        "texts": [_t(["BRAÇO"], (8, 8, 122, 56), (40, 24, 18))]}),
    # legenda escrita a mao embaixo do desenho de um teclado (teclas pretas)
    "BANDSTAGE.BPM:BG_BAND_KEYBOARD_060221": _s((128, 64), {
        "erase": [((14, 40, 114, 62), _not((77, 77, 77), 70))], "fill": (77, 77, 77),
        "texts": [_t(["TECLADO"], (16, 42, 112, 58), (240, 240, 240))]}),

    # --- bon-odori: barracas
    "BONODORI.BPM:BGBON_YATAIKANBAN1": _s((128, 64), _TAKOYAKI),
    # pesca de peixinhos (kingyo-sukui): letras vermelhas de contorno branco sobre azul-claro
    "BONODORI.BPM:BGBON_YATAIKANBAN10": _s((128, 64), {
        "erase": [((8, 12, 112, 52), lambda r, g, b, a: r > 120)], "fill": None,
        "texts": [_t(["PESCARIA"], (8, 15, 114, 50), (243, 64, 64), outline=(250, 250, 250))]}),
    # yakisoba: letras amarelas de contorno vinho sobre triangulos laranja e bege
    "BONODORI.BPM:BGBON_YATAIKANBAN11": _s((128, 64), {
        "erase": [((6, 8, 114, 56), _far([(217, 153, 110), (231, 194, 155), (225, 181, 140), (220, 164, 123)], 40))],
        "fill": None,
        "texts": [_t(["YAKISOBA"], (6, 14, 114, 52), (245, 230, 63), outline=(128, 28, 27))]}),
    # chocobanana: mesmo estilo, duas linhas
    "BONODORI.BPM:BGBON_YATAIKANBAN12": _s((128, 64), {
        "erase": [((6, 8, 128, 56), _far([(217, 153, 110), (231, 194, 155), (225, 181, 140), (220, 164, 123)], 40))],
        "fill": None,
        "texts": [_t(["CHOCO", "BANANA"], (6, 12, 122, 54), (245, 231, 64), outline=(128, 28, 27))]}),
    # algodao-doce: fundo amarelo com bolas brancas; letras brancas de contorno azul-agua
    "BONODORI.BPM:BGBON_YATAIKANBAN13": _s((128, 64), {
        "erase": [((14, 12, 98, 56), _not((249, 235, 28), 60))], "fill": (249, 235, 28),
        "texts": [_t(["ALGODÃO"], (12, 17, 100, 52), (253, 253, 253), outline=(80, 170, 180))]}),
    # lula assada: letras vermelhas de contorno claro sobre listras rosa e verde (o desenho branco fica)
    "BONODORI.BPM:BGBON_YATAIKANBAN4": _s((128, 64), {
        # as listras tem 16 px de largura: uma caixa por listra, cada uma preenchida com a cor mais comum da linha
        "erase": [((x, 8, x + 16, 56), _not(_LULA_BG[(x // 16) % 2], 45)) for x in range(32, 128, 16)], "fill": "rows",
        "texts": [_t(["LULA"], (36, 12, 124, 52), (187, 6, 21), outline=(250, 235, 230))]}),
    # faixa vertical da barraca de yakisoba: palavra grande vermelha de contorno amarelo e "delicia!" no explosao
    "BONODORI.BPM:YATAIB_UMAI": _s((64, 128), {
        "erase": [((0, 0, 35, 128), _not((228, 225, 208), 40)),
                  ((39, 12, 54, 96), lambda r, g, b, a: max(r, g, b) < 150 and r - g < 60)], "fill": None,
        "texts": [_t(["YAKISOBA"], (5, 9, 28, 121), (190, 30, 40), vertical=True, outline=(240, 195, 70)),
                  _t(["DELÍCIA!"], (41, 15, 53, 93), (40, 30, 30), vertical=True)]}),

    # --- portao do festival cultural e cartazes
    # grande placa laranja sobre o portao: "bunkasai" (festival cultural)
    "BUNKASAIGATE.BPM:GATE02": _s((256, 128), {
        "erase": [((10, 10, 246, 118), lambda r, g, b, a: r - b > 30)], "fill": "rows",
        "texts": [_t(["FESTIVAL", "CULTURAL"], (18, 16, 238, 112), (211, 119, 56))]}),
    # placa vertical da comissao organizadora, com seta e "aqui" embaixo
    "BUNKASAIGATE.BPM:JIKKOUIINKAI": _s((64, 128), {
        "erase": [((12, 10, 52, 102), _not((253, 252, 252), 40)),
                  ((24, 102, 50, 111), lambda r, g, b, a: r < 170 or g < 120)], "fill": None,
        "texts": [_t(["COMISSÃO"], (19, 14, 47, 94), (133, 33, 50), vertical=True, outline=(251, 248, 157)),
                  _t(["AQUI"], (28, 102, 49, 111), (133, 33, 50))]}),
    # recado vertical em duas colunas (tem folheto)
    "BUNKASAIGATE.BPM:JIKKOUIINKAI2": _s((32, 64), {
        "erase": [((0, 0, 32, 64), _not((242, 204, 169), 40))], "fill": (242, 204, 169),
        "texts": [_t(["TEM"], (4, 3, 14, 61), (94, 42, 18), vertical=True),
                  _t(["FOLHETO"], (17, 3, 29, 61), (94, 42, 18), vertical=True)]}),
    # cartaz do bolinho (imagawayaki): so o titulo azul no alto; o resto e letra miuda ilegivel
    "BUNKASAIGATE.BPM:SAI_POS_IMAKAWA": _s((64, 64), {
        "erase": [((0, 0, 64, 20), lambda r, g, b, a: b - r > 20), ((20, 20, 64, 24), lambda r, g, b, a: b - r > 20),
                  ((8, 19, 20, 22), lambda r, g, b, a: b - r > 20)], "fill": None,
        "texts": [_t(["BOLINHO"], (3, 2, 61, 19), (49, 84, 158))]}),
    # cartaz de caligrafia (shodo): titulo vertical a direita, o texto miudo da esquerda fica
    "BUNKASAIGATE.BPM:SAI_POS_SHODO": _s((64, 64), {
        "erase": [((38, 0, 64, 64), ("dark", 150))], "fill": (158, 157, 130),
        "texts": [_t(["CALIGRAFIA"], (42, 1, 61, 63), (70, 70, 70), vertical=True)]}),
    # cartaz do desafio de queda de braco: tres linhas claras sobre verde escuro
    "BUNKASAIGATE.BPM:SAI_POS_SUMOU": _s((64, 64), {
        "erase": [((2, 1, 63, 63), _not((99, 118, 80), 45))], "fill": (99, 118, 80),
        "texts": [_t(["BRAÇO", "DE FERRO", "VENHA!"], (4, 3, 61, 61), (150, 182, 160))]}),
    # cartaz do yakisoba: letras grandes cinza-marrom, mais uma linha vermelha em cima e uma laranja embaixo
    "BUNKASAIGATE.BPM:SAI_POS_YAKISOBA": _s((64, 64), {
        "erase": [((2, 8, 62, 20), lambda r, g, b, a: r - b > 60 and g < 130),
                  ((2, 20, 62, 44), lambda r, g, b, a: r - b > 25 and g < 135 and b < 100),
                  ((14, 36, 58, 46), lambda r, g, b, a: r - b > 60 and g > 120)], "fill": (187, 174, 117),
        "texts": [_t(["YAKISOBA"], (2, 21, 62, 41), (112, 86, 66))]}),

    # --- casa assombrada
    "OBAKEYASHIKI.BPM:BGOY_KANBAN": _s((128, 256), {
        "erase": [((24, 0, 100, 254), _not((8, 5, 10), 55)), ((6, 0, 24, 254), lambda r, g, b, a: min(r, g, b) > 100),
                  ((100, 0, 128, 200), _not((8, 5, 10), 50))], "fill": (6, 4, 9),
        "texts": [_t(["CASA"], (28, 10, 62, 110), (250, 250, 250), vertical=True),
                  _t(["ASSOMBRADA"], (66, 10, 100, 246), (250, 250, 250), vertical=True),
                  _t(["UUUUH"], (104, 20, 120, 120), (230, 230, 230), vertical=True)]}),
    # cartaz da casa assombrada (barraca do festival)
    "YATAI.BPM:SAI_POS_OBAKE": _s((128, 128), {
        "erase": [((4, 14, 126, 100), lambda r, g, b, a: min(r, g, b) > 92),
                  ((24, 2, 100, 14), lambda r, g, b, a: r - g > 40),
                  ((44, 98, 128, 124), _not((62, 72, 72), 60)),
                  ((22, 96, 36, 118), lambda r, g, b, a: min(r, g, b) > 140)], "fill": (62, 72, 72),
        "texts": [_t(["CASA", "ASSOMBRADA", "SE ATREVE?"], (6, 16, 122, 98), (245, 245, 245)),
                  _t(["BEM-VINDO..."], (26, 3, 98, 12), (210, 60, 130)),
                  _t(["ENTRE"], (60, 104, 118, 120), (245, 225, 90))]}),
    # cartaz da barraca de cafe: so as quatro linhas de texto de baixo (o "Cafe" em letras latinas fica)
    "YATAI.BPM:SAI_POS_CAFE": _s((128, 128), {
        "erase": [((28, 52, 106, 108), _not((58, 67, 66), 110))], "fill": None,
        "texts": [_t(["Café e bolo", "esperando", "por você!", "Culinária"], (30, 54, 104, 106), (245, 245, 240))]}),
    "YATAI.BPM:BGBON_YATAIKANBAN8L": _s((256, 128), _IMAGAWA),
    "YATAI.BPM:BGBON_YATAIKANBAN9L": _s((256, 128), {
        "erase": [((2, 2, 254, 126), _BRACO_WOOD)], "fill": None,
        "texts": [_t(["QUEDA DE", "BRAÇO"], (14, 14, 242, 114), (40, 24, 18))]}),
}
