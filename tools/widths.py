"""Largura das letras no balao (fonte do sistema), medida no PPSSPP com work/calib.py e work/measure.py.
Unidade: pixel do PSP. A linha do balao cabe entre 178 e 188 unidades e o jogo quebra por palavra sozinho;
a tabela serve para conferir textos de caixas que nao quebram (opcoes, titulos). Letras acentuadas = letra base;
W, X, Y, Z, digitos e pontuacao ainda sao estimativas (nao apareceram na calibracao)."""

MEASURED = {"a": 12.8, "b": 13.5, "c": 14.0, "d": 13.0, "e": 13.6, "f": 9.8, "g": 13.0, "h": 12.8, "i": 5.3, "j": 7.3, "k": 13.3, "l": 6.5, "m": 19.0, "n": 13.0, "o": 14.0, "p": 13.3, "q": 13.0, "r": 9.0, "s": 13.0, "t": 10.0, "u": 12.3, "v": 13.3, "w": 17.8, "x": 13.3, "y": 13.3, "z": 12.6, "A": 16.9, "B": 15.0, "C": 16.0, "D": 17.0, "E": 14.8, "F": 14.8, "G": 16.8, "H": 16.0, "I": 7.0, "J": 14.3, "K": 15.8, "L": 14.3, "M": 19.0, "N": 17.3, "O": 17.8, "P": 15.0, "Q": 17.8, "R": 15.8, "S": 14.8, "T": 15.0, "U": 15.8, "V": 16.1, "♪": 19.0, " ": 6.5}
ESTIMATED = {"W": 20.0, "X": 16.0, "Y": 15.5, "Z": 15.0, "0": 13.0, "1": 13.0, "2": 13.0, "3": 13.0, "4": 13.0,
             "5": 13.0, "6": 13.0, "7": 13.0, "8": 13.0, "9": 13.0, ".": 6.5, ",": 6.5, "!": 7.0, "?": 12.0, ":": 6.5,
             ";": 6.5, "-": 9.0, "'": 5.0, '"': 9.0, "(": 8.0, ")": 8.0, "~": 13.0, "…": 19.0}
BASE = str.maketrans("áàâãäéêëíìóôõöúùüçÁÀÂÃÄÉÊËÍÌÓÔÕÖÚÙÜÇ", "aaaaaeeeiioooouuucAAAAAEEEIIOOOOUUUC")
FULL = 19.0  # caractere japones (largura cheia)
LINE = 178.0


def width(text):
    """Largura estimada do texto (sem quebras)."""
    total = 0.0
    for ch in text.translate(BASE):
        total += MEASURED.get(ch) or ESTIMATED.get(ch) or (FULL if ord(ch) > 0x2000 else 13.0)
    return total
