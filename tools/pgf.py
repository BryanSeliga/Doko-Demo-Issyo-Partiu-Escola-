"""Larguras (avanco horizontal) dos caracteres de uma fonte PGF do PSP (formato lido pelo PPSSPP, revisao 2).

O jogo desenha o texto com a fonte do sistema (sceLibFont, jpn0.pgf = FTT-NewRodin Pro DB). O avanco vem em
1/64 de pixel na escala nativa da fonte; para quebrar linhas so importa a proporcao entre os caracteres.
Uso: pgf.py <fonte.pgf> [texto]
"""
import struct
import sys

DIM_IDX, BX_IDX, BY_IDX, ADV_IDX = 0x04, 0x08, 0x10, 0x20


class Bits:
    def __init__(self, data):
        self.data = data

    def get(self, pos, n):
        """n bits a partir do bit pos (fluxo LSB primeiro dentro de palavras de 32 bits)."""
        v = 0
        for k in range(n):
            p = pos + k
            word = struct.unpack_from("<I", self.data, (p // 32) * 4)[0]
            v |= ((word >> (p % 32)) & 1) << k
        return v


class Pgf:
    def __init__(self, path):
        b = open(path, "rb").read()
        assert b[4:8] == b"PGF0", "nao e PGF"
        hsize = struct.unpack_from("<H", b, 2)[0]
        rev = struct.unpack_from("<i", b, 8)[0]
        assert rev == 2, f"revisao {rev} nao tratada"
        (self.map_len, self.ptr_len, self.map_bpe, self.ptr_bpe) = struct.unpack_from("<4i", b, 16)
        self.first, self.last = struct.unpack_from("<HH", b, 182)
        dim_n, xadj_n, yadj_n, adv_n = b[258], b[259], b[260], b[261]
        shadow_len, shadow_bpe = struct.unpack_from("<2i", b, 364)
        pos = hsize

        def table(n):
            nonlocal pos
            vals = struct.unpack_from(f"<{2 * n}i", b, pos)
            pos += 8 * n
            return vals[:n], vals[n:]

        self.dim = table(dim_n)
        self.xadj = table(xadj_n)
        self.yadj = table(yadj_n)
        self.adv = table(adv_n)
        pos += ((shadow_len * shadow_bpe + 31) & ~31) // 8
        self.charmap = Bits(b[pos:pos + ((self.map_len * self.map_bpe + 31) & ~31) // 8 + 4])
        pos += ((self.map_len * self.map_bpe + 31) & ~31) // 8
        self.charptr = Bits(b[pos:pos + ((self.ptr_len * self.ptr_bpe + 31) & ~31) // 8 + 4])
        pos += ((self.ptr_len * self.ptr_bpe + 31) & ~31) // 8
        self.font = Bits(b[pos:] + b"\0" * 64)

    def glyph_index(self, ch):
        u = ord(ch) - self.first
        if not 0 <= u < self.map_len:
            return None
        g = self.charmap.get(u * self.map_bpe, self.map_bpe)
        return g if g < self.ptr_len else None

    def advance(self, ch):
        """Avanco horizontal em 1/64 de pixel, ou None se a fonte nao tem o caractere."""
        g = self.glyph_index(ch)
        if g is None:
            return None
        p = self.charptr.get(g * self.ptr_bpe, self.ptr_bpe) * 4 * 8
        f = self.font
        p += 14 + 7 + 7 + 7 + 7  # tamanho do glifo, largura, altura, esquerda, topo
        flags = f.get(p, 6)
        p += 6 + 7 + 9  # flags, sombra (7 bits), id da sombra (9 bits)
        for flag in (DIM_IDX, BX_IDX, BY_IDX):
            p += 8 if flags & flag else 64
        if flags & ADV_IDX:
            return self.adv[0][f.get(p, 8)]
        v = f.get(p, 32)
        return v - (1 << 32) if v & 0x80000000 else v


if __name__ == "__main__":
    fnt = Pgf(sys.argv[1])
    text = sys.argv[2] if len(sys.argv) > 2 else "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?áãçéíóõúÁÉ"
    sys.stdout.reconfigure(encoding="utf-8")
    print(" ".join(f"{c}={fnt.advance(c)}" for c in text))
