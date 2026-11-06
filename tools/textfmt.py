"""Converte strings do script <-> texto legivel e mede a largura em pixels.

Variaveis embutidas viram marcadores: bytes 14/15/17/18/19/1a/1b/1c + u16 => {14:0001}; byte 16 => {W}.
"""
import re

TMPL_VAR = (0x14, 0x15, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C)
TOKEN = re.compile(r"\{W\}|\{([0-9a-f]{2}):([0-9a-f]{4})\}")
# 0x8540 nao existe no Shift-JIS padrao: a fonte do jogo tem um coracao nesse codigo.
HEART = "♥"
HEART_CODE = b"\x85\x40"
WAVE_CODE = b"\x81\x60"


def to_text(raw):
    """Bytes do script -> str. Levanta UnicodeDecodeError se houver bytes fora do Shift-JIS."""
    out = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c in TMPL_VAR:
            out.append("{%02x:%04x}" % (c, int.from_bytes(raw[i + 1:i + 3], "little")))
            i += 3
        elif c == 0x16:
            out.append("{W}")
            i += 1
        elif c >= 0x80:
            out.append(HEART if raw[i:i + 2] == HEART_CODE else raw[i:i + 2].decode("cp932"))
            i += 2
        else:
            out.append(chr(c))
            i += 1
    return "".join(out)


def to_bytes(text, amap):
    """str -> bytes do script. Acentos usam o mapa da fonte; o resto precisa ser ASCII ou Shift-JIS."""
    out = bytearray()
    i = 0
    while i < len(text):
        m = TOKEN.match(text, i)
        if m:
            if m.group(1):
                out.append(int(m.group(1), 16))
                out += int(m.group(2), 16).to_bytes(2, "little")
            else:
                out.append(0x16)
            i = m.end()
            continue
        ch = text[i]
        if ch == HEART:
            out += HEART_CODE
        elif ch == "~":
            # O "~" ASCII da fonte fica no alto da celula e invade a linha de cima; usa o til largo japones.
            out += WAVE_CODE
        elif ch in amap:
            out += amap[ch].to_bytes(2, "big")
        else:
            out += ch.encode("cp932")
        i += 1
    return bytes(out)


def glyph_index(code):
    """Indice do glifo a partir do byte (ASCII) ou codigo de 2 bytes (mesma conta de 0x4078 no BOOT)."""
    if code < 0x80:
        return code - 0x20
    lead, trail = code >> 8, code & 0xFF
    row = (lead * 2 - 1) & 0xFF if lead < 0xA0 else (lead * 2 + 0x7F) & 0xFF
    if trail < 0x9F:
        cell = trail - 0x40 if trail >= 0x80 else trail - 0x3F
    else:
        row += 1
        cell = (trail + 0x62) & 0xFF
    return row * 96 + cell


def line_width(raw, widths, var_px=64):
    """Largura em pixels de cada linha de bytes do script. Variaveis valem var_px."""
    lines = [0]
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == 0x0A:
            lines.append(0)
            i += 1
        elif c in TMPL_VAR:
            lines[-1] += var_px
            i += 3
        elif c == 0x16:
            i += 1
        elif c >= 0x80:
            idx = glyph_index((c << 8) | raw[i + 1])
            lines[-1] += widths[idx] if 0 <= idx < len(widths) else 16
            i += 2
        else:
            idx = c - 0x20
            lines[-1] += widths[idx] if 0 <= idx < len(widths) else 0
            i += 1
    return lines
