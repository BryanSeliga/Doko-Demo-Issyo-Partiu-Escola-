"""Quebra de linha por palavra para o balao de fala (largura util de cerca de 119 unidades; usamos 112 de margem da fonte)."""
import re

from textfmt import TOKEN, WAVE_CODE, glyph_index

BALLOON_WIDTH = 112
# Palavras inseridas pelo jogo (vocabulario, palavras ensinadas): a maioria cabe em 90 unidades.
VAR_WIDTH = 90
# $_WORD dentro de um texto do pool (palavra ensinada, nome): estimativa de uma palavra curta.
POOL_WORD_WIDTH = 40
# Largura do tique verbal ({17:...}); make_iso troca pela largura real do texto ("miau"; a ", " fica no texto).
TIC_WIDTH = 48
PIECE = re.compile(r"\{W\}|\{[0-9a-f]{2}:[0-9a-f]{4}\}|\$_[A-Z0-9]+|.", re.S)


def char_width(ch, widths, amap):
    if ch in amap:
        lead, trail = amap[ch] >> 8, amap[ch] & 0xFF
        return widths[2 * 96 + trail - 0x9E] if lead == 0x81 else 16
    if ch == "~":
        return widths[glyph_index(int.from_bytes(WAVE_CODE, "big"))]
    code = ord(ch)
    if 0x20 <= code < 0x7F:
        return widths[code - 0x20]
    return 16


def text_width(text, widths, amap, var_width=None):
    var_width = VAR_WIDTH if var_width is None else var_width
    total = 0
    for p in PIECE.findall(text):
        if p == "{W}":
            continue
        if len(p) > 1:
            total += TIC_WIDTH if p.startswith("{17") else var_width
        else:
            total += char_width(p, widths, amap)
    return total


VOWELS = set("aeiouáàâãéêíóôõúü")
# grupos que nao se separam: ch, lh, nh e consoante + r/l (pr, bl, tr...)
JOINED = {"ch", "lh", "nh"} | {a + b for a in "pbtdcgfv" for b in "rl"}


def syllable_cut(word, i):
    """True se da para hifenizar antes de word[i] (divisao silabica simplificada do portugues)."""
    w = word.lower()
    if i < 2 or len(w) - i < 2 or not any(c in VOWELS for c in w[:i]) or not any(c in VOWELS for c in w[i:]):
        return False
    a, b = w[i - 1], w[i]
    nxt = w[i + 1] if i + 1 < len(w) else ""
    if a in VOWELS and b not in VOWELS:  # a-mi, a-pre
        return nxt in VOWELS or b + nxt in JOINED
    if a not in VOWELS and b not in VOWELS:  # car-ro, cum-pri, men-tam
        return a + b not in JOINED and a.isalpha() and b.isalpha()
    return False


def hyphenate(word, widths, amap, limit):
    """Parte uma palavra maior que a linha, com hifen, de preferencia entre silabas."""
    hy = char_width("-", widths, amap)
    pieces = []
    while text_width(word, widths, amap) > limit:
        fit = 1
        while fit < len(word) and text_width(word[:fit + 1], widths, amap) + hy <= limit:
            fit += 1
        cut = next((i for i in range(fit, 1, -1) if syllable_cut(word, i)), fit)
        pieces.append(word[:cut] + "-")
        word = word[cut:]
    return pieces + [word]


def wrap(text, widths, amap, limit=BALLOON_WIDTH, var_width=None):
    """Troca espacos por quebras para nenhuma linha passar do limite. Mantem o \\n final."""
    tail = "\n" if text.endswith("\n") else ""
    body = text[:-1] if tail else text
    lead = body[:len(body) - len(body.lstrip(" "))]
    trail = body[len(body.rstrip(" ")):]
    words = " ".join(body.split()).split(" ") if body.strip() else []
    lines, cur = [], ""
    space = widths[0]
    for w in words:
        if "{" not in w and "$_" not in w and text_width(w, widths, amap, var_width) > limit:
            # palavra maior que o balao: o jogo cortaria em qualquer letra; aqui vai com hifen
            if cur:
                lines.append(cur)
            *full, cur = hyphenate(w, widths, amap, limit)
            lines.extend(full)
            continue
        if not cur:
            cur = w
        elif text_width(cur, widths, amap, var_width) + space + text_width(w, widths, amap, var_width) <= limit:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lead + "\n".join(lines) + trail + tail
