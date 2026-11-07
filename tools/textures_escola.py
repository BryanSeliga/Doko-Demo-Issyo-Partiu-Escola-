"""Texturas da escola e da cidade com japones desenhado na imagem (cartazes, faixas, lousa, botao do onibus).
Mesmo formato de textures.py; as chaves sao "PACOTE.BPM:NOME" e cada entrada traz "size" porque o mesmo nome existe
em outros pacotes com tamanho diferente. Os corpos pequenos (tabuada, tabela de nutrientes, formula do pi, grade
de kanji) ficam como estao: so os titulos viram portugues.
"""
from textures import _not

_FAIXA = (10, 1, 55, 58)  # miolo das faixas de entrada/formatura (fora das bordas vermelha e amarela)


def _colorido(r, g, b, a):
    """Tinta colorida (azul/vermelho/rosa) sobre fundo cinza ou branco."""
    return max(r, g, b) - min(r, g, b) > 18


SPECS = {
    # placa do correio: "yuubin" (correio) em cinza acima do POST; recebe "CORREIO" no lugar
    "BUSTOURB.BPM:BGCV_POST2L": {
        "size": (128, 128),
        "erase": [((40, 8, 92, 29), lambda r, g, b, a: g > 105)], "fill": None,
        "texts": [{"lines": ["CORREIO"], "box": (36, 10, 92, 28), "color": (205, 150, 138)}]},
    # botao do onibus: seta de "play" e "ruuto kensaku" (busca de rota) em cinza
    "BUSTOURB.BPM:NAVI_BUTTOM": {
        "size": (128, 32),
        "erase": [((42, 6, 126, 30), _not((213, 222, 193), 38))], "fill": None,
        "texts": [{"lines": ["VER ROTA"], "box": (46, 9, 122, 26), "color": (130, 138, 128)}]},
    # rolo de regras da sala (seis colunas verticais de kanji): fica so o titulo "REGRAS"
    "CAFEROOM.BPM:BGCL_PAPER1": {
        "size": (64, 64),
        "erase": [((0, 0, 64, 64), lambda r, g, b, a: r + g + b < 380)], "fill": None,
        "texts": [{"lines": ["REGRAS"], "box": (24, 6, 42, 58), "color": (100, 90, 69), "vertical": True}]},
    # tabuada: titulo "kuku hyou" em branco sobre a faixa verde
    "CAFEROOM.BPM:KOMONO_99": {
        "size": (64, 64),
        "erase": [((11, 2, 54, 11), _not((83, 123, 77), 70))], "fill": (83, 123, 77),
        "texts": [{"lines": ["TABUADA"], "box": (12, 3, 53, 10), "color": (237, 234, 218)}]},
    # cartaz do pi: titulo "enshuuritsu" em branco sobre a faixa bege
    "CAFEROOM.BPM:KOMONO_ENNSYUURITU": {
        "size": (64, 64),
        "erase": [((13, 2, 52, 11), _not((206, 175, 118), 50))], "fill": (206, 175, 118),
        "texts": [{"lines": ["PI"], "box": (14, 2, 51, 11), "color": (240, 238, 230)}]},
    # quadro de kanji de uso comum: titulo "jouyou kanji hyou" em branco sobre a faixa azul-esverdeada
    "CLASSROOMA01.BPM:KOMONO_KANNJI1": {
        "size": (64, 64),
        "erase": [((12, 2, 52, 12), _not((63, 137, 139), 60))], "fill": (63, 137, 139),
        "texts": [{"lines": ["KANJI"], "box": (13, 3, 51, 11), "color": (236, 236, 224)}]},
    # "oshimai" (fim) em letras grandes pintadas a mao: branco semitransparente sobre fundo transparente
    "CLASSROOME.BPM:BG_OSHIMAI": {
        "size": (256, 64),
        "erase": [((0, 0, 256, 64), lambda r, g, b, a: a > 0)], "fill": (0, 0, 0, 0),
        "texts": [{"lines": ["FIM"], "box": (50, 2, 206, 62), "color": (221, 221, 221)}]},
    # tabela de nutrientes: titulo branco sobre a faixa vermelha
    "COOKINGROOM01.BPM:KOMONO_EIYOUSO2": {
        "size": (64, 64),
        "erase": [((6, 2, 58, 13), _not((215, 113, 113), 60))], "fill": (215, 113, 113),
        "texts": [{"lines": ["NUTRIÇÃO"], "box": (7, 3, 57, 12), "color": (245, 240, 228)}]},
    # bandeira de festa com um kanji dourado no centro
    "ENTRANCE.BPM:BGNY_FLAG": {
        "size": (64, 64),
        "erase": [((20, 5, 42, 29), _not((129, 25, 42), 90))], "fill": (129, 25, 42),
        "texts": [{"lines": ["FESTA"], "box": (13, 10, 51, 25), "color": (214, 184, 52), "outline": (96, 12, 30)}]},
    # faixa vertical "shuku nyuugaku" (parabens pela entrada na escola): tres kanji, azul, vermelho e rosa
    "ENTRANCE.BPM:BGNY_HANAWAMAKU": {
        "size": (64, 64),
        "erase": [(_FAIXA, _colorido)], "fill": "rows",
        "texts": [{"lines": ["BOAS"], "box": (10, 3, 55, 18), "color": (60, 90, 210)},
                  {"lines": ["VINDAS"], "box": (10, 20, 55, 34), "color": (210, 40, 60)},
                  {"lines": ["ALUNOS"], "box": (10, 38, 55, 56), "color": (210, 40, 60)}]},
    # faixa alta e estreita "o-me-de-to-u" (parabens), uma letra hiragana vermelha por linha
    "ENTRANCE.BPM:BGNY_MAKU01": {
        "size": (64, 256),
        "erase": [((0, 0, 64, 256), lambda r, g, b, a: r - max(g, b) > 14)], "fill": None,
        "texts": [{"lines": ["PARABÉNS"], "box": (8, 6, 56, 250), "color": (240, 30, 70), "vertical": True}]},
    # faixa de formatura "sotsugyou" (kanji azul, vermelho, vermelho): FORMA / TURA em duas linhas
    "GRADUATION.BPM:BGNY_HANAWAMAKU2": {
        "size": (64, 64),
        "erase": [(_FAIXA, _colorido)], "fill": "rows",
        "texts": [{"lines": ["FORMA"], "box": (10, 4, 55, 28), "color": (60, 90, 210)},
                  {"lines": ["TURA"], "box": (10, 33, 55, 57), "color": (210, 40, 60)}]},
    # lousa de ano novo: "akemashite omedetou" em giz, uma linha larga; vira tres linhas empilhadas
    "NEWYEARROOM.BPM:BGCR1_BLBOARD_NEWYEAR": {
        "size": (256, 256),
        "erase": [((0, 90, 256, 256), lambda r, g, b, a: r + g + b > 335)], "fill": None,
        "texts": [{"lines": ["FELIZ", "ANO", "NOVO"], "box": (30, 100, 226, 246), "color": (232, 226, 222)}]},
    # cartao de ano novo: dois kanji vermelhos ("gashou") sobre branco com raios bege
    "NEWYEARROOM.BPM:SEASON_01_01": {
        "size": (64, 64),
        "erase": [((0, 0, 64, 64), lambda r, g, b, a: r - max(g, b) > 25)], "fill": None,
        "texts": [{"lines": ["ANO", "NOVO"], "box": (6, 4, 58, 60), "color": (170, 0, 10)}]},
}
