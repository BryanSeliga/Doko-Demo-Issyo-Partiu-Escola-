"""Relocacoes do BOOT.BIN (PRX de um segmento so): lista e aplicacao, como faz o carregador do PSP.

Cada entrada da secao 0x700000A0 e (offset, info): tipo no byte baixo (0 = nada, 2 = palavra de 32 bits, 4 = alvo de
jal, 5 = parte alta de um par lui/imediato, 6 = parte baixa). A parte alta e calculada junto com a parte baixa
da proxima entrada do tipo 6.
"""
import struct

R_NONE, R_32, R_26, R_HI16, R_LO16 = 0, 2, 4, 5, 6
FILE_OFF = 0x60


def relocs(d):
    """Lista de (endereco virtual, tipo), na ordem da tabela."""
    e_shoff = struct.unpack_from("<I", d, 0x20)[0]
    e_shentsize, e_shnum = struct.unpack_from("<HH", d, 0x2E)
    out = []
    for i in range(e_shnum):
        typ, _flags, _addr, off, size = struct.unpack_from("<5I", d, e_shoff + i * e_shentsize + 4)
        if typ == 0x700000A0:
            for k in range(off, off + size, 8):
                r_off, r_info = struct.unpack_from("<II", d, k)
                assert r_info >> 8 == 0, hex(r_info)          # um segmento so: bases 0
                out.append((r_off, r_info & 0xFF))
    return out


def relocated(d, base):
    """Copia do arquivo com as relocacoes aplicadas para o endereco base."""
    out = bytearray(d)
    rel = relocs(d)
    word = lambda va: struct.unpack_from("<I", d, va + FILE_OFF)[0]
    put = lambda va, w: struct.pack_into("<I", out, va + FILE_OFF, w & 0xFFFFFFFF)
    for k, (va, t) in enumerate(rel):
        w = word(va)
        if t == R_32:
            put(va, w + base)
        elif t == R_26:
            put(va, (w & 0xFC000000) | ((((w & 0x03FFFFFF) << 2) + base) >> 2 & 0x03FFFFFF))
        elif t == R_HI16:
            lo_va = next(v for v, tt in rel[k + 1:] if tt == R_LO16)
            lo = word(lo_va) & 0xFFFF
            full = ((w & 0xFFFF) << 16) + (lo - 0x10000 if lo & 0x8000 else lo) + base
            put(va, (w & 0xFFFF0000) | (((full + 0x8000) >> 16) & 0xFFFF))
        elif t == R_LO16:
            put(va, (w & 0xFFFF0000) | ((w + base) & 0xFFFF))
        elif t != R_NONE:
            raise AssertionError(t)
    return bytes(out)
