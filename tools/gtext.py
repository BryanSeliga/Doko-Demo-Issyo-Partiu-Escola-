"""Texto dos scripts do Let's Gakkou <-> bytes.

Variaveis da string-modelo (helper 0x48938 do BOOT): bytes 14/15/17/1b seguidos de u16 viram {14:0001};
o byte 1d (valor vem da pilha) vira {1d}. Outros bytes de controle (exceto quebra de linha) viram {xx}.
O texto e Shift-JIS; as letras acentuadas do portugues usam os codigos do JIS X 0213 (linha 9), que as tabelas
JIS2UCS/UCS2JIS do jogo ja conhecem (por exemplo á = 0x8576).
"""
import re

TMPL_U16 = (0x14, 0x15, 0x17, 0x1B)
TOKEN = re.compile(r"\{([0-9a-f]{2})(?::([0-9a-f]{4}))?\}")
# JIS X 0213 linha 9 em Shift-JIS (conferido contra UCS2JIS.BIN/JIS2UCS.BIN do jogo)
ACCENTS = {
    "À": 0x8556, "Á": 0x8557, "Â": 0x8558, "Ã": 0x8559, "Ç": 0x855D, "É": 0x855F, "Ê": 0x8560, "Í": 0x8563,
    "Ó": 0x8569, "Ô": 0x856A, "Õ": 0x856B, "Ú": 0x856F, "Ü": 0x8571,
    "à": 0x8575, "á": 0x8576, "â": 0x8577, "ã": 0x8578, "ç": 0x857C, "é": 0x857E, "ê": 0x8580, "í": 0x8583,
    "ó": 0x8589, "ô": 0x858A, "õ": 0x858B, "ú": 0x858F, "ü": 0x8591,
}
FROM_CODE = {v: k for k, v in ACCENTS.items()}
# simbolos da fonte do jogo fora do Shift-JIS padrao. So entram no texto com extra=True: a lista de textos
# (extract_all) foi numerada sem eles, e os textos com coracao vao para o fim dela
EXTRA = {"♥": 0x8540}
FROM_EXTRA = {v: k for k, v in EXTRA.items()}


def to_text(raw, extra=False):
    """Bytes -> str. Levanta UnicodeDecodeError se houver 2 bytes fora do Shift-JIS e dos acentos (e, com
    extra=True, dos simbolos de EXTRA)."""
    out, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c in TMPL_U16:
            out.append("{%02x:%04x}" % (c, int.from_bytes(raw[i + 1:i + 3], "little")))
            i += 3
        elif c < 0x20 and c != 0x0A:
            out.append("{%02x}" % c)
            i += 1
        elif c >= 0x80:
            code = int.from_bytes(raw[i:i + 2], "big")
            if code in FROM_CODE:
                out.append(FROM_CODE[code])
            elif extra and code in FROM_EXTRA:
                out.append(FROM_EXTRA[code])
            else:
                out.append(raw[i:i + 2].decode("cp932"))
            i += 2
        else:
            out.append(chr(c))
            i += 1
    return "".join(out)


def to_bytes(text):
    """str -> bytes. Letras sem acento e pontuacao em ASCII; acentos pelo JIS X 0213; o resto em Shift-JIS."""
    out, i = bytearray(), 0
    while i < len(text):
        m = TOKEN.match(text, i)
        if m:
            out.append(int(m.group(1), 16))
            if m.group(2):
                out += int(m.group(2), 16).to_bytes(2, "little")
            i = m.end()
            continue
        ch = text[i]
        if ch == "~":
            out += b"\x81\x60"  # o ~ ASCII pode virar sobrelinha na tabela JIS; usa o ～ japones
        elif ch in ACCENTS:
            out += ACCENTS[ch].to_bytes(2, "big")
        elif ch in EXTRA:
            out += EXTRA[ch].to_bytes(2, "big")
        else:
            out += ch.encode("cp932")
        i += 1
    return bytes(out)
